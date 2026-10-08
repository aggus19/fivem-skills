# Natives essentials — the most-used natives by task

Baseline: native DB fetched 2026-10-07 (GTA V DB + CFX DB). Every signature below was rendered from the DB and checked with `python scripts/natives.py show <Name>`.
Full catalogue of all natives: [assets/natives/README.md](../assets/natives/README.md). Guide and lookup workflow: [natives.md](natives.md).

## Contents
1. How to read this file
2. Player and ped state
3. Entities (any handle)
4. Vehicles — spawn, seats, state
5. Vehicles — mods, colours, plates, extras, livery
6. Vehicles — damage, repair, fuel, doors, locks
7. Vehicles — handling
8. Weapons
9. Ped AI and tasks
10. Animations, clipsets and scenarios
11. Props and objects
12. Streaming (models, dicts, assets)
13. Camera and screen effects
14. HUD, text, notifications, help text, scaleforms
15. Blips and waypoints
16. Markers and 3D drawing
17. Controls and input (+ control IDs)
18. Raycasts, ground and street lookup
19. World — time, weather, population, IPLs, interiors, doors
20. Audio
21. Particles, explosions, fire, timecycles
22. Network IDs and ownership (client)
23. Server CFX — players, identifiers, permissions
24. Server CFX — entities, routing buckets, OneSync
25. State bags (server and client)
26. Convars, resources, HTTP, KVP, misc runtime
27. Client CFX — NUI, DUI, runtime textures, keymapping, Discord, KVP
28. Common pitfalls
29. Deprecated / legacy names and their replacements
30. Game references (IDs, models, hashes, lists)
31. Sources

## 1. How to read this file

- Column 1 is the **Lua call** generated from the DB: `Name(typed args) → returns`. Pointer parameters (`int*`, `Vector3*`, `Entity*` …) are **not** passed — they are **returned** after the native's own result (rule from the citizenfx Lua codegen). Exception: when the only pointer is the last argument it is passed *and* returned, shown as `(in/out)` (e.g. `DeleteEntity(entity)`).
- Side: **C** = client only, **S** = server only, **C/S** = both (CFX `shared`). Some names exist on both sides as **different** natives (`GetEntityCoords`, `DeleteEntity`, `SetVehicleNumberPlateText`, …): both rows are listed where it matters, and their parameters differ.
- `Hash` parameters accept a backtick literal (`` `adder` ``) or a string (the Lua wrapper hashes strings). `char*` = string. `BOOL` = boolean. Server natives that take a player take its server id (`source`, number or string).
- Click the name for docs.fivem.net. Re-verify any native with `python scripts/natives.py show <Name>`.

