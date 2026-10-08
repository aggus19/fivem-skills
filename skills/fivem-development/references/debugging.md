# Debugging FiveM resources, servers and clients

Baseline: FXServer Legacy 35245 / Latest 37150, Cfx Server (Enhanced) early access, txAdmin 8.1.1 — verified 2026-10-07.
Exact message strings below were taken from the FiveM/txAdmin source or official docs (Sources); crash-cause rows are community-reported and marked as such.

## Contents
1. Where logs and errors appear
2. Developer mode (needed for many client commands)
3. Client console (F8) commands
4. Server console commands
5. Profiler workflow
6. Error messages → causes (scripts, resources, network)
7. Streaming, asset and crash signatures
8. Debug workflows
9. Crash dumps
10. Sources

## 1. Where logs and errors appear
| What | Location |
|---|---|
| Server live console | FXServer/txAdmin console; script errors print as `SCRIPT ERROR: @res/path.lua:42: <message>` + stack |
| txAdmin log files | `txData/<profile>/logs/fxserver.log` (server console output), `server.log` (txAdmin server/player event log), `admin.log` (admin actions); rotated as `<name>_YYYY-MM-DD_HH-MM-SS.log` |
| Client console | F8 (Legacy & Enhanced) |
| Client log files | `%LocalAppData%\FiveM\FiveM.app\logs\CitizenFX_log_<YYYY-MM-DDTHHMMSS>.log` (one per session) |
| Client crash dumps | `%LocalAppData%\FiveM\FiveM.app\crashes\` (+ crash report ID in the crash dialog) |
| NUI (CEF) console | `nui_devtools` (dev mode) or Remote debugging; CEF log `FiveM.app\cef_console.txt` |
| Client caches | `FiveM.app\data\cache`, `data\server-cache`, `data\server-cache-priv` (safe to delete), keep `data\game-storage` |
| Client config | `FiveM.app\CitizenFX.ini` (game path, `UpdateChannel`, `EnableFullMemoryDump`, `SavedBuildNumber`) |

Verbosity helpers: `set ox:printlevel:<resource> "debug"` (ox_lib `lib.print`), `set mysql_debug true` (oxmysql, dev only), `setr voice_debugMode 1` (pma-voice). Print-filter the server console with `con_addChannelFilter script:noisy-res noprint` (regex filters; `con_channelFilters` lists them).

## 2. Developer mode
Docs mark many client commands as developer-only; without it you get `Access denied for command resmon` or `Command strdbg is disabled in production mode`.
- **Legacy client:** launch with `+set moo 31337` (e.g. shortcut argument) or use a non-production update channel (`UpdateChannel=beta`/`canary` in CitizenFX.ini, less stable).
- **Enhanced:** `+set moo 31337` was removed; set `sv_devMode true` on the **server** (dev servers only).
- Never ship eval/run-code commands in production resources; use ACE-restricted debug commands.

## 3. Client console (F8) commands
| Command | Purpose |
|---|---|
| `resmon true` | resource monitor: CPU ms and memory per resource (dev) |
| `profiler record 500` → `profiler view` | frame profiler (see §5) |
| `netgraph true` | ping, in/out packets and bytes, routing packets/delay |
| `neteventlog true` | live list of net events in/out with size |
| `net_statsFile metrics.csv` | write network stats CSV |
| `netobjviewer true` | synced objects/nodes (state-awareness) |
| `net_printOwner <objectId>` | owner of a network object |
| `strdbg true` | what the streamer is loading now (world not loading, stuck requests) |
| `strlist true` | all streaming entries and status |
| `strmem true` | streaming memory per asset + totals |
| `cl_drawfps true` / `cl_drawperf true` | FPS / FPS, ping, packet loss, CPU, GPU usage & temp |
| `con_miniconChannels script:*` | show console channels on screen (`*` all, `script:myres` one resource; default `minicon:*`) |
| `con_winconsole true` | separate windowed console |
| `nui_devtools` | Chromium devtools for NUI (dev) |
| `modelviewer true` | load TXDs/drawables in a viewer |
| `save_gta_cache <resource>` | write a map cache file to ship with a collision-heavy map |
| `se_debug true` · `list_aces` · `list_principals` · `test_ace <principal> <object>` | ACL debugging |
| `cmdlist` | all registered commands and set convars |
| `str_maxVehicleTextureRes <n>` | user-level cap on vehicle texture resolution (default 1024) |
| `connect <ip:port>` / `disconnect` / `quit` | connection tests |

Enhanced-only dev tools: `cl_drawResTimeGraphs`, `cl_drawResTimeWarnings`, `con_poolInspector`, `con_streamingMonitor`, `con_archetypeMonitor`, `con_handlingEditor`, `con_inputViewer`, `con_timeCycleEditor`, `netobjlabeling`. Pools on Legacy: F8 → Tools → Streaming → Pool Monitor.

## 4. Server console commands
| Command | Purpose |
|---|---|
| `ensure <res>` / `restart <res>` / `start` / `stop` | resource lifecycle (`ensure` = start or restart) |
| `refresh` | rescan `resources/` (new folders, changed manifests) |
| `status` | connected players with ids/endpoints/ping |
| `profiler record 500` / `profiler view` / `profiler saveJSON f.json` | server-side profile (copy the printed link into Chrome) |
| `test_ace <principal> <object>` | check permissions (`add_ace`, `add_principal`) |
| `con_addChannelFilter <regex> <action>` / `con_channelFilters` | filter noisy channels |
| `block_net_game_event <name>` | block a game event type (anti-abuse) |
| `sync_start_recording <netId>` / `replay_start` | Enhanced only: entity sync recording |

## 5. Profiler workflow
1. Reproduce the lag (stand where it happens / trigger the feature).
2. `profiler record 500` (≈ 500 frames; client F8 or server console). `profiler status` shows progress.
3. `profiler view` (client opens Chrome; server prints a link) — or `profiler saveJSON name.json` and load it in Chrome DevTools → Performance → Load profile.
4. Look for resource ticks (`myres: tick`) and event handlers taking > 1 ms; fix the loop, then re-measure. Combine with `resmon` for steady-state cost (target idle ≈ 0.00–0.02 ms). See `performance.md`.

## 6. Error messages → causes
| Message (exact where quoted) | Side | Likely cause / fix |
|---|---|---|
| `SCRIPT ERROR: @res/file.lua:N: attempt to index a nil value (global 'ESX')` (or `QBCore`) | both | framework object not loaded: missing `@es_extended/imports.lua` / `GetCoreObject`, wrong `ensure` order, wrong side |
| `attempt to index a nil value (field '?')` | both | data not ready (player not loaded, DB row missing); guard + wait for loaded event / `LocalPlayer.state.isLoggedIn` |
| `attempt to call a nil value (field 'xxx')` | both | function/export typo, resource not started, defined on the other side. A typo'd *native* does not fail at load: `_G.__index` resolves natives lazily via `Citizen.LoadNative` and caches misses in `nilCache`, so the error appears only when that line runs (possibly a rare branch); run `python scripts/natives.py check <res> --strict` (`natives_loader.lua`) |
| `Warning: sending large event <name> (<N> bytes). This may cause performance issues. Consider using latent events instead.` | server | a server to client event >= 1,000,000 bytes (printed at most every 5 s): `TriggerLatentClientEvent`, paginate, send ids (`ServerResources.cpp`) |
| `Setting values on Entity is not supported at this time.` | both | `Entity(ent).foo = v`: use `Entity(ent).state.foo = v` / `:set()` (same for `Player`; `scheduler.lua`) |
| `cannot set values on exports` / `cannot set values on an export resource` | both | assigning to `exports.x`: define with `exports('name', fn)` (`scheduler.lua`) |
| `Couldn't find resource category <[name]>.` | server | `ensure [cat]` with no such bracket folder (`ServerResources.cpp`) |
| `Server specified an invalid game build enforcement (N).` | client | unsupported `sv_enforceGameBuild` value (`NetLibrary.cpp`) |
| `Reliable server command overflow.` (drop) | server | client spamming commands, e.g. a keybind loop (`ServerCommandPacketHandler.cpp`) |
| `No such export xxx in resource yyy` | both | export not registered on this side, file not in manifest, resource name wrong, resource stopped |
| `An error occurred while calling export \`xxx\` in resource \`yyy\`` | both | the export itself threw; read the nested stack (bug in the other resource or bad args) |
| `event xxx was not safe for net` | both | net event handled with `AddEventHandler` only → use `RegisterNetEvent` (and validate!) |
| `Current execution context is not in the scheduler, you should use CreateThread / SetTimeout or Event system (AddEventHandler) to be able to Await` | both | `.await` / `Citizen.Await` / `lib.callback.await` at file scope or inside a non-coroutine callback → wrap in `CreateThread` |
| `attempt to yield across a C-call boundary` | both | `Wait`/await inside a C-called Lua function: `table.sort` comparator, `string.gsub` callback, metamethods (`__index`, `__gc`…) |
| `Could not find dependency xxx for resource yyy.` | server | `dependency`/`dependencies` names a resource not present/startable |
| `Couldn't find resource xxx.` / `Couldn't start resource xxx.` | server | folder name ≠ ensure name, manifest syntax error, dependency failed (scroll up for the first error) |
| `Started resource xxx (N warnings)` | server | manifest/asset warnings: read them (oversized assets, missing files) |
| `server thread hitch warning: timer interval of N milliseconds` | server | main thread blocked > 150 ms: heavy sync loops, sync file I/O, `.await` storms, huge JSON; also `network thread …` / `sync thread …` (> 100 ms) variants. Profile (§5); host CPU steal also causes it |
| `Reliable network event overflow.` (drop reason) | server→client | the client sent more net events than the rate limiter allows (`netEvent` default 50/s, burst 200; flood limiter 75/300) → loops calling `TriggerServerEvent`; batch/throttle |
| `Reliable network event size overflow: <event>` | server→client | > 128 KiB/s (burst 384 KiB) of event payload → send less / use latent events; convars `rateLimiter_netEventSize_rate` / `_burst` |
| `Unreliable network event overflow.` | server→client | latent event rate limit |
| `Access denied for command xxx` / `Command xxx is disabled in production mode` | client | developer mode not enabled (§2) |
| `bad argument #1 to 'decode'` (json) | both | decoding `nil`/empty DB or HTTP value; guard `if str and str ~= '' then` |
| oxmysql `Unknown column` / `Table ... doesn't exist` | server | schema not imported or outdated; run the resource's SQL |
| NUI blank/white | client | `ui_page` path wrong or not in `files`, absolute asset paths (`/assets/...`) instead of relative (`base: './'`), build not run |
| NUI frozen / no response | client | `RegisterNUICallback` handler never calls `cb(...)`; `SetNuiFocus` left on |
| Vehicles/peds not appearing, no error | both | `sv_entityLockdown strict`/`relaxed` drops client-created entities → spawn server-side |
| A client "tried to use NetworkRequestControlOfEntity …, but it was rejected" | server | `sv_filterRequestControl` blocking control requests (expected with anti-cheat settings) |

