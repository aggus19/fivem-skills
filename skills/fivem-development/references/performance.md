# Performance: measuring, budgets, threads, natives, network, NUI

Baseline: FXServer Legacy 35245/37150, Cfx Server (Enhanced) build 161, CfxLua 5.4, ox_lib 3.40 — verified 2026-10-07 against citizenfx/fivem source (master `a74c2cc`), docs.fivem.net and forum.cfx.re. Large servers, hardware, OneSync limits and streaming budgets: [performance-server-scaling.md](performance-server-scaling.md). Before/after code: [performance-cookbook.md](performance-cookbook.md).

## Contents
1. Measure first: resmon, profiler, server metrics
2. Budgets: what "good" looks like
3. Client threads and dynamic sleep
4. Event-driven design (points, zones, cache, state bags)
5. Natives: cost and per-frame-only natives
6. CfxLua 5.4 micro-optimizations that matter
7. JS / TS and NUI cost
8. Network: events, latent events, state bags, GlobalState
9. Server-side scripting
10. Memory leaks
11. USE vs AVOID
12. Standard good values
13. Checklist
14. Sources

## 1. Measure first

### Client: `resmon` (F8)
`resmon 1` opens it, `resmon 0` closes it (it is a bool convar). Columns (from `ResourceTimeWarnings.cpp`):

| Column | Meaning |
|---|---|
| Resource | Resource name; first row `[Total CPU]` = all script time per frame |
| CPU msec | Average **self** time per frame of this resource (time spent inside other resources it calls — exports, events — is excluded). Colour goes green → red between **1 ms and 8 ms** |
| Time % | Share of total script time |
| CPU (inclusive) | Self time **plus** time spent in resources it called (exports, triggered events) — a high inclusive / low self value means "my calls into X are expensive" |
| Memory | Script runtime heap (Lua: `collectgarbage('count')` equivalent), refreshed every 500 ms |
| Streaming | Memory of streamed assets belonging to the resource |

- **Automatic warning:** when a resource averages **> 6 ms** per frame the client shows "/!\ Resource time warning — X is taking N ms (or -N FPS @ 60 Hz)". Anything near this is a severe bug.
- Other client convars (all verified in source): `cl_drawFPS 1`, `cl_drawPerf 1`, `netgraph 1`, `strdbg 1` / `strlist 1` / `strmem 1` (streaming debug), `net_showPools 1` (game pool usage — useful for "pool full" crashes).
- `resmon` measures **script** time only. GPU cost of markers/NUI/lights is not shown — compare `cl_drawFPS` with the resource stopped.

