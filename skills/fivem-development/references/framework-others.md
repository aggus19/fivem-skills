# Other frameworks: ND_Core, vRP family, standalone

Baseline verified 2026-10-07 from source and official docs. Qbox, ESX Legacy and ox_core have their own files ([framework-qbox.md](framework-qbox.md), [framework-esx.md](framework-esx.md), [ox-core.md](ox-core.md)); QBCore is in [framework-qbcore.md](framework-qbcore.md). Community resources (voice, phones, appearance, banking, admin menus...) moved to [ecosystem-resources.md](ecosystem-resources.md).

## Contents
1. Landscape in 2026 (which framework is what)
2. ND_Core (ND Framework)
3. vRP classic (vRP 1 / vRP 2)
4. vRP Creative / vRPEX (Brazilian distributions)
5. Standalone (no framework)
6. Bridges for multi-framework resources
7. Choosing a stack for a new server
Sources

## 1. Landscape in 2026
| Framework | Repo / status (2026-10-07) | Notes |
|---|---|---|
| Qbox (qbx_core) | Qbox-project/qbx_core v1.24.0 (2026-08-22), very active | QBCore-compatible, ox-based — see framework-qbox.md |
| ESX Legacy | esx-framework/esx_core 1.15.2, active (push 2026-10-07) | see framework-esx.md |
| QBCore | qbcore-fivem/qb-core 1.3.0, maintained (big refactor 2026-05) | see framework-qbcore.md |
| ox_core | overextended/ox_core 1.5.14, active | see [ox-core.md](ox-core.md) |
| **ND_Core** | ND-Framework/ND_Core **v2.3.2 release (2025-02-22)**; `main` has unreleased commits up to **2026-03-20** | small, ox_lib/ox_inventory based |
| **vRP (classic)** | vRP-framework/vRP, last push 2025-05-15, last release "1.0" (2018) | vRP 2 on `master`; effectively unmaintained |
| **vRP Creative / vRPEX** | not on GitHub as a canonical repo; sold/shared in Brazilian communities | vRP 1-style API, every distribution differs |
| RedM frameworks (VORP, RSG...) | out of scope (RDR3, not FiveM) | |
"Renewed" (Renewed-Scripts) is **not** a framework: it is a set of resources (Renewed-Lib bridge, Renewed-Banking, Renewed-Weathersync) that run on top of QBCore/Qbox/ESX/ox/ND — see ecosystem-resources.md.

## 2. ND_Core
Repo https://github.com/ND-Framework/ND_Core (GPL-3.0) · Docs https://ndcore.dev (core API under https://ndcore.dev/core) · release v2.3.2 (2025-02-22); `main` since then: DB-backed groups (`groups.sql`, `group_ranks.sql`) and an admin group panel, money logs (`moneylogs.sql`), garages moved out to a separate `ND_Garages` resource (vehicle API kept). Ask whether the server runs the 2.3.2 release or `main`.
Dependencies: `ox_lib`, `oxmysql`; inventory = ox_inventory. Add-ons: ND_Characters, ND_Banking, ND_AppearanceShops, ND_Dealership, ND_Ambulance, ND_Police, ND_MDT (see ndcore.dev/addons).

### Import
```lua
-- fxmanifest.lua
shared_script '@ND_Core/init.lua'   -- defines global NDCore (proxy over exports)
-- or call exports directly without the import:
-- local player = exports['ND_Core']:getPlayer(src)
```
Every `NDCore.*` function is also an export of `ND_Core` (docs: "every function in ND Core is an export").

