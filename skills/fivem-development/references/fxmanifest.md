# fxmanifest.lua and resource structure

Baseline: `fx_version 'cerulean'`, FXServer Legacy 35245 / citizenfx/fivem master `a74c2cc`, game build 3889 — verified 2026-10-07.

## Contents
1. Canonical manifest
2. How the manifest is evaluated
3. Directives reference
4. Runtime constraints (`dependencies`)
5. data_file types
6. fx_version history
7. Resource layout
8. Load order and `ensure`
9. Escrow
10. Validation
11. Sources

## 1. Canonical manifest
```lua
fx_version 'cerulean'
game 'gta5'

name 'myres'
author 'you'
description 'Short description'
version '1.0.0'
repository 'https://github.com/you/myres'

shared_scripts {
    '@ox_lib/init.lua',
    'config/shared.lua',
    'bridge/init.lua',      -- framework adapter (see framework-bridge.md)
}
client_scripts {
    'client/*.lua',
}
server_scripts {
    '@oxmysql/lib/MySQL.lua',
    'config/server.lua',    -- server-only config (prices, limits)
    'server/*.lua',
}

ui_page 'web/dist/index.html'
files {
    'web/dist/**/*',
    'locales/*.json',
    'bridge/**/*.lua',      -- Lua loaded at runtime with require/lib.load must be listed for the client
}

dependencies {
    '/server:12913',        -- minimum FXServer build (oxmysql 2.13+ needs 12913)
    '/onesync',
    'ox_lib',
    'oxmysql',
}
```
`lua54 'yes'` is no longer needed (Lua 5.3 removed 2025-06; the directive is deprecated and harmless).

## 2. How the manifest is evaluated
- `fxmanifest.lua` runs in a **separate, restricted Lua runtime** at load/refresh: no natives, no game APIs. Every `key 'value'` call creates a metadata entry; plural forms with a table (`client_scripts { ... }`) expand to one entry per item; `key 'value' { extra }` creates `key` + `key_extra` (JSON) entries.
- Any unknown key is kept as custom metadata, readable with `GetNumResourceMetadata(res, key)` / `GetResourceMetadata(res, key, index)` (e.g. `version`, `ox_lib 'locale'`, `locales_path 'lang'`).
- Changes need `refresh` + `restart myres` (or `ensure`). Syntax errors make the resource fail to start ("Could not load resource").
- `__resource.lua` + `resource_manifest_version` GUIDs are deprecated; convert to `fxmanifest.lua` + `fx_version`.
- Globbing (where supported): `*.lua` (non-recursive), `**/*.lua` or `**.lua` (recursive), `dir/cl_*.lua`. Matches are de-duplicated and sorted byte-wise (std::set: `B.lua` before `a.lua`), so order within a glob is alphabetical, not manifest order.
- `@resource/path.lua` in a script list loads another resource's file **into this resource's runtime** (e.g. `@ox_lib/init.lua`). The other resource must be started first → add it to `dependencies`.