## 7. Streaming, asset and crash signatures
| Signal | Meaning / first action |
|---|---|
| `Asset <res>/<file> uses N MiB of physical memory.` (+ "Oversized assets can and WILL lead to streaming issues…" above 48 MiB) | split/optimise textures; warnings start at 16 MiB |
| Crash dialog naming a file (e.g. `.yft`/`.ytd` "failed"/"invalid", physics validation) | that asset is broken: remove/re-export it; often bad collisions or exporter bugs |
| Pool name in crash (e.g. `TxdStore`, `CMoveObject`) | raise only that pool: `increase_pool_size "<Pool>" <n>` within Cfx limits |
| `ERR_GFX_D3D_INIT` | community-reported: GPU driver/overlay/overclock issues (ShadowPlay, Afterburner, ReShade); update drivers, disable overlays, clear caches — client-side, not your resource |
| `ERR_MEM_EMBEDDEDALLOC_ALLOC` | community-reported: game memory allocator exhausted/corrupted (heavy streaming, many add-ons, low RAM); no single fix — reduce asset load, test vanilla |
| `Error loading component xyz.dll` | delete `caches.xml` in FiveM app data (docs) |
| `Entry Point Not Found` | stray `v8*.dll` in `C:\Windows\System32` (docs) |
| `Game storage outdated`, `privcache ... could not lock file` | Cfx support articles (client issue, not server) |
| Texture loss / purple textures | too much VRAM: oversized YTDs, many add-on vehicles/clothes; `strmem` to find top consumers |

