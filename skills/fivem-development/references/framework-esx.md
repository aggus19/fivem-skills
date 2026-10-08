# ESX Legacy (es_extended + esx_lib)

Baseline: es_extended 1.15.2 — verified 2026-10-07 (released 2026-09-06; `main` is 3 commits ahead with a multichar fade-in fix only)

Repo: https://github.com/esx-framework/esx_core (GPL-3.0) · Docs: https://docs.esx-framework.org/en · Addons: https://github.com/esx-framework/ESX-Legacy-Addons · Recipe: https://github.com/esx-framework/esx-recipes
Other core resources (multicharacter, identity, skin, menus, notify, textui, progressbar, context, cron, loading screen) and addons (society, billing, addon accounts/inventories, datastore, license, status): [esx-ecosystem.md](esx-ecosystem.md).

## Contents
1. Versions and what changed (1.10 → 1.15.2)
2. Install, requirements, resource order
3. Config options and convars
4. Getting the ESX object (and why fields are snapshots)
5. Player data model and database schema
6. Server API: `ESX.*`
7. xPlayer methods
8. Static players: `ESX.Player`, `ESX.ExtendedPlayers`
9. OneSync helpers and the vehicle class
10. Commands and permissions
11. Callbacks
12. Client API: `ESX.*`, `ESX.Game`, `ESX.Streaming`, `ESX.Scaleform`, `ESX.UI`
13. Shared helpers: `ESX.Table`, `ESX.Math`, timers, locale
14. Events (server and client) and trust
15. `ESX.SecureNetEvent`
16. Items, usable items, inventory backends (default, esx_inventory, ox_inventory)
17. Jobs, grades, duty, paycheck
18. esx_lib (xLib) API
19. Security pitfalls in 1.15.2
20. Performance notes
21. Migrating old ESX code
22. Common mistakes
23. Docs vs source mismatches, UNVERIFIED items
24. Sources

---

## 1. Versions and what changed (1.10 → 1.15.2)

| Release | Date | Changes that matter to scripts |
|---|---|---|
| 1.10 | 2023-07 | MultiSpawns, `Config.AdminGroups`, Discord admin logs, `esx:spawnVehicle` event, `ESX.GetAccount` (client); **removed** `xPlayer.updateCoords` |
| 1.10.1 | 2023-07 | **Removed** client `esx:removeWeapon` event: use `xPlayer.removeWeapon` |
| 1.10.2 | 2023-09 | Health/armour saved in metadata, `ESX.GetNumPlayers`, metadata sub-values, stops incompatible resources (essentialmode, …) |
| 1.10.3 | 2024-01 | **Requires artifact ≥ 6188** (`GetPlayerIdentifierByType`), `ESX.Game.SpawnObject` without callback networking, underflow check in `removeAccountMoney` |
| 1.10.6 | 2024-06 | `esx:setGroup` event, `ESX.PlayerData.vehicle/seat`, `ESX.ValidateType/AssertType`, `ESX.Math.Random`, `ESX.TriggerClientEvent` |
| 1.10.8 | 2024-10 | **BREAKING:** metadata and `xPlayer.set` are no longer synced via state bags; client gets them through `esx:updatePlayerData`. Account names case-insensitive |
| 1.11.0 | 2024-11 | **Requires FXServer ≥ 10188** (`SetEntityOrphanMode`). Job duty system, `ESX.SecureNetEvent`, `ESX.playerId`/`ESX.serverId`, GlobalState player count, orphan mode for vehicles, interaction system, multichar/skin/skinchanger rewrites, playtime tracking, spawnmanager dependency removed, routing buckets in multichar |
| 1.12.1 | 2025-01 | `ESX.GetItems()` |
| 1.12.2 | 2025-01 | Reverted ESX.Items/Players/Jobs restructuring from 1.12.0 |
| 1.12.3 | 2025-01 | `imports.lua` uses an ox_lib-style `require` |
| 1.13.0 | 2025-07 | Server **vehicle class** (`ESX.CreateExtendedVehicle`), lazy locales, **static player methods**, `ESX.AwaitClientCallback`, `xPlayer.executeCommand`, `vehicleType` arg for `ESX.OneSync.SpawnVehicle`, `ESX.RefreshItems`/`ESX.AddItems` at runtime, density multipliers |
| 1.13.1 | 2025-08 | `esx:identifier` convar (identifier type); `ESX.GetIdentifier` now errors if the identifier is missing |
| 1.13.2 | 2025-08 | **Default inventory UI split into `esx_inventory`** (menu in `esx_menu_default`); inventory/loadout synced in PlayerData |
| 1.13.3 | 2025-08 | `ESX.ExtendedPlayers`, **SSN** per player (`users.ssn`, migration) |
| 1.13.4/1.13.5 | 2025-08 / 2026-05 | **Auto-migrations on startup**, `isNew` player state bag, esx_notify position, `jobs.type` column (migration v1.13.5) |
| 1.14.0 | 2026-07-17 | **esx_lib (xLib)** introduced: DUI, entity, raycast, keybinds (`ESX.RegisterInput` now wraps `xLib.addKeybind`); es_extended loads `@esx_lib/imports.lua` |
| 1.14.1 | 2026-08-16 | `Config.CommandPermissions` (per-command groups), English fallback for missing locale keys, `xLib.isEnhanced()`, Medal.tv integration, ox_inventory override uses export proxy, `ESX.CreateJob` can add grades to existing jobs, many bug fixes (cron, progressbar, points loop) |
| 1.15.0 | 2026-09-01 | "Refactor core resources": most helpers now aliases of xLib (`shared/compat.lua`, `client/compat.lua`, `server/compat.lua`), new **esx_loadingscreen**, resource versions exposed as server info (`<resource>-version`), `inventory:accounts` default includes `black_money` |
| 1.15.1 | 2026-09-06 | Callback handlers cleaned up when the owning resource stops |
| 1.15.2 | 2026-09-06 | `registerCompat` callbacks: owner-resource lifecycle (ESX callbacks registered by a resource are removed when it stops) |
| 1.16.0 | unreleased | Branch `v1.16.0` exists (player class split into modules, `esx_whitelist`, fixes for negative-balance and pickup-dupe exploits). **UNVERIFIED** until released |

## 2. Install, requirements, resource order

Recommended: txAdmin → "Popular Recipes" → **ESX Legacy** (recipe `esx-framework/esx-recipes`, branch `legacy`). It downloads cfx-server-data, `esx_core` `[core]`, `ESX-Legacy-Addons` `[esx_addons]`, oxmysql, ox_lib, pma-voice, bob74_ipl, sd-phone, and imports `[SQL]/legacy.sql`. Use MariaDB (docs warn against XAMPP).

Hard requirements (checked in `server/main.lua`):
- FXServer **≥ 10188** (`SetEntityOrphanMode` must exist) — in practice use the current Recommended build.
- OneSync **on** (Infinity). `legacy`/`off` is rejected at connect, except on GTA V Enhanced (`xLib.isEnhanced()`).
- `oxmysql` connected before players join; `esx_lib` started before `es_extended`.
- es_extended **stops** `essentialmode`, `es_admin2`, `basic-gamemode`, `mapmanager`, `fivem-map-*`, `qb-core`, `default_spawnpoint` on start.

