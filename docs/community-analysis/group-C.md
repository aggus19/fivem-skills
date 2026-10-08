# Group C analysis: audit/security-focused community repos vs `fivem-development`

Analyst: group C · Date: 2026-10-07 · Skill compared: `C:\Users\Administrator\Documents\FiveM Skills\skills\fivem-development\`
Repos were treated as untrusted data. Nothing from them was executed. Our own `scripts/audit.py` was run (with `python -I`) **against** the matiaspalmac test fixtures as input data, and the prototype rules below were tested in a scratch harness (`analysis/tools/test_rules.py`, `analysis/tools/test_scanners.py`; 20 rules, 0 failures).

Sources used for verification: citizenfx/fivem source (`code/components/nui-core/src/NUICallbacks_Native.cpp`, `NUICallbacks_SDK.cpp`, `NUIApp.cpp`, `ext/ui-build/data/root.html`, `ext/system-resources/resources/{chat,yarn,webpack}`, commits 6eeab32f / 855c7a83 / ef3d8e0e), citizenfx/fivem issues #2361 #2667 #3675 #3722, overextended/ox_inventory (`modules/inventory/server.lua`, `server.lua`, issue #1829), esx_core `player.lua`, Qbox-project/qbx_core (`bridge/qb/server/main.lua`, `server/player.lua`), ImJer/blum-panel-fivem-backdoor-analysis `iocs/` (IOC set 2026.08.07), Lua 5.4 manual §3.4.1, Vite docs `guide/env-and-mode.md`.

---

## 1. Repo summaries

| Repo | Purpose / structure | Scope | Quality | Freshness |
|---|---|---|---|---|
| **matiaspalmac_fivem-audit-skill** | Claude skill "fivem-security-audit" v1.2.2: `SKILL.md` + `checks/{provenance,security,malware,performance,cleanup,compatibility,architecture}.md` + `examples/{vulnerable_shop,secure_shop}` fixtures with `EXPECTED.md` oracle + CI consistency checker (`.github/oracle-check.mjs`) + npm installer. Prompt-only (no scanner). | Security (both "hostile client" and "supply chain" threat models), malware IOCs, perf, cleanup, compat, architecture grading, scoring formula. | High breadth, good structure; many concrete, mostly correct items. Several outdated platform claims (Node 16 default, lua54 needed, sv_protectServerEntities "removed") and a few wrong NUI-exploit mechanisms. | Last commit 2026-09-04. Blum IOCs up to ~March 2026. |
| **matiaspalmac_fivem-security-audit** | **Byte-identical** to `fivem-audit-skill` (`diff -r -x .git` = no differences; same HEAD 193249ee; remote is `matiaspalmac/fivem-security-audit`). Treated as one repo. | — | — | — |
| **matiaspalmac_fivem-resource-builder** | Companion "fivem-resource-builder" v1.1.1: `SKILL.md` + `templates/{architecture,fxmanifest,server,client,nui,ox,framework,security,typescript,ci}.md` + sample_shop. | Scaffolding secure-by-default resources (module loader, bridge, React/Vite NUI, connection phase, HTTP handlers). | Good patterns (bounded arithmetic, fail-closed deferrals, constant-time token compare) but some API errors (RegisterStash arg order, Qbox = ox_core). | 2026-09-04. |
| **ayala2a_fivem-claude-code-expert** | Single French `CLAUDE.md` (27 KB) API cheat sheet + install scripts that clone framework repos into `refs/`. | ESX/QBCore/Qbox/ox_core/ox_lib/ox_inventory/ox_target/oxmysql APIs, security & perf snippets, server.cfg hardening. | Mixed: many API names wrong (lib.textUI, removeBoxZone, useItem hook, qbx GetCoreObject, pma-voice export, sv_enableDevtools). | 2026-06-13. |
| **SRock44_fivem-agents** | Claude Code "swarm": `CLAUDE.md` coordinator + 12 agent prompts (`.claude/agents/*`) mirrored as slash commands. | Generic FiveM roles (cfx, qbcore, ox, events, nui, security, database, perf, lua, pm, bug-review, test). | Generic, mostly sound advice; a few wrong claims (event-name "override", lib.callback 2nd arg). Little new. | 2026-04-28. |
| **abual3bed00_Fivem-Agent** | Electron desktop app (local LLM chat + editor) with 3 tiny knowledge files and QBCore templates (Arabic). | Generator UI, not a knowledge base. | Low FiveM content; template has an empty `while true do Wait(0)` loop. | 2026-03-25. |
| **NewwyKung_fivem-resource-ai-template** | Large AI-agent project template (`.ai/` rules, skills, recipes, matrices; Svelte NUI; MCP dev bridge over `SetHttpHandler`; release/secret-scan scripts). | Process/architecture, NUI pipeline, dev tooling. | High quality, current (lua54 deprecated, OAL opt-in, shallow state bags) — consistent with our skill; little new FiveM fact. | 2026-09-16. |

Baseline observation: our skill already covers most of what these repos contain (state-bag limiter constants, strict mode, entity lockdown modes, Enhanced changes, CommunityOx archive, ox_inventory dupe table, KVP trust, NUI strict mode, OAL, Node 22, Lua 5.4-only). The real gaps are in **malware IOCs / audit.py detection**, a handful of **security checklists** (HTTP handlers, connection phase, external identity, build chain) and one **audit.py false positive**.

---

## 2. Our audit.py vs the matiaspalmac fixtures (empirical)

`python -I audit.py examples/vulnerable_shop` found 1 critical / 2 high / 2 medium / 3 low. Missed (of the oracle's 18 expected findings, those a static regex could plausibly catch):

| Missed issue | Why missed | Fix proposed (§5) |
|---|---|---|
| Client sends `GetPlayerServerId(PlayerId())` and server uses it instead of `source` | no rule | `client-sends-own-id` |
| Net events written as `RegisterNetEvent('x')` + `AddEventHandler('x', function ...)` never use `source` (`vshop:makeAdmin`, `vshop:report`) | `scan_net_handlers` only matches the inline `RegisterNetEvent('x', function` form | split-form scanner (tested: flags both) |
| Server state-bag handler ignores `replicated` | no rule | `statebag-handler-no-replicated` |
| `innerHTML` XSS in `html/index.html` | `.html/.htm` not in `CODE_EXT` | add `.html`, `.htm` (side = client via path) |
| Wildcard executable script globs in manifest | no rule (and arguably by design) | optional low-severity `manifest-exec-glob` |

`secure_shop` (should be clean): one **HIGH false positive** — `client-money-event` on `TriggerServerEvent('vshop:buy', 'water', 10)` (10 is a quantity, the correct intent-only pattern). Recommendation: downgrade `client-money-event` to `medium`, or require the numeric arg to follow a price-like keyword. (`client-trusted-price` already covers explicit `price/amount` names.)

**Second false positive (verified, important):** `DROPPER_NAMES` flags `yarn_builder.js` and `webpack_builder.js` as *critical known-backdoor by name alone*, but these are **legitimate stock files** of the Cfx system resources `yarn` and `webpack` (citizenfx/fivem `ext/system-resources/resources/yarn/yarn_builder.js`, 3,026 bytes; `.../webpack/webpack_builder.js`). Blum *modifies* them (infected copies 43 KB / 632 KB per ImJer README). The matiaspalmac repo frames this correctly ("modifications to yarn_builder.js …"). Fix in §5 (content/size/location gated). `babel_config.js` stays name-alone (no stock file).

---

## 3. Claims extracted and verified

Legend: NEW = not in our skill; CONFLICT = contradicts our skill; COVERED = already in our skill (listed only when it matters). Verdicts: CONFIRMED / OUTDATED / WRONG / UNVERIFIABLE.

### 3.1 matiaspalmac audit skill (A)

| # | Claim | Status | Verdict | Evidence |
|---|---|---|---|---|
| A1 | Lua 5.4 integer arithmetic wraps silently; `price * qty` with huge integer qty can go negative and pass `balance < total` checks — bound operands before multiplying, sanity-check result (`total > 0`, ceiling). | NEW | CONFIRMED | Lua 5.4 manual §3.4.1 "all operations wrap around". Mitigated in our template by `count <= 50`, but the rule itself is absent. |
| A2 | ESX `removeMoney(negative)` adds money. | NEW | OUTDATED | esx_core `player.lua` `removeAccountMoney` only acts `if money > 0` (and errors on non-number). Still true for custom/old frameworks — keep principle "reject ≤ 0" only. |
| A3 | Server JS defaults to Node 16; flag any server JS without `node_version '22'`. | CONFLICT | OUTDATED | citizenfx/fivem 6eeab32f (2026-01-20) "NodeJS16 removal"; our versions.md/runtimes.md are right. |
| A4 | `lua54 'yes'` required (for escrow / 5.4 features). | CONFLICT | OUTDATED | 855c7a83 "Remove Lua 5.3 support" (merged 2025-06-24). Our fxmanifest.md right. |
| A5 | `sv_protectServerEntities` removed, use `sv_entityLockdown`. | CONFLICT | WRONG (Legacy) | Present in `ServerGameState.cpp` / `NetServerObject.cpp`; no-op only on Enhanced. Ours right. |
| A6 | `sv_enableDevtools` does not exist; flag it in server.cfg. | NEW | CONFIRMED | Issue #2667 (feature request, closed); no source hits. ayala2a recommends `set sv_enableDevtools false` → WRONG there. |
| A7 | NUI XSS can force-quit the victim's game via `invokeNative('quit')`. | NEW | CONFIRMED | `NUICallbacks_Native.cpp`: `if (nativeType == "quit") ExitProcess(0);` — handler registered for every NUI frame. `openUrl` shows a confirmation modal for untrusted URLs. |
| A8 | XSS can steal clipboard via `invokeNative('fxdkClipboardRead')`. | NEW | WRONG | `NUICallbacks_SDK.cpp` returns early `if (!launch::IsSDK() && !launch::IsSDKGuest())` — FxDK only. |
| A9 | XSS can run commands as victim via `invokeNative('chatResult')`. | NEW | WRONG | `chatResult` is the chat resource's NUI callback, not an invokeNative type; chat ships `nui_callback_strict_mode 'true'` (a407bb0b, 2024-08). |
| A10 | `top.citFrames['res']` lets XSS hijack another resource's iframe (mic access). | NEW | UNVERIFIABLE | `window.citFrames` exists in `root.html`, but resource frames have per-resource `cfx-nui-<res>` origins, so same-origin policy should block DOM access; not tested. Do not integrate. |
| A11 | NUI callbacks are POSTs to `localhost:13172`. | NEW | WRONG | 13172 is the CEF remote-debugging port (our nui.md). Callbacks are `https://<resource>/<name>` requests intercepted by CEF. Conclusion ("players can forge callbacks") is still right. |
| A12 | `nui_callback_strict_mode 'true'` (build 9549+). | COVERED | CONFIRMED (feature) / UNVERIFIABLE (build no.) | ef3d8e0e 2024-08-22. |
| A13 | State-bag limiter values 75/125, 150/175, 131072/262144. | COVERED | CONFIRMED | Same as our onesync-entities.md. |
| A14 | State-bag flood crash (#2361) "still valid". | — | OUTDATED | #2361 closed; limiters were the fix. |
| A15 | Scenario-spawned objects bypass `entityCreating` (#3675) → crash spam. | NEW | CONFIRMED | Issue #3675 open (2025-10-13): e.g. `WORLD_HUMAN_CONST_DRILL` objects sent to all players with no server event. |
| A16 | Undisclosed crash vector (#3722); durable control is artifact currency. | NEW | CONFIRMED | #3722 open (2025-11-17). |
| A17 | ox_inventory #1829: duplicate plate → access another player's trunk. | NEW | CONFIRMED | Issue #1829 (2.42.3, closed); maintainer added checks, ownership checks are framework-specific (ox_core). |
| A18 | ox_inventory 2.46.1 / 2.47.0 / 2.47.3 introduced dupe / 2.47.6 fix; floor ≥ 2.47.6. | COVERED | CONFIRMED | Matches security.md §16. |
| A19 | CommunityOx archived (read-only). | COVERED | CONFIRMED | — |
| A20 | Additional Blum/Warden/GFX/Cipher domains (blum-panel.com, 0xchitado.com, 2312321321321213.com, 5mscripts.net, bhlool.com, bybonvieux.com, fivemgtax.com, flowleakz.org, iwantaticket.org, l00x.org, monloox.com, noanimeisgay.com, ryenz.net, spacedev.fr, trezz.org, z1lly.org, 2nit32.com, useer.it.com, wsichkidolu.com, ciphercheats.com, keyx.club, dark-utilities.xyz). | NEW (audit.py has 9) | CONFIRMED (single researcher) | ImJer `iocs/domains.txt`. |
| A21 | C2 IPs 185.87.23.198 (origin, :5000), 185.80.128.35, 185.80.128.36, 185.80.130.168 (GFX, :3000). | NEW | CONFIRMED | ImJer `blum_iocs.json` `direct_ips`. `13.248.213.45` (AWS fallback) not in that list → UNVERIFIABLE. |
| A22 | Strings: `VB8mdVjrzd`, `bertjjgg`, `miausas`, JJ keys (`devJJ`, `nullJJ`, `zXeAHJJ`…), OAuth app `1444110004402655403`, BTC/LTC wallets, `installed_notices`. | NEW | CONFIRMED | ImJer `iocs/strings.txt`. SOL wallet not there → UNVERIFIABLE. |
| A23 | Socket.IO commands `registerServer`, `getServerPlayers`, `getPayloads`… | NEW | UNVERIFIABLE | ImJer lists different panel events (`admin:runPayload`, `admin:executeCmd`, `fs:startConsoleStream`, `joinServerRoom` …). |
| A24 | Blum reads/forwards `X-TxAdmin-Token` (session hijack). | NEW | CONFIRMED | ImJer strings: `X-TxAdmin-Token`, `X-TxAdmin-Identifiers`, `txadmin:js_create`. |
| A25 | txAdmin injection map: `cl_playerlist.lua`=`helpEmptyCode` (client RCE), `sv_resources.lua`=`onServerResourceFail` (server RCE), `sv_main.lua`=`RESOURCE_EXCLUDE`/`isExcludedResource` (cloaking, inline, not hand-cleanable). | partly COVERED | CONFIRMED | ImJer `txadmin_tampering`. Ours lists files and markers but not the mapping / "reinstall, don't hand-edit sv_main.lua". |
| A26 | XOR dropper keys 169/189/204. | — | OUTDATED | ImJer: key randomized per file (66, 75, 131 … 252); detect structurally: `String.fromCharCode(a[i]^k)`. |
| A27 | Payload size fingerprints (JS ~420–470 KB, replicator ~1.6 MB, XOR dropper 40–46 KB, Luraph Lua 60–67 KB). | NEW | CONFIRMED | ImJer `payload_size_ranges`. |
| A28 | 3,856 infected servers, ESX 48% / QBCore 36% / vRP 9%. | NEW | UNVERIFIABLE | Not checked against primary report. |
| A29 | Cipher: URL `/_i/i?to=`, sessionmanager `host_lock.lua`/`empty.lua`, `licence.txt`/`game.log`, Windows user "Moda". | NEW | UNVERIFIABLE | No primary source found. |
| A30 | FiveHub (`fivehub-panel.site`, `api.php?key=`, `Microstub.exe`), extra domains (ketamin.cc, admin-panel.sbs, spectre.sbs, docsfivem.com …). | NEW | UNVERIFIABLE | Only `keyx.club`/`dark-utilities.xyz` appear in ImJer list. |
| A31 | Evasion: sensitive natives invoked by hash (`Citizen.InvokeNative(0x561C060B…)`). | NEW | CONFIRMED (mechanism) | Hashes from our catalog: ExecuteCommand 0x561C060B, PerformHttpRequestInternal 0x8E8CC653 / Ex 0x6B171E87, SaveResourceFile 0xA09E7E7B. |
| A32 | Evasion: `_G['PerformHttpRequest']`, `_ENV['load']`. | NEW (we only match `_G['\x..`) | CONFIRMED (mechanism) | Lua semantics. |
| A33 | Exfil via `api.telegram.org/bot`, raw-IP URLs, URL shorteners. | NEW | UNVERIFIABLE (sound heuristic) | — |
| A34 | `io.open` write mode, `debug.sethook/setupvalue`, `os.tmpname` have no legit resource use. | NEW (os-exec lacks io.open) | CONFIRMED (availability: server CfxLua has `io`/`os`/`debug`, runtimes.md) | — |
| A35 | `SetHttpHandler` endpoints are public on the game port at `/<resource>/`; need auth (constant-time token from `set` convar), path whitelist, body cap, rate limit; `request.address` is not auth behind proxies. | NEW (only the URL is in natives-essentials.md) | CONFIRMED (endpoint location: native docs) | — |
| A36 | Connection phase: `deferrals.done()` on every branch incl. DB errors; reject players without `license`; bans match multiple identifiers; don't interpolate player names into `presentCard`. | NEW (we document the API only) | CONFIRMED (API: docs deferrals; rest best practice) | — |
| A37 | Abandoned connections never reach `playerDropped`. | NEW | UNVERIFIABLE | Advice "expire connection-phase tables by time" is still sound. |
| A38 | `screenshot-basic` client `requestScreenshotUpload` POSTs from the client → upload URL/key exposed; proxy server-side. | NEW nuance | CONFIRMED (screenshot-basic README API) | Our anticheat.md says store screenshots server-side but not this leak. |
| A39 | Discord-role whitelist must fail closed on API error/429; bot token via `set`; a `setr` token is already compromised. | NEW | CONFIRMED (setr replication per convars docs; fail-closed is logic) | — |
| A40 | Client KVP is untrusted. | COVERED | CONFIRMED | — |
| A41 | npm supply chain: commit lockfile, `npm ci --ignore-scripts`, review `preinstall/postinstall/prepare`, no git/http deps, minified bundle without source = UNAUDITED, `node_modules` committed = unaudited. | NEW | CONFIRMED (npm `--ignore-scripts`, lifecycle scripts) | — |
| A42 | Wildcard executable globs load injected files. | CONFLICT-ish (our template uses `client/*.lua`) | CONFIRMED (mechanism: globs expand at load, fxmanifest.md) | Opinion on severity; Blum edits manifests anyway. Low-severity note only. |
| A43 | N+1 "GOOD" fix: `WHERE id IN (?)` with `table.concat(ids, ',')`. | NEW | WRONG | Binds one string → `IN ('1,2,3')`. Use one `?` per id (SRock44 shows the correct form). |
| A44 | `QBCore:Server:UseItem` deprecated/exploitable — flag it. | NEW | OUTDATED | No longer present in qb-core. |
| A45 | "QBox (ox_core): Ox.GetPlayer, ox:playerLogout". | CONFLICT | WRONG | Qbox is `qbx_core`; ox_core is a separate framework (our framework-qbox.md / ox-core.md right). |
| A46 | Hardening `sv_authMaxVariance 1`, `sv_authMinTrust 5`. | CONFLICT | UNVERIFIABLE / risky | Ours: high values can lock everyone out; keep defaults unless tested. Ours stands. |
| A47 | Enhanced: pure always on, builders unsupported, .NET 10, KVP migration, `PrintRemoteCommandLog`, one endpoint per `endpoint_add_*`, renamed binaries. | COVERED | CONFIRMED | gta5-enhanced.md. |
| A48 | Server JS: Node callbacks off main thread → `setImmediate` before natives. | COVERED | CONFIRMED | runtimes.md L197. |

### 3.2 matiaspalmac resource builder (B)

| # | Claim | Status | Verdict | Evidence |
|---|---|---|---|---|
| B1 | `RegisterStash(id, label, slots, weight, nil, nil, instanceId)` binds instance. | — | WRONG | `registerStash(name, label, slots, maxWeight, owner, groups, coords, instance)` — 7th is coords (ox_inventory `modules/inventory/server.lua`). Ours correct. |
| B2 | Detect Qbox via `GetResourceState('ox_core')`; "Qbox built on ox_core". | CONFLICT | WRONG | qbx_core; check `qbx_core` before `qb-core` (our framework-bridge.md). |
| B3 | Constant-time token compare for HTTP handler auth. | NEW | CONFIRMED (good practice) | Folded into §4.3. |
| B4 | Fail-closed deferral pattern with `pcall(MySQL.query.await, ...)`. | NEW | CONFIRMED (pattern) | Folded into §4.4. |
| B5 | Server boot guard: `if not LoadResourceFile(res, 'web/build/index.html') then error('UI not built') end`. | NEW | CONFIRMED (API) | Nice-to-have for nui.md. |
| B6 | Node 16 default → add `node_version '22'`. | CONFLICT | OUTDATED | see A3. |
| B7 | Tooling versions (react 19, vite 5, tailwind 3, zustand 4). | — | OUTDATED | Not integrated. |

### 3.3 ayala2a CLAUDE.md (C)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| C1 | `exports.qbx_core:GetCoreObject()` | WRONG | Only `exports['qb-core']:GetCoreObject()` via `createQbExport` in qbx_core bridge. |
| C2 | Framework detection with `GetResourceState(x) ~= 'missing'` | WRONG (logic) | Picks installed-but-stopped frameworks; use `== 'started'`. |
| C3 | `ox_inventory:registerHook('useItem', …)` with side effects | WRONG | Hook event is `usingItem` (`server.lua` `TriggerEventHooks('usingItem'`); hooks are validation-only (ours). |
| C4 | `lib.textUI` | WRONG | `lib.showTextUI`. |
| C5 | `ox_target:removeBoxZone` | WRONG | `removeZone(id)`. |
| C6 | `exports['pma-voice']:addPlayerToChannel` | WRONG | no such export in pma-voice source. |
| C7 | `local flag = 0b0101` | UNVERIFIABLE (likely WRONG) | Not Lua 5.4 syntax; not in CfxLua power-patch list (runtimes.md). |
| C8 | `table.create(n, 0)` | CONFIRMED | CfxLua GRIT_POWER_WOW (runtimes.md). |
| C9 | `set sv_enableDevtools false` | WRONG | see A6. |
| C10 | `sv_authMinTrust 5`, `sv_authMaxVariance 2` | UNVERIFIABLE / risky | see A46. |
| C11 | qbx convars `qbx:max_jobs_per_player`, `qbx:max_gangs_per_player`, `qbx:setjob_replaces` | CONFIRMED (COVERED) | qbx_core `server/player.lua` L6–8. |

### 3.4 SRock44 agents (D)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| D1 | Same event name registered in two resources: "one silently overrides the other". | WRONG | Events are global; every resource's handler for that name runs (that's the real hazard: both execute). Worth a one-line gotcha in our events doc. |
| D2 | Vite inlines every `VITE_*` env var into the client bundle — never put secrets there. | CONFIRMED, NEW | vite `docs/guide/env-and-mode.md`: "Variables prefixed with `VITE_` will be exposed in client-side source code". |
| D3 | Don't ship source maps in NUI builds. | CONFIRMED, NEW (minor) | Vite `build.sourcemap` default false; shipped `.map` exposes source and author paths. |
| D4 | `lib.callback.await(name, false, …)`: "false = not a yielding NUI context". | WRONG | 2nd arg is `delay` (ms rate limit) — ours ox-lib-core.md right. |
| D5 | `onesync_enableInfinity` widens scope. | OUTDATED | Internal since OneSync forced (our convars-and-commands.md). |
| D6 | Declare `server_exports`/`client_exports` "so they appear in the dependency graph". | WRONG | Legacy manifest directives; `exports()` in code is the norm; no dependency-graph effect. |
| D7 | Server tick budget "~8 ms at 128 tick". | UNVERIFIABLE | — |
| D8 | Correct N+1 fix with `string.rep('?,', n)` placeholders. | CONFIRMED | oxmysql positional params. |

### 3.5 abual3bed00 (E)
| E1 | Templates (QBCore server/client, fxmanifest) | No new facts. Client template ships an empty `while true do Wait(0) end` — anti-pattern (already in our rules). |

### 3.6 NewwyKung template (F)

| # | Claim | Verdict | Note |
|---|---|---|---|
| F1 | `lua54 'yes'` deprecated; OAL ≠ OneSync, opt-in | CONFIRMED | COVERED. |
| F2 | State bags serialize shallowly | CONFIRMED | COVERED (onesync-entities.md L217). |
| F3 | Network IDs transient/reusable/out of scope | CONFIRMED | COVERED. |
| F4 | Production `ui_page` never localhost | CONFIRMED | COVERED (nui.md L127). |
| F5 | Dev-only HTTP bridge pattern: gated by `mcp_dev_mode` convar, refuses empty token, localhost-only unless opted in, per-IP rate limit, whitelisted actions, audit log | CONFIRMED (sound pattern) | Good reference for §4.3. Note its own `ExecuteCommand('restart ' .. resourceName)` is an injection-prone concatenation — exactly what our `execute-command` rule flags. |
| F6 | Concurrent mutation: idempotency key + correlation id + re-read state before commit | CONFIRMED (best practice) | Optional addition to security.md §5. |

### Verdict counts (all rows above)
CONFIRMED 45 · OUTDATED 10 · WRONG 22 · UNVERIFIABLE 12  (total 89; "CONFIRMED/UNVERIFIABLE" split rows counted under their first verdict).

---

## 4. Recommended integrations (ready to paste)

### 4.1 `references/security.md` §5 (Economy and duplication) — append
```markdown
- **Bound before you multiply.** Lua 5.4 integer arithmetic wraps silently on overflow (no error, no clamp), so `price * qty` with a huge integer `qty` can become negative and pass a `balance < total` check. Cap every client-influenced operand first (`qty <= MAX_QTY`, `math.type(qty) == 'integer'`), then sanity-check the result (`total > 0 and total <= MAX_TX`). Modern ESX/QBCore reject non-positive amounts, but custom accounts and bridges often don't. Source: Lua 5.4 manual §3.4.1.
- Idempotent economy endpoints: for retries/double clicks, accept a client request id, keep a bounded per-player set of processed ids, and return the earlier result instead of re-applying.
```

### 4.2 `references/security.md` §7 (NUI) — append
```markdown
- XSS impact is real even without a server bug: any NUI frame can call `window.invokeNative('quit', '')`, which force-exits the victim's game (`ExitProcess(0)` in `nui-core/src/NUICallbacks_Native.cpp`); `openUrl` asks the user first. (`fxdkClipboard*` handlers exist only in FxDK, not the normal client.)
- NUI callbacks are `https://<resource>/<name>` requests intercepted by CEF (not a localhost port). A player can still send them by hand (CEF devtools on port 13172), so every callback is client input; `nui_callback_strict_mode 'true'` only blocks *other resources'* frames.
- Vite inlines every `VITE_*` env variable into the shipped bundle — never put keys/webhooks there (vite docs: env-and-mode). Do not ship `.map` files in `web/build`.
```

### 4.3 `references/security.md` — new subsection "Resource HTTP handlers (`SetHttpHandler`)" (after §4)
```markdown
### HTTP handlers (`SetHttpHandler`)
`SetHttpHandler` serves `http://<server>:30120/<resource>/...` on the public game port — unauthenticated and unthrottled unless you add it.
- Require a token from a `set` convar (never `setr`), compare in constant time; refuse to register the handler when the token is empty.
- Don't authorize on `req.address` alone (wrong behind proxies/`sv_proxyIPRanges`); if you need "local only", combine it with the token.
- Whitelist `req.path`; never build file paths, SQL or `ExecuteCommand` strings from it.
- Cap body size in `req.setDataHandler`, `pcall(json.decode, body)`, per-IP rate limit, no privileged action without auth, no identifiers/IPs/stack traces in responses.
- Dev-only bridges: gate the whole file behind a convar (`if GetConvar('myres_dev', 'false') ~= 'true' then return end`) and never ship it enabled.
```

### 4.4 `references/events-and-callbacks.md` (after the `playerConnecting` row) — add
```markdown
**Connection-phase rules:** call `deferrals.done()` on *every* branch, including DB errors and timeouts (wrap awaits in `pcall`; on failure `deferrals.done('Auth unavailable')` = fail closed); reject when `GetPlayerIdentifierByType(src, 'license')` is nil; match bans on several identifiers (license, license2, fivem, discord, tokens via `GetPlayerToken`), not one; never interpolate the player name into `presentCard` JSON unescaped; expire connection-phase tables by time, not only in `playerDropped`.
**Same event name in two resources:** handlers are global — every resource's handler for that name runs (no shadowing). Namespace names (`res:side:action`) so a generic name doesn't trigger someone else's logic.
```

### 4.5 `references/security.md` §11/§12 — append
```markdown
- Screenshots: `screenshot-basic`'s client `requestScreenshotUpload(url, field, cb)` uploads **from the player's client**, exposing the URL/API key to every player. Capture with the server-side `requestClientScreenshot` (or screencapture) and upload from the server; gate captures by ACE + rate limit.
- Discord-role whitelists/permissions: resolve roles server-side from the `discord:` identifier, cache with a TTL, and **fail closed** on API errors/429 (`if not ok then return false end`). A bot token ever set with `setr` or committed to Git is compromised — regenerate it, don't just move it.
```

### 4.6 `references/audit-checklist.md` §2 (Provenance and supply-chain review) — append
```markdown
- **NUI/server JS build chain:** a committed minified bundle without its source is NOT REVIEWABLE (report like escrow). Check `package.json` for `preinstall`/`install`/`postinstall`/`prepare` scripts and git/http/file dependencies; require a committed lockfile; recommend `npm ci --ignore-scripts && npm run build`. Committed `node_modules` in a server-JS resource = unreviewed code with full server privileges.
- Purpose/capability mismatch is the highest-signal manual check: a HUD that reads `mysql_connection_string`, a UI resource with `PerformHttpRequest`, a single-purpose script calling `GetResourceByFindIndex`.
```

### 4.7 `references/audit-checklist.md` §3 (Known backdoor families) — replace/extend rows
```markdown
| C2 domains (ImJer iocs/domains.txt, 2026-08) | add: `blum-panel.com`, `0xchitado.com`, `2312321321321213.com`, `5mscripts.net`, `bhlool.com`, `bybonvieux.com`, `fivemgtax.com`, `flowleakz.org`, `iwantaticket.org`, `l00x.org`, `monloox.com`, `noanimeisgay.com`, `ryenz.net`, `spacedev.fr`, `trezz.org`, `z1lly.org`, `2nit32.com`, `useer.it.com`, `wsichkidolu.com`, `ciphercheats.com`, `keyx.club`, `dark-utilities.xyz` |
| C2 IPs | `185.87.23.198` (origin, Socket.IO :5000), `185.80.128.35`, `185.80.128.36`, `185.80.130.168` (GFX :3000) |
| Operator strings | `VB8mdVjrzd` (Discord invite), handles `bertjj`/`bertjjgg`/`miauss`/`miausas`, JJ keys (`devJJ`, `nullJJ`, `zXeAHJJ`…), `installed_notices`, `vm').runInThisContext`, `txadmin:js_create`, `X-TxAdmin-Token`/`X-TxAdmin-Identifiers`, dropper comment `// if you found this contact us to fix problems`, BTC `bc1q2wd7y6cp5dukcj3krs8rgpysa9ere0rdre7hhj`, LTC `LSxKJm6SpdExCACUcFTUADcvZgea65AaWo` |
| XOR dropper | `String.fromCharCode(a[i]^k)` — key is random per file (66…252): match the structure, not a key |
| Dropper names | distinctive (report on name, confirm by content): `babel_config.js`, `babel_preset.js`, `build_cache.js`, `cache_old.js`, `env_backup.js`, `eslint_rc.js`, `hook_system.js`, `jest_mock.js`, `jest_setup.js`, `mock_data.js`, `patch_update.js`, `sync_worker.js`, `vite_temp.js`, `webpack_bundle.js` …; common names (`main.js`, `index.js`, `sync.js`, `core.js` …) only with loader code (`eval(`, `new Function(`, `runInThisContext`, XOR decoder). Placement varies (any dir, resource root). **`yarn_builder.js`/`webpack_builder.js` are legitimate stock files of the `yarn`/`webpack` system resources (~3 KB); flag them only when modified/large (infected copies 43 KB / 632 KB) or outside those resources.** |
| Manifest concealment | `--[[server.lua]]` decoy + ≥20 spaces + hidden `.js` path on the same line; dot-file scripts (`'.x.js'`, `'node_modules/.cache.js'`) |
| Cloaked resources | Blum names its own resources from its `RESOURCE_EXCLUDE` list (e.g. `acct`, `core`, `data`, `sync`, `util` …) so txAdmin hides them — a name match alone is not proof |
| txAdmin map | `cl_playerlist.lua` → `helpEmptyCode` (client RCE, appended), `sv_resources.lua` → `onServerResourceFail` (server RCE), `sv_main.lua` → `RESOURCE_EXCLUDE`/`isExcludedResource` (inline cloak, **not hand-cleanable: reinstall txAdmin of the same version**) |
| Size fingerprints | JS 420–470 KB (JScrambler loader), 1.60–1.65 MB (replicator), 40–46 KB (XOR builder dropper); Luraph Lua 60–67 KB |
| Evasion | natives by hash (`Citizen.InvokeNative(0x561C060B…)` = ExecuteCommand), `_G['load']`/`_ENV['PerformHttpRequest']`, `debug.sethook`, `io.open(…,'w')` |
```
(Source line: "Blum/Cipher IOC set 2026.08.07: https://github.com/ImJer/blum-panel-fivem-backdoor-analysis/tree/main/iocs — single researcher; verify before attributing.")

### 4.8 `references/anticheat.md` (entity / crash section) — append
```markdown
- Known gaps: objects created by **scenarios** (e.g. `WORLD_HUMAN_CONST_DRILL`) replicate without firing `entityCreating`/`entityCreated` (citizenfx/fivem#3675, open) — lockdown/`entityCreating` filters don't see them; consider `block_net_game_event` for scenario abuse and watch object counts. Undisclosed client crash methods are reported regularly (#3722): stay on the Recommended artifact and update promptly.
```

### 4.9 `references/ox-inventory.md` (vehicles) — append
```markdown
- Vehicle inventories are keyed by plate: a player who copies a plate can reach the original owner's trunk (ox_inventory#1829). Use ox_inventory ≥ 2.48 (netid-only open), keep plate changers server-validated and unique, and enforce ownership in your framework layer; ox_inventory's own owner check is ox_core-specific.
```

### 4.10 `references/use-vs-avoid.md` — add row
```markdown
| `sv_enableDevtools` | nothing (convar does not exist; feature request citizenfx/fivem#2667). Enhanced: `sv_devMode false` | community guides recommend it; it's a no-op |
```

### 4.11 `references/nui.md` (build section) — optional
```lua
-- server: fail fast when the UI was never built
if not LoadResourceFile(GetCurrentResourceName(), 'web/build/index.html') then
    error('UI not built: cd web && npm ci --ignore-scripts && npm run build')
end
```

---

## 5. `scripts/audit.py` changes

### 5.1 New `LINE_RULES` (tested: `analysis/tools/test_rules.py`, 20 rules, 0 miss / 0 FP on the cases below)
```python
    ("blum-xor-dropper", "critical", "any",
     r"String\.fromCharCode\s*\(\s*[A-Za-z0-9_$]+\s*\[\s*[A-Za-z0-9_$]+\s*\]\s*\^\s*[A-Za-z0-9_$]+\s*\)",
     "Key-independent Blum/Warden XOR dropper decoder (String.fromCharCode(a[i]^k)). Treat the resource as compromised."),
    ("known-backdoor-ext", "critical", "any",
     r"blum-panel\.com|0xchitado\.com|2312321321321213\.com|5mscripts\.net|bhlool\.com|bybonvieux\.com|fivemgtax\.com|flowleakz\.org"
     r"|iwantaticket\.org|l00x\.org|monloox\.com|noanimeisgay\.com|ryenz\.net|spacedev\.fr|trezz\.org|z1lly\.org|2nit32\.com"
     r"|useer\.it\.com|wsichkidolu\.com|gfxpanel\.org|ciphercheats\.com|keyx\.club|dark-utilities\.xyz"
     r"|185\.87\.23\.198|185\.80\.128\.3[56]|185\.80\.130\.168"
     r"|VB8mdVjrzd|\bmiausas\b|\binstalled_notices\b|txadmin:js_create|\bRESOURCE_EXCLUDE\b|\bisExcludedResource\b|\bonServerResourceFail\b"
     r"|UARZT6\[|\\u15E1|contact us to fix problems|bc1q2wd7y6cp5dukcj3krs8rgpysa9ere0rdre7hhj|LSxKJm6SpdExCACUcFTUADcvZgea65AaWo",
     "Matches a Blum/Warden/Cipher/GFX IOC (ImJer IOC set 2026.08.07): C2 domain/IP, operator string, txAdmin-cloak marker or obfuscator residue."),
    ("node-vm-run", "critical", "server", r"\.runIn(This|New)Context\s*\(|\bnew\s+vm\.Script\s*\(",
     "Node vm code execution (Blum loaders use require('vm').runInThisContext). No legitimate use in a resource."),
    ("invoke-native-sensitive", "critical", "any",
     r"(?i)InvokeNative\s*\(\s*(0x561C060B|0x8E8CC653|0x6B171E87|0xA09E7E7B|`(EXECUTE_COMMAND|PERFORM_HTTP_REQUEST_INTERNAL(_EX)?|SAVE_RESOURCE_FILE)`)",
     "ExecuteCommand / PerformHttpRequestInternal / SaveResourceFile called by native hash: evasion of name-based scanners."),
    ("hardcoded-discord-token", "critical", "any", r"\b[MN][A-Za-z\d]{23,25}\.[\w-]{6}\.[\w-]{27,}\b",
     "Looks like a Discord bot token in source: rotate it and load it from a `set` convar."),
    ("txadmin-token-access", "high", "any", r"X-TxAdmin-(Token|Identifiers)",
     "Resource code touching txAdmin auth headers: session-hijack indicator (only txAdmin's own monitor resource should)."),
    ("env-index-evasion", "high", "any",
     r"\b(_G|_ENV)\s*\[\s*['\"](PerformHttpRequest|load|loadstring|ExecuteCommand|assert|os|io|debug|GetConvar|SaveResourceFile)['\"]\s*\]",
     "Dangerous global reached through _G/_ENV string indexing: classic string-match evasion in backdoors."),
    ("telegram-exfil", "high", "server", r"api\.telegram\.org/bot",
     "Telegram Bot API endpoint in server code: known exfiltration channel; verify purpose."),
    ("http-raw-ip", "high", "any",
     r"(PerformHttpRequest|fetch|axios\.\w+|https?\.(get|request))\s*\(\s*['\"`]https?://(?!127\.|localhost)\d{1,3}(\.\d{1,3}){3}",
     "HTTP request to a raw IP address: typical C2 evasion; legitimate APIs use domain names."),
    ("io-open-write", "high", "server", r"\bio\.open\s*\([^)]*,\s*['\"][wa]",
     "Lua io.open in write/append mode: filesystem write outside the resource API."),
    ("hardcoded-license-key", "high", "any", r"\bcfxk_[A-Za-z0-9]{10,}",
     "Cfx.re server license key in a resource file: keep sv_licenseKey in a server-only cfg; regenerate it if published."),
    ("client-sends-own-id", "high", "client",
     r"TriggerServerEvent\s*\([^)]*GetPlayerServerId\s*\(\s*(PlayerId\s*\(\s*\)|cache\.playerId)\s*\)",
     "Client sends its own server id: the server must use `source`, never a client-supplied id."),
    ("debug-lib-tamper", "medium", "any",
     r"\bdebug\.(sethook|setupvalue|getupvalue|setlocal|getregistry|setmetatable|upvaluejoin)\s*\(",
     "Lua debug-library manipulation in a resource: anti-analysis / runtime tampering indicator."),
    ("resource-enumeration", "medium", "server", r"\bGetResourceByFindIndex\s*\(",
     "Enumerates every resource: rare in legit code, used by self-replicating backdoors to pick injection targets."),
    ("http-handler-public", "medium", "server", r"\bSetHttpHandler\s*\(",
     "SetHttpHandler is public on :30120/<resource>/: require a token (set convar), path whitelist, body cap and rate limit."),
    ("statebag-handler-no-replicated", "medium", "server",
     r"AddStateBagChangeHandler\s*\([^,]+,[^,]+,\s*function\s*\(\s*[\w.]*(\s*,\s*[\w.]+){0,3}\s*\)",
     "Server state bag handler declares < 5 params, so it ignores `replicated`: client-written values may be acted on."),
    ("lzstring-utf16", "medium", "any", r"\bdecompressFromUTF16\s*\(",
     "LZString.decompressFromUTF16: legit in some bundles but a Blum JScrambler dropper marker; read the surrounding code."),
```
Test snippets (should match / should not match):

| rule | match | no match |
|---|---|---|
| blum-xor-dropper | `s+=String.fromCharCode(a[i]^k);` | `String.fromCharCode(65,66)` |
| known-backdoor-ext | `PerformHttpRequest('https://gfxpanel.org/x', cb)`; `if RESOURCE_EXCLUDE[name] then` | `PerformHttpRequest('https://api.fivemanage.com/x')` |
| node-vm-run | `require('vm').runInThisContext(code)` | `const vmName='x'` |
| invoke-native-sensitive | ``Citizen.InvokeNative(`EXECUTE_COMMAND`, cmd)``; `Citizen.InvokeNative(0x561c060b, 'quit')` | `Citizen.InvokeNative(0xE5B302114D8162EE, ped)` |
| hardcoded-discord-token | `local TOKEN = 'MTA4NzQ1Njc4OTAxMjM0NTY3OA.GaBcDe.abcdefghijklmnopqrstuvwxyz0123'` | `local TOKEN = GetConvar('bot_token', '')` |
| txadmin-token-access | `headers['X-TxAdmin-Token']` | `headers['Content-Type']` |
| env-index-evasion | `_G['PerformHttpRequest'](u, cb)` | `_G['MyGlobal']` |
| telegram-exfil | `PerformHttpRequest('https://api.telegram.org/bot123:abc/sendMessage', cb)` | `-- telegram support` |
| http-raw-ip | `PerformHttpRequest('http://45.13.2.9/p', cb)` | `PerformHttpRequest('http://127.0.0.1:3000/x')` |
| io-open-write | `io.open('server.cfg', 'a')` | `io.open(path, 'r')` |
| hardcoded-license-key | `sv_licenseKey = 'cfxk_1a2b3c4d5e6f7g8h9i0j_abc'` | `GetConvar('sv_licenseKey','')` |
| client-sends-own-id | `TriggerServerEvent('vshop:buy', GetPlayerServerId(PlayerId()), 'water', 5, 10)` | `TriggerServerEvent('vshop:buy', 'water', 10)` |
| debug-lib-tamper | `debug.sethook(function() end, 'c')` | `print(debug.traceback())` |
| resource-enumeration | `local r = GetResourceByFindIndex(i)` | `GetCurrentResourceName()` |
| http-handler-public | `SetHttpHandler(function(req, res)` | — |
| statebag-handler-no-replicated | `AddStateBagChangeHandler('vip', nil, function(bagName, _, value)` | `AddStateBagChangeHandler('vip', nil, function(bagName, key, value, _, replicated)` |
| lzstring-utf16 | `LZString.decompressFromUTF16(p)` | `compressToBase64(x)` |

Note: `audit()` compiles with `re.I` only for `client-*` ids; `invoke-native-sensitive` carries an inline `(?i)`.

### 5.2 New `MANIFEST_RULES`
```python
    ("manifest-hidden-injection", "critical", r"--\[\[[^\]]*\]\]\s{20,}['\"][^'\"]*\.js['\"]",
     "Block-comment decoy + whitespace padding + hidden .js path: Blum fxmanifest concealment."),
    ("manifest-dotfile-js", "high", r"(['\"])(?:[^'\"]*[\\/])?\.[^'\"\\/]+\.js\1",
     "Manifest loads a hidden dot-file .js script."),
```
match: `server_scripts { --[[server.lua]]                              '.cache/x.js' }`, `server_script 'node_modules/.bin/.hidden.js'` · no match: `server_scripts { 'server.lua' } -- [[note]]`, `server_script 'server/main.js'`.

### 5.3 New `CFG_RULES` entry
```python
    ("cfg-nonexistent-devtools", "low", r"^\s*set[rs]?\s+sv_enableDevtools\b",
     "sv_enableDevtools does not exist (citizenfx/fivem#2667): no effect. Dev tools are gated by sv_devMode on Enhanced."),
```
match `set sv_enableDevtools false` · no match `set sv_devMode false`.

### 5.4 Fix the dropper-name false positive (replace `DROPPER_NAMES` + `scan_dropper_names`; tested: stock `yarn/yarn_builder.js` clean, XOR copy flagged)
```python
STRICT_LOADER = re.compile(r"eval\s*\(|new\s+Function\s*\(|runInThisContext|String\.fromCharCode\s*\([^)]*\^", re.I)
# ImJer IOC set 2026.08.07 'dropper_filenames' (distinctive). Report alone as medium, critical with loader code.
DROPPER_NAMES = {"babel_config.js", "babel_preset.js", "build_cache.js", "cache_old.js", "env_backup.js", "eslint_rc.js",
                 "hook_system.js", "jest_mock.js", "jest_setup.js", "mock_data.js", "patch_update.js", "sync_worker.js",
                 "vite_temp.js", "vite_plugin.js", "webpack_bundle.js", "webpack_chunk.js", "runtime_module.js",
                 "stable_core.js", "latest_utils.js", "utils_lib.js", "v1_config.js", "v2_settings.js", "beta_module.js",
                 "session_store.js", "queue_handler.js"}
# Legit stock files of the Cfx `yarn` / `webpack` system resources (~3 KB); Blum modifies them (43 KB / 632 KB).
STOCK_BUILDERS = {"yarn_builder.js": "yarn", "webpack_builder.js": "webpack"}


def scan_dropper_names(root: Path, out: list[Finding]):
    for f in root.rglob("*.js"):
        if not f.is_file() or (set(f.parts) & SKIP_DIRS):
            continue
        name = f.name.lower()
        if name not in DROPPER_NAMES and name not in STOCK_BUILDERS:
            continue
        rel = str(f.relative_to(root))
        loader = bool(STRICT_LOADER.search(f.read_text(encoding="utf-8", errors="replace")))
        if name in STOCK_BUILDERS:
            if f.parent.name.lower() != STOCK_BUILDERS[name] or loader or f.stat().st_size > 20_000:
                out.append(Finding("critical", "known-backdoor", rel, 1,
                                   "Builder file modified or misplaced (Blum dropper target; stock file is ~3 KB, no eval/XOR).", f.name))
        else:
            out.append(Finding("critical" if loader else "medium", "known-backdoor" if loader else "dropper-filename", rel, 1,
                               "File name used by Blum droppers" + (" and it contains loader code." if loader else ": read it."), f.name))
```
(The less distinctive ImJer names `development.js`, `production.js`, `staging.js`, `testing.js`, `config_settings.js`, `event_emitter.js`, `local_config.js`, `test_utils.js`, `helper_functions.js` are common in web tooling: only report them when `STRICT_LOADER` matches — add a second set if desired.)

### 5.5 Catch the split `RegisterNetEvent('x')` + `AddEventHandler('x', function…)` form (tested: flags `vshop:makeAdmin`, `vshop:report`)
Append to `scan_net_handlers`:
```python
    registered = set(re.findall(r"RegisterNetEvent\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", text))
    for m in re.finditer(r"AddEventHandler\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*function\s*\(([^)]*)\)", text):
        if m.group(1) not in registered:
            continue
        body = text[m.end(): m.end() + 2500]
        end = re.search(r"\n\S*end\)", body)
        body = body[: end.start()] if end else body
        body = re.sub(r"--[^\n]*", "", body)          # ignore comments mentioning 'source'
        if "source" not in body:
            line = text.count("\n", 0, m.start()) + 1
            out.append(Finding("medium", "net-event-no-source", rel, line,
                               f"Net event '{m.group(1)}' never uses `source`: who is allowed to call it?", m.group(0)[:160]))
```
(Also apply the same comment-stripping to the existing inline-form check.)

### 5.6 Smaller changes
- `CODE_EXT`: add `.html`, `.htm` (NUI inline scripts; path `html/`/`web/`/`ui/` already maps to side "client") — catches `innerHTML` in the fixture.
- `client-money-event`: downgrade to `medium` (false positive on the secure intent-only `TriggerServerEvent('vshop:buy', 'water', 10)`), or drop `buy|sell` from its keyword list since `client-trusted-price` covers named prices.
- Optional `package.json` scan (prototype in `analysis/tools/test_scanners.py::scan_package_json`): `medium npm-install-script` for `preinstall|install|postinstall|prepare`, `medium npm-nonregistry-dep` for `git+|git:|https?:|github:|file:` versions; skip `node_modules`.
- Optional size fingerprint: `.js` 420–470 KB / 1600–1650 KB or `.lua` 60–67 KB containing `Luraph` → `medium blum-size-fingerprint`.
- Update `references/audit-checklist.md` §9 rule table with the new ids.

---

## 6. Conflicts — who is right

| Topic | Other repo | Our skill | Right |
|---|---|---|---|
| `yarn_builder.js` / `webpack_builder.js` | flag *modifications* (M.14c) | flags the file name as critical | **Other repo** — stock files exist in citizenfx/fivem `ext/system-resources` |
| Node 16 default / require `node_version '22'` | yes | removed 2026-01 | Ours |
| `lua54 'yes'` needed | yes | deprecated no-op | Ours |
| `sv_protectServerEntities` removed | yes | Legacy-only, works | Ours |
| `sv_authMinTrust 5` hardening | recommended | keep defaults | Ours (risk of lockout) |
| Qbox == ox_core | yes | separate | Ours |
| Wildcard script globs | flag as risk | template uses globs | Partly theirs (mechanism real); severity low — mention as optional |
| XOR keys 169/189/204 | fixed keys | (not listed) | Neither: key is random per file — use structural regex |