Crash names shown by the FiveM crash dialog (e.g. `pasta-aspen-table`) are three-word identifiers that map to a crash location (the same crash gets the same name); search them on forum.cfx.re with the game build. Always test on the official test server (`connect cfx.re/join/y4lg95`) to separate client problems from server content (docs).

## 8. Debug workflows
**Script error**
1. Reproduce with the smallest action; note client vs server.
2. Read the **first** `SCRIPT ERROR` (later ones are consequences).
3. Check load order (`ensure` order, `dependencies`), resource state (`GetResourceState('x')`), manifest (`python scripts/manifest.py <res>`).
4. Verify every native/export/name (`python scripts/natives.py check <res> --strict`).
5. Add boundary prints (event received, args via `json.encode(args)`, return values); remove afterwards.
6. Intermittent: race on player load, entity not yet networked (`lib.waitFor` with timeout), `source` read after a yield (capture `local src = source` first), Enhanced player-id reuse.

**"Works locally, not on the live server"**: different artifact/game build (`sv_enforceGameBuild`), missing convars/`setr`, SQL not imported, ACE permissions, OneSync/lockdown settings, Linux case-sensitive file names in `fxmanifest.lua`.

**Network/sync**: `netgraph`, `neteventlog`, `netobjviewer`; check event sizes and rates (§6), state bag spam (set only on change), entity ownership (`NetworkGetEntityOwner`).