```cfg
# order from the official recipe server.cfg
ensure chat
ensure oxmysql
ensure esx_lib          # before es_extended (es_extended's manifest loads @esx_lib/imports.lua)
ensure es_extended
ensure [core]           # esx_menu_*, esx_notify, esx_textui, esx_context, esx_progressbar, esx_identity, esx_skin, skinchanger, esx_multicharacter, cron, esx_inventory, esx_loadingscreen
ensure [standalone]     # ox_lib, pma-voice, ...
ensure [esx_addons]
# es_extended needs these ACEs to manage principals for groups:
add_ace resource.es_extended command.add_ace allow
add_ace resource.es_extended command.add_principal allow
add_ace resource.es_extended command.remove_principal allow
add_ace resource.es_extended command.stop allow
```
With ox_inventory: `ensure ox_lib` → `oxmysql` → `esx_lib` → `es_extended` → `ox_inventory` (ox_inventory must start after the framework; ESX auto-detects it). Remove/disable `esx_inventory` (it errors when the default inventory is disabled).

## 3. Config options and convars

`es_extended/shared/config/main.lua`:

| Option | Default | Notes |
|---|---|---|
| `Config.Locale` | convar `esx:locale` → txAdmin locale → `"en"` | |
| `Config.LocaleFallback` | convar `esx:localeFallback` ≠ `"false"` | missing keys fall back to English |
| `Config.CustomInventory` | `false`; auto `"ox"` when ox_inventory is present | other inventories set their own value |
| `Config.Accounts` | `bank`, `black_money`, `money` (`label`, `round`) | adding an account here adds it to every player |
| `Config.StartingAccountMoney` | `{ bank = 50000 }` | |
| `Config.StartingInventoryItems` | `false` | table `{ bread = 2 }` (default inventory only) |
| `Config.DefaultSpawns` | 1 spawn | random pick |
| `Config.AdminGroups` | `{ owner = true, admin = true }` | **deprecated** (comment says removal in 1.15, still present); still used by `Core.IsPlayerAdmin` |
| `Config.CommandPermissions` | per command list of groups | source of truth for built-in command ACLs |
| `Config.ValidCharacterSets` | all false (`el`,`sr`,`he`,`ar`,`zh-cn`) | name validation |
| `Config.EnablePaycheck` / `PaycheckInterval` | `true` / 7 min | |
| `Config.LogPaycheck` | `false` | Discord |
| `Config.EnableSocietyPayouts` | `false` | pay from society account (needs esx_society + esx_addonaccount) |
| `Config.MaxWeight` | `24` (kg; ox gets `*1000`) | |
| `Config.SaveDeathStatus` | `true` | |
| `Config.EnableDebug` | `false` | enables debug commands/prints in several resources |
| `Config.DefaultJobDuty` / `OffDutyPaycheckMultiplier` | `true` / `0.5` | |
| `Config.Multichar` | auto: esx_multicharacter present | |
| `Config.Identity` | `true` | load firstname/lastname/... columns |
| `Config.DistanceGive` | `4.0` | |
| `Config.AdminLogging` | `false` | |
| `Config.Identifier` | convar `esx:identifier`, default `"license"` | |
| `Config.EnableDefaultInventory` | `CustomInventory == false` | F2 menu (esx_inventory) |

`shared/config/adjustments.lua`: `DisableHealthRegeneration`, `DisableVehicleRewards`, `DisableNPCDrops`, `DisableDispatchServices` (true), `DisableScenarios` (true), `DisableAimAssist`, `DisableVehicleSeatShuff`, `DisableDisplayAmmo`, `EnablePVP` (true), `EnableWantedLevel`, `RemoveHudComponents[1..22]`, `Multipliers` (ped/vehicle densities), `CustomAIPlates` pattern, `DiscordActivity` (rich presence: appId, assets, buttons, presence placeholders).
`shared/config/logs.lua`: `Config.DiscordLogs.Webhooks` (`default`, `Chat`, `UserActions`, `Resources`, `Paycheck`, …) — webhooks are in a **server-only** file; keep them there.
`shared/config/weapons.lua`: `Config.Weapons` (name, label, components, tints, ammo, throwable).

Convars: `esx:locale`, `esx:localeFallback`, `esx:identifier`, `xLib:debug`, `xLib:callbackTimeout` (ms, default 300000), `xLib:rateLimiterMaxEntries` (4096), `xLib:tokenMaxEntries` (4096), color tokens `esx:brand-color` `esx:darkest-color` `esx:dark-color` `esx:mid-color` `esx:light-color` `esx:lightest-color`, `inventory:accounts` (ox, default `["money","black_money"]`). es_extended **sets** `inventory:framework "esx"` and `inventory:weight` (replicated) when a custom inventory is active. GlobalState written: `playerCount`, `<job>:count`.

## 4. Getting the ESX object

```lua
-- fxmanifest.lua (recommended)
shared_scripts { '@es_extended/imports.lua' }        -- defines ESX; client keeps ESX.PlayerData/ESX.PlayerLoaded in sync
-- optional, only if you use xLib directly in your resource:
shared_scripts { '@esx_lib/imports.lua', '@es_extended/imports.lua' }
-- or, without imports:
local ESX = exports.es_extended:getSharedObject()
```
`imports.lua` also: sets `ESX.currentResourceName`, defines a global `OnPlayerData(key, val, last)` hook (client), defines `ESX.Player`/`ESX.ExtendedPlayers` (server), loads `ESX.Class` (client), and installs `require`/`ESX.require`/`ESX.load`/`ESX.loadJson` when ox_lib is **not** running.

**Snapshot semantics:** the shared object crosses resources through an export, so tables are **copied** and functions become references. In your resource, `xPlayer.job`, `xPlayer.accounts`, `ESX.Players`, `ESX.Jobs` are copies taken at call time; methods (`xPlayer.getJob()`) run inside es_extended and are live. Re-fetch the xPlayer in every handler, never cache it, never assign fields (`xPlayer.job = ...` does nothing to the real player).

## 5. Player data model and database schema

Identifier: `GetPlayerIdentifierByType(src, Config.Identifier)` with the `license:` prefix **stripped** (`ESX.GetIdentifier(src)` → `"abc123..."`). With esx_multicharacter: `char<N>:<identifier>` (e.g. `char1:abc123...`). `xPlayer.license` keeps the prefixed form (`license:abc123...`).