### Server API (from source, `server/*.lua`)
| Function | Notes |
|---|---|
| `NDCore.getPlayer(src)` | active character object or nil |
| `NDCore.getPlayers(key?, value?, returnArray?)` | filter by `id`, `firstname`, `lastname`, `gender`, `groups`, `job`, else metadata key |
| `NDCore.getPlayerIdentifierByType(src, type)`, `getPlayerServerInfo(src)`, `getConfig(key?)`, `getDiscordInfo(discordUserId)` | |
| `NDCore.newCharacter(src, info)`, `fetchCharacter(id, src?)`, `fetchAllCharacters(src)`, `setActiveCharacter(src, id)`, `enableMultiCharacter(bool)` | character management |
| Groups: `doesGroupExist(name)`, `getGroupData(name)`, `createNewGroup(name, label, isJob, ranks)`, `editGroupData(name, data)`, `deleteGroup(name)`, `getAllGroups()` | `main` branch (DB groups) |
| Vehicles: `createVehicle(info)`, `spawnOwnedVehicle(src, vehicleId, coords, heading)`, `setVehicleOwned(src, props, stored, setPlate?)`, `getVehicle(entity)`, `getVehicleById(id)`, `getVehicles(characterId)`, `giveVehicleAccess(src, veh, access, info)`, `shareVehicleKeys(src, target, veh)`, `transferVehicleOwnership(vehId, fromSrc, toSrc)`, `generateVehiclePlate()`, `generateUniqueVehiclePlate()` | |
| `NDCore.loadSQL(file, resource)` | run a .sql file |

Character (player) object — fields: `id`, `source`, `identifier`, `user_id`, `identifiers`, `discord`, `name`, `firstname`, `lastname`, `fullname`, `dob`, `gender`, `cash`, `bank`, `phonenumber`, `groups`, `job`, `jobInfo`, `metadata`, `inventory`.
Methods: `addMoney(account, amount, reason)` / `deductMoney(account, amount, reason)` (`account` = `'cash'|'bank'`; return `true`, or nil on invalid input — **they do not check the balance**, check `player.cash`/`player.bank` first), `depositMoney(n)`, `withdrawMoney(n)`, `getData(key)`, `setData(key, value, reason?)`, `getMetadata(key)`, `setMetadata(key, value)`, `addGroup(name, rank, customGroup?, isJob?)`, `removeGroup(name)`, `getGroup(name)`, `setJob(name, rank, customGroup?, keepGroup?)`, `getJob()` → `name, info`, `createLicense(type, expire)`, `getLicense(id)`, `updateLicense(id, data)`, `setCoords(coords)`, `triggerEvent(name, ...)`, `notify(...)` (ox_lib notify), `revive()`, `drop(reason)`, `save(key?)`, `unload()`, `delete()`.
```lua
-- server/main.lua
local PRICE <const> = 250
RegisterNetEvent('myres:server:buy', function()
    local src = source
    local player = NDCore.getPlayer(src)
    if not player then return end
    if player.cash < PRICE then return player.notify({ type = 'error', description = 'Not enough cash' }) end
    if not exports.ox_inventory:CanCarryItem(src, 'sandwich', 1) then return end
    player.deductMoney('cash', PRICE, 'sandwich')
    exports.ox_inventory:AddItem(src, 'sandwich', 1)
end)
```
### Client API
`NDCore.getPlayer()` (local cached character), `getCharacters()`, `getPlayersFromCoords(distance?, coords?)`, `getConfig(key?)`, `notify(...)`, `createAiPed(info, cb)`, `removeAiPed(id)`.

### Events
Server (local): `ND:characterLoaded` (character), `ND:characterUnloaded` (src, character), `ND:updateCharacter` (character, key), `ND:moneyChange` (src, account, amount, `'add'|'remove'|'set'`, reason), `ND:groupAdded` / `ND:groupRemoved` (character, group).
Client: `ND:characterLoaded` (character), `ND:characterUnloaded`, `ND:updateCharacter` (character), `ND:updateMoney` (cash, bank), `ND:updateLastLocation`, `ND:revivePlayer`, `ND:groupsUpdated`.

### Config (convars, read with `GetConvar` on the server)
`core:serverName`, `core:discordInvite`, `core:characterIdentifier` (default `license`), `core:admins` (JSON), `core:adminDiscordRoles`, `core:groupRoles`, `core:discordGuildId`, `core:discordBotToken`, `core:compatibility` (JSON, e.g. `["qb","esx"]` enables the partial QB/ESX shims in `compatibility/`), `core:useInventoryForKeys`, `core:platePattern`, `core:randomUnlockedVehicleChance`. Put `core:discordBotToken` in server.cfg with **`set`**, never `setr`/`sets`.

## 3. vRP classic
Repo https://github.com/vRP-framework/vRP (MIT). `master` = **vRP 2** (OOP, extensions); tag `1.0` (2018) = vRP 1 API that most forks copy. Docs: https://vrp-framework.github.io/vRP (also `doc/` in repo). Last push 2025-05-15 (deleted a `modules` directory); manifest still `fx_version "adamant"` and a `__resource.lua` — expect to modernise (`cerulean`, oxmysql DB driver) before use. Not recommended for new servers.

