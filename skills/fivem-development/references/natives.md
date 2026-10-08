# Natives: lookup, verification, calling conventions and pitfalls

Baseline: native DB fetched 2026-10-07 — 7379 natives (6436 GTA V in 44 namespaces + 943 CFX: 583 client, 286 server, 74 shared; 1001 still unnamed `N_0x…`).

## Contents
1. Golden rule and lookup workflow
2. What lives where (catalogue, essentials, scripts)
3. Reading a signature (types, out-params, returns)
4. Naming: Lua names, aliases, unnamed natives, InvokeNative
5. Client vs server natives
6. Player identifiers
7. Things that look like natives but are not
8. Frequently confused / deprecated
9. Top pitfalls (short version)
10. Game build and edition gating
11. Other runtimes (JS/TS, C#)
12. Regenerating the catalogue
13. Sources

## 1. Golden rule and lookup workflow

**Never invent a native.** Before writing a native you are not 100% sure about (name, parameters, return values, side), look it up:

```bash
python scripts/natives.py search vehicle plate           # fuzzy name search (skips N_0x unless you search a hash)
python scripts/natives.py search fuel --desc             # also search descriptions
python scripts/natives.py search door --side server      # only natives callable on the server
python scripts/natives.py show SetVehicleFuelLevel       # signature(s), side, hash, docs link, description
python scripts/natives.py check path/to/resource         # every native used exists and is on the right side
python scripts/natives.py check path/to/resource --strict   # also report unknown PascalCase calls (typos/hallucinations)
grep -n "PlateText" assets/natives/*.md                  # offline catalogue, one line per native
```

The first `natives.py` run downloads ~3 MB into `~/.cache/fivem-skill` (override with `FIVEM_SKILL_CACHE`); `update` refreshes it (warning after 14 days).
Workflow when writing code: pick candidates from [natives-essentials.md](natives-essentials.md) (task-grouped) → confirm each with `show` → after writing, run `check --strict`.

## 2. What lives where

| Resource | Use it for |
|---|---|
| [natives-essentials.md](natives-essentials.md) | ~700 most-used natives grouped by task (player, entity, vehicle, weapons, AI, anims, props, streaming, camera, HUD, blips, markers, controls + control-ID table, raycasts, world, audio, particles, network, server CFX, state bags, KVP, NUI/DUI…), exact DB signatures, side, usage notes, pitfalls, legacy→current names, game-reference links |
| [assets/natives/README.md](../assets/natives/README.md) | Index of the full generated catalogue: one file per namespace (`PLAYER.md`, `VEHICLE.md`, `PED.md`, … `CFX-CLIENT.md`, `CFX-SERVER.md`, `CFX-SHARED.md`) with every native's Lua call, returns, side, hash/docs link, minimum build, aliases and first-sentence description |
| `scripts/natives.py` | Live lookup / verification against the official DB |
| `scripts/build_natives_catalog.py` | Regenerates `assets/natives/` |

## 3. Reading a signature

`natives.py show` prints the **C-style DB signature**; the catalogue and essentials print the **Lua call**:

```
natives.py:  GetGroundZFor_3dCoord(float x, float y, float z, float* groundZ, BOOL includeWater) -> BOOL   [client]
catalogue:   GetGroundZFor_3dCoord(float x, float y, float z, BOOL includeWater) → BOOL, float groundZ
Lua:         local found, groundZ = GetGroundZFor_3dCoord(x, y, z, false)
```

Rules (from the citizenfx Lua codegen, `ext/natives/codegen_out_lua.lua`):
- **Pointer params** (`int*`, `float*`, `BOOL*`, `Vector3*`, `Hash*`, `Entity*`, `Ped*`, `Vehicle*`, `Any*` …) are **not passed**; they are **returned** after the native's own result, in parameter order. `GetVehicleColours(veh)` → `primary, secondary`; `GetShapeTestResult(h)` → `status, hit, endCoords, surfaceNormal, entityHit`.
- **Exception — single trailing pointer:** if a native has exactly one pointer param and it is the last one, it is passed **and** returned (in/out): `DeleteEntity(entity)`, `SetEntityAsNoLongerNeeded(entity)`, `RemoveBlip(blip)`, `GetEntityPlayerIsFreeAimingAt(player)` → `retval, entity`.
- `void` natives with pointers return only the pointer values. Natives returning `BOOL` return a Lua boolean.
- Types: `char*` = string (passing `0`/`nil` sends NULL); `Hash` = number — strings are auto-hashed by the wrapper, prefer backtick literals (`` `adder` ``, compile-time); `BOOL` = boolean; `Entity/Ped/Vehicle/Object/Player/Blip/Cam/Pickup/ScrHandle` = integer handles; `Vector3` = `vector3`; `func` = Lua function; `object` = Lua table (msgpack).
- Side tag: `[client]` / `[server]` / `[shared]` (both). All 44 GTA namespaces are client-side in FiveM; server natives come only from the CFX DB.
- A name can map to **two different natives** (client GTA + server CFX), e.g. `GetEntityCoords(entity, alive)` vs server `GetEntityCoords(entity)`, `GetPlayerPed(playerId)` vs server `GetPlayerPed(playerSrc)`. `show` lists both.

## 4. Naming

- Lua/JS name = PascalCase of the DB name: lower-case it, upper-case the first letter and each letter after `_`, drop those underscores. An underscore before a **digit** stays: `GET_GROUND_Z_FOR_3D_COORD` → `GetGroundZFor_3dCoord`, `DRAW_MARKER_2` → `DrawMarker_2`. Leading `_` (community-named natives) disappears: `_SET_PED_AUDIO_GENDER` → `SetPedAudioGender`.
- **Aliases**: when Cfx renames a native, the old names stay callable in Lua (the codegen emits `Global.Old = Global.New`). Examples: `DrawText` → `EndTextCommandDisplayText`, `SetNotificationTextEntry` → `BeginTextCommandThefeedPost`, `GetLabelText` → `GetFilenameForAudioConversation`, `StartShapeTestRay` → `StartExpensiveSynchronousShapeTestLosProbe`. Full list of common ones: [natives-essentials.md §29](natives-essentials.md#29-deprecated--legacy-names-and-their-replacements); every native's aliases are in the catalogue (`aka`). Note: `natives.py` does not index aliases (see §7).
- **Unnamed natives**: `N_0x<hash lower-case>` (e.g. `N_0x0205f5365292d2eb`) or `Citizen.InvokeNative(0x0205F5365292D2EB, ...)`. Prefer a named native; names are added to the DB over time, so re-check before using an `N_0x`.
- `Citizen.InvokeNative(hash, args...)` needs explicit result/pointer markers: `Citizen.ResultAsInteger()`, `ResultAsFloat()`, `ResultAsString()`, `ResultAsVector()`, `PointerValueInt()`, `PointerValueFloat()`, `PointerValueVector()`, `PointerValueIntInitialized(v)`, `ReturnResultAnyway()`. Only use it for natives without a generated wrapper.

## 5. Client vs server natives

| Task | Client | Server |
|---|---|---|
| Local / a player's ped | `PlayerPedId()` / `cache.ped` | `GetPlayerPed(src)` |
| Coordinates | `GetEntityCoords(ent, false)` | `GetEntityCoords(ent)` |
| Players | `GetActivePlayers()` (in scope only), `GetPlayerServerId(player)`, `GetPlayerFromServerId(id)` | `GetPlayers()` (Lua helper, strings), `DoesPlayerExist(src)` |
| Spawn vehicle | `CreateVehicle(...)` (blocked by strict entity lockdown) | `CreateVehicleServerSetter(model, type, x, y, z, h)` |
| Spawn ped / object | `CreatePed` / `CreateObject` after `RequestModel` | `CreatePed` / `CreateObjectNoOffset` (server RPC) |
| Delete | `DeleteEntity(ent)` — needs network control | `DeleteEntity(ent)` |
| All entities | `GetGamePool('CVehicle')` (in scope) | `GetAllVehicles()`, `GetAllPeds()`, `GetAllObjects()` |
| Entity ⇄ net id | `NetworkGetNetworkIdFromEntity` / `NetworkGetEntityFromNetworkId` | same names (server versions) |
| Owner | `NetworkGetEntityOwner(ent)` → player index | `NetworkGetEntityOwner(ent)` → server id |
| Synced data | `Entity(ent).state`, `LocalPlayer.state`, `GlobalState` | same + `Player(src).state`, `AddStateBagChangeHandler` |
| Instances | — | `SetPlayerRoutingBucket`, `SetEntityRoutingBucket`, `SetRoutingBucketEntityLockdownMode` |
| Permissions | — | `IsPlayerAceAllowed(src, 'ace')` |
| Kick | — | `DropPlayer(src, reason)` |
| Time | `GetGameTimer()`, `GetCloudTimeAsInt()` | `GetGameTimer()`, `os.time()` |
| Storage | `SetResourceKvp` (player's PC, untrusted) | `SetResourceKvp` (server), oxmysql for real data |
| UI | `SetNuiFocus`, `SendNUIMessage`, `RegisterNUICallback`, `RegisterKeyMapping` | — |
| Edition / build | `IsGameEnhancedVersion()`, `GetGameBuildNumber()` | `GetGameBuildNumber()`, `GetGameName()` = `'fxserver'` |

Server natives that take a player accept the **server id** (`source`) as number or string (`char* playerSrc`).

## 6. Player identifiers

`GetPlayerIdentifierByType(src, 'license')` → `'license:…'` or `nil`. Types: `license` (Rockstar, stable — the default account key), `license2`, `discord`, `fivem`, `steam`, `ip`. `xbl:` / `live:` were removed (see [server-ops.md](server-ops.md)). Don't key accounts on `steam` (optional) or `ip`. Hardware tokens: `GetNumPlayerTokens` / `GetPlayerToken`. Identifier list: https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/

## 7. Things that look like natives but are not

Defined in the Lua runtime (`citizen/scripting/lua/scheduler.lua`), **not** in the native DB, so `natives.py show` won't find them: `GetPlayers`, `GetPlayerIdentifiers`, `GetPlayerTokens`, `GetPlayerEP`, `PerformHttpRequest`, `PerformHttpRequestAwait`, `SendNUIMessage`, `RegisterNUICallback` (the native is `RegisterNuiCallback`), `RegisterNetEvent`, `RegisterServerEvent`, `AddEventHandler`, `RemoveEventHandler`, `TriggerEvent`, `TriggerServerEvent`, `TriggerClientEvent`, `TriggerLatent*Event`, `CreateThread`, `Wait`, `SetTimeout`, `ClearTimeout`, `RconPrint`, `RconLog`, `Player(src)`, `Entity(ent)`, `GlobalState`, `LocalPlayer`, `exports`, `json`, `msgpack`, `vector2/3/4`, `quat`.

Known `natives.py` limitations (as of this baseline): it does not index DB **aliases** (so `show DrawText` fails and `check --strict` reports legacy names like `DrawText` as UNKNOWN even though they work), and its non-native allowlist lacks `GetPlayers`, `GetPlayerIdentifiers`, `GetPlayerTokens`, `GetPlayerEP`, `PerformHttpRequestAwait`, `RconPrint`, `RconLog` (strict mode flags them). Treat those reports as false positives.

## 8. Frequently confused / deprecated

| Avoid | Use |
|---|---|
| `GetPlayerPed(-1)` | `PlayerPedId()` / `cache.ped` |
| `GetHashKey('x')` in hot loops | backtick `` `x` `` |
| `GetDistanceBetweenCoords(...)` | `#(a - b)` with vectors |
| `Citizen.CreateThread`, `Citizen.Wait` | `CreateThread`, `Wait` |
| `SetTextEntry`/`DrawText`, `SetNotificationTextEntry`/`DrawNotification` | `BeginTextCommandDisplayText`/`EndTextCommandDisplayText`, `BeginTextCommandThefeedPost`/`EndTextCommandThefeedPostTicker` (or ox_lib notify) |
| `PushScaleformMovieFunction*` | `BeginScaleformMovieMethod` / `ScaleformMovieMethodAddParam*` / `EndScaleformMovieMethod` |
| `StartShapeTestRay` / `CastRayPointToPoint` (synchronous, expensive) | `StartShapeTestLosProbe` + `GetShapeTestResult` |
| `NetworkRegisterEntityAsNetworked` hacks | server-side creation |
| `GetPlayerIdentifiers` + loop to find license | `GetPlayerIdentifierByType(src, 'license')` |
| `SetEntityAsMissionEntity` + `DeleteVehicle` dance | `DeleteEntity` with control / server-side delete |
| `SetStateOfClosestDoorOfType` | `AddDoorToSystem` + `DoorSystemSetDoorState` (or ox_doorlock) |
| `SetEntityDistanceCullingRadius` | flagged deprecated in the DB — avoid; rely on scope / server data |
| `DisableControlAction` every frame for whole UI | `SetNuiFocus` (+ `SetNuiFocusKeepInput` carefully), only while open |
| `DrawText3D` helpers every frame | ox_lib textUI / ox_target |
| `GetClosestVehicle` | `GetGamePool('CVehicle')` / `lib.getClosestVehicle` |

## 9. Top pitfalls (short version)

Details and more: [natives-essentials.md §28](natives-essentials.md#28-common-pitfalls).
- **Ownership:** tasks, velocity, health, deletion and most `Set*` natives only work on the entity's **owner**. Run them on the owner, request control (with timeout) or use a server native / state bag.
- **Load first:** `RequestModel` / `RequestAnimDict` / `RequestNamedPtfxAsset` / `RequestStreamedTextureDict` + `Has…Loaded` (with timeout, check `IsModelInCdimage`), then release (`SetModelAsNoLongerNeeded`, `RemoveAnimDict`).
- **Out-params are returns** (§3); don't pass placeholders.
- **Per-frame natives** (`Draw*`, `EndTextCommandDisplayText`, `DrawScaleformMovie*`, `Hide*ThisFrame`, `*DensityMultiplierThisFrame`, `DisableControlAction`, `DisablePlayerFiring`) must run every frame while active — gate the loop so it sleeps when idle.
- **Handles are local**; send network IDs between client and server and check `NetworkDoesEntityExistWithNetworkId` before converting.
- **Scope (~424 m):** clients don't see far entities/players; ask the server.
- **Never trust client-sent values** derived from natives; re-read on the server.

## 10. Game build and edition gating

Some natives/assets need a minimum game build (`sv_enforceGameBuild`, latest 3889). The catalogue marks `build ≥N` when the DB says "NativeDB Introduced: vN". Guard with manifest `dependencies { '/gameBuild:3889' }` or check `GetGameBuildNumber()` at runtime. GTA V Enhanced: `IsGameEnhancedVersion()` (client) — see [gta5-enhanced.md](gta5-enhanced.md).

## 11. Other runtimes (JS/TS, C#)

- JS/TS uses the same PascalCase global names; out-params are returned as an **array** (`const [found, z] = GetGroundZFor_3dCoord(x, y, z, false)`). Types: `@citizenfx/client`, `@citizenfx/server`.
- C#: `API.GetEntityCoords(...)` / `Function.Call<T>(Hash.GET_ENTITY_COORDS, ...)` in CitizenFX.Core; see [runtimes.md](runtimes.md).

## 12. Regenerating the catalogue

```bash
python scripts/natives.py update                    # refresh lookup cache
python scripts/build_natives_catalog.py --refresh   # re-download DB and rewrite assets/natives/
python scripts/build_natives_catalog.py --out /tmp/natives   # write elsewhere
```
Then update the "Baseline" lines here and in natives-essentials.md, and re-run the essentials verification (`natives.py show` on each listed name).

## 13. Sources

- Native reference: https://docs.fivem.net/natives/ · DB source: https://github.com/citizenfx/natives
- GTA V DB JSON: https://static.cfx.re/natives/natives.json · CFX DB JSON: https://runtime.fivem.net/doc/natives_cfx.json
- Lua codegen (naming, pointers, aliases): https://github.com/citizenfx/fivem/blob/master/ext/natives/codegen_out_lua.lua
- Lua runtime helpers (non-native globals): https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/scheduler.lua
- Identifiers: https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/
- OneSync: https://docs.fivem.net/docs/scripting-reference/onesync/ · State bags: https://docs.fivem.net/docs/scripting-manual/networking/state-bags/
- Game references: https://docs.fivem.net/docs/game-references/