`users` (es_extended.sql + addon columns): `identifier` VARCHAR(60) PK, `ssn` VARCHAR(11) UNIQUE, `accounts` LONGTEXT (JSON `{bank=..,money=..}`), `group`, `inventory` LONGTEXT (JSON `{item=count}`; ox stores its slot array), `job`, `job_grade`, `loadout` LONGTEXT, `metadata` LONGTEXT (health, armor, lastPlaytime, jobDuty, custom), `position` LONGTEXT (`{x,y,z,heading}`); esx_identity adds `firstname`, `lastname`, `dateofbirth`, `sex` (`m`/`f`), `height`; esx_skin adds `skin`; multichar adds `disabled`. `legacy.sql` also has `status`, `is_dead`, `id`, `last_property`, `created_at`, `last_seen`, `phone_number`, `pincode`.
`jobs`: `name` PK, `label`, `type` (default `civ`, e.g. `leo`, `ems`), `whitelisted`. `job_grades`: `id`, `job_name`, `grade`, `name`, `label`, `salary`, `skin_male`, `skin_female` (JSON). A job without grades is ignored. `items`: `name` PK, `label`, `weight`, `rare`, `can_remove` (unused with ox_inventory).
Other tables in `legacy.sql`: `owned_vehicles` (`owner`, `plate`, `vehicle` JSON props, `type`, `job`, `stored`, `parking`, `pound`), `rented_vehicles`, `vehicles`, `vehicle_categories`, `addon_account(_data)`, `addon_inventory(_items)`, `datastore(_data)`, `billing`, `licenses`, `user_licenses`, `society_moneywash`, `multicharacter_slots`, `fine_types`, `banking`, `whitelist`.
Migrations run automatically at start (`server/migration/v*/`), recorded in resource KVP `esx_migration:<version>`; console `resetmigrations` re-runs them. Some migrations print "Server restart required" in a loop until you restart.

Client `ESX.PlayerData` after `esx:playerLoaded`: `identifier`, `accounts` (array of `{name,money,label,round,index}`), `inventory`, `loadout`, `weight`, `maxWeight`, `money`, `job` (`id,name,label,type,onDuty,grade,grade_name,grade_label,grade_salary,skin_male,skin_female`), `coords` (spawn coords; afterwards read live through a metatable), `skin`, `metadata`, `variables`, `name`, `firstName`, `lastName`, `dateofbirth`, `sex`, `height`, `dead`, plus `ped`, `vehicle`, `seat`, `weapon`, `group` maintained by actions/events. `ssn` is not sent to the client.
Player state bags (set server-side): `identifier`, `license` (not replicated), `job`, `group`, `name` (replicated), `isNew` (not replicated, only for new characters). Vehicle state bag `VehicleProperties` is applied by the entity owner.

## 6. Server API: `ESX.*`

| Function | Behaviour |
|---|---|
| `ESX.GetPlayerFromId(src)` → xPlayer? | nil until loaded; always nil-check |
| `ESX.GetPlayerFromIdentifier(identifier)` → xPlayer? | identifier as stored (with `charN:` under multichar) |
| `ESX.GetPlayerIdFromIdentifier(identifier)` → number? | |
| `ESX.IsPlayerLoaded(src)` → boolean | |
| `ESX.GetExtendedPlayers(key?, val?, minimal?)` | all xPlayers; `('job','police')`; `val` table → `{ police = {...}, ambulance = {...} }`; `minimal=true` → source ids |
| `ESX.GetNumPlayers(key?, val?)` | count; `('job','police')` uses cached job counts |
| `ESX.GetPlayers()` | = `GetPlayers()` (strings) |
| `ESX.GetIdentifier(src)` → string | asserts (throws) if the identifier type is missing; returns `ESX-DEBUG-LICENCE` in FxDK |
| `ESX.Trace(msg)` | prints when `Config.EnableDebug` |
| `ESX.TriggerClientEvent(name, idOrIds, ...)` | packs payload once for arrays |
| `ESX.RegisterCommand(name|names, group|groups, cb, allowConsole?, suggestion?)` | see §10 |
| `ESX.RegisterUsableItem(name, function(src, itemName, ...) end)` / `ESX.UseItem(src, item, ...)` / `ESX.GetUsableItems()` | |
| `ESX.GetItems()` / `ESX.GetItemLabel(name)` | with ox: ox item list / ox label |
| `ESX.RefreshItems()` → count, `ESX.AddItems({ {name,label,weight?,rare?,canRemove?} })` | default inventory only (INSERT IGNORE into `items`) |
| `ESX.GetJobs(jobType?)` | waits until jobs loaded; filter by `type` string or list |
| `ESX.DoesJobExist(job, grade)` | |
| `ESX.RefreshJobs()` / `ESX.RefreshJob(name)` → boolean | reload from DB; events `esx:jobsRefreshed`, `esx:jobRefreshed`, `esx:jobRemoved` |
| `ESX.CreateJob(name, label, grades, jobType?)` | runtime job/grades creation (DB transaction); `grades = { {grade=0,name='recruit',label='Recruit',salary=100,skin_male={},skin_female={}} }`; event `esx:jobCreated` |
| `ESX.GetVehicleType(model, playerId, cb?)` | asks a client; cached per model |
| `ESX.DiscordLog(name, title, color, message)` / `ESX.DiscordLogFields(name, title, color, fields)` | |
| `ESX.RegisterPlayerFunctionOverrides(index, { method = function(self) return function(...) end end })` / `ESX.SetPlayerFunctionOverride(index)` | xPlayer method overrides (all registered overrides are applied at creation) |
| `ESX.CreatePickup(type, name, count, label, src, components?, tint?, coords?)` | default inventory only |
| `ESX.CreateExtendedVehicle(owner, plate, coords4)` / `ESX.GetExtendedVehicleFromPlate(plate)` | §9 |
| `ESX.RegisterServerCallback`, `ESX.TriggerClientCallback`, `ESX.AwaitClientCallback`, `ESX.DoesServerCallbackExist` | §11 |
| `ESX.OneSync.*` | §9 |
| `ESX.GetConfig(key?)`, `ESX.GetWeapon*`, `ESX.Table`, `ESX.Math`, `ESX.SetTimeout`, … | shared, §13 |
| `ESX.Players`, `ESX.Jobs`, `ESX.Items` | tables (snapshots outside es_extended) |

## 7. xPlayer methods

Fields: `source`/`playerId`, `identifier`, `license`, `ssn`, `name`, `group`, `job`, `accounts`, `inventory`, `loadout`, `weight`, `maxWeight`, `metadata`, `variables`, `admin`, `paycheckEnabled`, `lastPlaytime`, `spawned`.

**Identity / state**
- `getIdentifier()`, `getSSN()`, `getSource()`/`getPlayerId()`, `getName()`, `setName(name)` (updates `name` state bag only, not the DB identity)
- `getCoords(vector?, heading?)` → table `{x,y,z[,heading]}`, or `vector3`/`vector4` when `vector=true`
- `setCoords(coords)` (vector3/vector4/table with `heading`)
- `getPlayTime()` (seconds, saved + session), `kick(reason)` (= `DropPlayer`)
- `set(key, value)` / `get(key)` — session variables, synced to client `ESX.PlayerData.variables`, **not saved**
- `getMeta(index?, subIndex?)`, `setMeta(index, value)` (number/string/table), `setMeta(index, subKey, subValue)` (nested), `clearMeta(index, subKeys?)` — **saved** in `users.metadata`, synced to client
- `triggerEvent(name, ...)`, `executeCommand(command)` (client `ExecuteCommand`), `showNotification(msg, type?, length?, title?, position?)`, `showAdvancedNotification(sender, subject, msg, textureDict, iconType, flash, saveToBrief, hudColorIndex)`, `showHelpNotification(msg, thisFrame?, beep?, duration?)`

