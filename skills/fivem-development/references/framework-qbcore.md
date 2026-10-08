# QBCore (qb-core) — complete reference

Baseline: qb-core **1.3.0** (fxmanifest; no GitHub releases), last code commit 2026-06-17, repo push 2026-08-25 — verified 2026-10-07 against the source in `qbcore-fivem/qb-core@main`.
Repo **https://github.com/qbcore-fivem/qb-core** (old `qbcore-framework/*` URLs redirect) · Docs https://qbcore.org/docs (index: https://qbcore.org/docs/llms.txt; append `.md` to any page) · License GPL-3.0.
Status: maintained, slow. A large refactor landed **2026-04/05** (see §11). For new servers Qbox is usually the better choice ([framework-qbox.md](framework-qbox.md)); for existing QBCore servers, match what is installed and check `version` in their `qb-core/fxmanifest.lua` and the commit date — many servers run 2023–2024 forks with a different event model.

## Contents
1. Getting the core (object, filters, direct exports)
2. Server functions (`QBCore.Functions.*`)
3. Player object (`Player.Functions.*`) and PlayerData schema
4. Client functions
5. Callbacks
6. Events (server and client)
7. Commands and permissions
8. Shared data (items, jobs, gangs, vehicles, weapons) and runtime exports
9. Config (`QBCore.Config`)
10. QB resources: qb-inventory, qb-target, qb-menu, qb-input, qb-banking/qb-management, multicharacter/spawn/apartments, qb-phone, PolyZone, progressbar, others
11. Breaking changes 2024–2026
12. Best practices and common mistakes
13. qbcore-fivem repository list
Sources

## 1. Getting the core
```lua
-- Full object (works everywhere; heavy: every resource gets a msgpack copy of Shared)
local QBCore = exports['qb-core']:GetCoreObject()

-- Filtered (1.3.0+, recommended by the docs): only the keys you need
local QBCore = exports['qb-core']:GetCoreObject({ 'Functions', 'Shared' })
-- valid keys: Config, Shared, ClientCallbacks, ServerCallbacks, PlayerData, Functions,
--             Players, PlayersByCitizenId, Player_Buckets, Entity_Buckets, UsableItems, Commands

-- Direct exports (1.3.0+): every QBCore.Functions.* is also an export on its side
local Player = exports['qb-core']:GetPlayer(src)                 -- server
local items  = exports['qb-core']:GetShared('Items')              -- shared; 'Vehicles'|'VehicleHashes'|'Items'|'Gangs'|'Jobs'|'Locations'|'Weapons'|'StarterItems'
local bread  = exports['qb-core']:GetShared('Items', 'sandwich')  -- single entry or nil
local ver    = exports['qb-core']:GetCoreVersion()               -- '1.3.0'
```
Official qb-* resources switched to `GetShared(...)` / direct exports in 2026-05 ("Don't import whole core").
If you keep a full copy, refresh it when shared data changes at runtime:
```lua
RegisterNetEvent('QBCore:Client:UpdateObject', function() QBCore = exports['qb-core']:GetCoreObject() end) -- client
AddEventHandler('QBCore:Server:UpdateObject', function() QBCore = exports['qb-core']:GetCoreObject() end)  -- server
```
Never call `GetCoreObject()` per event or inside loops.

## 2. Server functions (`QBCore.Functions.*`, server)
Getters
| Function | Returns / notes |
|---|---|
| `GetPlayer(source)` | Player or nil. Accepts number, numeric string, or an identifier string (scans online players) |
| `GetPlayerByCitizenId(cid)` | online Player or nil (indexed lookup) |
| `GetOfflinePlayerByCitizenId(cid)` | Player built from DB (`Offline = true`), or nil |
| `GetPlayerByLicense(license)` | online Player, else offline Player from DB |
| `GetPlayerByPhone(number)` / `GetPlayerByAccount(acc)` / `GetPlayerByCharInfo(prop, value)` | online scan |
| `GetPlayers()` | array of sources (online, logged in) |
| `GetQBPlayers()` | `{ [source] = Player }` |
| `GetPlayersByJob(jobOrType, checkOnDuty)` | `sources, count` — matches `job.name` **or** `job.type` (e.g. `'leo'`) |
| `GetPlayersOnDuty(job)` | `sources, count` |
| `GetDutyCount(job)` | number |
| `GetIdentifier(source, idtype?)` | `GetPlayerIdentifierByType` wrapper, default `'license'` |
| `GetSource(identifier)` | source or `0` |
| `GetCoords(entity)` | `vector4` |
| `GetClosestPlayer(source, coords?)` / `GetClosestObject` / `GetClosestVehicle` / `GetClosestPed` | `entityOrId, distance` (`-1, -1` if none) |
| `GetDatabaseInfo()` | `{ exists, database }` from `mysql_connection_string` |

Vehicles (server-side creation)
| Function | Notes |
|---|---|
| `CreateVehicle(source, model, vehtype, coords?, warp?)` | **Preferred.** `CreateVehicleServerSetter`; `vehtype` = `'automobile'|'bike'|'boat'|'heli'|'plane'|'submarine'|'trailer'|'train'` (from vehicles.meta / `QBCore.Shared.Vehicles[model].type`) |
| `SpawnVehicle(source, model, coords?, warp?)` | `CreateVehicle` RPC — needs the player nearby; waits for ownership |
| `CreateAutomobile(source, model, coords?, warp?)` | `CREATE_AUTOMOBILE` (automobiles only) |

Routing buckets: `SetPlayerBucket(src, bucket)` (also sets `Player(src).state.instance`), `SetEntityBucket(entity, bucket)`, `GetPlayersInBucket(b)`, `GetEntitiesInBucket(b)`, `GetBucketObjects()`.