## 2. Player and ped state

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`PlayerPedId`](https://docs.fivem.net/natives/?_0xD80958FC74E988A6)`()` → `Ped` | C | Local player's ped. Changes after `SetPlayerModel`/respawn — re-read it (ox_lib `cache.ped` tracks it). |
| [`PlayerId`](https://docs.fivem.net/natives/?_0x4F8644AF03D0E0D6)`()` → `Player` | C | Local player index (not the server id). |
| [`GetPlayerServerId`](https://docs.fivem.net/natives/?_0x4D97BCC7)`(Player player)` → `int` | C | Player index → server id (what the server calls `source`). |
| [`GetPlayerFromServerId`](https://docs.fivem.net/natives/?_0x344EA166)`(int serverId)` → `Player` | C | Server id → player index; `-1` if that player is not in scope. |
| [`GetActivePlayers`](https://docs.fivem.net/natives/?_0xCF143FB9)`()` → `object` | C | Only players **in scope** (OneSync culling), not the whole server. |
| [`GetPlayerPed`](https://docs.fivem.net/natives/?_0x43A66C31C68491C0)`(Player playerId)` → `Ped` | C | Player index → ped. Avoid `GetPlayerPed(-1)`; use `PlayerPedId()`. |
| [`GetPlayerName`](https://docs.fivem.net/natives/?_0x6D0DE6A7B5DA71F8)`(Player player)` → `char*` | C | Player index → name. |
| [`NetworkIsPlayerActive`](https://docs.fivem.net/natives/?_0xB8DFD30D6973E135)`(Player player)` → `BOOL` | C | Is this player index valid/active. |
| [`GetEntityHealth`](https://docs.fivem.net/natives/?_0xEEF059FAD016D209)`(Entity entity)` → `int` | C | Ped health ≤ 100 = dead for player peds; default max 200. |
| [`SetEntityHealth`](https://docs.fivem.net/natives/?_0x6B76DC1F3AE6E6A3)`(Entity entity, int health)` | C | On peds this is local; healing remote peds must happen on their owner. |
| [`GetPedMaxHealth`](https://docs.fivem.net/natives/?_0x4700A416E8324EF3)`(Ped ped)` → `int` | C |  |
| [`GetPedArmour`](https://docs.fivem.net/natives/?_0x9483AF821605B1D8)`(Ped ped)` → `int` | C | 0–100 (max set by `SetPlayerMaxArmour`). |
| [`SetPedArmour`](https://docs.fivem.net/natives/?_0xCEA04D83135264CC)`(Ped ped, int amount)` | C |  |
| [`IsEntityDead`](https://docs.fivem.net/natives/?_0x5F9532F3B5CC2551)`(Entity entity)` → `BOOL` | C |  |
| [`IsPedDeadOrDying`](https://docs.fivem.net/natives/?_0x3317DEDB88C95038)`(Ped ped, BOOL checkMeleeDeathFlags)` → `BOOL` | C | Prefer for "is down" checks (includes dying state). |
| [`NetworkResurrectLocalPlayer`](https://docs.fivem.net/natives/?_0xEA23C49EAA83ACFB)`(float x, float y, float z, float heading, int nInvincibilityTime, BOOL bLeaveDeadPed)` | C | Respawn/revive the local player at coords. |
| [`SetEntityInvincible`](https://docs.fivem.net/natives/?_0x3882114BDE571AD4)`(Entity entity, BOOL toggle)` | C | Works on any entity; for players also see `SetPlayerInvincible`. |
| [`SetPlayerInvincible`](https://docs.fivem.net/natives/?_0x239528EACDC3E7DE)`(Player player, BOOL bInvincible)` | C |  |
| [`SetPlayerModel`](https://docs.fivem.net/natives/?_0x00A1CADD00108836)`(Player player, Hash model)` | C | Model must be loaded; replaces the ped (handle changes!). Then `SetPedDefaultComponentVariation`. |
| [`SetPedDefaultComponentVariation`](https://docs.fivem.net/natives/?_0x45EEE61580806D63)`(Ped ped)` | C |  |
| [`SetPedComponentVariation`](https://docs.fivem.net/natives/?_0x262B14F48D29DE80)`(Ped ped, int componentId, int drawableId, int textureId, int paletteId)` | C | Clothing: componentId 0–11 (3 torso, 4 legs, 6 shoes, 8 undershirt, 11 jacket). |
| [`GetPedDrawableVariation`](https://docs.fivem.net/natives/?_0x67F3780DD425D4FC)`(Ped ped, int componentId)` → `int` | C |  |
| [`GetPedTextureVariation`](https://docs.fivem.net/natives/?_0x04A355E041E004E6)`(Ped ped, int componentId)` → `int` | C |  |
| [`SetPedPropIndex`](https://docs.fivem.net/natives/?_0x93376B65A266EB5F)`(Ped ped, int componentId, int drawableId, int textureId, BOOL attach)` | C | Props: 0 hat, 1 glasses, 2 ears, 6 watch, 7 bracelet. |
| [`ClearPedProp`](https://docs.fivem.net/natives/?_0x0943E5B8E078E76E)`(Ped ped, int propId)` | C |  |
| [`SetPedHeadBlendData`](https://docs.fivem.net/natives/?_0x9414E18B9434C2FE)`(Ped ped, int shapeFirstID, int shapeSecondID, int shapeThirdID, int skinFirstID, int skinSecondID, int skinThirdID, float shapeMix, float skinMix, float thirdMix, BOOL isParent)` | C | Freemode face/heritage. |
| [`SetPedConfigFlag`](https://docs.fivem.net/natives/?_0x1913FE4CBF41C463)`(Ped ped, int flagId, BOOL value)` | C | Ped behaviour flags (e.g. 32 = can fly through windscreen, 184 = prevent seat shuffle; 35 = UseHelmet, auto-wear helmet on bikes, not "no idle anims"). Flag list: DurtyFree dumps. |
| [`GetPedConfigFlag`](https://docs.fivem.net/natives/?_0x7EE53118C892B513)`(Ped ped, int flagId, BOOL p2)` → `BOOL` | C |  |
| [`SetPedCanRagdoll`](https://docs.fivem.net/natives/?_0xB128377056A54E2A)`(Ped ped, BOOL toggle)` | C |  |
| [`SetPedToRagdoll`](https://docs.fivem.net/natives/?_0xAE99FB955581844A)`(Ped ped, int minTime, int maxTime, int ragdollType, BOOL bAbortIfInjured, BOOL bAbortIfDead, BOOL bForceScriptControl)` → `BOOL` | C |  |
| [`IsPedRagdoll`](https://docs.fivem.net/natives/?_0x47E4E977581C5B55)`(Ped ped)` → `BOOL` | C |  |
| [`IsPedInAnyVehicle`](https://docs.fivem.net/natives/?_0x997ABD671D25CA0B)`(Ped ped, BOOL atGetIn)` → `BOOL` | C | `atGetIn=true` also counts entering. |
| [`GetVehiclePedIsIn`](https://docs.fivem.net/natives/?_0x9A9112A0FE9A4713)`(Ped ped, BOOL lastVehicle)` → `Vehicle` | C | `lastVehicle=true` returns the last vehicle even after exiting. |
| [`GetVehiclePedIsTryingToEnter`](https://docs.fivem.net/natives/?_0x814FA8BE5449445D)`(Ped ped)` → `Vehicle` | C |  |
| [`IsPedOnFoot`](https://docs.fivem.net/natives/?_0x01FEE67DB37F59B2)`(Ped ped)` → `BOOL` | C |  |
| [`IsPedSwimming`](https://docs.fivem.net/natives/?_0x9DE327631295B4C2)`(Ped ped)` → `BOOL` | C |  |
| [`IsPedFalling`](https://docs.fivem.net/natives/?_0xFB92A102F1C4DFA3)`(Ped ped)` → `BOOL` | C |  |
| [`IsPedArmed`](https://docs.fivem.net/natives/?_0x475768A975D5AD17)`(Ped ped, int typeFlags)` → `BOOL` | C | typeFlags bitmask: 1 melee, 2 explosive, 4 guns (7 = any). |
| [`IsPedAPlayer`](https://docs.fivem.net/natives/?_0x12534C348C6CB68B)`(Ped ped)` → `BOOL` | C |  |
| [`GetPedType`](https://docs.fivem.net/natives/?_0xFF059E1E4C01E63C)`(Ped ped)` → `int` | C |  |
| [`SetPlayerWantedLevel`](https://docs.fivem.net/natives/?_0x39FF19C64EF7DA5B)`(Player player, int wantedLevel, BOOL delayedResponse)` | C | Follow with `SetPlayerWantedLevelNow`. |
| [`ClearPlayerWantedLevel`](https://docs.fivem.net/natives/?_0xB302540597885499)`(Player player)` | C |  |
| [`SetMaxWantedLevel`](https://docs.fivem.net/natives/?_0xAA5F02DB48D704B9)`(int maxWantedLevel)` | C | `0` disables police wanted system for the local player. |
| [`SetRunSprintMultiplierForPlayer`](https://docs.fivem.net/natives/?_0x6DB47AA77FD94E09)`(Player player, float multiplier)` | C | 1.0–1.49 only. |
| [`ResetPlayerStamina`](https://docs.fivem.net/natives/?_0xA6F312FCCE9C1DFE)`(Player player)` | C |  |
| [`SetPlayerHealthRechargeMultiplier`](https://docs.fivem.net/natives/?_0x5DB660B38DD98A31)`(Player player, float regenRate)` | C | `0.0` disables health regen. |
| [`AddRelationshipGroup`](https://docs.fivem.net/natives/?_0xF372BC22FCB88606)`(char* name, Hash groupHash (in/out))` → `Any, Hash groupHash` | C | Returns the group hash as second value. |
| [`SetRelationshipBetweenGroups`](https://docs.fivem.net/natives/?_0xBF25EB89375A37AD)`(int relationship, Hash group1, Hash group2)` | C | 0 companion … 5 hate. |
| [`SetPedRelationshipGroupHash`](https://docs.fivem.net/natives/?_0xC80A74AC829DDD92)`(Ped ped, Hash hash)` | C |  |

## 3. Entities (any handle)

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`DoesEntityExist`](https://docs.fivem.net/natives/?_0x7239B21A38F536BA)`(Entity entity)` → `BOOL` | C | Always check before using a handle you stored. |
| [`GetEntityCoords`](https://docs.fivem.net/natives/?_0x3FEF770D40960D5A)`(Entity entity, BOOL alive)` → `Vector3` | C | Usually `GetEntityCoords(ent)` / `(ent, false)`; returns a `vector3`. |
| [`GetEntityCoords`](https://docs.fivem.net/natives/?_0x1647F1CB)`(Entity entity)` → `Vector3` | S | Server version: 1 arg, OneSync only. |
| [`SetEntityCoords`](https://docs.fivem.net/natives/?_0x06843DA7060A026B)`(Entity entity, float xPos, float yPos, float zPos, BOOL alive, BOOL deadFlag, BOOL ragdollFlag, BOOL clearArea)` | C | Teleport; `clearArea` should be `false` on MP. Use `SetEntityCoordsNoOffset` to avoid the offset quirk. |
| [`SetEntityCoordsNoOffset`](https://docs.fivem.net/natives/?_0x239A3351AC1DA385)`(Entity entity, float x, float y, float z, BOOL keepTasks, BOOL keepIK, BOOL doWarp)` | C |  |
| [`GetEntityHeading`](https://docs.fivem.net/natives/?_0xE83D4F9BA2A38914)`(Entity entity)` → `float` | C |  |
| [`SetEntityHeading`](https://docs.fivem.net/natives/?_0x8E2530AA8ADA980E)`(Entity entity, float heading)` | C |  |
| [`GetEntityRotation`](https://docs.fivem.net/natives/?_0xAFBD61CC738D9EB9)`(Entity entity, int rotationOrder)` → `Vector3` | C | rotationOrder 2 is the common default. |
| [`SetEntityRotation`](https://docs.fivem.net/natives/?_0x8524A8B0171D5E07)`(Entity entity, float pitch, float roll, float yaw, int rotationOrder, BOOL bDeadCheck)` | C |  |
| [`GetEntityVelocity`](https://docs.fivem.net/natives/?_0x4805D2B1D8CF94A9)`(Entity entity)` → `Vector3` | C |  |
| [`SetEntityVelocity`](https://docs.fivem.net/natives/?_0x1C99BB7B6E96D16F)`(Entity entity, float x, float y, float z)` | C |  |
| [`GetEntitySpeed`](https://docs.fivem.net/natives/?_0xD5037BA82E12416F)`(Entity entity)` → `float` | C | m/s (×3.6 km/h, ×2.236936 mph). |
| [`GetEntityForwardVector`](https://docs.fivem.net/natives/?_0x0A794A5A57F8DF91)`(Entity entity)` → `Vector3` | C |  |
| [`GetOffsetFromEntityInWorldCoords`](https://docs.fivem.net/natives/?_0x1899F328B0E12848)`(Entity entity, float offsetX, float offsetY, float offsetZ)` → `Vector3` | C | "2 m in front of the ped": offset (0, 2, 0). |
| [`GetOffsetFromEntityGivenWorldCoords`](https://docs.fivem.net/natives/?_0x2274BC1C4885E333)`(Entity entity, float posX, float posY, float posZ)` → `Vector3` | C | Inverse: world → local offset. |
| [`GetEntityModel`](https://docs.fivem.net/natives/?_0x9F47B058362C84B5)`(Entity entity)` → `Hash` | C |  |
| [`GetEntityType`](https://docs.fivem.net/natives/?_0x8ACD366038D14505)`(Entity entity)` → `int` | C | 0 none, 1 ped, 2 vehicle, 3 object. |
| [`IsEntityAPed`](https://docs.fivem.net/natives/?_0x524AC5ECEA15343E)`(Entity entity)` → `BOOL` | C |  |
| [`IsEntityAVehicle`](https://docs.fivem.net/natives/?_0x6AC7003FA6E5575E)`(Entity entity)` → `BOOL` | C |  |
| [`IsEntityAnObject`](https://docs.fivem.net/natives/?_0x8D68C8FD0FACA94E)`(Entity entity)` → `BOOL` | C |  |
| [`FreezeEntityPosition`](https://docs.fivem.net/natives/?_0x428CA6DBD1094446)`(Entity entity, BOOL toggle)` | C |  |
| [`SetEntityVisible`](https://docs.fivem.net/natives/?_0xEA1C610A04DB6BBB)`(Entity entity, BOOL toggle, BOOL unk)` | C |  |
| [`SetEntityAlpha`](https://docs.fivem.net/natives/?_0x44A0870B7E92D7C0)`(Entity entity, int alphaLevel, BOOL skin)` | C | 0–255; `ResetEntityAlpha` to restore. |
| [`ResetEntityAlpha`](https://docs.fivem.net/natives/?_0x9B1E824FFBB7027A)`(Entity entity)` | C |  |
| [`SetEntityCollision`](https://docs.fivem.net/natives/?_0x1A9205C1B9EE827F)`(Entity entity, BOOL toggle, BOOL keepPhysics)` | C |  |
| [`SetEntityDynamic`](https://docs.fivem.net/natives/?_0x1718DE8E3F2823CA)`(Entity entity, BOOL toggle)` | C |  |
| [`SetEntityAsMissionEntity`](https://docs.fivem.net/natives/?_0xAD738C3085FE7E11)`(Entity entity, BOOL scriptHostObject, BOOL bGrabFromOtherScript)` | C | Keeps the game from cleaning it up; required before some delete paths. |
| [`SetEntityAsNoLongerNeeded`](https://docs.fivem.net/natives/?_0xB736A491E64A32CF)`(Entity entity (in/out))` → `Entity entity` | C | Hand the entity back to the game's cleanup (in/out handle). |
| [`DeleteEntity`](https://docs.fivem.net/natives/?_0xAE3CBE5BF394C9C9)`(Entity entity (in/out))` → `Entity entity` | C | Needs network control of the entity (or do it on the server). |
| [`DeleteEntity`](https://docs.fivem.net/natives/?_0xFAA3D236)`(Entity entity)` | S | Preferred for networked entities. |
| [`AttachEntityToEntity`](https://docs.fivem.net/natives/?_0x6B9BBD38AB0796DF)`(Entity entity1, Entity entity2, int boneIndex, float xPos, float yPos, float zPos, float xRot, float yRot, float zRot, BOOL p9, BOOL useSoftPinning, BOOL collision, BOOL isPed, int rotationOrder, BOOL syncRot)` | C | Bone index from `GetPedBoneIndex` / `GetEntityBoneIndexByName`. |
| [`DetachEntity`](https://docs.fivem.net/natives/?_0x961AC54BF0613F5D)`(Entity entity, BOOL dynamic, BOOL collision)` | C |  |
| [`IsEntityAttached`](https://docs.fivem.net/natives/?_0xB346476EF1A64897)`(Entity entity)` → `BOOL` | C |  |
| [`IsEntityAttachedToEntity`](https://docs.fivem.net/natives/?_0xEFBE71898A993728)`(Entity from, Entity to)` → `BOOL` | C |  |
| [`GetPedBoneIndex`](https://docs.fivem.net/natives/?_0x3F428D08BE5AAE31)`(Ped ped, int boneId)` → `int` | C | Ped bone **ID** (e.g. 57005 right hand, 18905 left hand, 31086 head) → index. |
| [`GetEntityBoneIndexByName`](https://docs.fivem.net/natives/?_0xFB71170B7E76ACBA)`(Entity entity, char* boneName)` → `int` | C | Vehicles/objects: bone name (e.g. `'boot'`, `'bonnet'`, `'wheel_lf'`). |
| [`GetWorldPositionOfEntityBone`](https://docs.fivem.net/natives/?_0x44A8FCB8ED227738)`(Entity entity, int boneIndex)` → `Vector3` | C |  |
| [`HasEntityClearLosToEntity`](https://docs.fivem.net/natives/?_0xFCDFF7B72D23A1AC)`(Entity entity1, Entity entity2, int flags)` → `BOOL` | C | Line-of-sight check; `flags` are trace flags (17 = world + objects). |
| [`IsEntityInWater`](https://docs.fivem.net/natives/?_0xCFB0A0D8EDD145A3)`(Entity entity)` → `BOOL` | C |  |
| [`GetEntityHeightAboveGround`](https://docs.fivem.net/natives/?_0x1DD55701034110E5)`(Entity entity)` → `float` | C |  |
| [`IsEntityInZone`](https://docs.fivem.net/natives/?_0xB6463CF6AF527071)`(Entity entity, char* zone)` → `BOOL` | C | Zone names: docs game-references/zones. |
| [`GetGamePool`](https://docs.fivem.net/natives/?_0x2B9D4F50)`(char* poolName)` → `object` | C/S | `'CPed'`, `'CVehicle'`, `'CObject'`, `'CPickup'` — all local entities (replaces Find*/Enumerate loops). |

## 4. Vehicles — spawn, seats, state

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`CreateVehicle`](https://docs.fivem.net/natives/?_0xAF35D0D2583051B0)`(Hash modelHash, float x, float y, float z, float heading, BOOL isNetwork, BOOL netMissionEntity)` → `Vehicle` | C | Model must be loaded. With entity lockdown (default for new buckets in strict mode) client creation is blocked — spawn on the server. |
| [`CreateVehicleServerSetter`](https://docs.fivem.net/natives/?_0x6AE51D4B)`(Hash modelHash, char* type, float x, float y, float z, float heading)` → `Vehicle` | S | Recommended server spawn: `type` = `'automobile'`, `'bike'`, `'boat'`, `'heli'`, `'plane'`, `'submarine'`, `'trailer'`, `'train'`. No model load needed on server. |
| [`CreateVehicle`](https://docs.fivem.net/natives/?_0xDD75460A)`(Hash modelHash, float x, float y, float z, float heading, BOOL isNetwork, BOOL netMissionEntity)` → `Entity` | S | Legacy server RPC spawn (uses a client to create it); prefer `CreateVehicleServerSetter`. |
| [`GetVehicleType`](https://docs.fivem.net/natives/?_0xA273060E)`(Vehicle vehicle)` → `char*` | C/S | Server: returns the type string needed by `CreateVehicleServerSetter` (vehicle must exist). |
| [`SetVehicleOnGroundProperly`](https://docs.fivem.net/natives/?_0x49733E92263139D1)`(Vehicle vehicle)` → `BOOL` | C |  |
| [`SetPedIntoVehicle`](https://docs.fivem.net/natives/?_0xF75B0D629E1C063D)`(Ped ped, Vehicle vehicle, int seatIndex)` | C | seatIndex: -1 driver, 0 front passenger, 1+ rear. -2 = any free seat. |
| [`SetPedIntoVehicle`](https://docs.fivem.net/natives/?_0x7500C79)`(Ped ped, Vehicle vehicle, int seatIndex)` | S | Server RPC version. |
| [`TaskWarpPedIntoVehicle`](https://docs.fivem.net/natives/?_0x9A7D091411C5F684)`(Ped ped, Vehicle vehicle, int seatIndex)` | C | Task version (more reliable right after spawn). |
| [`GetPedInVehicleSeat`](https://docs.fivem.net/natives/?_0xBB40DD2270B65366)`(Vehicle vehicle, int seatIndex)` → `Ped` | C |  |
| [`IsVehicleSeatFree`](https://docs.fivem.net/natives/?_0x22AC59A870E6A669)`(Vehicle vehicle, int seatIndex)` → `BOOL` | C |  |
| [`GetVehicleMaxNumberOfPassengers`](https://docs.fivem.net/natives/?_0xA7C4F2C6E744A550)`(Vehicle vehicle)` → `int` | C | Excludes the driver. |
| [`GetVehicleNumberOfPassengers`](https://docs.fivem.net/natives/?_0x24CB2137731FFE89)`(Vehicle vehicle)` → `int` | C |  |
| [`GetVehicleClass`](https://docs.fivem.net/natives/?_0x29439776AAA00A62)`(Vehicle vehicle)` → `int` | C | 0 compacts … 8 motorcycles, 14 boats, 15 helicopters, 16 planes, 18 emergency, 21 trains. |
| [`GetVehicleClassFromName`](https://docs.fivem.net/natives/?_0xDEDF1C8BD47C2200)`(Hash modelHash)` → `int` | C | Same from a model hash (no entity needed). |
| [`GetDisplayNameFromVehicleModel`](https://docs.fivem.net/natives/?_0xB215AAC32D25D019)`(Hash modelHash)` → `char*` | C | Returns a label key; wrap with `GetLabelText` (alias of `GetFilenameForAudioConversation`) for the display name. |
| [`GetMakeNameFromVehicleModel`](https://docs.fivem.net/natives/?_0xF7AF4F159FF99F97)`(Hash modelHash)` → `char*` | C |  |
| [`IsThisModelACar`](https://docs.fivem.net/natives/?_0x7F6DB52EEFC96DF8)`(Hash model)` → `BOOL` | C | Also `IsThisModelABike`, `…AHeli`, `…APlane`, `…ABoat`. |
| [`IsModelAVehicle`](https://docs.fivem.net/natives/?_0x19AAC8F07BFEC53E)`(Hash model)` → `BOOL` | C |  |
| [`GetClosestVehicle`](https://docs.fivem.net/natives/?_0xF73EB622C4F1689B)`(float x, float y, float z, float radius, Hash modelHash, int flags)` → `Vehicle` | C | Unreliable (ignores many vehicles); prefer `GetGamePool('CVehicle')` or `lib.getClosestVehicle`. |
| [`SetVehicleEngineOn`](https://docs.fivem.net/natives/?_0x2497C4717C8B881E)`(Vehicle vehicle, BOOL value, BOOL instantly, BOOL disableAutoStart)` | C | `instantly`, `disableAutoStart`. |
| [`GetIsVehicleEngineRunning`](https://docs.fivem.net/natives/?_0xAE31E7DF9B5B132E)`(Vehicle vehicle)` → `BOOL` | C |  |
| [`SetVehicleUndriveable`](https://docs.fivem.net/natives/?_0x8ABA6AF54B942B95)`(Vehicle vehicle, BOOL toggle)` | C |  |
| [`SetVehicleHasBeenOwnedByPlayer`](https://docs.fivem.net/natives/?_0x2B5F9D2AF1F1722D)`(Vehicle vehicle, BOOL owned)` | C | Prevents some NPC/cleanup behaviour. |
| [`SetVehicleNeedsToBeHotwired`](https://docs.fivem.net/natives/?_0xFBA550EA44404EE6)`(Vehicle vehicle, BOOL toggle)` | C |  |
| [`SetVehicleLights`](https://docs.fivem.net/natives/?_0x34E710FF01247C5A)`(Vehicle vehicle, int state)` | C | 0 normal, 1 always off, 2 always on. |
| [`SetVehicleSiren`](https://docs.fivem.net/natives/?_0xF4924635A19EB37D)`(Vehicle vehicle, BOOL toggle)` | C |  |
| [`SetVehicleHasMutedSirens`](https://docs.fivem.net/natives/?_0xD8050E0EB60CF274)`(Vehicle vehicle, BOOL toggle)` | C | Lights without the siren sound. |
| [`SetVehicleForwardSpeed`](https://docs.fivem.net/natives/?_0xAB54A438726D25D5)`(Vehicle vehicle, float speed)` | C | Launch speed (m/s). |
| [`ModifyVehicleTopSpeed`](https://docs.fivem.net/natives/?_0x93A3996368C94158)`(Vehicle vehicle, float percentChange)` | C | Percent bonus; needs re-applying after some changes. |
| [`SetEntityMaxSpeed`](https://docs.fivem.net/natives/?_0x0E46A3FCBDE2A1B1)`(Entity entity, float speed)` | C | Speed limiter (m/s). |
| [`GetVehicleEstimatedMaxSpeed`](https://docs.fivem.net/natives/?_0x53AF99BAA671CA47)`(Vehicle vehicle)` → `float` | C |  |
| [`DeleteVehicle`](https://docs.fivem.net/natives/?_0xEA386986E786A54F)`(Vehicle vehicle (in/out))` → `Vehicle vehicle` | C | Client; needs control + mission entity. Prefer `DeleteEntity`. |

## 5. Vehicles — mods, colours, plates, extras, livery

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`SetVehicleModKit`](https://docs.fivem.net/natives/?_0x1F2AA07F00B3217A)`(Vehicle vehicle, int modKit)` | C | **Call `SetVehicleModKit(veh, 0)` before any `SetVehicleMod`.** |
| [`GetNumVehicleMods`](https://docs.fivem.net/natives/?_0xE38E9162A2500646)`(Vehicle vehicle, int modType)` → `int` | C |  |
| [`SetVehicleMod`](https://docs.fivem.net/natives/?_0x6AF0636DDEDCB6DD)`(Vehicle vehicle, int modType, int modIndex, BOOL customTires)` | C | modType 0 spoiler … 11 engine, 12 brakes, 13 transmission, 15 suspension, 16 armour, 23 front wheels, 48 livery. `-1` = stock. |
| [`GetVehicleMod`](https://docs.fivem.net/natives/?_0x772960298DA26FDB)`(Vehicle vehicle, int modType)` → `int` | C |  |
| [`ToggleVehicleMod`](https://docs.fivem.net/natives/?_0x2A1F4F37F95BAD08)`(Vehicle vehicle, int modType, BOOL toggle)` | C | Toggle mods: 18 turbo, 20 tyre smoke, 22 xenon. |
| [`IsToggleModOn`](https://docs.fivem.net/natives/?_0x84B233A8C8FC8AE7)`(Vehicle vehicle, int modType)` → `BOOL` | C |  |
| [`SetVehicleWheelType`](https://docs.fivem.net/natives/?_0x487EB21CC7295BA1)`(Vehicle vehicle, int wheelType)` | C | Set before wheel mods (23/24). |
| [`SetVehicleColours`](https://docs.fivem.net/natives/?_0x4F1D4BE3A7F24601)`(Vehicle vehicle, int colorPrimary, int colorSecondary)` | C | Indexes from the vehicle colour list. |
| [`SetVehicleColours`](https://docs.fivem.net/natives/?_0x57F24253)`(Vehicle vehicle, int colorPrimary, int colorSecondary)` | S | Server RPC. |
| [`GetVehicleColours`](https://docs.fivem.net/natives/?_0xA19435F193E081AC)`(Vehicle vehicle)` → `int colorPrimary, int colorSecondary` | C |  |
| [`SetVehicleExtraColours`](https://docs.fivem.net/natives/?_0x2036F561ADD12E33)`(Vehicle vehicle, int pearlescentColor, int wheelColor)` | C | Pearlescent + wheel colour. |
| [`GetVehicleExtraColours`](https://docs.fivem.net/natives/?_0x3BC4245933A166F7)`(Vehicle vehicle)` → `int pearlescentColor, int wheelColor` | C |  |
| [`SetVehicleCustomPrimaryColour`](https://docs.fivem.net/natives/?_0x7141766F91D15BEA)`(Vehicle vehicle, int r, int g, int b)` | C | RGB; overrides the indexed colour. |
| [`SetVehicleCustomSecondaryColour`](https://docs.fivem.net/natives/?_0x36CED73BFED89754)`(Vehicle vehicle, int r, int g, int b)` | C |  |
| [`GetVehicleCustomPrimaryColour`](https://docs.fivem.net/natives/?_0xB64CF2CCA9D95F52)`(Vehicle vehicle)` → `int r, int g, int b` | C |  |
| [`ClearVehicleCustomPrimaryColour`](https://docs.fivem.net/natives/?_0x55E1D2758F34E437)`(Vehicle vehicle)` | C |  |
| [`SetVehicleXenonLightsColor`](https://docs.fivem.net/natives/?_0xE41033B25D003A07)`(Vehicle vehicle, int color)` | C | Requires mod 22 on; index 0–12, 255 default. |
| [`SetVehicleNeonLightEnabled`](https://docs.fivem.net/natives/?_0x2AA720E4287BF269)`(Vehicle vehicle, int index, BOOL toggle)` | C | index 0 left, 1 right, 2 front, 3 back. |
| [`SetVehicleNeonLightsColour`](https://docs.fivem.net/natives/?_0x8E0A582209A62695)`(Vehicle vehicle, int r, int g, int b)` | C |  |
| [`SetVehicleTyreSmokeColor`](https://docs.fivem.net/natives/?_0xB5BA80F839791C0F)`(Vehicle vehicle, int r, int g, int b)` | C | Requires mod 20. |
| [`SetVehicleWindowTint`](https://docs.fivem.net/natives/?_0x57C51E6BAD752696)`(Vehicle vehicle, int tint)` | C |  |
| [`SetVehicleNumberPlateText`](https://docs.fivem.net/natives/?_0x95A88F0B409CDA47)`(Vehicle vehicle, char* plateText)` | C | Max 8 characters. |
| [`SetVehicleNumberPlateText`](https://docs.fivem.net/natives/?_0x400F9556)`(Vehicle vehicle, char* plateText)` | S | Server RPC. |
| [`GetVehicleNumberPlateText`](https://docs.fivem.net/natives/?_0x7CE1CCB9B293020E)`(Vehicle vehicle)` → `char*` | C | Returns padded text — `trim` it before comparing/storing. |
| [`GetVehicleNumberPlateText`](https://docs.fivem.net/natives/?_0xE8522D58)`(Vehicle vehicle)` → `char*` | S |  |
| [`SetVehicleNumberPlateTextIndex`](https://docs.fivem.net/natives/?_0x9088EB5A43FFB0A1)`(Vehicle vehicle, int plateIndex)` | C | Plate style index (see `GetVehicleNumberPlateTextIndex` docs). |
| [`DoesExtraExist`](https://docs.fivem.net/natives/?_0x1262D55792428154)`(Vehicle vehicle, int extraId)` → `BOOL` | C |  |
| [`IsVehicleExtraTurnedOn`](https://docs.fivem.net/natives/?_0xD2E6822DBFD6C8BD)`(Vehicle vehicle, int extraId)` → `BOOL` | C |  |
| [`SetVehicleExtra`](https://docs.fivem.net/natives/?_0x7EE3A3C5E4A40CC9)`(Vehicle vehicle, int extraId, BOOL disable)` | C | **Inverted:** `disable=false` turns the extra ON. Repairs the vehicle as a side effect. |
| [`SetVehicleLivery`](https://docs.fivem.net/natives/?_0x60BF608F1B8CD1B6)`(Vehicle vehicle, int livery)` | C | Model "liveries" (not mod 48). |
| [`GetVehicleLivery`](https://docs.fivem.net/natives/?_0x2BB9230590DA5E8A)`(Vehicle vehicle)` → `int` | C |  |
| [`GetVehicleLiveryCount`](https://docs.fivem.net/natives/?_0x87B63E25A529D526)`(Vehicle vehicle)` → `int` | C | -1 when the model has none (then try mod 48). |
| [`SetVehicleDirtLevel`](https://docs.fivem.net/natives/?_0x79D3B596FE44EE8B)`(Vehicle vehicle, float dirtLevel)` | C | 0.0–15.0. |
| [`GetVehicleDirtLevel`](https://docs.fivem.net/natives/?_0x8F17BC8BA08DA62B)`(Vehicle vehicle)` → `float` | C |  |
| [`WashDecalsFromVehicle`](https://docs.fivem.net/natives/?_0x5B712761429DBC14)`(Vehicle vehicle, float p1)` | C |  |

## 6. Vehicles — damage, repair, fuel, doors, locks

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GetVehicleEngineHealth`](https://docs.fivem.net/natives/?_0xC45D23BAF168AAB8)`(Vehicle vehicle)` → `float` | C | -4000…1000; < 0 = burning/broken. |
| [`SetVehicleEngineHealth`](https://docs.fivem.net/natives/?_0x45F6D8EEF34ABEF1)`(Vehicle vehicle, float health)` | C |  |
| [`GetVehicleBodyHealth`](https://docs.fivem.net/natives/?_0xF271147EB7B40F12)`(Vehicle vehicle)` → `float` | C | 0…1000. |
| [`SetVehicleBodyHealth`](https://docs.fivem.net/natives/?_0xB77D05AC8C78AADB)`(Vehicle vehicle, float value)` | C |  |
| [`GetVehiclePetrolTankHealth`](https://docs.fivem.net/natives/?_0x7D5DABE888D2D074)`(Vehicle vehicle)` → `float` | C |  |
| [`SetVehicleFixed`](https://docs.fivem.net/natives/?_0x115722B1B9C14C1C)`(Vehicle vehicle)` | C | Repairs everything (owner-side). |
| [`SetVehicleDeformationFixed`](https://docs.fivem.net/natives/?_0x953DA1E1B12C0491)`(Vehicle vehicle)` | C | Only visual deformation. |
| [`SetVehicleTyreBurst`](https://docs.fivem.net/natives/?_0xEC6A202EE4960385)`(Vehicle vehicle, int index, BOOL onRim, float p3)` | C | onRim + damage 1000.0 for a flat. |
| [`SetVehicleTyreFixed`](https://docs.fivem.net/natives/?_0x6E13FC662B882D1D)`(Vehicle vehicle, int tyreIndex)` | C |  |
| [`IsVehicleTyreBurst`](https://docs.fivem.net/natives/?_0xBA291848A0815CA9)`(Vehicle vehicle, int wheelID, BOOL isBurstToRim)` → `BOOL` | C |  |
| [`SetVehicleTyresCanBurst`](https://docs.fivem.net/natives/?_0xEB9DC3C7D8596C46)`(Vehicle vehicle, BOOL toggle)` | C |  |
| [`SmashVehicleWindow`](https://docs.fivem.net/natives/?_0x9E5B5E4D2CCD2259)`(Vehicle vehicle, int windowIndex)` | C |  |
| [`SetVehicleDoorBroken`](https://docs.fivem.net/natives/?_0xD4D4F6A4AB575A33)`(Vehicle vehicle, int doorIndex, BOOL deleteDoor)` | C |  |
| [`GetVehicleFuelLevel`](https://docs.fivem.net/natives/?_0x5F739BB8)`(Vehicle vehicle)` → `float` | C | Scale follows the model's tank volume; fuel scripts treat it as 0–100 and keep the truth in a state bag. |
| [`SetVehicleFuelLevel`](https://docs.fivem.net/natives/?_0xBA970511)`(Vehicle vehicle, float level)` | C | Only matters on the entity owner; most servers use a fuel resource (ox_fuel/LegacyFuel) instead. |
| [`SetVehicleDoorOpen`](https://docs.fivem.net/natives/?_0x7C65DAC73C35C862)`(Vehicle vehicle, int doorIndex, BOOL loose, BOOL openInstantly)` | C | doorIndex 0 FL, 1 FR, 2 RL, 3 RR, 4 hood, 5 trunk. |
| [`SetVehicleDoorShut`](https://docs.fivem.net/natives/?_0x93D9BD300D7789E5)`(Vehicle vehicle, int doorIndex, BOOL closeInstantly)` | C |  |
| [`GetVehicleDoorAngleRatio`](https://docs.fivem.net/natives/?_0xFE3F9C29F7B32BD5)`(Vehicle vehicle, int doorIndex)` → `float` | C | > 0 = open. |
| [`SetVehicleDoorsLocked`](https://docs.fivem.net/natives/?_0xB664292EAECF7FA6)`(Vehicle vehicle, int doorLockStatus)` | C | eVehicleLockState: 1 unlocked, 2 locked, 3 locked for players only, 4 locked with player inside, 7 locked but damageable… (full table on docs). |
| [`SetVehicleDoorsLocked`](https://docs.fivem.net/natives/?_0x4CDD35D0)`(Vehicle vehicle, int doorLockStatus)` | S | **Server-side lock is the reliable way** under OneSync. |
| [`GetVehicleDoorLockStatus`](https://docs.fivem.net/natives/?_0x25BC98A59C2EA962)`(Vehicle vehicle)` → `int` | C |  |
| [`GetVehicleDoorLockStatus`](https://docs.fivem.net/natives/?_0xD72CEF2)`(Vehicle vehicle)` → `int` | S |  |
| [`SetVehicleDoorsLockedForAllPlayers`](https://docs.fivem.net/natives/?_0xA2F80B8D040727CC)`(Vehicle vehicle, BOOL toggle)` | C |  |
| [`SetVehicleDoorsLockedForPlayer`](https://docs.fivem.net/natives/?_0x517AAF684BB50CD1)`(Vehicle vehicle, Player player, BOOL toggle)` | C |  |

## 7. Vehicles — handling

All per-vehicle handling natives are CFX client natives and only change the **local** instance (call on every client, e.g. from a state bag handler). Field names: `fMass`, `fInitialDriveForce`, `fBrakeForce`, `fTractionCurveMax`, `fInitialDriveMaxFlatVel`, `nInitialDriveGears`, `strAdvancedFlags`… (see the handling.meta reference).

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GetVehicleHandlingFloat`](https://docs.fivem.net/natives/?_0x642FC12F)`(Vehicle vehicle, char* class_, char* fieldName)` → `float` | C | class is always `'CHandlingData'` (or `'CCarHandlingData'` etc. for sub-handling). |
| [`SetVehicleHandlingFloat`](https://docs.fivem.net/natives/?_0x488C86D2)`(Vehicle vehicle, char* class_, char* fieldName, float value)` | C |  |
| [`GetVehicleHandlingInt`](https://docs.fivem.net/natives/?_0x27396C75)`(Vehicle vehicle, char* class_, char* fieldName)` → `int` | C |  |
| [`SetVehicleHandlingInt`](https://docs.fivem.net/natives/?_0xC37F4CF9)`(Vehicle vehicle, char* class_, char* fieldName, int value)` | C |  |
| [`GetVehicleHandlingVector`](https://docs.fivem.net/natives/?_0xFB341304)`(Vehicle vehicle, char* class_, char* fieldName)` → `Vector3` | C |  |
| [`SetVehicleHandlingVector`](https://docs.fivem.net/natives/?_0x12497890)`(Vehicle vehicle, char* class_, char* fieldName, Vector3 value)` | C |  |
| [`SetVehicleHandlingField`](https://docs.fivem.net/natives/?_0x2BA40795)`(Vehicle vehicle, char* class_, char* fieldName, Any value)` | C | Generic setter (any type). |
| [`SetHandlingFloat`](https://docs.fivem.net/natives/?_0x90DD01C)`(char* vehicle, char* class_, char* fieldName, float value)` | C | Changes the **model's** handling (all vehicles of that model). |
| [`GetVehicleTopSpeedModifier`](https://docs.fivem.net/natives/?_0x998B7FEE)`(Vehicle vehicle)` → `float` | C |  |
| [`SetVehicleCheatPowerIncrease`](https://docs.fivem.net/natives/?_0xB59E4BD37AE292DB)`(Vehicle vehicle, float value)` | C | Engine power multiplier — reapply each frame while needed. |

## 8. Weapons

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GiveWeaponToPed`](https://docs.fivem.net/natives/?_0xBF0FD6E56C964FCB)`(Ped ped, Hash weaponHash, int ammoCount, BOOL isHidden, BOOL bForceInHand)` | C | Client-side give is local; servers with ox_inventory/framework weapons should use those APIs. |
| [`GiveWeaponToPed`](https://docs.fivem.net/natives/?_0xC4D88A85)`(Ped ped, Hash weaponHash, int ammoCount, BOOL isHidden, BOOL bForceInHand)` | S | Server RPC. |
| [`RemoveWeaponFromPed`](https://docs.fivem.net/natives/?_0x4899CB088EDF59B8)`(Ped ped, Hash weaponHash)` | C |  |
| [`RemoveAllPedWeapons`](https://docs.fivem.net/natives/?_0xF25DF915FA38C5F3)`(Ped ped, BOOL p1)` | C |  |
| [`RemoveAllPedWeapons`](https://docs.fivem.net/natives/?_0xA44CE817)`(Ped ped, BOOL p1)` | S |  |
| [`HasPedGotWeapon`](https://docs.fivem.net/natives/?_0x8DECB02F88F428BC)`(Ped ped, Hash weaponHash, BOOL p2)` → `BOOL` | C |  |
| [`SetCurrentPedWeapon`](https://docs.fivem.net/natives/?_0xADF692B254977C0C)`(Ped ped, Hash weaponHash, BOOL bForceInHand)` | C | `` `WEAPON_UNARMED` `` to holster. |
| [`GetSelectedPedWeapon`](https://docs.fivem.net/natives/?_0x0A6DB4965674D243)`(Ped ped)` → `Hash` | C | Returns hash directly (simplest). |
| [`GetSelectedPedWeapon`](https://docs.fivem.net/natives/?_0xD240123E)`(Ped ped)` → `Hash` | S |  |
| [`GetCurrentPedWeapon`](https://docs.fivem.net/natives/?_0x3A87E44BB9A01D54)`(Ped ped, BOOL p2)` → `BOOL, Hash weaponHash` | C | Returns `retval, weaponHash`. |
| [`SetPedAmmo`](https://docs.fivem.net/natives/?_0x14E56BC5B5DB6A19)`(Ped ped, Hash weaponHash, int ammo)` | C |  |
| [`GetAmmoInPedWeapon`](https://docs.fivem.net/natives/?_0x015A522136D7F951)`(Ped ped, Hash weaponhash)` → `int` | C |  |
| [`AddAmmoToPed`](https://docs.fivem.net/natives/?_0x78F0424C34306220)`(Ped ped, Hash weaponHash, int ammo)` | C |  |
| [`GetAmmoInClip`](https://docs.fivem.net/natives/?_0x2E1202248937775C)`(Ped ped, Hash weaponHash, int ammo (in/out))` → `BOOL, int ammo` | C |  |
| [`SetAmmoInClip`](https://docs.fivem.net/natives/?_0xDCD2A934D65CB497)`(Ped ped, Hash weaponHash, int ammo)` → `BOOL` | C |  |
| [`GetMaxAmmoInClip`](https://docs.fivem.net/natives/?_0xA38DCFFCEA8962FA)`(Ped ped, Hash weaponHash, BOOL p2)` → `int` | C |  |
| [`GiveWeaponComponentToPed`](https://docs.fivem.net/natives/?_0xD966D51AA5B28BB9)`(Ped ped, Hash weaponHash, Hash componentHash)` | C | Component hashes: weapon-models reference. |
| [`RemoveWeaponComponentFromPed`](https://docs.fivem.net/natives/?_0x1E8BE90C74FB4C09)`(Ped ped, Hash weaponHash, Hash componentHash)` | C |  |
| [`HasPedGotWeaponComponent`](https://docs.fivem.net/natives/?_0xC593212475FAE340)`(Ped ped, Hash weaponHash, Hash componentHash)` → `BOOL` | C |  |
| [`SetPedWeaponTintIndex`](https://docs.fivem.net/natives/?_0x50969B9B89ED5738)`(Ped ped, Hash weaponHash, int tintIndex)` | C |  |
| [`IsPedShooting`](https://docs.fivem.net/natives/?_0x34616828CD07F1A1)`(Ped ped)` → `BOOL` | C |  |
| [`IsPlayerFreeAiming`](https://docs.fivem.net/natives/?_0x2E397FD2ECD37C87)`(Player player)` → `BOOL` | C |  |
| [`GetEntityPlayerIsFreeAimingAt`](https://docs.fivem.net/natives/?_0x2975C866E6713290)`(Player player, Entity entity (in/out))` → `BOOL, Entity entity` | C | Returns `retval, entity`. |
| [`SetPedInfiniteAmmo`](https://docs.fivem.net/natives/?_0x3EDCB0505123623B)`(Ped ped, BOOL toggle, Hash weaponHash)` | C |  |
| [`SetPedInfiniteAmmoClip`](https://docs.fivem.net/natives/?_0x183DADC6AA953186)`(Ped ped, BOOL toggle)` | C |  |
| [`SetPedDropsWeaponsWhenDead`](https://docs.fivem.net/natives/?_0x476AE72C1D19D1A8)`(Ped ped, BOOL toggle)` | C |  |
| [`IsWeaponValid`](https://docs.fivem.net/natives/?_0x937C71165CF334B3)`(Hash weaponHash)` → `BOOL` | C |  |
| [`GetWeapontypeGroup`](https://docs.fivem.net/natives/?_0xC3287EE3050FB74C)`(Hash weaponHash)` → `Hash` | C |  |
| [`SetWeaponDamageModifier`](https://docs.fivem.net/natives/?_0x4757F00BC6323CFE)`(Hash weaponHash, float damageMultiplier)` | C | CFX client: per weapon type, local. |
| [`SetPlayerWeaponDamageModifier`](https://docs.fivem.net/natives/?_0xCE07B9F7817AADA3)`(Player player, float modifier)` | C |  |
| [`DisablePlayerFiring`](https://docs.fivem.net/natives/?_0x5E6CC07646BBEAB8)`(Player player, BOOL toggle)` | C | **Per frame.** |
| [`SetWeaponsNoAutoreload`](https://docs.fivem.net/natives/?_0x311150E5)`(BOOL state)` | C |  |
| [`SetWeaponsNoAutoswap`](https://docs.fivem.net/natives/?_0x2A7B50E)`(BOOL state)` | C |  |

## 9. Ped AI and tasks

Tasks only run on the client that **owns** the ped. Load the model first; spawn networked peds on the server when possible.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`CreatePed`](https://docs.fivem.net/natives/?_0xD49F9B0955C367DE)`(int pedType, Hash modelHash, float x, float y, float z, float heading, BOOL isNetwork, BOOL bScriptHostPed)` → `Ped` | C | pedType 4 civ male, 5 civ female (the model mostly decides). Model must be loaded. |
| [`CreatePed`](https://docs.fivem.net/natives/?_0x389EF71)`(int pedType, Hash modelHash, float x, float y, float z, float heading, BOOL isNetwork, BOOL bScriptHostPed)` → `Entity` | S | Server RPC (owned by a nearby client). |
| [`DeletePed`](https://docs.fivem.net/natives/?_0x9614299DCB53E54B)`(Ped ped (in/out))` → `Ped ped` | C |  |
| [`SetPedRandomComponentVariation`](https://docs.fivem.net/natives/?_0xC8A9481A01E63C28)`(Ped ped, int p1)` | C |  |
| [`SetBlockingOfNonTemporaryEvents`](https://docs.fivem.net/natives/?_0x9F8AA94D6D97DBF4)`(Ped ped, BOOL toggle)` | C | Ped ignores events (shots, threats) — essential for shop/job NPCs. |
| [`SetPedFleeAttributes`](https://docs.fivem.net/natives/?_0x70A2D1137C8ED7C9)`(Ped ped, int attributeFlags, BOOL enable)` | C |  |
| [`SetPedCombatAttributes`](https://docs.fivem.net/natives/?_0x9F7794730795E019)`(Ped ped, int attributeIndex, BOOL enabled)` | C |  |
| [`SetPedCombatAbility`](https://docs.fivem.net/natives/?_0xC7622C0D36B2FDA8)`(Ped ped, int p1)` | C |  |
| [`SetPedAccuracy`](https://docs.fivem.net/natives/?_0x7AEFB85C1D49DEB6)`(Ped ped, int accuracy)` | C |  |
| [`SetPedKeepTask`](https://docs.fivem.net/natives/?_0x971D38760FBC02EF)`(Ped ped, BOOL toggle)` | C |  |
| [`SetPedCanBeTargetted`](https://docs.fivem.net/natives/?_0x63F58F7C80513AAD)`(Ped ped, BOOL toggle)` | C |  |
| [`SetPedSeeingRange`](https://docs.fivem.net/natives/?_0xF29CF591C4BF6CEE)`(Ped ped, float value)` | C |  |
| [`SetPedHearingRange`](https://docs.fivem.net/natives/?_0x33A8F7F7D5F7F33C)`(Ped ped, float value)` | C |  |
| [`ClearPedTasks`](https://docs.fivem.net/natives/?_0xE1EF3C1216AFF2CD)`(Ped ped)` | C | Smooth stop. |
| [`ClearPedTasksImmediately`](https://docs.fivem.net/natives/?_0xAAA34F8A7CB32098)`(Ped ped)` | C | Instant (also kicks out of vehicles). |
| [`ClearPedSecondaryTask`](https://docs.fivem.net/natives/?_0x176CECF6F920D707)`(Ped ped)` | C | Stops upper-body anims. |
| [`TaskGoToCoordAnyMeans`](https://docs.fivem.net/natives/?_0x5BC448CB78FA3E88)`(Ped ped, float x, float y, float z, float fMoveBlendRatio, Vehicle vehicle, BOOL bUseLongRangeVehiclePathing, int drivingFlags, float fMaxRangeToShootTargets)` | C |  |
| [`TaskGoStraightToCoord`](https://docs.fivem.net/natives/?_0xD76B57B44F1E6F8B)`(Ped ped, float x, float y, float z, float speed, int timeout, float targetHeading, float distanceToSlide)` | C |  |
| [`TaskFollowNavMeshToCoord`](https://docs.fivem.net/natives/?_0x15D3A79D4E44B913)`(Ped ped, float x, float y, float z, float moveBlendRatio, int time, float radius, int flags, float finalHeading)` | C |  |
| [`TaskWanderStandard`](https://docs.fivem.net/natives/?_0xBB9CE077274F6A1B)`(Ped ped, float p1, int p2)` | C |  |
| [`TaskWanderInArea`](https://docs.fivem.net/natives/?_0xE054346CA3A0F315)`(Ped ped, float x, float y, float z, float radius, int minimalLength, float timeBetweenWalks)` | C |  |
| [`TaskStandStill`](https://docs.fivem.net/natives/?_0x919BE13EED931959)`(Ped ped, int time)` | C |  |
| [`TaskTurnPedToFaceEntity`](https://docs.fivem.net/natives/?_0x5AD23D40115353AC)`(Ped ped, Entity entity, int duration)` | C |  |
| [`TaskTurnPedToFaceCoord`](https://docs.fivem.net/natives/?_0x1DDA930A0AC38571)`(Ped ped, float x, float y, float z, int duration)` | C |  |
| [`TaskLookAtEntity`](https://docs.fivem.net/natives/?_0x69F4BE8C8CC4796C)`(Ped ped, Entity lookAt, int duration, int unknown1, int unknown2)` | C |  |
| [`TaskHandsUp`](https://docs.fivem.net/natives/?_0xF2EAB31979A7F910)`(Ped ped, int duration, Ped facingPed, int p3, BOOL p4)` | C |  |
| [`TaskCombatPed`](https://docs.fivem.net/natives/?_0xF166E48407BAC484)`(Ped ped, Ped targetPed, int p2, int p3)` | C |  |
| [`TaskShootAtEntity`](https://docs.fivem.net/natives/?_0x08DA95E8298AE772)`(Entity entity, Entity target, int duration, Hash firingPattern)` | C |  |
| [`TaskSmartFleePed`](https://docs.fivem.net/natives/?_0x22B0D0E37CCB840D)`(Ped ped, Ped fleeTarget, float distance, Any fleeTime, BOOL p4, BOOL p5)` | C |  |
| [`TaskReactAndFleePed`](https://docs.fivem.net/natives/?_0x72C896464915D1B1)`(Ped ped, Ped fleeTarget)` | C |  |
| [`TaskEnterVehicle`](https://docs.fivem.net/natives/?_0xC20E50AA46D09CA8)`(Ped ped, Vehicle vehicle, int timeout, int seatIndex, float speed, int flag, Any p6)` | C | seat -1 driver; speed 1.0 walk, 2.0 run. |
| [`TaskLeaveVehicle`](https://docs.fivem.net/natives/?_0xD3DBCE61A490BE02)`(Ped ped, Vehicle vehicle, int flags)` | C | flags: 0 normal, 16 teleport out, 64 fast, 256 leave door open, 4160 jump out. |
| [`TaskVehicleDriveToCoord`](https://docs.fivem.net/natives/?_0xE2A2AA2F659D77A7)`(Ped ped, Vehicle vehicle, float x, float y, float z, float speed, Any p6, Hash vehicleModel, int drivingMode, float stopRange, float p10)` | C |  |
| [`TaskVehicleDriveToCoordLongrange`](https://docs.fivem.net/natives/?_0x158BB33F920D360C)`(Ped ped, Vehicle vehicle, float x, float y, float z, float speed, int drivingStyle, float stopRange)` | C | Uses the road network; drivingStyle is a flag set (DurtyFree `drivingStyleFlagValues.json`). |
| [`TaskVehicleDriveWander`](https://docs.fivem.net/natives/?_0x480142959D337D00)`(Ped ped, Vehicle vehicle, float speed, int drivingStyle)` | C |  |
| [`TaskVehicleTempAction`](https://docs.fivem.net/natives/?_0xC429DCEEB339E129)`(Ped driver, Vehicle vehicle, int action, int time)` | C |  |
| [`OpenSequenceTask`](https://docs.fivem.net/natives/?_0xE8854A4326B9E12B)`(int taskSequenceId (in/out))` → `int taskSequenceId` | C | Sequence: Open → Task…(0, …) → Close → TaskPerformSequence → ClearSequenceTask. |
| [`TaskPerformSequence`](https://docs.fivem.net/natives/?_0x5ABA3986D90D8A3B)`(Ped ped, int taskSequenceId)` | C |  |
| [`CloseSequenceTask`](https://docs.fivem.net/natives/?_0x39E72BC99E6360CB)`(int taskSequenceId)` | C |  |
| [`ClearSequenceTask`](https://docs.fivem.net/natives/?_0x3841422E9C488D8C)`(int taskSequenceId (in/out))` → `int taskSequenceId` | C |  |
| [`GetScriptTaskStatus`](https://docs.fivem.net/natives/?_0x77F1BEB8863288D5)`(Ped ped, Hash taskHash)` → `int` | C | 7 = task not running (hash of the TASK_ name). |

## 10. Animations, clipsets and scenarios

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`RequestAnimDict`](https://docs.fivem.net/natives/?_0xD3BD40951412FEF6)`(char* animDict)` | C | Then poll `HasAnimDictLoaded` (or `lib.requestAnimDict`). |
| [`HasAnimDictLoaded`](https://docs.fivem.net/natives/?_0xD031A9162D01088C)`(char* animDict)` → `BOOL` | C |  |
| [`RemoveAnimDict`](https://docs.fivem.net/natives/?_0xF66A602F829E2A06)`(char* animDict)` | C | Release when done. |
| [`TaskPlayAnim`](https://docs.fivem.net/natives/?_0xEA47FE3719165B94)`(Ped ped, char* animDictionary, char* animationName, float blendInSpeed, float blendOutSpeed, int duration, int flag, float playbackRate, BOOL lockX, BOOL lockY, BOOL lockZ)` | C | flag bits: 1 loop, 2 hold last frame, 16 upper body only, 32 player keeps control (secondary). `duration -1` = full clip. |
| [`TaskPlayAnimAdvanced`](https://docs.fivem.net/natives/?_0x83CDB10EA29B370B)`(Ped ped, char* animDictionary, char* animationName, float posX, float posY, float posZ, float rotX, float rotY, float rotZ, float blendInSpeed, float blendOutSpeed, int duration, Any flag, float animTime, Any p14, Any p15)` | C | Plays at a position/rotation. |
| [`StopAnimTask`](https://docs.fivem.net/natives/?_0x97FF36A1D40EA00A)`(Ped ped, char* animDictionary, char* animationName, float animExitSpeed)` | C |  |
| [`IsEntityPlayingAnim`](https://docs.fivem.net/natives/?_0x1F0B79228E461EC9)`(Entity entity, char* animDict, char* animName, int taskFlag)` → `BOOL` | C |  |
| [`GetEntityAnimCurrentTime`](https://docs.fivem.net/natives/?_0x346D81500D088F42)`(Entity entity, char* animDict, char* animName)` → `float` | C |  |
| [`SetEntityAnimCurrentTime`](https://docs.fivem.net/natives/?_0x4487C259F0F70977)`(Entity entity, char* animDictionary, char* animName, float time)` | C |  |
| [`PlayEntityAnim`](https://docs.fivem.net/natives/?_0x7FB218262B810701)`(Entity entity, char* animName, char* animDict, float fBlendDelta, BOOL bLoop, BOOL bHoldLastFrame, BOOL bDriveToPose, float fStartPhase, int iFlags)` → `BOOL` | C | Objects/vehicles. |
| [`RequestAnimSet`](https://docs.fivem.net/natives/?_0x6EA47DAE7FAD0EED)`(char* animSet)` | C | Movement clipsets (walk styles): request then `SetPedMovementClipset`. |
| [`HasAnimSetLoaded`](https://docs.fivem.net/natives/?_0xC4EA073D86FB29B0)`(char* animSet)` → `BOOL` | C |  |
| [`SetPedMovementClipset`](https://docs.fivem.net/natives/?_0xAF8A94EDE7712BEF)`(Ped ped, char* clipSet, float transitionSpeed)` | C |  |
| [`ResetPedMovementClipset`](https://docs.fivem.net/natives/?_0xAA74EC0CB0AAEA2C)`(Ped ped, float transitionSpeed)` | C |  |
| [`SetPedWeaponMovementClipset`](https://docs.fivem.net/natives/?_0x2622E35B77D3ACA2)`(Ped ped, char* clipSet)` | C |  |
| [`RequestClipSet`](https://docs.fivem.net/natives/?_0xD2A71E1A77418A49)`(char* clipSet)` | C |  |
| [`HasClipSetLoaded`](https://docs.fivem.net/natives/?_0x318234F4F3738AF3)`(char* clipSet)` → `BOOL` | C |  |
| [`PlayFacialAnim`](https://docs.fivem.net/natives/?_0xE1E65CA8AC9C00ED)`(Ped ped, char* animName, char* animDict)` | C |  |
| [`SetFacialIdleAnimOverride`](https://docs.fivem.net/natives/?_0xFFC24B988B938B38)`(Ped ped, char* animName, char* animDict)` | C |  |
| [`TaskStartScenarioInPlace`](https://docs.fivem.net/natives/?_0x142A02425FF02BD9)`(Ped ped, char* scenarioName, int timeToLeave, BOOL playIntroClip)` | C | Scenario names: see §30. Cancel with `ClearPedTasks`. |
| [`TaskStartScenarioAtPosition`](https://docs.fivem.net/natives/?_0xFA4EFC79F69D4F07)`(Ped ped, char* scenarioName, float x, float y, float z, float heading, int timeToLeave, BOOL playIntro, BOOL warp)` | C |  |
| [`IsPedUsingAnyScenario`](https://docs.fivem.net/natives/?_0x57AB4A3080F85143)`(Ped ped)` → `BOOL` | C |  |
| [`IsPedActiveInScenario`](https://docs.fivem.net/natives/?_0xAA135F9482C82CC3)`(Ped ped)` → `BOOL` | C |  |
| [`NetworkCreateSynchronisedScene`](https://docs.fivem.net/natives/?_0x7CD6BC4C2BBDD526)`(float x, float y, float z, float xRot, float yRot, float zRot, int rotationOrder, BOOL holdLastFrame, BOOL looped, float phaseToStopScene, float phaseToStartScene, float animSpeed)` → `int` | C | Networked synced scenes (e.g. ATM/door anims). |
| [`NetworkAddPedToSynchronisedScene`](https://docs.fivem.net/natives/?_0x742A637471BCECD9)`(Ped ped, int netScene, char* animDict, char* animClip, float blendInSpeed, float blendOutSpeed, int syncedSceneFlags, int ragdollFlags, float moverBlendInDelta, int ikFlags)` | C |  |
| [`NetworkAddEntityToSynchronisedScene`](https://docs.fivem.net/natives/?_0xF2404D68CBC855FA)`(Entity entity, int netScene, char* animDict, char* animName, float blendIn, float blendOut, int flag)` | C |  |
| [`NetworkStartSynchronisedScene`](https://docs.fivem.net/natives/?_0x9A1B3FCDB36C8697)`(int netScene)` | C |  |
| [`NetworkStopSynchronisedScene`](https://docs.fivem.net/natives/?_0xC254481A4574CB2F)`(int netScene)` | C |  |
| [`CreateSynchronizedScene`](https://docs.fivem.net/natives/?_0x8C18E0F9080ADD73)`(float x, float y, float z, float roll, float pitch, float yaw, int p6)` → `int` | C | Local synced scene. |

## 11. Props and objects

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`CreateObject`](https://docs.fivem.net/natives/?_0x509D5878EB39E842)`(Hash modelHash, float x, float y, float z, BOOL isNetwork, BOOL netMissionEntity, BOOL doorFlag)` → `Object` | C | Model must be loaded. `isNetwork=false` for purely local props. |
| [`CreateObjectNoOffset`](https://docs.fivem.net/natives/?_0x9A294B2138ABB884)`(Hash modelHash, float x, float y, float z, BOOL isNetwork, BOOL netMissionEntity, BOOL doorFlag)` → `Object` | C | Places exactly at the coords (no bounding-box offset). |
| [`CreateObject`](https://docs.fivem.net/natives/?_0x2F7AA05C)`(Hash modelHash, float x, float y, float z, BOOL isNetwork, BOOL netMissionEntity, BOOL doorFlag)` → `Entity` | S | Server RPC. |
| [`CreateObjectNoOffset`](https://docs.fivem.net/natives/?_0x58040420)`(Hash modelHash, float x, float y, float z, BOOL isNetwork, BOOL netMissionEntity, BOOL doorFlag)` → `Entity` | S |  |
| [`DeleteObject`](https://docs.fivem.net/natives/?_0x539E0AE3E6634B9F)`(Object object (in/out))` → `Object object` | C | Client; needs control. Prefer `DeleteEntity`. |
| [`GetClosestObjectOfType`](https://docs.fivem.net/natives/?_0xE143FA2249364369)`(float x, float y, float z, float radius, Hash modelHash, BOOL isMission, BOOL p6, BOOL p7)` → `Object` | C | Find a map/world prop by model near coords. |
| [`DoesObjectOfTypeExistAtCoords`](https://docs.fivem.net/natives/?_0xBFA48E2FF417213F)`(float x, float y, float z, float radius, Hash hash, BOOL p5)` → `BOOL` | C |  |
| [`PlaceObjectOnGroundProperly`](https://docs.fivem.net/natives/?_0x58A850EAEE20FAA3)`(Object object)` → `BOOL` | C |  |
| [`SetEntityLodDist`](https://docs.fivem.net/natives/?_0x5927F96A78577363)`(Entity entity, int value)` | C |  |
| [`CreateModelHide`](https://docs.fivem.net/natives/?_0x8A97BCA30A0CE478)`(float x, float y, float z, float radius, Hash model, BOOL surviveMapReload)` | C | Hide a map prop at coords. |
| [`RemoveModelHide`](https://docs.fivem.net/natives/?_0xD9E3006FB3CBD765)`(float x, float y, float z, float radius, Hash model, BOOL lazy)` | C |  |
| [`CreateModelSwap`](https://docs.fivem.net/natives/?_0x92C47782FDA8B2A3)`(float x, float y, float z, float radius, Hash originalModel, Hash newModel, BOOL bSurviveMapReload)` | C |  |

## 12. Streaming (models, dicts, assets)

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GetHashKey`](https://docs.fivem.net/natives/?_0xD24D37CC275948CC)`(char* string)` → `Hash` | C | Prefer backtick literals (`` `prop_bench_01a` ``) — compile-time hash. |
| [`IsModelInCdimage`](https://docs.fivem.net/natives/?_0x35B9E0803292B641)`(Hash model)` → `BOOL` | C | Model exists in the game/streamed files. Check before requesting. |
| [`IsModelValid`](https://docs.fivem.net/natives/?_0xC0296A2EDF545E92)`(Hash model)` → `BOOL` | C |  |
| [`RequestModel`](https://docs.fivem.net/natives/?_0x963D27A58DF860AC)`(Hash model)` | C | Poll `HasModelLoaded` with `Wait(0)`; ox_lib: `lib.requestModel(model, timeout)`. |
| [`HasModelLoaded`](https://docs.fivem.net/natives/?_0x98A4EB5D89A0C952)`(Hash model)` → `BOOL` | C |  |
| [`SetModelAsNoLongerNeeded`](https://docs.fivem.net/natives/?_0xE532F5D78798DAAB)`(Hash model)` | C | **Always release** after creating the entity. |
| [`RequestStreamedTextureDict`](https://docs.fivem.net/natives/?_0xDFA2EF8E04127DD5)`(char* textureDict, BOOL p1)` | C | For `DrawSprite` / blip textures. |
| [`HasStreamedTextureDictLoaded`](https://docs.fivem.net/natives/?_0x0145F696AAAAD2E4)`(char* textureDict)` → `BOOL` | C |  |
| [`SetStreamedTextureDictAsNoLongerNeeded`](https://docs.fivem.net/natives/?_0xBE2CACCF5A8AA805)`(char* textureDict)` | C |  |
| [`RequestNamedPtfxAsset`](https://docs.fivem.net/natives/?_0xB80D8756B4668AB6)`(char* fxName)` | C |  |
| [`HasNamedPtfxAssetLoaded`](https://docs.fivem.net/natives/?_0x8702416E512EC454)`(char* fxName)` → `BOOL` | C |  |
| [`RemoveNamedPtfxAsset`](https://docs.fivem.net/natives/?_0x5F61EBBE1A00F96D)`(char* fxName)` | C |  |
| [`RequestWeaponAsset`](https://docs.fivem.net/natives/?_0x5443438F033E29C3)`(Hash weaponHash, int p1, int p2)` | C |  |
| [`HasWeaponAssetLoaded`](https://docs.fivem.net/natives/?_0x36E353271F0E90EE)`(Hash weaponHash)` → `BOOL` | C |  |
| [`RequestScriptAudioBank`](https://docs.fivem.net/natives/?_0x2F844A8B08D76685)`(char* bankName, BOOL bOverNetwork)` → `BOOL` | C |  |
| [`RequestCollisionAtCoord`](https://docs.fivem.net/natives/?_0x07503F7948F491A7)`(float x, float y, float z)` | C | After teleporting far: request collision then wait for `HasCollisionLoadedAroundEntity`. |
| [`HasCollisionLoadedAroundEntity`](https://docs.fivem.net/natives/?_0xE9676F61BC0B3321)`(Entity entity)` → `BOOL` | C |  |
| [`NewLoadSceneStartSphere`](https://docs.fivem.net/natives/?_0xACCFB4ACF53551B0)`(float x, float y, float z, float radius, Any p4)` → `BOOL` | C | Preload a whole area (cutscene/teleport). |
| [`NewLoadSceneStop`](https://docs.fivem.net/natives/?_0xC197616D221FF4A4)`()` | C |  |

## 13. Camera and screen effects

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`CreateCam`](https://docs.fivem.net/natives/?_0xC3981DCE61D9E13F)`(char* camName, BOOL active)` → `Cam` | C | `'DEFAULT_SCRIPTED_CAMERA'`. |
| [`CreateCamWithParams`](https://docs.fivem.net/natives/?_0xB51194800B257161)`(char* camName, float posX, float posY, float posZ, float rotX, float rotY, float rotZ, float fov, BOOL active, int rotationOrder)` → `Cam` | C |  |
| [`SetCamCoord`](https://docs.fivem.net/natives/?_0x4D41783FB745E42E)`(Cam cam, float posX, float posY, float posZ)` | C |  |
| [`SetCamRot`](https://docs.fivem.net/natives/?_0x85973643155D0B07)`(Cam cam, float rotX, float rotY, float rotZ, int rotationOrder)` | C |  |
| [`SetCamFov`](https://docs.fivem.net/natives/?_0xB13C14F66A00D047)`(Cam cam, float fieldOfView)` | C |  |
| [`PointCamAtCoord`](https://docs.fivem.net/natives/?_0xF75497BB865F0803)`(Cam cam, float x, float y, float z)` | C |  |
| [`PointCamAtEntity`](https://docs.fivem.net/natives/?_0x5640BFF86B16E8DC)`(Cam cam, Entity entity, float offsetX, float offsetY, float offsetZ, BOOL p5)` | C |  |
| [`AttachCamToEntity`](https://docs.fivem.net/natives/?_0xFEDB7D269E8C60E3)`(Cam cam, Entity entity, float xOffset, float yOffset, float zOffset, BOOL isRelative)` | C |  |
| [`SetCamActive`](https://docs.fivem.net/natives/?_0x026FB97D0A425F84)`(Cam cam, BOOL active)` | C |  |
| [`SetCamActiveWithInterp`](https://docs.fivem.net/natives/?_0x9FBDA379383A52A4)`(Cam camTo, Cam camFrom, int duration, int easeLocation, int easeRotation)` | C | Smooth transition between two cams. |
| [`RenderScriptCams`](https://docs.fivem.net/natives/?_0x07E5B515DB0636FC)`(BOOL render, BOOL ease, int easeTime, BOOL easeCoordsAnim, BOOL p4)` | C | `RenderScriptCams(false, true, 500, true, true)` to go back to gameplay cam. |
| [`DestroyCam`](https://docs.fivem.net/natives/?_0x865908C81A2C22E9)`(Cam cam, BOOL bScriptHostCam)` | C |  |
| [`DestroyAllCams`](https://docs.fivem.net/natives/?_0x8E5FB15663F79120)`(BOOL bScriptHostCam)` | C |  |
| [`IsCamActive`](https://docs.fivem.net/natives/?_0xDFB2B516207D3534)`(Cam cam)` → `BOOL` | C |  |
| [`ShakeCam`](https://docs.fivem.net/natives/?_0x6A25241C340D3822)`(Cam cam, char* shakeName, float intensity)` | C |  |
| [`GetGameplayCamCoord`](https://docs.fivem.net/natives/?_0x14D6F5678D8F1B37)`()` → `Vector3` | C |  |
| [`GetGameplayCamRot`](https://docs.fivem.net/natives/?_0x837765A25378F0BB)`(int rotationOrder)` → `Vector3` | C |  |
| [`GetFinalRenderedCamCoord`](https://docs.fivem.net/natives/?_0xA200EB1EE790F448)`()` → `Vector3` | C | Works whether a script cam or gameplay cam is active. |
| [`GetFinalRenderedCamRot`](https://docs.fivem.net/natives/?_0x5B4E4C817FCC2DFB)`(int rotationOrder)` → `Vector3` | C |  |
| [`GetGameplayCamRelativeHeading`](https://docs.fivem.net/natives/?_0x743607648ADD4587)`()` → `float` | C |  |
| [`SetGameplayCamRelativeHeading`](https://docs.fivem.net/natives/?_0xB4EC2312F4E5B1F1)`(float heading)` | C |  |
| [`GetFollowPedCamViewMode`](https://docs.fivem.net/natives/?_0x8D4D46230B2C353A)`()` → `int` | C | 4 = first person. |
| [`SetFollowPedCamViewMode`](https://docs.fivem.net/natives/?_0x5A4F9EDF1673F704)`(int viewMode)` | C |  |
| [`ShakeGameplayCam`](https://docs.fivem.net/natives/?_0xFD55E49555E017CF)`(char* shakeName, float intensity)` | C |  |
| [`StopGameplayCamShaking`](https://docs.fivem.net/natives/?_0x0EF93E9F3D08C178)`(BOOL bStopImmediately)` | C |  |
| [`DoScreenFadeOut`](https://docs.fivem.net/natives/?_0x891B5B39AC6302AF)`(int duration)` | C |  |
| [`DoScreenFadeIn`](https://docs.fivem.net/natives/?_0xD4E8E24955024033)`(int duration)` | C |  |
| [`IsScreenFadedOut`](https://docs.fivem.net/natives/?_0xB16FCE9DDC7BA182)`()` → `BOOL` | C |  |

## 14. HUD, text, notifications, help text, scaleforms

Text natives are **command sequences**: `Begin…` → `AddTextComponent…` → `End…`. Drawing natives (`EndTextCommandDisplayText`, `DrawRect`, `DrawSprite`, `DrawScaleformMovie*`, `EndTextCommandDisplayHelp` with `loop`) only show **for one frame** — call every frame (`Wait(0)` loop) while visible.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`AddTextEntry`](https://docs.fivem.net/natives/?_0x32CA01C3)`(char* entryKey, char* entryText)` | C | CFX: register a GXT label (`'MY_LABEL'`, `'Press ~INPUT_CONTEXT~ to open'`). |
| [`GetFilenameForAudioConversation`](https://docs.fivem.net/natives/?_0x7B5280EBA9840C72)`(char* labelName)` → `char*` | C | Better known as `GetLabelText` (alias): label key → localized text. |
| [`BeginTextCommandDisplayText`](https://docs.fivem.net/natives/?_0x25FBB336DF1804CB)`(char* text)` | C | `'STRING'` then add components. |
| [`AddTextComponentSubstringPlayerName`](https://docs.fivem.net/natives/?_0x6C188BE134E074AA)`(char* text)` | C | Adds a string component (max 99 chars per component). |
| [`AddTextComponentInteger`](https://docs.fivem.net/natives/?_0x03B504CF259931BC)`(int value)` | C |  |
| [`EndTextCommandDisplayText`](https://docs.fivem.net/natives/?_0xCD015E5BB0D96A57)`(float x, float y)` | C | **Per frame.** Screen coords 0.0–1.0. |
| [`SetTextFont`](https://docs.fivem.net/natives/?_0x66E0276CC5F6B9DA)`(int fontType)` | C | 0 chalet, 4 chalet condensed, 7 pricedown. |
| [`SetTextScale`](https://docs.fivem.net/natives/?_0x07C837F9A01C34C9)`(float scale, float size)` | C |  |
| [`SetTextColour`](https://docs.fivem.net/natives/?_0xBE6B23FFA53FB442)`(int red, int green, int blue, int alpha)` | C |  |
| [`SetTextCentre`](https://docs.fivem.net/natives/?_0xC02F4DBFB51D988B)`(BOOL align)` | C |  |
| [`SetTextOutline`](https://docs.fivem.net/natives/?_0x2513DFB0FB8400FE)`()` | C |  |
| [`SetTextDropShadow`](https://docs.fivem.net/natives/?_0x1CA3E9EAC9D93E5E)`()` | C |  |
| [`SetTextWrap`](https://docs.fivem.net/natives/?_0x63145D9C883A1A70)`(float start, float end)` | C |  |
| [`SetDrawOrigin`](https://docs.fivem.net/natives/?_0xAA0008F3BBB8F416)`(float x, float y, float z, Any p3)` | C | 3D → 2D text: set origin, draw at (0,0), then `ClearDrawOrigin`. |
| [`ClearDrawOrigin`](https://docs.fivem.net/natives/?_0xFF0B610F6BE0D7AF)`()` | C |  |
| [`GetScreenCoordFromWorldCoord`](https://docs.fivem.net/natives/?_0x34E82F05DF2974F5)`(float worldX, float worldY, float worldZ)` → `BOOL, float screenX, float screenY` | C | Returns `onScreen, x, y`. |
| [`BeginTextCommandThefeedPost`](https://docs.fivem.net/natives/?_0x202709F4C58A0424)`(char* text)` | C | Notification (feed) start. |
| [`EndTextCommandThefeedPostTicker`](https://docs.fivem.net/natives/?_0x2ED7843F8F801023)`(BOOL isImportant, BOOL showInBrief)` → `int` | C | Simple notification. |
| [`EndTextCommandThefeedPostMessagetext`](https://docs.fivem.net/natives/?_0x1CCD9A37359072CF)`(char* textureDict, char* textureName, BOOL flash, int iconType, char* sender, char* subject)` → `int` | C | Notification with picture (`'CHAR_…'` txd). |
| [`BeginTextCommandDisplayHelp`](https://docs.fivem.net/natives/?_0x8509B634FBE7DA11)`(char* inputType)` | C | Help text (top-left). `'STRING'` or an `AddTextEntry` label. |
| [`EndTextCommandDisplayHelp`](https://docs.fivem.net/natives/?_0x238FFE5C7B0498A6)`(int shape, BOOL loop, BOOL beep, int duration)` | C | `shape -1`; call per frame with `loop=false` or once with `loop=true`. |
| [`BeginTextCommandPrint`](https://docs.fivem.net/natives/?_0xB87A37EEB7FAA67D)`(char* GxtEntry)` | C | Subtitle (bottom centre). |
| [`EndTextCommandPrint`](https://docs.fivem.net/natives/?_0x9D77056A530643F6)`(int duration, BOOL drawImmediately)` | C |  |
| [`DisplayOnscreenKeyboard`](https://docs.fivem.net/natives/?_0x00DC833F2568DBF6)`(int keyboardType, char* windowTitle, char* description, char* defaultText, char* defaultConcat1, char* defaultConcat2, char* defaultConcat3, int maxInputLength)` | C | Native text input (prefer `lib.inputDialog`). |
| [`UpdateOnscreenKeyboard`](https://docs.fivem.net/natives/?_0x0CF2B696BBF945AE)`()` → `int` | C | -1 invalid, 0 pending, 1 success, 2 cancelled, 3 failed. |
| [`GetOnscreenKeyboardResult`](https://docs.fivem.net/natives/?_0x8362B09B91893647)`()` → `char*` | C |  |
| [`DrawRect`](https://docs.fivem.net/natives/?_0x3A618A217E5154F0)`(float x, float y, float width, float height, int r, int g, int b, int a)` | C | **Per frame.** |
| [`DrawSprite`](https://docs.fivem.net/natives/?_0xE7FFAE5EBF23D890)`(char* textureDict, char* textureName, float screenX, float screenY, float width, float height, float heading, int red, int green, int blue, int alpha)` | C | **Per frame.** Texture dict must be loaded. |
| [`HideHudAndRadarThisFrame`](https://docs.fivem.net/natives/?_0x719FF505F097FD20)`()` | C | **Per frame.** |
| [`HideHudComponentThisFrame`](https://docs.fivem.net/natives/?_0x6806C51AD12B83B8)`(int id)` | C | **Per frame.** Component ids: 1 wanted, 2 weapon icon, 3 cash, 6 vehicle name, 7 area name, 8 vehicle class, 9 street name, 14 reticle, 19 weapon wheel. |
| [`DisplayRadar`](https://docs.fivem.net/natives/?_0xA0EBB943C300E693)`(BOOL toggle)` | C |  |
| [`IsRadarHidden`](https://docs.fivem.net/natives/?_0x157F93B036700462)`()` → `BOOL` | C |  |
| [`DisplayHud`](https://docs.fivem.net/natives/?_0xA6294919E56FF02A)`(BOOL toggle)` | C |  |
| [`SetBigmapActive`](https://docs.fivem.net/natives/?_0x231C8F89D0539D8F)`(BOOL toggleBigMap, BOOL showFullMap)` | C |  |
| [`IsPauseMenuActive`](https://docs.fivem.net/natives/?_0xB0034A223497FFCB)`()` → `BOOL` | C |  |
| [`GetActualScreenResolution`](https://docs.fivem.net/natives/?_0x873C9F3104101DD3)`()` → `int x, int y` | C | Alias `GetActiveScreenResolution`. |
| [`GetAspectRatio`](https://docs.fivem.net/natives/?_0xF1307EF624A80D87)`(BOOL physicalAspect)` → `float` | C |  |
| [`RequestScaleformMovie`](https://docs.fivem.net/natives/?_0x11FE353CF9733E6F)`(char* scaleformName)` → `int` | C | Poll `HasScaleformMovieLoaded`. |
| [`HasScaleformMovieLoaded`](https://docs.fivem.net/natives/?_0x85F01B8D5B90570E)`(int scaleformHandle)` → `BOOL` | C |  |
| [`BeginScaleformMovieMethod`](https://docs.fivem.net/natives/?_0xF6E48914C7A8694E)`(int scaleform, char* methodName)` → `BOOL` | C | Then `ScaleformMovieMethodAddParam*` and `EndScaleformMovieMethod`. |
| [`ScaleformMovieMethodAddParamInt`](https://docs.fivem.net/natives/?_0xC3D0841A0CC546A6)`(int value)` | C |  |
| [`ScaleformMovieMethodAddParamFloat`](https://docs.fivem.net/natives/?_0xD69736AAE04DB51A)`(float value)` | C |  |
| [`ScaleformMovieMethodAddParamBool`](https://docs.fivem.net/natives/?_0xC58424BA936EB458)`(BOOL value)` | C |  |
| [`ScaleformMovieMethodAddParamTextureNameString`](https://docs.fivem.net/natives/?_0xBA7148484BD90365)`(char* string)` | C | String parameter. |
| [`ScaleformMovieMethodAddParamPlayerNameString`](https://docs.fivem.net/natives/?_0xE83A3E3557A56640)`(char* string)` | C |  |
| [`EndScaleformMovieMethod`](https://docs.fivem.net/natives/?_0xC6796A8FFA375E53)`()` | C |  |
| [`DrawScaleformMovieFullscreen`](https://docs.fivem.net/natives/?_0x0DF606929C105BE1)`(int scaleform, int red, int green, int blue, int alpha, int unk)` | C | **Per frame.** |
| [`DrawScaleformMovie`](https://docs.fivem.net/natives/?_0x54972ADAF0294A93)`(int scaleformHandle, float x, float y, float width, float height, int red, int green, int blue, int alpha, int unk)` | C | **Per frame.** |
| [`SetScaleformMovieAsNoLongerNeeded`](https://docs.fivem.net/natives/?_0x1D132D614DD86811)`(int scaleformHandle (in/out))` → `int scaleformHandle` | C |  |

## 15. Blips and waypoints

Blips are **client-side and local**; create them on each client (e.g. on resource start / state change). Sprite and colour IDs: §30.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`AddBlipForCoord`](https://docs.fivem.net/natives/?_0x5A039BB0BCA604B6)`(float x, float y, float z)` → `Blip` | C |  |
| [`AddBlipForEntity`](https://docs.fivem.net/natives/?_0x5CDE92C702A8FCE7)`(Entity entity)` → `Blip` | C | Entity must exist locally; for far players use coords from the server. |
| [`AddBlipForRadius`](https://docs.fivem.net/natives/?_0x46818D79B1F7499A)`(float posX, float posY, float posZ, float radius)` → `Blip` | C | Radius blips ignore `SetBlipSprite`; set alpha. |
| [`AddBlipForArea`](https://docs.fivem.net/natives/?_0xCE5D0E5E315DB238)`(float x, float y, float z, float width, float height)` → `Blip` | C | Open bug citizenfx/fivem#3973 (2026-05): `SetBlipAsShortRange` is ignored for area blips (stay on the minimap at any distance); create/remove them by player distance instead. |
| [`SetBlipSprite`](https://docs.fivem.net/natives/?_0xDF735600A4696DAF)`(Blip blip, int spriteId)` | C |  |
| [`SetBlipColour`](https://docs.fivem.net/natives/?_0x03D7FB09E75D6B7E)`(Blip blip, int color)` | C |  |
| [`SetBlipScale`](https://docs.fivem.net/natives/?_0xD38744167B2FA257)`(Blip blip, float scale)` | C |  |
| [`SetBlipDisplay`](https://docs.fivem.net/natives/?_0x9029B2F3DA924928)`(Blip blip, int displayId)` | C | 2 = map + minimap, 3/4 = main map only, 5 = minimap only, 8 = both but not selectable. |
| [`SetBlipAsShortRange`](https://docs.fivem.net/natives/?_0xBE8BE4FE60E27B72)`(Blip blip, BOOL toggle)` | C | Only shows on minimap when near. |
| [`SetBlipCategory`](https://docs.fivem.net/natives/?_0x234CDD44D996FD9A)`(Blip blip, int index)` | C |  |
| [`SetBlipAlpha`](https://docs.fivem.net/natives/?_0x45FF974EEE1C8734)`(Blip blip, int alpha)` | C |  |
| [`SetBlipFlashes`](https://docs.fivem.net/natives/?_0xB14552383D39CE3E)`(Blip blip, BOOL toggle)` | C |  |
| [`SetBlipRoute`](https://docs.fivem.net/natives/?_0x4F7D8A9BFB0B43E9)`(Blip blip, BOOL enabled)` | C | GPS route to the blip. |
| [`SetBlipRouteColour`](https://docs.fivem.net/natives/?_0x837155CD2F63DA09)`(Blip blip, int colour)` | C |  |
| [`SetBlipCoords`](https://docs.fivem.net/natives/?_0xAE2AF67E9D9AF65D)`(Blip blip, float posX, float posY, float posZ)` | C |  |
| [`SetBlipRotation`](https://docs.fivem.net/natives/?_0xF87683CDF73C3F6E)`(Blip blip, int rotation)` | C |  |
| [`SetBlipPriority`](https://docs.fivem.net/natives/?_0xAE9FC9EF6A9FAC79)`(Blip blip, int priority)` | C |  |
| [`ShowHeadingIndicatorOnBlip`](https://docs.fivem.net/natives/?_0x5FBCA48327B914DF)`(Blip blip, BOOL toggle)` | C |  |
| [`BeginTextCommandSetBlipName`](https://docs.fivem.net/natives/?_0xF9113A30DE5C6670)`(char* textLabel)` | C | `'STRING'` → `AddTextComponentSubstringPlayerName(name)` → `EndTextCommandSetBlipName(blip)`. |
| [`EndTextCommandSetBlipName`](https://docs.fivem.net/natives/?_0xBC38B49BCB83BC9B)`(Blip blip)` | C |  |
| [`GetBlipFromEntity`](https://docs.fivem.net/natives/?_0xBC8DBDCA2436F7E8)`(Entity entity)` → `Blip` | C |  |
| [`DoesBlipExist`](https://docs.fivem.net/natives/?_0xA6DB27D19ECBB7DA)`(Blip blip)` → `BOOL` | C |  |
| [`RemoveBlip`](https://docs.fivem.net/natives/?_0x86A652570E5F25DD)`(Blip blip (in/out))` → `Blip blip` | C | In/out handle. |
| [`GetFirstBlipInfoId`](https://docs.fivem.net/natives/?_0x1BEDE233E6CD2A1F)`(int blipSprite)` → `Blip` | C | Waypoint: `GetFirstBlipInfoId(8)`. |
| [`GetBlipInfoIdCoord`](https://docs.fivem.net/natives/?_0xFA7C7F0AADF25D09)`(Blip blip)` → `Vector3` | C | Waypoint coords (z is 0 — use ground lookup). |
| [`GetBlipCoords`](https://docs.fivem.net/natives/?_0x586AFE3FF72D996E)`(Blip blip)` → `Vector3` | C |  |
| [`IsWaypointActive`](https://docs.fivem.net/natives/?_0x1DD1F58F493F1DA5)`()` → `BOOL` | C |  |
| [`SetNewWaypoint`](https://docs.fivem.net/natives/?_0xFE43368D2AA4F2FC)`(float x, float y)` | C |  |

## 16. Markers and 3D drawing

All of these are **per frame** and client-only. Use `lib.points`/distance gating so the per-frame loop only runs near the marker.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`DrawMarker`](https://docs.fivem.net/natives/?_0x28477EC23D892089)`(int type, float posX, float posY, float posZ, float dirX, float dirY, float dirZ, float rotX, float rotY, float rotZ, float scaleX, float scaleY, float scaleZ, int red, int green, int blue, int alpha, BOOL bobUpAndDown, BOOL faceCamera, int rotationOrder, BOOL rotate, char* textureDict, char* textureName, BOOL drawOnEnts)` | C | Types: §30 markers. `rotate`/`faceCamera`/`bobUpAndDown` flags; textureDict/Name `nil` for defaults. |
| [`DrawLine`](https://docs.fivem.net/natives/?_0x6B7256074AE34680)`(float x1, float y1, float z1, float x2, float y2, float z2, int red, int green, int blue, int alpha)` | C |  |
| [`DrawPoly`](https://docs.fivem.net/natives/?_0xAC26716048436851)`(float x1, float y1, float z1, float x2, float y2, float z2, float x3, float y3, float z3, int red, int green, int blue, int alpha)` | C |  |
| [`DrawBox`](https://docs.fivem.net/natives/?_0xD3A9971CADAC7252)`(float x1, float y1, float z1, float x2, float y2, float z2, int red, int green, int blue, int alpha)` | C |  |
| [`DrawLightWithRange`](https://docs.fivem.net/natives/?_0xF2A1B2771A01DBD4)`(float posX, float posY, float posZ, int colorR, int colorG, int colorB, float range, float intensity)` | C |  |
| [`DrawSpotLight`](https://docs.fivem.net/natives/?_0xD0F64B265C8C8B33)`(float posX, float posY, float posZ, float dirX, float dirY, float dirZ, int colorR, int colorG, int colorB, float distance, float brightness, float hardness, float radius, float falloff)` | C |  |

## 17. Controls and input

`padIndex`/`inputGroup` is `0` (PLAYER_CONTROL) for gameplay, `2` (FRONTEND_CONTROL) for menus. For rebindable keys use `RegisterKeyMapping` + `RegisterCommand` instead of polling every frame.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`IsControlJustPressed`](https://docs.fivem.net/natives/?_0x580417101DDB492F)`(int padIndex, int control)` → `BOOL` | C | **Per frame** polling (one-shot). |
| [`IsControlJustReleased`](https://docs.fivem.net/natives/?_0x50F940259D3841E6)`(int padIndex, int control)` → `BOOL` | C | **Per frame.** |
| [`IsControlPressed`](https://docs.fivem.net/natives/?_0xF3A21BCD95725A4A)`(int padIndex, int control)` → `BOOL` | C | **Per frame** (held). |
| [`IsDisabledControlJustPressed`](https://docs.fivem.net/natives/?_0x91AEF906BCA88877)`(int padIndex, int control)` → `BOOL` | C | Use for controls you disabled with `DisableControlAction`. |
| [`IsDisabledControlJustReleased`](https://docs.fivem.net/natives/?_0x305C8DCD79DA8B0F)`(int padIndex, int control)` → `BOOL` | C |  |
| [`IsDisabledControlPressed`](https://docs.fivem.net/natives/?_0xE2587F8CBBD87B1D)`(int padIndex, int control)` → `BOOL` | C |  |
| [`DisableControlAction`](https://docs.fivem.net/natives/?_0xFE99B66D079CF6BC)`(int padIndex, int control, BOOL disable)` | C | **Per frame.** Disable only while needed (e.g. menu open). |
| [`EnableControlAction`](https://docs.fivem.net/natives/?_0x351220255D64C155)`(int padIndex, int control, BOOL enable)` | C |  |
| [`DisableAllControlActions`](https://docs.fivem.net/natives/?_0x5F4B6931816E599B)`(int padIndex)` | C | **Per frame.** |
| [`EnableAllControlActions`](https://docs.fivem.net/natives/?_0xA5FFE9B05F199DE7)`(int padIndex)` | C |  |
| [`GetControlNormal`](https://docs.fivem.net/natives/?_0xEC3C9B8D5327B563)`(int padIndex, int control)` → `float` | C | Axis value 0–1 / -1–1. |
| [`GetDisabledControlNormal`](https://docs.fivem.net/natives/?_0x11E65974A982637C)`(int padIndex, int control)` → `float` | C |  |
| [`SetPlayerControl`](https://docs.fivem.net/natives/?_0x8D32347D6D4C40A2)`(Player player, BOOL bHasControl, int flags)` | C | Freeze/unfreeze player input (cutscenes). |
| [`IsUsingKeyboard`](https://docs.fivem.net/natives/?_0xA571D46727E2B718)`(int padIndex)` → `BOOL` | C | true = keyboard/mouse, false = gamepad. |
| [`GetControlInstructionalButton`](https://docs.fivem.net/natives/?_0x0499D7B09FC9B407)`(int padIndex, int control, BOOL p2)` → `char*` | C | Button label (`~INPUT_…~` string) for instructional scaleforms. |
| [`RegisterKeyMapping`](https://docs.fivem.net/natives/?_0xD7664FD1)`(char* commandString, char* description, char* defaultMapper, char* defaultParameter)` | C | CFX client: rebindable key in Settings → Key Bindings → FiveM; pair with `RegisterCommand('+cmd'/'-cmd')`. |

### Most-used control IDs (padIndex 0, default PC binding — verified against docs.fivem.net/docs/game-references/controls/)

| ID | Name | Key | ID | Name | Key |
|---|---|---|---|---|---|
| 0 | INPUT_NEXT_CAMERA | V | 47 | INPUT_DETONATE | G |
| 1 / 2 | INPUT_LOOK_LR / UD | mouse | 51 | INPUT_CONTEXT | E |
| 14 / 15 | INPUT_WEAPON_WHEEL_NEXT / PREV | scroll down / up | 52 | INPUT_CONTEXT_SECONDARY | Q |
| 19 | INPUT_CHARACTER_WHEEL | Left Alt | 56 / 57 | INPUT_DROP_WEAPON / DROP_AMMO | F9 / F10 |
| 20 | INPUT_MULTIPLAYER_INFO | Z | 71 / 72 | INPUT_VEH_ACCELERATE / BRAKE | W / S |
| 21 | INPUT_SPRINT | Left Shift | 73 | INPUT_VEH_DUCK | X |
| 22 | INPUT_JUMP | Space | 74 | INPUT_VEH_HEADLIGHT | H |
| 23 | INPUT_ENTER | F | 75 | INPUT_VEH_EXIT | F |
| 24 | INPUT_ATTACK | LMB | 76 | INPUT_VEH_HANDBRAKE | Space |
| 25 | INPUT_AIM | RMB | 86 | INPUT_VEH_HORN | E |
| 26 | INPUT_LOOK_BEHIND | C | 140 / 141 / 142 | INPUT_MELEE_ATTACK_LIGHT / HEAVY / ALTERNATE | R / Q / LMB |
| 27 | INPUT_PHONE | Arrow Up / MMB | 157,158,160,164,165 | INPUT_SELECT_WEAPON_* | 1–5 |
| 29 | INPUT_SPECIAL_ABILITY_SECONDARY | B | 166 / 167 / 168 | INPUT_SELECT_CHARACTER_* | F5 / F6 / F7 |
| 30 / 31 | INPUT_MOVE_LR / UD | A-D / W-S | 172–175 | INPUT_CELLPHONE_UP/DOWN/LEFT/RIGHT | arrows |
| 32 / 33 / 34 / 35 | INPUT_MOVE_UP/DOWN/LEFT/RIGHT_ONLY | W / S / A / D | 176 / 177 | INPUT_CELLPHONE_SELECT / CANCEL | Enter / Backspace-Esc-RMB |
| 36 | INPUT_DUCK | Left Ctrl | 178 | INPUT_CELLPHONE_OPTION | Delete |
| 37 | INPUT_SELECT_WEAPON | Tab | 182 | INPUT_CELLPHONE_CAMERA_FOCUS_LOCK | L |
| 38 | INPUT_PICKUP | E | 191 / 194 | INPUT_FRONTEND_RDOWN / RRIGHT | Enter / Backspace |
| 44 | INPUT_COVER | Q | 199 / 200 | INPUT_FRONTEND_PAUSE / PAUSE_ALTERNATE | P / Esc |
| 45 | INPUT_RELOAD | R | 201 / 202 | INPUT_FRONTEND_ACCEPT / CANCEL | Enter / Backspace-Esc |
| 46 | INPUT_TALK | E | 237 / 238 | INPUT_CURSOR_ACCEPT / CANCEL | LMB / RMB |
| 81 / 82 | INPUT_VEH_NEXT/PREV_RADIO | . / , | 241 / 242 | INPUT_CURSOR_SCROLL_UP / DOWN | wheel |
| 106 | INPUT_VEH_MOUSE_CONTROL_OVERRIDE | LMB | 243 | INPUT_ENTER_CHEAT_CODE | ~ |
| 288 / 289 | INPUT_REPLAY_START_STOP_RECORDING (/ SECONDARY) | F1 / F2 | 244 | INPUT_INTERACTION_MENU | M |
| 170 | INPUT_SAVE_REPLAY_CLIP | F3 | 245 / 246 | INPUT_MP_TEXT_CHAT_ALL / TEAM | T / Y |
| 303 | INPUT_REPLAY_SCREENSHOT | U | 249 | INPUT_PUSH_TO_TALK | N |
| 311 | INPUT_REPLAY_SHOWHOTKEY | K | 344 | INPUT_SWITCH_VISOR | F11 |

Several IDs share a key (E = 38, 46, 51, 86) — pick the one whose context matches (on foot vs vehicle). Players can rebind GTA controls, so prefer `RegisterKeyMapping` for custom actions. Key names for `RegisterKeyMapping`: docs game-references/input-mapper-parameter-ids/keyboard.

## 18. Raycasts, ground and street lookup

Shape tests are **asynchronous**: start the test, then poll `GetShapeTestResult` until status ≠ 1 (1 = pending, 2 = done). ox_lib: `lib.raycast.fromCamera` / `lib.raycast.cam`.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`StartShapeTestLosProbe`](https://docs.fivem.net/natives/?_0x7EE9F5D83DD4F90E)`(float x1, float y1, float z1, float x2, float y2, float z2, int traceFlags, Entity entity, int optionFlags)` → `int` | C | traceFlags: 1 world, 2 vehicles, 4 peds, 8 ragdolls, 16 objects, 256 foliage, 511 everything. `entity` = entity to ignore. optionFlags 7 typical. |
| [`StartExpensiveSynchronousShapeTestLosProbe`](https://docs.fivem.net/natives/?_0x377906D8A31E5586)`(float x1, float y1, float z1, float x2, float y2, float z2, int flags, Entity entity, int p8)` → `int` | C | Synchronous (result immediately) — expensive, don't use every frame. |
| [`StartShapeTestCapsule`](https://docs.fivem.net/natives/?_0x28579D1B8F8AAC80)`(float x1, float y1, float z1, float x2, float y2, float z2, float radius, int flags, Entity entity, int p9)` → `int` | C |  |
| [`StartShapeTestBoundingBox`](https://docs.fivem.net/natives/?_0x052837721A854EC7)`(Entity entity, int flags1, int flags2)` → `int` | C |  |
| [`GetShapeTestResult`](https://docs.fivem.net/natives/?_0x3D87450E15D98694)`(int shapeTestHandle)` → `int, BOOL hit, Vector3 endCoords, Vector3 surfaceNormal, Entity entityHit` | C | Returns `status, hit, endCoords, surfaceNormal, entityHit`. |
| [`GetShapeTestResultIncludingMaterial`](https://docs.fivem.net/natives/?_0x65287525D951F6BE)`(int shapeTestHandle)` → `int, BOOL hit, Vector3 endCoords, Vector3 surfaceNormal, Hash materialHash, Entity entityHit` | C |  |
| [`GetGroundZFor_3dCoord`](https://docs.fivem.net/natives/?_0xC906A7DAB05C8D2B)`(float x, float y, float z, BOOL includeWater)` → `BOOL, float groundZ` | C | Only works when collision is loaded around the point. |
| [`GetSafeCoordForPed`](https://docs.fivem.net/natives/?_0xB61C8E878A4199CA)`(float x, float y, float z, BOOL onlyOnPavement, int flags)` → `BOOL, Vector3 outPosition` | C |  |
| [`GetClosestVehicleNode`](https://docs.fivem.net/natives/?_0x240A18690AE96513)`(float x, float y, float z, int nodeFlags, float zMeasureMult, float zTolerance)` → `BOOL, Vector3 outPosition` | C |  |
| [`GetClosestVehicleNodeWithHeading`](https://docs.fivem.net/natives/?_0xFF071FB798B803B0)`(float x, float y, float z, int nodeFlags, float zMeasureMult, int zTolerance)` → `BOOL, Vector3 outPosition, float outHeading` | C |  |
| [`GetStreetNameAtCoord`](https://docs.fivem.net/natives/?_0x2EB41072B4C1E4C0)`(float x, float y, float z)` → `Hash streetName, Hash crossingRoad` | C | Returns street hash + crossing hash. |
| [`GetStreetNameFromHashKey`](https://docs.fivem.net/natives/?_0xD0EF8A959B8A4CB9)`(Hash hash)` → `char*` | C |  |
| [`GetNameOfZone`](https://docs.fivem.net/natives/?_0xCD90657D4C30E1CA)`(float x, float y, float z)` → `char*` | C | Zone code (e.g. `'DOWNT'`); `GetLabelText(code)` for the display name. |
| [`IsPointOnRoad`](https://docs.fivem.net/natives/?_0x125BF4ABFC536B09)`(float x, float y, float z, Vehicle vehicle)` → `BOOL` | C |  |

## 19. World — time, weather, population, IPLs, interiors, doors

Weather/time are **synced by the server** in most setups (e.g. a weather-sync resource); setting them only on one client gets overwritten.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`NetworkOverrideClockTime`](https://docs.fivem.net/natives/?_0xE679E3E06E363892)`(int hours, int minutes, int seconds)` | C | Set client time (h, m, s). |
| [`GetClockHours`](https://docs.fivem.net/natives/?_0x25223CA6B4D20B7F)`()` → `int` | C |  |
| [`GetClockMinutes`](https://docs.fivem.net/natives/?_0x13D2B8ADD79640F2)`()` → `int` | C |  |
| [`PauseClock`](https://docs.fivem.net/natives/?_0x4055E40BD2DBEC1D)`(BOOL toggle)` | C |  |
| [`SetWeatherTypeNowPersist`](https://docs.fivem.net/natives/?_0xED712CA327900C8A)`(char* weatherType)` | C | e.g. `'CLEAR'`, `'EXTRASUNNY'`, `'RAIN'`, `'THUNDER'`, `'XMAS'`. |
| [`SetWeatherTypeOvertimePersist`](https://docs.fivem.net/natives/?_0xFB5045B7C42B75BF)`(char* weatherType, float time)` | C | Smooth transition (seconds). |
| [`SetWeatherTypePersist`](https://docs.fivem.net/natives/?_0x704983DF373B198F)`(char* weatherType)` | C |  |
| [`SetOverrideWeather`](https://docs.fivem.net/natives/?_0xA43D5C6FE51ADBEF)`(char* weatherType)` | C |  |
| [`ClearOverrideWeather`](https://docs.fivem.net/natives/?_0x338D2E3477711050)`()` | C |  |
| [`ClearWeatherTypePersist`](https://docs.fivem.net/natives/?_0xCCC39339BEF76CF5)`()` | C |  |
| [`SetRainLevel`](https://docs.fivem.net/natives/?_0x643E26EA6E024D92)`(float level)` | C |  |
| [`SetWindSpeed`](https://docs.fivem.net/natives/?_0xEE09ECEDBABE47FC)`(float speed)` | C |  |
| [`SetArtificialLightsState`](https://docs.fivem.net/natives/?_0x1268615ACE24D504)`(BOOL state)` | C | Blackout (true = lights off). |
| [`SetPedDensityMultiplierThisFrame`](https://docs.fivem.net/natives/?_0x95E3D6257B166CF2)`(float multiplier)` | C | **Per frame.** 0.0 = no ambient peds. |
| [`SetScenarioPedDensityMultiplierThisFrame`](https://docs.fivem.net/natives/?_0x7A556143A1C03898)`(float interiorMult, float exteriorMult)` | C | **Per frame.** |
| [`SetVehicleDensityMultiplierThisFrame`](https://docs.fivem.net/natives/?_0x245A6883D966D537)`(float multiplier)` | C | **Per frame.** |
| [`SetRandomVehicleDensityMultiplierThisFrame`](https://docs.fivem.net/natives/?_0xB3B3359379FE77D3)`(float multiplier)` | C | **Per frame.** |
| [`SetParkedVehicleDensityMultiplierThisFrame`](https://docs.fivem.net/natives/?_0xEAE6DCC7EEE3DB1D)`(float multiplier)` | C | **Per frame.** |
| [`SetGarbageTrucks`](https://docs.fivem.net/natives/?_0x2AFD795EEAC8D30D)`(BOOL toggle)` | C |  |
| [`SetRandomBoats`](https://docs.fivem.net/natives/?_0x84436EC293B1415F)`(BOOL toggle)` | C |  |
| [`SetCreateRandomCops`](https://docs.fivem.net/natives/?_0x102E68B2024D536D)`(BOOL toggle)` | C |  |
| [`EnableDispatchService`](https://docs.fivem.net/natives/?_0xDC0F817884CDD856)`(int dispatchService, BOOL toggle)` | C | Disable police/EMS/fire dispatch (services 1–15). |
| [`ClearArea`](https://docs.fivem.net/natives/?_0xA56F01F3765B93A0)`(float X, float Y, float Z, float radius, BOOL p4, BOOL ignoreCopCars, BOOL ignoreObjects, BOOL p7)` | C |  |
| [`ClearAreaOfVehicles`](https://docs.fivem.net/natives/?_0x01C7B9B38428AEB6)`(float x, float y, float z, float radius, BOOL p4, BOOL p5, BOOL p6, BOOL p7, BOOL p8)` | C |  |
| [`RequestIpl`](https://docs.fivem.net/natives/?_0x41B4893843BBDB74)`(char* iplName)` | C | Load an IPL (map addon/interior state). Names: DurtyFree `ipls.json`. |
| [`RemoveIpl`](https://docs.fivem.net/natives/?_0xEE6C5AD3ECE0A82D)`(char* iplName)` | C |  |
| [`IsIplActive`](https://docs.fivem.net/natives/?_0x88A741E44A2B3495)`(char* iplName)` → `BOOL` | C |  |
| [`GetInteriorAtCoords`](https://docs.fivem.net/natives/?_0xB0F7F8663821D9C3)`(float x, float y, float z)` → `int` | C |  |
| [`GetInteriorFromEntity`](https://docs.fivem.net/natives/?_0x2107BA504071A6BB)`(Entity entity)` → `int` | C |  |
| [`PinInteriorInMemory`](https://docs.fivem.net/natives/?_0x2CA429C029CCF247)`(int interior)` | C |  |
| [`IsInteriorReady`](https://docs.fivem.net/natives/?_0x6726BDCCC1932F0E)`(int interiorID)` → `BOOL` | C |  |
| [`ActivateInteriorEntitySet`](https://docs.fivem.net/natives/?_0x55E86AF2712B36A1)`(int interior, char* entitySetName)` | C | Then `RefreshInterior`. |
| [`DeactivateInteriorEntitySet`](https://docs.fivem.net/natives/?_0x420BD37289EEE162)`(int interior, char* entitySetName)` | C |  |
| [`IsInteriorEntitySetActive`](https://docs.fivem.net/natives/?_0x35F7DD45E8C0A16D)`(int interior, char* entitySetName)` → `BOOL` | C |  |
| [`RefreshInterior`](https://docs.fivem.net/natives/?_0x41F37C3427C75AE0)`(int interiorID)` | C |  |
| [`AddDoorToSystem`](https://docs.fivem.net/natives/?_0x6F8838D03D1DC226)`(Hash doorHash, Hash modelHash, float x, float y, float z, BOOL p5, BOOL scriptDoor, BOOL isLocal)` | C | Register a map door (doorHash = any unique hash). Door locks: prefer ox_doorlock. |
| [`DoorSystemSetDoorState`](https://docs.fivem.net/natives/?_0x6BAB9442830C7F53)`(Hash doorHash, int state, BOOL requestDoor, BOOL forceUpdate)` | C | 0 unlocked, 1 locked, 4 force-locked-this-frame… |
| [`DoorSystemGetDoorState`](https://docs.fivem.net/natives/?_0x160AA1B32F6139B8)`(Hash doorHash)` → `int` | C |  |
| [`IsDoorRegisteredWithSystem`](https://docs.fivem.net/natives/?_0xC153C43EA202C8C1)`(Hash doorHash)` → `BOOL` | C |  |
| [`RemoveDoorFromSystem`](https://docs.fivem.net/natives/?_0x464D8E1427156FE4)`(Hash doorHash)` | C |  |

## 20. Audio

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`PlaySoundFrontend`](https://docs.fivem.net/natives/?_0x67C540AA08E4A6F5)`(int soundId, char* audioName, char* audioRef, BOOL p3)` | C | soundId -1 for fire-and-forget. Name/set lists: DurtyFree `soundNames.json`. |
| [`PlaySoundFromEntity`](https://docs.fivem.net/natives/?_0xE65F427EB70AB1ED)`(int soundId, char* audioName, Entity entity, char* audioRef, BOOL isNetwork, Any p5)` | C |  |
| [`PlaySoundFromCoord`](https://docs.fivem.net/natives/?_0x8D8686B622B88120)`(int soundId, char* audioName, float x, float y, float z, char* audioRef, BOOL isNetwork, int range, BOOL p8)` | C |  |
| [`GetSoundId`](https://docs.fivem.net/natives/?_0x430386FE9BF80B45)`()` → `int` | C | Reserve an id for sounds you need to stop. |
| [`StopSound`](https://docs.fivem.net/natives/?_0xA3B0C41BA5CC0BB5)`(int soundId)` | C |  |
| [`ReleaseSoundId`](https://docs.fivem.net/natives/?_0x353FC880830B88FA)`(int soundId)` | C | Always release reserved ids. |
| [`RequestScriptAudioBank`](https://docs.fivem.net/natives/?_0x2F844A8B08D76685)`(char* bankName, BOOL bOverNetwork)` → `BOOL` | C |  |
| [`ReleaseNamedScriptAudioBank`](https://docs.fivem.net/natives/?_0x77ED170667F50170)`(char* audioBank)` | C |  |
| [`StartAudioScene`](https://docs.fivem.net/natives/?_0x013A80FC08F6E4F2)`(char* scene)` → `BOOL` | C |  |
| [`StopAudioScene`](https://docs.fivem.net/natives/?_0xDFE8422B3B94E688)`(char* sceneName)` | C |  |
| [`SetAudioFlag`](https://docs.fivem.net/natives/?_0xB9EFD5C25018725A)`(char* flagName, BOOL toggle)` | C | e.g. `'DisableFlightMusic'`, `'PoliceScannerDisabled'`. |
| [`PlayPedAmbientSpeechNative`](https://docs.fivem.net/natives/?_0x8E04FEDD28D42462)`(Ped ped, char* speechName, char* speechParam)` | C |  |
| [`StopCurrentPlayingAmbientSpeech`](https://docs.fivem.net/natives/?_0xB8BEC0CA6F0EDB0F)`(Ped ped)` | C |  |
| [`SetVehRadioStation`](https://docs.fivem.net/natives/?_0x1B9C0099CB942AC6)`(Vehicle vehicle, char* radioStation)` | C | `'OFF'` to switch off. Station names: docs radiostations. |
| [`SetVehicleRadioEnabled`](https://docs.fivem.net/natives/?_0x3B988190C0AA6C0B)`(Vehicle vehicle, BOOL toggle)` | C |  |
| [`SetUserRadioControlEnabled`](https://docs.fivem.net/natives/?_0x19F21E63AE6EAE4E)`(BOOL toggle)` | C |  |
| [`MumbleSetVolumeOverride`](https://docs.fivem.net/natives/?_0x61C309E3)`(Player player, float volume)` | C | CFX client voice (pma-voice handles this normally). |

## 21. Particles, explosions, fire, timecycles

Request + `UseParticleFxAsset` **before every** `StartParticleFx*` call. Effect lists: DurtyFree `particleEffectsCompact.json`.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`UseParticleFxAsset`](https://docs.fivem.net/natives/?_0x6C38AF3693A69A91)`(char* name)` | C |  |
| [`StartParticleFxNonLoopedAtCoord`](https://docs.fivem.net/natives/?_0x25129531F77B9ED3)`(char* effectName, float xPos, float yPos, float zPos, float xRot, float yRot, float zRot, float scale, BOOL xAxis, BOOL yAxis, BOOL zAxis)` → `int` | C | Local one-shot. |
| [`StartParticleFxNonLoopedOnEntity`](https://docs.fivem.net/natives/?_0x0D53A3B8DA0809D2)`(char* effectName, Entity entity, float offsetX, float offsetY, float offsetZ, float rotX, float rotY, float rotZ, float scale, BOOL axisX, BOOL axisY, BOOL axisZ)` → `BOOL` | C |  |
| [`StartNetworkedParticleFxNonLoopedAtCoord`](https://docs.fivem.net/natives/?_0xF56B8137DF10135D)`(char* effectName, float xPos, float yPos, float zPos, float xRot, float yRot, float zRot, float scale, BOOL xAxis, BOOL yAxis, BOOL zAxis)` → `BOOL` | C | Seen by everyone in range. |
| [`StartParticleFxLoopedAtCoord`](https://docs.fivem.net/natives/?_0xE184F4F0DC5910E7)`(char* effectName, float x, float y, float z, float xRot, float yRot, float zRot, float scale, BOOL xAxis, BOOL yAxis, BOOL zAxis, BOOL p11)` → `int` | C | Returns handle → `StopParticleFxLooped`. |
| [`StartParticleFxLoopedOnEntity`](https://docs.fivem.net/natives/?_0x1AE42C1660FD6517)`(char* effectName, Entity entity, float xOffset, float yOffset, float zOffset, float xRot, float yRot, float zRot, float scale, BOOL xAxis, BOOL yAxis, BOOL zAxis)` → `int` | C |  |
| [`StartParticleFxLoopedOnEntityBone`](https://docs.fivem.net/natives/?_0xC6EB449E33977F0B)`(char* effectName, Entity entity, float xOffset, float yOffset, float zOffset, float xRot, float yRot, float zRot, int boneIndex, float scale, BOOL xAxis, BOOL yAxis, BOOL zAxis)` → `int` | C |  |
| [`StartNetworkedParticleFxLoopedOnEntity`](https://docs.fivem.net/natives/?_0x6F60E89A7B64EE1D)`(char* effectName, Entity entity, float xOffset, float yOffset, float zOffset, float xRot, float yRot, float zRot, float scale, BOOL xAxis, BOOL yAxis, BOOL zAxis)` → `int` | C |  |
| [`StopParticleFxLooped`](https://docs.fivem.net/natives/?_0x8F75998877616996)`(int ptfxHandle, BOOL p1)` | C |  |
| [`RemoveParticleFx`](https://docs.fivem.net/natives/?_0xC401503DFE8D53CF)`(int ptfxHandle, BOOL p1)` | C |  |
| [`SetParticleFxLoopedColour`](https://docs.fivem.net/natives/?_0x7F8F65877F88783B)`(int ptfxHandle, float r, float g, float b, BOOL bLocalOnly)` | C |  |
| [`SetParticleFxLoopedAlpha`](https://docs.fivem.net/natives/?_0x726845132380142E)`(int ptfxHandle, float alpha)` | C |  |
| [`SetParticleFxNonLoopedColour`](https://docs.fivem.net/natives/?_0x26143A59EF48B262)`(float r, float g, float b)` | C |  |
| [`AddExplosion`](https://docs.fivem.net/natives/?_0xE3AD2BDBAEE269AC)`(float x, float y, float z, int explosionType, float damageScale, BOOL isAudible, BOOL isInvisible, float cameraShake)` | C | Explosion types: DurtyFree `explosionTypesCompact.json`. Server-side explosions are logged by `explosionEvent`. |
| [`StartScriptFire`](https://docs.fivem.net/natives/?_0x6B83617E04503888)`(float X, float Y, float Z, int maxChildren, BOOL isGasFire)` → `FireId` | C |  |
| [`RemoveScriptFire`](https://docs.fivem.net/natives/?_0x7FF548385680673F)`(FireId fireHandle)` | C |  |
| [`StopFireInRange`](https://docs.fivem.net/natives/?_0x056A8A219B8E829F)`(float x, float y, float z, float radius)` | C |  |
| [`SetTimecycleModifier`](https://docs.fivem.net/natives/?_0x2C933ABF17A1DF41)`(char* modifierName)` | C | Names: DurtyFree `timecycleModifiers.json`. |
| [`SetTimecycleModifierStrength`](https://docs.fivem.net/natives/?_0x82E7FFCD5B2326B3)`(float strength)` | C |  |
| [`ClearTimecycleModifier`](https://docs.fivem.net/natives/?_0x0F07E7745A236711)`()` | C |  |
| [`AnimpostfxPlay`](https://docs.fivem.net/natives/?_0x2206BF9A37B7F724)`(char* effectName, int duration, BOOL looped)` | C | Screen effects (e.g. `'DrugsMichaelAliensFight'`). |
| [`AnimpostfxStop`](https://docs.fivem.net/natives/?_0x068E835A1D0DC0E3)`(char* effectName)` | C |  |
| [`AnimpostfxStopAll`](https://docs.fivem.net/natives/?_0xB4EDDC19532BFB85)`()` | C |  |

## 22. Network IDs and ownership (client)

Handles are **per-client**; send **network IDs** over events and convert back. Only the **owner** can apply most changes (tasks, velocity, health, deletion).

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`NetworkGetNetworkIdFromEntity`](https://docs.fivem.net/natives/?_0xA11700682F3AD45C)`(Entity entity)` → `int` | C |  |
| [`NetworkGetEntityFromNetworkId`](https://docs.fivem.net/natives/?_0xCE4E5D9B0A4FF560)`(int netId)` → `Entity` | C |  |
| [`NetworkDoesNetworkIdExist`](https://docs.fivem.net/natives/?_0x38CE16C96BD11344)`(int netId)` → `BOOL` | C |  |
| [`NetworkDoesEntityExistWithNetworkId`](https://docs.fivem.net/natives/?_0x18A47D074708FD68)`(int netId)` → `BOOL` | C | Check before converting (entity may be out of scope). |
| [`NetworkGetEntityIsNetworked`](https://docs.fivem.net/natives/?_0xC7827959479DCC78)`(Entity entity)` → `BOOL` | C |  |
| [`NetworkHasControlOfEntity`](https://docs.fivem.net/natives/?_0x01BF60A500E28887)`(Entity entity)` → `BOOL` | C |  |
| [`NetworkRequestControlOfEntity`](https://docs.fivem.net/natives/?_0xB69317BF5E782347)`(Entity entity)` → `BOOL` | C | Request, then poll `NetworkHasControlOfEntity` with a timeout. Fails if the server set the entity as non-migratable. |
| [`NetworkRequestControlOfNetworkId`](https://docs.fivem.net/natives/?_0xA670B3662FAFFBD0)`(int netId)` → `BOOL` | C |  |
| [`NetworkGetEntityOwner`](https://docs.fivem.net/natives/?_0x526FEE31)`(Entity entity)` → `int` | C/S | Returns player **index**. |
| [`NetworkGetPlayerIndexFromPed`](https://docs.fivem.net/natives/?_0x6C0E2E0125610278)`(Ped ped)` → `Player` | C |  |
| [`NetToVeh`](https://docs.fivem.net/natives/?_0x367B936610BA360C)`(int netHandle)` → `Vehicle` | C | Typed helpers (also `NetToPed`, `NetToObj`, `VehToNet`, `PedToNet`, `ObjToNet`). |
| [`VehToNet`](https://docs.fivem.net/natives/?_0xB4C94523F023419C)`(Vehicle vehicle)` → `int` | C |  |
| [`SetNetworkIdCanMigrate`](https://docs.fivem.net/natives/?_0x299EEB23175895FC)`(int netId, BOOL toggle)` | C |  |
| [`SetNetworkIdExistsOnAllMachines`](https://docs.fivem.net/natives/?_0xE05E81A888FA63C8)`(int netId, BOOL toggle)` | C |  |
| [`NetworkIsSessionStarted`](https://docs.fivem.net/natives/?_0x9DE624D2FC4B603F)`()` → `BOOL` | C |  |
| [`NetworkIsPlayerTalking`](https://docs.fivem.net/natives/?_0x031E11F3D447647E)`(Player player)` → `BOOL` | C |  |
| [`NetworkSetFriendlyFireOption`](https://docs.fivem.net/natives/?_0xF808475FA571D823)`(BOOL toggle)` | C |  |
| [`SetCanAttackFriendly`](https://docs.fivem.net/natives/?_0xB3B1CB349FF9C75D)`(Ped ped, BOOL toggle, BOOL p2)` | C |  |

## 23. Server CFX — players, identifiers, permissions

`GetPlayers()`, `GetPlayerIdentifiers(src)` and `GetPlayerTokens(src)` are **Lua helpers** built on the natives below (not natives themselves).

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GetNumPlayerIndices`](https://docs.fivem.net/natives/?_0x63D13184)`()` → `int` | S |  |
| [`GetPlayerFromIndex`](https://docs.fivem.net/natives/?_0xC8A9CE08)`(int index)` → `char*` | S |  |
| [`DoesPlayerExist`](https://docs.fivem.net/natives/?_0x12038599)`(char* playerSrc)` → `BOOL` | S |  |
| [`GetPlayerName`](https://docs.fivem.net/natives/?_0x406B4B20)`(char* playerSrc)` → `char*` | S |  |
| [`GetPlayerPed`](https://docs.fivem.net/natives/?_0x6E31E993)`(char* playerSrc)` → `Entity` | S | Ped of a player (OneSync). |
| [`GetPlayerIdentifierByType`](https://docs.fivem.net/natives/?_0xA61C8FC6)`(char* playerSrc, char* identifierType)` → `char*` | S | `'license'` (primary key), `'license2'`, `'discord'`, `'fivem'`, `'steam'`, `'ip'`. Returns e.g. `'license:abc…'` or nil. |
| [`GetNumPlayerIdentifiers`](https://docs.fivem.net/natives/?_0xFF7F66AB)`(char* playerSrc)` → `int` | S |  |
| [`GetPlayerIdentifier`](https://docs.fivem.net/natives/?_0x7302DBCF)`(char* playerSrc, int identiferIndex)` → `char*` | S |  |
| [`GetNumPlayerTokens`](https://docs.fivem.net/natives/?_0x619E4A3D)`(char* playerSrc)` → `int` | S | Hardware tokens (ban evasion checks). |
| [`GetPlayerToken`](https://docs.fivem.net/natives/?_0x54C06897)`(char* playerSrc, int index)` → `char*` | S |  |
| [`GetPlayerEndpoint`](https://docs.fivem.net/natives/?_0xFEE404F9)`(char* playerSrc)` → `char*` | S | IP:port — personal data, don't store/log needlessly. |
| [`GetPlayerPing`](https://docs.fivem.net/natives/?_0xFF1290D4)`(char* playerSrc)` → `int` | S |  |
| [`GetPlayerLastMsg`](https://docs.fivem.net/natives/?_0x427E8E6A)`(char* playerSrc)` → `int` | S | ms since last packet. |
| [`GetPlayerGuid`](https://docs.fivem.net/natives/?_0xE52D9680)`(char* playerSrc)` → `char*` | S |  |
| [`IsPlayerAceAllowed`](https://docs.fivem.net/natives/?_0xDEDAE23D)`(char* playerSrc, char* object)` → `BOOL` | S | ACE permission check (`add_ace group.admin myres.admin allow`). |
| [`IsPrincipalAceAllowed`](https://docs.fivem.net/natives/?_0x37CF52CE)`(char* principal, char* object)` → `BOOL` | C/S |  |
| [`ExecuteCommand`](https://docs.fivem.net/natives/?_0x561C060B)`(char* commandString)` | C/S | Run a console command (e.g. `add_principal`). Never with user input. |
| [`DropPlayer`](https://docs.fivem.net/natives/?_0xBA0613E1)`(char* playerSrc, char* reason)` | S | Kick with reason. |
| [`GetPlayerRoutingBucket`](https://docs.fivem.net/natives/?_0x52441C34)`(char* playerSrc)` → `int` | S |  |
| [`SetPlayerRoutingBucket`](https://docs.fivem.net/natives/?_0x6504EB38)`(char* playerSrc, int bucket)` | S | Instance/dimension per player. |
| [`GetPlayerCameraRotation`](https://docs.fivem.net/natives/?_0x433C765D)`(char* playerSrc)` → `Vector3` | S |  |
| [`IsPlayerUsingSuperJump`](https://docs.fivem.net/natives/?_0xC7D2C20C)`(char* playerSrc)` → `BOOL` | S | Simple server-side anti-cheat signal. |
| [`GetPlayerInvincible`](https://docs.fivem.net/natives/?_0x680C90EE)`(char* playerSrc)` → `BOOL` | S | Server-side god-mode flag (anti-cheat signal). |
| [`GetPlayerWeaponDamageModifier`](https://docs.fivem.net/natives/?_0x2A3D7CDA)`(Player playerId)` → `float` | C/S |  |
| [`CanPlayerStartCommerceSession`](https://docs.fivem.net/natives/?_0x429461C3)`(char* playerSrc)` → `BOOL` | S | Tebex/commerce. |

## 24. Server CFX — entities, routing buckets, OneSync

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GetAllVehicles`](https://docs.fivem.net/natives/?_0x332169F5)`()` → `object` | S | All server-known vehicles (OneSync). |
| [`GetAllPeds`](https://docs.fivem.net/natives/?_0xB8584FEF)`()` → `object` | S |  |
| [`GetAllObjects`](https://docs.fivem.net/natives/?_0x6886C3FE)`()` → `object` | S |  |
| [`DoesEntityExist`](https://docs.fivem.net/natives/?_0x3AC90869)`(Object entity)` → `BOOL` | S |  |
| [`GetEntityModel`](https://docs.fivem.net/natives/?_0xDAFCB3EC)`(Entity entity)` → `Hash` | S |  |
| [`GetEntityType`](https://docs.fivem.net/natives/?_0xB1BD08D)`(Entity entity)` → `int` | S |  |
| [`GetEntityHeading`](https://docs.fivem.net/natives/?_0x972CC383)`(Entity entity)` → `float` | S |  |
| [`SetEntityCoords`](https://docs.fivem.net/natives/?_0xDF70B41B)`(Entity entity, float xPos, float yPos, float zPos, BOOL alive, BOOL deadFlag, BOOL ragdollFlag, BOOL clearArea)` | S |  |
| [`SetEntityHeading`](https://docs.fivem.net/natives/?_0xE0FF064D)`(Entity entity, float heading)` | S |  |
| [`GetEntityVelocity`](https://docs.fivem.net/natives/?_0xC14C9B6B)`(Entity entity)` → `Vector3` | S |  |
| [`FreezeEntityPosition`](https://docs.fivem.net/natives/?_0x65C16D57)`(Entity entity, BOOL toggle)` | S |  |
| [`GetVehiclePedIsIn`](https://docs.fivem.net/natives/?_0xAFE92319)`(Ped ped, BOOL lastVehicle)` → `Vehicle` | S |  |
| [`GetPedInVehicleSeat`](https://docs.fivem.net/natives/?_0x388FDE9A)`(Vehicle vehicle, int seatIndex)` → `Entity` | S |  |
| [`GetVehicleEngineHealth`](https://docs.fivem.net/natives/?_0x8880038A)`(Vehicle vehicle)` → `float` | S |  |
| [`GetVehicleBodyHealth`](https://docs.fivem.net/natives/?_0x2B2FCC28)`(Vehicle vehicle)` → `float` | S |  |
| [`GetEntityPopulationType`](https://docs.fivem.net/natives/?_0xFC30DDFF)`(Entity entity)` → `int` | S | ePopulationType: 7 = mission (script-created); 1–5 = random/ambient (enum link on docs page). |
| [`NetworkGetNetworkIdFromEntity`](https://docs.fivem.net/natives/?_0x9E35DAB6)`(Entity entity)` → `int` | S |  |
| [`NetworkGetEntityFromNetworkId`](https://docs.fivem.net/natives/?_0x5B912C3F)`(int netId)` → `Entity` | S |  |
| [`NetworkGetEntityOwner`](https://docs.fivem.net/natives/?_0x526FEE31)`(Entity entity)` → `int` | C/S | Returns the owner's **server id**. |
| [`NetworkGetFirstEntityOwner`](https://docs.fivem.net/natives/?_0x1E546224)`(Entity entity)` → `int` | S | Who created it — useful in `entityCreating` anti-cheat. |
| [`SetEntityOrphanMode`](https://docs.fivem.net/natives/?_0x489E9162)`(Entity entity, int orphanMode)` | S | 0 delete when not relevant (default), 1 delete when original owner disconnects, 2 keep (server never deletes). |
| [`SetEntityDistanceCullingRadius`](https://docs.fivem.net/natives/?_0xD3A183A3)`(Entity entity, float radius)` | S | **Deprecated per DB** (culling natives have known unfixable issues); avoid in new code. |
| [`SetEntityIgnoreRequestControlFilter`](https://docs.fivem.net/natives/?_0x9F7F8D36)`(Entity entity, bool ignore)` | S |  |
| [`GetEntityRoutingBucket`](https://docs.fivem.net/natives/?_0xED4B0486)`(Entity entity)` → `int` | S |  |
| [`SetEntityRoutingBucket`](https://docs.fivem.net/natives/?_0x635E5289)`(Entity entity, int bucket)` | S |  |
| [`SetRoutingBucketPopulationEnabled`](https://docs.fivem.net/natives/?_0xCE51AC2C)`(int bucketId, BOOL mode)` | S | Ambient peds/traffic per bucket. |
| [`SetRoutingBucketEntityLockdownMode`](https://docs.fivem.net/natives/?_0xA0F2201F)`(int bucketId, char* mode)` | S | `'strict'` / `'relaxed'` / `'inactive'` — strict blocks client entity creation. |
| [`CancelEvent`](https://docs.fivem.net/natives/?_0xFA29D35D)`()` | C/S | Cancel the current event (e.g. inside `entityCreating`). |

## 25. State bags (server and client)

Prefer the Lua wrappers `Entity(ent).state`, `Player(src).state`, `GlobalState`, `LocalPlayer.state`. Clients can only set **their own** player/owned-entity bags and only replicated if the server allows it; validate in a change handler on the server.

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`AddStateBagChangeHandler`](https://docs.fivem.net/natives/?_0x5BA35AAF)`(char* keyFilter, char* bagFilter, func handler)` → `int` | C/S | `(keyFilter, bagFilter, handler(bagName, key, value, reserved, replicated))`. |
| [`RemoveStateBagChangeHandler`](https://docs.fivem.net/natives/?_0xD36BE661)`(int cookie)` | C/S |  |
| [`GetStateBagValue`](https://docs.fivem.net/natives/?_0x637F4C75)`(char* bagName, char* key)` → `object` | C/S |  |
| [`SetStateBagValue`](https://docs.fivem.net/natives/?_0x8D50E33A)`(char* bagName, char* keyName, char* valueData, int valueLength, BOOL replicated)` | C/S | Low-level (wrappers are easier). |
| [`GetStateBagKeys`](https://docs.fivem.net/natives/?_0x78D864C7)`(char* bagName)` → `object` | C/S |  |
| [`StateBagHasKey`](https://docs.fivem.net/natives/?_0x12A330)`(char* bagName, char* key)` → `bool` | C/S |  |
| [`EnsureEntityStateBag`](https://docs.fivem.net/natives/?_0x3BB78F05)`(Entity entity)` | C/S |  |
| [`GetEntityFromStateBagName`](https://docs.fivem.net/natives/?_0x4BDF1867)`(char* bagName)` → `Entity` | C/S | `'entity:<netId>'` → handle (0 if not in scope on the client). |
| [`GetPlayerFromStateBagName`](https://docs.fivem.net/natives/?_0xA56135E0)`(char* bagName)` → `int` | C/S | `'player:<id>'` → player. |

## 26. Convars, resources, HTTP, KVP, misc runtime

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`GetConvar`](https://docs.fivem.net/natives/?_0x6CCD2564)`(char* varName, char* default_)` → `char*` | C/S | Always string; use `GetConvarInt`/`GetConvarBool`/`GetConvarFloat` for typed reads. |
| [`GetConvarInt`](https://docs.fivem.net/natives/?_0x935C0AB2)`(char* varName, int default_)` → `int` | C/S |  |
| [`GetConvarBool`](https://docs.fivem.net/natives/?_0x7E8EBFE5)`(char* varName, BOOL defaultValue)` → `BOOL` | C/S |  |
| [`GetConvarFloat`](https://docs.fivem.net/natives/?_0x9E666D)`(char* varName, float defaultValue)` → `float` | C/S |  |
| [`SetConvar`](https://docs.fivem.net/natives/?_0x341B16D2)`(char* varName, char* value)` | S |  |
| [`SetConvarReplicated`](https://docs.fivem.net/natives/?_0xF292858C)`(char* varName, char* value)` | S | Visible to clients (never secrets). |
| [`SetConvarServerInfo`](https://docs.fivem.net/natives/?_0x9338D547)`(char* varName, char* value)` | S | Shows in server list info. |
| [`AddConvarChangeListener`](https://docs.fivem.net/natives/?_0xAB7F7241)`(char* conVarFilter, func handler)` → `int` | C/S |  |
| [`RemoveConvarChangeListener`](https://docs.fivem.net/natives/?_0xEAC49841)`(int cookie)` | C/S |  |
| [`GetCurrentResourceName`](https://docs.fivem.net/natives/?_0xE5E9EBBB)`()` → `char*` | C/S |  |
| [`GetInvokingResource`](https://docs.fivem.net/natives/?_0x4D52FE5B)`()` → `char*` | C/S | Which resource called your export/event — use to restrict exports. |
| [`GetResourceState`](https://docs.fivem.net/natives/?_0x4039B485)`(char* resourceName)` → `char*` | C/S | `'started'`, `'starting'`, `'stopped'`, `'missing'`… — dependency checks. |
| [`StartResource`](https://docs.fivem.net/natives/?_0x29B440DC)`(char* resourceName)` → `BOOL` | S |  |
| [`StopResource`](https://docs.fivem.net/natives/?_0x21783161)`(char* resourceName)` → `BOOL` | S |  |
| [`GetNumResources`](https://docs.fivem.net/natives/?_0x863F27B)`()` → `int` | C/S |  |
| [`GetResourceByFindIndex`](https://docs.fivem.net/natives/?_0x387246B7)`(int findIndex)` → `char*` | C/S |  |
| [`GetResourceMetadata`](https://docs.fivem.net/natives/?_0x964BAB1D)`(char* resourceName, char* metadataKey, int index)` → `char*` | C/S | Read fxmanifest keys (e.g. `'version'`). |
| [`GetNumResourceMetadata`](https://docs.fivem.net/natives/?_0x776E864)`(char* resourceName, char* metadataKey)` → `int` | C/S |  |
| [`LoadResourceFile`](https://docs.fivem.net/natives/?_0x76A9EE1F)`(char* resourceName, char* fileName)` → `char*` | C/S | Read a file from any resource. |
| [`SaveResourceFile`](https://docs.fivem.net/natives/?_0xA09E7E7B)`(char* resourceName, char* fileName, char* data, int dataLength)` → `BOOL` | S | Write a file into a resource folder (server). |
| [`GetResourcePath`](https://docs.fivem.net/natives/?_0x61DCF017)`(char* resourceName)` → `char*` | S |  |
| [`PerformHttpRequestInternalEx`](https://docs.fivem.net/natives/?_0x6B171E87)`(object requestData)` → `int` | S | Backing native of the `PerformHttpRequest(url, cb, method, data, headers)` Lua helper — use the helper. |
| [`SetHttpHandler`](https://docs.fivem.net/natives/?_0xF5C6330C)`(func handler)` | S | Serve HTTP at `http://server:30120/<resource>/`. |
| [`GetGameTimer`](https://docs.fivem.net/natives/?_0xA4EA0691)`()` → `long` | S | ms since start — use for cooldowns. |
| [`GetGameName`](https://docs.fivem.net/natives/?_0xE8EAA18B)`()` → `char*` | C/S | `'fxserver'` on the server, `'fivem'`, `'redm'`, `'libertym'` on clients. |
| [`GetGameBuildNumber`](https://docs.fivem.net/natives/?_0x804B9F7B)`()` → `int` | C/S |  |
| [`GetHashKey`](https://docs.fivem.net/natives/?_0x98EFF6F1)`(char* model)` → `Hash` | S |  |
| [`SetGameType`](https://docs.fivem.net/natives/?_0xF90B7469)`(char* gametypeName)` | S | Server list game type. |
| [`SetMapName`](https://docs.fivem.net/natives/?_0xB7BA82DC)`(char* mapName)` | S |  |
| [`SetResourceKvp`](https://docs.fivem.net/natives/?_0x21C7A35B)`(char* key, char* value)` | C/S | Per-resource key/value store (server: server-side store; client: on the player's PC — never trust it). |
| [`SetResourceKvpInt`](https://docs.fivem.net/natives/?_0x6A2B1E8)`(char* key, int value)` | C/S |  |
| [`SetResourceKvpFloat`](https://docs.fivem.net/natives/?_0x9ADD2938)`(char* key, float value)` | C/S |  |
| [`SetResourceKvpNoSync`](https://docs.fivem.net/natives/?_0xCF9A2FF)`(char* key, char* value)` | C/S | Batch writes; then `FlushResourceKvp`. |
| [`FlushResourceKvp`](https://docs.fivem.net/natives/?_0xE27C97A0)`()` | S |  |
| [`GetResourceKvpString`](https://docs.fivem.net/natives/?_0x5240DA5A)`(char* key)` → `char*` | C/S |  |
| [`GetResourceKvpInt`](https://docs.fivem.net/natives/?_0x557B586A)`(char* key)` → `int` | C/S |  |
| [`GetResourceKvpFloat`](https://docs.fivem.net/natives/?_0x35BDCEEA)`(char* key)` → `float` | C/S |  |
| [`DeleteResourceKvp`](https://docs.fivem.net/natives/?_0x7389B5DF)`(char* key)` | C/S |  |
| [`StartFindKvp`](https://docs.fivem.net/natives/?_0xDD379006)`(char* prefix)` → `int` | C/S | Iterate keys by prefix: `StartFindKvp` → `FindKvp` until nil → `EndFindKvp`. |
| [`FindKvp`](https://docs.fivem.net/natives/?_0xBD7BEBC5)`(int handle)` → `char*` | C/S |  |
| [`EndFindKvp`](https://docs.fivem.net/natives/?_0xB3210203)`(int handle)` | C/S |  |

## 27. Client CFX — NUI, DUI, runtime textures, keymapping, Discord, KVP

| Native (Lua call → returns) | Side | Note |
|---|---|---|
| [`SetNuiFocus`](https://docs.fivem.net/natives/?_0x5B98AE30)`(BOOL hasFocus, BOOL hasCursor)` | C | `(hasFocus, hasCursor)`. Always release on close and on resource stop. |
| [`SetNuiFocusKeepInput`](https://docs.fivem.net/natives/?_0x3FF5E5F8)`(BOOL keepInput)` | C | Keep game input while NUI has focus (then disable controls you don't want). |
| [`IsNuiFocused`](https://docs.fivem.net/natives/?_0x98545E6D)`()` → `BOOL` | C |  |
| [`SendNuiMessage`](https://docs.fivem.net/natives/?_0x78608ACB)`(char* jsonString)` → `BOOL` | C | Raw JSON string; the Lua helper `SendNUIMessage(table)` wraps it. |
| [`RegisterNuiCallback`](https://docs.fivem.net/natives/?_0xC59B980C)`(char* callbackType, func callback)` | C | `(name, function(data, cb) … cb(result) end)`; `RegisterNUICallback` is the Lua helper. |
| [`RegisterNuiCallbackType`](https://docs.fivem.net/natives/?_0xCD03CDA9)`(char* callbackType)` | C | Legacy event-based registration. |
| [`GetNuiCursorPosition`](https://docs.fivem.net/natives/?_0xBDBA226F)`()` → `int x, int y` | C |  |
| [`SetManualShutdownLoadingScreenNui`](https://docs.fivem.net/natives/?_0x1722C938)`(BOOL manualShutdown)` | C | Keep the loading screen until `ShutdownLoadingScreenNui`. |
| [`ShutdownLoadingScreenNui`](https://docs.fivem.net/natives/?_0xB9234AFB)`()` | C |  |
| [`CreateDui`](https://docs.fivem.net/natives/?_0x23EAF899)`(char* url, int width, int height)` → `long` | C | Web page rendered into a texture (in-world screens). Destroy it when done. |
| [`DestroyDui`](https://docs.fivem.net/natives/?_0xA085CB10)`(long duiObject)` | C |  |
| [`IsDuiAvailable`](https://docs.fivem.net/natives/?_0x7AAC3B4C)`(long duiObject)` → `BOOL` | C |  |
| [`GetDuiHandle`](https://docs.fivem.net/natives/?_0x1655D41D)`(long duiObject)` → `char*` | C | For `CreateRuntimeTextureFromDuiHandle`. |
| [`SetDuiUrl`](https://docs.fivem.net/natives/?_0xF761D9F3)`(long duiObject, char* url)` | C |  |
| [`SendDuiMessage`](https://docs.fivem.net/natives/?_0xCD380DA9)`(long duiObject, char* jsonString)` | C |  |
| [`SendDuiMouseMove`](https://docs.fivem.net/natives/?_0xD9D7A0AA)`(long duiObject, int x, int y)` | C |  |
| [`SendDuiMouseDown`](https://docs.fivem.net/natives/?_0x5D01F191)`(long duiObject, char* button)` | C |  |
| [`CreateRuntimeTxd`](https://docs.fivem.net/natives/?_0x1F3AC778)`(char* name)` → `long` | C | Runtime texture dictionary. |
| [`CreateRuntimeTextureFromDuiHandle`](https://docs.fivem.net/natives/?_0xB135472B)`(long txd, char* txn, char* duiHandle)` → `long` | C |  |
| [`CreateRuntimeTextureFromImage`](https://docs.fivem.net/natives/?_0x786D8BC3)`(long txd, char* txn, char* fileName)` → `long` | C | PNG from the resource → texture. |
| [`AddReplaceTexture`](https://docs.fivem.net/natives/?_0xA66F8F75)`(char* origTxd, char* origTxn, char* newTxd, char* newTxn)` | C | Replace a game texture (e.g. a billboard) with a runtime one. |
| [`RemoveReplaceTexture`](https://docs.fivem.net/natives/?_0xA896B20A)`(char* origTxd, char* origTxn)` | C |  |
| [`RegisterKeyMapping`](https://docs.fivem.net/natives/?_0xD7664FD1)`(char* commandString, char* description, char* defaultMapper, char* defaultParameter)` | C | `RegisterKeyMapping('+cmd', 'Label', 'keyboard', 'E')`; players can rebind; default only applies on first use. |
| [`SetDiscordAppId`](https://docs.fivem.net/natives/?_0x6A02254D)`(char* appId)` | C |  |
| [`SetDiscordRichPresenceAsset`](https://docs.fivem.net/natives/?_0x53DFD530)`(char* assetName)` | C |  |
| [`SetDiscordRichPresenceAction`](https://docs.fivem.net/natives/?_0xCBBC3FAC)`(int index, char* label, char* url)` | C |  |
| [`SetRichPresence`](https://docs.fivem.net/natives/?_0x7BDCBD45)`(char* presenceState)` | C |  |
| [`SetTextChatEnabled`](https://docs.fivem.net/natives/?_0x97B2F9F8)`(BOOL enabled)` → `BOOL` | C |  |
| [`GetCurrentServerEndpoint`](https://docs.fivem.net/natives/?_0xEA11BFBA)`()` → `char*` | C |  |
| [`IsGameEnhancedVersion`](https://docs.fivem.net/natives/?_0x4DD998F6)`()` → `BOOL` | C | `true` on GTA V Enhanced (Cfx Server early access). |
| [`GetGameBuildNumber`](https://docs.fivem.net/natives/?_0x804B9F7B)`()` → `int` | C/S |  |

## 28. Common pitfalls

- **Ownership.** Under OneSync the entity's *owner* simulates it. Tasks, velocity, health, deletion, vehicle damage/handling and many `Set*` natives silently do nothing on non-owners. Either run the code on the owner (send the net ID to the owner), request control (`NetworkRequestControlOfEntity` + poll with timeout), or use the server RPC/state-bag route. Server-side spawned entities belong to a nearby client, not to the server.
- **Model must be loaded.** `CreateVehicle`, `CreatePed`, `CreateObject`, `SetPlayerModel` on the client need `RequestModel` + `HasModelLoaded` first, then `SetModelAsNoLongerNeeded`. Check `IsModelInCdimage` so a typo doesn't hang the loop — always add a timeout.
- **Out-params are returns.** `local ok, groundZ = GetGroundZFor_3dCoord(x, y, z, false)`; `local retval, weaponHash = GetCurrentPedWeapon(ped, true)`; `local status, hit, endCoords, normal, entity = GetShapeTestResult(handle)`. Don't pass placeholders for them (except the single-trailing-pointer case, e.g. `DeleteEntity(ent)`).
- **Per-frame natives** must be called every frame (`Wait(0)` loop) while active: all `Draw*`, `EndTextCommandDisplayText`, `DrawScaleformMovie*`, `HideHudComponentThisFrame`, `HideHudAndRadarThisFrame`, `*ThisFrame` density natives, `DisableControlAction`/`DisableAllControlActions`, `DisablePlayerFiring`, `IsControlJustPressed` polling. Gate the loop by distance/state so it sleeps (`Wait(500)`) when idle.
- **Handles are local.** A ped/vehicle handle on one client ≠ another client ≠ server. Send `NetworkGetNetworkIdFromEntity` (or `VehToNet`) and convert back with `NetworkGetEntityFromNetworkId` after checking `NetworkDoesEntityExistWithNetworkId`.
- **Scope.** Clients only know entities and players within ~424 m (OneSync culling). `GetActivePlayers`, `GetGamePool`, `GetPlayerFromServerId` and blips on entities only see in-scope ones; ask the server for global data (`GetAllVehicles`, player coords).
- **Same name, two natives.** `GetEntityCoords`, `GetPlayerPed`, `GetPlayerName`, `DeleteEntity`, `SetVehicleNumberPlateText`, `GiveWeaponToPed`… have different server signatures (`playerSrc` strings, fewer args). Look them up with `natives.py show`.
- **Inverted/odd booleans.** `SetVehicleExtra(veh, id, false)` turns the extra **on**; `SetVehicleDoorsLocked` uses lock-status numbers, not booleans; `SetBlipDisplay` uses display IDs.
- **Server-side fuel/health/locks.** Values set on a client are not authoritative; servers should hold the truth (state bags) and validate.
- **Strings & text.** Each `AddTextComponentSubstringPlayerName` is limited (~99 chars); split long text. Plates are padded to 8 chars.
- **Time/weather** get overridden by your weather-sync resource; change them there.
- **Never trust client-reported values** from these natives in server events (coords, weapon, vehicle) — re-read them server-side (`GetEntityCoords(GetPlayerPed(src))`).

## 29. Deprecated / legacy names and their replacements

Old names still work in Lua (the codegen emits aliases), but use the current name in new code. Verified as aliases in the DB unless marked otherwise.

| Legacy | Use instead |
|---|---|
| `SetNotificationTextEntry` | `BeginTextCommandThefeedPost` |
| `DrawNotification` | `EndTextCommandThefeedPostTicker` |
| `SetTextEntry` | `BeginTextCommandDisplayText` |
| `DrawText` | `EndTextCommandDisplayText` |
| `AddTextComponentString` | `AddTextComponentSubstringPlayerName` |
| `SetTextComponentFormat` | `BeginTextCommandDisplayHelp` |
| `DisplayHelpTextFromStringLabel` | `EndTextCommandDisplayHelp` |
| `SetTextEntry_2` | `BeginTextCommandPrint` |
| `DrawSubtitleTimed` | `EndTextCommandPrint` |
| `StartShapeTestRay` | `StartExpensiveSynchronousShapeTestLosProbe` |
| `CastRayPointToPoint` | `StartExpensiveSynchronousShapeTestLosProbe` |
| `GetRaycastResult` | `GetShapeTestResult` |
| `GetLabelText` | `GetFilenameForAudioConversation` |
| `GetActiveScreenResolution` | `GetActualScreenResolution` |
| `PushScaleformMovieFunction` | `BeginScaleformMovieMethod` |
| `PushScaleformMovieFunctionParameterInt` | `ScaleformMovieMethodAddParamInt` |
| `PushScaleformMovieFunctionParameterFloat` | `ScaleformMovieMethodAddParamFloat` |
| `PushScaleformMovieFunctionParameterBool` | `ScaleformMovieMethodAddParamBool` |
| `PushScaleformMovieFunctionParameterString` | `ScaleformMovieMethodAddParamTextureNameString` |
| `PopScaleformMovieFunctionVoid` | `EndScaleformMovieMethod` |
| `SetBlackout` | `SetArtificialLightsState` |
| `GetPlayerPed(-1)` | `PlayerPedId()` / ox_lib `cache.ped` |
| `GetDistanceBetweenCoords(...)` | `#(vec3(a) - vec3(b))` (Lua vector math, much faster) |
| `GetHashKey('x')` in loops | backtick literal `` `x` `` |
| `Citizen.CreateThread` / `Citizen.Wait` | `CreateThread` / `Wait` |
| `SetStateOfClosestDoorOfType` | door system (`AddDoorToSystem` + `DoorSystemSetDoorState`) or ox_doorlock |
| client `CreateVehicle` for persistent/owned vehicles | server `CreateVehicleServerSetter` |
| `GetPlayerIdentifiers` loop for the license | `GetPlayerIdentifierByType(src, 'license')` |
| `GetClosestVehicle` | `GetGamePool('CVehicle')` + distance, or `lib.getClosestVehicle` |

## 30. Game references (IDs, models, hashes, lists)

All URLs checked on 2026-10-07.

| What | Where |
|---|---|
| Control IDs | https://docs.fivem.net/docs/game-references/controls/ |
| Key names for `RegisterKeyMapping` | https://docs.fivem.net/docs/game-references/input-mapper-parameter-ids/keyboard/ |
| Blip sprites and colours | https://docs.fivem.net/docs/game-references/blips/ |
| Marker types | https://docs.fivem.net/docs/game-references/markers/ |
| Checkpoints | https://docs.fivem.net/docs/game-references/checkpoints/ |
| HUD colours | https://docs.fivem.net/docs/game-references/hud-colors/ |
| Text formatting (`~r~`, `~INPUT_CONTEXT~`, …) | https://docs.fivem.net/docs/game-references/text-formatting/ |
| Instructional buttons | https://docs.fivem.net/docs/game-references/instructional-buttons/ |
| Ped models | https://docs.fivem.net/docs/game-references/ped-models/ |
| Vehicle models | https://docs.fivem.net/docs/game-references/vehicle-references/vehicle-models/ |
| Vehicle colours | https://docs.fivem.net/docs/game-references/vehicle-references/vehicle-colors/ |
| Vehicle flags | https://docs.fivem.net/docs/game-references/vehicle-references/vehicle-flags/ |
| Weapon models / hashes / components | https://docs.fivem.net/docs/game-references/weapon-models/ |
| Pickup hashes | https://docs.fivem.net/docs/game-references/pickup-hashes/ |
| Zones (`GetNameOfZone` codes) | https://docs.fivem.net/docs/game-references/zones/ |
| Radio stations | https://docs.fivem.net/docs/game-references/radiostations/ |
| Speeches | https://docs.fivem.net/docs/game-references/speeches/ |
| Game events / net game events | https://docs.fivem.net/docs/game-references/game-events/ · https://docs.fivem.net/docs/game-references/net-game-events/ |
| Data files (`data_file` keys) | https://docs.fivem.net/docs/game-references/data-files/ |
| Scenarios, anim dicts, clipsets, particles, sounds, IPLs, timecycles, explosions, ped config flags (community dumps) | https://github.com/DurtyFree/gta-v-data-dumps (`scenariosCompact.json`, `animDictsCompact.json`, `movementClipsetsCompact.json`, `particleEffectsCompact.json`, `soundNames.json`, `ipls.json`, `timecycleModifiers.json`, `explosionTypesCompact.json`) |
| Animation browser | https://alexguirre.github.io/animations-list/ · https://forge.plebmasters.de/animations |
| Scenario list (wiki) | https://wiki.rage.mp/index.php?title=Scenarios |

docs.fivem.net has no scenario or anim-dict page; the community lists above are **UNVERIFIED** against the current game build (most entries are stable since 2015).

## 31. Sources

- Native docs: https://docs.fivem.net/natives/ · DB repo: https://github.com/citizenfx/natives
- GTA V native DB: https://static.cfx.re/natives/natives.json · CFX native DB: https://runtime.fivem.net/doc/natives_cfx.json
- Lua codegen (names, pointer/return rules, aliases): https://github.com/citizenfx/fivem/blob/master/ext/natives/codegen_out_lua.lua
- Game references: https://docs.fivem.net/docs/game-references/
- OneSync / entity ownership: https://docs.fivem.net/docs/scripting-reference/onesync/
- State bags: https://docs.fivem.net/docs/scripting-manual/networking/state-bags/ · Network IDs: https://docs.fivem.net/docs/scripting-manual/networking/ids/
- Routing buckets: https://docs.fivem.net/docs/cookbook/2020/11/27/routing-buckets-split-game-state/
- Key mapping: https://docs.fivem.net/natives/?_0xD7664FD1
