# Mapping, streaming and custom assets (MLOs, YMAPs, IPLs, clothing)

Baseline: FXServer Legacy 35245 / game build 3889 (`mp2026_01`) / Cfx Server (Enhanced) early access — verified 2026-10-07.
Vehicles have their own file: [vehicles-and-handling.md](vehicles-and-handling.md). Verify natives with `python scripts/natives.py show <Name>`.

## Contents
1. Streaming basics and file types
2. Legacy vs Enhanced (stream_enhanced, Alchemist)
3. Map / MLO resources
4. Vanilla IPLs, interiors and entity sets (bob74_ipl)
5. Add-on clothing (freemode peds)
6. Tools in 2026 (versions)
7. Asset budgets and FXServer size warnings
8. Pools, cache and load time
9. Scenarios, popgroups, timecycles and other data files
10. Workflow checklists
11. Legal
12. Sources

## 1. Streaming basics and file types
- Every file under `stream/` (any depth) is registered with the game streamer by **file name**; the folder structure is ignored. Duplicate names across resources: the last one loaded wins.
- `.meta`/`.xml` data files are **not** streamed: add them to `files {}` and declare them with `data_file` (table in `vehicles-and-handling.md` §2 and https://docs.fivem.net/docs/game-references/data-files/).
- `this_is_a_map 'yes'` marks a resource as a map and reloads map storage when it loads (use it for YMAP/MLO packs).
- FiveM accepts **raw XML** `.ymap`/`.ytyp` files (name them `foo.ymap`, not `foo.ymap.xml`); they go through the game parser, which can differ from CodeWalker/OpenIV parsers.

| Ext | Content |
|---|---|
| `.ydr` | single drawable (prop/building mesh) |
| `.ydd` | drawable dictionary (ped components, clothing) |
| `.yft` | fragment (vehicles, breakable props) |
| `.ytd` | texture dictionary |
| `.ybn` | static collision (bounds) |
| `.ymap` | map placement: entities, car generators, occluders, LOD lights, timecycle mods |
| `.ytyp` | archetype definitions (incl. MLO interiors, rooms, portals, entity sets) |
| `.ycd` | clip dictionary (animations) |
| `.ynv` / `.ynd` | navmesh / path nodes |
| `.ypt` | particle effects |
| `.awc` | audio wave container |
| `.ymt` | metadata (ped variations / creature metadata / scenarios) |

## 2. Legacy vs Enhanced
- GTA V Enhanced (Gen9) needs Gen9 assets. Resources can ship both: `stream/` (Gen8) and `stream_enhanced/` (Gen9). When `stream_enhanced/` exists, Enhanced loads it **instead of** `stream/`; `stream/` alone still works on Enhanced but is deprecated.
- **Alchemist** (Cfx Portal downloads, Windows 11) converts YDR, YTD, YFT, YPT, YDD from Legacy to Enhanced ("Asset Conversion") or fixes old-tool output ("Asset Refinement"). CLI: `AlchemistCli.exe <in> <out> [--refine] [--relaxed] [-f] [-jN] [--fail-on-error]`. The GUI stops on escrowed assets; the CLI skips them and lists them in its report.
- Pointing Alchemist at a whole `resources/` folder produces a drop-in Enhanced resources folder.
- Enhanced early access: pure mode always on (no graphics mods), Asset Escrow not implemented yet. See `gta5-enhanced.md`.

## 3. Map / MLO resources
```lua
-- fxmanifest.lua (map/MLO)
fx_version 'cerulean'
game 'gta5'
this_is_a_map 'yes'

-- only when the .ytyp must be requested explicitly (custom archetypes used by other ymaps / props)
data_file 'DLC_ITYP_REQUEST' 'stream/my_mlo.ytyp'
```
- **MLO** = `.ytyp` (archetype with interior: rooms, portals, entity sets) + `.ymap` placing the MLO instance + `.ybn` collisions (shell + per-room) + `.ydr`/`.ytd` assets. Since Sollumz 2.9 you can also create MLO instances directly in YMAPs from Blender.
- Removing vanilla buildings: ship a modified copy of the vanilla `.ymap` (CodeWalker "Save as" into your resource) or use entity-removal techniques; never stream a whole modified vanilla area if a small ymap suffices.
- Overlaps: two MLOs or an MLO over a vanilla interior → flickering, missing collisions, "falling through floor". Disable the vanilla IPL first (§4).
- Doors in MLOs: give door archetypes proper door flags (see the official assets manual part 8) and manage locks with ox_doorlock.
- LODs: keep `lodDist`/HD/LOD/SLOD hierarchy coherent; broken parent links cause pop-in. Sollumz 2.9 manages LOD hierarchies across map groups and can auto-partition entities into `strm`/`long`/`critical`/per-interior YMAPs.
- Collisions: `.ybn` must match the visual; missing/oversized collisions are a common crash and "can't walk inside" cause. Test by walking every room and driving around the exterior.

## 4. Vanilla IPLs, interiors and entity sets
- Many online interiors (apartments, offices, bunkers, nightclubs, yachts, heist sets) are not loaded by default. **bob74_ipl** (MIT, `Bob74/bob74_ipl`) fixes map holes and exposes every interior with per-interior functions documented on its wiki. Current: **2.7.1** (2026-10-04, adds Enhanced streaming files; 2.7.0 added "The Kortz Center Heist"). The Qbox recipe installs it by default. It needs a game build that contains those DLCs (use the latest `sv_enforceGameBuild`).
- Raw natives (client):
```lua
-- client: load an IPL and toggle an entity set inside an interior
local IPL_NAME = 'my_ipl_name'          -- take real names from the bob74_ipl wiki / CodeWalker
local SET_NAME = 'my_entity_set'        -- entity set name defined in the interior's .ytyp
local coords = vec3(0.0, 0.0, 0.0)      -- any point inside the interior

RequestIpl(IPL_NAME)

local interior = GetInteriorAtCoords(coords.x, coords.y, coords.z)
if interior ~= 0 then
    PinInteriorInMemory(interior)
    local timeout = GetGameTimer() + 5000
    while not IsInteriorReady(interior) and GetGameTimer() < timeout do Wait(0) end
    if not IsInteriorEntitySetActive(interior, SET_NAME) then
        ActivateInteriorEntitySet(interior, SET_NAME)
    end
    SetInteriorEntitySetColor(interior, SET_NAME, 1)   -- only for sets that support tint colours
    RefreshInterior(interior)   -- required after changing entity sets
end
```
- `RemoveIpl(name)` / `IsIplActive(name)`; `DeactivateInteriorEntitySet(interior, set)`.
- Make interior state **server-driven** when it matters for RP (e.g. business upgrades): store it server-side, publish with `GlobalState`/state bags, apply on clients in a change handler, and re-apply when the player enters (interiors unload).
- Never let two resources toggle the same interior: if you use bob74_ipl, configure through its API instead of calling the natives in parallel.

## 5. Add-on clothing (freemode peds)
- Naming (forum how-to 3345474): pick a lowercase collection name, e.g. `mp_f_freemode_01_myclothes`. Components: `mp_f_freemode_01_myclothes^jbib_000_u.ydd` + textures `mp_f_freemode_01_myclothes^jbib_diff_000_a_uni.ytd` (`_u`/`_uni` universal, `_r`/`_whi` race; up to 26 textures a–z per drawable). Props add `_p_`: `mp_f_freemode_01_p_myclothes^p_head_000.ydd` / `^p_head_diff_000_a.ytd`. Ship `mp_f_freemode_01_myclothes.ymt` and a same-named `.meta` declared as `data_file 'SHOP_PED_APPAREL_META_FILE' 'mp_f_freemode_01_myclothes.meta'` (male: `mp_m_freemode_01`).
- Tools: **grzyClothTool** (GPL-3.0, open source; v1.3.0 2026-07-14 — adds "256 drawables per type" with option to keep 128) builds FiveM-ready packs from loose `.ydd`/`.ytd`; durty-cloth-tool (DurtyFree) is the older alternative.
- Limits: historically **128 drawables per component type per YMT** (indices > 127 not visible to other clients because of 7-bit sync fields). Newer tools allow up to 255/256 per type, implying recent FiveM support — **UNVERIFIED**: test indices ≥ 128 with a second client before relying on it, otherwise split into multiple DLC names.
- Appearance resources read drawable counts at runtime and address clothes by index, so adding drawables needs no code change; removing or reordering them shifts indices and breaks saved outfits. Qbox recipe uses **illenium-appearance** (v5.7.0, last release 2024-12); ESX uses `esx_skin` + `skinchanger`; `fivem-appearance` (pedr0fontoura) is unmaintained since 2023.
- Every drawable costs memory on every client that sees it: keep textures ≤ 1024–2048 px, avoid 4K "detail" textures, and monitor `strmem`.

## 6. Tools in 2026 (versions checked 2026-10-07)
| Tool | Version / status | Use |
|---|---|---|
| **CodeWalker** (dexyfex) | Binaries via CodeWalker Discord `#releases` (official assets manual uses **Dev48**); GitHub `dexyfex/CodeWalker` last commit 2025-04-11; includes a **Gen9 (Enhanced) converter** (April 2025) — exact latest dev number **UNVERIFIED** | YMAP/YTYP editing, RPF explorer, XML import/export, map placement |
| **Sollumz** (Blender add-on, GPL-3.0) | **v2.9.0** (2026-08-04): YMAP rework (entities, MLO instances, LOD hierarchies, car generators, occluders, LOD lights, grass), texture dictionaries, Blender 5.2 fixes; README: Blender ≥ 4.0 | Modelling/export of YDR/YFT/YDD/YBN/YMAP/YTYP; install from GitHub releases zip via Blender "Install from Disk"; optional pyMateria for direct binary I/O |
| **Alchemist** (Cfx.re) | Cfx Portal download; Windows 11 | Legacy → Enhanced conversion, asset refinement |
| **OpenIV** | No confirmed Enhanced-compatible release (community patchers exist) — **UNVERIFIED** | Browsing Legacy RPFs; respect Rockstar/OpenIV terms |
| **grzyClothTool** | v1.3.0 (2026-07-14) | Clothing packs |
| Blender | Official FiveM assets manual uses 4.5 LTS | 3D |

The official **FiveM assets manual** (docs.fivem.net/docs/assets-manual/) has a 9-part beginner series: tooling, exporting vanilla assets, Blender creation, placing assets, collisions, LODs, map animations, doors, asset libraries.

## 7. Asset budgets and FXServer size warnings
FXServer checks every streamed asset's physical (VRAM) and virtual (RAM) size at start (`ResourceStreamComponent.cpp`):

| Size (per asset, physical or virtual) | Console colour | Message |
|---|---|---|
| > 16 MiB | `^4` | `Asset <res>/<file> uses N MiB of physical memory.` |
| > 32 MiB | `^3` | same |
| > 48 MiB | — | adds "**Oversized assets can and WILL lead to streaming issues (such as models not loading/rendering).**" |
| > 64 MiB | `^1` (red) | same |

Practical budget (community guidance, not engine limits):
- Vehicles: one `.ytd` ≤ 8–16 MiB, main textures ≤ 2048², most ≤ 1024²; clients default to `str_maxVehicleTextureRes 1024`.
- Props/buildings: reuse texture dictionaries (`GTXD_PARENTING_DATA` / `txdRelationships`), avoid unique 4K textures per prop.
- Clothing: ≤ 1024² per diffuse; normal/spec at half resolution.
- Always generate mipmaps and use block compression (DXT1/BC1 for opaque, DXT5/BC3 for alpha, BC7 where supported).
- Total streamed MB affects first-join download and RAM: audit your top 20 largest files every content update.

## 8. Pools, cache and load time
- Pool-exhaustion crashes name the pool in the crash dialog/log (e.g. `TxdStore`, `CMoveObject`). Raise only that pool in `server.cfg`: `increase_pool_size "TxdStore" 6000`. Startup-only; clients restart to match. Allowed pools/max increases are set by Cfx (e.g. TxdStore 26000, Building 20000, CMoveObject 600, FragmentStore 14000, InteriorProxy 450, StaticBounds 5000). Inspect pools in F8 → Tools → Streaming → Pool Monitor.
- `save_gta_cache <resource>` (client dev command) writes `<resource>_cache_y.dat` to `%AppData%\CitizenFX`; copy it to the resource root and add it to `files {}` to speed up loading of collision-heavy maps.
- Player-side cache clears (when assets look stale): delete `%LocalAppData%\FiveM\FiveM.app\data\cache`, `server-cache` and `server-cache-priv` (keep `game-storage`).

## 9. Scenarios, popgroups, timecycles and other data files
- Scenario points: `SCENARIO_POINTS_OVERRIDE_PSO_FILE` (`sp_manifest.ymt`) + `.ymt` scenario regions; FiveM cookbook "Using modified scenario files" explains overriding vanilla scenarios.
- Population: `DLC_POP_GROUPS` (popgroups.ymt), `POPSCHED_FILE` (popcycle.dat), `ZONEBIND_FILE`. Prefer runtime density control (qbx_density / `SetPedDensityMultiplierThisFrame`) unless you need different ped models per zone.
- Timecycle mods: `TIMECYCLEMOD_FILE`; time/weather visuals are client-side and must be synchronised by a weather resource (`gameplay-patterns.md` §6).
- Audio: `AUDIO_WAVEPACK` (folder), `AUDIO_GAMEDATA`, `AUDIO_SOUNDDATA` (`.rel` files) for custom sounds/sirens/engines.
- Level meta overrides (`before_level_meta`, `after_level_meta`, `replace_level_meta`) are deprecated: use data files.

## 10. Workflow checklists
New MLO from a seller:
```
- [ ] Confirm license allows your server use; no ripped/brand assets
- [ ] Read fxmanifest: this_is_a_map, data_file entries, no client scripts you don't need
- [ ] Check for overlap with vanilla IPLs / other MLOs at the same coords (CodeWalker map view)
- [ ] Start server: note size warnings for the resource; optimise > 16 MiB files
- [ ] Walk every room: collisions, portals (no world disappearing), doors, LODs from distance
- [ ] Enhanced server? Provide stream_enhanced/ converted with Alchemist, retest
```
Debug "map not loading / holes / flicker":
1. `strdbg true` and `strlist true` (dev mode) near the spot; look for failed/looping requests.
2. Stop the suspect map resources one by one (bisect), restart client between tests.
3. Check duplicate file names across resources (`dir /s /b *.ymap` or `find resources -name '*.ymap' | sort | uniq -d` on names).
4. Check bob74_ipl / other IPL loaders for conflicting interior toggles.

## 11. Legal
- Only stream assets you have rights to. The Cfx Platform License Agreement (2026-09-10) forbids selling Rockstar-made content and access to it; assets ripped from other games or real brands can get the server delisted. See `licensing-and-policy.md`.
- Converting someone else's escrowed asset with Alchemist is not possible (escrow) and redistributing converted paid assets violates their license.

## 12. Sources
- https://docs.fivem.net/docs/game-references/data-files/
- https://docs.fivem.net/docs/scripting-reference/resource-manifest/
- https://docs.fivem.net/docs/developers/legacy-vs-enhanced/
- https://docs.fivem.net/docs/alchemist/
- https://docs.fivem.net/docs/assets-manual/ (beginner series part 1: CodeWalker Dev48, Blender 4.5 LTS, Sollumz)
- https://docs.fivem.net/docs/server-manual/server-commands/ (`increase_pool_size`, pool limits)
- https://docs.fivem.net/docs/client-manual/console-commands/ (`save_gta_cache`, `strdbg`, `strlist`, `strmem`, `str_maxVehicleTextureRes`)
- https://docs.fivem.net/docs/cookbook/2021/04/09/fyi-fivem-and-redm-support-raw-ymap-ytyp-files/
- https://docs.fivem.net/docs/cookbook/2021/04/13/using-modified-scenario-files-on-fivem/
- https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/ResourceStreamComponent.cpp
- https://github.com/Sollumz/Sollumz/releases/tag/v2.9.0
- https://github.com/dexyfex/CodeWalker (commits "Gen9 converter", April 2025) · https://www.gta5-mods.com/tools/codewalker-gtav-interactive-3d-map
- https://github.com/Bob74/bob74_ipl (README changelog, releases 2.7.1)
- https://github.com/grzybeek/grzyClothTool/releases/tag/v1.3.0
- https://forum.cfx.re/t/how-to-stream-clothes-and-props-as-addons-for-mp-freemode-models/3345474 (clothing naming)
- https://forum.cfx.re/t/increase-streamed-drawables-limit-visible-on-other-clients/4206451 · https://forum.cfx.re/t/request-increase-ymt-limit-as-a-priority/5371314
- https://github.com/Qbox-project/txAdminRecipe (qbox.yaml: bob74_ipl, illenium-appearance)