Items: `CreateUseableItem(name, function(source, item) end)`, `CanUseItem(name)`, `UseItem(source, item)` (delegates to qb-inventory), `HasItem(source, items, amount)` (**deprecated** — use `exports['qb-inventory']:HasItem`). Usable items registered by a resource are removed when it stops.

Permissions / admin: `HasPermission(src, perm|perms[])` (pure ACE: `IsPlayerAceAllowed`), `GetPermission(src)` (map of `Config.Server.Permissions` the player has), `AddPermission(src, perm)` / `RemovePermission(src, perm?)` (runtime `add_principal player.<src> qbcore.<perm>` — **not persisted**), `IsWhitelisted(src)`, `IsOptin(src)` / `ToggleOptin(src)`, `IsPlayerBanned(src)` (`bans` table), `IsLicenseInUse(license)`, `Kick(src, reason, setKickReason?, deferrals?)`, `Notify(src, text, type?, length?)`.

Runtime shared editing (server only; broadcast to clients and fire `QBCore:Server/Client:UpdateObject`): `AddJob(name, job)`, `AddJobs(tbl)`, `UpdateJob`, `RemoveJob`, `AddItem(name, item)` (**this adds an item definition, not an item to a player**), `AddItems`, `UpdateItem`, `RemoveItem`, `AddGang`, `AddGangs`, `UpdateGang`, `RemoveGang`, `SetMethod(name, fn)`, `SetField(name, data)`. All return `ok, 'success'|'job_exists'|'invalid_job_name'|...`.

Player-object extension: `AddPlayerMethod(ids, name, fn)`, `AddPlayerField(ids, name, data)` — `ids` = source, `-1` (all online), or array. Other: `CreatePhoneNumber()`, `CreateAccountNumber()`, `GetCoreVersion()`, export `ExploitBan(src, origin)` (permanent ban row + drop).

Lower level (`QBCore.Player.*`): `Login(src, citizenid|false, newData?)`, `Logout(src)`, `Save(src)`, `SaveOffline(PlayerData)`, `DeleteCharacter(src, cid)` (checks license), `ForceDeleteCharacter(cid)`, `CheckPlayerData`, `CreateCitizenId()`, `CreateFingerId()`, `CreateWalletId()`, `CreateSerialNumber()`.

## 3. Player object and PlayerData
```lua
-- server
local src = source
local Player = QBCore.Functions.GetPlayer(src)        -- or exports['qb-core']:GetPlayer(src)
if not Player then return end
local pd = Player.PlayerData
```
Since 2026-05 the player is a metatable class; `Player.Functions.X(...)` still works (wrappers), and the export interface also exposes methods at top level (`Player.SetPlayerData(...)`).

Internally methods are defined as `function Player:AddMoney(...)`, but **from another resource always use the dot form** (`Player.Functions.AddMoney('cash', 5)` or, on the `exports['qb-core']:GetPlayer(src)` interface, `Player.AddMoney('cash', 5)`). Those are pre-bound wrappers (`buildMethodTable`/`buildInterface` in `server/player.lua`); calling them with a colon passes the table as the first argument (`moneytype`) and errors, and metatable methods do not survive the export boundary. Source: https://github.com/qbcore-fivem/qb-core/blob/main/server/player.lua

| `Player.Functions.*` | Notes |
|---|---|
| `AddMoney(type, amount, reason?)` | `true`; `false` unknown type; `nil` if amount < 0/invalid. Fires `QBCore:Server:OnMoneyChange`, client `QBCore:Client:OnMoneyChange`, `hud:client:OnMoneyChange`, `qb-log` |
| `RemoveMoney(type, amount, reason?)` | `false` if it would go below 0 for `Config.Money.DontAllowMinus` types or below `MinusLimit` (-5000) |
| `SetMoney(type, amount, reason?)` / `GetMoney(type)` | |
| `SetJob(name, grade)` / `SetGang(name, grade)` | `false` if job/gang not in Shared; grade looked up as `tostring(grade)` |
| `SetJobDuty(bool)` | |
| `SetMetaData(key, val)` / `GetMetaData(key)` | hunger/thirst clamped 0–100 |
| `AddRep(k, n)` / `RemoveRep(k, n)` / `GetRep(k)` | `metadata.rep` |
| `SetPlayerData(key, val)` | sets top-level field and syncs that key |
| `UpdateClient(key?, val?)` (alias `UpdatePlayerData`) | partial sync; no key = full sync |
| `GetPlayerData()`, `GetName()`, `Notify(text, type, len)`, `HasItem(items, amount)` | |
| `Save()`, `Logout()` | offline players: `Save()` → `SaveOffline` |
| `AddMethod(name, fn)`, `AddField(name, data)` | per-player extension |
| **added by qb-inventory** at load: `AddItem(item, amount, slot?, info?, reason?)`, `RemoveItem(item, amount, slot?, reason?)`, `GetItemBySlot(slot)`, `GetItemByName(name)`, `GetItemsByName(name)`, `ClearInventory(filter?)`, `SetInventory(items)` | absent if qb-inventory is not running |

