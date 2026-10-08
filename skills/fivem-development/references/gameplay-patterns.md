# Gameplay patterns: vehicles, peds, animations, props, blips, interactions, world sync

Baseline: FXServer Legacy 35245 / game build 3889, ox_lib 3.40 — verified 2026-10-07.
All natives below were checked with `python scripts/natives.py show <Name>`; re-check parameters before relying on them. RP system architecture (jobs, garages, housing, death, status…) lives in [rp-systems-design.md](rp-systems-design.md); add-on vehicles and handling in [vehicles-and-handling.md](vehicles-and-handling.md).

## Contents
1. Vehicles (spawn, properties, cleanup)
2. Peds and NPCs
3. Animations and props
4. Blips and markers
5. Interaction pattern (target / points)
6. Weather and time sync
7. Instances (routing buckets)
8. Population density
9. Job flow template
10. Persistence of player state
11. Sources

## 1. Vehicles
Spawn server-side (`onesync-entities.md`), then apply properties on the owner client:
```lua
-- server
local function spawnOwnedVehicle(src, model, vehType, coords, props)
    local veh = CreateVehicleServerSetter(joaat(model), vehType, coords.x, coords.y, coords.z, coords.w)
    local timeout = GetGameTimer() + 5000
    while not DoesEntityExist(veh) do
        if GetGameTimer() > timeout then return nil end
        Wait(0)
    end
    SetVehicleNumberPlateText(veh, props.plate)
    SetEntityOrphanMode(veh, 2)                      -- keep when owner leaves (persistent vehicles only)
    Entity(veh).state:set('owner', Bridge.GetIdentifier(src), true)
    local netId = NetworkGetNetworkIdFromEntity(veh)
    TriggerClientEvent('myres:client:vehicleSpawned', src, netId, props)
    return veh
end

-- client
RegisterNetEvent('myres:client:vehicleSpawned', function(netId, props)
    local veh = lib.waitFor(function()
        if NetworkDoesEntityExistWithNetworkId(netId) then return NetToVeh(netId) end
    end, 'vehicle did not network', 5000)
    if not veh then return end
    lib.setVehicleProperties(veh, props)
    TaskWarpPedIntoVehicle(cache.ped, veh, -1)
end)
```
- `vehType` for `CreateVehicleServerSetter`: `'automobile'`, `'bike'`, `'boat'`, `'heli'`, `'plane'`, `'submarine'`, `'trailer'`, `'train'` — store it with the model in config/DB.
- Plates: max 8 chars; `GetVehicleNumberPlateText` pads with spaces — trim before comparing.
- Fuel: ox_fuel uses `Entity(veh).state.fuel`; LegacyFuel/cdn-fuel use exports — detect which is started.
- Keys/locks: see `rp-systems-design.md` §4. Never lock/unlock from a client event without a server ownership check.
- Delete server-side (`DeleteEntity(veh)` on server) after checking the requester owns it and is near it.

## 2. Peds and NPCs
```lua
-- client: local (non-networked) shop NPC, spawned only near the player
local ped
local point = lib.points.new({ coords = vec3(25.7, -1347.3, 29.5), distance = 40.0 })

function point:onEnter()
    local model = `mp_m_shopkeep_01`
    lib.requestModel(model)
    ped = CreatePed(4, model, self.coords.x, self.coords.y, self.coords.z - 1.0, 270.0, false, true)
    SetEntityInvincible(ped, true)
    FreezeEntityPosition(ped, true)
    SetBlockingOfNonTemporaryEvents(ped, true)
    TaskStartScenarioInPlace(ped, 'WORLD_HUMAN_STAND_IMPATIENT', 0, true)
    SetModelAsNoLongerNeeded(model)
end

function point:onExit()
    if ped and DoesEntityExist(ped) then DeleteEntity(ped) end
    ped = nil
end
```
- Local NPCs (shops, job givers) = zero network cost and unaffected by `sv_entityLockdown`.
- Networked NPCs (missions, AI drivers, hostages): create on the server (`CreatePed` exists server-side), task them on the owner client (`NetworkGetEntityOwner`), and handle ownership migration.
- AI driving: `TaskVehicleDriveToCoordLongrange(ped, veh, x, y, z, speed, drivingStyle, stopRange)` + `SetDriverAbility(ped, 1.0)` + `SetPedKeepTask(ped, true)` on the owner.