**Streaming/map**: `strdbg`, `strlist`, `strmem`; bisect stream resources (stop half, restart client, repeat); check duplicate file names; Enhanced: missing `stream_enhanced/`.

**Performance**: `resmon` → `profiler` → fix → re-measure (`performance.md`).

**NUI**: `nui_devtools` → Console (JS errors) and Network (failed `https://<resource>/callback` fetches → callback not registered or wrong resource name; `GetParentResourceName()` in JS).

**Automating the loop (AI agents, CI)**: see [ai-dev-workflow-and-mcp.md](ai-dev-workflow-and-mcp.md) (RCON, `/info.json`, txAdmin API, community MCP servers and their risks).
- NUI automation: the CEF remote-debugging endpoint `http://127.0.0.1:13172/json` lists one target per NUI frame (`https://cfx-nui-<resource>/...`); any Chrome DevTools Protocol client (Chrome "inspect", Playwright `connectOverCDP`) can query the DOM, click and record network calls. Localhost only; dev use.
- Server console capture from Lua: `RegisterConsoleListener(function(channel, message) ... end)` (server) receives all console output and `GetConsoleBuffer()` (server) returns the current console buffer — useful for in-game log viewers and diagnostics resources. Keep such tooling out of production.

## 9. Crash dumps
- Client full dump: add `EnableFullMemoryDump=1` to `CitizenFX.ini`, reproduce (the game may freeze minutes while writing), Explorer opens `crashes\` with the dump selected; zip it; remove the line afterwards (dumps are 1–10 GB).
- Server (Windows): Sysinternals ProcDump — `procdump64.exe -accepteula -i` (register), then `procdump64.exe -accepteula -e -h -mp <FXServer PID>`; unregister with `-u`. Load in Visual Studio with symbols from `https://runtime.fivem.net/client/symbols/`. Linux full dumps are not supported by this method.
- Report reproducible engine bugs on forum.cfx.re (Bug reports) with build numbers, steps and dump.

## 10. Sources
- https://docs.fivem.net/docs/client-manual/console-commands/
- https://docs.fivem.net/docs/client-manual/citizenfx/ · https://docs.fivem.net/docs/client-manual/enabling-full-client-dumps/
- https://docs.fivem.net/docs/support/client-issues/ · https://docs.fivem.net/docs/support/server-debug/ · https://docs.fivem.net/docs/support/server-issues/
- https://docs.fivem.net/docs/server-manual/server-commands/ (`con_addChannelFilter`, `increase_pool_size`, Enhanced-only commands)
- https://docs.fivem.net/docs/developers/legacy-vs-enhanced/ (`sv_devMode`)
- https://forum.cfx.re/t/809058 (profiler guide, linked from docs "Using the Profiler")
- https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/scheduler.lua (`SCRIPT ERROR`, `was not safe for net`, `No such export`, Await message)
- https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/GameServer.cpp (hitch warnings) · `.../packethandlers/ServerEventPacketHandler.cpp` (net event rate limits) · `.../ServerResources.cpp` · `.../ResourceStreamComponent.cpp` · `code/components/citizen-resources-core/src/ResourceDependencyLoader.cpp`
- https://github.com/citizenfx/fivem/blob/master/code/client/launcher/Console.Logging.cpp (client log file name)
- https://github.com/citizenfx/txAdmin/blob/master/core/modules/Logger/index.ts (log paths)
- https://forum.cfx.re/t/rage-error-err-gfx-d3d-init/27811 · https://forum.cfx.re/t/rage-error-err-mem-embeddedalloc-alloc/989388 · https://forum.cfx.re/t/gta5-b2699-exe-sub-141607dd4-0x230-pasta-aspen-table/4999222
