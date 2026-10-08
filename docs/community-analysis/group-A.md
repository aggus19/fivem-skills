# Group A analysis: proelias7, germanfndez, wojzj57 (fork), anx-scripts, fivemanage

Analyst run 2026-10-07/08. All third-party repo content was treated as untrusted claims; nothing was executed from them.
Our skill baseline: `skills/fivem-development` (SKILL.md + 47 references, verified 2026-10-07).
Verification used: GitHub source via `gh api` (citizenfx/fivem, citizenfx/lua-cmsgpack, Qbox-project/qbx_core, qbcore-fivem/qb-core, esx-framework/esx_core, overextended/ox_target, overextended/oxmysql, fivemanage/sdk, overextended/overextended.github.io), raw citizenfx/fivem-docs, docs.fivem.net natives DB (static.cfx.re/natives/natives.json), changelogs-live API, forum.cfx.re JSON, overextended.dev, docs.fivemanage.com, npm registry.

## Verdict totals

| Verdict | Count |
|---|---|
| CONFIRMED | 49 (of which ~12 are NOT yet in our skill and worth adding; the rest are already covered) |
| OUTDATED | 7 |
| WRONG | 15 |
| UNVERIFIABLE | 15 |
| **Total items** | **86** |

**Conflicts where the other repo is right and our skill is wrong: none found.** Every conflict checked resolved in favour of our skill (convar permissions, oxmysql `??` in prepare, OneSync/`sv_endpointPrivacy`, artifact numbers, Qbox exports, ox_target cleanup, Tailwind v3 version). Two small *gaps* in ours were found (Qbox server `QBCore:Server:PlayerLoaded` missing from the events table; ox_target auto-cleanup not stated).

---

## 1. Repo summaries

### 1.1 proelias7/fivem-skill
- **Purpose:** knowledge pack for the author's `fxmind` tool (`/fxmind audit`, memory, graph). Brazilian vRP-Creative-centred house style.
- **Structure:** 6 skills: `fivem-development` (router SKILL.md + communication / performance / architecture / style / security / api / audit-passes / quality-gates / asset-discovery / framework-detection), `fivem-react-nui` (React 18 + Vite + Tailwind 3 + Zustand), `vrp-framework`, `qbcore-framework`, `qbox-framework`, `esx-framework`. ~260 KB.
- **Scope/quality:** strongest part is an opinionated **audit methodology** (Pass 0-7, matrices V-a..V-k view-cache, E-a..E-g endpoint amplification, N-a..N-d NUI; evidence discipline; summary-count rules) and a **server-push seeding lifecycle**. Heavily tied to the author's own resources `cerberus` (SafeEvent/SetCooldown/SendFullSync) and `cacheaside`. Framework skills are thin and contain several fabricated APIs (Qbox especially). Mixed English/Portuguese.
- **Freshness:** no explicit dates/versions; Tailwind "3.4.17 latest v3" (now 3.4.19 v3-lts), React 18 / Vite 5. Qbox content predates qbx_core 1.x exports layout.

### 1.2 germanfndez/fiveai-skills (last commit 2026-09-13)
- **Purpose:** 12 installable skills + multi-agent plugin manifests (Codex, Cursor, Claude Code, Hermes, DeepSeek Harness, CodeBuddy) + a `validate-plugin.mjs` test harness; website usefiveai.vercel.app.
- **Structure:** `skills/<name>/SKILL.md` with "Activation Contract / Hard Rules / Decision Gates / Execution Steps / Output Contract / References" + `rules/*.md`. Skills: lua-basics, fivem-basics, fivem-nui, fivem-security, fivem-deployment, esx-framework, qbcore-framework, oxlib, oxmysql, ox-inventory, ox-target, fivemanage.
- **Quality:** good general security write-ups (ACE, identifiers, deferrals, rate limiting, sandbox, net game events, convars) mostly sourced from docs.fivem.net; deployment skill is date-aware (35245, 2026-10-15 cutoff). Weak spots: framework docs copied from older guides (QBCore methods removed from core, wrong net-event registration), several factual errors listed below.
- **Freshness:** snapshot 2026-09-13 (latest artifact 35945 - now 37150). Still recommends `onesync on` and `sv_endpointPrivacy` (both obsolete since 2026-07/08).

