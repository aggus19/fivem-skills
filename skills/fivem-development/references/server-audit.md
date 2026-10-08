# Whole-server audit: deterministic procedure and coverage contract

Use when the target is a server or a `resources/` folder (more than one resource), or when
the user asks to "analyse/audit/review my server/project". For one resource,
[audit-checklist.md](audit-checklist.md) alone is enough. This file decides **what** is
reviewed and **when the audit is complete**, so that two reviewers (or two different models)
using the skill on the same tree produce the same inventory, the same coverage numbers and
the same class of findings. audit-checklist.md stays the reference for *how* to judge each
item (backdoor indicators, §6 server authority, report wording).

## Contents
1. Contract
2. Phase 0: scope and evidence
3. Phase 1: server inventory (`project.py`)
4. Phase 2: heuristic scan (`audit.py`) and triage
5. Phase 3: endpoint coverage (`surface.py`)
6. Phase 4: manifests, natives and performance
7. Parallel review (sharding)
8. Economy exploit classes (always check)
9. Severity rubric
10. Known false positives (dismiss consistently)
11. Report template

## 1. Contract
- **Enumerate with tools, never by sampling.** Inventories come from `project.py`, `audit.py --json` and `surface.py`; their numbers go into the report unchanged. A reviewer may add items, never silently drop them.
- **Coverage is explicit.** Every `surface.py` ledger row ends as `finding`, `ok` (one-line reason), `opaque` or `not-reviewed` (reason). The report states the counts. "Reviewed the important ones" is not a valid scope.
- **Stop rule.** The audit is complete when: (a) every Phase 1 high/medium item is in the report; (b) every Phase 2 finding in the categories Backdoor/RCE, SQL and Trust boundary is confirmed or dismissed with a reason, whatever its severity; (c) no ledger row is `TODO`. Otherwise, publish as **partial** and list what is left.
- **Facts carry citations.** A version, a missing file or a convar is reported with `file:line` from the tool output. Never write "up to date" / "al día" without the `project.py` versions row.
- **Same tree.** State what was audited: path, git HEAD and whether uncommitted changes were included (`project.py` repo section). Two audits of different trees are not comparable.
- **Do not block on questions.** Unknown provenance, licences or runtime data are recorded as `unknown` and the audit continues; ask at the end.

## 2. Phase 0: scope and evidence
1. Resolve the server root and the resources directory (they may be the same folder).
2. Record git HEAD, dirty state and submodules (Phase 1 prints them). If the working tree differs from HEAD, audit the working tree (it is what runs) and say so.
3. Provenance per resource: own / official release / purchased (Tebex, Portal) / leaked / unknown. Leaked = treat as malware (audit-checklist.md §2); unknown = continue.
4. Never print secrets. Report that a secret exists at `file:line` and that it must be rotated; do not echo the value.

## 3. Phase 1: server inventory
```
python scripts/project.py                     # from the server root, resources/ or any folder inside it
python scripts/project.py --json > inventory.json
python scripts/logs.py                        # runtime evidence: finds txData/<profile>/logs/fxserver.log
```
It computes, the same way every time:
- **stack:** framework, inventory, target, DB driver, voice, phone... with the reference to read for each. Review economy handlers against the installed owner of money/items, never against a template; multiple frameworks/inventories are a finding.
- **launch cfg:** the txAdmin `cfgPath` when a txAdmin profile points at this server (dev and prod cfg pairs are common), else `server.cfg`; `--cfg` overrides.
- **cfg:** `exec` chain from `server.cfg`, cfg files that are not exec'd (often `+exec` on the command line, analysed separately), convars set twice with different values, removed `sv_experimental*` convars.
- **ensure:** `ensure`/`start` targets that match no folder or category (a typo such as `[cloth]` vs `[clothe]` silently starts nothing), resource names that exist twice, resources never started, dependencies started after their dependants.
- **versions:** installed `fxmanifest.lua` version of every resource listed in `assets/baseline.json`, classified `< min-safe` / `< baseline` / `= baseline` / `> baseline` / `unknown`, with `file:line`. A fork may carry a stale manifest: say so, do not guess.
- **datafiles:** every `data_file` path resolves to a file (`[category]` folders are literal names) and is covered by `files {}`.
- **assets:** streamed files over 16 MiB, repeated streamed file names, largest resources.
- **repo:** HEAD/dirty state, deleted tracked files, nested `.git`/`node_modules` in resources, `*.bat`/`*.cmd`/`*.ps1`/`*.sh` that reference missing files.

Secrets in cfg files (`cfg-public-secret`, plaintext keys) come from Phase 2; `project.py` never prints values.

`logs.py` adds what static analysis cannot see: resources that failed to start (escrow entitlement, missing category), script errors with their first stack frame, slow queries and oversized result sets per resource, hitches, oversized streamed assets and secrets printed to the console. Report its high/medium groups in the Inventory section, mark dev-only causes (escrow on a dev key, local endpoints) as such, and use [console-logs.md](console-logs.md) for meaning and fix.