### Proxy and Tunnel (both versions)
```lua
-- fxmanifest.lua of your resource: include vRP's utils on each side that uses it
-- server_scripts { '@vrp/lib/utils.lua', 'server.lua' }  client_scripts { '@vrp/lib/utils.lua', 'client.lua' }
local Proxy  = module('vrp', 'lib/Proxy')
local Tunnel = module('vrp', 'lib/Tunnel')
local vRP = Proxy.getInterface('vRP')          -- server-side vRP API (cross-resource calls)
```
- **Proxy** = resource ↔ resource (server-server or client-client) via events; `Proxy.addInterface(name, table)`, `Proxy.getInterface(name, identifier?)`.
- **Tunnel** = server ↔ client; `Tunnel.bindInterface(name, table)`, `Tunnel.getInterface(name, identifier?)`, `Tunnel.setDestDelay(dest, ms)`. Calling `iface.fn(...)` waits for the result; `iface._fn(...)` (underscore) is fire-and-forget.
- **Security:** every server function exposed with `Tunnel.bindInterface` is a net event any client can call with any arguments. Validate `source` → `user_id`, permissions and values in each one — tunnel functions are a classic money/item exploit vector.

### vRP 1 API (tag 1.0; basis of vRPEX/Creative)
```lua
local user_id = vRP.getUserId(source)                   -- nil if not loaded
local src = vRP.getUserSource(user_id) ; local users = vRP.getUsers()   -- { [user_id] = source }
vRP.getMoney(uid) ; vRP.setMoney(uid, v) ; vRP.giveMoney(uid, n) ; vRP.tryPayment(uid, n)   -- wallet
vRP.getBankMoney(uid) ; vRP.giveBankMoney(uid, n) ; vRP.tryWithdraw(uid, n) ; vRP.tryDeposit(uid, n) ; vRP.tryFullPayment(uid, n)
vRP.giveInventoryItem(uid, idname, amount, notify) ; vRP.tryGetInventoryItem(uid, idname, amount, notify)
vRP.getInventoryItemAmount(uid, idname) ; vRP.getInventoryWeight(uid) ; vRP.getInventoryMaxWeight(uid) ; vRP.defInventoryItem(idname, name, desc, choices, weight)
vRP.hasPermission(uid, perm) ; vRP.hasGroup(uid, group) ; vRP.addUserGroup(uid, g) ; vRP.removeUserGroup(uid, g) ; vRP.getUsersByPermission(perm)
vRP.getUData(uid, key, cb) ; vRP.setUData(uid, key, value) ; vRP.getSData(key, cb) ; vRP.setSData(key, value)
vRP.prepare(name, sql) ; vRP.query(name, params, mode) ; vRP.execute(name, params) ; vRP.scalar(name, params)
vRP.kick(source, reason) ; vRP.ban(source, reason) ; vRP.isBanned(uid, cb) ; vRP.isWhitelisted(uid, cb)
```
### vRP 2 (master)
Scripts run inside the vRP context: `vRP.loadScript('my_resource', 'vrp')` loads `my_resource/vrp.lua`, which defines an extension:
```lua
local MyExt = class('MyExt', vRP.Extension)
MyExt.event, MyExt.proxy, MyExt.tunnel = {}, {}, {}
function MyExt.event:playerSpawn(user, first_spawn) end
vRP:registerExtension(MyExt)
```
Users are objects: `vRP.users_by_source[source]` → `user`; money `user:getWallet()`, `user:giveWallet(n)`, `user:tryPayment(n, dry)`, `user:getBank()`, `user:tryWithdraw/tryDeposit/tryFullPayment`; inventory `user:tryGiveItem(fullid, n, dry, no_notify)`, `user:tryTakeItem(...)`, `user:getItemAmount(fullid)`; groups `user:hasGroup(g)`, `user:addGroup(g)`, `user:hasPermission(perm)`. Other extensions: `vRP.EXT.Money`, `vRP.EXT.Inventory`, ... (see `doc/dev/modules/*.adoc`).