**Money / accounts** (`money`, `bank`, `black_money`; names case-insensitive)
- `getMoney()`, `setMoney(n)`, `addMoney(n, reason?)`, `removeMoney(n, reason?)` (cash = `money` account)
- `getAccount(name)` → `{name, money, label, round, index}`?, `getAccounts(minimal?)` (minimal → `{bank=n,...}`)
- `setAccountMoney(name, n, reason?)`, `addAccountMoney(name, n, reason?)`, `removeAccountMoney(name, n, reason?)` → `true` on success. They **throw** (`error`) for amounts ≤ 0, non-numbers or unknown accounts. **`removeAccountMoney` does not refuse insufficient funds in 1.15.2** (balance can go negative; fixed in the unreleased 1.16 branch). Always check the balance first:
```lua
local price = 500                                   -- server-side price, never from the client
local bank = xPlayer.getAccount('bank')
if not bank or bank.money < price then return xPlayer.showNotification('Not enough money', 'error') end
xPlayer.removeAccountMoney('bank', price, 'shop purchase')
```
- `togglePaycheck(bool)`, `isPaycheckEnabled()`

**Items** (default inventory; with ox_inventory these are proxied, see §16)
- `getInventory(minimal?)`, `getInventoryItem(name)` → `{name,label,count,weight,usable,rare,canRemove}`?, `hasItem(name)` → item, count | `false`
- `addInventoryItem(name, count)` → bool — **does not check weight**; call `canCarryItem` first
- `removeInventoryItem(name, count)` → bool (false if not enough), `setInventoryItem(name, count)`
- `canCarryItem(name, count)`, `canSwapItem(firstItem, firstCount, testItem, testCount)`, `getWeight()`, `getMaxWeight()`, `setMaxWeight(kg)`

**Weapons** (default inventory only; no-ops/false with ox_inventory)
- `addWeapon(name, ammo)`, `removeWeapon(name)`, `hasWeapon(name)`, `getWeapon(name)` → index, weapon, `getLoadout(minimal?)`
- `addWeaponAmmo(name, n)`, `removeWeaponAmmo(name, n)`, `updateWeaponAmmo(name, n)`
- `addWeaponComponent(name, comp)`, `removeWeaponComponent(name, comp)`, `hasWeaponComponent(name, comp)`, `setWeaponTint(name, tint)`, `getWeaponTint(name)`

**Job / group**
- `getJob()`, `setJob(name, grade, onDuty?)` (invalid job → warning, no change; `onDuty` default `Config.DefaultJobDuty`, unemployed always off), `refreshJob()`
- `getGroup()`, `setGroup(group)` (moves the `identifier.license:...` principal between `group.*`), `isAdmin()` (ACE `command` or group in `Config.AdminGroups`)

## 8. Static players: `ESX.Player`, `ESX.ExtendedPlayers` (1.13+)

Server-only, from `imports.lua`. `ESX.Player(srcOrIdentifier)` returns a proxy whose every method call goes through `exports.es_extended:RunStaticPlayerMethod(src, method, ...)` — no serialized copy of the player, always live, cheap to create. It has `.src` but **no data fields** (use `getJob()`, not `.job`).
```lua
local player = ESX.Player(source)                   -- nil if not loaded
if player then player.addAccountMoney('bank', 100, 'bonus') end
for _, p in ipairs(ESX.ExtendedPlayers('job', 'police')) do p.showNotification('Dispatch: 10-31') end
```

## 9. OneSync helpers and the vehicle class

Server:
- `ESX.OneSync.SpawnVehicle(model, coords, heading, props, cb?, vehicleType?)` → netId (awaits when no cb). Uses `CreateVehicleServerSetter`, sets orphan mode 2 and state bag `VehicleProperties` (applied by the owner client). Needs a player online to resolve the vehicle type unless you pass `vehicleType` (`automobile`, `bike`, `boat`, `heli`, `plane`, `submarine`, `trailer`, `train`).
- `ESX.OneSync.SpawnObject(model, coords, heading, cb?)`, `SpawnPed(model, coords, heading, cb?)`, `SpawnPedInVehicle(model, vehicle, seat, cb?)` → netId.
- `ESX.OneSync.GetPlayersInArea(srcOrCoords, maxDistance?, ignore?, bucket?)` → `{ {id, ped=netId, coords, dist} }`; `GetClosestPlayer(...)` → `{id, ped, coords, dist}` (empty table if none; default distance 100).
- `GetPedsInArea/GetObjectsInArea/GetVehiclesInArea(coords, maxDistance, modelFilter?)` → netIds; `GetClosestPed/Object/Vehicle(coords, modelFilter?)`.

Vehicle class (`owned_vehicles` must have the row with `stored = 1`):
```lua
local xVehicle = ESX.CreateExtendedVehicle(xPlayer.getIdentifier(), plate, vector4(x, y, z, h))  -- spawns, marks stored=0
if xVehicle then
    xVehicle:getNetId(); xVehicle:getEntity(); xVehicle:getOwner(); xVehicle:getModelHash()
    xVehicle:setProps(props); xVehicle:setPlate('NEW123'); xVehicle:setOwner(newIdentifier)
    xVehicle:delete('legion_garage', false)                  -- despawn + stored=1 (+ parking or pound column)
end
-- events: esx:createdExtendedVehicle (obj), esx:deletedExtendedVehicle (obj)
```

## 10. Commands and permissions

```lua
ESX.RegisterCommand({ 'givecash', 'gc' }, 'admin', function(xPlayer, args, showError)
    -- xPlayer is false when run from console (allowConsole = true)
    args.target.addMoney(args.amount, 'admin givecash')
end, true, {
    help = 'Give cash',
    validate = true,                                        -- arg count must match
    arguments = {
        { name = 'target', help = 'Player id or "me"', type = 'player' },   -- player → xPlayer, playerId → number
        { name = 'amount', help = 'Amount', type = 'number',
          Validator = { validate = function(v) return v > 0 and v <= 100000 end, err = 'Invalid amount' } },
    },
})
```
Arg types: `number`, `player`, `playerId`, `string` (rejects numbers), `item` (must exist), `weapon`, `coordinate`, `merge` (rest of line), `any`. ESX registers the command restricted and runs `add_ace group.<g> command.<name> allow`, so the group is checked through ACE principals (`add_principal identifier.license:xxx group.admin` is added on load).
Groups: `user` (default), `admin`, `owner` (any string works). A player with ACE `command` gets `admin` on first creation. `superadmin` in the DB is downgraded to `admin`.
Built-in commands and their groups come from `Config.CommandPermissions`: `setcoords/tp`, `setjob`, `car`, `cardel/dv`, `fix/repair`, `setaccountmoney`, `giveaccountmoney`, `removeaccountmoney`, `giveitem`, `giveweapon`, `giveammo`, `giveweaponcomponent`, `clearall/clsall`, `refreshjobs`, `refreshitems`, `clearinventory`, `clearloadout`, `setgroup`, `save`, `saveall`, `goto`, `bring`, `kill`, `freeze`, `unfreeze`, `setdim/setbucket`, `players`, `noclip`, `tpm`, `coords` (admins); `clear/cls`, `group`, `job`, `info`, `playtime` (all). **Gotcha:** an entry missing or empty in `Config.CommandPermissions` falls back to `{ "user" }` — i.e. everyone.
For new permission checks in your resources prefer ACE (`IsPlayerAceAllowed(src, 'myres.admin')`) or `xPlayer.getGroup()`.