## 4. Phase 2: heuristic scan and triage
```
python scripts/audit.py <resources dir> --json > audit.json        # all severities
```
Triage rules (identical for every reviewer):
1. **Backdoor/RCE, SQL and Trust boundary rules** (audit-checklist.md §9 table): confirm or dismiss **every** hit, any severity. Use §10 below for known false positives so the same hit is dismissed the same way.
2. **Manifest and server.cfg rules:** report every hit (they are facts, not heuristics) with the fix.
3. **Legacy/perf rules** (`wait-zero-loop`, `citizen-prefix`, `draw-marker-everywhere`...): do not list hundreds of lines. Report counts per resource and the confirmed per-frame offenders (§6).
4. Hits in vendored dependencies (ox_*, oxmysql, chat, yarn/webpack, screenshot-basic) are triaged once, with the reason, and then grouped.

## 5. Phase 3: endpoint coverage
```
python scripts/surface.py <resources dir>                          # summary by resource
python scripts/surface.py <resources dir> --ledger ledger.md       # one row per endpoint with sinks or tags
```
`surface.py` lists every client-reachable server entry point (net events in both forms, `lib.callback.register`, ESX/QBCore callbacks, custom `*.Register*Event`/`*Callback` wrappers, commands, exports, `SetHttpHandler`, JS `onNet`), the sinks each one reaches (money, items, vehicles, jobs/permissions, SQL writes, coords/routing buckets, spawns, `ExecuteCommand`, broadcasts, state bags) including through same-resource helper functions, and fixed-meaning risk tags.

For **each ledger row**, read the handler and apply audit-checklist.md §6 (all 13 points) plus §8 below, then set the status:
- `finding` - link the report item (one finding may cover several rows that share a cause).
- `ok` - one line saying why (e.g. "amount from server config; job checked; cooldown via players_time").
- `opaque` - escrowed (`FXAP` header / `.fxap`), obfuscated or minified without source.
- `not-reviewed` - only with a reason (time box, out of scope requested by the user).

Rows without sinks or tags (`--all` shows them) are read-only or display endpoints: skim them for amplification (§6 point 10) and info leaks, no status required.

Tags are leads, not verdicts: a tag can be dismissed with a reason; an untagged row with sinks is still reviewed.

## 6. Phase 4: manifests, natives and performance
- `python scripts/manifest.py <resources dir>` checks every resource (exposed server files, missing files, `ui_page`, `data_file`).
- `python scripts/natives.py check <own resource> --strict` on the resources the owner maintains; on vendored or obfuscated code it only produces noise. Report coverage as "lexical check on N resources".
- Performance is **static** unless a profile/resmon capture exists: list per-frame threads without gating, pool scans in loops, NUI messages per tick, broadcasts to `-1`, DB queries per tick/per call, synchronous DB calls in handlers (`MySQL.Sync.*`, `.await` in hot paths), oversized assets from Phase 1. Mark every cost **unmeasured**; never invent milliseconds. Measuring: [hitch-diagnostics.md](hitch-diagnostics.md), [performance.md](performance.md).

## 7. Parallel review (sharding)
When several reviewers (subagents) share the work, split **the ledger**, not the reviewers' judgement:
```
python scripts/surface.py <resources dir> --shard 1/3 --ledger ledger-1.md
python scripts/surface.py <resources dir> --shard 2/3 --ledger ledger-2.md
python scripts/surface.py <resources dir> --shard 3/3 --ledger ledger-3.md
```
Shards are deterministic and balanced by resource. Give each reviewer its ledger file, this file, audit-checklist.md §6 and security-validation.md; do not hand them a list of "suspicious files" chosen by hand (that is what made two audits disagree). Phase 1 and the Phase 2 triage of cfg/manifest/version facts are done once by the coordinator. Merge: union of findings, sum of statuses; any `TODO` left makes the report partial.

## 8. Economy exploit classes (always check)
Each class names the `surface.py` tag / `audit.py` rule that points at it. Fix pattern: [security.md](security.md), [security-validation.md](security-validation.md).

