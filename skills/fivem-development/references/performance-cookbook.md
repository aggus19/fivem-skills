# Performance cookbook: before/after recipes (CfxLua 5.4)

Baseline: CfxLua 5.4 (LuaGLM), ox_lib 3.40, FXServer Legacy 35245+ — verified 2026-10-07. Natives checked with `scripts/natives.py show`; ox_lib functions checked in the ox_lib source. Theory and numbers: [performance.md](performance.md); server scale: [performance-server-scaling.md](performance-server-scaling.md).

Every "after" assumes `shared_script '@ox_lib/init.lua'` in the manifest when it uses `lib`/`cache`. Measure each change with `resmon 1` (client) or `profiler record` (both sides) and report before/after numbers.

## Contents
1. Marker + key loop → `lib.points`
2. Many points without ox_lib → one thread, dynamic sleep
3. Per-frame ped/vehicle lookups → `cache` + `lib.onCache`
4. Key polling → `lib.addKeybind` / `RegisterKeyMapping`
5. Per-frame-only natives → one thread, only while needed
6. `GetGamePool` every frame → throttled, spread scan
7. Synchronous raycast → async (`lib.raycast`)
8. Allocation in hot loops → reuse tables, `table.concat`
9. NUI HUD every frame → on-change, throttled
10. Server broadcast → targeted, packed once, latent for big data
11. State bags: nested rewrite → granular keys, change threshold
12. DB write per change → dirty flag + batched flush
13. Server player polling → event-driven registry
14. Leaking entities → tracked + cleaned up
15. Memory and timing probes
16. JS `setTick` → interval

## 1. Marker + key loop → `lib.points`
Before (client) — ~0.10–0.30 ms always, even across the map:
```lua
CreateThread(function()
    while true do
        Wait(0)
        local coords = GetEntityCoords(PlayerPedId())
        for _, shop in pairs(Config.Shops) do
            local dist = GetDistanceBetweenCoords(coords.x, coords.y, coords.z, shop.coords.x, shop.coords.y, shop.coords.z, true)
            if dist < 20.0 then
                DrawMarker(2, shop.coords.x, shop.coords.y, shop.coords.z, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.3, 255, 255, 255, 150, false, true, 2, false, nil, nil, false)
                if dist < 1.5 and IsControlJustReleased(0, 38) then
                    openShop(shop)
                end
            end
        end
    end
end)
```
After (client) — 0.00 ms away from shops; per-frame work only inside 15 m:
```lua
local textShown = false

for i = 1, #Config.Shops do
    local shop = Config.Shops[i]
    lib.points.new({
        coords = shop.coords,
        distance = 15.0,
        shop = shop,
        onExit = function()
            if textShown then lib.hideTextUI(); textShown = false end
        end,
        nearby = function(self)                     -- every frame, only while inside 15 m
            local c = self.coords
            DrawMarker(2, c.x, c.y, c.z, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.3, 255, 255, 255, 150, false, true, 2, false, nil, nil, false)
            local close = self.currentDistance < 1.5
            if close ~= textShown then
                textShown = close
                if close then lib.showTextUI('[E] Shop') else lib.hideTextUI() end
            end
            if close and IsControlJustReleased(0, 38) then
                openShop(self.shop)
            end
        end,
    })
end
```
Even better when the server runs ox_target: no marker, no per-frame code at all (`exports.ox_target:addSphereZone`, see [ox-inventory-target.md](ox-inventory-target.md)).

## 2. Many points without ox_lib → one thread, dynamic sleep
```lua
local DrawMarker, GetEntityCoords, PlayerPedId = DrawMarker, GetEntityCoords, PlayerPedId
local points = Config.Points            -- array of { coords = vec3(...) }

CreateThread(function()
    while true do
        local sleep = 1500
        local coords = GetEntityCoords(PlayerPedId())
        for i = 1, #points do
            local p = points[i].coords
            local dist = #(coords - p)
            if dist < 15.0 then
                sleep = 0
                DrawMarker(2, p.x, p.y, p.z, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.3, 255, 255, 255, 150, false, true, 2, false, nil, nil, false)
            elseif dist < 60.0 and sleep > 500 then
                sleep = 500
            end
        end
        Wait(sleep)
    end
end)
```
For hundreds of points, bucket them by grid cell at start and only test the player's cell and neighbours (this is what `lib.points` does via `lib.grid`).