PlayerData (defaults from `config.lua` `PlayerDefaults`; DB columns are JSON text):
```lua
{
  source, license, name,                     -- name = FiveM name
  citizenid = 'ABC12345', cid = 1, optin = true,
  money    = { cash = 500, bank = 5000, crypto = 0 },          -- from Config.Money.MoneyTypes
  charinfo = { firstname, lastname, birthdate, gender = 0, nationality, phone, account },
  job  = { name = 'unemployed', label, type = 'none'|'leo'|'ems'|..., onduty, isboss,
           grade = { name, level, payment, isboss } },
  gang = { name = 'none', label, isboss, grade = { name, level, isboss } },
  metadata = {
    hunger = 100, thirst = 100, stress = 0, isdead = false, inlaststand = false, armor = 0,
    ishandcuffed = false, tracker = false, injail = 0, jailitems = {}, status = {}, phone = {},
    rep = {}, currentapartment = nil, callsign = 'NO CALLSIGN', bloodtype, fingerprint, walletid,
    criminalrecord = { hasRecord = false, date = nil },
    licences = { driver = true, business = false, weapon = false },   -- spelled "licences"
    inside = { house = nil, apartment = { apartmentType = nil, apartmentId = nil } },
    phonedata = { SerialNumber, InstalledApps = {} },
  },
  position = vector4, items = { [slot] = { name, amount, info, label, weight, type, unique, useable, image, slot, ... } },
}
```
Job pay is `job.grade.payment` (the default unemployed table still has a root `payment = 10`). On login, a job/gang that no longer exists in Shared is reset to the default; with `QBCore.Shared.ForceJobDefaultDutyAtLogin = true` (default) duty is reset to the job's `defaultDuty`.

## 4. Client functions (`QBCore.Functions.*`, client; also exported)
Player: `GetPlayerData(cb?)`, `GetName()`, `HasItem(items, amount)` (→ qb-inventory client export), `GetCoords(entity)`.
UI: `Notify(text|{text, caption}, type?, length?, icon?)` (types from `Config.Notify.VariantDefinitions`: `success|primary|warning|error|police|ambulance`), `Progressbar(name, label, duration, useWhileDead, canCancel, disableControls, animation, prop, propTwo, onFinish, onCancel)` (**errors unless the `progressbar` resource is started**), `DrawText(x, y, w, h, scale, r, g, b, a, text)`, `DrawText3D(x, y, z, text)`.
World: `GetVehicles()`, `GetObjects()`, `GetPeds(ignoreList)`, `GetPlayers()` (active player indices), `GetPlayersFromCoords(coords?, dist=5)`, `GetClosestPlayer(coords?)`, `GetClosestPed(coords?, ignore)`, `GetClosestVehicle(coords?)`, `GetClosestObject(coords?)`, `GetClosestBone(entity, list)`, `GetBoneDistance(entity, boneType, boneIndex)`, `SpawnClear(coords, radius)`, `GetStreetNametAtCoords(coords)` (sic — typo is the real name), `GetZoneAtCoords`, `GetCardinalDirection(entity?)`, `GetCurrentTime()`, `GetGroundZCoord(coords)`, `GetGroundHash(entity)`.
Assets/anim: `LoadModel(model, timeout?)` → `ok, hash`, `RequestAnimDict(dict, timeout?)`, `LoadAnimSet`, `LoadParticleDictionary`, `StartParticleAtCoord(...)`, `StartParticleOnEntity(...)`, `PlayAnim(dict, name, upperbodyOnly, duration)`, `LookAtEntity(entity, timeout, speed)`, `AttachProp(ped, model, boneId, x, y, z, xR, yR, zR, vertex)`, `IsWearingGloves()`.
Vehicles: `SpawnVehicle(model, cb, coords, isnetworked, teleportInto)` (**client-side creation — avoid for persistent/owned vehicles**), `DeleteVehicle(veh)`, `GetPlate(veh)` (trimmed), `GetVehicleLabel(veh)`, `GetVehicleProperties(veh)`, `SetVehicleProperties(veh, props)`.
NUI DrawText exports (override the 2D `DrawText` export name): `exports['qb-core']:DrawText(text, 'left'|'right'|'top')`, `ChangeText`, `HideText`, `KeyPressed`; events `qb-core:client:DrawText` etc.
Client state: `LocalPlayer.state.isLoggedIn` (set on load/unload).

## 5. Callbacks
```lua
-- server (server/main.lua)
QBCore.Functions.CreateCallback('myres:server:getStock', function(source, cb, shopId)
    local src = source
    if type(shopId) ~= 'string' then return cb(nil) end
    cb(Stock[shopId])
end)

-- client: callback style
QBCore.Functions.TriggerCallback('myres:server:getStock', function(stock) end, 'shop1')
-- client: await style (2025-01+; omit the function, must run inside a thread/handler)
local stock = QBCore.Functions.TriggerCallback('myres:server:getStock', 'shop1')
-- gotcha: the pending promise is stored by callback NAME (QBCore.ServerCallbacks[name]); two concurrent calls with the
-- same name on one client overwrite each other. Serialize them, or use lib.callback (qb-core client/functions.lua).

-- server -> client
QBCore.Functions.CreateClientCallback('myres:client:getHeading', function(cb) cb(GetEntityHeading(PlayerPedId())) end) -- client
local heading = QBCore.Functions.TriggerClientCallback('myres:client:getHeading', src)                                  -- server, await style
```
Callbacks have no rate limit or timeout. Client callbacks keyed `name .. source` since 2025-10 (earlier versions collided between players). For portable code, ox_lib `lib.callback` works on QBCore too. Built-in: `QBCore:Server:SpawnVehicle` and `QBCore:Server:CreateVehicle` (return netId) — **any client can call them**; don't leave them reachable on public servers without a wrapper/permission (they spawn arbitrary models).