### 1.3 wojzj57/fiveai-skills (fork of germanfndez, last commit 2026-09-24)
- **Only differences:** (a) skill files are an **older pre-fix copy** (reintroduces `MySQL.Async.*` with `@named` params, "validate the sender with GetInvokingResource()", syntactically invalid `RegisterNetEvent('x', source, message) ... end`, emoji headings; drops fivem-deployment, ox-inventory, ox-target and 6 security rule files); (b) adds **`fivem-mcp`**: a FiveM resource serving a local Streamable-HTTP MCP endpoint (`http://127.0.0.1:30130/mcp`) with tools `status, queue, execute_lua, execute_js, resource, logs, esx, qbcore, ox, reference`, plus a `skills/fivem-mcp` skill and a large TS test suite. Its own README states real FXServer/FxDK acceptance is **NOT_EXECUTED**.
- **Quality:** skill content regresses vs upstream; MCP is an interesting tooling idea but unproven and is an arbitrary-code-execution surface.

### 1.4 anx-scripts/fivem-skills (v0.6.0, 2026-07-11; npm `@anx-scripts/fivem-skills` 0.6.0)
- **Purpose:** a CLI (`fivem-skills pull|search|list`) that sparse-clones three doc sources (~8 MB) into `~/.fivem-skills/data` and does offline AND/camelCase/native-name-normalised search; plus a SKILL.md teaching "search, then read only the printed path; never read the huge `game-references/*` tables whole".
- **Quality:** small, clean, sensible. No FiveM knowledge content of its own. Sources verified to exist.

### 1.5 fivemanage/skills (last commit 2026-05-31; official Fivemanage org)
- **Purpose:** 4 skills for the Fivemanage SDK (`fmsdk`): `fivem-resource-logging` (strategy: passive listener vs patch vs direct), `add-fmsdk-logging`, `qbox-fmsdk-logging` (Qbox patch points + event maps), `migrate-to-fivemanage` (from `lib.logger` / Discord webhooks).
- **Quality:** good logging/audit-trail design guidance (static messages, metadata, place logs after auth+success, `clientReported` flag, dataset confirmation workflow). `config.json` reference is **outdated** vs SDK v3.2.0, and the passive-listener table has a real FiveM bug (see F6).
- **Freshness:** written for fmsdk < 3.x config schema.

---

## 2. Extracted items and verdicts

Legend: **C** = CONFIRMED, **O** = OUTDATED, **W** = WRONG, **U** = UNVERIFIABLE. "Covered" = already in our skill (file noted).

