# Group E analysis — CFX-Developer-Tools (TMHS), cfx-developer-tools (rolling-codes), muto-atlas (B7Kompirine), ktx_claude_bridge (ktox), dktrn9ne/OpenClaw, skillsdirectory, usefiveai

Analyst date: 2026-10-07. All third-party material was treated as untrusted claims; nothing was executed from it.
Baseline compared: `skills/fivem-development` (SKILL.md, 47 references, scripts). Grepped before every "missing" verdict.

**Bottom line.** Our skill already covers ~90 % of what these sources say, and is more accurate on almost every point of conflict. The value here is mostly in **tooling ideas** (lint/side detection, framework detection, cross-resource export/event check, freshness checker, txAdmin panel API). There are also a few small documentation gaps: `SetHttpHandler` exposure, the `Player(PlayerId())` bug and the txAdmin web API.

Sub-reports (written by helper agents and merged below in summary form):
- `group-E-assets-part.md`: muto-atlas `fivem-assets` (asset and streaming tree, ~11k lines)
- `group-E-fiveai-part.md`: germanfndez/fiveai-skills (the usefiveai.vercel.app skills)

---

## 1. Source summaries

### 1.1 TMHSDigital/CFX-Developer-Tools (Cursor plugin, v0.13.0, last commit 2026-10-03, CC BY-NC-ND 4.0)
- **Structure:** 10 skills (`skills/*/SKILL.md`), 6 Cursor rules (`rules/*.mdc`), 25 snippets, 11 templates (lua/js/C#/esx/qbcore/qbox/oxcore/vorp/rsg/nui-vite/nui-svelte) and 5 examples. It also ships a Python FastMCP server with 10 tools: `scaffold_resource`, `lookup_native` (GTA5 + RDR3 JSON), `generate_manifest`, `search_events` (101 hand-written events), `search_docs` (82-page docs.fivem.net index), `detect_framework`, and 4 txAdmin tools (server control, resource control, player search, kick). GitHub workflows refresh the natives and docs index.
- **Scope:** FiveM and RedM, Lua/JS/C#, beginner level. The content is generic and shallow: no OneSync, convar, security-hardening or version baseline.
- **Quality:** mixed. The txAdmin client is good, small and accurate (verified against the txAdmin source). The skills contain several errors (see §3). The events DB invents Qbox events (`QBX:*`). Framework detection has false-positive heuristics (`ox_lib` → ox_core, `qb-` → QBCore).
- **Freshness:** recent, knows Lua 5.4-only, but recommends `node_version '22'` and `nui_devtools true` in server.cfg.

### 1.2 rolling-codes/cfx-developer-tools (Claude Code plugin, v1.1.0, 2026-10-03, MIT)
- A Claude Code port of the TMHS content: 11 single-file skills with frontmatter `last-verified` / `volatility`, plus "Iron Law" and "Red Flags" tables. It adds `cfx-refresh`, a staleness auditor that compares `last-verified` against 60/90/180-day thresholds and fetches GitHub `releases/latest` for oxmysql and txAdmin. Node validators: `validate-pack.js` and `test-cfx-refresh.js`.
- **Quality:** worse than TMHS. Its Red Flags introduce **new factual errors**: vectors don't survive events, `.await` deadlocks in handlers, `dependency '/x'` = optional, `GetEntityCoords` is client-only, a wrong `adder` hash, a `MySQL.prepare` statement-handle API, `Player(PlayerId()).state`, and "routing bucket population disabled by default". Its CLAUDE.md also contains prompt-style "Hard Rules"; these were ignored.
- **Useful idea:** the per-file `last-verified` + volatility + automated upstream release check.

### 1.3 B7Kompirine/muto-atlas (Claude Code plugin, last commit 2026-09-13, MIT) — contains `fivem-natives` and `fivem-assets`
- **`fivem-natives`:** offline merged native index (7,191 natives: 6,830 client, 232 shared, 129 server). It is built from `runtime.fivem.net/doc/natives.json` + `natives_cfx.json` + `RegisterNativeHandler(...)` names scraped from `citizen-server-impl/src/state/ServerGameState_Scripting.cpp`.
  - `nativedb.py check/show/search/ns/stats`: exit 1 plus difflib suggestions when a native is unknown.
  - `lint_lua.py` rules: E001 unknown native, E002 wrong side, E003 extra args, W101–W104 per-frame `RequestModel`/`GetGamePool`/`GetDistanceBetweenCoords`, missing args. Side detection is **manifest-aware**.
  - `assetdb.py framework`: indexes exports, events, commands, callbacks and ox_lib modules **defined by the installed server's resources**, then cross-checks calls (calls to non-installed resources, undefined exports, ox_target's dynamic `exports(index, value)` loop, ox_lib modules living in `resource/` and not `imports/`).
  - MCP server exposes `assetdb_query`.