## 6. Events
Server-side (local `AddEventHandler`):
| Event | Args |
|---|---|
| `QBCore:Server:PlayerLoaded` | `Player` |
| `QBCore:Server:OnPlayerUnload` | `src` (also fired on drop since 2026-05) |
| `QBCore:Server:PlayerDropped` | `src` (**was the Player object before 2026-05**) |
| `QBCore:Server:OnPlayerUpdated` | `src, key, val` (`key = 'all'` → full PlayerData) — new central event |
| `QBCore:Server:OnJobUpdate` / `QBCore:Server:OnGangUpdate` | `src, job` / `src, gang` (re-fired for compat) |
| `QBCore:Server:OnMoneyChange` | `src, moneyType, amount, 'add'|'remove'|'set', reason` |
| `QBCore:Server:SetDuty` | `src, onDuty` |
| `QBCore:Server:PreCommandExecution` | `src, name, args, rawCommand` — `CancelEvent()` blocks the command (2026-05) |
| `QBCore:Server:UpdateObject` | — |
Net events handled by core (client → server): `QBCore:Server:OnPlayerLoaded`, `QBCore:ToggleDuty`, `QBCore:UpdatePlayer` (hunger/thirst tick, 10 s server cooldown), `QBCore:CallCommand` (ACE-checked), `QBCore:Server:CloseServer`/`OpenServer` (admin-checked), callback plumbing.

Client-side:
| Event | Args |
|---|---|
| `QBCore:Client:OnPlayerLoaded` / `QBCore:Client:OnPlayerUnload` | — |
| `QBCore:Client:OnPlayerUpdated` (net) | `key, val` — **the event to listen to for data changes** (`'money'`, `'metadata'`, `'job'`, `'gang'`, `'items'`, `'all'`) |
| `QBCore:Player:SetPlayerData` (local) | full PlayerData — **only on full syncs** now |
| `QBCore:Client:OnJobUpdate` / `QBCore:Client:OnGangUpdate` | `job` / `gang` |
| `QBCore:Client:SetDuty` | `onDuty` |
| `QBCore:Client:OnMoneyChange` | `moneyType, amount, 'add'|'remove'|'set', reason` |
| `QBCore:Notify` (net) | `text, type, length, icon` |
| `QBCore:Client:OnSharedUpdate` / `OnSharedUpdateMultiple` / `SharedUpdate` / `UpdateObject` | shared data changes |
| `QBCore:Client:PvpHasToggled`, `QBCore:Client:VehicleInfo` → `QBCore:Client:EnteringVehicle|EnteredVehicle|LeftVehicle` (needs baseevents) | |

Client data cache that survives partial updates:
```lua
-- client/main.lua
local PlayerData = {}
RegisterNetEvent('QBCore:Client:OnPlayerLoaded', function() PlayerData = QBCore.Functions.GetPlayerData() end)
RegisterNetEvent('QBCore:Client:OnPlayerUnload', function() PlayerData = {} end)
RegisterNetEvent('QBCore:Client:OnPlayerUpdated', function(key, val)
    if key == 'all' then PlayerData = val else PlayerData[key] = val end
end)
```
Simplest alternative: call `QBCore.Functions.GetPlayerData()` when needed (core keeps it current).