| Class | Signature | Tag / rule | Correct pattern |
|---|---|---|---|
| Client-chosen amount | price/amount/count/bet/reward from the client reaches money or items | `client-value-in-sink`, `client-trusted-price` | Amount from server config/state; client sends only an id/choice |
| Fractional or negative amount | `tonumber(x)` without integer check; ESX accounts with `round = true` round **after** the `> 0` check (0.4 charges 0 but the item is delivered) | `non-integer-amount` | `math.tointeger(n)` + `1 <= n <= MAX` |
| No balance check | `removeAccountMoney` / `removeMoney` without reading the balance (ESX has no floor) | `no-balance-check` | read balance, then remove; or a framework call that fails on insufficient funds |
| Pay before validate | credit happens before a later return/ban/time check | `credit-before-guard` | all checks first, then mutate |
| Removal result ignored | `RemoveItem(...)` result not checked before paying | `unchecked-removal` | `if not RemoveItem(...) then return end` |
| Client-reported position/distance | job payment by `data.distance`, distance check against `dt.pos` / client coords | `client-position`, `client-reported-position` | `GetEntityCoords(GetPlayerPed(source))` and server-side route state |
| Client-chosen target | target id / passengers / closest player from the client; routing bucket or teleport of other players | `client-target` | server distance + relationship check (same vehicle, invited, in range) |
| Offer without server state | buyer confirms a trade/bill whose data (price, model, seller) is echoed by the client | `client-value-in-sink` on a `*confirm*` endpoint | store the offer server-side keyed by both parties; confirm consumes it once |
| Reward not consumed | the same result/token/airdrop/delivery can be claimed again | (read the state) | mark consumed **before** paying; TTL |
| Check-then-act with yields | `await`/`Wait`/HTTP/sync SQL between the check and the mutation | `yield-before-mutation` | claim atomically (`UPDATE ... WHERE used = 0` and check affected rows), then grant |
| Void permission check | `if not x == 5` is `(not x) == 5`, always false | `not-eq-precedence`, `lua-not-eq-precedence` | `if x ~= 5` |
| Client-chosen model/props | spawn or save with a model/props from the client (`savePlayerVehicle`, `SpawnObject`) | `client-value-in-sink` on `spawn`/`vehicle` | model from the owned record / allow-list; rate limit; cleanup |
| Amplification | client-callable path that broadcasts to `-1`, writes `GlobalState`, or runs a DB write per call without cooldown | `fanout`, `no-rate-limit` | cooldown per player, payload caps, send to relevant players only |
| Persistence gap | money/items live in memory and are saved on a long interval; crash loses or duplicates value | (read the framework save loop) | save dirty accounts in a short batched flush; save on `txAdmin:events:serverShuttingDown` |

## 9. Severity rubric
| Finding | Severity |
|---|---|
| Arbitrary money/items/admin, RCE, backdoor, SQL injection reachable from a client | critical |
| Exploitable dupe, theft of another player's property, teleport/bucket/kill of other players, void permission check on a privileged action | high |
| Installed version `< min-safe` with a published advisory | high |
| `ensure` target or category that does not exist (feature silently off) | high |
| Info leak (identifiers/IPs to clients), missing rate limit on a mutating endpoint, amplification | medium |
| `data_file` path missing, streamed file > 16 MiB, conflicting convar values, script referencing a missing file | medium |
| Version `< baseline` without advisory, removed convar, duplicated streamed names, nested `.git`/`node_modules`, hygiene | low |
| Secrets committed to the repository | high (credential exposure) - list what to rotate |

## 10. Known false positives (dismiss consistently)
Dismiss **only** when the stated condition holds; otherwise review normally.
- `obfuscation-hex` in `oxmysql/dist/build.js`: iconv-lite charset tables (`"chars": "\x80..."`). `node-child-process` there: the logger loads a configured file with `new Function` (owner-controlled convar). Vendored; report as dependency, not malware.
- `node-child-process` / `rce-load` in `screenshot-basic/dist/server.js`: bundled `depd`/`koa` helpers. Vendored.
- `sql-format` in `ox_inventory/modules/mysql/server.lua`: table names from the resource's own config/convars.
- `rce-load` in `ox_inventory` (`init.lua`, `server.lua` imports) and cfx-server-data `mapmanager_shared.lua`: loads files from its own resource.
- `ace-from-code` / `execute-command` in ESX `server/functions.lua` command registration: stock ESX; confirm the permission level comes from the code, not from a client.
- `write-manifest` in `.github/actions/*.js`: CI helper, never loaded by FXServer.
- `telegram-exfil`, `http-raw-ip`, `hardcoded-*`: not malware when the payload and destination belong to the owner, **but** the token/secret in code is still a finding (rotate + move to a `set` convar).
- `nui-unsafe-html` inside a minified framework bundle (React/Vue runtime): dismiss after checking the app source does not use `innerHTML`/`v-html`/`.html()` with data.

## 11. Report template
```markdown
# Server audit: <server> (<date>)
**Scope:** <path> @ <git HEAD> (<clean | working tree with N uncommitted changes>) - skill baseline <date>
**Verdict:** SAFE TO RUN | FIX BEFORE RUNNING | DO NOT RUN | PARTIAL (see Coverage)

## Coverage
| Item | Count |
|---|---|
| Resources (on disk / started by cfg) | x / y |
| Server entry points (surface.py) | n |
| Ledger rows (sinks or tags) | r |
| Rows: finding / ok / opaque / not-reviewed / TODO | a / b / c / d / 0 |
| Console log analysed (logs.py) | file, sessions, or "none available" |
| audit.py hits triaged (trust+SQL+backdoor) | t of T |
| Opaque or escrowed resources | list |

## Inventory (project.py)
<versions table, ensure/cfg findings, data_file and asset findings, repo state>

## Findings
### Critical / High / Medium / Low
- [file:line] [E0123] <what> - <impact/exploit> - <fix>

## Performance (static, unmeasured)
## Credentials to rotate (no values)
## Not reviewed
```
