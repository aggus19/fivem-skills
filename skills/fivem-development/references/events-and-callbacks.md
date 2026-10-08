# Events, callbacks, commands and the built-in event list

Baseline: FXServer Legacy 35245 / citizenfx/fivem master `a74c2cc` (2026-10-07), docs.fivem.net event list + `runtime.fivem.net/doc/events/*.html.json` + `NETEV` annotations in source — verified 2026-10-07.

## Contents
1. Event API (Lua / JS / C#)
2. Naming and security rules
3. Built-in core events — server
4. Built-in core events — client
5. Network game events (OneSync, server, cancellable)
6. System-resource events (baseevents, spawnmanager, mapmanager, sessionmanager, chat)
7. Cancelling events
8. Callbacks (request/response)
9. Commands and key mappings
10. Framework player-loaded events
11. Latent events, payload size and rate limits
12. Sources

## 1. Event API
| From → To | Lua send | Lua receive | JS equivalent |
|---|---|---|---|
| client → server | `TriggerServerEvent(name, ...)` | `RegisterNetEvent(name, function(...) local src = source end)` | `emitNet(name, ...)` / `onNet(name, cb)` |
| server → one client | `TriggerClientEvent(name, src, ...)` | `RegisterNetEvent(name, handler)` | `emitNet(name, src, ...)` |
| server → all clients | `TriggerClientEvent(name, -1, ...)` | same | `emitNet(name, -1, ...)` |
| same side, any resource | `TriggerEvent(name, ...)` | `AddEventHandler(name, handler)` | `emit` / `on` |
| large payload | `TriggerLatentServerEvent(name, bps, ...)` / `TriggerLatentClientEvent(name, target, bps, ...)` | same handlers | `TriggerLatent*` globals |

- `RegisterNetEvent(name[, handler])` marks the event **safe for net** and (optionally) adds the handler. Without it, network triggers are dropped with "event X was not safe for net". `RegisterServerEvent` is a legacy alias.
- `AddEventHandler` returns a handle → `RemoveEventHandler(handle)`. JS: `removeEventListener(name, cb)`.
- Handlers run in their own coroutine (`Citizen.CreateThreadNow`): you can `Wait`/await inside, but **capture `local src = source` first**.
- C#: `[EventHandler("name")]` or `EventHandlers["name"] += new Action<...>(...)`; `[FromSource] Player player` (server) gets the sender. All C# handlers are net-callable — validate.
- `GetInvokingResource()` inside a handler/export: name of the resource that called `TriggerEvent`/the export. Use it to restrict internal events and privileged exports; for network events rely on `source`, not on this.
- Event names are case-sensitive strings; payloads are msgpack (see `runtimes.md` §8).

## 2. Naming and security rules
- Format `resource:side:action` (`myres:server:buyItem`). Never generic names (`giveMoney`, `server:payout`) — cheat menus enumerate and spam them.
- Every `RegisterNetEvent` on the server is a public API: validate `source`, permission, distance, types/ranges, server-side prices, cooldown. Details: `security.md`.
- Don't make client-to-client relays (`TriggerClientEvent(name, targetFromClient, ...)`) without checks.
- Server-only internal events: `AddEventHandler` (not `RegisterNetEvent`) and check `GetInvokingResource()`.

## 3. Built-in core events — server
`Cancel` = `CancelEvent()` has an effect.

| Event | Params (after `source`) | `source` | Cancel | Notes |
|---|---|---|---|---|
| `playerConnecting` | `name, setKickReason(reason), deferrals` | temporary id (not the final server id) | yes (rejects, only before yielding) | `deferrals.defer()`, wait ≥ 1 tick, then `update(msg)`, `presentCard(card, cb(data, raw))`, `handover(table)` (→ loading screen `window.nuiHandoverData`), `done(reason?)`. Use temp id only with identifier natives. |
| `playerJoining` | `oldId` (temp id string) | final server id | no | Player has its permanent id. Legacy ids never reused; **Enhanced reuses ids**. |
| `playerDropped` | `reason, resourceName, clientDropReason` | leaving player | no | `clientDropReason` = enum in `ClientDropReasons.h`. Clean per-player state here. |
| `playerEnteredScope` / `playerLeftScope` | `{ for = id, player = id }` (strings) | — | no | OneSync culling scope changes. |
| `onResourceStarting` | `resourceName` | — | yes (prevents start) | |
| `onResourceStart` / `onServerResourceStart` | `resourceName` | — | no | `onResourceStart` fires immediately; `onServerResourceStart` is queued after start. Compare with `GetCurrentResourceName()`. |
| `onResourceStop` / `onServerResourceStop` | `resourceName` | — | no | Cleanup entities/state. |
| `onResourceListRefresh` | — | — | no | After `refresh` command. |
| `entityCreating` | `handle` | — | yes (deletes entity) | OneSync; entity from a client. Anti-spam point. |
| `entityCreated` | `handle` | — | no | Queued after creation (client- or server-created). |
| `serverEntityCreated` | `handle` | — | no | Server-script-created entity; may have no owner yet. |
| `entityRemoved` | `entity` | — | no | |
| `onEntityBucketChange` | `entity, bucket, oldBucket` | — | no | Routing buckets. |
| `onPlayerBucketChange` | `player, bucket, oldBucket` | — | no | |
| `rconCommand` | `command, args` | — | yes | **Deprecated**: use `RegisterCommand(..., true)`. |
| `__cfx_internal:commandFallback`, `__cfx_internal:httpResponse` | internal | | | Don't handle. |

Network game events (also server) are in §5.

## 4. Built-in core events — client
| Event | Params | Cancel | Notes |
|---|---|---|---|
| `onClientResourceStart` / `onClientResourceStop` | `resourceName` | no | Queued after start / after stop. |
| `onResourceStart` / `onResourceStarting` / `onResourceStop` | `resourceName` | `onResourceStarting` yes | Same semantics as server. Release NUI focus / delete local entities on stop. |
| `gameEventTriggered` | `name, args[]` (ints) | no | Engine network events, e.g. `CEventNetworkEntityDamage` (args: victim, attacker, ..., fatal flag, weapon hash...). List: game-events page. |
| `<CEventName>` (e.g. `CEventShockingCarCrash`) | `entities[], eventEntity, data[]` | no | Any engine event name can be listened to directly. |
| `entityDamaged` | `victim, culprit, weaponHash, baseDamage` | no | **Locally** damaged entities only. |
| `populationPedCreating` | `x, y, z, model, setters` | yes (skip ped) | `setters.setModel(nameOrHash)`, `setters.setPosition(x, y, z)`. Load the model first. |
| `mumbleConnected` / `mumbleDisconnected` | `address, reconnecting` / `address` | no | Voice (Mumble deprecated on Enhanced). |
| `onPlayerJoining` / `onPlayerDropped` | `serverId, name, slotId` | no | Sent by the server when another player enters/leaves **your** OneSync scope. |
| `mapDataLoaded` / `mapDataUnloaded` | `mapDataHash` | no | ymap streamed in/out (**UNVERIFIED**: unloaded param shape). |
| `__cfx_nui:<callback>` | `body, cb` | — | Internal transport of `RegisterNUICallback`; don't use directly. |

## 5. Network game events (OneSync, server)
Signature: `AddEventHandler(name, function(sender, data) ... end)` — `sender` = id of the player that sent the engine event (the server passes it as a **string** — use `tonumber(sender)`; `source` is not set); `data` = table. All are dispatched with a return value: **`CancelEvent()` stops the engine event from being routed/applied** (this is how anticheats block explosions, weapon gives, task clears). The server command `block_net_game_event EXPLOSION_EVENT` (names from the net-game-events enum, case-insensitive; `unblock_net_game_event` reverts) drops a whole type before any script runs.

| Event | Key `data` fields | Typical use |
|---|---|---|
| `weaponDamageEvent` | `hitGlobalId`, `hitGlobalIds[]`, `weaponType` (hash), `weaponDamage`, `overrideDefaultDamage`, `willKill`, `damageType`, `damageFlags`, `silenced`, `hitComponent`, `localPosX/Y/Z`, `damageTime`, `tyreIndex`, `suspensionIndex`, `parentGlobalId` | Block god-damage, wrong weapon, friendly-fire rules. |
| `explosionEvent` | `explosionType`, `ownerNetId`, `damageScale`, `posX/Y/Z`, `cameraShake`, `isAudible`, `isInvisible` (+ `f*` unknowns) | Block spawned explosions (most common cheat). |
| `fireEvent` | list of fires (`posX/Y/Z`, `isEntity`, `entityGlobalId`, `weaponHash`, `maxChildren`, `fireId`, ...) — nesting **UNVERIFIED** | Block fire spam. |
| `startProjectileEvent` | `ownerId`, `projectileHash`, `weaponHash`, `initialPositionX/Y/Z`, `firePositionX/Y/Z`, `targetEntity`, `commandFireSingleBullet` | Block projectile spam. |
| `ptFxEvent` | `effectHash`, `assetHash`, `posX/Y/Z`, `offsetX/Y/Z`, `rotX/Y/Z`, `scale`, `isOnEntity`, `entityNetId` | Block particle spam. |
| `giveWeaponEvent` | `pedId`, `weaponType`, `ammo`, `givenAsPickup` | Block weapon give to others. |
| `removeWeaponEvent` / `removeAllWeaponsEvent` | `pedId`, `weaponType` / `pedId` | Block weapon strip of other players. |
| `clearPedTasksEvent` | `pedId`, `immediately` | Block "kick out of vehicle / freeze" trolling. |
| `respawnPlayerPedEvent` | `posX/Y/Z`, ... | Logging. |
| `vehicleComponentControlEvent` | `vehicleGlobalId`, `pedGlobalId`, `componentIndex`, `request`, `componentIsSeat`, `pedInSeat` | Seat/door control requests. |
| `givePedScriptedTaskEvent` | `entityNetId`, `taskId` | Block tasks on peds you don't own. |
| `requestNetworkSyncedSceneEvent` / `startNetworkSyncedSceneEvent` / `updateNetworkSyncedSceneEvent` / `stopNetworkSyncedSceneEvent` | `sceneId` (+ scene details on start: position, rotation, entities, anim dict hash...) | Synced scene abuse. |
| `weaponDamageReply`, `respawnPlayerPedReply`, `vehicleComponentControlReply` | reply packets | Rare. |

```lua
-- server/anticheat.lua
local blockedExplosions <const> = { [7] = true, [29] = true }   -- example types; tune per server
AddEventHandler('explosionEvent', function(sender, ev)
    if blockedExplosions[ev.explosionType] then
        CancelEvent()
        print(('[ac] blocked explosion %d from %s'):format(ev.explosionType, sender))
    end
end)
```
RedM-only events (`lightningEvent`, carriable/loot events) are compiled only for RDR3.

## 6. System-resource events
These come from Cfx default resources and are **client-originated** — a cheater can trigger them with fake data. Never pay out or punish based on them without server checks.

| Event | Side received | Params | Source resource |
|---|---|---|---|
| `baseevents:onPlayerDied` | client + server | `killerType, {x, y, z}` | baseevents |
| `baseevents:onPlayerKilled` | client + server | `killerId, { killertype, weaponhash, killerinveh, killervehseat, killervehname, killerpos }` | baseevents |
| `baseevents:onPlayerWasted` | client + server | `{x, y, z}` | baseevents |
| `baseevents:enteringVehicle` | server | `vehicle, seat, displayName, netId` | baseevents |
| `baseevents:enteringAborted` | server | — | baseevents |
| `baseevents:enteredVehicle` / `baseevents:leftVehicle` | server | `vehicle, seat, displayName, netId` | baseevents (`vehicle` is a client handle: use `netId`) |
| `playerSpawned` | client | `{ x, y, z, heading, idx, model, skipFade }` | spawnmanager |
| `onClientMapStart` / `onClientMapStop` / `onClientGameTypeStart` / `onClientGameTypeStop` | client | `resourceName` | mapmanager |
| `getMapDirectives` | client | `add` callback | mapmanager |
| `playerActivated`, `sessionInitialized` | client | — | sessionmanager |
| `chatMessage` | server | `source, author, text` (cancel = message not broadcast) | chat |
| `chat:addMessage` / `chat:addTemplate` / `chat:addSuggestion(s)` / `chat:removeSuggestion` / `chat:clear` | client (trigger them) | message object / `name, help, params[]` | chat |

## 7. Cancelling events
- `CancelEvent()` inside a handler; `WasEventCanceled()` after `TriggerEvent` (same side) to see if any handler cancelled.
- Works only for events whose emitter checks it: `playerConnecting` (before yield), `onResourceStarting`, `entityCreating`, `populationPedCreating`, all §5 net game events, `chatMessage`, `rconCommand`, and your own events where you check `WasEventCanceled()`.
- Cancelling a normal net event does nothing for other handlers already queued.

## 8. Callbacks (request/response)
Prefer **ox_lib** callbacks (any framework):
```lua
-- server/main.lua
lib.callback.register('myres:server:getStock', function(source, shopId)
    if type(shopId) ~= 'string' then return nil end
    return Stock[shopId]
end)
-- client/main.lua (inside a thread/handler)
local stock = lib.callback.await('myres:server:getStock', false, 'shop_1')
```
| Framework | Server register | Client call |
|---|---|---|
| ox_lib / Qbox | `lib.callback.register(name, function(source, ...) return ... end)` | `lib.callback.await(name, false, ...)` (2nd arg = delay/false) or `lib.callback(name, false, cb, ...)` |
| QBCore | `QBCore.Functions.CreateCallback(name, function(source, cb, ...) cb(result) end)` | `QBCore.Functions.TriggerCallback(name, function(result) end, ...)` |
| ESX | `ESX.RegisterServerCallback(name, function(source, cb, ...) cb(result) end)` | `ESX.TriggerServerCallback(name, cb, ...)` / `ESX.AwaitServerCallback(name, ...)` |

Server → client: `lib.callback.await(name, playerId, ...)` with `lib.callback.register` on the client. **Never** trust client answers for anything that grants value. Without ox_lib, the pattern is two events + a request id + `promise` (see `runtimes.md` §5).

## 9. Commands and key mappings
```lua
-- server: restricted = true → requires ACE "command.heal" (add_ace group.admin command.heal allow)
RegisterCommand('heal', function(source, args, raw)
    local target = tonumber(args[1]) or source
    -- source == 0 when run from the server console
end, true)

-- client: rebindable key (Settings > Key Bindings > FiveM)
RegisterCommand('+myres_menu', function() OpenMenu() end, false)
RegisterCommand('-myres_menu', function() end, false)
RegisterKeyMapping('+myres_menu', 'Open my menu', 'keyboard', 'F6')
TriggerEvent('chat:addSuggestion', '/heal', 'Heal a player', { { name = 'id', help = 'Server id' } })
```
- `RegisterKeyMapping(command, description, defaultMapper, defaultParameter)`: mappers include `keyboard`, `mouse_button`, `pad_digitalbutton` (full list on the native page). The player's binding is saved per command name: renaming the command resets user binds.
- Client commands are client-side: never trust them for privileged actions; server commands with `restricted = true` use ACE.
- Enhanced: `RegisterCommand` returns an id and `UnregisterCommand(id)` exists.
- ox_lib: `lib.addCommand` (server, typed params + restriction), `lib.addKeybind` (client).

## 10. Framework player-loaded events
| Framework | Client | Server |
|---|---|---|
| Qbox | `QBCore:Client:OnPlayerLoaded`, `qbx_core:client:playerLoggedOut`, `QBCore:Client:OnJobUpdate`, `QBCore:Client:OnGangUpdate`, `qbx_core:client:onGroupUpdate`; state `LocalPlayer.state.isLoggedIn` | `QBCore:Server:OnPlayerLoaded`, `QBCore:Server:OnPlayerUnload`, `QBCore:Server:OnJobUpdate` (see `framework-qbox.md`) |
| QBCore | `QBCore:Client:OnPlayerLoaded`, `QBCore:Client:OnPlayerUnload`, `QBCore:Client:OnJobUpdate`, `QBCore:Player:SetPlayerData` | `QBCore:Server:PlayerLoaded` (Player), `QBCore:Server:OnPlayerUnload` |
| ESX | `esx:playerLoaded` (xPlayer data, isNew, skin), `esx:onPlayerLogout`, `esx:setJob` | `esx:playerLoaded` (playerId, xPlayer, isNew), `esx:playerDropped`, `esx:setJob` |
| ox_core | `ox:playerLoaded`, `ox:playerLogout` | `ox:playerLoaded`, `ox:playerLogout` |

Handle **resource restart**: in your own `onResourceStart`, initialise for already-loaded players (e.g. `if LocalPlayer.state.isLoggedIn then init() end`), because the loaded event won't fire again.

## 11. Latent events, payload size and rate limits
- Normal net events share the reliable channel: multi-KB payloads stall it. Use latent events: `TriggerLatentClientEvent(name, target, bps, ...)`; `bps` ≤ 0 → default 25 000 B/s; with target `-1` the server sends `bps × players`. Avoid ~10 MB/s-scale values.
- Server rate limiters (per client, from source; tune with `rateLimiter_<name>_rate` / `rateLimiter_<name>_burst` convars):

| Limiter | Rate / burst | Effect |
|---|---|---|
| `netEvent` | 50/s, burst 200 | excess events dropped |
| `netEventFlood` | 75/s, burst 300 | client dropped (flood) |
| `netEventSize` | 128 KiB/s, burst 384 KiB | excess dropped |
| `latentEvent` | 75/s, burst 125 | |
| `netCommand` / `netCommandSize` | 7/s burst 14 / 1 KiB/s burst 8 KiB | client → server commands |

- Validate table sizes and string lengths on receipt; for state many clients observe, prefer state bags (`onesync-entities.md`).

## 12. Sources
- https://docs.fivem.net/docs/scripting-reference/events/list/ · https://docs.fivem.net/docs/scripting-reference/events/server-events/ · https://docs.fivem.net/docs/scripting-reference/events/client-events/
- https://runtime.fivem.net/doc/events/server.html.json · https://runtime.fivem.net/doc/events/client.html.json (generated from `NETEV` comments)
- https://docs.fivem.net/docs/scripting-manual/working-with-events/ (triggering, listening, canceling, latent)
- https://docs.fivem.net/docs/game-references/net-game-events/ · https://docs.fivem.net/docs/developers/legacy-vs-enhanced/
- https://github.com/citizenfx/fivem — `code/components/citizen-server-impl/src/state/ServerGameState.cpp` (net game event structs + dispatch), `code/components/citizen-server-impl/src/GameServer.cpp` (playerDropped), `code/components/citizen-server-impl/src/packethandlers/ServerEventPacketHandler.cpp` (rate limits), `code/components/citizen-resources-gta/src/GameEventFunctions.cpp`, `data/shared/citizen/scripting/lua/scheduler.lua`
- https://github.com/citizenfx/cfx-server-data/tree/master/resources/%5Bsystem%5D/baseevents · https://docs.fivem.net/docs/resources/baseevents/ · https://docs.fivem.net/docs/resources/chat/events/chatMessage/
