# Qbox ecosystem (resources other than qbx_core)
Baseline: qbx_core v1.24.0 — verified 2026-10-07

## Contents
1. How to read this file
2. Resource map (active vs archived)
3. Vehicles: qbx_vehicles, qbx_garages, qbx_vehiclekeys, qbx_vehicleshop, qbx_customs, qbx_mechanicjob
4. Health and emergency: qbx_medical, qbx_ambulancejob, qbx_police
5. Player-facing: qbx_spawn, qbx_properties, qbx_management, qbx_cityhall, qbx_idcard, qbx_hud, qbx_radialmenu, qbx_adminmenu, qbx_scoreboard, qbx_density, qbx_seatbelt
6. qbx_smallresources (deprecated)
7. Phone and radio: NPWD integration, mm_radio
8. Jobs, crime and activities (no or minimal API)
9. Third-party resources in the recipe
10. Patterns and common mistakes
11. Sources

## 1. How to read this file
Core APIs live in [framework-qbox.md](framework-qbox.md). This file lists the **Qbox-project** resources, which repos are active, and their public exports, as found in the source on 2026-10-07 (shallow clones of each repo's default branch). Version = `version` in `fxmanifest.lua`, plus the latest GitHub release when one exists. Most repos show a push date of 2026-09-26 because of an org-wide template sync, so the push date does not show real activity.
Note: there is **no `qbx_policejob` repo**. The police resource is `qbx_police` (its README still says "qbx_policejob").

## 2. Resource map
**Active** (in the recipe `qbox.yaml` unless marked *):
| Category | Resources (fxmanifest version / latest release) |
|---|---|
| Vehicles | qbx_vehicles 1.4.2 (v1.4.2 2024-12-19), qbx_garages 1.1.4 (v1.1.4 2024-11-11), qbx_vehiclekeys 1.0.3 (release v1.0.2 2024-12-01), qbx_vehicleshop 1.0.0, qbx_vehiclesales 1.0.0, qbx_customs 0.1.1, qbx_mechanicjob 1.0.0, qbx_carwash 1.0.0, qbx_seatbelt 1.0.0 |
| Health / emergency | qbx_medical 1.0.0, qbx_ambulancejob 1.0.0, qbx_police 1.0.0 |
| Player / UI | qbx_spawn 0.1.1 (v0.1.1 2025-01-12), qbx_properties 0.0.1, qbx_management 1.4.0 (v1.4.0 2025-09-06), qbx_cityhall, qbx_idcard, qbx_hud 0.1.0, qbx_radialmenu 0.1.0, qbx_adminmenu 0.1.0, qbx_scoreboard, qbx_density 1.0.1, qbx_chat_theme, qbx_binoculars 1.1.1, qbx_smallresources 0.2.0 (**deprecated**) |
| Phone / radio | qbx_npwd 1.0.0, npwd_qbx_garages 1.1.0*, npwd_qbx_mail 1.0.0*, mm_radio 0.2.1 (v0.2.1 2025-04-15) |
| Jobs | qbx_busjob, qbx_garbagejob, qbx_newsjob, qbx_taxijob, qbx_towjob, qbx_truckerjob, qbx_recyclejob 2.1.0, qbx_vineyard, qbx_diving 1.1.1, qbx_divegear 1.0.1, qbx_scrapyard |
| Crime | qbx_bankrobbery, qbx_jewelery, qbx_storerobbery, qbx_truckrobbery 1.1.1, qbx_houserobbery, qbx_drugs, qbx_weed, qbx_pawnshop |
| Activities | qbx_lapraces, qbx_streetraces, qbx_fireworks 1.3.0 |
| Infra | txAdminRecipe, qbxsql*, qbx_db_backup 1.1.0* (2026-09-18, Qbox dashboard backups), qbx_grafana_map*, qbx-lua* (linter/formatter/LSP), qbx-editor* (VS Code/Zed), mhacking, safecracker |

**Archived or unmaintained. Do not install these on a new server:** qbx_apartments and qbx_houses (replaced by qbx_properties), qbx_evidence, qbx_prison (the recipe uses xt-prison), qbx_radio (replaced by mm_radio), qbx_dutyblips, qbx_helicam, qbx_interior, qbx_loading, qbx_lockpick, qbx_nitro, qbx_playerstates, qbx_traphouse, qbx_tunerchip, qbx_vehiclefailure, qbx_commandbinding, qbx_weathersync (the recipe uses Renewed-Weathersync), qbx_crypto, qbx_phone, qbx_fitbit, qbx_skillbar, qbx-multicharacter (built into the core), qbx-customs, qbx-hotdogjob, qbx-printer, PolyZone, connectqueue, interact-sound, qbx-lua-ls (merged into qbx-lua).

**QB compatibility (`provide`)**: qbx_vehiclekeys → `qb-vehiclekeys` (can be turned off with the convar `qbx_vehiclekeys:enableBridge`), qbx_npwd → `qb-npwd`, qbx_mechanicjob → `qb-mechanicjob`, qbx_lapraces → `qb-lapraces`, qbx_scrapyard → `qb-scrapyard`, qbx_taxijob → `qb-taxijob`, qbx_towjob → `qb-towjob`, qbx_truckerjob → `qb-truckerjob`, npwd_qbx_garages → `npwd_qb_garage`, npwd_qbx_mail → `npwd_qb_mail`.

## 3. Vehicles
### qbx_vehicles: ownership database API (server)
The `player_vehicles` table. States: `OUT = 0`, `GARAGED = 1`, `IMPOUNDED = 2`. Required by core vehicle persistence (≥ 1.4.1).
| Export | Signature → return |
|---|---|
| `CreatePlayerVehicle(request)` | `{model, citizenid?, garage?, props?}` → `vehicleId?, ErrorResult?` |
| `GetPlayerVehicle(vehicleId, filters?)` | → `PlayerVehicle?` `{id, citizenid?, modelName, garage, state, depotPrice, props}` |
| `GetPlayerVehicles(filters?)` | filters `{citizenid?, states?, garage?}` → `PlayerVehicle[]` |
| `SetPlayerVehicleOwner(vehicleId, citizenid?)` | → `success, ErrorResult?` (nil citizenid = no owner) |
| `DeletePlayerVehicles(idType, idValue)` | `'citizenid'\|'license'\|'plate'\|'vehicleId'` → `success, ErrorResult?` (DB only) |
| `DoesPlayerVehiclePlateExist(plate)` | → `boolean` |
| `GetVehicleIdByPlate(plate)` | → `integer?` |
| `SaveVehicle(vehicle, options)` | entity, `{garage?, state?, depotPrice?, props?, coords?}` → `success, ErrorResult?` |
| `registerHook(event, cb)` / `removeHooks(id?)` | hooks `createPlayerVehicle` `{citizenid, garage, props}`, `changeVehicleOwner` `{vehicleId, newCitizenId}`; return `false` to cancel |
```lua
-- server: give a vehicle to a character, then spawn it with core lib
local vehicleId, err = exports.qbx_vehicles:CreatePlayerVehicle({
    model = 'sultan2',
    citizenid = citizenid,
    garage = 'pillboxgarage',
})
if not vehicleId then lib.print.error(err and err.message) return end
```
### qbx_garages
Garage backend plus an optional ox_lib UI. A garage has `label`, `type?` (depot), `vehicleType`, `groups?` (HasGroup filter), `shared?`, `states?`, `skipGarageCheck?`, `canAccess?(source)` and `accessPoints[]` (each with pickup, dropoff, spawn and an optional blip).
- Server exports: `RegisterGarage(name, config)`, `GetGarages()`, `SetVehicleGarage(vehicleId, garageName)` → `success, ErrorResult?`, `SetVehicleDepotPrice(vehicleId, price)` → `success, ErrorResult?`.
- Callbacks for custom UIs (`lib.callback.await` from the client): `qbx_garages:server:getGarages`, `getGarageVehicles(garageName)`, `isParkable(garageName, netId)`, `parkVehicle(netId, props, garageName)`, `payDepotPrice(vehicleId)`, `spawnVehicle(vehicleId, garageName, accessPointIndex)`.
- House garages: pass a `canAccess` function that checks property ownership.
### qbx_vehiclekeys
Keys, lockpicking/hotwire, carjacking, shared job vehicles, autolock. Core `config/server.lua` calls `GiveKeys` and `SetLockState` from it.
| Side | Export |
|---|---|
| server | `GiveKeys(source, vehicle, skipNotification?)`, `RemoveKeys(source, vehicle, skipNotification?)`, `HasKeys(source, vehicle)` → bool, `IsPlayerNearVehicle(source, vehicle)` → bool, `SetLockState(vehicle, 'lock'\|'unlock')` (sets the `doorslockstate` state bag) |
| client | `HasKeys(vehicle)` → bool |
Commands: `/givekeys [id]` (all players), `/addkeys [id]` (`group.admin`). `vehicle` is an **entity handle**. Do not pass a plate, as you would with qb-vehiclekeys.
### qbx_vehicleshop / qbx_vehiclesales / qbx_customs / qbx_mechanicjob
- qbx_vehicleshop (server): `IsFinanced(vehicleId)` → bool.
- qbx_customs (client): `OpenMenu()`.
- qbx_mechanicjob (client): `GetVehicleStatusList(plate)` → table?, `GetVehicleStatus(plate, part)` → number?, `SetVehicleStatus(plate, part, level)`.
- qbx_seatbelt (client): `HasHarness()` → bool.

## 4. Health and emergency
### qbx_medical: health and death state (use it instead of touching `isdead` directly)
| Side | Exports |
|---|---|
| server | `Revive(player)` (source or Player), `Heal(src)`, `HealPartially(src)`, `ResetHungerAndThirst(player)`, `GetPlayerStatus(src)` → `{injuries: string[], bleedLevel, bleedState, damageCauses}` |
| client | `IsDead()`, `IsLaststand()`, `GetDeathTime()`, `GetLaststandTime()`, `IncrementDeathTime(s)`, `IncrementLaststandTime(s)`, `KillPlayer()`, `StartLastStand()`, `AllowRespawn()`, `DisableRespawn()`, `PlayDeadAnimation()`, `EnableDamageEffects()`/`DisableDamageEffects()`, `EnableBleeding()`/`DisableBleeding()`, `RemoveBleed(level)`, `MakePedLimp()`, `MakePlayerBlackout()`, `MakePlayerFadeOut()`, `SendBleedAlert()`, `GetRespawnHoldTimeDeprecated()` |
Events: client `qbx_medical:client:onPlayerDied`, `qbx_medical:client:onPlayerLaststand`, `qbx_medical:client:playerRevived`, `qbx_medical:client:heal`; server `qbx_medical:server:playerRespawned`. Server hooks: `respawn` and `checkIn` (ambulancejob). The exact parameter lists are **UNVERIFIED**; read `qbx_medical/server/main.lua` before relying on them.
### qbx_ambulancejob
Depends on qbx_core, qbx_medical, ox_lib and ox_inventory. Adds the EMS job, hospitals and medical items. Server: `CheckIn(src, patientSrc, hospitalName)`.
### qbx_police
Covers duty, armory (citizenid whitelist), evidence and GSR, cuffing (as an item), impound, jail integration, radars and fines. Client export: `IsHandcuffed()` → bool. Everything else goes through events and ox_target, so treat the internals as private.

## 5. Player-facing resources
- **qbx_spawn**: spawn selector (config locations + last position). The core triggers it with `qb-spawn:client:setupSpawns(citizenid)` and `qb-spawn:client:openUI(true)` when the resource is started.
- **qbx_properties**: apartments, houses, decorations, keyholders, rent and stashes. It replaces qbx_apartments and qbx_houses. It handles `apartments:client:setupSpawnUI` (first-character apartment choice) and has its own SQL files (`property.sql`, `decorations.sql`, `property_garages.sql`). Version 0.0.1, so expect API churn. Net events are prefixed `qbx_properties:server:*`.
- **qbx_management**: boss and gang menus (hire/fire/promote, including offline members). Client: `OpenBossMenu(groupType)` (`'job'|'gang'`), `AddBossMenuItem(menuItem)`/`AddGangMenuItem(menuItem)` → id, `RemoveBossMenuItem(id)`/`RemoveGangMenuItem(id)`. Server: `RegisterBossMenu({groupName, type, coords, size?, rotation?})`. Convar `setr qbx:enableGroupManagement "false"`: set it to `true` to let bosses rename grades.
- **qbx_cityhall**: ID and licence requests, city job applications.
- **qbx_idcard** (server): `CreateMetaLicense(src, itemOrItems)`, `GetMetaLicense(src, itemOrItems)` → metadata. The core starter items use `GetMetaLicense`. Depends on MugShotBase64.
- **qbx_hud** (client): `AddCustomIndicator({id, icon?, color?, value?, label?, alwaysShow?})`, `UpdateCustomIndicator(id, value, color?)`, `RemoveCustomIndicator(id)`, `GetCustomIndicators()`. All of them return a boolean; values are clamped to 0–100.
- **qbx_radialmenu** (client): `AddOption(data, id?)` → id (an ox_lib radial item, converted from the QB format), `RemoveOption(id)`. Also exported under the QB name. Vehicle flip uses the `FlipVehicle` export from qbx_smallresources.
- **qbx_adminmenu**: `/admin`, `/noclip`, `/names`, `/blips`, `/setmodel`, `/admincar`, `/vec2|3|4`, `/heading`, `/report`. ACE-based.
- **qbx_scoreboard** (server): `SetActivityBusy(name, bool)` (marks robbery activities as busy in `GlobalState.illegalActions`).
- **qbx_density** (client): `SetDensity(type, value)`, with `type` one of `'parked'`, `'vehicle'`, `'randomvehicles'`, … (check the config for the full list).
- **qbx_chat_theme**: convars `qbx_chat:mainColor`, `borderColor`, `textColor`, `fontFamily`, `joinMessage`, `quitMessage`, icon URLs.

## 6. qbx_smallresources (deprecated)
The README says: "deprecated and will be deconstructed in future releases. No new code will be added." It still ships in the recipe. Modules: qbx_afk, qbx_consumables, qbx_crouch, qbx_cruise, qbx_disableservices, qbx_editor, qbx_entitiesblacklist, qbx_flipvehicle, qbx_hudcomponents, qbx_ignore, qbx_itempickup, qbx_noshuff, qbx_recoils, qbx_removeentities, qbx_staticemitters, qbx_stun, qbx_tackle, qbx_teleports, qbx_vehiclepush, qbx_vehicleradio.
Exports (each one exists in both PascalCase and camelCase):
- server: `SetHunger`, `AddHunger`, `SetThirst`, `AddThirst`;
- client: `FlipVehicle`, `AddDisableHudComponents`, `RemoveDisableHudComponents`, `GetDisableHudComponents`, `AddDisableControls`, `RemoveDisableControls`, `GetDisableControls`, `SetDisplayAmmo`, `GetDisplayAmmo`, `TrevorEffect`, `MethBagEffect`, `EcstasyEffect`, `AlienEffect`, `CrackBaggyEffect`, `CokeBaggyEffect`.

`qbx_entitiesblacklist` reads `qbx:bucketlockdownmode` with its **own default `relaxed`**, while the core default is `inactive`. Set the convar explicitly.

## 7. Phone and radio
- **NPWD** (project-error) is the recipe phone. Set `set npwd:framework "qbx"` and ensure `qbx_npwd` **before** `npwd` (the recipe does `ensure qbx_npwd` then `ensure npwd`). `qbx_npwd` provides `qb-npwd`; its client export is `HasPhone()` → bool (ox_inventory search over the configured phone item list). Apps: `npwd_qbx_garages` (provides `npwd_qb_garage`) and `npwd_qbx_mail` (provides `npwd_qb_mail`). `config/server.lua → characterDataTables` deletes the npwd_* rows when a character is deleted. Optional tokens: `SCREENSHOT_BASIC_TOKEN`, `NPWD_AUDIO_TOKEN`.
- **mm_radio** (replaces qbx_radio): depends on pma-voice, ox_lib and OneSync. Client: `JoinRadio(channel)`, `LeaveRadio()`.

## 8. Jobs, crime and activities
They have no public API, or only a minimal one. Configure them through each resource's `config/*.lua`.
- qbx_drugs (`GetDealers`), qbx_weed (`placePlant`, `foodPlant`), qbx_lapraces (`IsInRace`, `IsInEditor`), qbx_fireworks (`StartShow`).
- Several job resources read the convar `UseTarget` (`'false'` by default) to switch between ox_target and markers: cityhall, drugs, newsjob, pawnshop, recyclejob, scrapyard, towjob, truckerjob.
- Robberies (bank, jewelery, store, truck, house) rely on ox_inventory items, minigames (mhacking, safecracker, ultra-voltlab) and police counts (`exports.qbx_core:GetDutyCountType('leo')`).

## 9. Third-party resources in the recipe
ox_lib, oxmysql, ox_inventory, ox_target (`[ox]`); pma-voice; illenium-appearance (clothing, `playerskins` table); Renewed-Banking (society accounts, used by core paychecks); Renewed-Weathersync; xt-prison; vehiclehandler; mana_audio (replacement for `qbx.playAudio`); scully_emotemenu; bob74_ipl; MugShotBase64; screencapture; npwd; loadscreen; cfx-server-data. The exact versions are pinned in `qbox.yaml` (zip downloads), so check them there.

## 10. Patterns and common mistakes
- Give keys after spawning an owned car: `exports.qbx_vehiclekeys:GiveKeys(src, veh)` on the server, with the entity handle from `qbx.spawnVehicle`.
- Check death through qbx_medical (`exports.qbx_medical:IsDead()` on the client) or core `metadata.isdead`. Never set `isdead` yourself; use `Revive`/`KillPlayer`.
- Do not mix the archived qbx_apartments or qbx_houses with qbx_properties. Remove them as the qbx_properties README says.
- Do not install QB equivalents next to their Qbox replacements (qb-vehiclekeys, qb-garages, qb-policejob, qb-ambulancejob, qb-management). They conflict on events, and some names are `provide`d.
- Job/gang scripts must call core group exports. Never write `player_groups` directly.
- For a custom garage or shop UI, use the qbx_garages callbacks and qbx_vehicles exports instead of editing their SQL.

## 11. Sources
- https://api.github.com/orgs/Qbox-project/repos (repo list and archived flags, 2026-10-07)
- https://github.com/Qbox-project/txAdminRecipe (`qbox.yaml`, `server.cfg`, `ox.cfg`, `permissions.cfg`)
- https://github.com/Qbox-project/qbx_vehicles · https://github.com/Qbox-project/qbx_garages · https://github.com/Qbox-project/qbx_vehiclekeys · https://github.com/Qbox-project/qbx_medical · https://github.com/Qbox-project/qbx_ambulancejob · https://github.com/Qbox-project/qbx_police · https://github.com/Qbox-project/qbx_management · https://github.com/Qbox-project/qbx_properties · https://github.com/Qbox-project/qbx_spawn · https://github.com/Qbox-project/qbx_smallresources · https://github.com/Qbox-project/qbx_radialmenu · https://github.com/Qbox-project/qbx_hud · https://github.com/Qbox-project/qbx_npwd · https://github.com/Qbox-project/mm_radio · https://github.com/Qbox-project/qbx_idcard · https://github.com/Qbox-project/qbx_adminmenu (source and READMEs, default branches)
- https://github.com/Qbox-project/qbox-docs → docs.qbox.re pages `resources/qbx_vehicles/exports/{server,hooks}`, `resources/qbx_garages/{exports/server,callbacks/client}`, `resources/qbx_vehiclekeys/{exports/*,commands}`, `resources/qbx_management/{convars,exports/*}`
- GitHub releases API (`/repos/Qbox-project/<repo>/releases/latest`) for the release dates above