### 2.1 proelias7
| # | Claim | Verdict | Evidence / note |
|---|---|---|---|
| P1 | Qbox: `exports.qbx_core:GetCoreObject()` | **W** | qbx_core only registers `__cfx_export_qb-core_GetCoreObject` via `bridge/qb/shared/export-function.lua` → only `exports['qb-core']:GetCoreObject()` works. Ours correct (framework-qbox.md §15). |
| P2 | Qbox detection via `shared_script '@qbx_core/import.lua'` | **W** | No `import.lua` in qbx_core; real modules are `@qbx_core/modules/lib.lua`, `modules/playerdata.lua` (ours covers). |
| P3 | Qbox events `App:Client:OnPlayerLoaded`, `qbx_core:server:playerLoaded` | **W** | Not in qbx_core source; real: `QBCore:Client:OnPlayerLoaded`, `QBCore:Server:PlayerLoaded`(player), `QBCore:Server:OnPlayerLoaded`(net), `qbx_core:server:playerLoggedOut` (server/player.lua:757,979). |
| P4 | `exports.qbx_core:UpsertPlayerData` | **W** | Not exported (only internal in server/storage/players.lua). |
| P5 | Qbox manifest `@qbx_core/shared/locale.lua` | **O** | File exists (shared/locale.lua) but Qbox resources use ox_lib locales; legacy. |
| P6 | Player-loaded server hooks: QBCore/Qbox `QBCore:Server:PlayerLoaded(Player)`, ESX `esx:playerLoaded(playerId, xPlayer)`, standalone `playerJoining` | **C** | qb-core server/player.lua:458; qbx_core server/player.lua:979; es_extended server/main.lua:371 (`playerId, xPlayer, isNew`). Ours covers QBCore/ESX; **Qbox row of events-and-callbacks.md §10 lacks `QBCore:Server:PlayerLoaded`** (gap). |
| P7 | Server-push seeding lifecycle: build view once at start, push on player-loaded, patch one key + delta on CRUD; never client `Wait(N)`+`requestSync` | **C** (design) | Consistent with docs (every net event is client-callable; `-1` costs bps×players). **Not in ours** → add. |
| P8 | Endpoint amplification audit: per client-callable endpoint check DB-per-call, fan-out to `-1`, full cache reload, response size, N+1 client loops, missing rate limit | **C** (design) | Not explicit in ours audit-checklist §6 → add. |
| P9 | View cache: pre-build client payload once on load/CRUD, don't rebuild per send | **C** (design) | Ours has "packed once" (cookbook §10) but not the view-cache layer → fold into P7 text. |
| P10 | Limits "~16 KB per event (recommend < 8 KB), ~64 KB per tick" | **U** | No primary source; docs only say "multiple KBs and above → latent events" (fivem-docs triggering-events.md). Ours follows docs. |
| P11 | "Nested table max 16 levels" | **C** | citizenfx/lua-cmsgpack (grit) `lua_cmsgpack.h`: `MP_MAX_NESTING 16`; deeper tables are packed as **nil** silently (no `LUA_MSGPACK_ERROR_NESTING` in FiveM build). **Not in ours** → add. |
| P12 | Use `tostring(id)` keys so payload stays a map | **C** (nuance) | scheduler.lua sets `msgpack.set_array('without_hole')`; ours runtimes.md §8 already explains. Covered. |
| P13 | Large data: manual chunk loop with `Wait(100)` per chunk | **O** | Documented mechanism is latent events (`TriggerLatentClientEvent`, bps). Ours correct. |
| P14 | Callback/Tunnel 30 s timeout, deadlocks when unused | **U** | vRP Tunnel internals (closed). |
| P15 | Same-side `TriggerEvent` costs more than a direct call | **C** | scheduler.lua: payload msgpack + `CreateThreadNow` per handler. Covered. |
| P16 | `RegisterServerEvent(name, handler)` | **C** | scheduler.lua:331 alias of RegisterNetEvent. Covered. |
| P17 | StateBags: GlobalState replicates to all; no per-tick writes; tiny values | **C** | Covered (performance.md, cookbook §11). |
| P18 | Webhook URL never in client-loaded files; dedicated server-only webhook resource | **C** | Covered (security.md §11 uses server convar; equivalent). |
| P19 | Input validation checklist (type/shape, whitelist keys, ranges, string caps before LONGTEXT, `AND owner = ?`) | **C** | Mostly covered; string-length caps before DB write worth one line (in P8 text). |
| P20 | A cooldown helper (`CanUse*`) is not a permission check for admin endpoints | **C** (design) | Add one line in audit (P8 text). |
| P21 | Tailwind v4 uses OKLCH, unsupported in CEF; use Tailwind **3.4.17** | **O** | Reason/fix covered by ours (Chrome 111 features); current v3 is **3.4.19** (`v3-lts`, npm). |
| P22 | Vite assets must keep `[hash]` or CEF serves stale CSS | **U** | No primary source on NUI caching; harmless (Vite default). |
| P23 | `rgba()` fill on rounded overlay over transparent html disappears on some iGPUs; avoid jQuery fadeIn | **U** | Project-reported, no primary source. |
| P24 | Directional `inset/outset` border fallback | **U** | Project-reported. |
| P25 | `backdrop-filter`/`filter: blur` costly in CEF | **C** | Covered (nui.md §HUD). |
| P26 | `rem` + html font-size media-query scale table | **U** | Design preference. |
| P27 | NUI `cb` must return valid JSON, not bare `"ok"` | **U** | scheduler.lua passes value to `resultCallback`; JSON-vs-raw handling is in C++ (not verified). |
| P28 | vRP Creative API (Passport/Source/Datatable, Tunnel 150 calls/s, 64 KB warn / 256 KB cap) | **U** | Proprietary/closed distributions; ours already says "every distribution differs". |
| P29 | cerberus `SafeEvent`/`SetCooldown`/`SendFullSync`, cacheaside API | **U** | Author's own resources; not ecosystem standard. Do not integrate. |
| P30 | PlebMasters Forge for asset discovery | **C** | Site live (HTTP 200); ours references game-references. Optional. |
| P31 | ESX "use `ESX.SecureNetEvent`" for server-side sensitive events | **W** | Client-only (ESX 1.11+); ours framework-esx.md §15 correct. |

