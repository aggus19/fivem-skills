# Server-side anticheat design (defensive)

Baseline: FXServer Legacy 35245 / Latest 37150 (OneSync forced on), game-event structs read from `ServerGameState.cpp` (master, last change 2026-09-04) — verified 2026-10-07. Field names are the **Legacy GTA V** (`STATE_FIVE`) structs; on GTA V Enhanced they may differ (**UNVERIFIED**) — log `json.encode(ev)` once before relying on a field.

## Contents
1. Principles
2. Architecture: log mode → enforce mode
3. Game events you can intercept (names, fields, cancel effect)
4. Event filters (explosions, ptfx, projectiles, weapons, tasks, damage, entities)
5. Built-in hard blocks (`block_net_game_event`, convars)
6. Server-side state checks (movement, health, weapons, vehicles)
7. Heartbeats and honeypots
8. Scoring, evidence and sanctions
9. What a server-side anticheat cannot see
10. Sources

## 1. Principles
- **Prevention beats detection.** Most "anticheat" wins come from secure resources ([security.md](security.md) §2–§6): server-authoritative economy, `sv_entityLockdown strict`, `sv_stateBagStrictMode true`, `sv_filterRequestControl`, `sv_scriptHookAllowed false`, `sv_pureLevel 1/2`.
- **Server-side only for decisions.** Client-side checks are trivially disabled by executors; use them as signals at most.
- **Cancel, then log, then judge.** Cancelling a bad game event protects players instantly; bans need evidence and human review except for zero-false-positive signals (honeypots, impossible values).
- **Measure false positives first.** Desync, lag spikes, teleports by your own scripts, respawns, routing-bucket changes and vehicles all look like cheats to naïve checks.
- Commercial anticheats exist (paid resources); evaluate them like any third-party code (audit-checklist.md) — an obfuscated anticheat with server HTTP access is itself a supply-chain risk.

## 2. Architecture: log mode → enforce mode
```
resources/[security]/myac/
  fxmanifest.lua        -- server_scripts only (+ tiny client heartbeat)
  server/config.lua     -- thresholds, allow-lists, mode = 'log' | 'enforce'
  server/strikes.lua    -- scoring + evidence buffer + Log.alert
  server/gameevents.lua -- §4 filters
  server/checks.lua     -- §6 periodic checks
  server/honeypots.lua  -- §7
```
Start every rule in `log` mode for a week, review the logs, tune allow-lists, then switch the rule to `enforce`. Keep the mode **per rule**.

Shared helpers used below (server):
```lua
-- server/strikes.lua
AC = { strikes = {}, mode = ServerConfig.Mode or {} }

function AC.enforce(rule) return AC.mode[rule] == 'enforce' end

function AC.flag(src, rule, data, weight)
    src = tonumber(src)                                 -- game events pass the sender as a string
    if not src or src <= 0 then return end
    local s = AC.strikes[src] or { score = 0, log = {} }
    s.score = s.score + (weight or 1)
    s.log[#s.log + 1] = { t = os.time(), rule = rule, data = data }
    if #s.log > 50 then table.remove(s.log, 1) end
    AC.strikes[src] = s
    Log.alert(('AC %s'):format(rule), ('%s (%s) score=%d %s'):format(
        GetPlayerName(src) or '?', GetPlayerIdentifierByType(src, 'license') or '?', s.score, json.encode(data)))
end

AddEventHandler('playerDropped', function() AC.strikes[source] = nil end)
```
`Log.alert` is the batched webhook logger from security.md §11; `allow(src, key, rate, burst)` is the token bucket from security.md §10.

## 3. Game events you can intercept
All are **server** events (OneSync), registered with `AddEventHandler` (not `RegisterNetEvent`); handler `(sender, ev)` where `sender` is the client's server ID (passed as a **string** by the dispatcher — use `tonumber(sender)`). `CancelEvent()` stops the game event being routed to other clients.

