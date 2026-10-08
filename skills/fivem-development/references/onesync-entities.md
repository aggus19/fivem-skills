# OneSync, entities, state bags and routing buckets

Baseline: FXServer Recommended 35245 / Latest 37150 · Cfx Server (Enhanced) build 161 · game build 3889 — verified 2026-10-07. Natives below were checked with `scripts/natives.py show`.

## Contents
1. OneSync status and modes (2026)
2. Mental model: ownership, scope, culling, migration
3. OneSync convars
4. Server-side entity creation (and why)
5. Ownership, network ids, RPC natives
6. Orphan modes and persistence
7. Entity events: blocking and filtering
8. Entity lockdown, request-control filter, net game events
9. State bags (API, policy, strict mode, rate limits)
10. Routing buckets (instances)
11. Player scope, culling and far-away players
12. Population control
13. Pool sizes
14. Legacy vs Enhanced differences (OneSync)
15. Troubleshooting checklist
16. Sources

## 1. OneSync status and modes (2026)
- **OneSync is forced on** in current FXServer (citizenfx/fivem commit 19fa3d5, 2026-08-16): the `onesync` convar is internal and `set onesync on|off|legacy` lines are ignored. Remove `onesync`/`onesync_enabled`/`onesync_enableInfinity` from new configs. The docs page still lists `onesync [on/off/legacy]`; treat that as historical.
- What "on" means: the old *Infinity* model — 2048 slot cap, 16-bit network ids (65535), player and entity culling at 424 units, server-authoritative entity routing. "Legacy" mode (all players exist on every client) and "off" (P2P relay) are gone. Free up to 48 slots; more slots need an Element Club tier (Platinum for 2048).
- `sv_experimentalStateBagsHandler`, `sv_experimentalOneSyncPopulation`, `sv_experimentalNetGameEventHandler` are **removed** from the source (always on). The docs page still documents them "default true" — delete them from `server.cfg`.
- Enhanced (Cfx Server): only "big" mode, no P2P, sync over raw UDP (ENet still carries events), configurable tick rate `sv_syncTickRate` 1–120 (default 60) instead of the Legacy 30 Hz (40 with `sv_useAccurateSends`). See §14.

Write all code with these assumptions:
- A client only knows players/entities inside its scope. `GetActivePlayers()` (client) is **not** the player list; `GetPlayers()` (server) is.
- Entity handles are per-machine; send **network ids** across the wire.
- The client that owns an entity simulates it; the server holds the authoritative state copy and decides routing.

## 2. Mental model: ownership, scope, culling, migration
| Concept | What happens |
|---|---|
| Owner | One client per networked entity simulates it and sends sync nodes to the server. Query with `NetworkGetEntityOwner(ent)` (server: returns player source; `-1` = server-owned/no owner). `NetworkGetFirstEntityOwner(ent)` (server) = the creator. |
| Server-owned | Server-created entities with no relevant player stay server-owned (not simulated: no physics/AI) until a player gets near; then ownership migrates to a client. |
| Scope / relevance | A player sees entities/players within the focus zone (**424 units** around the player, hard-coded) and in the same routing bucket. |
| Culling | Outside that radius the entity is deleted *locally* on that client (not on the server). Per-entity/per-player overrides: `SetEntityDistanceCullingRadius`, `SetPlayerCullingRadius` — **deprecated** with known unfixable issues; avoid. |
| Migration | When the owner leaves range or disconnects, ownership moves to another relevant client (`onesync_forceMigration`, default true). With no relevant player the server decides per orphan mode (§6). |
| World grid | The map is divided into cells; each cell has an owning player who spawns population there. Each routing bucket has its own grid. |

Consequences: task/visual natives must run on the **owner** client (RPC natives are fallible); state set on a client that doesn't own an entity is rejected; an entity can "vanish" for a client simply by leaving scope; server-side handles are stable for the entity's lifetime but net ids are reused after deletion.

## 3. OneSync convars
Full list with defaults: [convars-and-commands.md](convars-and-commands.md). The ones that matter here:

| Convar | Default | Notes / recommendation |
|---|---|---|
| `onesync` | forced on | Internal since 2026-08; don't set. |
| `onesync_population` | `true` | `false` = no ambient peds/vehicles at all (server-wide). Startup convar. Prefer per-bucket `SetRoutingBucketPopulationEnabled`. |
| `onesync_forceMigration` | `true` | Keep on. |
| `onesync_distanceCulling` | `true` | Keep on. |
| `onesync_distanceCullVehicles` | `false` | Optional perf for busy servers; test vehicle pop-in. |
| `onesync_radiusFrequency` | `true` | Distance-based update rate. Keep on. |
| `sv_useAccurateSends` | `true` (Legacy) | Deprecated on Enhanced (use `sv_syncTickRate`). |
| `sv_entityLockdown` | `inactive` | `relaxed` for RP with ambient traffic; `strict` when the server spawns everything (no ambient population) (§8). |
| `sv_filterRequestControl` | `0` | `2` recommended (§8; [convars-and-commands.md](convars-and-commands.md) §4). |
| `sv_filterRequestControlSettleTimer` | `30000` ms | Settle time for modes 1 and 3. |
| `sv_stateBagStrictMode` | `false` | `setr sv_stateBagStrictMode true` in production (§9). |
| `sv_enableNetworkedSounds` | `true` | Set `false` unless a resource needs networked sounds. |
| `sv_enableNetworkedPhoneExplosions` | `false` | Keep `false`. |
| `sv_enableNetworkedScriptEntityStates` | `true` | `false` unless needed (blocks `SCRIPT_ENTITY_STATE_CHANGE_EVENT` abuse). |
| `sv_protectServerEntities` | `false` | Legacy (added 2025-03, replicated → use `setr`): clients can't delete server-created entities. Recommended `true` once no resource deletes server entities from the client. No effect on Enhanced (use lockdown). |
| `onesync_enableBeyond`, `onesync_enableInfinity`, `onesync_enabled`, `sv_enhancedHostSupport` | — | Internal/no effect. Remove. |
| `onesync_automaticResend` | `false` | Legacy only (ARQ); removed on Enhanced. |
| Enhanced only: `sv_syncTickRate` (60), `onesync_migrateDataTimeout` (10000), `onesync_mapBounds*`, `onesync_mapCellAreaSize` (100) | | See [gta5-enhanced.md](gta5-enhanced.md). |

## 4. Server-side entity creation (and why)
Create anything persistent, valuable or security-relevant on the **server**: the server knows it exists, controls cleanup, and you can run `strict` lockdown.
```lua
-- server.lua
local function spawnVehicle(model, coords, heading, plate)
    local hash = type(model) == 'string' and joaat(model) or model
    -- type: automobile | bike | boat | heli | plane | submarine | trailer | train
    local veh = CreateVehicleServerSetter(hash, 'automobile', coords.x, coords.y, coords.z, heading)
    local timeout = GetGameTimer() + 5000
    while not DoesEntityExist(veh) do
        if GetGameTimer() > timeout then return nil end
        Wait(0)
    end
    SetVehicleNumberPlateText(veh, plate)
    Entity(veh).state:set('owner', plate, true)
    return veh, NetworkGetNetworkIdFromEntity(veh)
end

local ped = CreatePed(4, `a_m_y_business_01`, x, y, z, h, true, true)       -- server-side despite "RPC" doc wording
local obj = CreateObjectNoOffset(`prop_bench_01a`, x, y, z, true, true, false)
```
- `CreateVehicleServerSetter(model, type, x, y, z, heading)` is the preferred vehicle API (creates the entity with all data server-side; no client involvement). `CreateVehicle(...)` on the server is an **RPC** native (executed on a client) — avoid it.
- The model does not need to be loaded on the server; the type string must match the model class (`GetVehicleType(veh)` returns it for existing vehicles).
- Server-created entities exist before any client streams them; client-side `NetToVeh(netId)` will be `0` until in scope. Wait for it:
```lua
-- client.lua
local veh = lib.waitFor(function()
    if NetworkDoesEntityExistWithNetworkId(netId) then return NetToVeh(netId) end
end, 'vehicle not streamed', 5000)
```
- Warp a player: `TaskWarpPedIntoVehicle(GetPlayerPed(src), veh, -1)` works server-side (verified server native) but can race with streaming; many frameworks warp from the client after the entity exists.
- Framework helpers: Qbox `qbx.spawnVehicle({...})` (`@qbx_core/modules/lib.lua`), ESX `ESX.OneSync.SpawnVehicle(...)`, QBCore `QBCore.Functions.CreateVehicle(...)` — check each framework file for exact signatures.
- Cleanup on stop:
```lua
local spawned = {}
AddEventHandler('onResourceStop', function(res)
    if res ~= GetCurrentResourceName() then return end
    for _, ent in pairs(spawned) do
        if DoesEntityExist(ent) then DeleteEntity(ent) end
    end
end)
```