### 2.2 germanfndez/fiveai-skills
| # | Claim | Verdict | Evidence / note |
|---|---|---|---|
| G1 | `GetInvokingResource()` nil for cross-network events; not auth | **C** | Covered. |
| G2 | NUI callbacks are not authentication | **C** | Covered. |
| G3 | Net game event payload fields (weaponDamageEvent etc.) | **C** | Covered (events-and-callbacks.md §5, anticheat.md). |
| G4 | `CancelEvent()` does not stop other server handlers of the same event | **C** | scheduler.lua dispatch loop (lines ~159-173) iterates all handlers via `pairs` without checking cancel; order unspecified. **Add** to §7. |
| G5 | Sandbox: write only own resource, errno 13, `os.execute`/`io.tmpfile` blocked, `io.popen` emulated ls/dir, `load()` allowed, `os.nanotime` etc. | **C** | fivem-docs developers/sandbox.md. Covered (runtimes.md). |
| G6 | "Once any `add_convar_permission` is configured, convar reads become opt-in server-wide" | **W** | Docs: "Once **a ConVar** has at least one permission configured, it becomes restricted" (per convar). Ours correct. |
| G7 | Deferrals: `defer()`, yield a tick, `update`, `done(reason?)` on every path | **C** | Covered. |
| G8 | `GetPlayerTokens` as evidence, not proof | **C** | Lua helper in scheduler.lua:347. Covered. |
| G9 | Token bucket + clear per-source state on `playerDropped` | **C** | Covered (security.md, anticheat.md). |
| G10 | ox_lib `restricted='group.admin'` needs the principal in server.cfg | **C** (incomplete) | Ours is more complete: also needs `add_ace resource.ox_lib command.add_ace allow` (ox-lib-core.md §5). |
| G11 | Hardened cfg with `onesync on`, `sv_endpointPrivacy true`, `onesync Off/On/Legacy` | **O** | OneSync forced: citizenfx/fivem commit 19fa3d5 (2026-08-16 "force onesync to be enabled"); endpoint anonymisation commit d52296e0 (2026-07-08) removed `sv_endpointPrivacy`. Ours correct. |
| G12 | Changelogs API; `critical`/`optional` stale at 7290 | **C** | API checked 2026-10-08: critical/optional 7290. Covered. |
| G13 | Snapshot recommended 35245 / latest 35945 | **O** | API now: recommended 35245, **latest 37150**, txAdmin 8.1.1. Ours current. |
| G14 | Enhanced: `sv_enforceGameBuild` only latest or `1` | **C** | Covered (gta5-enhanced.md). |
| G15 | 2026-10-15 cutoff for < 35245; `sv_replaceExeToSwitchBuilds` deprecated | **C** | forum.cfx.re/t/5422124. Covered. |
| G16 | oxmysql `prepare` accepts `?` and `??` | **W** | overextended.dev oxmysql prepare: "only ? value placeholders, ?? column placeholders and named placeholders will throw". Ours correct. |
| G17 | `@named` placeholders "deprecated" | **C** | Docs label; still supported in 2.14.3. Covered. |
| G18 | Prefer MariaDB | **C** | Covered (versions/Qbox reqs). |
| G19 | ox_target: remove zones on resource stop "otherwise they survive a restart" | **W** | ox_target v1.18.1 client/api.lua `onClientResourceStop` removes that resource's global/model/entity options and `v:remove()`s its zones. **Ours doesn't state the auto-cleanup** → add. |
| G20 | ox_target convars (toggleHotkey, defaultHotkey, drawSprite bool, leftClick, debug) | **C** (nuance) | Covered; ours more precise (drawSprite = max sprites, default 24). |
| G21 | ox_inventory `removeHooks()` clears own hooks; hooks auto-removed on stop | **C** | Covered (ox-inventory.md §7). |
| G22 | `CanCarryItem` before taking payment; check `AddItem` return | **C** | Covered. |
| G23 | QBCore "cache `PlayerPedId()` once at file top" | **W** | natives DB PLAYER_PED_ID: "this entity handle will change after using commands such as SET_PLAYER_MODEL"; SET_PLAYER_MODEL "will destroy the current Ped ... any reference to the old ped will be invalid". Add explicit anti-pattern. |
| G24 | `RegisterNetEvent('QBCore:Server:OnJobUpdate', ...)` on server | **W** | qb-core server/events.lua:202 / qbx_core player.lua:266 fire it with server-local `TriggerEvent`; listen with `AddEventHandler`. Registering it as net makes it client-spoofable inside your resource. Ours lists it correctly as server event. |
| G25 | `Player.Functions.SetCreditCard`, `GetCardSlot` | **O** | Not in qb-core server/player.lua (qbcore-fivem/qb-core, 2026-08). Ours lists current methods. |
| G26 | ESX client: `AddEventHandler('esx:playerLoaded', ...)` (net event) | **W** (conditional) | Works only when the resource includes `@es_extended/imports.lua` (which calls `RegisterNetEvent('esx:playerLoaded')` in your runtime, imports.lua:36); with `exports.es_extended:getSharedObject()` only, it is dropped "not safe for net". See item X1. |
| G27 | `ESX.SecureNetEvent` client-only | **C** | Covered. |
| G28 | Pass `reason` to money ops | **C** | Covered. |
| G29 | Lua style: no `table.insert`, `assert` pre-conditions, enums over booleans | **U** | Style guide, source not located. Low value. |
| G30 | `nui://` "no longer works" | **W** (overstated) | Docs: "no longer a secure context"; ours (still resolves, not secure) correct. |
| G31 | Relative asset paths (`./app.js`) are wrong in NUI | **W** | Docs use relative `ui_page`; relative URLs resolve under `https://cfx-nui-<res>/`; Vite `base:'./'` relies on it (their own Vite example too). Only absolute `/x` fails. |
| G32 | NUI focus stack / no click-through | **C** | Covered. |
| G33 | External `ui_page 'https://...'` | **C** | Covered. |
| G34 | Event names in past tense | **U** | Style opinion. |

