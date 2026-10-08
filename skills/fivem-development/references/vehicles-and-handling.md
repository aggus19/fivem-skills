# Vehicles: add-on packs, meta files, handling, runtime control

Baseline: FXServer Legacy 35245 / game build 3889 / Cfx Server (Enhanced) early access — verified 2026-10-07.
Verify any native with `python scripts/natives.py show <Name>` before relying on parameters.

## Contents
1. Add-on vehicle resource layout
2. Data files and load order
3. vehicles.meta essentials
4. handling.meta field reference (with vanilla values)
5. carcols.meta / carvariations.meta (mod kits, sirens, lights)
6. vehiclelayouts.meta, weapons.meta, dlctext
7. Runtime: handling overrides, fuel, damage, mods
8. Spawning, plates, ownership, keys (server-authoritative)
9. Validation checklist and common faults
10. Sources

## 1. Add-on vehicle resource layout
```
my_vehicles/
  fxmanifest.lua
  stream/              # .yft (model, _hi.yft for high LOD), .ytd (textures)  - Legacy (Gen8)
  stream_enhanced/     # Gen9 versions (Alchemist/CodeWalker converted) - used instead of stream/ on Enhanced
  data/<car>/vehicles.meta  handling.meta  carcols.meta  carvariations.meta  vehiclelayouts.meta
  client/names.lua     # AddTextEntry labels
```
```lua
-- fxmanifest.lua
fx_version 'cerulean'
game 'gta5'

files {
    'data/**/*.meta',
}

data_file 'HANDLING_FILE'          'data/**/handling.meta'
data_file 'VEHICLE_METADATA_FILE'  'data/**/vehicles.meta'
data_file 'CARCOLS_FILE'           'data/**/carcols.meta'
data_file 'VEHICLE_VARIATION_FILE' 'data/**/carvariations.meta'
data_file 'VEHICLE_LAYOUTS_FILE'   'data/**/vehiclelayouts.meta'

client_script 'client/names.lua'
```
- `data_file` supports globbing; `.meta` files must also be in `files {}` (they are not streamed).
- One resource per pack (not one per car): fewer resources → faster join, fewer manifest round-trips.
- Model files in `stream/` are matched by **file name** (`modelName.yft`, `modelName_hi.yft`, `modelName.ytd`, optional `modelName+hi.ytd`). Two resources streaming the same file name = last one wins (silent conflict).
- Enhanced: `stream_enhanced/` replaces `stream/` when present; `stream/` alone still works there but is deprecated. Convert with **Alchemist** (Cfx Portal) or CodeWalker's Gen9 converter. See `gta5-enhanced.md`.

## 2. Data files and load order
| `data_file` key | File | Notes |
|---|---|---|
| `HANDLING_FILE` | handling.meta | loaded **first** (FiveM sorts it before other data files) |
| `VEHICLE_LAYOUTS_FILE` | vehiclelayouts.meta | also loaded first; needed only for custom layouts/seat anims |
| `VEHICLE_METADATA_FILE` | vehicles.meta | model registration (`modelName`, `handlingId`, `layout`…) |
| `CARCOLS_FILE` | carcols.meta | mod kits, sirens, light settings |
| `VEHICLE_VARIATION_FILE` | carvariations.meta | colours, kit binding, siren/light setting ids |
| `VEHICLE_SHOP_DLC_FILE` | shop_vehicle.meta | SP/online shop data (rarely needed in FiveM) |
| `VEHICLEEXTRAS_FILE` | vehicleextras.dat | extras behaviour |
| `VFXVEHICLEINFO_FILE` | vfxvehicleinfo.meta | exhaust/backfire FX |
| `AUDIO_GAMEDATA` / `AUDIO_SOUNDDATA` / `AUDIO_WAVEPACK` | `*.dat151.rel`, `*.dat54.rel`, awc folder | custom engine sounds (`audioNameHash` in vehicles.meta) |

FiveM's loader (`LoadStreamingFile.cpp`) sorts `VEHICLE_LAYOUTS_FILE` and `HANDLING_FILE` before every other data file, and refuses `TEXTFILE_METAFILE` entries ("these don't work").