## 5. Ownership, network ids, RPC natives
- Translate handles: `NetworkGetNetworkIdFromEntity(ent)` / `NetworkGetEntityFromNetworkId(netId)` (both exist server-side). Net ids are 16-bit and **reused** after deletion — never store them in the database; store plates, citizen ids, etc.
- Server natives that read sync state (`GetEntityCoords`, `GetEntityHeading`, `GetEntityModel`, `GetVehiclePedIsIn`, `GetPedInVehicleSeat`, `GetEntityRoutingBucket`, `GetEntityPopulationType`, `GetEntityScript`...) are cheap and authoritative enough for validation (distance checks).
- Server setters (`SetEntityCoords`, `SetEntityHeading`, `FreezeEntityPosition`, `SetEntityVelocity`, `SetVehicleDoorsLocked`, `SetPedConfigFlag`, `TaskWarpPedIntoVehicle`...) are **RPC**: forwarded to the owner, may fail if ownership changes mid-flight. For anything complex (`TaskPlayAnim`, attachments, scenarios), send a net event to `NetworkGetEntityOwner(ent)` and do it client-side after `NetworkRequestControlOfEntity`.
- Client control: `NetworkRequestControlOfEntity(ent)` + wait for `NetworkHasControlOfEntity(ent)`. With `sv_filterRequestControl` ≥ 1 these requests can be refused (§8) — design so the server or the owner performs the change.
- `GetNetTypeFromEntity(ent)` (server) returns the network object type; `GetEntityType` is client-side.

## 6. Orphan modes and persistence
`SetEntityOrphanMode(entity, mode)` / `GetEntityOrphanMode(entity)` (server):