### 2.3 fivemanage/skills
| # | Claim | Verdict | Evidence / note |
|---|---|---|---|
| F1 | `exports.fmsdk:Log(dataset, level, msg, meta)` + `Info/Warn/Error`; `LogMessage` → default dataset | **C** | fivemanage/sdk v3.2.0 features/logs/server/logger.ts:131-136. Covered. |
| F2 | `metadata.playerSource`/`targetSource` auto-append identifiers (if `appendPlayerIdentifiers`) | **C** | sdk README. **Add** (ours only shows `playerSource` in an example). |
| F3 | SDK batches logs internally; don't batch yourself | **C** | fivemanage-transport.ts (`batchInterval`, `maxBatchSize` 100). **Add.** |
| F4 | Static `message`, dynamic values in metadata | **C** | https://docs.fivemanage.com/fivemanage/guides/logs/best-practices. **Add.** |
| F5 | `config.json`: flat booleans `playerEvents: true`, `txAdminEvents: true`, levels incl. `fatal`, `console: false` | **O** | v3.2.0 config.json: `levels ["error","warn","info","debug"]` (no `fatal` → such logs rejected), `console: true`, `excludedPlayerIdentifiers ["ip"]`, `excludeInDepthMetadata`, and `playerEvents/chatEvents/baseEvents/txAdminEvents/oxInventoryEvents` are objects `{ enabled: false, dataset: "default" }`. |
| F6 | A separate logging resource can passively log another resource's `RegisterNetEvent` events with `AddEventHandler` only | **W** | scheduler.lua: `eventHandlers` is per-runtime; net-sourced events without a local `RegisterNetEvent` are dropped ("event X was not safe for net"). Listener must `RegisterNetEvent` too, and the payload is client-controlled. |
| F7 | Log after auth and after success; denied attempts as `warn` with `denied = true`; `clientReported = true` for unverifiable client actions; internal audit `TriggerEvent` patch | **C** (design) | Sound; **add**. |
| F8 | `QBCore:Server:OnMoneyChange(src, moneyType, amount, actionType, reason)` = single economy audit point | **C** | qbx_core player.lua:1291; qb-core player.lua:204. Event covered in ours; the audit use-case is new. |
| F9 | `qbx_core:server:onJobUpdate(name, job)` = definition change | **C** | qbx_core server/groups.lua:155. Covered. |
| F10 | qbx_police / qbx_bankrobbery / qbx_adminmenu event names and menu index maps | **U** | Not verified (their own doc says verify before use). Don't integrate. |
| F11 | ox_lib logger convars `ox:logger fivemanage`, `fivemanage:key` | **C** | Covered (ox-lib-utilities.md §4). |
| F12 | Migrating Discord-webhook logs (find `PerformHttpRequest` to discord, helper wrappers, webhook convars) | **C** (design) | Ours has webhook hygiene; migration grep list is a nice audit hint (optional). |
| F13 | Workflow: group planned logs by domain, ask user once per group for dataset names | **C** (workflow) | Workflow idea (see §4). |

### 2.4 anx-scripts/fivem-skills
| # | Claim | Verdict | Evidence / note |
|---|---|---|---|
| A1 | Mirrorable doc sources: `citizenfx/fivem-docs` (`content/docs`), `citizenfx/natives`, `overextended/overextended.github.io` (`content/docs`: ox_core, ox_doorlock, ox_fuel, ox_inventory, ox_lib, ox_target, oxmysql, guides); sparse clone ≈ 8 MB | **C** | gh api contents listing. Tooling idea → add script. |
| A2 | `docs/.../game-references/*` are huge (vehicle-models ~330 KB) — grep, never read whole | **U** | Plausible; sizes not measured. |
| A3 | npm `@anx-scripts/fivem-skills` 0.6.0 | **C** | npm registry (2026-07-11). |

### 2.5 wojzj57 fork (delta only)
| # | Claim | Verdict | Evidence / note |
|---|---|---|---|
| W1 | Older skill copies: `MySQL.Async.execute/fetchScalar` with `@named`, "validate the sender with GetInvokingResource()", `RegisterNetEvent('x', source, msg) ... end` | **W/O** | mysql-async API removed from oxmysql; GetInvokingResource is not auth; syntax invalid. |
| W2 | fivem-mcp: local MCP with `execute_lua`/`execute_js`/`resource`/`logs` tools | **U** | Own README: real FiveM acceptance NOT_EXECUTED. Idea only; arbitrary code execution. |
| W3 | Server JS: after `await` of non-host promises, call natives back on the host tick | **C** | Covered (runtimes.md, Node thread affinity). |
| W4 | `GetConsoleBuffer()` for a server console snapshot | **C** | Present in our natives catalog (assets/natives/CFX-SERVER.md); not mentioned in debugging.md (optional). |
| W5 | Client log `CitizenFX.log`, history boundary "Game finished loading!" | **U** | Not verified. |