| Event | Main fields (Legacy) | Typical abuse |
|---|---|---|
| `explosionEvent` | `ownerNetId, explosionType, damageScale, posX/Y/Z, cameraShake, isAudible, isInvisible` (+ undocumented `f*`) | explosion spam, invisible kills |
| `ptFxEvent` | `effectHash, assetHash, posX/Y/Z, offsetX/Y/Z, rotX/Y/Z, scale, axisBitset, isOnEntity, entityNetId` | particle spam / crash attempts |
| `startProjectileEvent` | `ownerId, projectileHash, weaponHash, initialPositionX/Y/Z, targetEntity, firePositionX/Y/Z, effectGroup, commandFireSingleBullet, throwTaskSequence` | projectile spam, weapons not owned |
| `weaponDamageEvent` | `damageType, weaponType, overrideDefaultDamage, weaponDamage, hitGlobalId, hitGlobalIds, willKill, silenced, damageFlags, damageTime, hitComponent, localPosX/Y/Z, tyreIndex, suspensionIndex` | damage multipliers, kill-all; fires only for damage to **remotely owned** entities (docs) |
| `giveWeaponEvent` | `pedId, weaponType, ammo, givenAsPickup, unk1` | giving weapons to other players |
| `removeWeaponEvent` | `pedId, weaponType` | stripping others' weapons |
| `removeAllWeaponsEvent` | `pedId` | stripping others' weapons |
| `clearPedTasksEvent` | `pedId, immediately` | yanking players out of vehicles / freezing |
| `fireEvent` | `fires` (array: `posX/Y/Z, isEntity, entityGlobalId, weaponHash, maxChildren, fireId …`) | fire spam |
| `respawnPlayerPedEvent` | `posX/Y/Z, …` | — (rarely filtered) |
| `vehicleComponentControlEvent` | `vehicleGlobalId, pedGlobalId, componentIndex, request, componentIsSeat, pedInSeat` | — |
| `requestNetworkSyncedSceneEvent` / `startNetworkSyncedSceneEvent` / `updateNetworkSyncedSceneEvent` / `stopNetworkSyncedSceneEvent` | scene ids/flags | animation trolling (rare) |
| `entityCreating` | `(entity)` handle; `CancelEvent()` **deletes** the entity | blacklisted models, spawn spam |
| `entityCreated`, `entityRemoved` | `(entity)` | auditing |

Fields beginning with `f`/`unk` are undocumented — do not rely on them.