## 3. Directives reference
| Directive | Glob | Meaning / notes |
|---|---|---|
| `fx_version 'cerulean'` | — | Required. Selects behaviour level (§6). `adamant`/`bodacious` are older levels. |
| `game 'gta5'` / `games { 'gta5', 'rdr3' }` / `'common'` | — | Required. `common` = no game-specific APIs. No key selects Legacy vs Enhanced (different server binary); dual-edition resources may declare `games { 'gta5', 'gta5enhanced' }` (gta5-enhanced.md section 10). The server **refuses to start** a resource with no recognised `fx_version` ("does not specify an `fx_version` in fxmanifest.lua") or one declaring both `game 'common'` and a specific game ("considered ill-formed"; `ServerResources.cpp`). |
| `client_script(s)` | yes | Client files; extension picks runtime: `.lua`, `.js` (V8), `.net.dll` (C#). Auto-added to the client download. |
| `server_script(s)` | yes | Server files: `.lua`, `.js` (Node 22), `.net.dll`. Never sent to clients. |
| `shared_script(s)` | yes | Loaded on **both** sides, **before** client/server scripts; downloaded by clients (no secrets). |
| `file(s)` | yes | Extra client-downloadable files: NUI assets, JSON, runtime-loaded Lua, `.meta` data files, `.mdb` debug symbols. |
| `rdr3_warning '...'` | — | Required for `game 'rdr3'` resources; exact string: `'I acknowledge that this is a prerelease build of RedM, and I am aware my resources *will* become incompatible once RedM ships.'` (citizenfx `ext/system-resources/resources/chat/fxmanifest.lua`). |
| `ui_page 'path'` or `ui_page 'https://...'` | — | Full-screen NUI page; must also be in `files` (unless absolute URL). Served from `https://cfx-nui-<res>/` under cerulean. One per resource. |
| `ui_page_preload 'yes'` | — | Create the NUI frame immediately at resource start instead of the lazy/prepared frame (exact timing **UNVERIFIED**). |
| `nui_callback_strict_mode 'true'` | — | Only accept NUI callback POSTs whose `Origin` is this resource's own frame (`https://cfx-nui-<res>` / `nui://<res>`); others are logged "blocked by NUI Callback Strict Mode". Recommended hardening. |
| `loadscreen 'path'` | — | Loading screen page (also in `files`). |
| `loadscreen_manual_shutdown 'yes'` | — | Keep the loading screen until `ShutdownLoadingScreenNui()`. |
| `loadscreen_cursor 'yes'` | — | Show the cursor on the loading screen. |
| `data_file 'TYPE' 'path'` | path | Mount game data (§5). File must also be in `files`. |
| `this_is_a_map 'yes'` | — | Map resource: reloads map storage on load. |
| `server_only 'yes'` | — | Clients download nothing from this resource. |
| `dependency` / `dependencies` | — | Resources (and §4 constraints) that must start first; missing → resource won't start. |
| `provide 'name'` | — | Satisfies `dependency 'name'` and acts as that resource (e.g. qbx_core `provide 'qb-core'`, ox_target `provide 'qtarget'`, screencapture `provide 'screenshot-basic'`). |
| `export 'fn'` / `exports { }` | — | Client export of global `_G[fn]` (legacy; prefer `exports('fn', f)` in code). |
| `server_export 'fn'` / `server_exports { }` | — | Server equivalent. |
| `escrow_ignore { }` | yes | Files left unencrypted by Asset Escrow (configs, locales, bridge). |
| `convar_category 'Name' { title, { {label, convar, type, default, ...}, ... } }` | — | Documents convars for FxDK "Project Settings"; types `CV_STRING`, `CV_BOOL`, `CV_INT`, `CV_SLIDER`, `CV_COMBI`, `CV_PASSWORD`, `CV_MULTI`; prefix `$` for `setr`, `#` for `sets` convars. |
| `use_experimental_fxv2_oal 'yes'` | — | Lua "one argument list": faster native calls, corrected return types; vectors **not** auto-unpacked; breaks with mistyped natives. Experimental. |
| `clr_disable_task_scheduler 'yes'` | — | C#: disable custom TPL scheduler (implied by `bodacious`+). |
| `node_version '22'` | — | Docs: selects Node 16/22 for server JS. Current source routes all server JS to Node 22 and ignores it; Node 16 removed 2026. Harmless to keep `'22'`. |
| `lua54 'yes'` | — | Deprecated no-op (5.4 is the only Lua). |
| `mono_rt2 '...'` | — | Expired C# v2 pilot (2026-06-30): remove. |
| `before_level_meta` / `after_level_meta` / `replace_level_meta 'file'` | — | Level meta hooks (deprecated → prefer `data_file`). |
| `replace_traintrack_file`, `init_meta` | — | Advanced game-data hooks read by the GTA resource mounter (rarely needed; **UNVERIFIED** syntax). |
| `author`, `description`, `version`, `repository`, `name` | — | Metadata (`GetResourceMetadata(res, 'version', 0)`); shown by txAdmin/version checkers. |
| `ox_lib 'locale'` (repeatable), `locales_path 'dir'` | — | ox_lib custom keys: preload modules into `lib`; change the locales folder (default `locales`). |

Stream assets are not a directive: anything in `stream/` (and `stream_enhanced/` on Enhanced, which replaces `stream/` there) is auto-streamed.

## 4. Runtime constraints (`dependencies`)
| Constraint | Requirement | Example |
|---|---|---|
| `/server:<build>` | FXServer build ≥ value | `'/server:12913'` |
| `/policy:<name>` | Server key granted that policy | `'/policy:subdir_file_mapping'` |
| `/onesync` | State awareness enabled (always true now: OneSync forced on) | `'/onesync'` |
| `/gameBuild:<build or name>` | `sv_enforceGameBuild` ≥ value | `'/gameBuild:3889'` / `'/gameBuild:mp2026_01'` / `'/gameBuild:h4'` |
| `/native:0xHASH` | Server supports that native | `'/native:0xE27C97A0'` |

## 5. data_file types
Common types (full table with mounters and examples: game-references/data-files):

| Area | Types |
|---|---|
| Vehicles | `VEHICLE_METADATA_FILE` (vehicles.meta), `HANDLING_FILE`, `CARCOLS_FILE`, `VEHICLE_VARIATION_FILE` (carvariations.meta), `VEHICLE_LAYOUTS_FILE`, `VEHICLEEXTRAS_FILE`, `VFXVEHICLEINFO_FILE`, `VEHICLE_SHOP_DLC_FILE`, `CONTENT_UNLOCKING_META_FILE` |
| Weapons | `WEAPONINFO_FILE`, `WEAPONINFO_FILE_PATCH`, `WEAPON_METADATA_FILE`, `WEAPON_ANIMATIONS_FILE`, `WEAPONCOMPONENTSINFO_FILE`, `WEAPON_SHOP_INFO_METADATA_FILE`, `LOADOUTS_FILE`, `DLC_WEAPON_PICKUPS`, `EXPLOSION_INFO_FILE` |
| Peds / clothing | `PED_METADATA_FILE`, `PED_PERSONALITY_FILE`, `PED_COMPONENT_SETS_FILE`, `PEDSTREAM_FILE`, `SHOP_PED_APPAREL_META_FILE`, `ALTERNATE_VARIATIONS_FILE`, `PED_OVERLAY_FILE`, `TATTOO_SHOP_DLC_FILE`, `PED_FIRST_PERSON_ASSET_DATA`, `PED_DAMAGE_APPEND_FILE` |
| Audio | `AUDIO_WAVEPACK` (folder), `AUDIO_GAMEDATA` (`*.dat151.rel`), `AUDIO_SOUNDDATA` (`*.dat54.rel`), `AUDIO_SYNTHDATA`, `AUDIO_SPEECHDATA`, `AUDIO_CURVEDATA`, `AUDIO_DYNAMIXDATA` |
| Maps / world | `DLC_ITYP_REQUEST` (`.ityp`), `GTXD_PARENTING_DATA`, `INTERIOR_PROXY_ORDER_FILE`, `TIMECYCLEMOD_FILE`, `SCENARIO_POINTS_OVERRIDE_PSO_FILE`, `SCENARIO_INFO_FILE`, `ZONEBIND_FILE`, `POPSCHED_FILE`, `DLC_POP_GROUPS`, `TRAINCONFIGS_FILE`, `TRAINTRACK_FILE` |
| Anim / AI | `CLIP_SETS_FILE`, `CONDITIONAL_ANIMS_FILE`, `MOVE_NETWORK_DEFS`, `EXPRESSION_SETS_FILE`, `COMBAT_BEHAVIOUR_OVERRIDE_FILE`, `EVENTS_OVERRIDE_FILE` |
| Effects / UI | `PTFXASSETINFO_FILE`, `SCALEFORM_DLC_FILE`, `OVERLAY_INFO_FILE`, `STREAMING_REQUEST_LISTS_FILE` |
| Text | `DLC_TEXT_FILE` (dlctext.meta, widely used for add-on vehicle labels; not listed in the docs table — **UNVERIFIED** there) |

```lua
-- add-on vehicle resource
files {
    'data/**/vehicles.meta',
    'data/**/carvariations.meta',
    'data/**/carcols.meta',
    'data/**/handling.meta',
}
data_file 'HANDLING_FILE' 'data/**/handling.meta'
data_file 'VEHICLE_METADATA_FILE' 'data/**/vehicles.meta'
data_file 'CARCOLS_FILE' 'data/**/carcols.meta'
data_file 'VEHICLE_VARIATION_FILE' 'data/**/carvariations.meta'
```
Models/textures (`.yft`, `.ytd`) go in `stream/`. More in `mapping-streaming.md`.

## 6. fx_version history
| Version | Date | Adds |
|---|---|---|
| `cerulean` | 2020-05 | NUI in a secure context: `https://cfx-nui-<res>/` URLs, NUI callbacks via `https://<res>/<cb>` (not `http://`), WASM/fetch support. **Use this.** |
| `bodacious` | 2020-02 | Implies `clr_disable_task_scheduler`; no `window` in JS script contexts. |
| `adamant` | 2019-12 | Requires `game`; mandatory for RedM. |

## 7. Resource layout (recommended)
```
myres/
├── fxmanifest.lua
├── config/
│   ├── shared.lua        # values the client may know (labels, coords, blips)
│   └── server.lua        # prices, rewards, limits — never sent to clients
├── bridge/               # framework adapters (init.lua picks one)
├── client/
├── server/
├── locales/              # en.json, es.json ... (ox_lib locale)
├── web/                  # NUI source (src/) and build output (dist/)
├── stream/               # streamed assets; `stream_enhanced/` overrides it on Enhanced
├── sql/install.sql
└── README.md
```
Naming: lowercase, `-` or `_`; don't use other ecosystems' prefixes (`ox_`, `qbx_`, `esx_`, `qb-`) for third-party resources.

## 8. Load order and `ensure`
- Within a resource: all `shared_script` entries first, then that side's `client_script`/`server_script` list, in manifest order; globs expand in byte-wise sorted order.
- `server.cfg`: `ensure` starts resources in order; declared `dependencies` are started automatically, but explicit order keeps logs clean:
```cfg
ensure oxmysql
ensure ox_lib
ensure qbx_core        # or es_extended / qb-core
ensure ox_target
ensure ox_inventory
ensure [standalone]    # a [bracket] folder: starts every resource inside
ensure myres
```
- `restart myres` reloads code and clients re-download changed files; other resources' state is not reset. After editing the manifest run `refresh` first.

## 9. Escrow (Asset Escrow / Tebex)
- Files are encrypted when uploaded through the Cfx.re Portal; `escrow_ignore` keeps configs/locales/bridges editable. Encrypted files start with `FXAP` (tools skip them).
- Escrow is **not available on GTA V Enhanced** servers yet (early access 2026). See `licensing-and-policy.md`.

## 10. Validation
`python scripts/manifest.py <resource>`: missing files, `ui_page` not in `files`, server files listed as client/shared, `@imports` without dependencies, obsolete keys.

## 11. Sources
- https://docs.fivem.net/docs/scripting-reference/resource-manifest/resource-manifest/
- https://docs.fivem.net/docs/game-references/data-files/
- https://docs.fivem.net/docs/scripting-manual/nui-development/loading-screens/ · https://docs.fivem.net/docs/developers/legacy-vs-enhanced/
- https://github.com/citizenfx/fivem — `code/components/nui-resources/src/ResourceUI.cpp` (`ui_page_preload`, `nui_callback_strict_mode`, cfx-nui prefix), `code/components/citizen-scripting-core/src/ResourceScriptingComponent.cpp` (load order), `code/components/loading-screens-five/src/LoadingScreens.cpp` (`loadscreen_cursor`), `code/components/citizen-resources-gta/src/ResourcesTest.cpp` (`data_file_extra`, `init_meta`, `replace_traintrack_file`), `code/components/citizen-scripting-mono-v2/src/MonoScriptRuntime.cpp` (`mono_rt2` expiry)
- https://github.com/overextended/ox_lib (`init.lua` `ox_lib` key, `imports/locale/shared.lua` `locales_path`)