### 2.6 Cross-cutting fact verified while checking the above
| # | Claim | Verdict | Evidence |
|---|---|---|---|
| X1 | `RegisterNetEvent` "safe for net" is **per resource runtime** | **C** | citizenfx/fivem `data/shared/citizen/scripting/lua/scheduler.lua`: `local eventHandlers = {}` (file-local per runtime); net-sourced event without `safeForNet` → `Citizen.Trace('event ' .. eventName .. ' was not safe for net')` and return. Underlies G26 and F6. **Not explicit in ours** → add. |

---

## 3. Recommended integrations (ready to paste)

Ordered by value. Each block names the target file and section.

### 3.1 `references/events-and-callbacks.md` §1 (after the line "`RegisterNetEvent(name[, handler])` marks the event **safe for net** ...")
```markdown
- The safe-for-net flag is **per resource** (each resource's Lua runtime keeps its own handler table). A resource that only `AddEventHandler`s a net event fired by another resource or by the server — e.g. client `esx:playerLoaded`, a passive logger listening to another resource's client→server event — receives nothing ("event X was not safe for net") unless it calls `RegisterNetEvent(name)` itself. Exception: `@es_extended/imports.lua` already registers `esx:playerLoaded` inside your resource. A listener that registers a client→server event becomes a client-callable endpoint too: treat its payload as untrusted. Source: https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/scheduler.lua
```

### 3.2 `references/events-and-callbacks.md` §7 Cancelling events (append)
```markdown
- `CancelEvent()` only sets the cancel flag: every other handler of that event (in your resource and in others) still runs, in unspecified order (`pairs`). After cancelling, `return`; never assume yours ran first or last. For net game events it stops routing to other clients, not other server handlers. Source: scheduler.lua event dispatch loop (link above).
```

### 3.3 `references/runtimes.md` §8 Serialization (append)
```markdown
- **Nesting limit:** lua-cmsgpack packs tables nested deeper than **16 levels** as `nil` — silently, no error (`MP_MAX_NESTING 16`, FiveM builds without `LUA_MSGPACK_ERROR_NESTING`). Applies to event args, exports, state bags and callbacks. Flatten deep config/JSON trees or send them `json.encode`d. Source: https://github.com/citizenfx/lua-cmsgpack/blob/grit/src/lua_cmsgpack.h
```

### 3.4 `references/ox-target.md` §4 Exports (append) and §5 example comment
```markdown
- **Automatic cleanup:** on `onClientResourceStop` ox_target removes every global/model/entity/local-entity option and every zone registered by the stopping resource (tracked via `GetInvokingResource()`). Manual `removeZone`/`remove*` is only needed to remove things while your resource keeps running. Source: https://github.com/overextended/ox_target/blob/main/client/api.lua (v1.18.1)
```
(Optionally mark the `onResourceStop → removeZone` lines in §5 as "not required; shown for symmetry".)

### 3.5 `references/events-and-callbacks.md` §10 table, Qbox row, Server column (fix gap)
Replace `` `QBCore:Server:OnPlayerLoaded`, `QBCore:Server:OnPlayerUnload`, `QBCore:Server:OnJobUpdate` `` with:
```markdown
`QBCore:Server:PlayerLoaded` (player object, server-local, fired by `CreatePlayer`), `QBCore:Server:OnPlayerLoaded` (net, client-sent — notification only), `QBCore:Server:OnPlayerUnload`, `QBCore:Server:OnJobUpdate`
```
Source: https://github.com/Qbox-project/qbx_core/blob/main/server/player.lua (line ~979, v1.24.0)

### 3.6 `references/audit-checklist.md` §6 Server authority review (append items 10-13)
```markdown
10. **Amplification:** for every client-callable endpoint (net event, `lib.callback.register`/framework callback, NUI→server chain, vRP `Tunnel.bindInterface` function) assume a cheat calls it in a tight loop. Flag: DB query per call (serve reads from a server cache), fan-out `TriggerClientEvent(-1, ...)` or `GlobalState` writes from a client-triggered path, full cache reload/rebuild per call, oversized replies (lists with LONGTEXT/base64; return metadata, fetch details on demand in one batch), and client loops that call the server once per list item (N+1).
11. Admin/staff endpoints need a real permission (`IsPlayerAceAllowed`, framework group/job) — a cooldown/"CanUse" helper that only checks time is **not** authorization.
12. String inputs have length caps before any DB write (unbounded strings into LONGTEXT = storage DoS); ownership enforced in SQL (`WHERE id = ? AND owner = ?`).
13. Evidence discipline: list every file from `fxmanifest.lua` in "Files reviewed"; re-read each cited `file:line`; name the exact handler; summary counts must equal the findings rows.
```

