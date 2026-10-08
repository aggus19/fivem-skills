# ox_lib — core: callbacks, commands, keybinds, ACL, events, hooks, entity state

Baseline: ox_lib v3.40.0 — verified 2026-10-07

Part of the ox_lib reference. Entry point and index: [ox-lib.md](ox-lib.md).

## Contents
1. `cache` and `lib.onCache`
2. Callbacks (`lib.callback`)
3. `lib.addCommand` (server)
4. `lib.addKeybind` (client)
5. ACL: `lib.addAce` / `removeAce` / `addPrincipal` / `removePrincipal`
6. `lib.triggerClientEvent` (server, multi-target)
7. Hooks: `lib.hook` pipelines and `lib.registerHook`
8. Game entity classes: `lib.ped` / `lib.player` / `lib.prop` / `lib.vehicle`
9. Entity state replication modes and strict state bags
10. Server vehicle properties via state bag
11. Common mistakes
12. Sources

---

## 1. cache and lib.onCache
`cache` is a global table that `@ox_lib/init.lua` creates in your resource.

| Key | Side | Value |
|---|---|---|
| `cache.resource` | shared | `GetCurrentResourceName()` |
| `cache.game` | shared | `'fivem'`, `'redm'` or `'fxserver'` |
| `cache.playerId` | client | `PlayerId()` |
| `cache.serverId` | client | `GetPlayerServerId(PlayerId())` |
| `cache.ped` | client | the player ped, refreshed every **100 ms** (0 values during a model swap are skipped) |
| `cache.vehicle` | client | the vehicle entity, or `false` |
| `cache.seat` | client | seat index (-1 = driver), or `false` |
| `cache.weapon` | client | weapon hash, or `false` when unarmed |
| `cache.mount` | client (RedM) | mount entity, or `false` |
| `cache.coords` | client | player coords. **Only populated while your resource uses `lib.points` or `lib.zones`** (updated every 300 ms). It can't be watched with `onCache`. |

```lua
lib.onCache('vehicle', function(value, oldValue)   -- value is the NEW value
    -- inside the handler cache.vehicle still holds the OLD value; use `value`
    if value then lib.notify({ description = 'Entered vehicle' }) end
end)
```
- `onCache` handlers run in new threads, so they can yield.
- Generic memoisation: `cache(key, fn, timeoutMs?)` caches the result of `fn()` under `key`, and clears it after `timeoutMs` if you pass one.
```lua
local stations = cache('gasStations', function() return lib.loadJson('data.stations') end)
```
- Cached values are read once from `exports.ox_lib:cache(key)`, then kept up to date through the `ox_lib:cache:<key>` local events. Prefer `cache.ped` over `PlayerPedId()` in hot loops. It is a table read, but it can be up to 100 ms stale right after a respawn or model change.

## 2. Callbacks
Callbacks are a request/response layer built on net events: `__ox_cb_<name>` for the request, and a response event named after the **calling resource**.

### Client → server
```lua
-- server
lib.callback.register('myres:server:getStock', function(source, shopId)
    if type(shopId) ~= 'string' or not Shops[shopId] then return end
    return Shops[shopId].stock
end)

-- client (in a thread/handler)
local stock = lib.callback.await('myres:server:getStock', false, 'shop_1')
-- or asynchronously:
lib.callback('myres:server:getStock', false, function(stock) print(json.encode(stock)) end, 'shop_1')
```
### Server → client
```lua
-- client
lib.callback.register('myres:client:getStreet', function(coords)
    local streetHash = GetStreetNameAtCoord(coords.x, coords.y, coords.z)   -- returns streetName, crossingRoad
    return GetStreetNameFromHashKey(streetHash)
end)
-- server
local street = lib.callback.await('myres:client:getStreet', src, vec3(0.0, 0.0, 0.0))
```

