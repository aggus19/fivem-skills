# ox_core reference

Baseline: ox_core v1.5.14 (released 2026-05-29) — verified 2026-10-07 against the source and overextended.dev docs. `main` has unreleased commits up to 2026-08-17 (accounts transaction integrity, invoice-created event, cached `OxAccount.get`, `player.getState` fix).

Repo https://github.com/overextended/ox_core (LGPL-3.0) · npm `@overextended/ox_core` 1.5.14 · Docs https://overextended.dev/docs/ox_core

## Contents
1. Architecture and install
2. Convars
3. Using ox_core from Lua and TypeScript
4. Server functions (`Ox.*`)
5. OxPlayer (server and client)
6. Groups, grades, permissions
7. OxVehicle
8. OxAccount (banking, invoices)
9. Events
10. Global state bags
11. Database schema
12. Commands
13. Changes 2024–2026
14. Sources

## 1. Architecture and install
- Written in **TypeScript** (Node 22 runtime, `metadata node_version '22'`), built with bun; generated manifest requires `/server:12913` and `/onesync`. Download the release zip or `git clone … && bun i && bun run build`.
- Talks to the database **directly through the `mariadb` npm driver** (not oxmysql), using `mysql_connection_string`. **Requires MariaDB ≥ 11.4** — MySQL is rejected at startup ("MySQL x is not supported"). ox_core checks **ox_lib ≥ 3.24.0** at start; oxmysql is not used by ox_core itself but the docs list it because ox_inventory/ox_doorlock need it.
- Ships the schema in `sql/install.sql` (database name `overextended` by default) and runs schema updates at start.
- Recommended stack: ox_lib, oxmysql, ox_inventory (`setr inventory:framework "ox"`), ox_target, ox_doorlock, ox_banking; txAdmin recipe https://github.com/overextended/txAdminRecipe.
- Character data lives on the server in `OxPlayer` instances; clients get a light `OxPlayer` that mirrors replicated keys.
- Third-party resources must not use the `ox_` prefix (overextended naming convention).

```cfg
ensure oxmysql
ensure ox_lib
ensure ox_core
ensure ox_target
ensure ox_inventory
```