### 3.7 `references/performance-cookbook.md` new section "17. Client data bootstrap → server push + view cache"
```markdown
## 17. Client data bootstrap → server push + view cache
Before — every client pulls on start; each pull hits SQL and rebuilds the payload (N players = N queries; the endpoint is spam-able):
```lua
-- client
CreateThread(function() Wait(2000) TriggerServerEvent('myres:server:requestSync') end)
-- server
RegisterNetEvent('myres:server:requestSync', function()
    local rows = MySQL.query.await('SELECT * FROM myres_points')
    TriggerClientEvent('myres:client:sync', source, buildList(rows))
end)
```
After — build once, push, patch deltas:
```lua
local View = {}                      -- client-ready payload keyed by tostring(id); built at start / on CRUD only
CreateThread(function()
    for _, row in ipairs(MySQL.query.await('SELECT id, label, coords FROM myres_points') or {}) do
        View[tostring(row.id)] = { id = row.id, label = row.label, coords = json.decode(row.coords) }
    end
    TriggerClientEvent('myres:client:seed', -1, View)   -- covers `ensure` restarts; nobody online at boot
end)
AddEventHandler('QBCore:Server:PlayerLoaded', function(player)  -- ESX: 'esx:playerLoaded'(playerId); standalone: 'playerJoining'
    TriggerClientEvent('myres:client:seed', player.PlayerData.source, View)
end)
-- CRUD (after the DB write succeeded): patch one key, send one delta
local function upsert(row)
    local key = tostring(row.id)
    View[key] = { id = row.id, label = row.label, coords = row.coords }
    TriggerClientEvent('myres:client:upsert', -1, View[key])
end
```
Rules: never rebuild/sort/query inside the per-player send; large views (> a few KB) go out with `TriggerLatentClientEvent(name, target, bps, View)`; keys as strings so the table stays a msgpack map. Also handle the client's own resource restart (state bag / `isLoggedIn` check) since the player-loaded event won't fire again.
```

### 3.8 `references/performance.md` (anti-pattern list or §client natives)
```markdown
- Don't store `PlayerPedId()` in a file-level local: the handle changes after `SetPlayerModel` (clothing/appearance menus, respawn scripts) and old references become invalid. Read it per use, or use ox_lib `cache.ped` (refreshed by ox_lib) / ESX `esx:playerPedChanged`. Source: https://docs.fivem.net/natives/?_0xD80958FC74E988A6 and https://docs.fivem.net/natives/?_0x00A1CADD00108836
```

### 3.9 `references/ecosystem-resources.md` §4 Fivemanage SDK (append)
```markdown
- `metadata.playerSource` / `metadata.targetSource` make the SDK append that player's identifiers (when `appendPlayerIdentifiers` is true; drop types via `excludedPlayerIdentifiers`). Keep `message` static and put every dynamic value in metadata (filterable in the dashboard). Logs are queued and batched by the SDK — never batch yourself.
- `config.json` (v3.2.0) defaults: `level "info"`, `levels ["error","warn","info","debug"]` (no `fatal`: a `Log(ds, 'fatal', ...)` is rejected unless you add it), `console true`, `enableCloudLogging true`, `excludedPlayerIdentifiers ["ip"]`, `excludeInDepthMetadata false`; built-in auto-loggers are objects, all **off** by default: `playerEvents`, `chatEvents`, `baseEvents`, `txAdminEvents`, `oxInventoryEvents` = `{ "enabled": false, "dataset": "default" }`.
- Sources: https://github.com/fivemanage/sdk/blob/main/config.json · features/logs/server/fivemanage-transport.ts · https://docs.fivemanage.com/fivemanage/guides/logs/best-practices
```

