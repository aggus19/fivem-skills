# ox_lib — world: points, zones, proximity, raycast, streaming, animation, markers, DUI, scaleform, vehicle properties

Baseline: ox_lib v3.40.0 — verified 2026-10-07

Part of the ox_lib reference. Entry point and index: [ox-lib.md](ox-lib.md).

## Contents
1. `lib.points` (client)
2. `lib.zones` (shared: sphere, box, poly)
3. `lib.grid` (shared spatial index)
4. Closest / nearby helpers
5. `lib.raycast` (client)
6. Streaming helpers (`lib.requestX`)
7. `lib.playAnim`, `lib.disableControls`
8. `lib.marker`, `lib.dui`, `lib.scaleform`
9. Vehicle properties
10. `lib.getRelativeCoords`
11. Performance notes and common mistakes
12. Sources

---

## 1. lib.points (client)
```lua
local point = lib.points.new({
    coords = vec3(25.7, -1347.3, 29.5),   -- vector3, vector4 or {x,y,z}
    distance = 3.0,                       -- radius
    shopId = 'shop_1',                    -- any extra fields are kept on `self`
    onEnter = function(self) lib.showTextUI('[E] Shop') end,
    onExit = function(self) lib.hideTextUI() end,
    nearby = function(self)               -- every frame while inside
        if self.isClosest and IsControlJustReleased(0, 38) then openShop(self.shopId) end
    end,
})
point:remove()
```
- The legacy signature `lib.points.new(coords, distance, data?)` still works.
- Points live in `lib.grid`. A **300 ms** thread checks the nearby grid cells, updates `self.currentDistance` and `self.isClosest`, and fires `onEnter`/`onExit`. The per-frame `nearby` callbacks run in one `SetInterval(…, 0)` that only exists while at least one point is in range. When no point is near, the cost is close to zero.
- Helpers: `lib.points.getAllPoints()`, `lib.points.getNearbyPoints()`, `lib.points.getClosestPoint()` (`lib.points.closest` is a deprecated alias).
- While the module is loaded it fills `cache.coords`.

## 2. lib.zones (shared)
```lua
local sphere = lib.zones.sphere({ coords = vec3(441.0, -982.0, 30.7), radius = 2.0, debug = false,
    onEnter = function(self) end, onExit = function(self) end, inside = function(self) end })

local box = lib.zones.box({ coords = vec3(0.0, 0.0, 70.0), size = vec3(4.0, 6.0, 3.0), rotation = 45.0,
    debug = true, debugColour = { r = 255, g = 42, b = 24, a = 100 }, onEnter = function(self) print('in', self.name) end, name = 'garage' })

local poly = lib.zones.poly({ points = { vec3(10.0, 10.0, 30.0), vec3(20.0, 10.0, 30.0), vec3(20.0, 25.0, 30.0), vec3(10.0, 25.0, 30.0) },
    thickness = 4.0, onExit = function(self) end })

box:contains(GetEntityCoords(cache.ped))   -- manual test (also works on the server)
box:setDebug(true, { r = 0, g = 255, b = 0, a = 80 })   -- client only
box:remove()
```
| Shape | Required | Defaults |
|---|---|---|
| `sphere` | `coords` | `radius = 2` |
| `box` | `coords` | `size = vec3(4, 4, 4)` (the module stores half-size, so the default full size is 4); `rotation = 0` (heading in degrees, or a vector/quaternion) |
| `poly` | `points` (≥3) | `thickness = 4`. Non-planar points are flattened to the most common Z. Concave polygons have been supported since v3.33. |