| Function | Side | Signature |
|---|---|---|
| `lib.callback.register` | both | `(name, handler)`. On the server the handler receives `(source, ...)`, on the client `(...)`. Return any number of values. |
| `lib.callback.await` | client | `(name, delay: number|false|nil, ...)` returns the handler's values (yields) |
| `lib.callback.await` | server | `(name, playerId, ...)` returns the handler's values (yields). Asserts `DoesPlayerExist(playerId)`. |
| `lib.callback` | client / server | `(name, delay / playerId, cb, ...)`, async; `cb(...)` receives the values. Calling without `cb` warns and awaits. |

Behaviour and gotchas (checked in source):
- **`delay` (client only)** is a per-callback-name rate limit in ms. If the same name was called less than `delay` ms ago, the call **returns `nil` immediately** and sends nothing. Pass `false` or `nil` for no limit.
- **Timeout**: an awaited call rejects after `ox:callbackTimeout` ms (default **300000** = 5 min). A rejected `await` **throws**, which is also what happens for "callback 'x' does not exist". Use `pcall(lib.callback.await, ...)` where a failure must not kill the thread.
- An **error inside the handler** is printed with a stack trace, and the caller receives `false`.
- **Ownership**: the first resource that registers a name owns it. Another resource that registers the same name gets a "SCRIPT ERROR: attempted to overwrite callback" message. Names are freed when the owning resource stops.
- **Validation (v3.30+)**: before each call ox_lib checks that the callback exists, and the caller gets "does not exist" instead of hanging until the timeout.
- **v3.40 security fix**: the server only accepts a server→client response from the player the request was sent to (the key ends with that player's id). Since v3.30.4 the client has ignored responses that don't come from the server.
- Return values go through msgpack. ox_lib sets `msgpack.setoption('ignore_invalid', true)` in your resource, so functions and userdata are **silently dropped**, not errors.
- **Security**: a server callback is a public net endpoint. Validate `source`, argument types, permissions and distance, and rate-limit on the server. The client `delay` is only a courtesy to the server and doesn't protect it.

## 3. lib.addCommand (server)
```lua
lib.addCommand(name | names[], properties | false, handler)
-- handler(source, args, rawCommand)
```
`properties`:
- `help`: chat suggestion text.
- `params`: an array of `{ name, type?, help?, optional? }`. `type` is one of:
  - `'number'`: `tonumber(arg)`.
  - `'string'`: rejects values that are numeric.
  - `'playerId'`: a number, or **`me`** for the caller. Rejected if `DoesPlayerExist` fails.
  - `'longString'`: **last param only**. Captures the rest of the raw command.
  - nil: the raw string.
- `restricted`: `true` (ACE `command.<name>`), `'group.admin'`, or `{ 'group.admin', 'group.mod' }`. With a string or array, ox_lib runs `add_ace <principal> command.<name> allow` for you.

```lua
lib.addCommand({ 'givecash', 'gc' }, {
    help = 'Give cash to a player',
    params = {
        { name = 'target', type = 'playerId', help = 'Server id or "me"' },
        { name = 'amount', type = 'number', help = 'Amount' },
        { name = 'reason', type = 'longString', help = 'Reason', optional = true },
    },
    restricted = 'group.admin',
}, function(source, args, raw)
    if args.amount < 1 or args.amount > 1000000 or math.type(args.amount) ~= 'integer' then return end
    Bridge.AddMoney(args.target, 'cash', args.amount, args.reason or 'admin')
end)
```
- Parsed args are keyed by `name` (`args.target`). The numeric indexes are removed.
- An invalid or missing required argument prints `command 'x' received an invalid <type> for argument n` to the console and the handler **doesn't run**. The player gets no feedback, so if UX matters, validate yourself with `optional = true`.
- Handler errors are caught with `pcall` and printed.
- Chat suggestions are sent to all players one second after start and to each player on `playerJoining`.
- `source` is `0` when the command runs from the server console. Guard against that before you call player natives.
- The pre-v3.0 syntax `lib.addCommand(group, name, cb, params)` only prints a deprecation warning (via `lib.__addCommand`). Migrate it.
- **ACE prerequisite**: `restricted = 'group.x'` makes **ox_lib** execute `add_ace`, so server.cfg needs `add_ace resource.ox_lib command.add_ace allow` (see section 5).

## 4. lib.addKeybind (client)
```lua
local kb = lib.addKeybind({
    name = 'myres_hands_up',          -- unique; becomes +myres_hands_up / -myres_hands_up commands
    description = 'Hands up',         -- shown in Settings > Key Bindings > FiveM
    defaultKey = 'X',                 -- default ''
    defaultMapper = 'keyboard',       -- default 'keyboard' (see input mapper ids in the Cfx docs)
    -- secondaryKey / secondaryMapper: optional second mapping, registered as '~!+name'
    allowInPauseMenu = false,         -- v3.36; presses are ignored while the pause menu is open unless true
    disabled = false,
    onPressed = function(self) end,
    onReleased = function(self) end,
})
kb:disable(true)            -- blocks callbacks and resets isPressed
kb:isControlPressed()       -- boolean
print(kb.currentKey)        -- current binding label (via GetControlInstructionalButton)
```
- Built on `RegisterKeyMapping`, so **the default key only applies the first time a player sees the mapping**. After that the player's own binding wins, and changing `defaultKey` later doesn't affect existing players.
- FiveM only: the module returns early on RedM.
- Any extra fields you add stay on the returned object (`self`).
- The chat suggestions for `/+name` and `/-name` are removed automatically.
- `secondaryKey` and `secondaryMapper` (which defaults to `defaultMapper`) add a second binding. Mapper and key names follow the Cfx input-mapper list: https://docs.fivem.net/docs/game-references/input-mapper-parameter-ids/

## 5. ACL (server)
These run inside ox_lib through `ExecuteCommand`, and accept a number (turned into `player.<id>`) or a principal string:
```lua
lib.addAce(principal, ace, allow?)        -- allow=false -> 'deny'
lib.removeAce(principal, ace, allow?)
lib.addPrincipal(child, parent)           -- e.g. lib.addPrincipal(src, 'group.police')
lib.removePrincipal(child, parent)
```
Required server.cfg lines (from the official install docs):
```cfg
add_ace resource.ox_lib command.add_ace allow
add_ace resource.ox_lib command.remove_ace allow
add_ace resource.ox_lib command.add_principal allow
add_ace resource.ox_lib command.remove_principal allow
```
Principals added at runtime aren't persisted, so re-add them on join (for example from your job or group data).

## 6. lib.triggerClientEvent (server)
```lua
lib.triggerClientEvent(eventName, targetIds, ...)   -- targetIds: number (or -1) | array of numbers
lib.triggerClientEvent('myres:client:sync', { 1, 5, 9 }, payload)
```
It packs the arguments with msgpack **once** and sends the same payload to each target through `TriggerClientEventInternal`. That is cheaper than looping `TriggerClientEvent` over many players with large payloads.

## 7. Hooks (v3.34+)
A **pipeline** lets other resources veto or observe an action in your resource, the same idea as ox_inventory hooks.
```lua
-- server, resource 'mybank' (pipeline owner)
local withdrawHook = lib.hook:new('withdraw', function(hook, payload)   -- optional filter(hookOptions, payload)
    return not hook.account or hook.account == payload.account
end)
-- this exports registerHook:withdraw and removeHook:withdraw from 'mybank'

local function withdraw(src, account, amount)
    local result <close> = withdrawHook:dispatch({ source = src, account = account, amount = amount })
    if not result.ok then return false end   -- a hook returned false
    -- ... perform the withdrawal ...
    return true
end   -- when `result` closes, post-hook events fire with (ok, payload)

-- server, another resource
local hook = lib.registerHook('mybank:withdraw', function(payload)
    if payload.amount > 50000 then return false end   -- reject
end, { account = 'business' })                        -- options are matched by the pipeline filter
hook:on(function(ok, payload) lib.logger(payload.source, 'withdraw', ('ok=%s amount=%s'):format(ok, payload.amount)) end)
-- hook:off(); hook:remove()
```
- `dispatch` returns `{ ok, size }`, where `size` is the number of hooks that passed the filter. Declare it with `<close>` so the post-hook events fire.
- A hook rejects by returning **exactly `false`**. Returning `nil` allows the action.
- Hooks are removed automatically when the registering resource stops.
- `lib.registerHook('resource:event', options)` with no handler registers an observer-only hook. Use `:on()` to receive the outcome.
- **Built-in pipelines**: `ox_lib:setPlayerState` and `ox_lib:setEntityState` (section 9).

## 8. Game entity classes (v3.34+)
These are thin OOP wrappers that cache the handle, netId and state bag name.

| Class | Create | Notes |
|---|---|---|
| `lib.gameEntity` | (base) | methods below |
| `lib.ped` | client: `lib.ped.create(model, x, y, z, heading?, isNetworked?, bScriptHostPed?)`; server: `lib.ped.create(model, x, y, z, heading?)` (always networked) | `getArmour()`, `setArmour(n)` |
| `lib.player` | `lib.player:new(serverId)`; `-1` = yourself (client) / the first player (server) | `playerId`; `netId` = server id; `setModel(model)`; `handle` always re-reads `GetPlayerPed` on the client |
| `lib.prop` | client: `lib.prop.create(model, x, y, z, heading?, isNetworked?, netMissionEntity?, dynamic?)`; server: `lib.prop.create(model, x, y, z, heading?, dynamic?)` (`CreateObjectNoOffset`) | `setOnGround()` |
| `lib.vehicle` | client: `lib.vehicle.create(model, x, y, z, heading?, isNetworked?, netMissionEntity?)`; **server: `lib.vehicle.create(model, type, x, y, z, heading?)`** (`CreateVehicleServerSetter`) | `getType()`, `getPlate()`, `setPlate(p)`, `setOnGround()` |
| wrap an existing entity | `lib.vehicle:new(handle)`, `lib.ped:new(handle)`, `lib.prop:new(handle)` | |

Base methods: `set(key, value, mode?)`, `setr(key, value)`, `sets(key, value)`, `get(key)`, `has(key)`, `keys()`, `setHandle(handle)`, `getCoords()`, `setCoords(x, y, z, deadFlag?, ragdollFlag?, clearArea?)`, `getModel()`, `getHeading()`, `setHeading(h)`, `getRoutingBucket()`, `setRoutingBucket(bucket)` (server only; it also replicates state `bucket` so clients can read it).
```lua
-- server
local veh = lib.vehicle.create(`sultan`, 'automobile', -56.48, -1116.87, 26.43, 0.0)
veh:setPlate('OX 123')
veh:setr('owner', charId)          -- replicated state bag value
veh:setOnGround()                  -- the server asks the owning client to place it (state 'ox_entity_setonground')
print(veh.netId, veh.handle)
```
- Client `create` helpers call `lib.requestModel` and release the model afterwards. Server `create` passes the model straight to the native: use a backtick hash or a string the native accepts.
- **Server `setOnGround` for props**: v3.40.0's client handler calls `lib.object:new(...)` for non-vehicles, and no `object` module exists in ox_lib. Server-side `prop:setOnGround()` will most likely error on clients (observed in source, **UNVERIFIED** in game). Prefer client `PlaceObjectOnGroundProperly` for props.

## 9. Entity state replication modes (v3.36+)
`entity:set(key, value, mode)`:
- `mode = nil`: a local value only (not replicated).
- `mode = 1` (`setr`): replicated to the server and all relevant clients.
- `mode = 2` (`sets`): **synced**, kept only between the server and that player. Players only; non-player entities error.

What happens on a **client** write:
- If `sv_stateBagStrictMode` is off, a `mode 1` write goes directly through `SetStateBagValue`, as before.
- If strict mode is **on** (or for `mode 2`), the client calls `lib.callback.await('ox_lib:requestSetStateBag', ...)`. The server dispatches the `ox_lib:setPlayerState` or `ox_lib:setEntityState` hook pipeline, and the write is **rejected unless a hook for that key returns non-false**. A player can only target their own `player:` bag.
- These are `@async` calls, so call them from a thread. They return `true` or `false`.

```lua
-- server: allow clients to set their own 'isLooting' (boolean only)
lib.registerHook('ox_lib:setPlayerState', function(payload)
    -- payload: playerId, targetId, entityId, type ('player'|'entity'), bag, key, value, mode
    return type(payload.value) == 'boolean'
end, { key = 'isLooting' })

-- client
CreateThread(function()
    local me = lib.player:new(cache.serverId)
    local ok = me:setr('isLooting', true)
end)
```
Built-in entity hooks: `ox_lib:setVehicleProperties` (a client can only **clear** it, and only when the plate matches) and `ox_entity_setonground` (true or nil only).

**Security advisory (v3.37+)**: at startup ox_lib prints a warning if `sv_stateBagStrictMode` is disabled. Strict mode rejects client-originated state bag writes. Turn it on with `setr sv_stateBagStrictMode true`, then test your resources: anything that writes `LocalPlayer.state` or `Entity(x).state` replicated from the client will stop syncing unless it goes through a hook. To silence the warning: `set ox:ignoreSecurityAdvisory ["stateBagStrictMode"]`. The warning is skipped automatically when `qb-core` is present.

## 10. Server vehicle properties via state bag
`lib.setVehicleProperties(vehicle, props)` on the **server** sets the replicated entity state `ox_lib:setVehicleProperties`. The entity owner's client applies the properties with the client function and then clears the key. Use it right after server-side vehicle creation:
```lua
-- server
local veh = CreateVehicleServerSetter(`sultan`, 'automobile', x, y, z, h)
lib.setVehicleProperties(veh, props)   -- props from your DB (lib.getVehicleProperties output)
```
The deprecated net event `ox_lib:setVehicleProperties(netId, props)` still exists, but it depends on whoever owns the entity at that moment, so avoid it. Full property list and client usage: [ox-lib-world.md](ox-lib-world.md#9-vehicle-properties).

## 11. Common mistakes
- Using `lib.callback.await` without validating on the server, or trusting `delay` as anti-spam.
- Two resources registering the same callback name (the second fails).
- Not wrapping `await` in `pcall` when a player can drop mid-request. The server-side await asserts `DoesPlayerExist` and otherwise waits up to the timeout before throwing.
- `restricted = 'group.admin'` without the `add_ace resource.ox_lib command.add_ace allow` line, so the ACE never gets added.
- Using a `playerId` param and then forgetting that `source == 0` from the console.
- Expecting `lib.addKeybind` `defaultKey` changes to rebind existing players.
- Turning on `sv_stateBagStrictMode` without auditing client-side state writes, or turning it off to "fix" sync instead of adding a server hook.
- Calling `lib.vehicle.create` on the server with the client argument order (the server needs `type` second).

## 12. Sources
- https://github.com/overextended/ox_lib/blob/v3.40.0/init.lua (cache, onCache)
- https://github.com/overextended/ox_lib/blob/v3.40.0/resource/cache/client.lua
- https://github.com/overextended/ox_lib/tree/v3.40.0/imports/callback (client.lua, server.lua) and https://github.com/overextended/ox_lib/blob/v3.40.0/resource/callbacks/shared.lua
- https://github.com/overextended/ox_lib/blob/v3.40.0/imports/addCommand/server.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/imports/addKeybind/client.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/resource/acl/server.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/imports/triggerClientEvent/server.lua
- https://github.com/overextended/ox_lib/tree/v3.40.0/imports/hook, https://github.com/overextended/ox_lib/tree/v3.40.0/imports/registerHook, https://github.com/overextended/ox_lib/blob/v3.40.0/resource/state/server.lua
- https://github.com/overextended/ox_lib/tree/v3.40.0/imports/gameEntity (plus ped, player, prop, vehicle), https://github.com/overextended/ox_lib/blob/v3.40.0/resource/client.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/resource/server.lua
- https://github.com/overextended/ox_lib/blob/v3.40.0/resource/vehicleProperties/server.lua
- Docs: https://overextended.dev/docs/ox_lib/Callback/Lua/Server, https://overextended.dev/docs/ox_lib (install / ACE), docs source pages GameEntity.mdx, Hooks.mdx, Cache/Client.mdx, AddCommand/Server.mdx in https://github.com/overextended/overextended.github.io
- Release notes v3.34.0–v3.40.0: https://github.com/overextended/ox_lib/releases