### 3.10 `references/security.md` §11 Logging and Discord webhook hygiene (append "audit-trail placement")
```markdown
- **Where to log:** after the permission check and after the mutation succeeded (`AddMoney`/`AddItem` returned true, DB write returned). Log denied attempts separately (`warn`, `denied = true`, failed permission). Client-only actions the server can't verify: route through a server event with an ACE check and mark `clientReported = true`. Economy-wide audit: one `AddEventHandler('QBCore:Server:OnMoneyChange', function(src, moneyType, amount, action, reason) ... end)` covers every Qbox/QBCore AddMoney/RemoveMoney/SetMoney (qbx_core server/player.lua ~1291; qb-core server/player.lua ~204). To log a resource you can't edit, a server-local `TriggerEvent` is observable with `AddEventHandler`; a client→server net event needs `RegisterNetEvent` in the logger too (per-resource safe-for-net) and its payload is client-controlled; `lib.callback.register`/`lib.addCommand`/exports are not observable — patch after success with a namespaced audit event (`TriggerEvent('mylogs:server:<res>:<action>', src, data)`).
```

### 3.11 `references/tooling.md` §9 Skill scripts (new script proposal) + §10 sources
```markdown
- `docs_mirror.py` (proposed): shallow **sparse** clones for offline grep — `citizenfx/fivem-docs` (`content/docs`), `overextended/overextended.github.io` (`content/docs`: ox_lib, ox_inventory, ox_target, oxmysql, ox_core, ox_doorlock, ox_fuel) — ~8 MB total vs 274 MB full fivem-docs tarball. `git clone --depth 1 --filter=blob:none --sparse <url> <dir> && git -C <dir> sparse-checkout set content/docs`. Grep the huge `content/docs/game-references/*` tables, never read them whole. Fivemanage publishes an LLM index at https://docs.fivemanage.com/llms.txt (pages also served as `.md`).
```
(Implementation note: stdlib-only Python wrapper around `git`, cache in `$FIVEM_SKILL_CACHE/docs`, `update` + `search <terms>` with AND semantics and camelCase/`SNAKE_CASE` normalisation like natives.py.)

### 3.12 Optional small additions
- `references/debugging.md`: "Server-side console history: `GetConsoleBuffer()` (server native) returns the current console buffer — useful for in-game admin log viewers / diagnostics resources." (catalog: assets/natives/CFX-SERVER.md)
- `references/nui.md` §2: "Tailwind v3 line: `tailwindcss@3` = 3.4.19 (`v3-lts`); some guides still pin 3.4.17." (npm registry)

---

## 4. Ideas worth copying (structure / workflow / tooling)

1. **Audit methodology as numbered, mandatory passes with an output matrix** (proelias7 `audit-passes.md`): Pass 0 full-manifest scope with "Files reviewed (line counts)", Pass 1 evidence discipline, endpoint matrix (endpoint · type · auth · rate-limit · validation · DB cost · reply KB · fan-out · severity), severity↔fix-phase alignment, and a pre-save self-check (summary counts = findings rows). Our audit-checklist.md has the content but not the forcing structure; adding the endpoint matrix + self-check (3.6) captures most of the value.
2. **Task-mode "quality plan" before coding** (proelias7 `quality-gates.md` Gate A): a 6-line plan per change — endpoints, payload KB, cache, validation, rate limit, fan-out — then a 2-cycle self-review of the diff against a checklist. Could be a short section in SKILL.md "Before writing code".
3. **Skill section template** (germanfndez): Activation Contract / Hard Rules / Decision Gates / Execution Steps / Output Contract per skill. Our SKILL.md router is already good; the explicit "Output Contract" line (what the answer must contain, e.g. server.cfg lines, manifest entries) is worth borrowing.
4. **Plugin validation test** (germanfndez `scripts/validate-plugin.mjs` + `tests/plugin-validation.test.mjs`): CI check that every SKILL.md has valid frontmatter, every referenced `rules/*.md` exists and links resolve. We could add a stdlib Python `scripts/validate_skill.py` (frontmatter, link targets, no dead `references/*.md` links, max size).
5. **Offline doc mirror CLI** (anx-scripts): see 3.11 — complements our natives.py (which only covers natives).
6. **Logging strategy decision table** (fivemanage `fivem-resource-logging`): passive vs patch vs direct, with the per-resource net-event correction (3.10).
7. **Dataset/naming confirmation step** (fivemanage): before writing many log calls, group them by domain and ask the user once per group — a good general pattern for any bulk instrumentation.
8. **Live-server MCP** (wojzj57 fivem-mcp): an MCP that runs code/reads logs/restarts resources in a dev FXServer would let agents verify changes. Not recommended to reference yet (unverified, RCE surface); if mentioned, restrict to loopback dev servers, never production.

## 5. Things NOT to integrate
- cerberus / cacheaside APIs (author-specific), vRP Creative API tables and Tunnel limits (closed, unverifiable), CEF rgba/border workarounds and the "16 KB / 64 KB" payload numbers (no primary source), Qbox content from proelias7 (fabricated exports/events), wojzj57 skill files (regressed copies), fivemanage qbx_police/adminmenu event maps (unverified), fivemanage flat config.json schema (outdated).