## 3. Per-frame ped/vehicle lookups → `cache` + `lib.onCache`
Before:
```lua
CreateThread(function()
    while true do
        Wait(0)
        local ped = PlayerPedId()
        if IsPedInAnyVehicle(ped, false) then
            local veh = GetVehiclePedIsIn(ped, false)
            -- speedometer logic...
        end
    end
end)
```
After — no thread at all while on foot:
```lua
local speedoToken = 0                     -- bumping it stops any running loop

local function stopSpeedo()
    speedoToken += 1
end

local function startSpeedo(vehicle)
    speedoToken += 1
    local token = speedoToken
    CreateThread(function()
        while token == speedoToken and DoesEntityExist(vehicle) do
            local kmh = math.floor(GetEntitySpeed(vehicle) * 3.6)
            updateSpeedo(kmh)              -- see recipe 9: sends to NUI only on change
            Wait(200)
        end
    end)
end

lib.onCache('vehicle', function(vehicle)
    if vehicle then startSpeedo(vehicle) else stopSpeedo() end
end)

if cache.vehicle then startSpeedo(cache.vehicle) end   -- resource restarted while driving
```
Note: `lib.onCache` handlers receive the new value as the first argument; inside the handler `cache.vehicle` still holds the **old** value (ox_lib triggers the event before assigning). `cache` refreshes every 100 ms.

## 4. Key polling → `lib.addKeybind` / `RegisterKeyMapping`
Before: `Wait(0)` loop with `IsControlJustPressed(0, 166)` in every resource.
After (client, no thread; user can rebind in Settings > Key Bindings > FiveM):
```lua
lib.addKeybind({
    name = 'myres_menu',
    description = 'Open my menu',
    defaultKey = 'F5',
    onPressed = function() openMenu() end,
})
```
Without ox_lib:
```lua
RegisterCommand('+myres_menu', function() openMenu() end, false)
RegisterCommand('-myres_menu', function() end, false)
RegisterKeyMapping('+myres_menu', 'Open my menu', 'keyboard', 'F5')
```

## 5. Per-frame-only natives → one thread, only while needed
Before: a permanent `Wait(0)` loop disabling attack controls "just in case".
After — runs only while the menu is open:
```lua
local menuOpen = false

local function setMenuOpen(state)
    if state == menuOpen then return end
    menuOpen = state
    if not state then return end
    CreateThread(function()
        while menuOpen do
            DisableControlAction(0, 24, true)   -- attack
            DisableControlAction(0, 25, true)   -- aim
            HideHudComponentThisFrame(19)       -- weapon wheel
            Wait(0)
        end
    end)
end
```
ox_lib alternative: `lib.disableControls:Add(24, 25)` then call `lib.disableControls()` inside your existing per-frame loop; `:Remove(24, 25)` when done.
Density multipliers: put all `Set*DensityMultiplierThisFrame` calls in **one** server-wide resource, or prefer `onesync_population` / `SetPedPopulationBudget` (set once).

## 6. `GetGamePool` every frame → throttled, spread scan
Before: `for _, veh in ipairs(GetGamePool('CVehicle')) do ... end` inside `Wait(0)`.
After:
```lua
local nearbyVehicles = {}          -- reused, read by other code
local SCAN_RADIUS = 50.0

CreateThread(function()
    while true do
        local pool = GetGamePool('CVehicle')
        local origin = GetEntityCoords(cache.ped)
        local n = 0
        table.wipe(nearbyVehicles)                 -- CfxLua: reuse the table, no new allocation
        for i = 1, #pool do
            local veh = pool[i]
            if DoesEntityExist(veh) and #(GetEntityCoords(veh) - origin) < SCAN_RADIUS then
                n += 1
                nearbyVehicles[n] = veh
            end
            if i % 64 == 0 then Wait(0) end        -- spread big pools over several frames
        end
        Wait(1500)
    end
end)
```
ox_lib has `lib.getNearbyVehicles(coords, maxDistance, includePlayerVehicle)` / `lib.getClosestVehicle(...)` — still a pool scan, so also call them on a timer, not per frame.

## 7. Synchronous raycast → async
Before: `StartExpensiveSynchronousShapeTestLosProbe(...)` every frame (blocks the game thread).
After (must run inside a thread; it yields until the result is ready):
```lua
CreateThread(function()
    while aiming do
        local from = GetEntityCoords(cache.ped)
        local to = from + GetEntityForwardVector(cache.ped) * 10.0
        local hit, entity, endCoords = lib.raycast.fromCoords(from, to, 511, cache.ped)
        if hit then handleHit(entity, endCoords) end
        Wait(100)                                    -- 10 Hz is plenty for targeting UI
    end
end)
```
`lib.raycast.fromCoords` uses `StartShapeTestLosProbe` + `GetShapeTestResultIncludingMaterial` with `Wait(0)` polling.