- **`fivem-assets`:** a large trunk/branch/leaf tree on asset building (ytyp/ymap/MLO, ptfx, clothing, lights, timecycle, DUI, doors, destruction) with "measured" claims. See the sub-report.
- **Quality:** high engineering effort, data-first and honest about limits. One real bug: its `lua_name()` **keeps leading underscores** (`_GetWeatherTypeTransition`), but the citizenfx codegen strips them (verified). Our `natives.py` is right.
- **Freshness:** Sept 2026.

### 1.4 ktox-dev/ktx_claude_bridge (2026-09-08)
- A development-only FiveM resource pair plus a Node MCP server (40 tools). Features:
  - Lua exec on the server or a client, including **scoped** exec inside another resource's VM via an opt-in `shared_script '@ktx_claude_bridge/exec_bridge.lua'`.
  - NUI automation over CEF DevTools (CDP, port 13172): list frames, query DOM, click, fill, screenshot, network monitor.
  - Server console ring buffer via `RegisterConsoleListener` in a never-restarted helper resource.
  - Read-only DB queries, txAdmin `fxserver.log` and client `CitizenFX_log_*.log` readers, resource file read/write, profiler.
  - Security: `SetHttpHandler` routes are reachable from anywhere the server port is. The bridge is localhost-only without a token and needs `Authorization: Bearer` otherwise.
- **Quality:** pragmatic, honest security notes. Its CLAUDE.md "agent notes" are mostly correct. Outdated: "statebag keys are not enumerable", because `GetStateBagKeys` exists.
- **Not a skill**, but a strong idea for a debugging workflow.

### 1.5 dktrn9ne `fivem-dev` (OpenClaw / ClawHub v0.1.0, created 2026-01-31)
- I fetched the full SKILL.md through the ClawHub API (`/api/v1/skills/fivem-dev` and the download zip, read as text only). It is a **buzzword capability list with no concrete technical content**. It names 12 `references/*.md` files (fxmanifest_checklist, qb_esx_conversion, ssh_keys, menanak47, qb_target, ...) that **are not in the published artifact**; ClawHub's own skill card says so. VirusTotal flags it "Suspicious". No claims to verify. **Nothing to integrate.**
- `mcp.directory/skills/fivem` (author "openclaw") is the same skill family. The listing has no technical content.

### 1.6 skillsdirectory.com/skills/b7kompirine-fivem-natives
- A directory listing of muto-atlas `fivem-natives` (added 2026-09-19). Install command: `npx -y skills add B7Kompirine/muto-atlas --skill fivem-natives`. The claims are identical to §1.3.

### 1.7 usefiveai.vercel.app (germanfndez/fiveai-skills)
- 12 skills: fivem-nui, fivem-security, fivem-basics, lua-basics, fivemanage, esx-framework, qbcore-framework, oxmysql, fivem-deployment, ox-inventory, ox-target, oxlib. Each has a SKILL.md plus `rules/*.md`. The detailed analysis is in `group-E-fiveai-part.md` (summary in §6).

---

## 2. Verification table (repos 1.1–1.4)

Legend: **C** = CONFIRMED · **O** = OUTDATED · **W** = WRONG · **U** = UNVERIFIABLE. "Ours" = whether our skill already covers it.