## 3. vehicles.meta essentials
| Field | Meaning |
|---|---|
| `modelName` | spawn name; must match the `.yft` file name |
| `txdName` | texture dictionary (usually = modelName) |
| `handlingId` | `handlingName` in handling.meta (≤ 14 chars per GTAMods) |
| `gameName` | text label key (≤ 11 chars); set its text with `AddTextEntry` |
| `vehicleMakeName` | manufacturer label key |
| `layout` | seat/entry layout from vehiclelayouts.meta (e.g. `LAYOUT_STANDARD`) |
| `audioNameHash` | vanilla vehicle whose sounds are reused (e.g. `sultan`) |
| `lodDistances` | 6 LOD switch distances |
| `type` | `VEHICLE_TYPE_CAR`, `_BIKE`, `_BICYCLE`, `_BOAT`, `_HELI`, `_PLANE`, `_QUADBIKE`, `_TRAILER`, `_SUBMARINE`… |
| `vehicleClass` | `VC_COMPACT` (0) … `VC_SUPER` (7), `VC_MOTORCYCLE` (8), `VC_EMERGENCY` (18), `VC_OPEN_WHEEL` (22) |
| `flags` | e.g. `FLAG_EXTRAS_REQUIRE`, `FLAG_IS_VAN`, `FLAG_SPORTS`, `FLAG_LAW_ENFORCEMENT`, `FLAG_EMERGENCY_SERVICE` |
| `plateType`, `dashboardType`, `wheelType` | cosmetics/UI |
| `txdRelationships` | parent → child texture dictionaries (never loop child → parent: crash) |

`CreateVehicleServerSetter` needs the **type string** (`'automobile'`, `'bike'`, `'boat'`, `'heli'`, `'plane'`, `'submarine'`, `'trailer'`, `'train'`): derive it from the model on the client (`GetVehicleType` is also available server-side for existing entities) or store it with the vehicle in your config/DB.

## 4. handling.meta field reference
Values in the last column are the vanilla `SULTAN` / `ADDER` / `POLICE` entries (from the community dump `zfbx/GTA5-Handling-Meta`); meanings from GTAMods wiki.