## 8. Allocation in hot loops → reuse tables, `table.concat`
Before:
```lua
CreateThread(function()
    while true do
        Wait(0)
        local data = { health = GetEntityHealth(cache.ped), armour = GetPedArmour(cache.ped) }  -- new table per frame
        local label = 'HP: ' .. data.health .. ' / AR: ' .. data.armour                      -- new strings per frame
        drawLabel(label)
    end
end)
```
After:
```lua
local data = { health = 0, armour = 0 }      -- allocated once
local parts = {}
local lastHealth, lastArmour, label = -1, -1, ''

CreateThread(function()
    while true do
        data.health = GetEntityHealth(cache.ped)
        data.armour = GetPedArmour(cache.ped)
        if data.health ~= lastHealth or data.armour ~= lastArmour then
            lastHealth, lastArmour = data.health, data.armour
            parts[1], parts[2], parts[3], parts[4] = 'HP: ', data.health, ' / AR: ', data.armour
            label = table.concat(parts)          -- rebuilt only on change
        end
        drawLabel(label)                          -- per-frame draw call
        Wait(0)
    end
end)
```
CfxLua table helpers (from LuaGLM, enabled in FiveM): `table.wipe(t)`/`table.clear(t)`, `table.create(narr, nhash)`/`table.new`, `table.clone(t)`.

## 9. NUI HUD every frame → on-change, throttled
Before: `SendNUIMessage({ action = 'hud', health = ..., armour = ..., speed = ... })` inside `Wait(0)`.
After (client):
```lua
local last = {}
local payload = { action = 'hud' }

local function pushHud(health, armour, speed)
    if health == last.health and armour == last.armour and speed == last.speed then return end
    last.health, last.armour, last.speed = health, armour, speed
    payload.health, payload.armour, payload.speed = health, armour, speed
    SendNUIMessage(payload)
end

CreateThread(function()
    while true do
        local speed = cache.vehicle and math.floor(GetEntitySpeed(cache.vehicle) * 3.6) or 0
        pushHud(GetEntityHealth(cache.ped), GetPedArmour(cache.ped), speed)
        Wait(cache.vehicle and 150 or 500)        -- ~6.6 Hz driving, 2 Hz on foot
    end
end)
```
In the UI (now JIT-less CEF): update only changed DOM nodes; avoid re-rendering the whole React tree per message (memoize components, keep state flat).

## 10. Server broadcast → targeted, packed once, latent for big data
Before (server): `TriggerClientEvent('myres:client:fx', -1, coords)` for an explosion everyone everywhere receives.
After — only players within 150 m, payload packed once:
```lua
local function playersNear(coords, radius)
    local list, n = {}, 0
    for _, id in ipairs(GetPlayers()) do
        local ped = GetPlayerPed(id)
        if ped ~= 0 and #(GetEntityCoords(ped) - coords) < radius then
            n += 1
            list[n] = tonumber(id)
        end
    end
    return list
end

local targets = playersNear(coords, 150.0)
if #targets > 0 then
    lib.triggerClientEvent('myres:client:fx', targets, coords)   -- msgpacks args once for all targets
end
```
Large data (config dumps, logs, images, > a few KB) — send latent, to the one player who asked:
```lua
RegisterNetEvent('myres:server:requestCatalog', function()
    local src = source
    TriggerLatentClientEvent('myres:client:catalog', src, 50000, Catalog)  -- 50 KB/s for this client
end)
```
Static data that every client needs: ship it in a shared file (`shared_script 'data/catalog.lua'`) instead of sending it at all.

## 11. State bags: nested rewrite → granular keys, change threshold
Before (server, 10 Hz):
```lua
Entity(vehicle).state:set('vehicleData', { fuel = fuel, engine = engine, doors = doors }, true)  -- whole table replicated each time
```
After:
```lua
local lastFuel = {}

local function setFuel(vehicle, fuel)
    local rounded = math.floor(fuel + 0.5)
    if lastFuel[vehicle] == rounded then return end      -- replicate only meaningful changes
    lastFuel[vehicle] = rounded
    Entity(vehicle).state:set('fuel', rounded, true)
end

-- door 3 opened: one small key instead of the whole table
Entity(vehicle).state:set('door:3', true, true)
```
Client reacting without polling:
```lua
AddStateBagChangeHandler('fuel', nil, function(bagName, key, value)
    local entity = GetEntityFromStateBagName(bagName)
    if entity == 0 or entity ~= cache.vehicle then return end
    updateFuelGauge(value)
end)
```
Clear `lastFuel[vehicle]` when the vehicle is deleted (recipe 14) or it leaks.

## 12. DB write per change → dirty flag + batched flush
Before (server): `MySQL.update.await('UPDATE users SET money = ? WHERE identifier = ?', ...)` on every money change.
After:
```lua
local dirty = {}            -- [identifier] = money

local function setMoney(identifier, amount)
    dirty[identifier] = amount                -- in-memory value is authoritative; DB catches up
end

local function flush()
    if next(dirty) == nil then return end
    local queries, n = {}, 0
    for identifier, money in pairs(dirty) do
        n += 1
        queries[n] = { query = 'UPDATE users SET money = ? WHERE identifier = ?', values = { money, identifier } }
    end
    dirty = {}
    MySQL.transaction(queries, function(ok)
        if not ok then print('^1[myres] money flush failed^7') end
    end)
end

lib.cron.new('*/5 * * * *', flush)            -- every 5 minutes (or a CreateThread + Wait(300000))
AddEventHandler('txAdmin:events:serverShuttingDown', flush)
AddEventHandler('onResourceStop', function(res) if res == cache.resource then flush() end end)
```
Also flush a single player on `playerDropped`. Frameworks (Qbox/ESX/QBCore) already batch player saves — don't add a second per-change save on top. Indexes, pool size, query plans: `database-optimization.md`.

