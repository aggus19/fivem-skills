# Qbox (qbx_core) reference
Baseline: qbx_core v1.24.0 — verified 2026-10-07

## Contents
1. What Qbox is and the golden rules
2. Install, requirements, startup checks
3. Convars (complete list from source)
4. Config files
5. Using qbx_core from a resource (fxmanifest)
6. Server exports (exact signatures)
7. Client and shared exports
8. Events, state bags, GlobalState
9. PlayerData schema
10. Multicharacter, character creation and spawn flow
11. Groups: jobs, gangs, multijob, duty, paychecks
12. Items, vehicles, weapons, jobs data — how to add
13. Modules: lib (`qbx.*`), playerdata, hooks, logger, utils (deprecated)
14. Permissions (ACE), commands, opt-in, bans, queue
15. qb-core bridge: what works and what does not
16. Migration QBCore → Qbox (before/after)
17. Deprecations and breaking changes 2024–2026
18. Best practices and common mistakes
19. Sources

## 1. What Qbox is and the golden rules
v1.24.0 was released 2026-08-22 and checked against the tagged source and docs.qbox.re. `main` is 17 commits ahead of the tag (unreleased, see §17). Repo: https://github.com/Qbox-project/qbx_core · Docs: https://docs.qbox.re · License: GPL-3.0. Other Qbox resources (garages, keys, medical, police, management…): [qbox-ecosystem.md](qbox-ecosystem.md).

Qbox is a maintained fork of QBCore. It has no core object. You use `exports.qbx_core:*`, a few `require`-able modules, and the ox stack: ox_lib, oxmysql, ox_inventory, plus ox_target.
- Write new code against exports and ox_lib. `exports['qb-core']:GetCoreObject()` only exists through the compatibility bridge (§15).
- Inventory is **always ox_inventory**. qb-inventory is rejected: `Save` asserts that `qb-inventory` is not started.
- Server code is authoritative. Money, groups and metadata change only through server exports, and every net event must be validated (see `security.md`).
- Group names (jobs and gangs) must be lowercase. Grades are **integers**, not the strings QBCore uses.