### Profiler (client F8 and server console)
Exact subcommands (from `citizen-scripting-core/src/Profiler.cpp`):
```
profiler record <frames>      -- record N frames (500 is a good start client-side; server frames are 50 ms)
profiler record start         -- record until stopped
profiler record stop
profiler resource <name> [frames]   -- record only one resource
profiler status
profiler view [filename]      -- opens Chrome devtools (server: prints a link to open in Chrome)
profiler saveJSON <file.json> -- Chrome trace JSON; load in Chrome DevTools > Performance > "Load profile"
profiler save <file> / profiler load <file>   -- internal msgpack format
```
- Docs: "You also need google chrome installed"; keep the game/server running when viewing an unsaved profile.
- Read the flame chart for the resource's thread/event names; per-frame bars show which `CreateThread` body or handler is heavy.
- **Enhanced (Cfx Server):** the backend is **Perfetto**; commands stay `profiler record <duration>` and `profiler save <file>.json`; traces go to the `profiler/` folder of the install (Dev Update #3). Open them at https://ui.perfetto.dev.

### Server
- Console hitch warnings (source `GameServer.cpp`): `server thread hitch warning` (svMain, 20 Hz timer, warns > **150 ms**), `network thread hitch warning` (svNetwork, 100 Hz, > 150 ms), `sync thread hitch warning` (svSync/OneSync, 120 Hz timer, > **100 ms**). svMain hitches = your Lua/JS/C# (or sync I/O); svSync hitches = entity/population load.
- **Prometheus endpoint** `http://<ip>:30120/perf/` — Legacy exposes the `tickTime` histograms for `svMain`, `svNetwork`, `svSync` (Dev Update #3: "only exposed three metrics"); Enhanced exposes **80+** metrics. Protect it with `sv_prometheusBasicAuthUser` / `sv_prometheusBasicAuthPassword` (empty = open, rate-limited by `rateLimiter_http_perf` 2/s burst 5).
- **txAdmin** dashboard reads `/perf/` and draws the svMain/svSync/svNetwork tick-time histograms (5-minute snapshots, kept up to 96 h) plus FXServer memory and Node heap. A rising svMain p95 after a deploy points at the new resource.
- `profiler record 100` on the server console then `profiler view` → per-resource server ticks.
- Quick bisect: `stop <res>` / `ensure <res>` one at a time on a test server and watch resmon / svMain.

### Timing inside code
- Client: `GetGameTimer()` (ms) — **`os` and `io` libraries do not exist client-side** (only compiled `#ifdef IS_FXSERVER`). Use the profiler for sub-ms detail.
- Server: `os.nanotime()` / `os.microtime()` (CfxLua extensions), `os.clock()`.

## 2. Budgets
- 60 FPS = **16.6 ms per frame** for the game plus every resource. 144 FPS = 6.9 ms. Script time is pure overhead on top of the game.
- Per resource (community consensus, consistent with the warning threshold): idle **0.00–0.02 ms**, active (drawing, UI open) **< 0.10–0.20 ms**, frameworks/inventories under load < 0.5 ms. `[Total CPU]` for a whole RP server should stay well under 2 ms idle.
- Server svMain ticks every **50 ms**; all resources' work for that tick should take a few ms, never tens. Anything > 150 ms prints a hitch and delays every event for every player.
- A Lua thread sleeping in `Wait(n)` costs ~0 (scheduler bookmarks, C++ side). An empty JS `setTick` historically showed ~0.01–0.05 ms (JS ScRT has no bookmark scheduling — citizenfx/fivem#1653).

## 3. Client threads and dynamic sleep
- Never `while true do` without `Wait`. `Wait(0)` = every frame; only while drawing, reading per-frame input or calling `*ThisFrame` natives.
- `Wait(0)` resumes on the next frame, so cost scales with FPS (60 fps = 16.6 ms/tick, 180 fps = 5.5 ms). Per-frame work must use `Wait(0)`: `Wait(5)`/`Wait(10)` silently skips frames for high-FPS players. Everything else should use adaptive waits (>= 250-1000 ms when far). Source: https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/Citizen.Wait/
- **Dynamic sleep:** compute `sleep` per iteration (far → 1000–2000, near → 250–500, inside → 0).
- **One thread per concern**, iterating a table of points, instead of one thread per point/entity.
- Stop threads when not needed (flag checked each loop, or break and start a new one on enter).
- Spread heavy work across frames: process N items per frame and `Wait(0)` between batches.
- Prefer `RegisterKeyMapping` + `RegisterCommand` over polling `IsControlJustPressed` every frame for hotkeys (also user-rebindable).
- `SetTimeout(ms, fn)` for one-shot delays instead of a thread that waits once.
Code: [performance-cookbook.md §1–3](performance-cookbook.md).

## 4. Event-driven design
- **ox_lib `cache`** (client): `cache.ped`, `cache.vehicle`, `cache.seat`, `cache.weapon`, `cache.playerId`, `cache.serverId` — refreshed by one ox_lib thread every **100 ms**; `lib.onCache('vehicle', fn)` fires on change (event `ox_lib:cache:vehicle`). `cache.coords` is written only by the **points/zones** loop (every 300 ms) — don't rely on it unless you use `lib.points`/`lib.zones`.
- **`lib.points`**: one shared loop (`Wait(300)`, spatial grid) for all points of the resource; `onEnter`/`onExit`; `nearby` runs **every frame only while inside** (via an interval that is cleared when no point is near).
- **`lib.zones`** (sphere/box/poly): same 300 ms loop; `inside` every frame only while inside.
- **ox_target**: no per-frame markers at all — best for interactions.
- **State bag change handlers** (`AddStateBagChangeHandler`) instead of polling entity state; **net events** instead of server polling; `baseevents`/framework events (`QBCore:Client:OnPlayerLoaded`, `esx:playerLoaded`, `ox:playerLoaded`) instead of "wait until loaded" loops.
- `playerEnteredScope` / `playerLeftScope`: docs say "Using these events is frowned upon, these events have scaling performance costs" (called once per player in scope).

## 5. Natives
Each native call crosses the script ↔ game boundary (argument marshalling). Cheap ones (`PlayerPedId`, `GetEntityCoords`) are fine at 1–10 Hz but add up at 60 Hz × many threads.

**Expensive / scan-the-world** — throttle (≥ 500–1000 ms) or replace:
| Native | Why | Instead |
|---|---|---|
| `GetGamePool('CPed'/'CVehicle'/'CObject'/'CPickup')` | builds a table of every handle | scan every 1–2 s, cache, spread processing |
| `GetClosestObjectOfType`, `GetClosestVehicle`, `GetPedNearbyVehicles` | world searches | ox_target models, known handles, state bags |
| `StartExpensiveSynchronousShapeTestLosProbe` | blocks the frame | `StartShapeTestLosProbe` + `GetShapeTestResult` next frames |
| `GetDistanceBetweenCoords` | native call + 7 args | `#(a - b)` (vector math in Lua VM) |
| `GetHashKey('x')` in loops | string hash at runtime | backtick `` `x` `` (compile-time, zero overhead) |
| `GetActivePlayers()` + `GetPlayerPed` loop every frame | allocs + N natives | throttle to 500 ms |
| Model/anim requests in loops | streaming churn | `lib.requestModel`, then `SetModelAsNoLongerNeeded` |

- Don't store `PlayerPedId()` in a file-level local: the handle changes after `SetPlayerModel` (clothing/appearance menus, respawn scripts) and old references become invalid. Read it per use, or use ox_lib `cache.ped` (refreshed by ox_lib) / ESX `esx:playerPedChanged`. Source: https://docs.fivem.net/natives/?_0xD80958FC74E988A6 and https://docs.fivem.net/natives/?_0x00A1CADD00108836

**Per-frame-only natives** (effect lasts one frame — they legitimately need `Wait(0)`; batch them into **one** thread and only while needed):
`DrawMarker`, `DrawText`-family (`BeginTextCommandDisplayText`/`EndTextCommandDisplayText`), `DrawSprite`, `DrawLightWithRange`, `DisableControlAction`, `HideHudComponentThisFrame`, `SetPedDensityMultiplierThisFrame`, `SetVehicleDensityMultiplierThisFrame`, `SetRandomVehicleDensityMultiplierThisFrame`, `SetParkedVehicleDensityMultiplierThisFrame`, `SetScenarioPedDensityMultiplierThisFrame`, and `IsControlJustPressed/Released` polling.
- Population: prefer **server-side** control (`onesync_population false`, `SetRoutingBucketPopulationEnabled`) or `SetPedPopulationBudget`/`SetVehiclePopulationBudget` (set once) over five `*ThisFrame` calls in every resource. If you must use multipliers, have exactly one resource do it.

## 6. CfxLua 5.4 micro-optimizations that matter
Only in code that runs per frame or per entity × many; elsewhere favour clarity.
- **Locals beat globals**: natives are globals; `local GetEntityCoords = GetEntityCoords` at file top saves a hash lookup per call. Measurable only in hot loops.
- **Vectors are native types** in CfxLua: `#(a - b)`, `vec3(x,y,z)`; natives accept/return vectors. Don't unpack to x,y,z tables.
- **Backtick hashes** `` `prop_atm_01` `` are computed at compile time.
- **Avoid per-frame allocation**: no `{}` / closures / string building inside `Wait(0)` loops — reuse tables with `table.wipe(t)` (CfxLua; alias `table.clear`), preallocate with `table.create(narr, nhash)` (alias `table.new`), copy with `table.clone(t)`. These come from LuaGLM's `GRIT_POWER_WOW` flag, enabled in the FiveM build.
- **Strings**: build with `table.concat(parts)` instead of `..` in loops; `string.format` once, not per frame; compare hashes/ints instead of strings in hot paths.
- **`ipairs`/numeric `for i = 1, #t`** over arrays; keep arrays dense (msgpack `without_hole` also prefers it).
- **GC**: CfxLua uses the stock 5.4 incremental collector (runtime doesn't retune it). Don't call `collectgarbage('collect')` periodically (full stop-the-world pass, shows as spikes); use `collectgarbage('count')` (KB) to *watch* memory. Switching a resource to `collectgarbage('generational')` can reduce GC spikes for allocation-heavy code — **UNVERIFIED** benefit in FiveM; measure with the profiler before keeping it.
- `json.encode`/`msgpack` of big tables is O(size): never per frame; diff and send only changes.

## 7. JS / TS and NUI cost
- Client/server JS: prefer `setInterval`/`setTimeout` or awaiting a `Delay` inside one `setTick` that does real per-frame work; many idle `setTick`s cost more than idle Lua threads.
- **NUI (CEF) runs with V8 `--jitless` since 2026-10-07** (commit 38c47bc "tweak(cef/v8): disable JIT", `NUIApp.cpp`): all NUI JavaScript is interpreted. Consequences: heavy frameworks, big JSON parsing, per-frame React re-renders and charting libraries are several times slower; V8 jitless mode also disables WebAssembly. This applies to NUI only, not to the client JS scripting runtime.
- Visible NUI frames cost CPU + GPU compositing every frame. Hide the root (`display:none`) when closed, stop timers/animations, avoid `backdrop-filter`, big shadows, infinite CSS animations, video backgrounds on always-on HUDs.
- `SendNUIMessage` serializes to JSON and crosses into CEF: send **on change**, throttle HUD updates to 4–10 Hz, never every frame.
- Production builds only (minified, tree-shaken); local fonts/images; one NUI page per resource, not one per UI element. DUI (`CreateDui`) = a full browser instance each — destroy when unused.

## 8. Network
- **Client → server event limits** (source `ServerEventPacketHandler.cpp`, configurable `rateLimiter_<name>_rate/_burst`): `netEvent` **50/s, burst 200** (excess silently dropped); `netEventFlood` **75/s, burst 300** (excess → kick "Reliable network event overflow"); `netEventSize` **128 KiB/s, burst 384 KiB** (excess → kick "Reliable network event size overflow"). Design for ≤ a few events/s per player.
- **Client state bag writes**: `stateBag` 75/s burst 125, `stateBagFlood` 150/175, `stateBagSize` 128 KiB/s burst 256 KiB (kick "Reliable state bag packet overflow").
- **Latent events** for payloads of "multiple KBs and above": `TriggerLatentClientEvent(name, target, bps, ...)` / `TriggerLatentServerEvent(name, bps, ...)`. bps ≤ 0 → **25000** default; bps is per target (to `-1` = bps × players); ≥ ~10 000 000 bps "may lead to connectivity issues".
- `TriggerClientEvent(name, -1, ...)` sends to **every** player: with 500 players a 2 KB payload = 1 MB of upstream. Target players (by distance/job/bucket), or publish small values in state bags.
- **State bags**: server-set is replicated by default; entity bags reach only clients that have the entity in scope; player bags reach the owner plus players who have that player in scope (OneSync big mode, `ServerGameState.cpp`). Each get/set (de)serializes the whole value — use granular keys (`state['door:3'] = true`), not nested tables you rewrite. `set(key, value, false)` keeps a value server-only.
- **GlobalState** goes to every client including on join: keep it to small flags/counters, not inventories or lists.
- Never sync per-frame positions via events/state bags — entity sync already replicates movement.
- Enhanced: state bag handlers ~10× faster, sync over raw UDP, `sv_syncTickRate` (see scaling file).

## 9. Server-side scripting
- Never block svMain: no synchronous HTTP, no busy loops, no huge `json.decode` per tick, no `MySQL.*.await` for every player in one tick.
- Event handlers run on svMain: validate and return; offload heavy work to a thread that yields (`Wait(0)` between batches).
- Batch DB writes (dirty flag + flush every 5–15 min and on `playerDropped`/txAdmin shutdown event). oxmysql prints queries slower than `mysql_slow_query_warning` (default **200 ms**). Indexing, prepared statements, pool sizing: see `database-optimization.md` (owned separately) and [database-oxmysql.md](database-oxmysql.md).
- Iterate players on events (join/drop/job change) instead of `GetPlayers()` loops every second; keep a server-side table keyed by `source`.
- Delete what you create: track server entities; delete on `onResourceStop` and when the owner drops; `SetEntityOrphanMode` to control what happens when the owner leaves.
- Cache config/static data at start (don't re-read files/DB per request).

## 10. Memory leaks
- Symptom: resmon Memory column grows steadily over 30–60 min of normal play; txAdmin FXServer memory climbs until restart; "pool full" crashes (`net_showPools`).
- Common causes: tables keyed by `source`/entity never cleared on drop/delete; `AddEventHandler`/`AddStateBagChangeHandler` registered repeatedly (e.g. inside an event) without `RemoveEventHandler`/`RemoveStateBagChangeHandler`; entities/blips/DUIs/cams never deleted; `lib.points`/`zones` created repeatedly without `:remove()`; NUI JS arrays that only grow; caches without TTL.
- Diagnose: log `collectgarbage('count')` every minute per resource; compare before/after a scenario; restart one resource and see if memory drops.

## 11. USE vs AVOID
| USE | AVOID |
|---|---|
| ox_target / `lib.points` / `lib.zones` | Per-resource distance loops at `Wait(0)` |
| Dynamic sleep (1000 → 500 → 0) | `while true do Wait(0)` always |
| `cache.ped`, `lib.onCache('vehicle')` | `PlayerPedId()`/`GetVehiclePedIsIn` every frame in every resource |
| `#(a - b)` | `GetDistanceBetweenCoords` |
| Backtick hashes | `GetHashKey` in loops |
| `RegisterKeyMapping` commands | Polling `IsControlJustPressed` in 10 resources |
| Async shape tests | `StartExpensiveSynchronousShapeTestLosProbe` per frame |
| Scans every 1–2 s, cached | `GetGamePool` every frame |
| State bag change handlers, events | Polling server via callbacks every second |
| Latent events for big payloads | 100 KB `TriggerClientEvent(-1)` |
| Granular state bag keys | Rewriting a nested table bag at 10 Hz |
| Targeted `TriggerClientEvent` | Broadcast to `-1` for local effects |
| Dirty-flag batched DB saves | `UPDATE` on every money change |
| `table.wipe` reuse, `table.concat` | New tables/strings per frame |
| Server-side population control | Every resource calling density `*ThisFrame` |
| Hidden, idle NUI; on-change messages | Always-visible animated NUI, `SendNUIMessage` per frame |
| `profiler` + resmon before/after | Guessing, "optimized" claims without numbers |

## 12. Standard good values
| Setting | Value | Why |
|---|---|---|
| Idle thread sleep | 1000–2000 ms | Nothing to do; reaction time is still < 2 s |
| "Near" sleep | 250–500 ms | Player approaching; enough to enable drawing in time |
| Drawing / input sleep | 0 | Per-frame natives need every frame |
| Marker draw distance | 10–20 m | Markers invisible/useless further; enter at 20, exit at 25 (hysteresis) |
| Interaction distance | 1.5–2.5 m | Matches ox_target style reach |
| `lib.points` distance | 5–50 m | Loop is 300 ms; larger only for things that must preload |
| HUD / NUI updates | 4–10 Hz, on change | Human perception; JSON + CEF cost |
| Pool scans (`GetGamePool`) | every 1000–2000 ms | Scans allocate |
| Server periodic jobs | ≥ 1000 ms, staggered | svMain is 50 ms; avoid all jobs on the same tick |
| Autosave | 5–15 min + on drop | DB load vs data-loss window |
| Client → server events | ≤ 5/s sustained per player | Hard limit 50/s, kick above flood |
| State bag writes | ≤ 1–2/s per key, only on change | Every write replicates to all in scope |
| Latent bps | 25 000 default; 50 000–200 000 for MB-size | Higher can stall the connection |
| resmon target | idle ≤ 0.02 ms, active ≤ 0.1–0.2 ms | 6 ms triggers the client warning |
| Slow query threshold | 200 ms (oxmysql default), aim < 50 ms | Hot queries must be indexed |
| Entity culling radius | 424 (default; don't change) | Culling natives deprecated |
| Enhanced `sv_syncTickRate` | 60 default; up to 120 only with spare CPU | Higher = lower latency, more CPU |
More server/streaming values: [performance-server-scaling.md §9](performance-server-scaling.md).

## 13. Checklist
- [ ] Measured with resmon/profiler before and after; numbers reported.
- [ ] Resource idle ≤ 0.02 ms client; no thread at `Wait(0)` while idle.
- [ ] Interactions via ox_target / `lib.points` / `lib.zones`; keybinds via `RegisterKeyMapping`.
- [ ] No per-frame `GetHashKey`, `GetDistanceBetweenCoords`, pool scans, sync shape tests, table/string creation.
- [ ] Per-frame natives only while needed, in one thread.
- [ ] No events > a few/s per player; big payloads latent; no large broadcasts; GlobalState small.
- [ ] Server: no hitch warnings under load; DB writes batched; slow-query log clean.
- [ ] NUI hidden and idle when closed; messages on change only; production build.
- [ ] Entities, blips, handlers, points cleaned up on `onResourceStop` and player drop.
- [ ] Memory flat over a 30-minute session.

## 14. Sources
- citizenfx/fivem source (master a74c2cc, 2026-10-07): `code/components/citizen-devtools/src/ResourceTimeWarnings.cpp`, `ResourceMonitor.cpp`, `citizen-scripting-core/src/Profiler.cpp`, `citizen-server-impl/src/GameServer.cpp`, `PerfHttpHandler.cpp`, `packethandlers/ServerEventPacketHandler.cpp`, `StateBagPacketHandler.cpp`, `citizen-scripting-lua/src/LuaScriptRuntime.cpp`, `LuaOS.cpp`, `nui-core/src/NUIApp.cpp` — https://github.com/citizenfx/fivem
- CEF JIT disabled: https://github.com/citizenfx/fivem/commit/38c47bc (PR #4252)
- CfxLua table extensions: https://github.com/citizenfx/lua (branch `luaglm-548`, `ltablib.c`) and `code/vendor/lua.lua` defines
- Profiler: https://docs.fivem.net/docs/scripting-manual/debugging/using-profiler/
- Server commands, rate limiters, Prometheus auth: https://docs.fivem.net/docs/server-manual/server-commands/
- Latent events: https://docs.fivem.net/docs/scripting-manual/working-with-events/triggering-events/
- State bags: https://docs.fivem.net/docs/scripting-manual/networking/state-bags/
- OneSync (scope events, culling): https://docs.fivem.net/docs/scripting-reference/onesync/
- Lua runtime (vectors, backtick hashes): https://docs.fivem.net/docs/scripting-manual/runtimes/lua/
- Enhanced differences: https://docs.fivem.net/docs/developers/legacy-vs-enhanced/ · Dev Update #3 (Perfetto, metrics): https://forum.cfx.re/t/development-update-3-fivem-for-gtav-enhanced/5415045
- JS setTick cost: https://forum.cfx.re/t/javascripts-settick-is-much-slower-than-luas-citizen-createthread/4920326
- ox_lib cache/points/zones source: https://github.com/overextended/ox_lib (`resource/cache/client.lua`, `imports/points/client.lua`, `imports/zones/shared.lua`)
- txAdmin perf collection: https://github.com/citizenfx/txAdmin (`core/modules/Metrics/svRuntime/`)
- oxmysql convars: https://github.com/overextended/oxmysql (`src/config.ts`)