## 11. Callbacks

Since 1.14/1.15 every ESX callback runs on **xLib.callback** (an ox_lib-derived implementation; event names `__xLib_cb_<name>`). Timeout: `xLib:callbackTimeout` (300 s).
```lua
-- server (classic signature: source, cb, ...)
ESX.RegisterServerCallback('myres:getStock', function(source, cb, shopId)
    if type(shopId) ~= 'number' then return cb(nil) end
    cb(Stock[shopId])
end)
-- client
ESX.TriggerServerCallback('myres:getStock', function(stock) print(stock) end, 1)
local stock = ESX.AwaitServerCallback('myres:getStock', 1)          -- 1.13+, inside a thread

-- server → client
ESX.RegisterClientCallback('myres:getHeading', function(cb) cb(GetEntityHeading(PlayerPedId())) end) -- client: cb first
ESX.TriggerClientCallback(src, 'myres:getHeading', function(h) end)                                     -- server
local h = ESX.AwaitClientCallback(src, 'myres:getHeading')                                             -- server
ESX.DoesServerCallbackExist(name) / ESX.DoesClientCallbackExist(name)
```
Direct xLib style (return values, ox_lib-like):
```lua
xLib.callback.register('myres:ping', function(source, a) return 'pong', a end)       -- server
local r1, r2 = xLib.callback.await('myres:ping', false, 42)                           -- client: (name, delay|false, ...)
```
ox_lib's `lib.callback` works equally on ESX servers that run ox_lib. Callbacks registered with `ESX.Register*Callback` are removed when the registering resource stops (1.15.1/1.15.2).

## 12. Client API

**Core:** `ESX.PlayerData`, `ESX.PlayerLoaded`, `ESX.IsPlayerLoaded()`, `ESX.GetPlayerData()`, `ESX.SetPlayerData(key, val)` (local only; fires `esx:setPlayerData`), `ESX.playerId`, `ESX.serverId`, `ESX.GetAccount(name)`, `ESX.SearchInventory(items, count?)`, `ESX.SpawnPlayer(skin, coords, cb)`, `ESX.DisableSpawnManager()`, `ESX.HashString(str)` (→ `~INPUT_…~`), `ESX.GetVehicleType(model)` (client variant), `ESX.ShowInventory()`.
**UI wrappers** (error if the resource is missing): `ESX.ShowNotification(msg, type?, length?, title?, position?)` (esx_notify; types `info`, `success`, `error`, …), `ESX.TextUI(msg, type?)` / `ESX.HideUI()`, `ESX.Progressbar(msg, ms, options)` / `ESX.CancelProgressbar()`, `ESX.OpenContext(position, elements, onSelect, onClose, canClose?)`, `ESX.PreviewContext`, `ESX.CloseContext()`, `ESX.RefreshContext(elements?, position?)`, `ESX.ShowAdvancedNotification(...)`, `ESX.ShowHelpNotification(msg, thisFrame?, beep?, duration?)`, `ESX.ShowFloatingHelpNotification(msg, coords)`, `ESX.DrawMissionText(msg, ms)`, `ESX.UI.ShowInventoryItemNotification(add, item, count)`.
**Menus (legacy):** `ESX.UI.Menu.Open(type, namespace, name, data, submit, cancel, change?, close?)`, `.Close(type, ns, name, cancel?)`, `.CloseAll(cancel?)`, `.GetOpened(type, ns, name)` / `.IsOpen`, `.GetOpenedMenus()`, `.RegisterType(type, open, close)` — types `default`, `dialog`, `list` from esx_menu_* (see esx-ecosystem.md).
**ESX.Game** (aliases of xLib.game/entity): `SpawnVehicle(model, coords, heading, cb?, networked?)` (returns vehicle when no cb; refuses > 424 units from the player), `SpawnLocalVehicle`, `DeleteVehicle`, `SpawnObject(model, coords, cb?, networked?)`, `SpawnLocalObject`, `DeleteObject`, `GetVehicleProperties(veh)`, `SetVehicleProperties(veh, props)`, `GetClosestPlayer(coords?)` → player, distance (-1 if none), `GetClosestPed/Object/Vehicle(coords?, modelFilter?)`, `GetClosestEntity(entities, isPlayers, coords?, filter?)`, `GetPlayers(onlyOthers?, keyValue?, returnPeds?)`, `GetPeds(onlyOthers?)`, `GetVehicles()`, `GetObjects()`, `GetPlayersInArea(coords, max)`, `GetVehiclesInArea(coords, max)`, `IsSpawnPointClear(coords, max)`, `GetVehicleInDirection()`, `IsVehicleEmpty(veh)`, `GetPedMugshot(ped, transparent?)`, `Teleport(entity, coords, cb?)`, `StopRaycasting(r)`, `IsRaycastActive(r)`, `GetRaycastResult(r)`, `ESX.Game.Utils.DrawText3D(coords, text, size?, font?)`. There is **no `ESX.Game.StartRaycasting`** in 1.15.2: use `xLib.raycast.Start(depth, ...)`.
**ESX.Streaming:** `RequestModel(model, cb?)`, `RequestStreamedTextureDict`, `RequestNamedPtfxAsset`, `RequestAnimSet`, `RequestAnimDict`, `RequestWeaponAsset` (each returns the asset when no cb). `RequestModel` returns nil for models not in the CD image.
**ESX.Scaleform:** `ShowFreemodeMessage(title, msg, sec)`, `ShowBreakingNews(title, msg, bottom, sec)`, `ShowPopupWarning(title, msg, bottom, sec)`, `ShowTrafficMovie(sec)`, `Utils.RequestScaleformMovie(name)`, `Utils.RunMethod(sf, method, returnValue?, ...)`.
**Input / interaction / points:** `ESX.RegisterInput(name, label, mapper, key, onPress, onRelease?)` (→ `xLib.addKeybind`), `ESX.RegisterInteraction(name, onPress, condition?)` / `ESX.RemoveInteraction(name)` / `ESX.GetInteractKey()` (shared "esx_interact" key, default E), `ESX.Point:new({ coords, distance, hidden?, enter, leave, inside })` with `:delete()`, `:toggle(hidden?)`.

## 13. Shared helpers