## 4. Event filters
```lua
-- server/gameevents.lua
local Cfg = ServerConfig.GameEvents   -- allow-lists built from your log-mode data

AddEventHandler('explosionEvent', function(sender, ev)
    local src = tonumber(sender)
    local bad = not Cfg.allowedExplosionTypes[ev.explosionType]
        or ev.isInvisible
        or (ev.damageScale or 1.0) > 1.0
        or not allow(src, 'explosion', 1, 5)
    if bad then
        AC.flag(src, 'explosion', { type = ev.explosionType, scale = ev.damageScale, x = ev.posX, y = ev.posY })
        if AC.enforce('explosion') then CancelEvent() end
    end
end)

AddEventHandler('ptFxEvent', function(sender, ev)
    local src = tonumber(sender)
    if (ev.scale or 1.0) > Cfg.maxPtfxScale or not allow(src, 'ptfx', 2, 10) then
        AC.flag(src, 'ptfx', { effect = ev.effectHash, asset = ev.assetHash, scale = ev.scale })
        if AC.enforce('ptfx') then CancelEvent() end
    end
end)

AddEventHandler('startProjectileEvent', function(sender, ev)
    local src = tonumber(sender)
    if Cfg.blockedProjectileWeapons[ev.weaponHash] or not allow(src, 'projectile', 5, 20) then
        AC.flag(src, 'projectile', { weapon = ev.weaponHash, projectile = ev.projectileHash })
        if AC.enforce('projectile') then CancelEvent() end
    end
end)

-- Weapons and tasks on *other* players' peds: do it through your own server-validated events instead.
for _, name in ipairs({ 'giveWeaponEvent', 'removeWeaponEvent', 'removeAllWeaponsEvent', 'clearPedTasksEvent' }) do
    AddEventHandler(name, function(sender, ev)
        AC.flag(sender, name, { ped = ev.pedId, weapon = ev.weaponType }, 2)
        if AC.enforce(name) then CancelEvent() end
    end)
end

AddEventHandler('weaponDamageEvent', function(sender, ev)
    local src = tonumber(sender)
    if ev.overrideDefaultDamage and (ev.weaponDamage or 0) > Cfg.maxWeaponDamage then
        AC.flag(src, 'damage-value', { weapon = ev.weaponType, dmg = ev.weaponDamage })
        if AC.enforce('damage-value') then CancelEvent() end
        return
    end
    local victim = ev.hitGlobalId and NetworkGetEntityFromNetworkId(ev.hitGlobalId) or 0
    if victim ~= 0 and DoesEntityExist(victim) then
        local dist = #(GetEntityCoords(GetPlayerPed(src)) - GetEntityCoords(victim))
        if dist > (Cfg.maxRangeByWeapon[ev.weaponType] or 300.0) then
            AC.flag(src, 'damage-range', { weapon = ev.weaponType, dist = dist })
            if AC.enforce('damage-range') then CancelEvent() end
        end
    end
end)

AddEventHandler('entityCreating', function(entity)
    local model = GetEntityModel(entity)
    local owner = NetworkGetFirstEntityOwner(entity)
    if Cfg.blacklistedModels[model] then
        AC.flag(owner, 'blacklisted-model', { model = model }, 3)
        if AC.enforce('blacklisted-model') then CancelEvent() end
        return
    end
    if GetEntityPopulationType(entity) == 7 and owner and owner > 0 then   -- 7 = mission (script-created)
        if not allow(owner, 'spawn', 0.5, 5) then
            AC.flag(owner, 'spawn-rate', { model = model })
            if AC.enforce('spawn-rate') then CancelEvent() end
        end
    end
end)
```
Notes:
- Build `blacklistedModels` with backtick hashes / `joaat('name')`; build explosion/projectile allow-lists from log data (vehicles exploding, fire extinguishers, fireworks and your own scripts produce legitimate events).
- Under `sv_entityLockdown strict` client spawning is already blocked; `entityCreating` then mainly guards population and server-side spawns from other resources.
- `NetworkGetFirstEntityOwner` returns the first owner ID (docs) — treat non-positive values as server/population.
- Don't do heavy work (DB calls, `Wait`) inside these handlers — they run on the sync path; queue logging.
- Known gaps: objects created by **scenarios** (e.g. `WORLD_HUMAN_CONST_DRILL`) replicate without firing `entityCreating`/`entityCreated` (citizenfx/fivem#3675, open), so lockdown/`entityCreating` filters don't see them; consider `block_net_game_event` for scenario abuse and watch object counts. Undisclosed client crash methods are reported regularly (#3722): stay on the Recommended artifact and update promptly.

## 5. Built-in hard blocks
- `block_net_game_event "FIRE_EVENT"` (server.cfg / console) drops a game event type entirely, before scripts see it; `unblock_net_game_event` reverses. Names come from the Net Game Events list (e.g. `GIVE_WEAPON_EVENT`, `REMOVE_WEAPON_EVENT`, `BLOCK_WEAPON_SELECTION`). Use only for event types no resource on your server needs.
- `sv_filterRequestControl`, `sv_entityLockdown`, `sv_stateBagStrictMode`, `sv_enableNetworkedPhoneExplosions false`, `sv_enableNetworkedSounds false` (if unused) — see security.md §9.
- Built-in per-client net event and state bag rate limiters drop flooding clients (`rateLimiter_netEvent*`, `rateLimiter_stateBag*`).

## 6. Server-side state checks
Run one throttled loop (e.g. every 1000–2000 ms) over `GetPlayers()`; skip players in a grace window (spawning, server teleport, bucket change, admin noclip via txAdmin).
```lua
-- server/checks.lua
local last = {}

CreateThread(function()
    while true do
        Wait(1500)
        local now = GetGameTimer()
        for _, id in ipairs(GetPlayers()) do
            local src = tonumber(id)
            local ped = GetPlayerPed(src)
            if ped ~= 0 and not Grace.active(src, now) then
                local pos = GetEntityCoords(ped)
                local prev = last[src]
                if prev and GetVehiclePedIsIn(ped, false) == 0 then
                    local speed = #(pos - prev.pos) / ((now - prev.t) / 1000)
                    if speed > ServerConfig.MaxOnFootSpeed then
                        AC.flag(src, 'speed-onfoot', { speed = speed })
                    end
                end
                last[src] = { pos = pos, t = now }
                if GetPlayerInvincible(src) and not Admin.godAllowed(src) then
                    AC.flag(src, 'invincible', {})
                end
                local weapon = GetSelectedPedWeapon(ped)
                if weapon ~= `WEAPON_UNARMED` and not Inventory.hasWeapon(src, weapon) then
                    AC.flag(src, 'weapon-not-owned', { weapon = weapon }, 2)
                    if AC.enforce('weapon-not-owned') then RemoveWeaponFromPed(ped, weapon) end
                end
            end
        end
    end
end)

AddEventHandler('playerDropped', function() last[source] = nil end)
```
- `Grace.active`, `Admin.godAllowed`, `Inventory.hasWeapon` are your own helpers (e.g. ox_inventory `Search`/`GetItemCount` for the weapon item). Server natives used: `GetPlayerInvincible`, `IsPlayerUsingSuperJump`, `GetSelectedPedWeapon`, `GetEntityHealth`, `GetVehiclePedIsIn`, `GetEntityCoords`, `RemoveWeaponFromPed` (all verified server-side).
- Server sync data lags and can be spoofed by the owning client; treat these as **signals** feeding the score, not proof.
- Vehicles: compare model against what your garage spawned (plate/netId map); flag unknown networked vehicles owned by players when lockdown is relaxed.

## 7. Heartbeats and honeypots
**Heartbeat** (detects the client resource being stopped/blocked):
- Server issues a random per-session token on join (`TriggerClientEvent`), the client resource returns it every 30 s via `TriggerServerEvent('myac:server:hb', token)`; server rotates the token on each beat.
- Missing ≥ 3 beats while the player is otherwise active (`GetPlayerLastMsg(src)` small) → flag; wrong token → flag with higher weight.
- Caveat: a determined executor can replay the logic. It is a cheap signal, not protection.

**Honeypot net events** (near-zero false positives):
- Register net events that **no legitimate client code ever triggers**, named like real-but-unused resources or admin actions (e.g. events of resources you do not run). Any call means a menu is brute-forcing event names.
```lua
-- server/honeypots.lua
for _, name in ipairs(ServerConfig.HoneypotEvents) do
    RegisterNetEvent(name, function()
        local src = source
        AC.flag(src, 'honeypot', { event = name }, 100)
    end)
end
```
- Never place honeypot names in client files of your own resources and never reuse a name a real resource uses. Keep the list server-side only.
- Honeypot *commands* are weaker evidence than honeypot events (staff and players mistype commands): log them, don't auto-ban on them.

## 8. Scoring, evidence and sanctions
- Weighted score per player per session; decay over time. Thresholds: alert staff → kick → temp ban → permanent ban (human-reviewed).
- Auto-ban only for: honeypot events, blacklisted-model spawns under strict lockdown, impossible values (damage overrides far above any weapon), executor signatures you have confirmed.
- Evidence per action: rule, values, coords, timestamp, license, server build; optional screenshot via **screencapture** (successor of screenshot-basic) — store it server-side (Fivemanage etc.).
- Ban identity: license (`GetPlayerIdentifierByType(src, 'license')`) + Discord + hardware tokens (`GetNumPlayerTokens`/`GetPlayerToken`). Tokens are personal data: store hashed, document retention (PLA §4 privacy duty).
- Use txAdmin bans/warns for staff workflow; keep your own ban table in sync if you enforce in `playerConnecting` (deferrals: wait a tick after `deferrals.defer()` before `update`/`done`).
- Never ban on a single desync-prone signal (speed, health) alone.

## 9. What a server-side anticheat cannot see
- Purely local effects: ESP/wallhack, aimbot aim smoothing, local visual mods, menu UIs. (Aimbots show up statistically: headshot ratio, reaction time — needs a lot of data.)
- Local-only entities and effects that never become network events.
- Anything inside the Cfx client: that is Cfx.re's own anticheat and `sv_pureLevel`; report cheat sellers to Cfx.re rather than shipping client-side "detections" that read process memory (privacy and PLA risk).

## 10. Sources
- Server events (entityCreating, ptFxEvent, startProjectileEvent, weaponDamageEvent, removeAllWeaponsEvent): https://docs.fivem.net/docs/scripting-reference/events/server-events/
- Intercepting game events (explosionEvent, CancelEvent): https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/
- Net game events list: https://docs.fivem.net/docs/game-references/net-game-events/
- `block_net_game_event`, lockdown, request control, pure level: https://docs.fivem.net/docs/server-manual/server-commands/ · https://github.com/citizenfx/fivem-docs/blob/master/content/docs/server-manual/server-commands.md
- Game-event structs and dispatcher (field names, sender as string): https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/state/ServerGameState.cpp
- Secure your events / CnL kick convars: https://docs.fivem.net/docs/developers/server-security/
- Native reference (verified with `scripts/natives.py show`): https://docs.fivem.net/natives/