| Field | Meaning | Sultan / Adder / Police |
|---|---|---|
| `fMass` | kg; used in collisions with vehicles/objects | 1400 / 1800 / 1400 |
| `fInitialDragCoeff` | drag ∝ v²; higher = lower top speed | 8.0 / 7.8 / 6.0 |
| `fDownforceModifier` | extra downforce/grip at speed | — |
| `fPercentSubmerged` | % height submerged before floating (file uses 85) | 85 |
| `vecCentreOfMassOffset` | x right / y forward / z up, metres | 0,0,0 |
| `vecInertiaMultiplier` | rotational resistance per axis | 1,1,1 |
| `fDriveBiasFront` | 0 = RWD, 1 = FWD, between = AWD split | 0.40 / 0.20 / 0.0 |
| `nInitialDriveGears` | forward gears (≤ 10 since b1604, ≤ 8 recommended) | 5 / 6 / 5 |
| `fInitialDriveForce` | wheel drive force multiplier (most cars 0.10–0.40) | 0.26 / 0.32 / 0.20 |
| `fDriveInertia` | rev speed (1.0 default) | 1.0 |
| `fClutchChangeRateScaleUpShift/DownShift` | shift speed (1 ≈ 0.9 s per shift) | 1.8 / 3.0 / 1.8 |
| `fInitialDriveMaxFlatVel` | redline speed in top gear (≈ ×1.32 → km/h, ×0.82 → mph; approximate) | 145 / 160 / 145 |
| `fBrakeForce` | braking multiplier | 0.4 / 1.0 / 0.9 |
| `fBrakeBiasFront` | 0 rear … 1 front (real cars ≈ 0.65) | 0.65 / 0.45 / 0.525 |
| `fHandBrakeForce` | handbrake power | 0.7 / 0.7 / 0.6 |
| `fSteeringLock` | max wheel angle in degrees (most cars ≈ 35–42) | 35 / 42 / 40 |
| `fTractionCurveMax` | peak grip | 2.35 / 2.50 / 2.55 |
| `fTractionCurveMin` | grip while sliding | 1.95 / 2.38 / 2.45 |
| `fTractionCurveLateral` | slip-angle curve shape (peak at value/2 degrees) | 22.5 |
| `fTractionSpringDeltaMax` | tyre sidewall travel (m) | 0.15 |
| `fLowSpeedTractionLossMult` | burnout/low-speed wheelspin | 1.4 / 1.5 / 1.0 |
| `fCamberStiffnesss` | (sic, three "s") roll-induced push; keep 0–1 | 0.0 |
| `fTractionBiasFront` | grip split 0.01 rear … 0.99 front (0/1 = broken tyres) | 0.485 / 0.485 / 0.48 |
| `fTractionLossMult` | grip loss on loose surfaces (higher = more slide off-road) | 1.0 |
| `fSuspensionForce` | spring strength | 2.8 / 2.4 / 1.8 |
| `fSuspensionCompDamp` / `fSuspensionReboundDamp` | damping | 1.2/2.1 · 1.4/2.1 · 0.8/1.5 |
| `fSuspensionUpperLimit` / `fSuspensionLowerLimit` | wheel travel up/down (m) | 0.15/-0.14 · 0.12/-0.10 · 0.09/-0.14 |
| `fSuspensionRaise` | body height offset (small steps) | 0.0 |
| `fSuspensionBiasFront` | > 0.5 stiffer front | 0.5 / 0.5 / 0.51 |
| `fAntiRollBarForce` / `fAntiRollBarBiasFront` | body roll resistance / split | 0.3/0.53 · 0.9/0.6 · 0.8/0.6 |
| `fRollCentreHeightFront/Rear` | roll centre (m); too high = "negative roll" | 0.24/0.25 · 0.41/0.41 · 0.34/0.35 |
| `fCollisionDamageMult` | 0–10; 0 disables collision (and engine) damage | 0.7 |
| `fWeaponDamageMult` | 0–10 | 1.0 |
| `fDeformationDamageMult` | 0–10; visual deformation | 0.7 |
| `fEngineDamageMult` | 0–10; engine failure/fire | 1.5 |
| `fPetrolTankVolume` | litres; used by game fuel system (0 = infinite fuel) | 65 |
| `fOilVolume` | — | 5 |
| `fPetrolConsumptionRate` | per-vehicle fuel consumption (default 0.5) — FiveM fuel feature | — |
| `nMonetaryValue` | value (used by game insurance logic, not by frameworks) | 35000 / 80000 / 35000 |
| `strModelFlags` / `strHandlingFlags` / `strDamageFlags` | hex bit flags (e.g. `HF_CVT`, `HF_OFFROAD_ABILITIES`) | — |
| `AIHandling` | `AVERAGE`, `SPORTS_CAR`, `TRUCK`, `CRAP` | — |
| `SubHandlingData` | up to 3: `CCarHandlingData`, `CBikeHandlingData`, `CFlyingHandlingData`, `CBoatHandlingData`… | — |

Tuning rules of thumb (practical, not engine guarantees):
- Faster acceleration → `fInitialDriveForce`; higher top speed → `fInitialDriveMaxFlatVel` **and** lower `fInitialDragCoeff`; change one field at a time and test with a speedometer.
- Car flips in corners → lower `vecCentreOfMassOffset` z slightly (e.g. -0.1), raise `fAntiRollBarForce`, lower `fRollCentreHeight*`.
- Unrealistic grip on RP servers usually comes from `fTractionCurveMax/Min` > 3.0 on add-on cars: normalise packs against vanilla class peers.
- `handlingName` collisions: two packs defining the same `handlingName` overwrite each other (last loaded wins) — keep names unique.

In-game editors: on **Enhanced** clients the dev tool `con_handlingEditor true` (dev mode) shows a Handling Tool. On Legacy use a dev resource that calls `GetVehicleHandlingFloat`/`SetVehicleHandlingFloat`.

## 5. carcols.meta / carvariations.meta
- `carcols.meta` → `<Kits>` (mod kits: `kitName` like `1234_mycar_modkit`, `id`, `kitType`, `visibleMods`, `statMods`, `slotNames`), `<Lights>` (light settings) and `<Sirens>` (siren settings `id`, up to 20 siren items).
- `carvariations.meta` → per model: `colors`, `kits` (`<Item>1234_mycar_modkit</Item>`), `lightSettings id`, `sirenSettings id`, `plateProbabilities`.
- **IDs must be unique across the whole server.** Duplicate modkit ids → wrong/missing tuning parts in mod shops; duplicate siren ids → wrong light patterns. Community reports: siren setting ids wrap at 255 (ids > 255 overflow and can collide); modkit slot limit reported as 1023 (**UNVERIFIED**). Keep a registry of used ids per server; the open-source "Carcols Fixer" (forum.cfx.re/t/5402948) scans and renumbers them (**review before running**).
- Mod kits require `SetVehicleModKit(veh, 0)` before `SetVehicleMod`; `lib.setVehicleProperties` does this for you.