`ESX.Table.SizeOf/Set/IndexOf/LastIndexOf/Find/FindIndex/Filter/Map/Reverse/Clone/Concat/Join/TableContains/Sort/ToArray/Wipe`, `ESX.Math.Round(v, decimals?)`, `GroupDigits(v)`, `Trim(v)`, `Random(min, max)`, `GetHeadingFromCoords(a, b)`, `ESX.SetTimeout(ms, cb)` → id / `ESX.ClearTimeout(id)`, `ESX.Await(cb, err?, timeout?, interval?)` (= `xLib.waitFor`, default timeout 5000 ms, `false` = none), `ESX.GetRandomString(len)`, `ESX.GetConfig(key?)`, `ESX.GetWeapon(name)` → index, data, `ESX.GetWeaponFromHash(hash)`, `ESX.GetWeaponList(byHash?)`, `ESX.GetWeaponLabel(name)`, `ESX.GetWeaponComponent(weapon, comp)`, `ESX.DumpTable(t)`, `ESX.Round`, `ESX.ValidateType(v, ...types)` → ok, err, `ESX.AssertType`, `ESX.IsFunctionReference(v)`, `ESX.IsValidLocaleString(str, allowDigits?)`.
Locale (`@es_extended/locale.lua` + your `locales/*.lua` returning a table): `Translate(key, ...)` / `_`, `TranslateCap(key, ...)` / `_U`. Set `Config.Locale` in your resource (usually `GetConvar('esx:locale', 'en')`).

## 14. Events and trust

Server (local `AddEventHandler`; triggered by es_extended — trusted):

| Event | Params |
|---|---|
| `esx:playerLoaded` | playerId, xPlayer, isNew |
| `esx:playerDropped` | playerId, reason |
| `esx:playerLogout` | playerId, cb? (trigger it to log a player out; multichar relog) |
| `esx:playerSaved` | playerId, xPlayer |
| `esx:setJob` | playerId, job, lastJob |
| `esx:jobDataRefreshed` | playerId, job, lastJob |
| `esx:setGroup` | playerId, group, lastGroup |
| `esx:setAccountMoney` / `esx:addAccountMoney` / `esx:removeAccountMoney` | playerId, accountName, money, reason |
| `esx:onAddInventoryItem` / `esx:onRemoveInventoryItem` | playerId, itemName, newCount (default inventory) |
| `esx:jobsRefreshed`, `esx:jobRefreshed` (name, job), `esx:jobRemoved` (name, reason), `esx:jobCreated` (name, job) | |
| `esx:createdExtendedVehicle` / `esx:deletedExtendedVehicle` | vehicle object |

**Client-originated net events** (`TriggerServerEvent` from es_extended client — anyone can fake them, validate everything): `esx:onPlayerDeath` (data), `esx:enteringVehicle` (plate, seat, netId), `esx:enteringVehicleAborted`, `esx:enteredVehicle` (plate, seat, displayName, netId), `esx:exitedVehicle` (same), `esx:onPlayerSpawn`, `esx:onPlayerJoined`, `esx:updateWeaponAmmo`, `esx:useItem`, `esx:giveInventoryItem`, `esx:removeInventoryItem`, `esx:onPickup`. Never award anything solely because a client sent `esx:onPlayerDeath`/`esx:enteredVehicle`.

Client:

| Event | Params |
|---|---|
| `esx:playerLoaded` (net) | playerData, isNew, skin |
| `esx:onPlayerLogout` | — |
| `esx:onPlayerSpawn` (local) | — |
| `esx:onPlayerDeath` (local) | `{victimCoords, killedByPlayer, deathCause, killerCoords?, distance?, killerServerId?, killerClientId?}` |
| `esx:setJob` | job, lastJob |
| `esx:jobDataRefreshed` | job, lastJob |
| `esx:setGroup` | group, lastGroup |
| `esx:setAccountMoney` | account |
| `esx:addInventoryItem` / `esx:removeInventoryItem` | item, count, showNotification |
| `esx:setMaxWeight`, `esx:setInventory` | |
| `esx:setPlayerData` (local) | key, val, last |
| `esx:updatePlayerData` | key, val (`metadata`, `variables`) |
| `esx:enteringVehicle` (vehicle, plate, seat, netId), `esx:enteringVehicleAborted`, `esx:enteredVehicle` / `esx:exitedVehicle` (vehicle, plate, seat, displayName, netId), `esx:vehicleSeatChanged` (seat), `esx:pauseMenuActive` (bool), `esx:playerPedChanged` (ped), `esx:weaponChanged` (hash|false), `esx:loadingScreenOff`, `esx:restoreLoadout` | local |
| `esx:showNotification`, `esx:showAdvancedNotification`, `esx:showHelpNotification` | net, same args as the functions |

```lua
-- client: react to job changes without polling
RegisterNetEvent('esx:setJob', function(job, lastJob)
    if job.name == 'police' and job.onDuty then StartPoliceBlips() else StopPoliceBlips() end
end)
-- server: per-player init (local event, so AddEventHandler, never RegisterNetEvent)
AddEventHandler('esx:playerLoaded', function(playerId, xPlayer, isNew)
    if isNew then xPlayer.addInventoryItem('phone', 1) end
end)
```

## 15. `ESX.SecureNetEvent`

Client-side only (1.11+): `ESX.SecureNetEvent(eventName, handler)`. It registers a net event that **ignores triggers whose `source` is `''`** — i.e. local `TriggerEvent` calls from other client resources/executors — so only the server can fire it. Handlers are removed when the registering resource stops; errors are re-thrown. It does not exist on the server; server net events still need full validation.
```lua
ESX.SecureNetEvent('myres:client:setDoorState', function(doorId, locked)
    Doors[doorId].locked = locked
end)
```

## 16. Items, usable items, inventory backends

- **Default (es_extended)**: items from the `items` table, counts in `users.inventory`; xPlayer item/weapon methods; pickups (`ESX.CreatePickup`). UI is the separate `esx_inventory` resource (F2 menu built on `esx_menu_default`, `exports.esx_inventory:ShowInventory()`); it only renders and triggers `esx:useItem`/`esx:giveInventoryItem`/`esx:removeInventoryItem`.
- **ox_inventory**: auto-detected (`Config.CustomInventory = "ox"`). `ESX.Items` mirrors ox items; xPlayer methods are overridden: `getInventoryItem(name, metadata?)`, `addInventoryItem(name, count, metadata?, slot?)`, `removeInventoryItem(name, count, metadata?, slot?)`, `setInventoryItem`, `canCarryItem(name, count, metadata?)`, `canSwapItem`, `setMaxWeight`, `hasItem(name, metadata?)` call ox; **weapon methods are no-ops** (weapons are items); accounts listed in `inventory:accounts` are mirrored as items (`money`, `black_money`). Prefer `exports.ox_inventory:*` directly for metadata/slots. Usable items: define in ox `data/items.lua` (`server.export`/client `export`) or `ESX.RegisterUsableItem` (ox calls it for items without its own handler).
- **Other inventories**: set `Config.CustomInventory` per their instructions and use their API.
```lua
ESX.RegisterUsableItem('bandage', function(source, itemName)
    local xPlayer = ESX.GetPlayerFromId(source)
    if not xPlayer or not xPlayer.removeInventoryItem(itemName, 1) then return end  -- consume first
    xPlayer.triggerEvent('myres:client:applyBandage', 25)   -- health natives are client-side
end)
-- client
ESX.SecureNetEvent('myres:client:applyBandage', function(amount)
    local ped = PlayerPedId()
    SetEntityHealth(ped, math.min(GetEntityMaxHealth(ped), GetEntityHealth(ped) + amount))
end)
```
Detect backend: `GetResourceState('ox_inventory') == 'started'` or `ESX.GetConfig('CustomInventory')`.