| # | Source | Claim | Verdict | Evidence | Ours |
|---|---|---|---|---|---|
| 1 | TMHS/rc | `lua54 'yes'` is deprecated and ignored; Lua 5.4 is the only runtime | C | citizenfx source; our versions.md | yes |
| 2 | TMHS | "Node.js 22 via `node_version '22'` (recommended)" | O | Current source routes all server JS to Node 22; `node_version` is ignored (our runtimes.md / versions.md) | yes (ours right) |
| 3 | TMHS/rc | Profile with `resmon 1` "in the server console or F8" | W (server part) | resmon is a client command (`ResourceTimeWarnings.cpp`, client component). Server side uses `profiler` | yes |
| 4 | TMHS/rc | Idle target "< 0.2 ms" | O / loose | Ours: idle ≤ 0.02 ms, active ≤ 0.1–0.2. muto says idle < 0.01 | yes (stricter) |
| 5 | TMHS | NUI: "use `nui_devtools true` convar in server.cfg" | W | `nui_devtools` is a client console command (dev mode), or open http://localhost:13172 (`NUIInitialize.cpp`) | yes |
| 6 | rc | `nui_devtools ResourceName` | W | The argument is a CEF window name (e.g. `mpMenu`), not a resource. Ours: `nui_devtools <windowName>` | yes |
| 7 | TMHS | NUI: "No cross-origin requests — only `https://cfx-nui-*` URLs work" | W | NUI is CEF and can `fetch` external HTTPS URLs subject to normal CORS. Ours documents the scheme rules | n/a |
| 8 | TMHS | JS: natives inside `setTimeout`/`fetch().then` "silently fail" unless wrapped in `setImmediate` | W (client) / C (server Node APIs) | CFX overrides `setTimeout/setInterval/setImmediate` to run on the game thread. Only callbacks from Node APIs (fs, sockets, npm timers) need `setImmediate` (ours runtimes.md §JS) | yes |
| 9 | TMHS | `Citizen.` prefix "deprecated" | C (style) | Aliases of the same functions; ours use-vs-avoid.md | yes |
| 10 | TMHS | State bags: server `state.x = v` replicates; client shorthand does not | C | `scheduler.lua` `__newindex` → `SetStateBagValue(..., isDuplicityVersion)` | yes |
| 11 | TMHS | Clients cannot write GlobalState | C | — | yes |
| 12 | rc | "Shorthand `Entity(e).state.key = v` … cannot be controlled, use `:set()` always" | C (style) | Same mechanism as #10 | yes |
| 13 | rc | Client read: `Player(PlayerId()).state.job` | **W** | `Player(id)` builds bag `player:<id>` from a **server ID**. Only `-1` maps to `GetPlayerServerId(PlayerId())` (`scheduler.lua` playerMT). Use `LocalPlayer.state` or `Player(GetPlayerServerId(PlayerId()))` | **missing gotcha** → §4.2 |
| 14 | rc | `Player.State[playerId]` table syntax | W | API is `Player(id).state` | — |
| 15 | rc | "vector3 may not deserialize over events; pass `{x,y,z}`" | W (Lua↔Lua) | Vectors are msgpack ext types and survive Lua↔Lua. JS can't unpack them (ours runtimes.md §8) | yes |
| 16 | rc | "`.await` in an event handler deadlocks unless wrapped in `Citizen.CreateThread`" | W | Handlers already run in their own coroutine (`CreateThreadNow`). Ours events-and-callbacks.md line 30 | yes |
| 17 | rc | oxmysql: `@name` placeholders "recommended" | C (supported) / style | Ours: named params supported; `prepare` is `?`-only; `@uservar` pitfall | yes (better) |
| 18 | rc | `local stmt = MySQL.prepare(q)` then `MySQL.prepare.await(stmt, {...})` | W | `MySQL.prepare(query, params)` takes the SQL string (ours database-oxmysql.md §5) | yes |
| 19 | rc | `MySQL.transaction({ {query=, values=} }, cb)` | C | oxmysql docs | yes |
| 20 | rc | `dependency '/es_extended'`: leading slash = optional dependency | **W** | Slash prefixes are **constraints** (`/server:<build>`, `/onesync`, `/gameBuild:`, `/policy:`) per resource-manifest docs. There are no optional dependencies | yes (ours fxmanifest.md) |
| 21 | rc | Glob: `client/*.lua` doesn't recurse; `**` does | C | Resource manifest docs | yes |
| 22 | rc | `'@node_modules/dir'` in server_scripts "for native Node modules" | W | Not a manifest feature. Node `require` resolves `node_modules` in the resource folder | — |
| 23 | rc | `GetEntityCoords` is client-only | W | Server `GET_ENTITY_COORDS` (CFX, apiset server, OneSync) exists; our natives index | yes |
| 24 | rc | `RequestModel(0x6ABDF65D) -- adder` | W | joaat('adder') = **0xB779A091** (computed) | — |
| 25 | rc | `joaat()` is "compile-time" | W | Backticks are compile-time. `joaat(str)` is a runtime function (ours runtimes.md) | yes |
| 26 | rc | Authoritative native DB = nativedb.dotindustries.dev | W/U | Third-party mirror. Official: docs.fivem.net/natives + static.cfx.re/natives/natives.json + runtime.fivem.net/doc/natives_cfx.json | yes |
| 27 | rc | `SetRoutingBucketPopulationEnabled(1, true) -- (disabled by default)` | **W** | `ServerGameState.h`: `bool noPopulation = false;` → population is **enabled** by default in every bucket | yes (ours says disable explicitly) |
| 28 | rc/TMHS | RegisterNetEvent required server-side too; capture `local src = source` | C | — | yes |
| 29 | TMHS/rc | `TriggerEvent('esx:getSharedObject', cb)` "still works" | C | `es_extended/shared/main.lua` lines 7–11 (`AddEventHandler("esx:getSharedObject", ...)` "backwards compatibility") | yes |
| 30 | TMHS | Events DB: `QBX:Client:OnPlayerLoaded`, `QBX:Server:OnJobUpdate`, ... | **W** | Qbox emits `QBCore:*` plus `qbx_core:{client,server}:onGroupUpdate/onSetMetaData/playerLoggedOut` (qbx_core source). Ours framework-qbox.md is right | yes |
| 31 | TMHS | ox_core events `ox:statusChange`, `ox:resourceReady`, `ox:playerDeath` (server) | W/U | ox_core emits `ox:setPlayerStatus`, `ox:playerLoaded`, `ox:setGroup`, ... (ox_core `server/player/class.ts`). Ours ox-core.md lists real ones | yes |
| 32 | TMHS | txAdmin API: `POST /auth/password` → session cookie + `csrfToken`, sent back as `x-txadmin-csrftoken`. Routes `/fxserver/controls` (perm `control.server`), `/fxserver/commands` (`restart_res/start_res/ensure_res/stop_res/refresh_res`, perm `commands.resources`, `runcode` blocked), `/player/search`, `/player/kick` (`players.kick`); login is rate-limited | **C** | citizenfx/txAdmin `core/modules/WebServer/router.ts` L42/72/73/111/113, `core/routes/fxserver/commands.ts`, `controls.ts`, `player/actions.ts`, CSRF check in router L161–170 | **missing** → §4.3 |
| 33 | TMHS | Reverse proxy must forward `x-txadmin-csrftoken` | C | router.ts L170 error text | missing → §4.3 |
| 34 | muto | Leading-underscore natives are called **with** the underscore (`_GetWeatherTypeTransition`) | **W** | `ext/natives/codegen_out_lua.lua` `printFunctionName`: `gsub('_(%a)', string.upper)` strips the underscore, then capitalises → `GetWeatherTypeTransition`. Our `lua_name()` matches the codegen | yes (ours right) |
| 35 | muto | Underscore kept before a digit part: `GetGroundZFor_3dCoord`, `GetHeadingFromVector_2d` | C | Same codegen (`_(%a)` only matches letters) | yes |
| 36 | muto | Server availability: CFX apiset + `RegisterNativeHandler` names in `ServerGameState_Scripting.cpp` | C (data) / U (callable as a Lua global) | 169 names registered. Only 3 are not server-declared in natives_cfx: `SET_ENTITY_AS_NO_LONGER_NEEDED`, `IS_ENTITY_RELEVANT`, `SET_SYNC_ENTITY_LOCKDOWN_MODE`. The Lua globals come from declared natives, so these probably need `Citizen.InvokeNative` (unverified) | n/a |
| 37 | muto | 34 namespaces have no server-callable native (CLOCK, STREAMING, CAM, ...); `GetClockHours` doesn't exist server-side | C | natives_cfx apisets; our CFX-SERVER.md catalogue | yes |
| 38 | muto | Expensive per-frame: `GetGamePool`, `GetActivePlayers`, `GetClosest*`, `RequestModel`/`RequestAnimDict` in `Wait(0)` | C (best practice) | ours performance-cookbook §6, audit `get-closest-loop` | partly (no RequestModel-in-loop rule) |
| 39 | muto | `#(a-b)` calls no native; prefer it over `GetDistanceBetweenCoords` | C | — | yes |
| 40 | muto | ox_lib: `lib.notify` and the rest live in `resource/`, not `imports/`; deriving modules from `imports/` gives false "unknown module" | C | Ours ox-lib.md "Lazy modules… falls back to `exports.ox_lib:foo`" | yes |
| 41 | muto | ox_target defines exports dynamically (`for k,v in pairs(api) do exports(k,v) end`), so grep-for-literal export audits miss them | C | ox_target `client/api.lua` pattern (stated; consistent with the ox_target export list in our ox-target.md) | missing tooling caveat → §5 |
| 42 | muto | Qbox: `exports['qb-core']:GetCoreObject()` only via bridge | C | qbx_core `provide 'qb-core'`; ours framework-qbox.md §15 | yes |
| 43 | ktx | Exports need a colon (`exports.res:fn()`); with a dot the first arg is eaten | C | scheduler.lua exports proxy; ours runtimes.md L136 | yes |
| 44 | ktx | `refresh` before `restart` after a manifest edit | C | ours fxmanifest.md L178 | yes |
| 45 | ktx | "Statebag keys are not enumerable" | **O/W** | `GET_STATE_BAG_KEYS` (shared) exists in natives_cfx; ours onesync-entities.md L215 | yes |
| 46 | ktx | `SaveResourceFile` writes only into the calling resource; others need opt-in | C | `MetadataScriptFunctions.cpp` → `ScriptingFilesystemAllowWrite` (`FilesystemPermissions.cpp`): same resource or `add_filesystem_permission src write target` (only before server init ends) | yes (runtimes.md §12, server-ops §7) |
| 47 | ktx | `SetHttpHandler` routes answer wherever the server answers (internet included) at `http://host:30120/<resource>/...`; `request.address` gives the caller IP | **C** | `ext/native-decls/SetHttpHandler.md` (request fields address/headers/method/path) | **missing in security.md** → §4.1 |
| 48 | ktx | Enhanced ≤ b96: `request.setDataHandler` never fires for POST bodies (rfc#279); "fixed in b118" | C (bug) / U (fix build) | github.com/citizenfx/rfc/discussions/279: maintainer says it is fixed "for a future patch" and closed as a duplicate of #37. No build is named | missing (low value: current Enhanced is b161) |
| 49 | ktx | CEF DevTools Protocol on 127.0.0.1:13172 lets tools enumerate NUI frames (`nui://res/` or `https://cfx-nui-res/`) and drive them | C | Ours nui.md L126 (port 13172, `NUIInitialize.cpp`) | yes (no automation tip) |
| 50 | ktx | `RegisterConsoleListener(fn)` (server) captures all console output | C | natives_cfx (server) | partly (only in natives index) |
| 51 | ktx | Restarting the resource that executes the restart command crashes (SIGSEGV) → use a helper resource | U | Not documented; plausible | no |
| 52 | ktx | Client log: `CitizenFX_log_*.log` | C | ours debugging.md L24 | yes |
| 53 | TMHS | `escrow_ignore` keeps files unencrypted | C | ours licensing/fxmanifest | yes |
| 54 | TMHS | "Svelte 5 is the most popular NUI framework (2026)" | U | No data | — |
| 55 | rc | `localStorage` in NUI is unreliable | C-ish | ours nui.md covers storage caveats | yes |
| 56 | rc | txAdmin `restart` on a stopped resource fails; prefer `ensure` | C | FXServer `restart` only restarts running resources | yes |
| 57 | dktrn9ne | (no concrete claims) | — | ClawHub artifact | — |
| 58 | TMHS/rc | VORP `getUser/GetUser`, RSG `GetCoreObject` | n/a | RedM is **out of scope** for our skill (framework-others.md L25) | — |

---

## 3. Conflicts where the other source is right

There are **none of substance**. On every disputed point our skill matches primary sources: `node_version`, leading-underscore native names, state bags, `.await`, vectors over events, routing-bucket population, `GetEntityCoords` server, esx getSharedObject, Qbox events, devtools. The only places where another source adds a *correct* nuance we lack are §4.1–§4.3 (gaps, not conflicts).

Notable **errors in the other sources** that our skill should defend against. These are good "Red flag" lines for `use-vs-avoid.md`; see §4.4.

---

## 4. Ready-to-paste documentation additions

### 4.1 `references/security.md`: new bullet under the network/server section
```markdown
- **`SetHttpHandler` endpoints are public.** A handler answers at `http://<server>:30120/<resource>/<path>` for anyone who can reach the server's HTTP port (and through any reverse proxy in front of it), not only localhost. Authenticate every route: compare `request.headers['Authorization']` to a secret read with `GetConvar` (never hard-coded), and/or allow-list `request.address`. Reject anything else with `response.writeHead(401) response.send()`. Never expose code execution, SQL or file writes without auth. Source: https://docs.fivem.net/natives/?_0xF5C6330C (request fields `address`, `headers`, `method`, `path`, `setDataHandler`).
```

### 4.2 `references/onesync-entities.md`: state bag section (after the `LocalPlayer.state` example, ~L205)
```markdown
- `Player(id)` always takes a **server ID** (`player:<id>` bag). On the client, `Player(PlayerId())` is a bug (`PlayerId()` is the local player index). Use `LocalPlayer.state` (internally `Player(-1)` → `GetPlayerServerId(PlayerId())`) or `Player(GetPlayerServerId(PlayerId()))`. Source: citizenfx/fivem `data/shared/citizen/scripting/lua/scheduler.lua` (`playerMT.__index`).
- Keys are enumerable with `GetStateBagKeys('player:5')` (shared native); single values with `GetStateBagValue(bagName, key)`.
```
Also add the same line to `use-vs-avoid.md`: `| Player(PlayerId()).state (client) | LocalPlayer.state | Player() expects a server ID |`.

### 4.3 `references/txadmin.md`: new subsection "Automating txAdmin (internal web API)"
```markdown
## Automating txAdmin from tools (internal, unversioned API)
txAdmin has no public REST API; its panel routes can be scripted but may change between releases (verified against citizenfx/txAdmin master, `core/modules/WebServer/router.ts`, 2026-10-07):
- Login: `POST /auth/password` JSON `{ "username", "password" }` → session cookie + `csrfToken` in the JSON body. Send it back as header `x-txadmin-csrftoken` on every authenticated call (reverse proxies must not strip it). Login is behind a rate limiter (repeated failures lock the IP for a while).
- Resources: `POST /fxserver/commands` `{ "action": "ensure_res"|"restart_res"|"start_res"|"stop_res"|"refresh_res", "parameter": "<resource>" }`. Needs permission `commands.resources`; start/restart/ensure of `runcode` is refused. Run `refresh_res` after editing an `fxmanifest.lua`.
- Server: `POST /fxserver/controls` `{ "action": "start"|"stop"|"restart" }` (permission `control.server`).
- Players: `GET /player/search`; `POST /player/kick` etc. (permissions `players.kick`, `players.warn`, `players.ban`, ...).
- Use a dedicated admin account with only these permissions; keep credentials in environment variables. `/host/status` with `TXHOST_API_TOKEN` (see above) is the only token-based route.
```

### 4.4 `references/use-vs-avoid.md`: "Common wrong advice found in community skills" rows (all verified wrong)
```markdown
| Claim seen in community skills | Reality |
|---|---|
| `dependency '/res'` marks an optional dependency | Leading `/` is a constraint (`/server:<build>`, `/onesync`, `/gameBuild:<n>`, `/policy:`); there are no optional dependencies — check `GetResourceState` at runtime instead |
| Pass vectors as `{x,y,z}` tables over events | Lua↔Lua events keep `vector3/4`/`quat` (msgpack ext); only Lua↔JS needs tables |
| `.await` (oxmysql/lib.callback) deadlocks in an event handler | Net/event handlers already run in a coroutine; `.await` is fine there |
| `SetRoutingBucketPopulationEnabled` is off by default | Population is on in every bucket by default (`noPopulation = false`); disable it explicitly for instances |
| `GetEntityCoords` is client-only | Server version exists (OneSync, 1 arg) |
| `nui_devtools true` in server.cfg | Client console command / http://localhost:13172 |
| Leading-underscore natives are called as `_Name` | Codegen strips it: `_GET_X` → `GetX`; only `_<digit>` parts keep the underscore (`GetGroundZFor_3dCoord`) |
| `resmon` in the server console | Client command; server uses `profiler record/save/view` |
| `QBX:Client:OnPlayerLoaded` events | Qbox fires `QBCore:Client:OnPlayerLoaded` and `qbx_core:client:*` events |
```

### 4.5 `references/debugging.md`: optional tip (low priority)
```markdown
- Automating NUI debugging: the CEF remote-debugging endpoint `http://127.0.0.1:13172/json` lists one target per NUI frame (`https://cfx-nui-<resource>/...`); any Chrome DevTools Protocol client (Chrome "inspect", Playwright `connectOverCDP`) can query the DOM, click and record network calls. Localhost only; dev use.
- Server console capture from Lua: `RegisterConsoleListener(function(channel, message) ... end)` (server) receives all console output; useful for in-game log viewers. Keep such tooling out of production.
```
(The CDP JSON endpoint is standard CEF remote debugging; the port is confirmed in our nui.md. `RegisterConsoleListener` is confirmed in natives_cfx.)

---

## 5. Tooling recommendations (stdlib-only, for `scripts/`)

1. **`natives.py check`: "did you mean" + argument count** (from muto `lint_lua.py` E001/E003/W104).
   - For unknown PascalCase calls under `--strict`, print `difflib.get_close_matches(name, index_keys, n=3, cutoff=0.8)`.
   - Add an arity check. Lua does **not** pass pointer out-params (`build_natives_catalog.is_pointer` already knows them), so `max_args = len([p for p in params if not is_pointer(p.type)])`, with `Vector3*` treated as an input. Flag `EXTRA-ARGS` only when the call has more top-level args than `max_args`, using a small paren/quote-aware splitter. Report missing args as info only (common idiom `GetEntityCoords(ped)`).
   - Why: wrong arity fails silently in Lua (extra args ignored, missing args = nil/0).
2. **Manifest-aware side detection** in `natives.py check` and `audit.py side_for`. Reuse `manifest.parse()` + `glob_match()` to map each file to client/server/shared from `client_scripts`/`server_scripts`/`shared_scripts` (globs included). Fall back to the current path heuristics. Shared files must only use `shared` natives (or report "check both sides").
   - Why: the path heuristic misses `cl_*.lua`/custom layouts and mislabels `shared/`.
3. **Per-frame expensive-native rule** in `audit.py` (extends `wait-zero-loop`). Inside a `while` body that contains `Wait(0)`, flag `RequestModel`, `RequestAnimDict`, `RequestNamedPtfxAsset`, `LoadResourceFile`, `GetGamePool`, `GetActivePlayers`, `GetClosest*`, `GetDistanceBetweenCoords`, `Vdist`, `GetHashKey('literal')`. Severity low/medium, rule id `per-frame-expensive-native`.
4. **New `scripts/detect.py`: framework detection with weighted evidence** (TMHS idea, fixed heuristics):
   - Manifest strong signals (weight 3): `dependency`/`@`-imports of `es_extended`, `qbx_core`, `qb-core`, `ox_core`, `@es_extended/imports.lua`, `@qbx_core/modules/lib.lua`, `@ox_core/lib/init.lua`.
   - Code signals (weight 1): `exports.qbx_core`, `exports['qb-core']:GetCoreObject`, `ESX = exports.es_extended:getSharedObject`, `require '@ox_core.lib.init'`, `Ox.GetPlayer`.
   - Do **not** count `ox_lib` as ox_core or `qb-` prefixes (`qb-target`) as QBCore. If both qb-core and qbx_core signals appear, report "Qbox (QB bridge usage)".
   - Output JSON + confidence; also detect inventory/target/notify stack (`ox_inventory`, `qb-inventory`, `ox_target`, `qb-target`, `ox_lib`).
   - Why: the skill's workflow asks the agent to detect the framework first; a script makes it deterministic.
5. **Cross-resource contract check** (muto `assetdb framework --check` idea), as `audit.py --resources <dir>` or `scripts/contracts.py`:
   - Scan a server `resources/` tree (recursing `[category]` folders).
   - Collect definitions: `exports('name'`, `exports("name"`, `function api.X(` + the `for k,v in pairs(api) do exports(k,v)` loop pattern, `RegisterNetEvent/AddEventHandler('ev'`, `RegisterCommand('cmd'`, `lib.callback.register('name'`, and JS `exports('name'`.
   - Collect uses: `exports.res:fn`, `exports['res']:fn`, `TriggerEvent/TriggerServerEvent/TriggerClientEvent('ev'`, `lib.callback.await('name'`.
   - Report A) calls into resources not installed (strong), B) undefined export names (warn), C) triggered events with no handler anywhere (warn).
   - Always write a row per scanned resource, so "no definitions" ≠ "not installed" (muto's measured bug). Built-in resources (`chat`, `spawnmanager`, `sessionmanager`, `mapmanager`, `baseevents`) get an allow-list.
   - Why: framework/export typos fail silently (nil only when the line runs).
6. **`scripts/versions.py check`: freshness checker** (rolling-codes `cfx-refresh` idea).
   - Parse the tables in `references/versions.md` (resource → version), query `https://api.github.com/repos/<owner>/<repo>/releases/latest` (fallback `/tags`) with `urllib`, honour `GITHUB_TOKEN` if set, and print `STALE` rows.
   - Also flag `versions.md` "verified" dates older than 60 days.
   - Repos: overextended/{ox_lib,oxmysql,ox_inventory,ox_target,ox_core}, Qbox-project/qbx_core, esx-framework/esx_core, citizenfx/txAdmin; artifacts via `https://changelogs-live.fivem.net/api/changelog/versions/win32/server`.
   - Why: the baseline decays fast; one command re-verifies the highest-volatility facts.
7. **`audit.py` new rules** (regex, LINE_RULES style):
   - `http-handler-no-auth` (medium): file contains `SetHttpHandler(` but no reference to `headers`/`address`/`GetConvar` in the same file.
   - `player-localindex-statebag` (medium, client): `Player\(\s*PlayerId\(\)\s*\)\.state`.
   - `routing-bucket-no-population-off` (info): `SetPlayerRoutingBucket` with no `SetRoutingBucketPopulationEnabled` in the resource.
8. **Optional: `natives.py` server extras.** Fetch the `RegisterNativeHandler("...")` names from `ServerGameState_Scripting.cpp` (raw.githubusercontent.com) during `update`. When a client-only native is used in a server file but its name is registered server-side (currently `SET_ENTITY_AS_NO_LONGER_NEEDED`, `IS_ENTITY_RELEVANT`, `SET_SYNC_ENTITY_LOCKDOWN_MODE`), print `server handler exists but has no Lua global — use Citizen.InvokeNative` instead of WRONG-SIDE. *Unverified whether the global is absent; test on a server before shipping the message.*

Not recommended: the TMHS MCP server, its hand-written events DB (contains invented events) and docs index (HTML snippets, 82 pages). Our `assets/natives` catalogue and references are richer. A txAdmin MCP/client is out of scope for a stdlib skill; document the API (§4.3) instead.

---

## 6. Sub-report summaries
(See `group-E-assets-part.md` and `group-E-fiveai-part.md` for full tables and paste-ready text.)

PLACEHOLDER_SUBREPORTS

---

## 7. Counts (repos 1.1–1.4 table, 58 rows)
PLACEHOLDER_COUNTS