## 2. Convars
| Convar | Default | Side | Meaning |
|---|---|---|---|
| `ox:debug` | `0` | setr | debug commands/messages; allows duplicate identifiers; forced on with `sv_lan 1` or `bun watch` |
| `ox:characterSlots` | `1` | setr | slots for character select resources |
| `ox:plateFormat` | `"........"` | setr | plate pattern (uppercased) — see `SET_DEFAULT_VEHICLE_NUMBER_PLATE_TEXT_PATTERN` |
| `ox:defaultVehicleStore` | `"impound"` | setr | where previously spawned vehicles are stored on start (`""` = don't touch DB) |
| `ox:deathSystem` | `1` | setr | built-in death/respawn (state `isDead` + `ox:playerDeath` always fire) |
| `ox:hospitalBlips` | `1` | setr | hospital blips for the death system |
| `ox:characterSelect` | `1` | setr | built-in character registration/selection |
| `ox:spawnLocation` | `[-258.211, -293.077, 21.6132, 206.0]` | setr | spawn for new characters (x, y, z, heading) |
| `ox:createDefaultAccount` | `1` | set | create a personal bank account for new characters (source only; not in docs) |
| `sv_protectServerEntities` | `false` | set | read by ox_core to decide vehicle cleanup strategy |

## 3. Using ox_core from Lua and TypeScript
```lua
-- fxmanifest.lua
shared_script '@ox_lib/init.lua'
shared_script '@ox_core/lib/init.lua'   -- or: local Ox = require '@ox_core.lib.init'
```
- The Lua lib exposes a global `Ox`; unknown keys forward to `exports.ox_core:<Name>`. `Ox.GetGroup(name)` reads `GlobalState['group.<name>']`.
- Class methods are pre-bound, so call them with a **dot**: `player.getGroup('police')` (colon also works).
- Methods that hit the database (`setGroup`, `addLicense`, `createCharacter`, account operations…) are async in TS; from Lua call them inside an event handler/thread. Exact yielding semantics of the JS-promise → Lua export bridge are **UNVERIFIED** here — check return values instead of assuming success.
- TypeScript: `bun i @overextended/ox_core`, then `import { GetPlayer } from '@overextended/ox_core/server'` (package exports `.`, `./client`, `./server`).

## 4. Server functions (`Ox.*`)
| Function | Returns |
|---|---|
| `GetPlayer(source)` / `GetPlayerFromUserId(userId)` / `GetPlayerFromCharId(charId)` | OxPlayer or nil |
| `GetPlayers(filter?)` / `GetPlayerFromFilter(filter?)` | OxPlayer[] / OxPlayer — filter matches fields/metadata; `groups` may be a name or array |
| `GetCharIdFromStateId(stateId)` | number |
| `CreateVehicle(data, coords?, heading?)` | OxVehicle — `data` = model string or `{ model, owner? (charId), group?, stored?, properties? }`; owned/grouped vehicles persist |
| `SpawnVehicle(dbId, coords, heading?)` | OxVehicle from DB |
| `GetVehicle(entity)` / `GetVehicleFromEntity` / `GetVehicleFromNetId` / `GetVehicleFromVin` / `GetVehicles(filter?)` / `GetVehicleFromFilter(filter?)` | OxVehicle(s) |
| `GenerateVehiclePlate(pattern?)` / `GenerateVehicleVin(model)` | string |
| `GetVehicleData(filter?)` / `GetTopVehicleStats(category?)` / `GetVehicleNetworkType(model)` | shared vehicle data (`class, doors, make, name, price, seats, type, weapons?`) |
| `CreateGroup({ name, label, grades, type?, colour?, hasAccount? })` / `DeleteGroup(name)` | dynamic groups |
| `GetGroup(name)` / `GetGroupsByType(type)` / `GetGroupActivePlayers(name)` / `GetGroupActivePlayersByType(type)` | group data / names / player ids |
| `GetGroupPermissions(name)` / `SetGroupPermission(group, grade, perm, 'allow'\|'deny')` / `RemoveGroupPermission(group, grade, perm)` | permissions |
| `GetAccount(id)` / `GetCharacterAccount(charIdOrStateId)` / `GetGroupAccount(group)` / `CreateAccount(ownerId, label)` | OxAccount |
| `DeleteAccountInvoice(id)` / `PayAccountInvoice` (export) | `{ success, message? }` |
| `GetLicense(name)` / `GetLicenses()` | license data |
| `BanUser(userId, reason?, hours?)` / `UnbanUser(userId)` / `IsUserBanned(userId)` | bool / `{ reason, banned_at, unban_at, userId, token }` (ban system since 1.5.10) |
| `SaveAllPlayers()` / `SaveAllVehicles()` | — |

## 5. OxPlayer
Server fields: `source`, `userId`, `charId` (nil before a character is selected), `stateId` (short public id), `identifier`, `username`, `ped`.
Server methods: `get(key)`, `set(key, value, replicated?)` (replicated → visible to that client via `player.get`), `emit(event, ...)` (TriggerClientEvent to this player), `getCoords()`, `getState()`, `save()`, `logout(save?, dropped?)`, `getGroup(filter)`, `getGroupByType(type)`, `getGroups()`, `setGroup(name, grade?)`, `setActiveGroup(name?, temporary?)`, `hasPermission(perm)`, `getStatus/getStatuses/setStatus/addStatus/removeStatus`, `getLicense/getLicenses/addLicense/removeLicense/updateLicense(name, key, value)`, `getAccount()`, `payInvoice(id)`, `createCharacter({ firstName, lastName, gender, date })`, `setActiveCharacter(charIdOrData)`, `deleteCharacter(charId)`.

Client (`Ox.GetPlayer()` — a singleton): `userId`, `charId`, `stateId`, `state` (LocalPlayer.state), `get(key)` (cached + auto-updated), `on(key, cb)`, `getCoords()`, `getGroup`, `getGroupByType`, `getGroups`, `hasPermission`, `getStatus(es)`, `addStatus`, `removeStatus`.

```lua
-- server.lua
local Ox = require '@ox_core.lib.init'

RegisterNetEvent('myres:server:payFine', function(amount)
    local src = source
    local player = Ox.GetPlayer(src)
    if not player or not player.charId then return end
    if type(amount) ~= 'number' or amount <= 0 or amount > 5000 then return end
    if not player.getGroup('police') then return end          -- returns grade or nil

    local account = player.getAccount()
    if not account then return end
    local result = account.removeBalance({ amount = amount, message = 'Fine' })
    if not result.success then
        return player.emit('ox_lib:notify', { type = 'error', description = result.message })
    end
end)

AddEventHandler('ox:playerLoaded', function(playerId, userId, charId)
    local player = Ox.GetPlayer(playerId)
    print(('%s loaded character %s (%s)'):format(player.username, charId, player.stateId))
end)
```
```lua
-- client.lua
local Ox = require '@ox_core.lib.init'
local player = Ox.GetPlayer()

AddEventHandler('ox:playerLoaded', function(playerId, isNew)
    local name, grade = player.getGroupByType('job')
    print(name, grade)
end)
```

## 6. Groups, grades, permissions
- Groups are rows in `ox_groups` + grades in `ox_group_grades`; a group has `type` (e.g. `job`, `gang`): **a character can hold only one group of each type** (`setGroup` warns "already has group of type").
- `setGroup(name, grade)`: grade `0`/nil removes the group; invalid grades are rejected. `getGroup('police')` → grade; `getGroup({ police = 2, sheriff = 1 })` / `getGroup({ 'police', 'sheriff' })` → `name, grade` of the first match (min grade for the map form).
- Active group (`setActiveGroup`) drives `<name>:activeCount` globals and duty-style logic; `ox:setActiveGroup(playerId, name, previous)` fires.
- ACE: each group creates principal `group.<name>`, grades `group.<name>:<grade>` inheriting from lower grades; the player is added to `group.<name>:<grade>` — so `IsPlayerAceAllowed` and ox_lib `restricted = 'group.police'` work.
- Permissions: `Ox.SetGroupPermission('police', 1, 'handcuff', 'allow')`, then `player.hasPermission('group.police.handcuff')` (or the bare permission).

## 7. OxVehicle
Fields: `entity`, `netId`, `model`, `make`, `plate`, `id?` (DB id), `vin?`, `owner?` (charId), `group?`.
Methods: `get(key)`, `set(key, value)`, `getCoords()`, `getState()`, `getProperties()`, `setProperties(props, apply?)`, `getStored()`, `setStored(value?, despawn?)`, `setOwner(charId?)`, `setGroup(name?)`, `setPlate(plate)`, `save()`, `despawn(save?)`, `respawn(coords?, rotation?)`, `delete()`.
```lua
local Ox = require '@ox_core.lib.init'
local vehicle = Ox.CreateVehicle({ model = 'sultan', owner = player.charId }, vec3(-50.0, -1110.0, 26.4), 70.0)
vehicle.setStored('garage_legion', true)   -- store and despawn
```
Since 1.5.10 vehicles can exist without an entity and vehicle data parsing emits events you can hook to transform data.

## 8. OxAccount (banking, invoices)
Metadata: `id, balance, isDefault, label, owner?, group?, type ('personal'|'shared'|'group')`. Methods: `get(key|keys)`, `addBalance({ amount, message? })`, `removeBalance({ amount, message?, overdraw? })`, `transferBalance({ toId, amount, message?, note?, overdraw?, actorId? })`, `depositMoney(playerId, amount, message?, note?)` / `withdrawMoney(...)` (move cash item ↔ account), `deleteAccount()`, `getCharacterRole(id)`, `setCharacterRole(id, role?)`, `playerHasPermission(playerId, perm)`, `setShared()`, `createInvoice({ actorId?, toAccount, amount, message, dueDate })`. Most return `{ success, message? }` (e.g. `'no_balance'`, `'insufficient_funds'`, `'no_access'`). Roles and their permissions live in `account_roles` and `GlobalState['accountRole.<name>']`.

## 9. Events
Server (listen only): `ox:playerLoaded(playerId, userId, charId)`, `ox:playerLogout(playerId, userId, charId)`, `ox:createdCharacter(...)`, `ox:deletedCharacter(...)`, `ox:setGroup(playerId, group, grade?)`, `ox:setActiveGroup(playerId, group, previous?)`, `ox:licenseAdded/licenseRemoved(playerId, name)`, `ox:savedPlayers(count)` (every 10 min, shutdown, `SaveAllPlayers`, `saveplayers`), `ox:savedVehicles(count)`, `ox:spawnedVehicle(entityId, id)`, `ox:despawnVehicle(entityId, id)`, `ox:updatedBalance({ accountId, amount, action })`, `ox:transferredMoney`, `ox:depositedMoney`, `ox:withdrewMoney`, `ox:invoicePaid` (+ an invoice-created event on `main`, unreleased).
Client: `ox:playerLoaded(playerId, isNew?)`, `ox:statusTick(statuses)`, `ox:playerDeath`, `ox:playerRevived`; net events `ox:setGroup(name, grade?)`, `ox:licenseAdded/Removed(name)`, `ox:startCharacterSelect`, `ox:setActiveCharacter`. Never trigger them yourself.

## 10. Global state bags (read-only)
`GlobalState.groups` (names), `group.<name>` (`{ name, label, grades, type, hasAccount, accountRoles, principal }`), `<name>:count`, `<name>:activeCount`, `status.<name>` (`{ name, default, onTick }`), `license.<name>`, `accountRoles`, `accountRole.<name>` (deposit/withdraw/addUser/removeUser/manageUser/transferOwnership/viewHistory/manageAccount/closeAccount/sendInvoice/payInvoice flags). Player state `isDead` is set by the death system. ox_core 1.5.13+ supports `sv_stateBagStrictMode`.

## 11. Database schema (`sql/install.sql`)
`users(userId, username, license2, steam, fivem, discord)` · `characters(charId, userId, stateId, firstName, lastName, fullName (generated), gender, dateOfBirth, phoneNumber, lastPlayed, isDead, x, y, z, heading, health, armour, statuses JSON, deleted)` · `character_inventory(charId, inventory JSON)` · `ox_groups(name, label, type, colour, hasAccount)` · `ox_group_grades` · `character_groups(charId, name, grade, isActive)` · `ox_inventory(owner, name, data, lastupdated)` · `vehicles(id, plate CHAR(8), vin CHAR(17), owner, group, model, class, data JSON, trunk, glovebox, stored)` · `ox_statuses(name, default, onTick)` (hunger/thirst/stress seeded) · `ox_licenses` · `character_licenses` · `accounts` · `account_roles` · `accounts_access` · `accounts_transactions` · `accounts_invoices`. Foreign keys cascade from `characters`/`ox_groups`. Characters are soft-deleted (`deleted` date).

## 12. Commands
`/logout`, `/deletechar` (hard delete current character), `/charinfo`, `/setgroup <target> <group> [grade]` (grade 0 removes), `/reloadgroups`, `/reloadlicenses`, `/reloadstatuses`, `/car <model> [owner]`, `/dv [radius] [owned]`, `/saveall` (players + vehicles), console `saveplayers`, plus a vehicle-data parser command. Admin commands use `restricted = 'group.admin'`.

## 13. Changes 2024–2026
- v1.0.0 (2024-10-18): first stable after 0.x pre-releases; dynamic group create/delete, `GetGroupsByType`, `activeCount` state; some lib/server exports removed.
- v1.1.0 → 1.3.0 (2024-10 → 2025-01): `getProperties`, character gender, `GetLicense(s)`, `ox:despawnVehicle`.
- v1.4.0 (2025-02): `ox:defaultVehicleStore`. v1.5.0 (2025-02): **Node 22**, account transaction events, hospital blips.
- v1.5.10 (2026-04-24, first release from overextended after CommunityOx): **ban system**, `GetGroupPermissions`, `GetGroupActivePlayers(ByType)`, `GetPlayerFromCharId`, vehicle get-all/filter, custom plate pattern, `previousGroupName` in `ox:setActiveGroup`, status clamping, `/setgroup` restricted.
- v1.5.12–1.5.14 (2026-05): strict state bag support, type fixes.
- `main` after 1.5.14 (unreleased): transaction rollback/integrity in accounts, invoice-created event, `/dv` and entity cleanup changes (`sv_protectServerEntities`).

## 14. Sources
- https://github.com/overextended/ox_core (v1.5.14: `lib/init.lua`, `lib/server/{player,vehicle,account}.lua`, `lib/client/player.lua`, `common/config.ts`, `server/config.ts`, `client/config.ts`, `server/db/{pool,config}.ts`, `server/player/class.ts`, `server/groups/index.ts`, `sql/install.sql`, `package.json`, `build.js`)
- https://github.com/overextended/ox_core/releases and commits API (`commits?since=2026-05-30`)
- https://overextended.dev/docs/ox_core and source https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_core (index, States, Functions/common, Functions/server, Classes/Server/OxPlayer, OxVehicle, OxAccount, Classes/Client/OxPlayer, Events/server, Events/client)
- https://www.npmjs.com/package/@overextended/ox_core