## 3. Animations and props
```lua
-- client
lib.requestAnimDict('mp_common')
TaskPlayAnim(cache.ped, 'mp_common', 'givetake1_a', 8.0, -8.0, 2000, 49, 0.0, false, false, false)
RemoveAnimDict('mp_common')

-- prop in hand (local, cosmetic)
local model = `prop_cs_burger_01`
lib.requestModel(model)
local prop = CreateObject(model, 0.0, 0.0, 0.0, false, false, false)
AttachEntityToEntity(prop, cache.ped, GetPedBoneIndex(cache.ped, 18905),
    0.13, 0.05, 0.02, -50.0, 16.0, 60.0, true, true, false, true, 1, true)
SetModelAsNoLongerNeeded(model)
-- cleanup: DeleteEntity(prop); ClearPedTasks(cache.ped)
```
- Flags: 1 = loop, 16 = upper body, 32 = player keeps control → **49** = looped upper-body anim while moving; 0 = full body once.
- Prefer `lib.progressBar({ duration, label, anim = { dict, clip }, prop = { model, bone, pos, rot } })`: handles loading, cancel and cleanup.
- Cosmetic props are local (`isNetwork = false`); props other players must see should be networked or replicated via a state bag that every client renders.
- Emote menus in 2026: `scully_emotemenu` (Qbox recipe), rpemotes forks — integrate via their exports rather than duplicating anim tables.

## 4. Blips and markers
```lua
-- client
local blip = AddBlipForCoord(x, y, z)
SetBlipSprite(blip, 52)
SetBlipColour(blip, 2)
SetBlipScale(blip, 0.8)
SetBlipAsShortRange(blip, true)
BeginTextCommandSetBlipName('STRING')
AddTextComponentSubstringPlayerName('Shop')
EndTextCommandSetBlipName(blip)
-- RemoveBlip(blip) on resource stop
```
- Job-only blips: the server tells the client which ones to create; the client check is UX only.
- Live unit blips (police/EMS): OneSync Infinity culls distant players, so `AddBlipForEntity` fails outside scope. Send coords from the server on an interval to the relevant job members only (latent/throttled), or use a dedicated resource (Renewed-Dutyblips, ps-dispatch features).
- Markers (`DrawMarker`) must be drawn **every frame**: only inside a `lib.points` `nearby` callback, never in an always-on loop.
- Sprite/colour ids: https://docs.fivem.net/docs/game-references/blips/ · markers: https://docs.fivem.net/docs/game-references/markers/

## 5. Interaction pattern
1. Config lists locations (shared) and prices/rewards (server-only config).
2. Client: ox_target zone/entity option or `lib.points` → show option (UX only).
3. Client sends **intent** only (`myres:server:buy`, `itemName`, `count`) or calls a `lib.callback`.
4. Server: five checks (`security.md`): who, allowed, where (distance to the configured location), what (whitelist/clamp), how often → remove → add → log.
5. Client updates UI from the server response.

```lua
-- server
lib.callback.register('myres:server:buy', function(source, shopId, item, count)
    local src = source
    local shop = ServerConfig.Shops[shopId]
    if not shop or type(item) ~= 'string' or type(count) ~= 'number' then return false end
    count = math.floor(count)
    if count < 1 or count > 50 then return false end
    local price = shop.items[item]
    if not price then return false end
    if #(GetEntityCoords(GetPlayerPed(src)) - shop.coords) > 5.0 then return false end
    if not exports.ox_inventory:CanCarryItem(src, item, count) then return false, 'cannot_carry' end
    if not Bridge.RemoveMoney(src, 'cash', price * count, 'shop:' .. shopId) then return false, 'no_money' end
    exports.ox_inventory:AddItem(src, item, count)
    return true
end)
```