## 6. vehiclelayouts.meta, weapons.meta, dlctext
- Most add-ons reuse vanilla layouts (`LAYOUT_STANDARD`, `LAYOUT_LOW`, `LAYOUT_BIKE_SPORT`…); only ship vehiclelayouts.meta if the author created custom seat/anim layouts.
- Add-on/replacement weapons: `WEAPONINFO_FILE` (weapons.meta), `WEAPON_METADATA_FILE` (weaponarchetypes.meta), `WEAPON_ANIMATIONS_FILE` (weaponanimations.meta), `WEAPONCOMPONENTSINFO_FILE` (weaponcomponents.meta), plus `.ydr`/`.ytd` in `stream/`. `WEAPONINFO_FILE_PATCH` patches existing weapon infos. Weapon damage values live in weapons.meta (`Damage`, `HeadShotDamageModifierPlayer`…): balance on the server's design, but enforce damage server-side only via game events/anticheat, not by trusting clients.
- Vehicle display names: `DLC_TEXT_FILE` / dlctext.meta entries ship with many packs but the key is **not** in the official data-file table (**UNVERIFIED**); the reliable way is a client script:
```lua
-- client/names.lua
local labels = { mycar = 'Karin Sultan Custom', mytruck = 'Vapid Workhorse' }
for model, label in pairs(labels) do
    AddTextEntry(GetDisplayNameFromVehicleModel(joaat(model)), label)
end
```