| Mode | Name | Behaviour |
|---|---|---|
| `0` | DeleteWhenNotRelevant (default) | Server deletes the entity once it is not relevant to any player (not merely out of one player's scope). |
| `1` | DeleteOnOwnerDisconnect | Deleted when its *original* owner disconnects (if already gone: deleted immediately). Good for per-player props/vehicles. |
| `2` | KeepEntity | Never deleted by the server's relevancy cleanup. **Clients can still delete it**; you must delete it yourself. |

```lua
local veh = CreateVehicleServerSetter(`police`, 'automobile', x, y, z, h)
SetEntityOrphanMode(veh, 2)      -- persistent garage/parking vehicle
```
Persistence across restarts is your job: save model/plate/coords/props to SQL and respawn on start. Don't keep hundreds of `KeepEntity` entities: they all count against sync and pools.

## 7. Entity events: blocking and filtering
| Event (server) | Args | Use |
|---|---|---|
| `entityCreating` | `handle` | Fired before a **client**-created entity is accepted. `CancelEvent()` rejects it. Ideal model blacklist. |
| `entityCreated` | `handle` | After creation (any origin). Tagging, logging. Entity may not have full data yet. |
| `entityRemoved` | `entity` | Cleanup of your tables. |
| `onEntityBucketChange` / `onPlayerBucketChange` | `entity|player, bucket, oldBucket` | React to routing-bucket moves. |
| `playerEnteredScope` / `playerLeftScope` | `data` (`data.player`, `data['for']`) | Scope tracking — costly (N² calls); prefer state bags. |
| `weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, `removeAllWeaponsEvent`, `explosionEvent`, `giveWeaponEvent`, `removeWeaponEvent`, `clearPedTasksEvent`, `fireEvent` | `sender, data` | Routed game events; `CancelEvent()` blocks routing. Payload fields: docs server-events page / natives docs. |

```lua
-- server: block blacklisted client-created models and log the creator
local blocked = { [`rhino`] = true, [`hydra`] = true, [`lazer`] = true }

AddEventHandler('entityCreating', function(entity)
    local model = GetEntityModel(entity)
    if blocked[model] then
        local owner = NetworkGetEntityOwner(entity)
        print(('blocked model %s from %s'):format(model, owner))
        CancelEvent()
    end
end)
```
**Gotcha (open reports, 2026-10):** `GetEntityModel(entity)` can return `0` for a valid entity inside `entityCreating` (ambient pickups, client-created peds/vehicles; creation data not yet synced to the server). Do not `CancelEvent()` solely because the model is `0`: apply the model blacklist only when `model ~= 0`, and recheck in `entityCreated` (or after a short wait) with cleanup if it fails. Reports: citizenfx/fivem#2924 (closed), #4053, #2944 (RedM) — no fix is documented, so treat as version-sensitive.

Population type (`GetEntityPopulationType`, server) distinguishes ambient (1–5, random population) from mission/script (7 = `POPTYPE_MISSION`) entities — handy to skip ambient traffic in `entityCreating`.

**Entity lifecycle checklist:** (1) decide who creates and who may delete each entity; (2) persist a durable business/DB id; plates need uniqueness/ownership checks, while netIds and handles are temporary and reusable; (3) handle spawn failure (model timeout, `DoesEntityExist` timeout) without leaving a half-created state; (4) handle owner drop / migration (`SetEntityOrphanMode`, `entityRemoved`); (5) make cleanup idempotent (safe to call twice); (6) on resource start, **reconcile** with existing world entities/DB state before respawning persistent objects so restarts don't duplicate them.

## 8. Entity lockdown, request-control filter, net game events
**Entity lockdown** — who may create networked entities:

| Mode | Effect |
|---|---|
| `inactive` (default) | Clients can create any entity. |
| `relaxed` | Client **script** entities are blocked; ambient population still created by clients. On Enhanced, population only spawns if the player owns that world-grid cell. |
| `strict` | Clients cannot create any networked entity (ambient population included, verified in source) — the server must spawn everything. |
| `full` | **Enhanced only** (docs): disables dummy object creation (dynamic map objects created from clients). |
| `no_dummy` | Legacy source (`OneSyncVars.h`, undocumented): allows all client entities except networked dummy objects that fail validation (exploded gas pumps/propane tanks are still allowed). Niche; prefer `relaxed`. |

```cfg
set sv_entityLockdown relaxed         # global; strict only if the server spawns every entity
```
```lua
SetRoutingBucketEntityLockdownMode(1, 'strict')   -- per bucket (server); 'inactive' | 'relaxed' | 'strict'
```
Migration path: `relaxed` first, find resources that spawn client-side (they break: entity never appears), move them to server spawning (or callbacks that spawn on the server and return the net id). Go `strict` only if you don't need ambient population (PvP, minigame buckets) or you spawn traffic server-side. Local, non-networked entities (`CreateVehicle(..., false, false)` on the client — `isNetwork=false`) are unaffected by lockdown.

**Request-control filter** (`sv_filterRequestControl`, blocks `REQUEST_CONTROL_EVENT` routing):

| Value | Effect |
|---|---|
| `0` | Off (default); also disables bucket/lockdown policies below. |
| `1` | Block requests for player-controlled entities (occupied vehicles) that are "settled" (older than `sv_filterRequestControlSettleTimer`, 30000 ms). |
| `2` | Block requests for all player-controlled entities. |
| `3` | `2` + block settled non-player entities. |
| `4` | Never route `REQUEST_CONTROL_EVENT`. |
| `-1` | Like `2` but warns in console. |

Any mode ≠ 0 also blocks control requests across routing buckets and from senders in `strict` lockdown. Exempt one entity with `SetEntityIgnoreRequestControlFilter(entity, true)` (server). Recommended: `2` (see [convars-and-commands.md](convars-and-commands.md) §4), after testing towing/impound/carry scripts.

**Net game events**: `block_net_game_event "<EVENT_NAME>"` / `unblock_net_game_event` (startup cfg) drop game events server-wide (list: https://docs.fivem.net/docs/game-references/net-game-events/). Common hardening: `sv_enableNetworkedPhoneExplosions false` (default), `sv_enableNetworkedSounds false`, `sv_enableNetworkedScriptEntityStates false`, and cancel `explosionEvent`/`ptFxEvent` you don't expect.

## 9. State bags
```lua
-- server
Player(src).state:set('job', 'police', true)       -- replicated to clients that can see the player
Entity(veh).state:set('fuel', 75.0, true)
Entity(veh).state:set('serverOnly', 1, false)       -- server-only value
GlobalState.weather = 'RAIN'                        -- global bag, replicated to ALL clients (keep it small)

-- client
local fuel = Entity(veh).state.fuel
LocalPlayer.state:set('isBusy', true, true)         -- client writes its OWN player bag (untrusted; blocked in strict mode)

-- either side
local cookie = AddStateBagChangeHandler('fuel', nil, function(bagName, key, value, reserved, replicated)
    local ent = GetEntityFromStateBagName(bagName)
    if ent == 0 then return end                     -- not streamed here (Legacy can fire before entity exists)
    -- `value` is the NEW value; the bag still holds the old value during the callback
end)
-- RemoveStateBagChangeHandler(cookie)
```
- Bag names: `player:<serverId>`, `entity:<netId>`, `localEntity:<handle>`, `global`. Helpers (shared): `GetEntityFromStateBagName`, `GetPlayerFromStateBagName`, `GetStateBagValue`, `GetStateBagKeys`, `StateBagHasKey`, `SetStateBagValue`, `EnsureEntityStateBag`.
- `Player(id)` always takes a **server ID** (`player:<id>` bag). On the client, `Player(PlayerId())` is a bug (`PlayerId()` is the local player index). Use `LocalPlayer.state` (internally `Player(-1)` → `GetPlayerServerId(PlayerId())`) or `Player(GetPlayerServerId(PlayerId()))`. Source: citizenfx/fivem `data/shared/citizen/scripting/lua/scheduler.lua` (`playerMT.__index`).
- Keys are enumerable with `GetStateBagKeys('player:5')` (shared native); single values with `GetStateBagValue(bagName, key)`.
- Defaults: server sets replicate; client sets don't, unless `state:set(k, v, true)`.
- Shallow semantics: `Entity(x).state.a.b = 1` does **not** replicate; set the whole value or use flat keys (`state['a:b']`).
- Policy: by default player bags are writable by that player and the server; entity bags by the owning client and the server; global only by the server.
- **`setr sv_stateBagStrictMode true`** (server ≥ 12739; use `setr` so clients know it): only the server can modify networked entity and player bags; client writes error with `StateBags can't be modified from the client, because the StateBag strict mode is enabled`. Client-local entities are unaffected. Breaks resources that set `LocalPlayer.state` from the client (some voice/HUD scripts) — move those writes to server events with validation, or leave strict off and validate.
- Change handlers cannot reject a change. Without strict mode, revert unauthorised writes on the server (`Entity(ent).state:set(key, oldValue, true)`) and never trust client-writable keys for money/permissions.
- Rate limits: state bag writes from clients go through the `stateBag`, `stateBagFlood` and `stateBagSize` limiters (`set rateLimiter_stateBag_rate <n>` / `_burst`; defaults rate/burst 75/125, flood 150/175, size 131072/262144 bytes — same constants in Legacy source `StateBagPacketHandler.cpp` and the Enhanced docs table). Flooding gets the client dropped; the console names the convar to raise.
- Size: keep values small (ids, numbers, short strings). Large tables in `GlobalState` are re-sent to every client on change.
- Enhanced: handlers only fire when the entity exists; only values marked replicated are sent; sets ~10× faster; max 32 KB per value (gta5-enhanced.md 5b).
- When a client writes to a bag the server doesn't know yet, only `entity:<netId>` bags are auto-created. Writes to unknown `player:`/`global` bags are silently dropped. Under the base `stateBag` limit, excess updates are dropped with at most one `sbag-update-dropped` warning per second per client (no kick). Source: `StateBagPacketHandler.cpp`.
- Client side, resolving a netId the client doesn't hold (`NetworkGetEntityFromNetworkId`, `GetEntityFromStateBagName` in a change handler for a far-away entity) prints `GetNetworkObject: no object by ID <n>` each time. Guard with `NetworkDoesEntityExistWithNetworkId(netId)` (parse `entity:(%d+)` from the bag name) to avoid console spam.

## 10. Routing buckets (instances)
Server natives (all verified):

| Native | Purpose |
|---|---|
| `SetPlayerRoutingBucket(src, bucket)` / `GetPlayerRoutingBucket(src)` | Move/query a player. |
| `SetEntityRoutingBucket(ent, bucket)` / `GetEntityRoutingBucket(ent)` | Move/query an entity (vehicles, peds, objects). |
| `SetRoutingBucketPopulationEnabled(bucket, bool)` | Ambient population per bucket. |
| `SetRoutingBucketEntityLockdownMode(bucket, mode)` | Lockdown per bucket. |

```lua
-- server: private instance for a player and their vehicle
local function enterInstance(src, bucket)
    SetRoutingBucketPopulationEnabled(bucket, false)
    SetRoutingBucketEntityLockdownMode(bucket, 'strict')
    local ped = GetPlayerPed(src)
    local veh = GetVehiclePedIsIn(ped, false)
    SetPlayerRoutingBucket(src, bucket)
    if veh ~= 0 then SetEntityRoutingBucket(veh, bucket) end
end

AddEventHandler('playerDropped', function()
    -- buckets are per session; nothing to persist, but clear your own bookkeeping
end)
```
- Bucket `0` is the default world; any integer works; buckets don't need creating. Players in different buckets don't see or hear each other's entities (voice resources must also respect buckets; pma-voice does with `SetPlayerRoutingBucket`-aware channels — check its docs).
- Use for: character selection, apartments/shells, minigames, admin rooms, races. Do **not** use for ordinary MLO interiors.
- Common bugs: forgetting to move the vehicle/trailer/attached objects; not resetting to bucket 0 on logout/character switch; spawning entities and not setting their bucket (server-created entities start in bucket 0).
- Framework: Qbox `exports.qbx_core:SetPlayerBucket(src, bucket)` / `SetEntityBucket` (check Qbox docs).

## 11. Player scope, culling and far-away players
- Clients see players within 424 units in the same bucket. `GetActivePlayers()` returns only those; `GetPlayerFromServerId(id)` returns `-1` for out-of-scope players.
- For far players use the server: `GetPlayers()` (Lua helper returning sources as strings), `GetEntityCoords(GetPlayerPed(src))`. Send positions at low frequency (e.g. police GPS every 2–5 s, `TriggerLatentClientEvent` for bigger payloads) or use per-player state bags.
- `playerEnteredScope`/`playerLeftScope` exist but scale quadratically; prefer state bag handlers.
- Don't raise culling radius to "fix" far blips — culling natives are deprecated.

## 12. Population control
- Global off: `set onesync_population false` (startup). Per bucket: `SetRoutingBucketPopulationEnabled`.
- Density: client natives each frame (`SetVehicleDensityMultiplierThisFrame`, `SetPedDensityMultiplierThisFrame`...) on every client — population is spawned by the grid-owning client, so all clients must agree.
- Client population hook: `populationPedCreating` with `setters.setModel()` / `CancelEvent()`. It is not a server event or an authority boundary. Server network-entity filtering uses `entityCreating`; per-bucket population uses `SetRoutingBucketPopulationEnabled`.
- **`strict` lockdown also blocks ambient population** (population is client-created): source `ServerGameState.cpp` only allows random population types (ambient/parked/patrol/permanent/scenario) when the mode is *not* strict. So `strict` = empty streets unless the server spawns peds/vehicles itself; `relaxed` keeps ambient life while blocking script entities. A bucket with population disabled is treated as `strict` for lockdown checks. (Enhanced: in `relaxed`, population spawns only in grid cells the player owns.)

## 13. Pool sizes
`increase_pool_size "<Pool>" <increase>` (startup only; clients restart once to adapt). Allowed pools and max increase (FiveM): AnimStore 20480, AttachmentExtension 430, Building 20000, CMoveObject 600, CWeaponComponentInfo 2048, EntityDescPool 20480, fragInstGta 2000, FragmentStore 14000, InteriorProxy 450, LightEntity 1000, netGameEvent 400, Object 2000, ObjectIntelligence 512, OcclusionInteriorInfo 20, OcclusionPathNode 5000, OcclusionPortalEntity 750, OcclusionPortalInfo 750, PortalInst 225, ScaleformStore 200, StaticBounds 5000, TxdStore 26000. Limits come from content.cfx.re and may change. Raise only for a matching crash/"pool full" error. `set moo 31337` bypass is dev-only (Legacy; removed on Enhanced).

## 14. Legacy vs Enhanced differences (OneSync)
| Area | Legacy (FXServer) | Enhanced (Cfx Server) |
|---|---|---|
| Mode | Forced on (Infinity semantics) | "big" mode only; P2P removed |
| Tick rate | ~30 Hz (40 with `sv_useAccurateSends`) | `sv_syncTickRate` 1–120, default 60 |
| Player ids | Monotonic, wrap at 65535 | **Reused** immediately after disconnect |
| Player join/leave events for others | Global | Only for players in range |
| Lockdown | inactive/relaxed/strict | + `full`; `relaxed` population only in owned grid cells |
| State bags | Handlers may fire before entity exists; all values sent | Only when entity exists; only replicated values sent; ~10× faster sets |
| Migration timeout | — | `onesync_migrateDataTimeout` (10000 ms) |
| Removed | — | `onesync_automaticResend`, `sv_netHttp2`; no-ops: `onesync_enableBeyond`, `sv_enhancedHostSupport`, `sv_protectServerEntities` (Legacy-only convar, see [convars-and-commands.md](convars-and-commands.md) §4) |

## 15. Troubleshooting checklist
- Entity spawns on server but client handle is 0 → not in scope yet / wrong bucket; wait for `NetworkDoesEntityExistWithNetworkId`.
- Entity disappears when the spawning player leaves → orphan mode 0/1; use 2 and manage cleanup.
- "Vehicle won't spawn" after enabling `strict` → resource spawns client-side; move to server.
- Client can't take control (tow/carry scripts) → `sv_filterRequestControl`; use server natives or `SetEntityIgnoreRequestControlFilter`.
- State bag write ignored → not owner, strict mode on, or shallow nested set.
- Player list incomplete on client → OneSync scope; use server data.
- Desync in instances → entity left in bucket 0; check `GetEntityRoutingBucket`.

## 16. Sources
- https://docs.fivem.net/docs/scripting-reference/onesync/ (opened via citizenfx/fivem-docs `content/docs/scripting-reference/onesync/_index.md`, commit c2b2125, 2026-10-01)
- https://docs.fivem.net/docs/server-manual/server-commands/ (same repo, `server-manual/server-commands.md`)
- https://docs.fivem.net/docs/scripting-manual/networking/state-bags/ · https://docs.fivem.net/docs/scripting-manual/networking/ids/
- https://docs.fivem.net/docs/developers/legacy-vs-enhanced/
- https://github.com/citizenfx/fivem/issues/2924 · /issues/4053 · /issues/2944 (`GetEntityModel` returning 0 in `entityCreating`, checked via GitHub API 2026-10-08)
- https://docs.fivem.net/docs/scripting-reference/events/server-events/ and event pages `onEntityBucketChange`, `onPlayerBucketChange`, `populationPedCreating`
- Natives: https://docs.fivem.net/natives/?_0x489E9162 (SET_ENTITY_ORPHAN_MODE), ?_0xA0F2201F (SET_ROUTING_BUCKET_ENTITY_LOCKDOWN_MODE), ?_0x5BA35AAF (ADD_STATE_BAG_CHANGE_HANDLER), ?_0x9F7F8D36 (SET_ENTITY_IGNORE_REQUEST_CONTROL_FILTER), ?_0x8A2FBAD4 (SET_PLAYER_CULLING_RADIUS)
- Forum: https://forum.cfx.re/t/5415045 (Dev Update #3: tick rate, state bags), https://forum.cfx.re/t/5391635 (Dev Update #1: sync-mode consolidation)
- citizenfx/fivem source (convar/forced OneSync commits): https://github.com/citizenfx/fivem