## 6. Weather and time sync
- Weather/time are **client-side** game state; a server resource must publish the authoritative value and every client applies it.
- Pattern used by Renewed-Weathersync (Qbox recipe default): server writes `GlobalState.weather` / `GlobalState.blackout`; clients react with `AddStateBagChangeHandler('weather', 'global', ...)` and call `SetWeatherTypeOvertimePersist(weather, 60.0)` / `SetWeatherTypeNowPersist`, `SetArtificialLightsState(blackout)`.
- Time: server keeps the clock; clients call `NetworkOverrideClockTime(h, m, s)` and optionally `NetworkOverrideClockMillisecondsPerGameMinute(ms)` (2000 ms = vanilla 48-min day).
- Per-player overrides (interiors, cutscenes, instances): use a player state bag (`Player(src).state`) or stop applying sync while inside, then resync on exit.
- Resources: Renewed-Weathersync (v1.1.8, drop-in compatible with qb-weathersync), qb-weathersync (QBCore), esx_weather (ESX addons); `qbx_weathersync` is **archived** — don't recommend it.
```lua
-- client: minimal sync consumer
local function applyWeather(w)
    if not w then return end
    SetWeatherTypeOvertimePersist(w, 30.0)
end
applyWeather(GlobalState.weather)
AddStateBagChangeHandler('weather', 'global', function(_, _, value) applyWeather(value) end)
```

## 7. Instances (routing buckets)
- Apartments, character creation, interiors per player, minigames: `SetPlayerRoutingBucket(src, bucket)` server-side; also move their vehicle (`SetEntityRoutingBucket`). Disable ambient population in custom buckets: `SetRoutingBucketPopulationEnabled(bucket, false)`; lock entity creation with `SetRoutingBucketEntityLockdownMode(bucket, 'strict')`.
- Always return players to bucket 0 on exit **and** on `playerDropped`/reconnect paths.
- pma-voice: players only hear others in the same bucket (see pma-voice `docs/routingBuckets.md`).

## 8. Population density
- Per-frame client natives: `SetPedDensityMultiplierThisFrame`, `SetScenarioPedDensityMultiplierThisFrame(interior, exterior)`, `SetVehicleDensityMultiplierThisFrame`, `SetRandomVehicleDensityMultiplierThisFrame`, `SetParkedVehicleDensityMultiplierThisFrame` — each must be called every frame (`Wait(0)` loop), so keep one central resource (e.g. `qbx_density`) instead of several.
- Server-side alternatives: `populationPedCreating` event to cancel/replace spawns; `SetRoutingBucketPopulationEnabled` per bucket.

## 9. Job flow template (e.g. delivery job)
- Server keeps `activeJobs[src] = { startedAt, route, stage, vehicleNetId }`.
- Client receives the route; on reaching a checkpoint it asks the server to advance; server validates distance to the **expected** checkpoint, minimum elapsed time per stage and that the job vehicle is the one it spawned.
- Payout computed by the server from completed stages; clear state on finish, `playerDropped` and resource stop; delete job vehicles server-side.
- Use `lib.cron.new` or a server timer for timeouts (abandoned jobs).

## 10. Persistence of player state
- Framework metadata (Qbox `SetMetadata`, ESX `setMeta`, QBCore `SetMetaData`) for small per-character values (hunger, stress, licences).
- Own tables keyed by character id (`citizenid` / ESX identifier / ox `charId`) for larger data (see `rp-systems-design.md` for schemas).
- KVP (`SetResourceKvp`/`GetResourceKvpString`) for small server or client-local settings (client KVP lives on the player's machine: never trust it). On Enhanced, KVP DB files need migration.

## 11. Sources
- https://docs.fivem.net/natives/ (all natives above; checked through `scripts/natives.py`)
- https://docs.fivem.net/docs/game-references/blips/ · https://docs.fivem.net/docs/game-references/markers/
- https://docs.fivem.net/docs/scripting-reference/events/list/populationPedCreating/
- https://github.com/Renewed-Scripts/Renewed-Weathersync (client/weather.lua: GlobalState + state bag handlers)
- https://github.com/Qbox-project/txAdminRecipe (qbox.yaml default resources) · https://github.com/Qbox-project/qbx_weathersync (archived)
- https://github.com/AvarianKnight/pma-voice (docs/routingBuckets.md)
- https://overextended.dev/docs/ox_lib