## 7. Runtime: handling overrides, fuel, damage, mods
- `SetVehicleHandlingFloat(veh, 'CHandlingData', 'fInitialDriveForce', 0.30)` affects **one vehicle on this client only** (not synced): every client that simulates/owns it must apply it (state bag + handler). `SetHandlingFloat(modelName, class, field, value)` changes the model globally on that client. Some fields only take effect globally — test.
- Read: `GetVehicleHandlingFloat(veh, 'CHandlingData', 'fPetrolTankVolume')`, `GetVehicleHandlingInt`.
- `ModifyVehicleTopSpeed(veh, percent)` for engine-tune upgrades (client, owner).
- **Native fuel (FiveM feature):** `SetFuelConsumptionState(true)`, `SetFuelConsumptionRateMultiplier(m)`, `GetVehicleFuelLevel` / `SetVehicleFuelLevel`, `DoesVehicleUseFuel`. Consumption = time × RPM × `fPetrolConsumptionRate` × global multiplier; a 65 L tank lasts ≈ 2.5 h at max RPM. ox_fuel keeps the authoritative value in `Entity(veh).state.fuel`.
- Damage persistence: save `GetVehicleEngineHealth`, `GetVehicleBodyHealth`, `GetVehiclePetrolTankHealth` (all available server-side) plus `lib.getVehicleProperties` on store.
- Handling is client-simulated: a cheater can change their own handling. Server can only detect symptoms (e.g. `GetEntitySpeed(veh)` far above the model's configured max for several samples).

```lua
-- server: keep a tuning value in a state bag; clients apply it
Entity(veh).state:set('tune', { driveForce = 0.30 }, true)

-- client: apply when the vehicle streams in or the value changes
AddStateBagChangeHandler('tune', nil, function(bagName, _, value)
    if not value then return end
    local veh = GetEntityFromStateBagName(bagName)
    if veh == 0 then return end
    SetVehicleHandlingFloat(veh, 'CHandlingData', 'fInitialDriveForce', value.driveForce + 0.0)
end)
```

## 8. Spawning, plates, ownership, keys
- Spawn owned vehicles **server-side** (`CreateVehicleServerSetter`), set the plate server-side (`SetVehicleNumberPlateText` exists on server), then let the owner client apply properties (`gameplay-patterns.md` §1, `onesync-entities.md`).
- Plates: max 8 chars; `GetVehicleNumberPlateText` pads with spaces → always trim (`plate:gsub('^%s*(.-)%s*$', '%1')`) and uppercase before DB lookups.
- Mark persistent vehicles so they survive owner disconnect: `SetEntityOrphanMode(veh, 2)` (keep entity) — see `onesync-entities.md`.
- Framework data: Qbox/QBCore `player_vehicles` (citizenid, vehicle, hash, mods JSON, plate, state, garage …); Qbox exposes `exports.qbx_vehicles:CreatePlayerVehicle({ model, citizenid, garage?, props? })`. ESX `owned_vehicles` (owner, plate, vehicle JSON, type, job, stored, parking, pound).
- Keys: `qbx_vehiclekeys` server exports `GiveKeys(source, vehicle, skipNotification)`, `RemoveKeys(...)`, `HasKeys(source, vehicle)`; keys are kept in the player state bag `keysList` keyed by a per-vehicle session id. Design notes in `rp-systems-design.md` §4.
- Locks: `SetVehicleDoorsLocked(veh, 2)` works server-side (2 = locked, 1 = unlocked); check ownership/keys on the server before toggling.
- Marking a vehicle as the player's for game code (radio emitters, door entry behaviour): decorator `Player_Vehicle` (`DecorRegister('Player_Vehicle', 3)` once, `DecorSetInt(veh, 'Player_Vehicle', -1)`), per the FiveM cookbook.

## 9. Validation checklist and common faults
| Symptom | Likely cause |
|---|---|
| Vehicle spawns invisible / "model not found" | `modelName` ≠ file name, `.meta` missing from `files{}`, typo in `data_file` glob, resource not started before spawn |
| Spawns but drives like a default car | `handlingId` doesn't match `handlingName`, or another pack reuses the `handlingName` |
| Name shows `NULL` / `CARNOTFOUND` | no `AddTextEntry` for `gameName` |
| Wrong tuning parts / sirens | duplicate modkit / siren ids (§5) |
| Purple/low-res textures, texture loss | oversized `.ytd` (FXServer warns > 16 MiB; > 48 MiB "WILL lead to streaming issues"); clients cap vehicle textures with `str_maxVehicleTextureRes` (default 1024) |
| Crash on entering a vehicle | broken `.yft` (bad collision/physics, wrong LODs) — re-export with Sollumz/CodeWalker, test with the vanilla model swapped in |
| Works on Legacy, crashes on Enhanced | Legacy assets streamed on Gen9: provide `stream_enhanced/` converted with Alchemist |

Before shipping a pack: `python scripts/manifest.py <resource>`; spawn every model once on a test server with `strmem`/`strdbg` open (developer mode) and check the server console for size warnings.

## 10. Sources
- https://docs.fivem.net/docs/game-references/data-files/
- https://docs.fivem.net/docs/scripting-reference/resource-manifest/ (`data_file`, globbing, `this_is_a_map`)
- https://docs.fivem.net/docs/scripting-manual/using-new-game-features/fuel-consumption/
- https://docs.fivem.net/docs/developers/legacy-vs-enhanced/ (`stream_enhanced`)
- https://docs.fivem.net/docs/client-manual/console-commands/ (`str_maxVehicleTextureRes`, `con_handlingEditor`)
- https://docs.fivem.net/docs/cookbook/2022/01/06/marking-a-vehicle-as-player-vehicle-for-game-code/
- https://github.com/citizenfx/fivem/blob/master/code/components/gta-streaming-five/src/LoadStreamingFile.cpp (data file sort, TEXTFILE_METAFILE refused)
- https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/ResourceStreamComponent.cpp (asset size warnings)
- https://gtamods.com/wiki/Handling.meta · https://gtamods.com/wiki/Vehicles.meta
- https://github.com/zfbx/GTA5-Handling-Meta (vanilla handling dump)
- https://forum.cfx.re/t/release-carcols-fixer-free-open-source-siren-light-modkit-id-conflict-fixer/5402948 · https://forum.cfx.re/t/tutorial-fix-broken-lights-and-sirens/1071060
- https://github.com/Qbox-project/qbx_vehiclekeys (server/keys.lua) · https://github.com/Qbox-project/qbx_vehicles · https://github.com/esx-framework/esx_core (`[SQL]/legacy.sql`)