- Callbacks receive the zone table (`self`) with your extra fields. `inside` runs every frame while the player is inside.
- A 300 ms thread on the **client** handles enter and exit. Exits fire before enters, and both are sorted by distance. `inside` and `debug` drawing share one `SetInterval(…, 0)` that only runs while needed.
- **Server-side zones** use the same constructors and `contains(coords)`, but there is no player polling, `onEnter`/`onExit`/`inside` never fire, and `debug` is ignored. Use them for server checks, for example `if not zone:contains(GetEntityCoords(GetPlayerPed(src))) then return end`.
- Helpers: `lib.zones.getAllZones()`, `lib.zones.getCurrentZones()` (client: zones you are inside that have `inside` or `debug`), `lib.zones.getNearbyZones()`.
- Zone ids are `#Zones + 1`. Ids can repeat after removals, so store the zone object instead of the id.
- `/zone box|sphere|poly` (ACE `command.zone`) is an in-game creator that writes `ox_lib/created_zones.lua` (see [ox-lib-ui.md](ox-lib-ui.md#11-clipboard-nui-focus-settings-zone-creator)).
- The JS zones API is different (`Zone.Sphere`, `Zone.Cuboid`, `Zone.Prism`; it is experimental). See [ox-lib-js.md](ox-lib-js.md#5-zones-experimental).

## 3. lib.grid (shared)
This is the spatial hash that points and zones use. The map from (-3700,-4400) to (4500,8000) is split into 34×50 cells.
```lua
lib.grid.addEntry(entry)            -- entry = { coords = vec3, radius? | length? & width?, ... }
lib.grid.removeEntry(entry)
lib.grid.getCellPosition(coords)    -- cellX, cellY
lib.grid.getCell(coords)            -- entries in that cell
lib.grid.getNearbyEntries(coords, filter?)  -- entries in the surrounding cells (cached per cell), optional filter(entry)
```
Use it for your own large sets of locations (thousands of interaction spots) instead of looping over all of them.

## 4. Closest / nearby helpers
| Function | Side | Returns | Default `maxDistance` |
|---|---|---|---|
| `lib.getClosestPlayer(coords, maxDistance?, includePlayer?)` | client | `playerId` (**client player index**, not server id), `ped`, `coords`, `vehicle` | 2.0 |
| `lib.getClosestPlayer(coords, maxDistance?, ignorePlayerId?)` | server | server id, ped, coords | 2.0 |
| `lib.getNearbyPlayers(coords, maxDistance?, includePlayer?)` | client | `{ id, ped, coords }[]` (id = client player index) | 2.0 |
| `lib.getNearbyPlayers(coords, maxDistance?)` | server | `{ id, ped, coords }[]` (id = server id) | 2.0 |
| `lib.getClosestVehicle(coords, maxDistance?, includePlayerVehicle?)` | shared | vehicle, coords | 2.0 |
| `lib.getNearbyVehicles(coords, maxDistance?, includePlayerVehicle?)` | shared | `{ vehicle, coords }[]` | 2.0 |
| `lib.getClosestPed(coords, maxDistance?)` | shared | ped, coords (players excluded) | 2.0 |
| `lib.getNearbyPeds(coords, maxDistance?)` | shared | `{ ped, coords }[]` | 2.0 |
| `lib.getClosestObject(coords, maxDistance?)` | shared | object, coords | 2.0 |
| `lib.getNearbyObjects(coords, maxDistance?)` | shared | `{ object, coords }[]` | 2.0 |

```lua
-- client: convert to server id before sending
local playerId, ped = lib.getClosestPlayer(GetEntityCoords(cache.ped), 3.0)
if playerId then TriggerServerEvent('myres:server:search', GetPlayerServerId(playerId)) end
-- server: re-check the distance yourself, never trust the client's pick
```
- These loop over `GetGamePool` (and `GetActivePlayers`) on every call. That is fine for one interaction, but don't call them every frame. The server can only see entities that exist on the server (OneSync).
- The client `getClosestPlayer` uses a bone position for players in vehicles (since v3.33). It skips yourself unless `includePlayer` is set.

## 5. lib.raycast (client)
```lua
local hit, entity, endCoords, surfaceNormal, materialHash = lib.raycast.fromCamera(flags?, ignore?, distance?)
local hit, entity, endCoords, surfaceNormal, materialHash = lib.raycast.fromCoords(fromVec3, toVec3, flags?, ignore?)
```
- `flags` defaults to **511** (everything). Bits: 1 mover, 2 vehicle, 4 ped, 8 ragdoll, 16 object, 32 pickup, 64 glass, 128 river, 256 foliage.
- `ignore` defaults to **4** (no-collision). 1 = glass, 2 = see-through, 7 = all.
- `distance` defaults to 10.
- It uses `StartShapeTestLosProbe` and polls `GetShapeTestResultIncludingMaterial` with `Wait(0)`, so it **yields**. Your own ped is always excluded.
- `lib.raycast.cam` is a deprecated alias of `fromCamera`.

## 6. Streaming helpers (client)
All of them yield until the asset loads, return the asset, and **throw** on timeout or invalid input. The real default timeout is **30000 ms** (`lib.streamingRequest`), even though the inline comments say 10000.
```lua
local hash = lib.requestModel(model, timeout?)              -- string or hash; returns the hash; errors if not IsModelValid/IsModelInCdimage
lib.requestAnimDict(dict, timeout?)                         -- errors if not DoesAnimDictExist
lib.requestAnimSet(clipset, timeout?)
lib.requestNamedPtfxAsset(name, timeout?)
lib.requestStreamedTextureDict(txd, timeout?)
lib.requestWeaponAsset(weapon, timeout?, weaponResourceFlags = 31, extraComponentFlags = 0)
lib.requestAudioBank(bank, timeout?)                        -- RequestScriptAudioBank loop (30 s)
local sf = lib.requestScaleformMovie(name, timeout?)        -- returns the scaleform handle; default timeout 1000 ms
```
Release what you load: `SetModelAsNoLongerNeeded(hash)`, `RemoveAnimDict(dict)`, `RemoveAnimSet`, `RemoveNamedPtfxAsset`, `SetStreamedTextureDictAsNoLongerNeeded`, `ReleaseNamedScriptAudioBank`.
```lua
local model = lib.requestModel(`prop_box_wood02a`)
local obj = CreateObject(model, coords.x, coords.y, coords.z, true, true, false)
SetModelAsNoLongerNeeded(model)
```

## 7. lib.playAnim and lib.disableControls (client)
```lua
lib.playAnim(ped, dict, clip, blendIn = 8.0, blendOut = -8.0, duration = -1, flags = 0, startPhase = 0.0, phaseControlled = false, controlFlags = 0, overrideCloneUpdate = false)
```
It loads the dictionary, calls `TaskPlayAnim`, and then `RemoveAnimDict`. The annotations list every animation flag (1 loop, 16 upper body, 32 secondary, …).

`lib.disableControls` is a reference-counted set of controls:
```lua
lib.disableControls:Add(24, 25, 140)    -- or a table
CreateThread(function()
    while busy do
        lib.disableControls()           -- disables every stored control this frame
        Wait(0)
    end
    lib.disableControls:Remove(24, 25, 140)
end)
-- lib.disableControls:Clear(24) removes regardless of count
```

## 8. Markers, DUI, scaleform (client)
**Marker**
```lua
local marker = lib.marker.new({
    type = 'HorizontalCircleFat',          -- name from the MarkerType enum, or a number (default 0)
    coords = vec3(441.0, -982.0, 29.7),
    width = 1.5, height = 0.5,             -- defaults 2.0 / 1.0
    color = { r = 0, g = 150, b = 255, a = 120 },
    rotation = vec3(0, 0, 0), direction = vec3(0, 0, 0),
    bobUpAndDown = false, faceCamera = false, rotate = false, invert = false,
    -- textureDict, textureName optional
})
-- draw every frame only while near (e.g. in a point's `nearby`)
marker:draw()
```
**DUI** (a browser rendered to a texture)
```lua
local dui = lib.dui:new({ url = 'https://example.com', width = 1280, height = 720, debug = false })
-- dui.dictName / dui.txtName are runtime texture names, usable with AddReplaceTexture, DrawSprite, etc.
dui:setUrl(url); dui:sendMessage({ action = 'update' })  -- JSON-encoded SendDuiMessage
dui:sendMouseMove(x, y); dui:sendMouseDown('left'); dui:sendMouseUp('left'); dui:sendMouseWheel(dx, dy)
dui:remove()   -- also done automatically for all DUIs when your resource stops
```
**Scaleform**
```lua
local sf = lib.scaleform:new({ name = 'MP_BIG_MESSAGE_FREEMODE', fullScreen = true })   -- or lib.scaleform:new('NAME')
sf:callMethod('SHOW_SHARD_WASTED_MP_MESSAGE', { 'WASTED', 'You died' })   -- method/args depend on the movie (UNVERIFIED example)
sf:startDrawing()        -- draws every frame in its own thread
SetTimeout(5000, function() sf:stopDrawing(); sf:dispose() end)
```
Args are converted by Lua type: string, integer (`math.type`), float or boolean. Write `5.0`, not `5`, when the movie expects a float. Other methods: `callMethod(name, args, returnType)` where `returnType` is `'boolean'`, `'integer'` or `'string'` and the call waits for the return value; `setFullScreen(bool)`; `setProperties(x, y, w, h)`; `setRenderTarget(name, model)`; `isDrawing()`; `draw()` (call it yourself every frame instead of `startDrawing`).

## 9. Vehicle properties
```lua
local props = lib.getVehicleProperties(vehicle)          -- client; nil if the entity doesn't exist
local isOwner = lib.setVehicleProperties(vehicle, props, fixVehicle?)  -- client; errors if the entity doesn't exist
lib.setVehicleProperties(vehicle, props)                 -- server: via the state bag (see ox-lib-core.md section 10)
```
`VehicleProperties` keys, all optional on set:
- Identity: `model`, `plate`, `plateIndex`.
- Condition: `bodyHealth`, `engineHealth`, `tankHealth`, `fuelLevel` (rounded), `oilLevel`, `dirtLevel`, `lockState`.
- Paint: `paintType1/2`, `color1`, `color2` (an index or `{ r, g, b }` for custom), `pearlescentColor`, `interiorColor`, `dashboardColor`, `wheelColor`.
- Wheels: `wheels` (type), `wheelWidth`, `wheelSize`, `modFrontWheels`, `modBackWheels`, `modCustomTiresF/R`, `bulletProofTyres`, `driftTyres` (game build ≥ 2372).
- Lights: `windowTint`, `xenonColor`, `modXenon`, `neonEnabled` (array of 4 booleans), `neonColor` `{ r, g, b }`, `tyreSmokeColor`.
- Every `modX` slot: Spoilers, FrontBumper, RearBumper, SideSkirt, Exhaust, Frame, Grille, Hood, Fender, RightFender, Roof, Engine, Brakes, Transmission, Horns, Suspension, Armor, Nitrous, Turbo, Subwoofer, SmokeEnabled, Hydraulics, PlateHolder, VanityPlate, TrimA, Ornaments, Dashboard, Dial, DoorSpeaker, Seats, SteeringWheel, ShifterLeavers, APlate, Speakers, Trunk, Hydrolic, EngineBlock, AirFilter, Struts, ArchCover, Aerials, TrimB, Tank, Windows, DoorR, Livery, RoofLivery, Lightbar. Also `livery`.
- Extras: `{ [id] = 0 }` means the extra is **on**, `1` means **off**.
- Damage: `windows` (indexes of broken windows), `doors` (broken-off doors), `tyres` (`{ [i] = 1 }` burst, `2` fully burst, `3` wheel broken off since v3.39).

Notes:
- `lockState` is only applied when `setr ox:setLockState true` (v3.34+, default off).
- `setVehicleProperties` returns `true` if the vehicle isn't networked or you are its network owner. Several natives only stick when the owner applies them, which is why the server path uses the state bag.
- Pass `fixVehicle = true` when you change extras (the game damages the body when toggling them).
- Store props as JSON in your DB. Never accept a full props table from a client for a vehicle the player claims to own without validating it (plate, model, allowed mods) on the server.

## 10. lib.getRelativeCoords (shared, v3.29+)
```lua
lib.getRelativeCoords(coords: vector3, heading: number, offset: vector3) -- vector3
lib.getRelativeCoords(coords: vector4, offset: vector3)                -- vector4 (uses .w as heading)
lib.getRelativeCoords(coords: vector3, rotation: vector3, offset: vector3) -- full pitch/roll/yaw (v3.30)
local front = lib.getRelativeCoords(GetEntityCoords(cache.ped), GetEntityHeading(cache.ped), vec3(0.0, 1.0, 0.0))
```
This is pure math, so it works on the server, which has no `GetOffsetFromEntityInWorldCoords`.

## 11. Performance notes and common mistakes
- Prefer `lib.points`, `lib.zones` or ox_target over `while true do Wait(0) … #(a - b) … end`. Points and zones poll every 300 ms and only tick every frame while you are inside or near one.
- Keep `nearby` and `inside` callbacks cheap, because they run every frame. Do the heavy work in `onEnter`.
- Turn `debug = true` off before shipping. It draws polygons every frame while you are in range.
- Don't create zones or points inside loops or per-frame callbacks without removing the old ones.
- Server zones never fire callbacks. Use `zone:contains(coords)`.
- `getClosestPlayer` on the client returns the **client player index**. Convert it with `GetPlayerServerId` before you send it to the server.
- Streaming helpers throw on timeout. Wrap them in `pcall` if the asset is optional, and always release what you request.

## 12. Sources
- https://github.com/overextended/ox_lib/blob/v3.40.0/imports/points/client.lua
- https://github.com/overextended/ox_lib/blob/v3.40.0/imports/zones/shared.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/imports/grid/shared.lua
- https://github.com/overextended/ox_lib/tree/v3.40.0/imports (getClosestPlayer, getClosestVehicle, getClosestPed, getClosestObject, getNearbyPlayers, getNearbyVehicles, getNearbyPeds, getNearbyObjects, raycast, streamingRequest, requestModel, requestAnimDict, requestAnimSet, requestNamedPtfxAsset, requestStreamedTextureDict, requestWeaponAsset, requestAudioBank, requestScaleformMovie, playAnim, disableControls, marker, dui, scaleform, getRelativeCoords)
- https://github.com/overextended/ox_lib/blob/v3.40.0/resource/vehicleProperties/client.lua
- Docs: https://overextended.dev/docs/ox_lib/Zones/Shared, plus the Points, Raycast, Streaming, Marker, Dui, Scaleform and VehicleProperties pages (source: https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_lib)
- Natives checked with `scripts/natives.py`: GetGamePool, StartShapeTestLosProbe, GetShapeTestResultIncludingMaterial, IsControlJustReleased, SetModelAsNoLongerNeeded, RemoveAnimDict, DrawMarker, CreateDui, GetDuiHandle, SendDuiMessage, CreateObject, GetPlayerServerId, GetEntityCoords, GetEntityHeading, IsModelInCdimage, DoesAnimDictExist