## 17. Jobs, grades, duty, paycheck

Jobs load from `jobs` + `job_grades` at start (wait with `ESX.GetJobs()` which blocks until loaded). Duty: `xPlayer.job.onDuty` (stored in `metadata.jobDuty`), toggle with `xPlayer.setJob(job.name, job.grade, not job.onDuty)`. Paycheck every `Config.PaycheckInterval`: unemployed → "Welfare Check", off-duty → `salary * OffDutyPaycheckMultiplier`, with `EnableSocietyPayouts` the salary comes from `society_<job>` (no payout if the society is broke). Job counts: `GlobalState['police:count']` (readable on clients). Change grades/salaries in the DB then `/refreshjobs` or `ESX.RefreshJob(name)`.

## 18. esx_lib (xLib) API

`esx_lib` (manifest `version '0.01'`, `legacyversion '1.15.0'`) is a lazy-loading module library modelled on ox_lib (several files are LGPL-3.0 ox_lib code). Import with `shared_script '@esx_lib/imports.lua'` → global `xLib`; modules load on first access (`xLib.<module>`), shared + side files from `esx_lib/imports/<module>/`. It also overrides `require` with `xLib.require`.

| Module | API |
|---|---|
| `xLib.addKeybind(data)` (client) | `{name, description, defaultMapper='keyboard', defaultKey, disabled?, onPressed(self), onReleased(self)}` → keybind with `:disable(bool)`, `:remove()`, `:getCurrentKey()`, `:isControlPressed()`, `.currentKey` |
| `xLib.cache` (client) | `ped`, `vehicle`, `seat`, `weapon`, `playerId`, `serverId`, `coords` (live); emits local `xLib:cache:<key>` (value, previous); polls every 100 ms |
| `xLib.callback` | server: `xLib.callback(name, playerId, cb, ...)`, `.await(name, playerId, ...)`, `.register(name, fn(source, ...))`, `.registerCompat(name, fn(source, cb, ...), owner?)`; client: `xLib.callback(name, delay|false, cb, ...)`, `.await(name, delay, ...)`, `.register`, `.registerCompat(name, fn(cb, ...))` |
| `xLib.class(copy?)` | class with `:new(...)` calling `constructor` |
| `xLib.colors` (client) | brand palette from convars |
| `xLib.dui` (client) | `xLib.dui:new({url, width, height, debug?})` → `.dictName`, `.txtName`, `:setUrl(url)`, `:sendMessage(tbl)`, `:sendMouseMove(x,y)`, `:sendMouseDown/Up(button)`, `:sendMouseWheel(dx,dy)`, `:remove()` |
| `xLib.entity` (client) | `closest(entities, isPlayers, coords?, filter?)`, `EnumerateWithinDistance(...)`, `Teleport(entity, coords, cb?)` |
| `xLib.game` (client) | everything behind `ESX.Game.*` (camelCase: `spawnVehicle`, `getVehicleProperties`, …) |
| `xLib.interactions` (client) | `register(name, onPress, condition?)`, `remove(name)`, `getInteractKey()` |
| `xLib.isEnhanced()` | true on GTA V Enhanced (server: `gamename` convar) |
| `xLib.math` | `clamp`, `toNumber`, `toScalars`, `toVector`, `normalToRotation`, `toRGBA`, `hexToRGBA`, `toHex`, `groupDigits`, `round`, `interpolate`, `lerp`, `inverseLerp`, `remap`, + ESX-style `Round`, `GroupDigits`, `Trim`, `Random`, `GetHeadingFromCoords` |
| `xLib.medal` (client) | `getConfig()`, `triggerClip(publicKey?, eventName?, clipOptions?)` — posts to the local Medal.tv client (`localhost:12665`); `Config.Medal.enabled = true` by default in `esx_lib/config.lua` |
| `xLib.onesync` (server) | backing for `ESX.OneSync.Get*` (uses `ESX.Players`; call through `ESX.OneSync`) |
| `xLib.overload(name, types, cb, obj?)` | typed overloads |
| `xLib.point` / `xLib.points` (client) | `xLib.points.create(coords, distance, hidden, enter, leave, inside?)` → handle, `.remove(h)`, `.hide(h, bool)`, `.startLoop()` |
| `xLib.pubsub` | server: `subscribe(src, topic)`, `unsubscribe`, `publish(topic, data)` → count, `subscribers(topic)`, `isSubscribed`, `clear(topic)`; client: `on(topic, fn(data, topic))`, `off(topic, fn?)`. Topics `^[%w_:%.%-]+$`, namespace by resource; clients cannot subscribe themselves |
| `xLib.rateLimiter(opts)` (server) | token bucket `{capacity, refill, interval, maxEntries?, staleMs?}` → `:consume(key, cost?)` → ok, retryAfterMs; `:retryAfter`, `:reset(key)`, `:clear()`, `:size()` |
| `xLib.raycast` (client) | `GetShapeTestResult(handle)`, `FromScreen(depth, ...)` → target, hit, coords, normal, material, entity; `Start(depth, ...)` → object with `.result`, `:Stop()`, `:IsActive()` (runs every frame while active) |
| `xLib.require` / `xLib.load` / `xLib.loadJson` | module loader (`@resource.module` supported) |
| `xLib.scaleform`, `xLib.streaming` | behind `ESX.Scaleform`/`ESX.Streaming`; streaming also has `requestAudioBank` |
| `xLib.string` | `normalize`, `capitalize`, `toSnake`, `toCamel`, `toPascal`, `escapePattern`, `matchSafe`, `before`, `after`, `contains`, `replace`, `randomHex(len)`, `uuid()` |
| `xLib.table` | `isArray`, `searchForKey`, `filter`, `deepcopy`, `merge`, `dump`, `sizeOf`, `set`, `indexOf`, `lastIndexOf`, `find`, `findIndex`, `map`, `reverse`, `clone`, `concat`, `join`, `contains`, `sort`, `toArray`, `wipe` |
| `xLib.timeout` | `setTimeout(ms, cb)` → id, `clearTimeout(id)` |
| `xLib.token` (server) | one-time tokens: `create({source?, ttl=30000, data?})` → id, `consume(id, source?)` → data/true/nil, `remove(id)`, `reset(source)`, `clear()`, `size()` |
| `xLib.verify(value, types, throw?)` | type checks |
| `xLib.waitFor(cb, err?, timeout?, interval?)` | poll until non-nil |
| `xLib.triggerClientEvent(name, idOrIds, ...)` (export) | packed broadcast |