## 2. Install, requirements, startup checks
**Recommended**: txAdmin → Popular Recipes → **QBox Framework** (recipe: https://github.com/Qbox-project/txAdminRecipe). It downloads `server.cfg`, `ox.cfg`, `permissions.cfg`, `voice.cfg`, `misc.cfg` and `qbox.sql`, plus about 50 `qbx_*` resources and third-party ones: Renewed-Banking, illenium-appearance, npwd, pma-voice, mm_radio, Renewed-Weathersync, xt-prison, mana_audio, scully_emotemenu, bob74_ipl and others.

Hard requirements. `server/main.lua` checks these at start: it prints the error and runs `quit immediately` if any check fails.
| Requirement | Value |
|---|---|
| FXServer artifact | `/server:10731`+ (manifest dependency) |
| OneSync | `/onesync`, and the server checks `GetConvarInt('onesync_enableInfinity', 0) == 1` |
| ox_lib | ≥ 3.20.0 (`lib.checkDependency`) |
| ox_inventory | ≥ 2.42.1 and `setr inventory:framework "qbx"` (in `ox.cfg`) |
| oxmysql | required (`@oxmysql/lib/MySQL.lua`) |
| Database | **MariaDB ≥ 10.9.0** (uses `JSON_VALUE`, `CREATE INDEX IF NOT EXISTS`); docs recommend 12.3 LTS. MySQL and XAMPP are "not supported" per the docs |

ox_inventory's qbx bridge in turn requires qbx_core ≥ 1.18.1.

Recommended `server.cfg` order (from the recipe):
```cfg
ensure ox_lib
ensure qbx_core
ensure ox_target
ensure [ox]        # oxmysql, ox_inventory, ...
ensure [qbx]
ensure [standalone]
ensure [voice]
exec permissions.cfg
```
SQL: `qbx_core.sql` creates `players` (PK `citizenid`, `utf8mb4_unicode_ci`), `bans` and `player_groups` (FK on `players.citizenid` with ON DELETE CASCADE). On start the core also creates the `users` table and adds `players.userId`.

## 3. Convars (complete list from source v1.24.0)
FXServer convar names are evidently case-insensitive: the official recipe sets `qbx:enableBridge`, while the source reads `qbx:enablebridge`, and it works. Use `setr` for every convar a client script reads.
| Convar | Default | Side | Effect |
|---|---|---|---|
| `qbx:enablebridge` | `true` | **setr** (client+server) | Loads the qb-core bridge (`GetCoreObject`, QB events, item conversion) |
| `qbx:enablequeue` | `true` | server | Built-in connection queue (`config/queue.lua`) |
| `qbx:bucketlockdownmode` | `inactive` | server | `SetRoutingBucketEntityLockdownMode(0, mode)`: `inactive`/`relaxed`/`strict` |
| `qbx:discordlink` | `discord.gg/qbox` | server | Kick message link (bridge `Kick` and deprecated utils only) |
| `qbx:max_jobs_per_player` | `1` | server | Multijob limit |
| `qbx:max_gangs_per_player` | `1` | server | Multigang limit |
| `qbx:setjob_replaces` | `true` | server | `SetJob` removes the old primary job before adding the new one |
| `qbx:setgang_replaces` | `true` | server | Same for `SetGang` |
| `qbx:cleanPlayerGroups` | `false` (recipe: `true`) | server | Deletes invalid groups/grades from `player_groups` on start |
| `qbx:allowmethodoverrides` | `true` | server | Lets bridge `SetMethod`/`AddPlayerMethod` override player methods |
| `qbx:disableoverridewarning` | `false` | server | Silences the override warning |
| `qbx:enableVehiclePersistence` | `false` | **setr** | Respawns persisted owned vehicles that the server deleted (needs qbx_vehicles ≥ 1.4.1) |
| `qbx:vehiclePersistenceType` | `semi` | **setr** | `full` also respawns them after a restart (v1.24.0) |
| `qbx:acknowledge` | `false` | server | `true` hides the service-message/docs console banner |
| `qbx:serviceMessagesUrl` | txAdminRecipe `service-messages.json` | server | Source of console service messages (not in the docs) |
| `qbx:motd` | `''` | **setr** | HTML chat message shown after load |

Convars from other resources that the core reads: `inventory:framework` (must be `qbx`), `inventory:accounts` (default `["money"]`; cash mirrors to the ox_inventory `money` item), `onesync_enableInfinity` and `sv_maxclients`.
Recipe extras: `setr qb_locale "en"`, `setr qbx:enableGroupManagement "false"` (qbx_management), `set npwd:framework "qbx"`, `setr loadscreen:externalShutdown true`.

## 4. Config files
| File | Key settings (defaults) |
|---|---|
| `config/server.lua` | `updateInterval=5` (min, hunger/thirst tick and save); `money.moneyTypes={cash=500,bank=5000,crypto=0}`; `money.dontAllowMinus={'cash','crypto'}` (**bank can go negative**); `paycheckTimeout=10`; `paycheckSociety=false`; `player.hungerRate=4.2`, `thirstRate=3.8`; `bloodTypes`; `identifierTypes` (citizenid `A.......`, AccountNumber, PhoneNumber, FingerId, WalletId, SerialNumber generators); `characterDataTables` (rows deleted with a character); `server.pvp/closed/closedReason/whitelist/whitelistPermission='admin'/discord/checkDuplicateLicense/requireOptIn=true/permissions={'god','admin','mod'}`; `characters.playersNumberOfCharacters[license]`, `defaultNumberOfCharacters=3`; `logging.webhook.{default,joinleave,ooc,anticheat,playermoney}`, `logging.role`; `persistence.lockState`; hooks `giveVehicleKeys`, `setVehicleLock`, `getSocietyAccount`/`removeSocietyMoney` (Renewed-Banking), `sendPaycheck` |
| `config/client.lua` | `statusIntervalSeconds=5`, `loadingModelsTimeout=30000`, `pauseMapText`; `characters.useExternalCharacters=false`, `enableDeleteButton`, `startingApartment=true`, date format/min/max, `limitNationalities`, `profanityWords`, preview `locations`; `discord` rich presence (`richPresence` placeholders `{id} {charName} {playerName} {currentPlayers} {maxPlayers} {streetName}`, `updateInterval` ≥ 5000); `hasKeys` (bridge); teleport, `/me` and vehicle-prop tuning |
| `config/shared.lua` | `serverName`, `defaultSpawn` (vec4), `notifyPosition='top-right'`, `starterItems` (phone, id_card, driver_license with `qbx_idcard` metadata) |
| `config/queue.lua` | `timeoutSeconds=30`, `joiningTimeoutSeconds`, `subQueues` (first entry: an admin queue with ACE predicate `admin`), adaptive card generator |
| `shared/main.lua` | `ForceJobDefaultDutyAtLogin=true` |

## 5. Using qbx_core from a resource
```lua
-- fxmanifest.lua
fx_version 'cerulean'
game 'gta5'
lua54 'yes'                                  -- optional on current artifacts (Lua 5.4 only)

shared_scripts {
    '@ox_lib/init.lua',
    '@qbx_core/modules/lib.lua',             -- optional: qbx.* helpers (must come after ox_lib)
}
client_scripts {
    '@qbx_core/modules/playerdata.lua',      -- optional: global QBX.PlayerData kept in sync
    'client/*.lua',
}
server_scripts {
    '@oxmysql/lib/MySQL.lua',
    'server/*.lua',
}
dependencies { 'qbx_core', 'ox_lib' }
```
Server-only modules are loaded with ox_lib `require`: `local logger = require '@qbx_core.modules.logger'` and `local triggerEventHooks = require '@qbx_core.modules.hooks'`.

## 6. Server exports (`exports.qbx_core:Name(...)`)
`identifier` = server id **or** citizenid string. A citizenid also resolves **offline** players (loaded from the DB through `GetOfflinePlayer`); an offline save uses `SaveOffline`. `ErrorResult` = `{ code: string, message: string }`.

**Players and lookup**
| Export | Returns / notes |
|---|---|
| `GetPlayer(source \| identifierString)` | `Player?`. A non-numeric string is treated as a FiveM identifier (`license2:...`), **not** a citizenid |
| `GetPlayerByCitizenId(citizenid)` | `Player?` (online only) |
| `GetPlayerByUserId(userId)` / `GetUserId(identifier)` | `Player?` / `integer` (0 if none) |
| `GetPlayerByPhone(number)` | `Player?` (`charinfo.phone`) |
| `GetSource(identifier)` | `integer` source, or `0` |
| `GetOfflinePlayer(citizenid)` | `Player?` with `Offline = true` |
| `GetQBPlayers()` | `table<Source, Player>` (live table, do not mutate) |
| `GetPlayersData()` | `PlayerData[]` |
| `SearchPlayers(filters)` | `Player[]`, online and offline. Filters: `license`, `job`, `gang`, `charinfo = {key=value}` (1.24), `metadata = {['licences.driver']=true, strict?=bool}` (number values match `>=` unless `strict`) |
| `GetDutyCountJob(job)` / `GetDutyCountType(type)` | `count, Source[]` of on-duty players |
| `Login(source, citizenid?, newData?)` | `boolean`. Loads an existing character, or creates one from `newData` |
| `Logout(source)` | Saves, unloads and fires the unload events; the client returns to character select |
| `CreatePlayer(playerData, offline)` | Internal. Do not call |
| `Save(source)` / `SaveOffline(playerData)` | Async DB upsert |
| `DeleteCharacter(citizenid)` | Force-delete (drops the player if online) |
| `GenerateUniqueIdentifier(type)` | `type`: `citizenid`/`AccountNumber`/`PhoneNumber`/`FingerId`/`WalletId`/`SerialNumber` |
| `SetPlayerData(identifier, key, value)` / `UpdatePlayerData(identifier)` | Sets a field and syncs to the client (`QBCore:Player:SetPlayerData`) |
| `SetCharInfo(identifier, key, value)` | Writes `charinfo[key]` and syncs |
| `GetMetadata(identifier, key)` / `SetMetadata(identifier, key, value)` | Supports **one** nesting level: `'licences.driver'` (1.23). hunger/thirst/stress are clamped to 0–100 and must be finite (1.24) |

**Money** (types from `config.money.moneyTypes`: `cash`, `bank`, `crypto` + custom)
| Export | Notes |
|---|---|
| `AddMoney(identifier, moneyType, amount, reason?)` | `boolean`. Amount must be finite and ≥ 0 and is rounded; returns false otherwise or when a hook cancels |
| `RemoveMoney(identifier, moneyType, amount, reason?)` | `false` if it would go below 0 for a `dontAllowMinus` type (cash and crypto by default) |
| `SetMoney(identifier, moneyType, amount, reason?)` | `boolean` |
| `GetMoney(identifier, moneyType)` | `number`, or `false` |
Each change fires hooks (§13), the money events (§8) and a log (role tags above 100000), and mirrors `cash` to the ox_inventory `money` item.

**Groups** (§11)
| Export | Notes |
|---|---|
| `SetJob(identifier, jobName, grade?)` / `SetGang(...)` | `boolean, ErrorResult?`. Replaces the primary group when the `setjob_replaces`/`setgang_replaces` convar is true |
| `SetJobDuty(identifier, onDuty)` | Fires `QBCore:Server:SetDuty` and `QBCore:Client:SetDuty` |
| `AddPlayerToJob(citizenid, job, grade?)` / `AddPlayerToGang(...)` | Adds the group or updates its grade; respects the max convars |
| `RemovePlayerFromJob(citizenid, job)` / `RemovePlayerFromGang(...)` | Removing the primary group resets it to `unemployed`/`none` |
| `SetPlayerPrimaryJob(citizenid, job)` / `SetPlayerPrimaryGang(...)` | The player must already hold the group |
| `HasGroup(source, filter)` / `HasPrimaryGroup(source, filter)` | `boolean` |
| `GetGroups(source)` | `table<name, grade>` (jobs + gangs) |
| `GetGroupMembers(group, type)` | `{citizenid, grade}[]` from the DB; `type` = `'job'`/`'gang'` |
| `IsGradeBoss(group, grade)` | `boolean` |
| `GetJobs()` / `GetGangs()` / `GetJob(name)` / `GetGang(name)` | Group definitions |
| `CreateJob(name, job, commitToFile?)` / `CreateJobs(jobs, commitToFile?)` / `RemoveJob(name, commitToFile?)` | Runtime changes. `commitToFile=true` rewrites `shared/jobs.lua` |
| `CreateGangs(gangs, commitToFile?)` / `RemoveGang(name, commitToFile?)` | Same for gangs |
| `UpsertJobData(name, {label,type,defaultDuty,offDutyPay}, commit?)` / `UpsertGangData(name, {label}, commit?)` | Partial update |
| `UpsertJobGrade(name, grade, {name,payment,isboss?,bankAuth?}, commit?)` / `UpsertGangGrade(...)` / `RemoveJobGrade(name, grade, commit?)` / `RemoveGangGrade(...)` | |

**Utilities**
| Export | Notes |
|---|---|
| `Notify(source, text, type?, duration?, subTitle?, position?, style?, icon?, iconColor?)` | Sends `ox_lib:notify`. `text` may be `{text=, caption=}`; type is `inform`/`success`/`error`/`warning` |
| `CreateUseableItem(name, function(source, item) end)` / `CanUseItem(name)` | ox_inventory's qbx bridge calls `CanUseItem` when the item is used |
| `SetPlayerBucket(source, bucket)` / `SetEntityBucket(entity, bucket)` | `boolean`; also sets `Player(src).state.instance` |
| `GetPlayersInBucket(b)` / `GetEntitiesInBucket(b)` / `GetBucketObjects()` | Only tracks buckets set through these exports |
| `IsWhitelisted(source)` / `IsPlayerBanned(source)` → `bool, message?` / `ExploitBan(source, reason)` | Bans are checked by license, license2, discord and ip |
| `IsOptin(source)` / `ToggleOptin(source)` | Admin opt-in (§14) |
| `GetCoreVersion()` | `'1.24.0'` |
| `GetVehicleClass(model)` | Class from a cached client callback; **errors if no client is online** |
| `GetVehiclesByName(key?)` / `GetVehiclesByHash(key?)` / `GetVehiclesByCategory()` / `GetWeapons(key?)` | Shared data; with a key, returns one entry |
| `CreateSessionId(entity)` | Stable `Entity(e).state.sessionId` |
| `EnablePersistence(veh)` / `DisablePersistence(veh)` / `DeleteVehicle(veh)` | Vehicle persistence (`DeleteVehicle` disables persistence first) |
| `registerHook(event, cb)` → `hookId` / `removeHooks(id?)` | §13 |
| Deprecated: `AddPermission`, `RemovePermission`, `HasPermission`, `GetPermission`, `GetLocations` | §17 |

```lua
-- server: pay a fine from a validated client request
RegisterNetEvent('myres:server:payFine', function(amount)
    local src = source
    if not exports.qbx_core:GetPlayer(src) then return end
    if not exports.qbx_core:HasGroup(src, { police = 1 }) then return end -- police, grade >= 1
    amount = math.tointeger(tonumber(amount))
    if not amount or amount < 1 or amount > 50000 then return end
    if not exports.qbx_core:RemoveMoney(src, 'bank', amount, 'fine-payment') then
        exports.qbx_core:Notify(src, 'Insufficient funds', 'error')
    end
end)
```

## 7. Client and shared exports
| Client export | Notes |
|---|---|
| `GetPlayerData()` | `PlayerData?` (works; missing from the docs page) |
| `HasGroup(filter)` / `HasPrimaryGroup(filter)` / `GetGroups()` | Same filter semantics as on the server |
| `Notify(text, type?, duration?, subTitle?, position?, style?, icon?, iconColor?)` | Wraps `lib.notify` |
| `GetJobs()` / `GetGangs()` / `GetJob(name)` / `GetGang(name)` | Cached from the server (`qbx_core:server:getGroups`) and updated on group changes |
| `GetVehiclesByName(key?)` / `GetVehiclesByHash(key?)` / `GetVehiclesByCategory()` / `GetWeapons(key?)` / `GetLocations()` (deprecated) | Shared data |

Client globals inside qbx_core: `QBX.PlayerData`, `QBX.IsLoggedIn`, `QBX.Shared`. In your resource use the playerdata module or `exports.qbx_core:GetPlayerData()`.
```lua
-- client: react to job changes (playerdata module loaded)
RegisterNetEvent('QBCore:Client:OnJobUpdate', function(job)
    if job.name == 'police' and job.onduty then
        -- enable police features
    end
end)

AddEventHandler('QBCore:Client:OnPlayerLoaded', function()
    local data = QBX.PlayerData
    print(data.charinfo.firstname, data.job.name, data.money.cash)
end)
```

## 8. Events, state bags, GlobalState
Do **not** trigger these events from your own scripts (docs warning). Listen only.

**Server, local (`AddEventHandler`)**
| Event | Args |
|---|---|
| `QBCore:Server:PlayerLoaded` | `player` (Player object), fired when the player object is created |
| `QBCore:Server:OnPlayerUnload` | `source`; logout started, player may still be in memory |
| `qbx_core:server:playerLoggedOut` | `source`; the player is no longer in memory |
| `QBCore:Server:OnJobUpdate` / `QBCore:Server:OnGangUpdate` | `source, PlayerJob` / `source, PlayerGang` |
| `QBCore:Server:SetDuty` | `source, onDuty` |
| `qbx_core:server:onGroupUpdate` | `source, groupName, grade?` (`grade` is nil when removed) |
| `QBCore:Server:OnMoneyChange` | `source, moneyType, amount, 'add'\|'remove'\|'set', reason` |
| `qbx_core:server:onSetMetaData` | `key, oldValue, newValue, source` (note the arg order) |
| `QBCore:Player:SetPlayerData` | `PlayerData` (every sync) |
| `qbx_core:server:onJobUpdate` / `qbx_core:server:onGangUpdate` | `name, Job\|nil`: a group **definition** changed (CreateJob/Upsert/Remove) |
| `qbx_core:server:onPaycheck` | `source, payment` (v1.24.0) |
| `QBCore:Server:OnPermissionUpdate` | `source` (deprecated permission API) |
| `qbx_core:server:jobsconverted` | After the `convertjobs` console command |
| `qbx_core:server:characterDeleted` | `citizenid`, **unreleased on main** after v1.24.0 |

**Server, networked**: `QBCore:Server:OnPlayerLoaded` is sent by the client after spawn; the core sets `Player(src).state.isLoggedIn = true`. Because a client can fire it, treat it only as a notification.

**Client**
| Event | Args |
|---|---|
| `QBCore:Client:OnPlayerLoaded` (local `TriggerEvent`, listen with `AddEventHandler` or `RegisterNetEvent`) | none; fired after spawn |
| `QBCore:Client:OnPlayerUnload` | none |
| `qbx_core:client:playerLoggedOut` | none; opens character select (server-only trigger) |
| `QBCore:Player:SetPlayerData` | `PlayerData` |
| `QBCore:Client:OnJobUpdate` / `QBCore:Client:OnGangUpdate` | `PlayerJob` / `PlayerGang` |
| `QBCore:Client:SetDuty` | `onDuty` |
| `qbx_core:client:onGroupUpdate` | `groupName, grade?` |
| `QBCore:Client:OnMoneyChange` | `moneyType, amount, operation, reason` |
| `hud:client:OnMoneyChange` | `moneyType, amount, isMinus, reason` (for HUDs) |
| `qbx_core:client:onSetMetaData` | `key, oldValue, newValue` |
| `qbx_core:client:onJobUpdate` / `qbx_core:client:onGangUpdate` | `name, Job\|nil` (definition) |
| `QBCore:Client:OnPermissionUpdate` | none |

**State bags**
- `Player(src).state.isLoggedIn` / `LocalPlayer.state.isLoggedIn`: true after spawn, false on unload.
- `hunger`, `thirst`, `stress` (replicated player state). The server mirrors client changes into metadata and clamps them to 0–100. **Clients can write their own state**, so never trust these values for rewards.
- `canUseWeapons` is set to false while `isdead`/`inlaststand`. `instance` holds the routing bucket set via `SetPlayerBucket`. `loadInventory` is used by ox_inventory.
- Entity state: `sessionId`, `persisted`, `initVehicle`, `vehicleid` (qbx_vehicles).
- GlobalState: `PlayerCount`, `MaxPlayers`, `PVPEnabled`.

## 9. PlayerData schema (`player.PlayerData`)
Defaults applied in `CheckPlayerData` (server/player.lua):
```lua
{
  source = 1,                 -- online only
  userId = 12,                -- users table id (1.22)
  citizenid = 'A1B2C3D4',     -- 'A.......' pattern, PK
  cid = 1,                    -- character slot index
  license = 'license2:...',   -- license2 preferred, else license
  name = 'FiveM name',
  money = { cash = 500, bank = 5000, crypto = 0 },  -- from config.money.moneyTypes
  charinfo = {
    firstname = 'Firstname', lastname = 'Lastname', birthdate = '00-00-0000',
    gender = 0,               -- 0 male, 1 female
    backstory = 'placeholder backstory', nationality = 'USA',
    phone = '5551234567', account = 'US0...QBX...', cid = 1,
    card = nil,               -- set by legacy SetCreditCard
  },
  job  = { name = 'unemployed', label = 'Civilian', payment = 10, type = nil,
           onduty = true, isboss = false, bankAuth = false,
           grade = { name = 'Freelancer', level = 0 } },
  gang = { name = 'none', label = 'No Gang', isboss = false, bankAuth = false,
           grade = { name = 'Unaffiliated', level = 0 } },
  jobs  = { police = 2 },     -- all held jobs: name -> grade (player_groups)
  gangs = { },                -- all held gangs
  position = vec4(...),       -- defaultSpawn for new characters
  lastLoggedOut = 1759800000, -- os.time()
  items = {},                 -- deprecated, always empty (use ox_inventory)
  metadata = {
    health = 200, armor = 0, hunger = 100, thirst = 100, stress = 0,
    isdead = false, inlaststand = false, ishandcuffed = false, tracker = false,
    injail = 0, jailitems = {}, status = {}, phone = {},
    bloodtype = 'O+',         -- random from config.player.bloodTypes
    dealerrep = 0, craftingrep = 0, attachmentcraftingrep = 0,
    currentapartment = nil,
    jobrep = { tow = 0, trucker = 0, taxi = 0, hotdog = 0 },
    callsign = 'NO CALLSIGN',
    fingerprint = '...', walletid = 'QB-12345678',
    criminalrecord = { hasRecord = false, date = nil },
    licences = { id = true, driver = true, weapon = false },  -- note the spelling 'licences'
    inside = { house = nil, apartment = { apartmentType = nil, apartmentId = nil } },
    phonedata = { SerialNumber = 12345678, InstalledApps = {} },
    optin = false,            -- admin opt-in
  },
}
```
`Player` object: `{ PlayerData, Offline: boolean, Functions = {...} }`. The `Functions.*` methods are deprecated wrappers around the exports (§17).

## 10. Multicharacter, character creation and spawn flow
Built-in multicharacter (`client/character.lua`), using ox_lib context menus and an input dialog:
1. On session start the client disables spawnmanager autospawn, starts a **solo tutorial session**, places a preview ped at a random `config.characters.locations` entry and shuts down the loading screen (`ShutdownLoadingScreen`/`ShutdownLoadingScreenNui`).
2. `lib.callback.await('qbx_core:server:getCharacters')` → `PlayerEntity[], allowedAmount` (per-license limit `playersNumberOfCharacters`, else 3).
3. **Play**: `qbx_core:server:loadCharacter(citizenid)` → `Login(source, citizenid)` (checks that the license owns the character, else drops for exploit) → `CreatePlayer` → `QBCore:Server:PlayerLoaded`. Then the spawn path:
   - if `qbx_apartments` is started → `apartments:client:setupSpawnUI`;
   - else if `qbx_spawn` is started → `qb-spawn:client:setupSpawns` + `qb-spawn:client:openUI`;
   - else spawn at the last position.
4. **Create**: `qbx_core:server:createCharacter(data)`. The server sanitizes it: first/last name and nationality as strings ≤ 50 chars, backstory ≤ 1000, gender numeric, the **cid computed server-side**, and the character limit enforced (v1.24.0). Then `Login(source, nil, newData)` and the starter items (`config/shared.lua`, given via ox_inventory). Spawn: without `qbx_spawn` → default spawn + `qb-clothes:client:CreateFirstCharacter`; else `startingApartment` → `apartments:client:setupSpawnUI` (qbx_properties handles apartment selection), or `qbx_core:client:spawnNoApartments`.
5. After spawn the client fires `QBCore:Server:OnPlayerLoaded` (net) and `QBCore:Client:OnPlayerLoaded` (local).
6. **Delete**: `lib.callback 'qbx_core:server:deleteCharacter'` (v1.24.0; the old net event is kept but deprecated). The license must own the character, and rows in `characterDataTables` are deleted.
7. **Logout**: `exports.qbx_core:Logout(src)` or `/logout` (admin) → back to selection.

External multicharacter: set `config/client.lua → characters.useExternalCharacters = true`. The docs FAQ says "set to false", which is **wrong**: the source returns early when the setting is `true`. Your resource must call `exports.qbx_core:Login(source, citizenid)` (or `Login(source, nil, newData)`), spawn the ped, fire the two loaded events and shut down the loading screen. If players stay stuck on the loading screen, set `setr loadscreen:externalShutdown false` or call the shutdown natives.

## 11. Groups: jobs, gangs, multijob, duty, paychecks
- Storage: the `player_groups` table holds (`citizenid`, `group`, `type` = `job`/`gang`, `grade`). The primary job and gang are stored as JSON in `players.job` and `players.gang`. Multijob is built in (since 1.7.0) and **cannot be disabled**; limit it with `qbx:max_jobs_per_player`/`qbx:max_gangs_per_player`.
- Default groups `unemployed` (job) and `none` (gang) are required. You cannot add players to them or remove players from them.
- Error codes: `player_not_found`, `job_not_found`, `gang_not_found`, `job_missing_grade`, `gang_missing_grade`, `max_jobs`, `max_gangs`, `unemployed`, `none`, `player_not_in_job`, `player_not_in_gang`. `SetJob`/`SetGang` return plain `false` (and only print an error) for an unknown group or grade.
- `HasGroup`/`HasPrimaryGroup`/`GetGroups(source)` index `QBX.Players[source].PlayerData` with no nil check, so they throw for a source that is not loaded (character select, dropped). Guard with `if not exports.qbx_core:GetPlayer(src) then return end` first (qbx_core `server/functions.lua`).
- Filter semantics of `HasGroup`/`HasPrimaryGroup`: `'police'`, `{'police','ambulance'}`, or `{ police = 2 }` (minimum grade). A filter string also matches the player's **citizenid**. `HasPrimaryGroup` checks only `job`/`gang`; `HasGroup` checks every held group.
- Duty: `job.onduty`. `ForceJobDefaultDutyAtLogin=true` resets it to `defaultDuty` at login. `QBCore:ToggleDuty` (net) toggles duty.
- Paychecks run every `paycheckTimeout` minutes, use the grade `payment`, skip off-duty players unless `offDutyPay`, may be paid from the society account (`paycheckSociety`, Renewed-Banking), and fire `qbx_core:server:onPaycheck`.
- Console commands: `convertjobs` copies the primary job/gang of every DB player into `player_groups` (needed when migrating). `cleanplayergroups` removes invalid rows.

```lua
-- server: hire into a second job without touching the primary job
local ok, err = exports.qbx_core:AddPlayerToJob(citizenid, 'mechanic', 1)
if not ok then lib.print.warn(err.code, err.message) end

-- members of a job (online + offline)
for _, row in ipairs(exports.qbx_core:GetGroupMembers('mechanic', 'job')) do
    print(row.citizenid, row.grade)
end
```

## 12. Items, vehicles, weapons, jobs data — how to add
| Data | Where | Format |
|---|---|---|
| Items | **`ox_inventory/data/items.lua`** | ox_inventory format. `qbx_core/shared/items.lua` is deprecated (empty); entries there are converted into ox_inventory at start **by the bridge** (written with `SaveResourceFile`, a restart is needed), but client/server item exports must still be added to ox_inventory by hand |
| Usable items | `exports.qbx_core:CreateUseableItem(name, cb)` or ox_inventory item `client.export`/`server.export` | |
| Jobs | `qbx_core/shared/jobs.lua` | `['name'] = { label, type?, defaultDuty, offDutyPay, grades = { [0] = { name, payment, isboss?, bankAuth? } } }`, **lowercase keys, numeric grades** |
| Gangs | `qbx_core/shared/gangs.lua` | `['name'] = { label, grades = { [0] = { name, isboss?, bankAuth? } } }` |
| Vehicles | `qbx_core/shared/vehicles.lua` | `model = { name, brand, model, price, category, type, hash = \`model\` }`; `type` is one of `automobile`/`bike`/`boat`/`heli`/`plane`/`submarine`/`trailer`/`train` and is required by `qbx.spawnVehicle` (otherwise it spawns a temporary vehicle to detect the type). Keys that start with a digit need `['5vigero']` |
| Weapons | `ox_inventory/data/weapons.lua` | `qbx_core/shared/weapons.lua` is deprecated and only feeds `QBCore.Shared.Weapons` for bridged scripts |
| Locations | deprecated (`shared/locations.lua` is empty) | |

```lua
-- shared/jobs.lua entry
['mechanic'] = {
    label = 'LS Customs',
    type = 'mechanic',
    defaultDuty = true,
    offDutyPay = false,
    grades = {
        [0] = { name = 'Trainee', payment = 50 },
        [1] = { name = 'Mechanic', payment = 75 },
        [2] = { name = 'Owner', payment = 150, isboss = true, bankAuth = true },
    },
},
```

## 13. Modules
### lib (`@qbx_core/modules/lib.lua`, global `qbx`)
Shared: `qbx.string.trim(s)`, `qbx.string.capitalize(s)`, `qbx.math.round(n, decimals?)`, `qbx.math.isFinite(v)`, `qbx.table.size(t)`, `qbx.table.mapBySubfield(t, field)`, `qbx.array.contains(arr, v)`, `qbx.getVehiclePlate(veh)` (trimmed), `qbx.generateRandomPlate(pattern?)` (`'........'`, `lib.string.random` syntax), `qbx.getCardinalDirection(entity)` → `'North'|'East'|'South'|'West'`. Tables: `qbx.armsWithoutGloves.{male,female}`, `qbx.duffelbagIndexes`.
Server: `qbx.spawnVehicle({ model, spawnSource = ped|vec3|vec4, warp? = bool|ped, props? = oxProps, bucket? })` → `netId, veh`. It uses `CreateVehicleServerSetter`, waits for an owner, applies the props through the owning client (3 attempts), sets orphan mode 2 and enables persistence. It raises an error on failure, so wrap it in `pcall`.
Client: `qbx.drawText2d({text, coords=vec2, scale?, font?, color?=vec4, width?, height?, enableDropShadow?, enableOutline?})`, `qbx.drawText3d({text, coords=vec3, scale?, disableDrawRect?, ...})`, `qbx.getEntityAndNetIdFromBagName(bagName)`, `qbx.entityStateHandler(key, cb(entity, netId, value, bagName))`, `qbx.deleteVehicle(veh)` → bool, `qbx.getVehicleDisplayName(veh)`, `qbx.getVehicleMakeName(veh)`, `qbx.getVehicleModName(veh, modType, modIndex)`, `qbx.getVehicleLiveryName(veh, livery)`, `qbx.getStreetName(coords)` → `{main, cross}`, `qbx.getZoneName(coords)`, `qbx.setVehicleExtra(veh, extra, enable)`, `qbx.resetVehicleExtras(veh)`, `qbx.setVehicleExtras(veh, {[id]=bool})`, `qbx.isWearingGloves()`, `qbx.isWearingDuffelbag()` (1.23), `qbx.loadAudioBank(bank, timeout?)`, `qbx.playAudio({audioName, audioRef, returnSoundId?, audioSource?, range?})` (deprecated → mana_audio).
```lua
-- server: spawn an owned car next to the player and warp them in
local ok, netId = pcall(qbx.spawnVehicle, {
    model = `sultan2`,
    spawnSource = GetPlayerPed(src),
    warp = true,
    props = { plate = 'QBX 123' },
})
if not ok then lib.print.error(netId) return end
-- client side: lib.waitFor(function() if NetworkDoesEntityExistWithNetworkId(netId) then return NetToVeh(netId) end end)
```
### playerdata (`@qbx_core/modules/playerdata.lua`, client)
Creates the global `QBX.PlayerData`, fills it from `exports.qbx_core:GetPlayerData()`, updates it on `QBCore:Player:SetPlayerData` and clears it on unload.
### hooks (`@qbx_core/modules/hooks`, server)
Requiring the module **registers the `registerHook`/`removeHooks` exports in your resource** and returns `triggerEventHooks(event, payload) → boolean`. A hook that returns `false` cancels the action; hooks taking more than 100 ms log a warning, and hooks are removed when their resource stops. qbx_core hook events: `addMoney`, `removeMoney`, `setMoney` with payload `{source, moneyType, amount}` (`source` is nil for offline players).
```lua
-- block crypto changes above 1000 per operation
exports.qbx_core:registerHook('addMoney', function(p)
    if p.moneyType == 'crypto' and p.amount > 1000 then return false end
end)
```
### logger (`@qbx_core/modules/logger`, server only)
`logger.log({ source, event, message, webhook?, color?, tags?, oxLibTags? })`. It always calls `lib.logger` (ox_lib providers: fivemanage, datadog, grafana loki), and also posts to a Discord webhook when one is given (queued and rate-limit aware). Colors: default, blue, red, green, white, black, orange, yellow, pink, lightgreen.
### utils (deprecated since 1.5.0)
`@qbx_core/modules/utils.lua` prints a warning on load. Replace it with `qbx.*` and ox_lib.

## 14. Permissions (ACE), commands, opt-in, bans, queue
- Use ACE in `permissions.cfg`: `add_ace group.admin command allow`, `add_ace group.admin admin allow`, inheritance `add_principal group.admin group.mod`, and `add_ace resource.qbx_core command allow`. Check access with `IsPlayerAceAllowed(src, 'admin')` or with `restricted = 'group.admin'` in `lib.addCommand`.
- Built-in commands (all `group.admin` except `ooc`, `me`, `id`, `job` and `gang`): `tp`, `tpm`, `togglepvp`, `addpermission`, `removepermission`, `openserver`, `closeserver`, `car`, `dv`, `givemoney`, `setmoney`, `job`, `setjob`, `changejob`, `addjob`, `removejob`, `gang`, `setgang`, `ooc`, `me`, `id`, `logout`, `deletechar`, `optin`.
- **Opt-in**: `config.server.requireOptIn = true` (default). Admin commands then do nothing until the admin runs `/optin` (stored in `metadata.optin`). Set it to false to disable the check.
- Closed server: only `qbadmin.join` can connect. Whitelist: `config.server.whitelist` plus the ACE in `whitelistPermission`.
- Queue: built in, with sub-queues defined by ACE predicates and an adaptive card. Disable it with `set qbx:enablequeue false`.
- Connect flow (deferrals): license check → duplicate license check → create the `users` row → ban check → whitelist → queue. The database checks time out after 30 s.

## 15. qb-core bridge
Enabled by default (`setr qbx:enablebridge true`). qbx_core declares `provide 'qb-core'` and handles the `exports['qb-core']:...` export events, so `exports['qb-core']:GetCoreObject()` returns a compat object on both client and server.
**Works**: `QBCore.Functions.*` (GetPlayer, GetPlayerByCitizenId, GetOfflinePlayerByCitizenId, GetPlayers, GetQBPlayers, GetDutyCount, CreateUseableItem, Notify, HasItem → ox_inventory, SpawnVehicle/CreateVehicle, Kick, the TriggerCallback/CreateCallback family, the client GetPlayerData/GetClosest*/DrawText/Progressbar → ox_lib, and so on); `Player.Functions.*` wrappers (AddMoney, SetJob, SetMetaData, AddItem/RemoveItem → ox_inventory, `info`/`amount` item compat); `QBCore.Commands.Add` → `lib.addCommand`; `QBCore.Shared.Items` (built from ox_inventory), `.Jobs`, `.Gangs`, `.Vehicles`, `.Weapons`, `.StarterItems`; the `qb-core` DrawText exports; the `QBCore:Client:VehicleInfo` baseevents relay; the `QBCore:Notify` event.
**Does not work, or errors**: qb-inventory (assert); `Player.Functions.SetInventory`, `AddField`, `AddMethod`, `GetCardSlot`, `QBCore.Player.CheckPlayerData` (error); `QBCore.Functions.UseItem` (no-op); `QBCore.Functions.AddItem(s)/UpdateItem/RemoveItem` on shared items (warns, the item must exist in ox_inventory); the legacy `QBCore:GetObject` event (not implemented); direct SQL against `players.job`/`gang` for multijob, or custom multijob tables (data corruption); job grades given as strings; overriding player methods (allowed but warned, blocked when `qbx:allowmethodoverrides false`). Other Qbox resources provide their own QB names: `qbx_vehiclekeys` provides `qb-vehiclekeys`, `qbx_npwd` provides `qb-npwd`, and so on (see the ecosystem file).
Disable the bridge (`setr qbx:enablebridge false`) only after every resource is native. The bridge also runs the `shared/items.lua` → ox_inventory conversion.

## 16. Migration QBCore → Qbox
Server setup: use the recipe or copy its cfgs; change job/gang grades to **numbers**; convert the inventory with ox_inventory's QB converter (back up first); run `qbx_core.sql` (adds `last_logged_out` and `userId` and fixes the `citizenid` collation to `utf8mb4_unicode_ci`); start the server and run `convertjobs` in the console.

Code mapping:
| QBCore | Qbox |
|---|---|
| `local QBCore = exports['qb-core']:GetCoreObject()` | nothing; call `exports.qbx_core:*` directly |
| `QBCore.Functions.GetPlayer(src)` | `exports.qbx_core:GetPlayer(src)` |
| `Player.Functions.AddMoney('bank', 100, 'r')` | `exports.qbx_core:AddMoney(src, 'bank', 100, 'r')` |
| `Player.Functions.SetJob('police', 1)` | `exports.qbx_core:SetJob(src, 'police', 1)` |
| `Player.Functions.SetMetaData('hunger', 50)` | `exports.qbx_core:SetMetadata(src, 'hunger', 50)` |
| `Player.Functions.AddItem('bread', 1)` | `exports.ox_inventory:AddItem(src, 'bread', 1)` |
| `QBCore.Functions.HasItem(src, 'x')` | `exports.ox_inventory:Search(src, 'count', 'x') > 0` |
| `QBCore.Functions.CreateCallback` / `TriggerCallback` | `lib.callback.register` / `lib.callback.await` |
| `QBCore.Functions.Notify(msg, 'error')` | `exports.qbx_core:Notify(msg, 'error')` or `lib.notify` |
| `QBCore.Functions.GetPlayerData()` | `QBX.PlayerData` (playerdata module) |
| `QBCore.Functions.GetPlate(veh)` | `qbx.getVehiclePlate(veh)` |
| `QBCore.Functions.SpawnVehicle` (client) | server `qbx.spawnVehicle{...}` |
| `QBCore.Shared.Jobs/Gangs/Vehicles/Weapons` | `GetJobs()` / `GetGangs()` / `GetVehiclesByName()` / `GetWeapons()` |
| `QBCore.Shared.Items` | `exports.ox_inventory:Items()` |
| `QBCore.Commands.Add` | `lib.addCommand(name, { restricted = 'group.admin', params = {...} }, cb)` |
| `PlayerData.job.grade.level` as a string | number |
| `exports['qb-core']:DrawText(t, pos)` / `HideText()` | `lib.showTextUI(t, { position = pos })` / `lib.hideTextUI()` |
| qb-target / qb-menu / qb-input / PolyZone | ox_target / `lib.registerContext` / `lib.inputDialog` / `lib.zones` |

```lua
-- BEFORE (QBCore)
local QBCore = exports['qb-core']:GetCoreObject()
QBCore.Functions.CreateCallback('shop:buy', function(source, cb, item)
    local Player = QBCore.Functions.GetPlayer(source)
    if Player.Functions.RemoveMoney('cash', 100) then
        Player.Functions.AddItem(item, 1)
        cb(true)
    else
        cb(false)
    end
end)

-- AFTER (Qbox)
local ALLOWED = { bread = true, water = true }
lib.callback.register('shop:buy', function(source, item)
    if not ALLOWED[item] then return false end
    if not exports.ox_inventory:CanCarryItem(source, item, 1) then return false end
    if not exports.qbx_core:RemoveMoney(source, 'cash', 100, 'shop-purchase') then return false end
    return exports.ox_inventory:AddItem(source, item, 1) and true or false
end)
```

## 17. Deprecations and breaking changes 2024–2026
**Deprecated** (they still work, but avoid them in new code):
| Item | Since | Replacement |
|---|---|---|
| `modules/utils.lua` | 1.5.0 (2024-01) | `modules/lib.lua`, ox_lib |
| `AddPermission`/`RemovePermission`/`HasPermission`/`GetPermission`, `config.server.permissions` | 1.8.0 (2024-03) | ACE (`IsPlayerAceAllowed`) |
| `shared/items.lua`, `shared/weapons.lua`, `shared/locations.lua`, `GetLocations` | 1.15.1 (2024-07) | ox_inventory data files |
| `Player.Functions.*` (SetJob, SetMetaData, AddItem, Save, Logout…) | 1.22.0 (2024-12) | exports. The money wrappers still lack the `@deprecated` tag, but prefer the exports |
| Bridge QB callbacks, `QBCore.Debug/ShowError/ShowSuccess`, `Commands.Add` | bridge | `lib.callback`, `lib.print`, `lib.addCommand` |
| `qbx.playAudio` | **UNVERIFIED** (marked in the 1.24 source) | mana_audio |
| `qbx_core:server:deleteCharacter` net event | 1.24.0 | callback of the same name |
| `config.server.requireOptIn` (tagged deprecated, but still the active switch) | — | ACE |

**Breaking or behavior changes**
- **1.5.0** (2024-01-28): lib module introduced, utils deprecated, queue sub-queues.
- **1.7.0** (2024-02-29): built-in multijob/multigang with the `player_groups` table. Run the SQL and `convertjobs`. External multijob resources become incompatible. LoginV2 removed.
- **1.8.0** (2024-03-11): permissions deprecated in favor of ACE; `qbx:setjob_replaces` convar added; client `GetJob`/`GetGang` exports.
- **1.11.0** (2024-04-20): ox_lib ≥ 3.20.0 required.
- **1.15.0** (2024-06-24): starter items moved from the server config to `config/shared.lua` (`fix!`).
- **1.18.0–1.18.1** (2024-08/09): native ox_inventory compatibility. `inventory:framework "qbx"` and ox_inventory ≥ 2.42.1 are required, and the core refuses to start otherwise.
- **1.19.0** (2024-09-19): hard stop without OneSync Infinity; uppercase group names reported as errors; player-method overrides warned and blockable; vehicle persistence; `GetVehicleClass`.
- **1.22.0** (2024-12-02): `users` table and `userId`; Player.Functions deprecated; money hooks; `type` field in `shared/vehicles.lua`. **1.22.3**: minimum artifact 10731.
- **1.23.0** (2025-04-15): nested metadata (`'a.b'`); clients cache groups from the server; `commitToFile` persistence for runtime group edits.
- **1.24.0** (2026-08-22): `/optin` enforced for admin commands (default on). Server-side validation: money amounts must be finite and non-negative (rounded); hunger, thirst and stress clamped to 0–100; character creation sanitized, with the cid set server-side and the character limit enforced. Character deletion moved to a callback; bans checked by discord and ip; SQL injection fixed in `SearchPlayers`; `qbx_core:server:onPaycheck`; full vehicle persistence; config-driven Discord presence.
- **Unreleased on `main`** (after 1.24.0, as of 2026-10-07): `qbx_core:server:characterDeleted(citizenid)`, `config.characters.enableHealthInitialization`, vitals preserved across character select, overflowing group grades rejected, fixed handler leaks on job/gang updates.

## 18. Best practices and common mistakes
- Do: resolve the player on the server from `source` and use exports with a `reason` string for money; use `HasGroup(src, { job = minGrade })` for authorization; use `lib.callback` instead of QB callbacks; check the returned `ok, err` from group exports.
- Do: read `QBX.PlayerData` on the client only for UI. Re-check everything on the server.
- Do: run `/optin` as admin (or disable `requireOptIn`) before reporting that admin commands are broken.
- Mistake: passing a citizenid to `GetPlayer`. Use `GetPlayerByCitizenId`; `GetPlayer('ABC123')` is treated as a FiveM identifier.
- Mistake: string job grades (`['0']`), uppercase job names, or adding items only to `qbx_core/shared/items.lua`.
- Mistake: assuming bank cannot go negative. Only cash and crypto are in `dontAllowMinus`.
- Mistake: trusting the `hunger`/`thirst`/`stress` state bags or the `QBCore:Server:OnPlayerLoaded` net event for rewards.
- Mistake: running qb-inventory, an external multijob resource that writes its own tables, or `qbx_smallresources` modules that duplicate other resources.
- Mistake: calling `GetVehicleClass` on an empty server (it errors), or `qbx.spawnVehicle` without `pcall`.
- Mistake: `useExternalCharacters = false` to "disable" the built-in multicharacter. It must be `true`.
- Mistake: `set qbx:enablebridge false` instead of `setr`. The client-side bridge then stays enabled.

## 19. Sources
- https://github.com/Qbox-project/qbx_core (tag v1.24.0; files `fxmanifest.lua`, `server/*.lua`, `client/*.lua`, `modules/*.lua`, `config/*.lua`, `shared/*.lua`, `bridge/qb/**`, `types.lua`, `qbx_core.sql`)
- https://github.com/Qbox-project/qbx_core/releases (v1.5.0–v1.24.0 notes) and `git log v1.24.0..main`
- https://github.com/Qbox-project/qbox-docs (source of docs.qbox.re, commit 260c0ec 2026-09-24): `docs/resources/qbx_core/**`, `docs/introduction/{installation,converting,faq}.mdx`
- https://docs.qbox.re/installation · https://docs.qbox.re/converting · https://docs.qbox.re/faq · https://docs.qbox.re/resources/qbx_core/convars
- https://github.com/Qbox-project/txAdminRecipe (`server.cfg`, `ox.cfg`, `permissions.cfg`, `qbox.yaml`)
- https://github.com/communityox/ox_inventory (`modules/bridge/qbx/server.lua`: `CanUseItem`, qbx_core ≥ 1.18.1)