## 13. Server player polling → event-driven registry
Before: every second, loop `GetPlayers()` and query each player's job from the framework.
After:
```lua
local onDuty = {}                     -- [source] = true

RegisterNetEvent('myres:server:setDuty', function(state)
    local src = source
    if type(state) ~= 'boolean' then return end
    if not isPolice(src) then return end           -- your framework check
    onDuty[src] = state or nil
end)

AddEventHandler('playerDropped', function()
    onDuty[source] = nil                            -- avoid a leak keyed by source
end)

local function getOnDutyPolice()
    local list, n = {}, 0
    for src in pairs(onDuty) do n += 1; list[n] = src end
    return list
end
```

## 14. Leaking entities → tracked + cleaned up
```lua
local spawned = {}                    -- [entity] = owner source

local function spawnJobVehicle(src, model, coords, heading)
    local veh = CreateVehicleServerSetter(model, 'automobile', coords.x, coords.y, coords.z, heading)
    if veh == 0 then return end
    spawned[veh] = src
    return veh
end

local function despawn(veh)
    if DoesEntityExist(veh) then DeleteEntity(veh) end
    spawned[veh] = nil
end

AddEventHandler('playerDropped', function()
    local src = source
    for veh, owner in pairs(spawned) do
        if owner == src then despawn(veh) end
    end
end)

AddEventHandler('onResourceStop', function(res)
    if res ~= GetCurrentResourceName() then return end
    for veh in pairs(spawned) do
        if DoesEntityExist(veh) then DeleteEntity(veh) end
    end
end)
```
Client side: delete blips (`RemoveBlip`), cameras, DUIs, `lib.points`/`zones` (`point:remove()`), and `RemoveEventHandler`/`RemoveStateBagChangeHandler` for handlers created dynamically.

## 15. Memory and timing probes
Memory growth log (either side; temporary, remove after diagnosing):
```lua
CreateThread(function()
    local start = collectgarbage('count')
    while true do
        Wait(60000)
        print(('[%s] Lua heap: %.1f KB (Δ %.1f KB since start)'):format(GetCurrentResourceName(), collectgarbage('count'), collectgarbage('count') - start))
    end
end)
```
Timing a block — server (`os` exists only server-side):
```lua
local t0 = os.nanotime()
rebuildIndex()
print(('rebuildIndex took %.3f ms'):format((os.nanotime() - t0) / 1e6))
```
Client (no `os` library; ms resolution — use `profiler` for finer detail):
```lua
local t0 = GetGameTimer()
for _ = 1, 1000 do doWork() end
print(('1000x doWork: %d ms'):format(GetGameTimer() - t0))
```

## 16. JS `setTick` → interval
Before (client JS): `setTick(() => { if (Date.now() - last > 1000) { last = Date.now(); check(); } });` — a tick every frame to do work once a second.
After:
```js
const interval = setInterval(check, 1000);
// later, when no longer needed:
clearInterval(interval);
```
Use `setTick` only for real per-frame natives, and `clearTick(handle)` as soon as they are no longer needed.

## Sources
- Natives verified via `scripts/natives.py show` (DrawMarker, IsControlJustReleased, GetGamePool, DoesEntityExist, GetEntitySpeed, DisableControlAction, HideHudComponentThisFrame, AddStateBagChangeHandler, GetEntityFromStateBagName, CreateVehicleServerSetter, DeleteEntity, GetPlayerPed, GetEntityCoords, RegisterKeyMapping, StartShapeTestLosProbe) — https://docs.fivem.net/natives/
- ox_lib source (points, cache, onCache, addKeybind, disableControls, raycast, triggerClientEvent, getNearbyVehicles, cron): https://github.com/overextended/ox_lib
- CfxLua table extensions: https://github.com/citizenfx/lua (branch `luaglm-548`, `ltablib.c`); `os` server-only: https://github.com/citizenfx/fivem/blob/master/code/components/citizen-scripting-lua/src/LuaScriptRuntime.cpp
- Latent events: https://docs.fivem.net/docs/scripting-manual/working-with-events/triggering-events/
- State bags: https://docs.fivem.net/docs/scripting-manual/networking/state-bags/
- oxmysql transactions: https://overextended.dev/docs/oxmysql