## 7. Commands and permissions
```lua
-- server
QBCore.Commands.Add('givecash', 'Give cash (admin)', { { name = 'id', help = 'Player ID' }, { name = 'amount', help = 'Amount' } }, true,
function(source, args)
    local target = QBCore.Functions.GetPlayer(tonumber(args[1]))
    local amount = math.floor(tonumber(args[2]) or 0)
    if not target or amount <= 0 or amount > 100000 then return end
    target.Functions.AddMoney('cash', amount, ('admin %s'):format(source))
end, 'admin')   -- permission; extra levels may follow: , 'god', 'mod'
```
Signature `QBCore.Commands.Add(name, help, arguments, argsrequired, callback, permission?, ...)`. `'user'` (default) = unrestricted; any other level registers a restricted command and runs `add_ace qbcore.<perm> command.<name> allow`. Groups come from `Config.Server.Permissions = { 'god', 'admin', 'mod' }` (core adds `add_ace qbcore.<perm> <perm> allow`). Grant in server.cfg:
```cfg
add_principal identifier.license:xxxxxxxx qbcore.god
add_principal identifier.fivem:123456 qbcore.admin
```
`/addpermission id perm` is runtime only (lost on restart). `QBCore.Commands.Refresh(src)` updates chat suggestions.
Built-in commands: `tp`, `tpm`, `togglepvp`, `addpermission`/`removepermission` (god), `openserver`, `closeserver`, `car`, `dv`, `dvall`, `dvp`, `dvo`, `givemoney`, `setmoney`, `setjob`, `setgang` (admin), `job`, `gang`, `ooc`, `me` (user). qb-inventory adds `giveitem`, `randomitems`, `clearinv`; other qb-* add their own (see https://qbcore.org/docs/qb-core/commands).

## 8. Shared data
Files in `qb-core/shared/` (edit them or use runtime exports from §2):
```lua
-- shared/items.lua  (key must equal name)
sandwich = { name = 'sandwich', label = 'Sandwich', weight = 200, type = 'item', image = 'sandwich.png',
             unique = false, useable = true, shouldClose = true, description = 'Nice bread for your stomach' },
-- weapons: type = 'weapon', ammotype = 'AMMO_PISTOL', unique = true
-- shared/jobs.lua (grades keyed by STRING)
police = { label = 'Law Enforcement', type = 'leo', defaultDuty = true, offDutyPay = false,
           grades = { ['0'] = { name = 'Recruit', payment = 50 }, ['4'] = { name = 'Chief', isboss = true, payment = 150 } } },
-- shared/gangs.lua
ballas = { label = 'Ballas', grades = { ['0'] = { name = 'Recruit' }, ['3'] = { name = 'Boss', isboss = true } } },
-- shared/vehicles.lua (array converted to QBCore.Shared.Vehicles[model]; also VehicleHashes[hash])
{ model = 'blista', name = 'Blista', brand = 'Dinka', price = 13000, category = 'compacts', type = 'automobile', shop = 'pdm' },
-- shared/weapons.lua (keyed by hash)
[`weapon_pistol`] = { name = 'weapon_pistol', label = '...', weapontype = 'Pistol', ammotype = 'AMMO_PISTOL', damagereason = '...' },
```
Also `QBCore.Shared.Locations` (teleport names), `StarterItems`, `MaleNoGloves`/`FemaleNoGloves`, helpers `RandomStr(n)`, `RandomInt(n)`, `SplitStr`, `Trim`, `FirstToUpper`, `Round`, `ChangeVehicleExtra`, `SetDefaultVehicleExtras`, `IsFunction`.
Item images live in `qb-inventory/html/images/`. On ox_inventory hybrids, items are defined in `ox_inventory/data/items.lua` instead — keep both in sync or use one.

## 9. Config (`qb-core/config.lua`, global `QBCore.Config`)
| Key | Default |
|---|---|
| `MaxPlayers` | `GetConvarInt('sv_maxclients', 48)` |
| `DefaultSpawn` | `vector4(-1035.71, -2731.87, 12.86, 0.0)` |
| `UpdateInterval` / `StatusInterval` | 5 (min, save + needs tick) / 5000 ms (starvation damage) |
| `Money.MoneyTypes` | `{ cash = 500, bank = 5000, crypto = 0 }` — adding a type is permanent in DB |
| `Money.DontAllowMinus` / `MinusLimit` | `{ 'cash', 'crypto' }` / `-5000` |
| `Money.PayCheckTimeOut` / `PayCheckSociety` | 10 min / `false` (true = paid from **qb-banking** job account) |
| `Player.HungerRate` / `ThirstRate` / `Bloodtypes` / `PlayerDefaults` | 4.2 / 3.8 / list / see §3 |
| `Server.Closed` / `ClosedReason` | `false` (bypass ACE `qbadmin.join`) |
| `Server.Whitelist` / `WhitelistPermission` | `false` / `'admin'` |
| `Server.PVP`, `Server.Discord`, `Server.CheckDuplicateLicense` (true), `Server.Permissions` | |
| `Commands.OOCColor`, `Notify.NotificationStyling` (`group`, `position`, `progress`), `Notify.VariantDefinitions` | |
Locale: `qb_locale` convar selects `locale/<lang>.lua`. Requires the `bans` and `players` tables from `qbcore.sql` — the server refuses joins if `bans` is missing.

## 10. QB resources
Versions are each repo's fxmanifest `version` on 2026-10-07; "last code" = last commit that is not the 2026-08 org-wide housekeeping commit.

### qb-inventory 2.2.3 (last code 2026-09-10) — https://github.com/qbcore-fivem/qb-inventory
Docs https://qbcore.org/docs/qbcore-resources/qb-inventory. Tables: `inventories (identifier, items)`; `migrate.sql` moves old `stashitems/trunkitems/gloveboxitems`. Config: `MaxWeight = 120000`, `MaxSlots = 40`, `StashSize { maxweight = 2000000, slots = 100 }`, `DropSize`, keybinds TAB/Z, `UseTarget` convar.
Server exports (`identifier` = player source or inventory id string such as `'stash-x'`, `'trunk-PLATE'`, `'glovebox-PLATE'`):
```lua
exports['qb-inventory']:AddItem(identifier, item, amount, slot?, info?, reason?)      -- -> boolean
exports['qb-inventory']:RemoveItem(identifier, item, amount, slot?, reason?)          -- -> boolean
exports['qb-inventory']:CanAddItem(identifier, item, amount)                          -- -> ok, 'weight'|'slots'
exports['qb-inventory']:HasItem(source, items, amount?)  -- items: 'name' | {'a','b'} | { a = 2, b = 1 }
exports['qb-inventory']:GetItemCount(source, items) ; GetItemByName(source, name) ; GetItemsByName ; GetItemBySlot(source, slot)
exports['qb-inventory']:GetSlotsByItem(items, name) ; GetFirstSlotByItem(items, name) ; GetTotalWeight(items) ; GetSlots(identifier) ; GetFreeWeight(source)
exports['qb-inventory']:SetItemData(source, itemName, key, val, slot?) ; SetInventory(identifier, items, reason?) ; ClearInventory(source, keep?) ; ClearStash(id)
exports['qb-inventory']:CreateInventory(id, { label, maxweight, slots }) ; GetInventory(id) ; RemoveInventory(id)
exports['qb-inventory']:OpenInventory(source, id?, { label, maxweight, slots }?) ; OpenInventoryById(source, targetId) ; CloseInventory(source, id?)
exports['qb-inventory']:CreateShop({ name, label, coords?, slots, items = { { name, price, amount } } }) ; OpenShop(source, name) -- 5 m distance check if coords given
exports['qb-inventory']:UseItem(name, source, item) ; LoadInventory(source, cid) ; SaveInventory(source|PlayerData, offline)
exports['qb-inventory']:AddHook(type, fn) -> id ; RemoveHook(type, id) ; AddListener(type, fn) -> id ; RemoveListener(type, id)
```
Hook/listener types (2026-05+): `ItemMoved`, `ItemDropped`, `ItemUsed`, `ItemBought`, `ItemAdded`, `ItemRemoved`, `InventoryOpened`, `ShopOpened`. Callback `fn(typeOrInvType, payload)`; a **hook** returning `false` cancels; listeners run after and cannot cancel. Hooks are auto-removed when the registering resource stops.
```lua
-- server: block moving weapons into stashes
exports['qb-inventory']:AddHook('ItemMoved', function(_, payload)
    if payload.toType == 'inventory' and payload.item and payload.item.type == 'weapon' then return false end
end)
```
Client export: `exports['qb-inventory']:HasItem(items, amount?)`. Player state bag `inv_busy` blocks opening. Never open stashes from a client-supplied id without server-side job/ownership/distance checks (OpenInventory itself does not check permissions).

### qb-target 5.5.0 (last code 2026-05-20) — https://github.com/qbcore-fivem/qb-target
Client-only exports; depends on PolyZone. Many servers run **ox_target** instead. ox_target only `provide`s `qtarget` (partial compatibility); it does **not** provide `qb-target`, so `exports['qb-target']:*` calls fail unless qb-target is also running or a shim is installed — port them to ox_target options ([ox-target.md](ox-target.md)).
```lua
exports['qb-target']:AddBoxZone('myres_duty', vector3(441.8, -982.1, 30.7), 0.45, 0.35,
    { name = 'myres_duty', heading = 11.0, debugPoly = false, minZ = 30.6, maxZ = 30.9 },
    { options = {
        { type = 'server', event = 'myres:server:toggleDuty', icon = 'fas fa-clipboard', label = 'Sign in',
          job = 'police',                       -- or { police = 2, sheriff = 0 } ; also gang, citizenid, item, excludejob, excludegang
          canInteract = function(entity, distance, data) return true end },
      }, distance = 2.5 })
```
Option `type`: `'client'` (TriggerEvent), `'server'` (TriggerServerEvent with the option table), `'command'`, `'qbcommand'`; or `action = function(entity) end`. Exports: `AddCircleZone(name, center, radius, opts, targetopts)`, `AddBoxZone`, `AddPolyZone(name, points, opts, targetopts)`, `AddComboZone(zones, opts, targetopts)`, `AddEntityZone(name, entity, opts, targetopts)`, `RemoveZone(name)`, `AddTargetBone(bones, params)`, `AddTargetEntity(entities, params)`, `AddTargetModel(models, params)`, `AddGlobalPed|Vehicle|Object|Player(params)`, matching `Remove*`, `Get*Data`/`Update*Data`, `SpawnPed`, `RemoveSpawnedPed`, `AllowTargeting(bool)`, `IsTargetActive()`, `IsTargetSuccess()`, `DisableTarget(bool)`, `RaycastCamera`. **Client checks (job, item) are UX only — re-check on the server.**

### qb-menu 1.5.0 / qb-input 1.2.0 (last code 2026-05-20)
```lua
exports['qb-menu']:openMenu({
    { header = 'Garage', isMenuHeader = true },
    { header = 'Take vehicle', txt = 'Sultan', icon = 'fas fa-car',
      params = { event = 'myres:client:takeVehicle', args = { plate = 'ABC123' } } },  -- isServer / isCommand / isQBCommand / isAction
    { header = 'Locked', disabled = true, params = { event = '' } },
}, sort?, skipFirst?)
exports['qb-menu']:closeMenu() ; exports['qb-menu']:showHeader(items)

local dialog = exports['qb-input']:ShowInput({ header = 'Bill', submitText = 'Send', inputs = {
    { text = 'Amount ($)', name = 'amount', type = 'number', isRequired = true },  -- text|password|number|radio|checkbox|select|color
} })
if dialog then local amount = tonumber(dialog.amount) end   -- strings; nil when cancelled
```
Both are legacy NUI; for new code prefer ox_lib `lib.registerContext` / `lib.inputDialog` if ox_lib is present.

### qb-banking 2.0.0 / qb-management 2.2.0 (last code 2026-05-20)
Society money lives in **qb-banking** (`bank_accounts` table); qb-management is only the boss/gang menus.
```lua
exports['qb-banking']:GetAccountBalance('police')            -- number
exports['qb-banking']:AddMoney('police', 500, 'Fine')        -- AddGangMoney is an alias
exports['qb-banking']:RemoveMoney('police', 500, 'Payroll')  -- RemoveGangMoney is an alias
exports['qb-banking']:GetAccount(name) ; CreatePlayerAccount(src, name, balance, users) ; CreateJobAccount(name, bal) ; CreateGangAccount(name, bal)
exports['qb-banking']:CreateBankStatement(src, account, amount, reason, statementType, accountType)
```
qb-management client exports: `AddBossMenuItem(data, id)`, `RemoveBossMenuItem(id)`, `AddGangMenuItem(data, id)`, `RemoveGangMenuItem(id)`. Renewed-Banking `provide`s `qb-management` and is a common replacement ([ecosystem-resources.md](ecosystem-resources.md)).

### qb-multicharacter 1.5.0 / qb-spawn 1.5.0 / qb-apartments 2.2.1
Flow: multicharacter → `QBCore.Player.Login(src, citizenid)` (license must match the row) → spawn: last location (`Config.SkipSelection`), `qb-spawn:client:setupSpawns` + `openUI`, or `apartments:client:setupSpawnUI` when `Apartments.Starting = true` → client `TriggerServerEvent('QBCore:Server:OnPlayerLoaded')` → core fires `QBCore:Client:OnPlayerLoaded`. Config: `Config.DefaultNumberOfCharacters = 5`, `Config.PlayersNumberOfCharacters` per license, `Config.EnableDeleteButton`. qb-apartments got a stash ownership fix on 2026-08-26 — update. Housing replacements: ps-housing (archived 2026-02 — avoid for new installs) or paid housing scripts; Qbox's `qbx_properties`/`qbx_spawn` need qbx_core, not qb-core.

### qb-phone 1.5.0 (last code 2026-05-20) — legacy
Still in the org but feature-frozen; depends on `screenshot-basic` (use screencapture, which provides it) and many qb-* resources. Only export: `sendNewMailToOffline`. Prefer **npwd** (free) or **lb-phone** (paid) — see ecosystem file.

### PolyZone 2.6.2
Upstream https://github.com/mkafrin/PolyZone (MIT, v2.6.2 2025-01-05); `qbcore-fivem/PolyZone` is a fork. Import in the consumer's manifest (order matters):
```lua
client_scripts { '@PolyZone/client.lua', '@PolyZone/BoxZone.lua', '@PolyZone/EntityZone.lua', '@PolyZone/CircleZone.lua', '@PolyZone/ComboZone.lua', 'client/*.lua' }
```
```lua
local zone = BoxZone:Create(vector3(441.8, -982.1, 30.7), 3.0, 3.0, { name = 'mrpd', heading = 0, minZ = 29.5, maxZ = 32.5, debugPoly = false })
zone:onPlayerInOut(function(isInside) end)   -- polls internally; prefer lib.zones for new code
```

### progressbar 1.0.0 (2024-03)
Required by `QBCore.Functions.Progressbar`. Client exports `Progress(data, cb(cancelled))`, `ProgressWithStartEvent`, `ProgressWithTickEvent`, `ProgressWithStartAndTick`, `isDoingSomething()`.

### Other exports worth knowing
- qb-vehiclekeys 1.6.0: server `GiveKeys(src, plate)`, `RemoveKeys(src, plate)`, `HasKeys(src, plate)`; client `HasKeys(plate)`, `addNoLockVehicles(model)`, `removeNoLockVehicles(model)`; legacy event `vehiclekeys:client:SetOwner`.
- qb-garages 2.0.0: `getAllGarages`; `Config.FuelResource = 'LegacyFuel'` (any resource exporting `GetFuel/SetFuel`, e.g. qb-fuel 0.0.4, ox_fuel, cdn-fuel).
- qb-weathersync 2.3.0: `setWeather`, `setTime`, `setBlackout`, `setTimeFreeze`, `setDynamicWeather`, `nextWeatherStage`, getters; events `qb-weathersync:client:DisableSync|EnableSync`.
- qb-doorlock 2.0.0: `GetDoorList`, `GetDoorStates`, `GetClosestDoor`, `GetNearbyDoors`. qb-radialmenu: `AddOption(data, id)`, `RemoveOption(id)`. qb-smallresources: `AddFood`, `AddDrink`, `AddAlcohol`, `AddCustom`, `HasHarness`, `HasSeatbeltOn`, `addDisableControls`, `addDisableHudComponents`... qb-policejob: `IsHandcuffed`. qb-ambulancejob: `GetDoctorCount`. qb-clothing: `IsCreatingCharacter`, `getOutfits`, `reloadSkin`. qb-houses: `hasKey`, `isNearHouses`, `getKeyHolderData`. qb-cityhall: `AddCityJob`.

## 11. Breaking changes 2024–2026
| Date | Change | Fix |
|---|---|---|
| 2024-05 | **qb-inventory 2.0** ("Inventory Update"): inventory moved out of core; `inventories` table replaces `stashitems/trunkitems/gloveboxitems`; item `combinable` removed; server `QBCore.Functions.HasItem` deprecated | run `migrate.sql`; use `exports['qb-inventory']:*`; `Player.Functions.AddItem/RemoveItem` exist only because qb-inventory injects them |
| 2024-05 | invalid job/gang on login reset to defaults | add jobs to Shared before players log in |
| 2024-10 | `Config.Money.MinusLimit`; `RemoveMoney` checks it | handle `false` |
| 2025-01 | callbacks promise-based (await style), `GetCoreObject(filters)`, all functions exported | |
| 2025-05 | `GetPlayersByJob(job, onDuty)` matches job **type** too | don't name jobs like types |
| 2025-10 | client callbacks keyed per source | update forks with custom callback code |
| 2025-11 | `GetShared(namespace, key)` export, `StarterItems` moved to shared | |
| 2025-12 | `ForceJobDefaultDutyAtLogin` | set `false` to restore saved duty |
| 2026-04-21 | **partial player updates**: server sends `QBCore:Client:OnPlayerUpdated(key, val)` | listen to it instead of `QBCore:Player:SetPlayerData` |
| 2026-05-19 | **core refactor** (commit 74ac036): `QBConfig`/`QBShared` globals gone (use `QBCore.Config`/`QBCore.Shared`); exports `GetSharedItems/Vehicles/Weapons/Jobs/Gangs` removed (use `GetShared`); `client/main.lua`/`server/main.lua` removed; Player is a class; net events `QBCore:Player:SetPlayerData`, `QBCore:Player:UpdatePlayerDataField`, `QBCore:Player:UpdatePlayerData`, and exploitable `QBCore:Server:UseItem/AddItem/RemoveItem`, `QBCore:Client:UseItem` removed; `QBCore:Server:PlayerDropped` now passes `src`; new notification UI (vanilla JS, `Config.Notify`) | grep resources for the removed names (see §12) |
| 2026-05-27 | `QBCore:Server:PreCommandExecution` middleware event | |
| 2026-05/09 | qb-inventory hooks/listeners (2.1–2.2.3), server-authoritative `useItem`, theft fix on moves | update to ≥ 2.2.3 |
| 2026-08/09 | security fixes: qb-garages spawn ownership, qb-vehiclekeys key acquisition, qb-smallresources item dupe, qb-fuel negative refill, qb-radialmenu trunk abuse, qb-hud stress, qb-apartments stash ownership | update these resources |
| 2026 | GitHub org moved `qbcore-framework` → `qbcore-fivem` (redirects); docs at qbcore.org/docs (docs.qbcore.org redirects there) | update URLs, txAdmin recipe |

Quick compatibility grep for old resources: `QBShared`, `QBConfig`, `GetSharedItems`, `QBCore:Player:SetPlayerData` (as a net event handler expecting per-key updates), `QBCore:Server:AddItem`, `QBCore:Server:RemoveItem`, `QBCore:Server:UseItem`, `PlayerDropped', function(Player`.

## 12. Best practices and common mistakes
- `local src = source` first; `GetPlayer(src)` and nil-check every time; never accept a citizenid/source/price/amount from the client without validating it.
- Use `Player.Functions.RemoveMoney` return values; no yield between the check and the mutations (else take/verify first, grant after, refund on failure); re-check item count with `HasItem`/`GetItemCount` on the server.
- `CreateUseableItem` callbacks receive the server-side item (qb-inventory ≥ 2026-05); still validate `item.info`.
- Prefer server vehicle creation (`QBCore.Functions.CreateVehicle`) and send the netId; give keys via `exports['qb-vehiclekeys']:GiveKeys(src, plate)` server-side.
- Use ACE (`HasPermission`) for admin actions; `Config.Server.Permissions` must match server.cfg principals.
- Don't run your own 5-minute `Save()` loops — core saves every `UpdateInterval` and on drop.
- Don't spam `SetMetaData` per tick (each call syncs the full metadata table to the client).
- `QBCore.Functions.AddItem` is the *shared definition* adder, not a give-item function (very common mistake).
- `QBCore.Functions.Notify` is `(text, type, length)` on the client but `(source, text, type, length)` on the server.
- Job grades are string keys (`['0']`); `SetJob('police', 2)` works because grade is `tostring`ed.
- On hybrid servers (ox_inventory, ox_target, ox_lib) detect with `GetResourceState('ox_inventory') == 'started'` and use one API consistently ([framework-bridge.md](framework-bridge.md)).
- Old forks (2022–2023, "QBCore + qb-inventory 1.x") use `Player.Functions.AddItem` from core, `QBCore:Server:AddItem` events and the `stashitems` table — confirm the version before writing code.

## 13. qbcore-fivem repositories (GitHub API, 2026-10-07)
70 repos; most received only a housekeeping commit on 2026-08-24/26 (`remove local community files`). Real activity in 2026: qb-core, qb-inventory, qb-vehiclekeys, qb-garages, qb-ambulancejob, qb-weathersync, qb-radialmenu, qb-smallresources, qb-fuel, qb-apartments, qb-hud, qb-houses (security fixes Aug–Sep), plus the 2026-05-20 "Don't import whole core" sweep across almost every qb-* resource.
Core set: qb-core, qb-inventory, qb-target, qb-menu, qb-input, qb-multicharacter, qb-spawn, qb-apartments, qb-clothing, qb-banking, qb-management, qb-garages, qb-vehiclekeys, qb-vehicleshop, qb-doorlock, qb-hud, qb-radialmenu, qb-smallresources, qb-weathersync, qb-adminmenu, qb-scoreboard, qb-loading, qb-cityhall, qb-shops, qb-phone, qb-houses, qb-interior, qb-weapons, qb-radio, qb-fuel, qb-crafting, txAdminRecipe, PolyZone, menuv, bob74_ipl, progressbar (2024-03), interact-sound (2024-11), qb-minigames (2024-03), connectqueue/safecracker (2022, dead).
Jobs/crime: qb-policejob, qb-ambulancejob, qb-mechanicjob, qb-taxijob, qb-busjob, qb-truckerjob, qb-towjob, qb-garbagejob, qb-newsjob, qb-hotdogjob, qb-vineyard, qb-recyclejob, qb-diving, qb-prison, qb-bankrobbery, qb-storerobbery, qb-jewelery, qb-houserobbery, qb-truckrobbery, qb-drugs, qb-weed, qb-scrapyard, qb-pawnshop, qb-crypto, qb-streetraces, qb-lapraces, qb-vehiclesales; maps prison_map, hospital_map, dealer_map.
List them yourself: `gh api "orgs/qbcore-fivem/repos?per_page=100&sort=pushed" --jq '.[] | "\(.pushed_at[:10]) \(.name)"'`.

## Sources
- https://github.com/qbcore-fivem/qb-core (files: fxmanifest.lua, config.lua, server/{functions,player,events,commands,exports,debug}.lua, client/{functions,events,loops,drawtext}.lua, shared/*.lua, qbcore.sql; commits incl. 74ac036 and 1cee09a)
- https://qbcore.org/docs/llms.txt · https://qbcore.org/docs/qb-core/core-object.md · https://qbcore.org/docs/qbcore-resources/qb-inventory.md
- https://github.com/qbcore-fivem/qb-inventory (server/functions.lua, server/hooks.lua, server/main.lua, client/main.lua, config/config.lua, README.md)
- https://github.com/qbcore-fivem/qb-target (registration.lua, client.lua, EXAMPLES.md) · https://github.com/qbcore-fivem/qb-menu · https://github.com/qbcore-fivem/qb-input
- https://github.com/qbcore-fivem/qb-banking · https://github.com/qbcore-fivem/qb-management · https://github.com/qbcore-fivem/qb-multicharacter · https://github.com/qbcore-fivem/qb-spawn · https://github.com/qbcore-fivem/qb-apartments · https://github.com/qbcore-fivem/qb-phone · https://github.com/qbcore-fivem/qb-vehiclekeys · https://github.com/qbcore-fivem/qb-garages · https://github.com/qbcore-fivem/progressbar
- https://github.com/mkafrin/PolyZone · https://api.github.com/orgs/qbcore-fivem/repos