## 4. vRP Creative / vRPEX
Brazilian vRP 1 derivatives (vRPEX, "Creative" v3–v5 and newer "Creative Network" bases) are distributed outside GitHub, often paid and sometimes obfuscated; there is no canonical source or docs. Patterns that are common but **UNVERIFIED for any specific base**: `vRP.getUserId(source)`/`vRP.Passport(source)`, `vRP.giveMoney`, `vRP.PaymentFull`/`vRP.paymentFull`, `vRP.giveInventoryItem`/`vRP.GiveItem`, `vRP.tryGetInventoryItem`/`vRP.TakeItem`, `vRP.hasPermission`/`vRP.HasGroup`, `vRP.getInformation`, plus `vRPC = Tunnel.getInterface('vRP')` for client calls. Names and casing change between versions: **read the server's `vrp/modules/*.lua` (or equivalent) before writing code**, keep the user's naming, and never assume a function exists. Also check for leaked/obfuscated code and license issues ([licensing-and-policy.md](licensing-and-policy.md)). Community skill with Creative/vRPEX coverage: https://github.com/proelias7/fivem-skill (third party).

## 5. Standalone
No framework: ox_lib + oxmysql + your own tables keyed by `license` (from `GetPlayerIdentifierByType(src, 'license')`), ACE for permissions (`IsPlayerAceAllowed`), state bags for synced flags. Good for utilities, maps, HUDs, admin tools and resources sold to multiple frameworks (pair with a bridge, §6).

## 6. Bridges for multi-framework resources
Prefer a small in-resource bridge ([framework-bridge.md](framework-bridge.md)). Third-party bridges that resource authors depend on (verify the user has them installed):
| Bridge | Repo | Version (2026-10-07) | Covers |
|---|---|---|---|
| community_bridge | https://github.com/TheOrderFivem/community_bridge (GPL-3.0) | 0.13.6 (2026-08-14) | QBCore, ESX, targets, locks, fuel, clothing... |
| Renewed-Lib | https://github.com/Renewed-Scripts/Renewed-Lib (GPL-3.0) | 2.0.7 (2025-01; push 2025-11) | qbcore, qbox, esx, ox, ndcore (needs ox_lib) |
| jim_bridge | https://github.com/jimathy/jim_bridge (no license file) | v2.1.09 (2025-11; push 2026-03) | required by jim-* scripts |

## 7. Choosing a stack for a new server (2026)
| Need | Recommended default |
|---|---|
| Framework | **Qbox** (active, ox-native, QB-compatible) or **ESX Legacy 1.15** (big ecosystem). QBCore only if the community/scripts require it; ox_core for developers who want a lean TS/Lua core; ND_Core for small ox-based servers; avoid vRP for new servers unless the community is vRP-only |
| Library / DB | ox_lib · oxmysql + MariaDB |
| Inventory / target | ox_inventory · ox_target |
| Voice / phone / appearance | pma-voice · npwd (free) or lb-phone (paid) · illenium-appearance |
| Logs / screenshots | Fivemanage SDK or `lib.logger` · screencapture |
| Server | FXServer Legacy Recommended (35245); evaluate Enhanced (Cfx Server) only for testing |
Always respect the user's existing stack over these defaults. Category-by-category "use vs avoid": [ecosystem-resources.md](ecosystem-resources.md).

## Sources
- https://github.com/ND-Framework/ND_Core (init.lua, fxmanifest.lua, server/{main,functions,player,groups,vehicle}.lua, client/{functions,events}.lua, compatibility/, database/) · https://github.com/ND-Framework/ND_Core/releases
- https://ndcore.dev · https://ndcore.dev/core
- https://github.com/vRP-framework/vRP (README.adoc, doc/dev/index.adoc, doc/dev/modules/{money,inventory,group}.adoc, vrp/fxmanifest.lua; tag 1.0: vrp/base.lua, vrp/modules/{money,inventory,group}.lua, vrp/lib/Tunnel.lua) · https://vrp-framework.github.io/vRP
- https://github.com/Qbox-project/qbx_core/releases · https://github.com/esx-framework/esx_core · https://github.com/overextended/ox_core
- https://github.com/TheOrderFivem/community_bridge · https://github.com/Renewed-Scripts/Renewed-Lib · https://github.com/jimathy/jim_bridge
- https://github.com/proelias7/fivem-skill