```lua
-- server: rate-limit + one-time token for a two-step action
local limiter = xLib.rateLimiter({ capacity = 5, refill = 1, interval = 2000 })
RegisterNetEvent('myres:server:requestCraft', function(recipeId)
    local src = source
    if not limiter:consume(src) then return end
    local id = xLib.token.create({ source = src, ttl = 10000, data = { recipe = recipeId } })
    TriggerClientEvent('myres:client:confirmCraft', src, id)
end)
RegisterNetEvent('myres:server:confirmCraft', function(tokenId)
    local data = xLib.token.consume(tokenId, source)       -- nil if forged, expired, reused or other player
    if not data then return end
    -- validate recipe, distance, items server-side, then craft
end)
```

## 19. Security pitfalls in 1.15.2

- `removeAccountMoney`/`removeMoney` do not refuse insufficient balance → check `getAccount(name).money >= amount` first (dupe/negative-balance exploit class; fixed only in the unreleased 1.16 branch).
- `addInventoryItem` ignores weight → `canCarryItem` first; `removeInventoryItem` returns false when short → check its return before giving rewards.
- Money methods `error()` on amounts ≤ 0 → validate `type(n) == 'number' and n > 0 and n == math.floor(n)` before calling, or a malicious client can crash your handler mid-transaction.
- Default-inventory pickups: no claim lock in 1.15.2 (pickup-dupe fixed in the 1.16 branch). Prefer ox_inventory on public servers.
- Do not `RegisterNetEvent` framework-local events (`esx:playerLoaded`, `esx:setJob`, `esx:playerDropped`) on the server — use `AddEventHandler`, otherwise clients can trigger them.
- Removing a key from `Config.CommandPermissions` opens that command to everyone (fallback group `user`).
- `esx_lib` ships Medal.tv clip integration enabled with a public key; disable `Config.Medal.enabled` if you don't want it.
- Never trust ESX client data (`ESX.PlayerData`) in server logic — read xPlayer on the server.

## 20. Performance notes

- Player saves: every 10 min (batched prepared UPDATE), on drop, on txAdmin shutdown/restart warning; `/save`, `/saveall`. Don't add your own per-player save loops for core data.
- `ESX.GetExtendedPlayers()` copies every xPlayer across the export boundary — in hot paths use `ESX.GetExtendedPlayers(key, val, true)` (ids) + `ESX.Player(id)`, or `GlobalState['job:count']`/`ESX.GetNumPlayers('job', name)`.
- Client loops: es_extended's action loop runs at 500 ms, xLib cache at 100 ms; use `ESX.PlayerData`/`xLib.cache` instead of your own polling. `xLib.raycast.Start` runs every frame — stop it.
- `esx_addonaccount` broadcasts every balance change to all clients (`-1`) — avoid high-frequency society money writes.
- Points (`ESX.Point`/`xLib.points`) share one loop; prefer them (or ox_lib zones/ox_target) over per-resource distance loops.

## 21. Migrating old ESX code

| Old | Current |
|---|---|
| `TriggerEvent('esx:getSharedObject', function(obj) ESX = obj end)` | `@es_extended/imports.lua` or `exports.es_extended:getSharedObject()` (the event still exists for compatibility) |
| `MySQL.Async.fetchAll` / `mysql-async` / `ghmattimysql` | oxmysql `MySQL.query.await(sql, params)` |
| `RegisterServerEvent` | `RegisterNetEvent` |
| `xPlayer.getMoney() - x` then `setMoney` | `removeMoney` after a balance check |
| `xPlayer.identifier` with `steam:` | license (prefix stripped), `charN:` under multichar; use `xPlayer.getIdentifier()` |
| `TriggerClientEvent('esx:removeWeapon'/'esx:addWeapon', ...)` | `xPlayer.removeWeapon`/`addWeapon` (events now error) |
| `ESX.SetTimeout` from old shared files | still available (xLib.timeout) |
| `ESX.UI.Menu` default/dialog | still works; for new UIs prefer `ESX.OpenContext` or ox_lib `lib.registerContext`/`lib.inputDialog` |
| `esx:playerLoaded` client with `xPlayer.job` read once | listen to `esx:setJob` too |
| `xPlayer.updateCoords`, `driftTyres` props | removed |
| `ESX.JobsLoaded` / `esx:jobsLoaded` (1.13.1) | not present in 1.15.2: use `ESX.GetJobs()` (blocks until loaded) / `esx:jobsRefreshed` |
| `Config.AdminGroups` for commands | `Config.CommandPermissions` |
| statebag-synced metadata (≤1.10.7) | `esx:updatePlayerData` / `ESX.PlayerData.metadata` |
| spawnmanager-driven spawn | ESX spawns itself (`ESX.SpawnPlayer`), spawnmanager auto-spawn is disabled if present |

## 22. Common mistakes

- Using `source` after a `Wait`/await without `local src = source` first.
- Caching an xPlayer table across ticks or reading `xPlayer.job` after `setJob` in another resource (snapshot).
- Taking prices/amounts/item names from the client.
- Calling `ESX.GetPlayerFromId` in `playerConnecting` (not loaded yet) — use `esx:playerLoaded`.
- Spawning vehicles on the client for persistent/owned vehicles → use `ESX.OneSync.SpawnVehicle` or the vehicle class.
- Starting `es_extended` before `esx_lib`/`oxmysql`, or running both `esx_inventory` and ox_inventory.
- Expecting `xPlayer.addWeapon` to work with ox_inventory.
- Assuming `cron` weekday `1` is Monday (it is `os.date('*t').wday`: 1 = Sunday).
- Running ESX with `onesync legacy` (rejected) or an old artifact (connect refused below 10188).

## 23. Docs vs source mismatches, UNVERIFIED items

- docs.esx-framework.org documents `esx:playerJumping` (client/server) and `xPlayer.updatePlayerData` — not present in 1.15.2 source. Treat as removed.
- `ESX.JobsLoaded`/`esx:jobsLoaded` from the 1.13.1 notes are not in 1.15.2 source.
- `Config.AdminGroups` comment says "Will be removed in ESX 1.15" — still present in 1.15.2.
- Behaviour of ox_inventory calling `ESX.RegisterUsableItem` handlers is from ox_inventory's ESX bridge, not verified here (**UNVERIFIED** for current ox_inventory).
- 1.16.0 content (branch `v1.16.0`) is **UNVERIFIED** until a release is published.

## 24. Sources

- https://github.com/esx-framework/esx_core (tag 1.15.2 and `main` @ fe59ca0, 2026-09-07; files: `[core]/es_extended/**`, `[core]/esx_lib/**`, `[core]/esx_inventory/**`, `[SQL]/legacy.sql`, `server.cfg`)
- https://github.com/esx-framework/esx_core/releases (1.10 → 1.15.2 notes)
- https://github.com/esx-framework/esx_core/compare/main...v1.16.0 (unreleased fixes)
- https://github.com/esx-framework/esx-recipes (`recipe.yaml`, `server.cfg`)
- https://github.com/esx-framework/esx-legacy-documentation (source of the docs site, 2026-09-06)
- https://docs.esx-framework.org/en/tutorial/install
- https://docs.esx-framework.org/en/esx_core/es_extended/server/xplayer
