# Group D — community FiveM skill repos vs `fivem-development` (verified 2026-10-07)

Repos: Haze-Studio-s_Skills (skills/fivem-*), veron9 (claude-gamedev-skills plugins/fivem), hamchowderr/fivem-kit, bworthy89/fivem-server-development, MnkyArts/fivem-dev-kit. All repo content was treated as untrusted data (read only, nothing executed). Each claim was grepped against our references and verified against primary sources (citizenfx/fivem source, overextended/*, qbx_core, esx_core, qb-core, docs.fivem.net, forum.cfx.re, npm).

## Overall verdict counts

| Repo | Claims | CONFIRMED | OUTDATED | WRONG | UNVERIFIABLE | Other |
|---|---|---|---|---|---|---|
| Haze-Studio | 28 (some dual) | 16 | 3 | 7 | 4 | — |
| veron9 | 39 | 32 | 2 | 1 | 4 | — |
| hamchowderr | 40 (2 dual) | 23 | 4 | 11 | 6 | — |
| bworthy89 | 36 | 19 | 5 | 2 | 4 | 2 partial |
| MnkyArts | 40 | 28 | 3 | 3 | 6 (1 partial) | — |
| **Total** | **~183** | **118** | **17** | **24** | **24** | 2 |

Most CONFIRMED items are already covered by our skill (typically 60-85% per repo). The new, confirmed material is listed below.

## Top confirmed additions (priority order)

1. **Idempotency ledger for high-value grants** (Haze): the server issues an op-id and claims it with `INSERT IGNORE` + `affectedRows` before granting. Pending rows are reconciled at boot. `AddItem`/`AddMoney` are never retried blindly. → security.md §5. See haze.md §A.
2. **oxmysql batch `MySQL.transaction` commits when a conditional UPDATE matches 0 rows.** It only rolls back when a query throws (`rawTransaction.ts`). Debit/credit transfers need `startTransaction` with an `affectedRows` check. → database-oxmysql.md §7.1. See haze.md §B.
3. **`citizenfx/kvdb-migrator` v1.0.0 (2026-07-21) exists.** It is the official KVP migration tool for Legacy → Enhanced. Our gta5-enhanced.md marks it UNVERIFIED, which is wrong. → gta5-enhanced.md. See veron9.md §A.
4. **Enhanced detection via the `gamename` convar (`gta5enhanced`)** and `games { 'gta5', 'gta5enhanced' }` for shared resources. This replaces our "set your own convar" advice. Enhanced patch-note changes: state bag values capped at 32 KB, client resource-start events now match Legacy, nearby-entity caps 256/256/512 are also the maximums, and clients freeze on `data_file` mounts from server build 157 on (still open on 161). See veron9.md §A/5b.
5. **server.cfg and the console split on any `;` outside double quotes** (citizenfx `Console.cpp`). Add a docs note plus an audit.py rule for unquoted `;` in cfg values (passwords, hostnames). See hamchowderr.md.
6. **Lua msgpack nesting ≥ 16 levels sends the value as `nil` silently** (`lua-cmsgpack` `MP_MAX_NESTING 16`). → events-and-callbacks.md. See bworthy.md.
7. **Client Lua has no `os`/`io` libraries.** Shared files must not call `os.time()`/`os.date()`. `json.encode` serialises vectors as `{x,y,z}` (or as an array with `vectorarray = true`). JS receives Lua vectors as a raw msgpack ext object, which resolves an item our skill marks UNVERIFIED. → runtimes.md. See mnky.md.
8. **A resource cannot change its own ACE** ("Changing ones own access is not permitted"). `ExecuteCommand('set …')` needs `command.set`. The `exports.txAdmin` → `monitor` remap also applies in Lua. → security.md / txadmin.md. See mnky.md.
9. **QBCore cross-resource player methods are pre-bound.** Call `Player.Functions.X(...)` with a dot, never a colon (qb-core `player.lua`). → framework-qbcore.md. See hamchowderr.md.
10. **The server, not the client amount, sets payouts; clamping is not validation.** Use a single-use start/complete record kept on the server and derive the amount from it. Also: the oxmysql driver can't log in with MariaDB `ed25519`, so use a dedicated `mysql_native_password` account. → security.md / database-oxmysql.md. See bworthy.md.

Also worth adding: a natives return a single vector3 note (Haze), an entity-lifecycle checklist for onesync-entities.md (Haze §D), `sv_disconnectOnUnhandledNetEvent` (veron9, correct spelling), and about 10 lint rules for audit.py (MnkyArts: reading `source` after `Wait`, `CreateThread` inside an event handler, etc.).

## Conflicts where the other repo is right / our skill needs a fix

- **KVP migrator**: veron9 is right (see #3). Our UNVERIFIED marker is stale.
- **Enhanced detection**: veron9's built-in `gamename` convar beats our custom-convar advice.
- **"Remove before add" stated as an absolute rule** (hamchowderr): ox_inventory's own shops add the item and then charge. That is safe because nothing yields between the check and the two changes. Reword the rule to "no yield between check and the mutations, plus remove-before-add when an await is involved" in security.md:101 and rp-systems-design.md:57.
- **Internal inconsistency in our skill** (found by bworthy review): `sv_endpointPrivacy` is listed as removed in versions.md / convars-and-commands.md / server-ops.md, but is still recommended in security.md:161, use-vs-avoid.md:185 and performance-server-scaling.md:83. Delete those rows.

## Where the other repos are wrong (our skill already right; do NOT import)
`.await` outside a coroutine "fails silently" (it errors) · `GetPlayerByCitizenId` works offline (online only) · `GetEntityCoords` returns x,y,z (one vector3) · lowercase `ox_inventory:addItem` (`AddItem`) · streaming range ~300 m (424 units) · `lua54 'yes'` mandatory (no-op) · `node_version` default 16 / mono_rt2 "preview" (Node 22 / expired) · "OneSync on by default"/"must enable OneSync" (forced on) · json.encode can't encode vectors · state-bag drop log once per 15 s (source: ~1 s) · ped config flag 35 = "no idle anims" (UseHelmet) · `use_experimental_fxv2_oal` = object attribute loader (wrong) · "Could not find dependency" = load order (resource missing; deps auto-start) · `IsGradeBoss` bug (fixed 2025-09) · `CreateJob` can't persist (`commitToFile`) · screenshot-basic dependency (unmaintained).

## Structural ideas worth copying (consolidated)
- **Source-of-truth order** (Haze): installed resource code > our references > memory. Also FAST/STANDARD/DEEP risk tiers and a mandatory "Audit & Security" footer on delivered code.
- **Evals with baseline vs green scorecards** (bworthy): 5 scenario prompts, scored without the skill and with it. Cheap regression tests for our skill.
- **Hooks** (hamchowderr, MnkyArts): post-edit lint of `.lua` files plus a secrets scanner on writes. **verify-docs** script that checks reference claims against upstream sources. Stack detection script.
- **In-game test harness** (MnkyArts `fxclient`/fivem-devtools): a dev resource with a file queue that runs client snippets and returns logs and screenshots. Note it relies on screenshot-basic, so swap in screencapture.
- **Specialised agents** (hamchowderr, MnkyArts): manifest doctor, native researcher, security auditor, ox migrator, perf auditor, reviewer.
- **Native docs auto-regenerated by a scheduled CI workflow** (Haze natives-skill). Note its source endpoint now returns HTTP 308, so the snapshot is stale (2026-03-24). Our `natives.py update` already covers this.

---
Per-repo detail follows: summary, full findings table and ready-to-paste integration text with source URLs.


---

## Haze-Studio-s_Skills — FiveM analysis (group D, part 1)

### Summary
- **Purpose:** personal skill bundle for the "Antigravity" agent (Portuguese/pt-BR), plus non-FiveM extras. FiveM parts: `fivem-developer` (main skill + 15 references), `fivem-entity-lifecycle`, `fivem-statebags`, `fivem-performance` (+ `scan_hotpaths.py`), `fivem-nui-lation` (a house NUI design system), `fivem-natives-skill` (vendored copy of `heyyczer/fivem-natives-skill`: 45 namespace files generated from the cfxnatives.dev API), and a generic `lua` skill.
- **Not FiveM:** `mcp/rea` is a set of tool schemas for a reverse-engineering MCP server (morluto/rea). `rules/rtk` is about a token-saving CLI proxy. grill-me/grilling/physics-3d-collision are generic. All were ignored.
- **Scope:** Qbox-first (qbx_core + ox_lib + ox_inventory + oxmysql), with short QBCore/ESX pages. It covers security (fail-closed handling, a reusable `Security` module, an `op_id` ledger), DB patterns, NUI and natives. There is nothing on server ops, convars, txAdmin, Enhanced, streaming or licensing.
- **Quality:** medium-low. The doctrine is sound (server authority, remove-before-add, minimal diff). But it has several factual errors: `.await` outside a coroutine is said to "fail silently", `GetPlayerByCitizenId` is said to work offline, the `qbx HasPermission` export is presented as current, and `GetEntityCoords` is said to return x, y, z. It also has buggy examples: a `MySQL.transaction` transfer that commits even when the balance is too low, and an `op_id` keyed on `os.time()`. Several skills are generic stubs (entity-lifecycle, statebags and performance are workflow checklists with no APIs). Much of it is tied to one private server (`Qbox_753251`, `vp_cityworks`).
- **Freshness:** stale. The pinned server context is qbx_core 1.23.0 / ox_lib 3.32.2 / ox_inventory 2.44.8, against our baseline of 1.24 / 3.40 / 2.48 (ox_inventory < 2.47.6 has known dupes). The natives snapshot is from 2026-03-24 (7,358 natives vs our 7,379). The upstream "every 3 days" update job last ran 2026-03-24, and `cfxnatives.dev/api/natives` now answers HTTP 308. The statebags sources were last checked 2026-08-30.

### Findings
Verdicts: CONFIRMED (verified) · OUTDATED · WRONG · UNVERIFIABLE.

| # | Claim | Repo file | Covered in our skill? | Verdict | Source / notes |
|---|---|---|---|---|---|
| 1 | Durable economy operations: write an `op_id` row (PENDING), then grant, then mark COMPLETED/FAILED. A PK on `op_id` blocks replays, and PENDING rows are reconciled at boot. | fivem-developer/references/security/durable-operations-idempotency.md | **No.** We have a per-player lock, `affectedRows == 1` guards and transactions, but no idempotency ledger. | CONFIRMED (concept), but the example is flawed | A unique key rejects a duplicate insert (ER_DUP_ENTRY, https://mariadb.com/kb/en/insert-ignore/). Flaw: `opId = citizenid_action_os.time()` has 1 s granularity. It wrongly rejects two legitimate actions in the same second, and it does not dedupe a replay arriving one second later. The key must come from the business event (heist/job/session id issued by the server). Use `INSERT IGNORE` + `affectedRows`, not `pcall`. |
| 2 | "Blind retry" anti-pattern: never re-grant after a timeout or ambiguous result; reconcile first. | same | Partly. We cover retrying deadlocked DB transactions, which is safe because they roll back. Nothing warns against retrying non-transactional grants (framework `AddMoney`, ox_inventory `AddItem`). | CONFIRMED (logic) | oxmysql rolls back only on SQL error (src/database/rawTransaction.ts). Framework or inventory calls are outside the DB transaction, so a retry can double-grant. |
| 3 | Bank-transfer example: `MySQL.transaction.await` with `UPDATE … SET balance = balance - ? WHERE id = ? AND balance >= ?` gives an "automatic ROLLBACK" if anything fails. | references/database/oxmysql-database-patterns.md §3 | Our §8 uses `startTransaction` + `affectedRows ~= 1`, which is correct, but we have no explicit warning. | **WRONG (repo bug) → gotcha CONFIRMED** | `rawTransaction.ts` runs every query, commits, and rolls back only in `catch`. An UPDATE that matches 0 rows is not an error, so the transfer **commits and credits money that was never debited**. https://github.com/overextended/oxmysql/blob/main/src/database/rawTransaction.ts |
| 4 | `.await` outside `CreateThread`/callbacks "fails silently". | SKILL.md, oxmysql-database-patterns.md, nui-lation | Yes: debugging.md:91, runtimes.md:106. | WRONG | `Citizen.Await` asserts: "Current execution context is not in the scheduler…" (citizenfx/fivem `data/shared/citizen/scripting/lua/scheduler.lua` L85-87). It is a loud error. Our skill is right. |
| 5 | Always declare `lua54 'yes'`. | SKILL.md, scaffolding, audit-and-precheck | Yes: fxmanifest.md:57/94 says it is a deprecated no-op. | OUTDATED | Lua 5.3 was removed 2025-06 (versions.md). The directive is harmless. Our skill is right. |
| 6 | `exports.qbx_core:GetPlayerByCitizenId` works "offline or online". | frameworks/qbox.md §2 | Yes: framework-qbox.md:125/129 (online only; `GetOfflinePlayer`). | WRONG | qbx_core source/docs: online only. Use `GetOfflinePlayer(citizenid)`. Our skill is right. |
| 7 | `exports.qbx_core:HasPermission(source, 'admin')` for admin checks. | frameworks/qbox.md §4 | Yes: framework-qbox.md:186/479 marks it deprecated. | OUTDATED | qbx_core `server/functions.lua` L343-347: `---@deprecated use IsPlayerAceAllowed`. Our skill is right. |
| 8 | qbx_core `GetMoney`/`AddMoney`/`RemoveMoney(source, type, amount, reason)` exports. | frameworks/qbox.md | Yes: framework-qbox.md:150. | CONFIRMED | qbx_core `server/player.lua` L1364/1423/1492. |
| 9 | `GetDistanceBetweenCoords` → `#(a-b)` saves "up to ~0.15 ms per call". | natives/cfx-natives-guide.md §1 | Direction covered (performance.md:99, use-vs-avoid.md:45). | WRONG (magnitude) | No source. A single native call costs microseconds, not 0.15 ms. Keep our wording, which gives no number. |
| 10 | `local x, y, z = GetEntityCoords(entity, true)` ("out params returned as extra values"). | fivem-natives-skill/docs/types-reference.md | Our runtimes.md:54 documents `local x, y, z in coords` / `.x`. | WRONG | `GetEntityCoords` returns one `vector3`. Multiple returns apply only to pointer out-params (e.g. `GetGroundZFor_3dCoord`). The x, y, z assignment gives x = vector, y = z = nil. |
| 11 | `exports.ox_inventory:addItem(source, 'money', amount)` | fivem-natives-skill/docs/best-practices.md | Yes (ox-inventory.md uses `AddItem`). | WRONG | Export names are PascalCase (`AddItem`); `addItem` does not exist on the server. |
| 12 | ox_lib `cache(key, fn, ttl)` memoisation, plus `cache.ped/vehicle/seat/coords/serverId`. | best-practices.md, ox-ecosystem.md | Yes: ox-lib-core.md:46-50. | CONFIRMED | overextended.dev ox_lib cache docs. |
| 13 | `lib.callback.await(name, false, ...)`: on the client the 2nd argument is a delay/throttle (`false` = none); on the server it is the target player. | ox-ecosystem.md, best-practices.md | Yes (ox-lib-core.md). | CONFIRMED | https://overextended.dev/ox_lib/Modules/Callback/Shared |
| 14 | Close NUI with `RegisterKeyMapping('close_x', …, 'keyboard', 'ESCAPE')` as an "emergency close". | references/nui/nui-patterns.md §3 | We recommend page `keydown` plus release on `onResourceStop` (nui.md:110). | CONFIRMED key name; usefulness UNVERIFIABLE | `ESCAPE` is a valid mapper key (fivem-docs `input-mapper-parameter-ids/keyboard.md`). While NUI has keyboard focus the game does not get input, so the mapping is unlikely to fire. Also ESC opens the pause menu. Keep our approach. |
| 15 | "CEF blocks external CDNs in several builds; everything must be local." The Lation template then `@import`s Google Fonts. | nui-patterns.md, nui-lation/lation-design-system.md | Yes: nui.md:120 (bundle locally; CDNs slow / may fail offline). | UNVERIFIABLE (overstated) and self-contradictory | No Cfx source says CDNs are blocked. Bundling locally is correct for latency and offline use. |
| 16 | Release NUI focus in `onResourceStop`. | nui-lation/SKILL.md | Yes: nui.md:110. | CONFIRMED | docs.fivem.net NUI docs; covered. |
| 17 | OneSync streaming bubble "~300 m". | client-server/statebags-and-onesync.md §4 | Yes: onesync-entities.md:25/39 gives 424 units. | WRONG | The focus zone is 424 units (our source-verified value). |
| 18 | State bag hygiene: small values, flat/namespaced keys, bounded write frequency, no secrets, server-only writes for gameplay-critical keys. | fivem-statebags/SKILL.md | Yes: onesync-entities.md §9 (shallow semantics, strict mode, rate limiters, size). | CONFIRMED | https://docs.fivem.net/docs/scripting-manual/networking/state-bags/ ; ours is more detailed. |
| 19 | Client handler: `GetPlayerFromStateBagName(bag)` → `GetPlayerPed(player)`; `== 0` means not found. | statebags-and-onesync.md §3 | Helper listed (onesync-entities.md:215). | CONFIRMED native (returns source on server, player handle on client); invalid-value check UNVERIFIABLE | Native 0xA56135E0. Player handle 0 can be a valid local index, so check `GetPlayerPed(p) ~= 0` / `DoesEntityExist`. |
| 20 | `Security.IsValidSource`: `GetPlayerPing(src) > 0`. | security/hardening-and-anticheat.md | We use `source` checks and framework player lookup. `DoesPlayerExist`/`GetPlayerPing` are listed in natives-essentials.md:778/787. | UNVERIFIABLE | Ping can plausibly be 0 for a freshly connected client. Prefer `DoesPlayerExist(src)` or a framework player object. |
| 21 | Repeated `AddEventHandler` (e.g. inside a loop or an event) leaks memory. | examples/audit-and-precheck.md | Yes: performance.md:146. | CONFIRMED | Covered. |
| 22 | Resmon targets: idle < 0.05 ms, active < 0.10 ms. | SKILL.md, audit-and-precheck.md | Ours is stricter: 0.00–0.02 ms idle. | UNVERIFIABLE (house rule) | No official threshold. Keep ours. |
| 23 | Rate limits "≥ 2 s on money/item actions, ≥ 30 s on crimes". | nui-lation/references/qbox-server-context.md | We have a token bucket (security.md §10). | UNVERIFIABLE (house rule) | Server-specific policy. |
| 24 | `CreateVehicleServerSetter(hash, 'automobile', x, y, z, heading)` then wait for `DoesEntityExist`. | natives/cfx-natives-guide.md §3 | Yes (gameplay-patterns.md, onesync-entities.md). | CONFIRMED signature (our `natives.py show`); the example lacks a timeout | Our pattern already uses a timeout. |
| 25 | `RegisterStash(id, label, slots, maxWeight, owner)` | examples/inventory-integration.md | Yes: ox-inventory.md:218 (fuller signature). | CONFIRMED | overextended.dev ox_inventory server docs. |
| 26 | Crafting: check counts, remove each input, give back on failure, then `AddItem` the product and refund everything if it fails. | examples/inventory-integration.md | Yes: security.md §5 (remove-first, CanCarry, give back). | CONFIRMED (pattern), but weak | Better: `CanCarryItem` before removing, and wrap in the per-player lock (our pattern). |
| 27 | Natives reference via the cfxnatives.dev API with ETag + SHA-256 change detection and scheduled CI regeneration. | fivem-natives-skill/src/*.ts, workflow | We have `natives.py update` / `build_natives_catalog.py --refresh` (official DB). | CONFIRMED that it existed; now OUTDATED | Last update 2026-03-24; the API URL returns 308. Our official-source tool is better. |
| 28 | Cache player coords outside per-entity loops; yield every N iterations in long loops; `SetModelAsNoLongerNeeded` after spawning. | fivem-natives-skill/docs/best-practices.md | Yes (performance.md, gameplay-patterns.md:68/93). | CONFIRMED | Covered. |

**Verdict counts (28 items):** CONFIRMED 16 (incl. #1–3 as new or gotcha items, #14/#19/#24/#26 partially), WRONG 7 (#3 repo example, #4, #6, #9, #10, #11, #17), OUTDATED 3 (#5, #7, #27), UNVERIFIABLE 4 (#15, #20, #22, #23). The total is above 28 because #14, #19 and #27 carry two verdicts.

### Recommended integrations

#### A. `references/security.md` → §5 "Economy and duplication", append after the per-player lock block
```markdown
- **Idempotency ledger for high-value grants** (heist payouts, job/mission rewards, vehicle purchases, cross-resource transfers). The server issues the operation id when the activity starts (e.g. `heist:<netId>:<startTime>`, or a random token stored server-side). Never derive it from `os.time()` at payout time, and never accept one from the client. Claim it atomically before granting:
  ```lua
  -- server; table: CREATE TABLE IF NOT EXISTS op_ledger (op_id VARCHAR(64) PRIMARY KEY, charid VARCHAR(64) NOT NULL,
  --   action VARCHAR(32) NOT NULL, status ENUM('PENDING','DONE','FAILED') NOT NULL DEFAULT 'PENDING',
  --   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, KEY (status))
  local claimed = MySQL.update.await('INSERT IGNORE INTO op_ledger (op_id, charid, action) VALUES (?, ?, ?)', { opId, charid, action })
  if claimed ~= 1 then return false end                 -- replay or duplicate: already processed
  local ok = exports.ox_inventory:AddItem(src, item, count)
  MySQL.update.await('UPDATE op_ledger SET status = ? WHERE op_id = ?', { ok and 'DONE' or 'FAILED', opId })
  ```
  On boot, list rows still `PENDING` and **reconcile** them: check the inventory or account and finish or void each one by hand or by script. Do not re-grant blindly.
- **No blind retries of grants.** Retrying a whole DB transaction after a deadlock is safe, because oxmysql rolled it back. Retrying `AddMoney`/`AddItem` after a timeout or an ambiguous result can double-grant. Check the ledger or inventory state first.
  (Unique-key semantics: https://mariadb.com/kb/en/insert-ignore/ · oxmysql rollback only on SQL error: https://github.com/overextended/oxmysql/blob/main/src/database/rawTransaction.ts)
```

#### B. `references/database-oxmysql.md` → §7.1 `MySQL.transaction`, add a bullet after "Returns `false` on any failure…"
```markdown
- **A conditional statement that matches 0 rows is not a failure.** `UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?` with too little balance updates 0 rows, and the batch still **commits** the remaining statements (e.g. the credit). oxmysql rolls back only when a query throws (`src/database/rawTransaction.ts`). For "check then debit/credit" logic use `MySQL.startTransaction` and `return false` when `affectedRows ~= 1` (§7.2, database-optimization.md §8).
```

#### C. `references/runtimes.md` (vectors section, near line 54), one line
```markdown
- `GetEntityCoords` and other `Vector3`-returning natives return **one** `vector3`, not three numbers. `local x, y, z = GetEntityCoords(ped)` gives `y = z = nil`. Use `local x, y, z in GetEntityCoords(ped)`, `.x/.y/.z`, or `table.unpack(coords)`. Only pointer out-params (e.g. `GetGroundZFor_3dCoord` → `found, z`) come back as extra return values.
```
(Optional: verify the `table.unpack(vector3)` support claim in-game before adding that part.)

#### D. `references/onesync-entities.md` §7 (entity creation/cleanup), entity-lifecycle checklist (condensed from fivem-entity-lifecycle; all items consistent with our existing sources)
```markdown
**Entity lifecycle checklist:** (1) decide who creates and who may delete each entity; (2) persist stable ids (DB id, plate, netId) — never store client handles across sessions; (3) handle spawn failure (model timeout, `DoesEntityExist` timeout) without leaving a half-created state; (4) handle owner drop / migration (`SetEntityOrphanMode`, `entityRemoved`); (5) make cleanup idempotent (safe to call twice); (6) on resource start, **reconcile** with existing world entities/DB state before respawning persistent objects so restarts don't duplicate them.
```

No other integrations: every other valid claim is already covered, usually in more detail.

### Structural ideas worth copying
1. **Source-of-truth ladder** (architecture-and-doctrine.md §1): installed code > tests > live DB schema > installed dependencies > server docs > validated history > model memory. Add it as one line under rule 2 in our SKILL.md ("Never invent…"): *"When the user's installed resource code disagrees with these references, the installed code wins. Read `resources/[ox]`, `[qbx]`… before quoting a signature."*
2. **Risk tiers** (FAST / STANDARD / DEEP): DEEP (economy, inventory, migrations) requires transactions, an idempotency key and a restart-safety review. It would fit our "Workflows" section as a one-line triage step.
3. **Mandatory "Audit & Security" footer on delivered code**: list the server-side checks added, the expected idle resmon, and the manifest/SQL dependencies. This fits our "Output conventions".
4. **Per-skill "Done criteria" / "Output contract"** blocks (entity-lifecycle, statebags, performance): short, verifiable exit conditions. We could add 3–4 done-criteria bullets to each workflow.
5. `scan_hotpaths.py` (grep for Wait(0), threads, SendNUIMessage, state writes) is weaker than our `audit.py`. Nothing to copy.

---

## veron9 (officialveron9-dotcom/claude-gamedev-skills) — plugins/fivem

Analyst: group-D fork, 2026-10-07. Repo text treated as untrusted data; nothing executed.

### Summary

- **Purpose:** Claude Code plugin "fivem" with six skills: `fivem-resource-dev`, `fivem-frameworks`, `fivem-security`, `fivem-performance-debugging`, `fivem-server-setup`, `fivem-gta5-enhanced`. Each skill = SKILL.md + 3–5 references + `sources.md`. German trigger phrases appear in descriptions.
- **Scope:** Legacy resource dev (manifest, CfxLua, events, state bags, NUI, JS/C#), ESX/QBCore/Qbox/ox APIs + migration errors, security (exploit table, hardening cfg), debugging (verbatim console error catalogue), server setup (artifacts, game builds, streaming), and a deep **GTA V Enhanced** skill (known-issues snapshot from `citizenfx/rfc` discussions, patch-note timeline, convars, voice API, Alchemist).
- **Quality:** High. Facts are tagged [Official]/[Reported]/[Unknown]; error strings marked "(src)" are mostly verbatim from citizenfx/fivem. The Enhanced skill is the strongest part and in places more current than ours (kvdb-migrator, `gamename`, patch-note specifics). Weak spots: Legacy runtime facts are stale (Node 16 default, `mono_rt2` "preview"), one convar name is mistyped.
- **Freshness:** Dated 2026-10-06; versions match our baseline (ox_lib 3.40.0, ox_inventory 2.48.0, qbx_core 1.24.0, ESX 1.15.2, Recommended 35245). Its newest artifact tag (36897) is older than ours (37150).
- **Overlap with our skill:** ~85 % of its content is already in our references, often in more depth. Our gta5-enhanced.md, convars-and-commands.md, debugging.md, framework-* and security.md already cover most claims. Its added value is the Enhanced patch-note detail and a handful of verbatim errors and framework source gotchas.

### Findings

Verdicts: **C** = CONFIRMED, **O** = OUTDATED, **W** = WRONG, **U** = UNVERIFIABLE.

| # | Claim | Repo file | In our skill? | Verdict | Source / notes |
|---|---|---|---|---|---|
| 1 | KVP DB migration tool `citizenfx/kvdb-migrator` exists (Bun/TS; input is the Legacy `db/<sv_kvsName>` folder) | gta5-enhanced/legacy-vs-enhanced.md, server-setup.md | **Conflict**: ours says "migration script announced; UNVERIFIED availability" | C | https://github.com/citizenfx/kvdb-migrator (created 2026-07-17, release v1.0.0 on 2026-07-21). **Theirs is right.** |
| 2 | Server-side edition detection: `GetConvar('gamename','gta5')` is `gta5enhanced` (or `gta5_enhanced`) on Cfx Server; client: `IsGameEnhancedVersion()`, guarded with `type(...) == 'function'` | gta5-enhanced SKILL.md | **Conflict**: our gta5-enhanced.md §10 says to set your own convar; convars-and-commands.md lists `gamename` values only `gta5`, `rdr3` | C (secondary) | esx_lib source: https://github.com/esx-framework/esx_core/blob/main/%5Bcore%5D/esx_lib/imports/isEnhanced/shared.lua. Not in the Cfx docs. **Theirs is better.** |
| 3 | `games { 'gta5', 'gta5enhanced' }` is used by Cfx's own map resources (cross-edition manifest) | gta5-enhanced | No | C | https://github.com/citizenfx/cfx-server-data/commit/e265cb251c88260533c847d4a1a2838c7d828a66 ("feat: add gta5enhanced to fivem maps", 2026-07-20). Not documented on docs.fivem.net. `game 'gta5'`-only resources (spawnmanager, mapmanager) still ship in the Enhanced recipe. |
| 4 | Enhanced player IDs are reused, but staff say only "up to 4k"; the 08-31 patch made reuse "less likely" | legacy-vs-enhanced.md, known-issues.md | Partly: ours says "reused as soon as freed" | C | https://github.com/citizenfx/rfc/discussions/136 (wolfram-cfx: "We will only reuse them up to 4k"; a b139 report still shows quick reuse) · https://github.com/citizenfx/rfc/discussions/474 |
| 5 | Enhanced 08-31: client start events now match Legacy. `onClientResourceStart` fires for every resource; `onResourceStarting`/`onResourceStart` fire only on restart | gta5-enhanced | No (Enhanced-specific) | C | https://github.com/citizenfx/rfc/discussions/474 |
| 6 | Threads created while a resource loads get their first tick after `onClientResourceStart` (Enhanced 09-24, "matching the server and Legacy") | legacy-vs-enhanced.md | No | C | https://github.com/citizenfx/rfc/discussions/545 |
| 7 | Enhanced state bags: max 32 KB per value (was 256 KB), key ≤ 1024 chars, warnings above 256-char keys / 1 KB values | gta5-enhanced | No | C | https://github.com/citizenfx/rfc/discussions/564 (2026-09-30) |
| 8 | Convar `sv_disconnectOnUnhandledUnhandledNetEvent` ("spelled that way in the notes") | legacy-vs-enhanced.md | No | **W** | The patch notes spell it `sv_disconnectOnUnhandledNetEvent` (off by default; disconnects clients sending reliable net events with no handler). https://github.com/citizenfx/rfc/discussions/530 |
| 9 | Enhanced adds the `netGameEvent` / `netGameEventFlood` rate limiters (`rateLimiter_<name>_rate/_burst`) | legacy-vs-enhanced.md | Partly (onesync-entities.md mentions netGameEvent) | C | https://github.com/citizenfx/rfc/discussions/564 |
| 10 | `onesync_maxNearbyVehicles/Peds/Objects/Players/Other`, defaults ~256 vehicles / 256 peds / 512 objects | legacy-vs-enhanced.md | No | C (+ extra) | https://github.com/citizenfx/rfc/discussions/360. Extra fact the repo misses: the defaults are also the **maximums**, so higher values are rejected with "Value out of range", and staff say this is intentional: https://github.com/citizenfx/rfc/discussions/368 |
| 11 | `onesync_multithreadedPacketProcessing` (default true; `set ... false` disables parallel sync processing) | legacy-vs-enhanced.md | No | C | https://github.com/citizenfx/rfc/discussions/564 |
| 12 | `sv_entityLockdown no_dummy` is accepted on Enhanced again (also via `SetRoutingBucketEntityLockdownMode`) | legacy-vs-enhanced.md | Ours documents `no_dummy` as Legacy-only | C | https://github.com/citizenfx/rfc/discussions/474 |
| 13 | `NetworkGetEntityOwner` returns `-1` for server-owned entities (Enhanced fix); `sv_protectServerEntities` is a no-op on Enhanced | known-issues.md | Yes (onesync-entities.md, gta5-enhanced.md) | C | https://github.com/citizenfx/rfc/discussions/287. Already covered. |
| 14 | Open Enhanced bugs: data_file mounts freeze clients on b157 (#567; workaround b156; **still reproduces on b161**), custom peds invisible (#543), `increase_pool_size` ineffective for `CWeaponComponentInfo` (#524), `SetNuiFocusKeepInput` broken (#555), loading screen gets only `loadProgress` (#427), C# server crash when cancelling HTTP (#572) | known-issues.md | No | C (open as of 2026-10-07) | https://github.com/citizenfx/rfc/discussions/567 · /543 · /524 · /555 · /427 · /572 |
| 15 | C# on Enhanced: `sv_devMode 1` + `sv_enableCoreclrSandboxing 0` partly disables the sandbox (dev only); whitelisted NuGet packages include MS.Extensions.Logging.Abstractions, DependencyInjection, EntityFrameworkCore, Npgsql; Legacy `CitizenFX.Core` NuGets load; new module has StateBag API, `API.EveryTick`, `[OnTick]`, ColShape API | legacy-vs-enhanced.md | No (ours only says ".NET 10") | C | https://github.com/citizenfx/rfc/discussions/439 |
| 16 | Gen9 asset pitfalls: max **128 materials/geometries** per drawable (more crashes the client); `script_rt_*` textures must be `D3DFMT_A8R8G8B8` or the game crashes with `ERR_GFX_STATE`; CodeWalker `G9_Flags` = 2490920 | assets-and-streaming.md | No | C (secondary) | https://github.com/Sollumz/wiki/blob/main/tutorials/asset-conversion-for-gtav-enhanced.md |
| 17 | Official txAdmin recipe `default-fivem-enhanced` ships only mapmanager, spawnmanager, basic-gamemode and two maps. The cfg has no `sv_enforceGameBuild`, onesync, chat, hardcap or sessionmanager | server-setup.md | Partly (ours names the recipe) | C | https://github.com/citizenfx/txAdmin-recipes/tree/main/default-fivem-enhanced |
| 18 | Enhanced has built-in **colshape** natives (polygon/square/sphere); Legacy needs PolyZone/ox_lib zones | legacy-vs-enhanced.md | No | C | https://docs.fivem.net/docs/scripting-manual/migrating-from-other-platforms/ (source `content/docs/scripting-manual/migrating-from-other-platforms/_index.md` §Colshape system) |
| 19 | Enhanced server native `SetPlayerName` (usable in `playerConnecting` and later) + events `onPlayerNameChanged`, `onPedDeath`, `onPedHealthChanged` (attacker + weapon) | legacy-vs-enhanced.md | No | C | https://github.com/citizenfx/rfc/discussions/404 (Hotfix 9) |
| 20 | Enhanced client needs **WebView2** (since Hotfix 6, a missing WebView2 shows an error instead of a black screen) | legacy-vs-enhanced.md | No | C | https://github.com/citizenfx/rfc/discussions/312 |
| 21 | Enhanced CEF is Chromium 140 | legacy-vs-enhanced.md | Ours: "version not published" | U | Community claim only; no Cfx source. Keep ours. |
| 22 | Enhanced client logs in `%AppData%\FiveM for GTAV Enhanced\logs` | gta5-enhanced | No | U | Not in the rfc README or bug template. |
| 23 | `stream_enhanced/` replaces `stream/` (also for wildcard matches); `stream/` alone is deprecated on Enhanced | assets-and-streaming.md | Yes | C | https://github.com/citizenfx/rfc/discussions/530 · /545. Already covered. |
| 24 | Enhanced pools auto-extend (StaticBounds, MapTypesStore, MapDataStore, TxdStore, InteriorProxy, FragmentStore, DrawableStore, MaxExtraVehicleModelInfos; dwdStore sized from streamed `.ydd`) | assets-and-streaming.md | No | C | https://github.com/citizenfx/rfc/discussions/474 · /530 |
| 25 | Enhanced script event rate limit relaxed to ~75 events/s by default (callbacks timing out on join) | known-issues.md (implicit) | No | C | https://github.com/citizenfx/rfc/discussions/545 |
| 26 | Patches with protocol changes (08-31, 09-22, 09-30) need a cfx-server update, or clients get handshake/connection errors | gta5-enhanced, server-setup.md | No | C | https://github.com/citizenfx/rfc/discussions/474 · /530 · /564 |
| 27 | Server JS runs Node 16 by default; `node_version '22'` opts in | resource-dev SKILL.md, runtimes-js-csharp.md, artifacts-gamebuilds.md | **Conflict** | **O** | Ours (versions.md, runtimes.md): Node 16 removed 2026-02, all server JS on Node 22, `node_version` ignored. **Ours is right.** |
| 28 | `mono_rt2` is "a preview" | runtimes-js-csharp.md | **Conflict** | **O** | Ours: `mono_rt2` expired 2026-06-30 (versions.md). **Ours is right.** |
| 29 | Community list of broken artifacts `jgscripts/fivem-artifacts-db` (e.g. 35186–35214 Lua `io.readdir` errors, 31689 server `GetVehiclePedIsIn` returns 0, 28626 packet loss, 14583–14716 `onEntityBucketChange` crash) | server-setup/artifacts-gamebuilds.md | No (ours only mentions onEntityBucketChange) | C | https://github.com/jgscripts/fivem-artifacts-db/blob/main/db.json (pushed 2026-10-04) |
| 30 | `Warning: sending large event <name> (<N> bytes). ... Consider using latent events instead.` | common-errors.md | No | C (+ detail) | citizenfx/fivem `code/components/citizen-server-impl/src/ServerResources.cpp` (`TriggerClientEvent`). Printed for server→client payloads ≥ 1,000,000 bytes, at most once per 5 s. |
| 31 | `Setting values on Entity is not supported at this time.` (writing `Entity(x).foo = v` instead of `.state`) | common-errors.md | No | C | citizenfx/fivem `data/shared/citizen/scripting/lua/scheduler.lua` (line ~866) |
| 32 | `cannot set values on exports` / `cannot set values on an export resource` | common-errors.md | No | C | same scheduler.lua (lines ~723/729); also v8 `main.js` |
| 33 | `Couldn't find resource category <[name]>.` | common-errors.md | No | C | `ServerResources.cpp` (line ~667) |
| 34 | `Server specified an invalid game build enforcement (N).` (client) and `Reliable server command overflow.` (drop reason) | common-errors.md | No | C | `code/components/net/src/NetLibrary.cpp`; `code/components/citizen-server-impl/src/packethandlers/ServerCommandPacketHandler.cpp` |
| 35 | `Failed to verify protected resource` (escrow `.fxap` damaged), `Invalid client configuration`, `Connection to CNL timed out.` | common-errors.md | Partly (ours has "You lack the required entitlement") | U | Not found in public citizenfx/fivem source (the escrow/auth code is closed). Plausible; widely reported on the forum. |
| 36 | QBCore: two concurrent `QBCore.Functions.TriggerCallback` calls with the same name on one client overwrite each other (pending promise stored by name) | qbcore-qbox.md | No | C | https://github.com/qbcore-fivem/qb-core/blob/main/client/functions.lua (`QBCore.ServerCallbacks[name] = { ... promise = promise.new() }`) |
| 37 | Qbox `HasGroup` / `HasPrimaryGroup` / `GetGroups` index `QBX.Players[source].PlayerData` **without a nil check**, so they throw for a source that is not loaded | qbcore-qbox.md | No | C | https://github.com/Qbox-project/qbx_core/blob/main/server/functions.lua (lines ~506–527) |
| 38 | ESX switches to ox mode when the `ox_inventory` folder exists, even if it is not started | esx.md, migration-errors.md | Partly (ours: "auto `ox` when ox_inventory is present") | C | `es_extended/shared/config/main.lua` line ~116: `if GetResourceState("ox_inventory") ~= "missing" then Config.CustomInventory = "ox"` |
| 39 | (Side note, from rfc #136 comment) Enhanced bundles "txAdmin v9.0.0-beta" | — | Ours: txAdmin 8.1.1 embedded | U | No v9 release on github.com/citizenfx/txAdmin (latest v8.1.1). A user's comment only. Worth re-checking. |

**Counts:** CONFIRMED 32 (2 already fully covered: #13, #23) · OUTDATED 2 · WRONG 1 · UNVERIFIABLE 4 · total 39.

### Recommended integrations (ready to paste)

#### A. `references/gta5-enhanced.md`

**A1 — replace the KVP row in §4** (`| KVP | ... migration script announced; **UNVERIFIED** availability) |`) with:
```
| KVP | `sv_kvsName` DB | files **must be migrated** with the official tool https://github.com/citizenfx/kvdb-migrator (v1.0.0, 2026-07-21; input = Legacy `db/<sv_kvsName>` folder). Since 2026-08-31 KVP DBs are no longer keyed by server URL (survive IP/proxy changes). |
```
And in §11 step 6 replace "migrate with the Cfx-provided script (when published)" with "migrate with `citizenfx/kvdb-migrator`".

**A2 — replace the server-side block in §10:**
````
```lua
-- server side: Cfx Server reports gamename = 'gta5enhanced' (esx_lib also accepts 'gta5_enhanced')
local isEnhanced = ({ gta5enhanced = true, gta5_enhanced = true })[GetConvar('gamename', 'gta5')] == true
-- client side (guard for old Legacy builds that lack the native):
-- local isEnhanced = type(IsGameEnhancedVersion) == 'function' and IsGameEnhancedVersion()
```
Source: esx_lib `imports/isEnhanced/shared.lua` (https://github.com/esx-framework/esx_core/blob/main/%5Bcore%5D/esx_lib/imports/isEnhanced/shared.lua). The `gamename` value is not documented by Cfx — verify on your build.
````
Also add under §10 rules:
```
- Manifest for dual-edition resources: `games { 'gta5', 'gta5enhanced' }` (used by Cfx's own map resources, cfx-server-data commit e265cb2, 2026-07-20; not on docs.fivem.net). `game 'gta5'`-only resources still load on Enhanced (the official Enhanced recipe ships spawnmanager/mapmanager).
```

**A3 — §4 table, player-ID row:** change "**reused** as soon as freed" to:
```
**reused** after disconnect; staff: "we will only reuse them up to 4k" (https://github.com/citizenfx/rfc/discussions/136); 08-31 patch made reuse less likely. Never key data by server id.
```

**A4 — new subsection "Early-access behaviour changes (patch notes)"** after §5:
```
### 5b. Early-access behaviour changes (patch notes, citizenfx/rfc)
- Protocol bumps (2026-08-31, 09-22, 09-30): an outdated cfx-server gives clients handshake/connection errors → update cfx-server first when "nobody can connect" after a Cfx patch.
- Client start events (08-31, #474): match Legacy — `onClientResourceStart` fires for every resource; `onResourceStarting`/`onResourceStart` fire only on restart. Threads created during load get their first tick after `onClientResourceStart` (09-24, #545).
- State bags (09-30, #564): max **32 KB per value** (was 256 KB), keys ≤ 1024 chars; warnings above 256-char keys or 1 KB values.
- `sv_disconnectOnUnhandledNetEvent` (09-22, #530, default off): disconnects clients that send a reliable net event with no handler.
- Rate limiters: new `netGameEvent` / `netGameEventFlood` (09-30); script event limit relaxed to ~75/s (09-24). Tune with `rateLimiter_<name>_rate|_burst`.
- `onesync_maxNearbyVehicles|Peds|Objects|Players|Other` (08-04, #360): priority streaming caps ≈ 256 / 256 / 512 objects. The defaults are also the maximums ("Value out of range"; intentional per staff, #368).
- `onesync_multithreadedPacketProcessing` (default true, 09-30): parallel sync; `set onesync_multithreadedPacketProcessing false` to disable.
- `sv_entityLockdown no_dummy` accepted again (08-31), also for routing buckets.
- Pools auto-extend (08-31/09-22): StaticBounds, MapTypesStore, MapDataStore, TxdStore, InteriorProxy, FragmentStore, DrawableStore, MaxExtraVehicleModelInfos, dwdStore. `increase_pool_size` is still ineffective for `CWeaponComponentInfo` (#524).
- New server native `SetPlayerName` (usable from `playerConnecting`) + events `onPlayerNameChanged`, `onPedDeath`, `onPedHealthChanged` (Hotfix 9, #404). Built-in colshape natives exist on Enhanced only (search "Colshape" in the native reference).
- Client needs Microsoft **WebView2** (Hotfix 6, #312).
Patch notes: https://github.com/citizenfx/rfc/discussions/categories/patch-notes
```

**A5 — §9 C# bullet, append:**
```
Sandbox: dev-only escape `sv_devMode 1` + `sv_enableCoreclrSandboxing 0`; whitelisted NuGets include Microsoft.Extensions.Logging.Abstractions, Microsoft.Extensions.DependencyInjection, Microsoft.EntityFrameworkCore, Npgsql; Legacy `CitizenFX.Core.*` NuGets load; the new module adds a StateBag API, `API.EveryTick`, `[OnTick]`, ColShape API (C# patch 2026-08-20, https://github.com/citizenfx/rfc/discussions/439). Open bug: cancelling a pending HTTP/WebSocket op crashes the server (`CancelIoEx` not implemented, #572). Avoid cancellation tokens on HTTP calls for now.
```

**A6 — §8 Assets, append:**
```
- Gen9 limits (Sollumz wiki, community-verified): max **128 materials/geometries** per drawable (more → client crash on approach); `script_rt_*` textures must be uncompressed `D3DFMT_A8R8G8B8` (DXT5/BC3 → `ERR_GFX_STATE` crash when entering the vehicle; CodeWalker `G9_Flags` 2490920). https://github.com/Sollumz/wiki/blob/main/tutorials/asset-conversion-for-gtav-enhanced.md
```

**A7 — new "Known open issues (2026-10-07)" box (re-check before quoting):**
```
| Issue | Workaround | Thread |
|---|---|---|
| Client freezes at 100 % loading when the server mounts `data_file`s (regression b157, still on b161) | run server b156 | https://github.com/citizenfx/rfc/discussions/567 |
| Custom ped models invisible | none | /543 |
| `SetNuiFocusKeepInput` has no effect | none | /555 |
| Loading screen only gets `loadProgress` (no Legacy granular events/`onLogLine`) | plain 0–100 % bar | /427 |
| `increase_pool_size` ignored for `CWeaponComponentInfo` | keep custom weapon components within free slots | /524 |
```

**A8 — §3 Installing: add** "The official `default-fivem-enhanced` recipe ships only mapmanager, spawnmanager, basic-gamemode and two maps. Its cfg has no `sv_enforceGameBuild`, onesync, chat, hardcap or sessionmanager (https://github.com/citizenfx/txAdmin-recipes/tree/main/default-fivem-enhanced)."

#### B. `references/convars-and-commands.md`
- `gamename` row: change accepted values to "`gta5`, `rdr3`; Cfx Server (Enhanced) reports `gta5enhanced` (per esx_lib)".
- Add Enhanced rows: `sv_disconnectOnUnhandledNetEvent` (false; Enh) · `onesync_maxNearbyVehicles/Peds/Objects/Players/Other` (≈256/256/512 = max; Enh) · `onesync_multithreadedPacketProcessing` (true; Enh) · `sv_enableCoreclrSandboxing` (dev mode only; Enh). Sources as in A4/A5.

#### C. `references/debugging.md` — add rows to the error table
```
| `Warning: sending large event <name> (<N> bytes). This may cause performance issues. Consider using latent events instead.` | server | a server→client event ≥ 1,000,000 bytes (printed at most every 5 s) → `TriggerLatentClientEvent`, paginate, send ids (citizenfx/fivem `ServerResources.cpp`) |
| `Setting values on Entity is not supported at this time.` | both | `Entity(ent).foo = v` → use `Entity(ent).state.foo = v` / `:set()` (scheduler.lua) |
| `cannot set values on exports` / `cannot set values on an export resource` | both | assigning to `exports.x` → define with `exports('name', fn)` (scheduler.lua) |
| `Couldn't find resource category <[name]>.` | server | `ensure [cat]` with no such bracket folder (ServerResources.cpp) |
| `Server specified an invalid game build enforcement (N).` | client | unsupported `sv_enforceGameBuild` value (NetLibrary.cpp) |
| `Reliable server command overflow.` (drop) | server | client spamming commands (keybind loop) (ServerCommandPacketHandler.cpp) |
```

#### D. `references/server-ops.md` (artifact update section)
```
Before updating artifacts, check the community list of known-broken builds: https://github.com/jgscripts/fivem-artifacts-db (`db.json`; e.g. 35186–35214 Lua `io.readdir` errors that break ox_lib `getFilesInDirectory`/locales, 31689 server `GetVehiclePedIsIn` returns 0, 28626 packet loss, 27783–27938 SIGSEGV). Keep the previous artifact folder for rollback.
```

#### E. `references/framework-qbcore.md` (callbacks)
```
- Gotcha: `QBCore.Functions.TriggerCallback` stores the pending promise by callback **name** (`QBCore.ServerCallbacks[name]`). Two concurrent calls with the same name on one client overwrite each other, so one never resolves correctly. Serialize them, or use `lib.callback` (https://github.com/qbcore-fivem/qb-core/blob/main/client/functions.lua).
```

#### F. `references/framework-qbox.md` (near the HasGroup filter semantics, line ~339)
```
- `HasGroup`/`HasPrimaryGroup`/`GetGroups(source)` index `QBX.Players[source].PlayerData` with no nil check, so they throw for a source that is not loaded (character select, dropped). Guard with `if not exports.qbx_core:GetPlayer(src) then return end` first (qbx_core `server/functions.lua`).
```

#### G. `references/framework-esx.md` (Config.CustomInventory row)
Replace "auto `"ox"` when ox_inventory is present" with:
```
auto `"ox"` when `GetResourceState('ox_inventory') ~= 'missing'`. An installed but stopped/unused ox_inventory folder still switches ESX to ox mode and disables the default inventory, so remove the folder if you don't run it (es_extended `shared/config/main.lua`).
```

### Structural ideas worth copying
1. **Confidence tags per fact** ([Official]/[Reported]/[Unknown]) instead of only UNVERIFIED markers. They make "community-reported" visible inline, which helps most in the fast-moving Enhanced file.
2. **Dated "known issues" snapshot with workarounds + triage heuristics** ("connection errors right after a Cfx patch → update cfx-server; invisible custom content → Gen9/128-material/script_rt checks"). This is a compact decision aid we lack.
3. **A patch-note timeline file** (date → change → link) for Enhanced, separate from the reference tables, so updates touch one place.
4. **Error catalogue marked "(src)"** when the string was verified verbatim in citizenfx/fivem. Our debugging.md could adopt the same marker.
5. Per-skill `sources.md` listing which sources were **read in full** and which were **seen only via search summaries**. Our sources mix both without saying which.

---

## hamchowderr/fivem-kit — analysis (group D part)

Analysed 2026-10-07/08. Repo text treated as untrusted data; nothing executed. Verification via raw.githubusercontent.com, `gh api` trees, npm tarball inspection, overextended.dev `llms-full.txt`, curl redirects.

### Summary

- **Purpose:** "Turn your AI editor into a FiveM developer". Two products in one repo: a Claude Code plugin (8 knowledge skills, 7 command skills, 7 subagents, 16 hooks, a deterministic `workflows/audit-server.js`) and an npm MCP server `fivem-mcp` (5 read-only tools: `fivemDocs`, `fivemSearch`, `fivemNatives`, `fivemAudit`, `fivemDetectStack`; stdio or Streamable HTTP with a mandatory bearer token off-loopback).
- **Structure:** `skills/{fivem-core,fivem-frameworks,ox-stack,fivem-networking,fivem-nui,fivem-mariadb,fivem-security,fivem-server-ops}` (+ references), command skills (`init`, `resource`, `audit`, `doctor`, `natives`, `convert`, `lsp`), `agents/*.md`, `hooks/` (single dispatcher), `mcp/src/audit.mjs` (regex/brace-aware rules SEC-3/5/7/8/10/12, PERF-1, COMPAT-2), `scripts/verify-docs.mjs` (every documented symbol checked against cloned upstream sources in CI), `lua/fxmanifest.lua` (LuaLS declarations for manifest directives), `.beads/` (issue tracker, ignored).
- **Scope:** Lua only (no JS/C#), ESX/QBCore/Qbox/ox, oxmysql/MariaDB, NUI basics, networking/state bags, 15 security rules. No Enhanced, txAdmin depth, vehicles/mapping, licensing, performance scaling.
- **Quality:** Well engineered (CI, symbol verification, fail-closed HTTP mode, tests). Prose is accurate on most mainstream points but has several factual slips (ped config flag 35, `use_experimental_fxv2_oal`, ox_core "no version", dependency error = load order, ox_commands contents, QBCore colon advice). Much shallower than our skill: almost every API it documents is already in our references, usually with more detail.
- **Freshness:** v0.2.0 dated 2026-08-10, last commit 2026-08-11. Pins ox_lib 3.38.0 / ox_inventory 2.47.8 (refs also say 2.44.1) / ox_target 1.17.2 / ox_core 1.5.1 — all behind our 2026-10-07 baseline. Still lists `xbl`/`live` identifiers, `set onesync on`, `sv_enforceGameBuild 3095`.

### Findings

| # | Claim | Repo file | In our skill? | Verdict | Source / notes |
|---|---|---|---|---|---|
| 1 | server.cfg/console splits commands on `;` (and newlines); a `;` is not a comment; only `"..."` protects it | skills/fivem-server-ops/SKILL.md, skills/doctor | **No** (only connection-string format listed) | CONFIRMED | `code/client/citicore/console/Console.cpp` `Context::ExecuteBuffer`: `if (!inQuote && m_commandBuffer[i] == ';') break;` https://github.com/citizenfx/fivem/blob/master/code/client/citicore/console/Console.cpp |
| 2 | `/fivem:doctor` flags every cfg line containing `;` | skills/doctor/SKILL.md, scripts/detect-stack.mjs | — | WRONG (over-broad) | Same source: `;` inside double quotes does not split. Only unquoted `;` is a defect. |
| 3 | `SetPedConfigFlag` flag 35 = "no idle anims" | skills/fivem-core/references/natives.md | partial (we list 32, 184) | WRONG | Flag 35 = `CPED_CONFIG_FLAG_UseHelmet` https://github.com/citizenfx/natives/blob/master/PED/SetPedConfigFlag.md |
| 4 | `use_experimental_fxv2_oal` = "newer object-attribute loader" | fivem-core/references/fxmanifest.md | Yes (correct: "one argument list") | WRONG | Our fxmanifest.md/runtimes.md are right. |
| 5 | QBCore player methods are now a class: `Player:AddMoney(...)`; `.Functions` is a compat shim; "write the colon form in new code" | fivem-frameworks/references/qbcore.md | Partial (we say metatable + wrappers) | CONFIRMED (class) / WRONG (advice) | `server/player.lua` defines `function Player:AddMoney` and `self.Functions = buildMethodTable(self)` (bound wrappers). `exports['qb-core']:GetPlayer` returns `buildInterface()` whose top-level methods are those bound wrappers — calling `iface:AddMoney('cash', 5)` passes the table as `moneytype` and errors. Objects crossing a resource boundary also lose metatables (inferred). Use dot form from other resources. https://github.com/qbcore-fivem/qb-core/blob/main/server/player.lua |
| 6 | `GetStreetNametAtCoords` typo is the real QBCore API | qbcore.md | Yes | CONFIRMED | `client/functions.lua:1067` (qbcore-fivem/qb-core main) |
| 7 | QBCore `RemoveMoney` "returns false if unaffordable" | qbcore.md | Yes (more precise) | WRONG (oversimplified) | Returns false only for `Config.Money.DontAllowMinus` types (cash, crypto) or below `MinusLimit` (-5000); `bank` can go negative. player.lua `Player:RemoveMoney`. Ours is correct. |
| 8 | "ox_core declares no `version` in its fxmanifest — pin by commit" | ox-stack/SKILL.md | — | WRONG | fxmanifest is generated at build by `@overextended/fx-utils` `createFxmanifest`, which writes `version: pkg.version` (package.json = 1.5.14). Repo has no committed fxmanifest; release zips do. https://github.com/overextended/ox_core/blob/main/build.js |
| 9 | `coxdocs.dev` redirect drops the path and serves the homepage | ox-stack/SKILL.md | Partial ("redirects here") | CONFIRMED | `curl -I https://coxdocs.dev/ox_lib/Modules/Callback/Lua/Server` → `301 https://overextended.dev/` |
| 10 | ox_lib web UI = React 18 + Mantine + Framer Motion; ox_inventory = React 19 + Redux + SCSS | skills/fivem-nui | Partial | CONFIRMED | ox_lib `web/package.json`: react 18.2.0, @mantine/core ^5.10.0, framer-motion ^8.0.2; ox_inventory: react ^19.2.5, @reduxjs/toolkit ^1.9.7, sass |
| 11 | ox_target `canInteract(entity, distance, coords, name, bone)` | ox-target.md, migration-map.md | Yes | CONFIRMED | `client/main.lua:121` `pcall(option.canInteract, entityHit, distance, endCoords, option.name, bone)` |
| 12 | "Always remove ox_target options on onResourceStop or they stack as duplicates" | ox-target.md | Yes (precise) | WRONG (mostly) | ox_target auto-removes the stopping resource's zones/models/entities/global ped/vehicle/object/player options (`client/api.lua:414`); only `addGlobalOption` entries are not cleaned. Ours already says exactly this. |
| 13 | `lib.setClipboard` silently fails if another NUI already holds focus; newline must be written `\t\n` | ox-stack/references/ox-lib.md | **No** | CONFIRMED | overextended.dev ox_lib docs (llms-full.txt, "lib.setClipboard" callouts) |
| 14 | oxmysql queues queries until connected, so `MySQL.ready` is not required | fivem-frameworks/references/migration-map.md | Partial | CONFIRMED (with caveat) | `src/database/connection.ts` `getConnection`: `while (!pool) await sleep(0);`. `.await` still needs a coroutine; `MySQL.ready` remains useful to run schema setup once. https://github.com/overextended/oxmysql/blob/main/src/database/connection.ts |
| 15 | ox_banking is TypeScript; client exports `openBank()` / `openAtm()`; money logic lives in ox_core accounts | ox-stack/references/ox-banking.md | Partial (no exports) | CONFIRMED | `src/client/index.ts` `exports('openAtm', …)`, `exports('openBank', …)` https://github.com/overextended/ox_banking |
| 16 | ox_commands "ships very little — /freeze and /thaw" | ox-stack/references/ox-commands.md | Yes (generic) | WRONG | Server: `freeze`, `thaw`; client: `goback`, `tpm`, `setcoords`, `coords`, `noclip`, car menu (`client/main.lua`, `client/carmenu.lua`). |
| 17 | ox_doorlock exports/events (`getDoor`, `getDoorFromName`, `getAllDoors`, `setDoorState`, `editDoor`, `registerHook`, `removeResourceHook`, client `useClosestDoor`, `pickClosestDoor`, …); `ox_doorlock:loaded(doors)` | ox-doorlock.md | Yes (more complete: createDoor/removeDoor) | CONFIRMED / WRONG detail | `ox_doorlock:loaded` is triggered with no arguments; `stateChanged` passes a boolean `state` (server/main.lua:310,335,340). |
| 18 | `Could not find dependency X for resource Y` = X ensured after Y (load order) | docs/hooks.md, fivem-server-ops | Yes (correct) | WRONG | `ResourceDependencyLoader.cpp`: declared dependencies are started automatically; the message means the resource X is not known/present. https://github.com/citizenfx/fivem/blob/master/code/components/citizen-resources-core/src/ResourceDependencyLoader.cpp |
| 19 | RedM resources need `rdr3_warning '<acknowledgement>'` | fxmanifest.md | No | CONFIRMED | `ext/system-resources/resources/chat/fxmanifest.lua` line 24 (exact string) |
| 20 | `dependency '/assetpacks'` for escrowed asset packs | fxmanifest.md | No | UNVERIFIABLE | Not in citizenfx/fivem source or the manifest docs. Do not add. |
| 21 | `PerformHttpRequest(url, cb, method, data, headers, options)` defaults GET/''/{}; `options.followLocation` default true; cb gets `(status, body, headers, errorData)` | fivem-core/references/lua-runtime.md | Partial (Await only) | CONFIRMED | `data/shared/citizen/scripting/lua/scheduler.lua:378-410`; on dispatch failure it calls `cb(0, nil, {}, 'Failure handling HTTP request')`. |
| 22 | Identifier types include `xbl`, `live` | lua-runtime.md | Yes (removed) | OUTDATED | Removed 2026-04-27 (our versions.md / server-ops.md). |
| 23 | server.cfg template: `set onesync on`, `sv_enforceGameBuild 3095` | fivem-server-ops | Yes | OUTDATED | OneSync forced on (2026-08-16); latest game build 3889. |
| 24 | ox pins: ox_lib 3.38.0, ox_inventory 2.47.8 / 2.44.1, ox_target 1.17.2, ox_core 1.5.1 | ox-stack | Yes | OUTDATED | Current: 3.40.0 / 2.48.0 / 1.18.1 / 1.5.14 (our versions.md). |
| 25 | LuaLS `checkThirdParty: "Ask"` prompts, which an agent/CI run cannot answer → load `fivem-lls-addon/library` via `workspace.library` and set `checkThirdParty` to `Disable`; the addon has no manifest-directive declarations, so `fxmanifest.lua` shows undefined-global warnings unless declared | docs/lsp.md, lua/fxmanifest.lua | Partial (we ship "Ask") | CONFIRMED | Addon tree has only `library/runtime/*` + natives and `config.json` (`files: ["fxmanifest.lua"]`, no manifest globals) https://github.com/overextended/fivem-lls-addon ; LuaLS setting values Ask/Apply/ApplyInMemory/Disable https://luals.github.io/wiki/settings/#workspacecheckthirdparty |
| 26 | `.lsp.json` `settings` are not `${CLAUDE_PLUGIN_*}`-interpolated | docs/lsp.md | n/a | UNVERIFIABLE | Claude Code harness behaviour, not FiveM. Out of scope. |
| 27 | SEC-6: "add the item first, take payment only once the add succeeded" | fivem-security/SKILL.md, patterns.md | **Conflicts** with our "Remove before add" | CONFIRMED as a valid pattern (context-dependent) | ox_inventory shops do `canAffordItem` → `Inventory.SetSlot` (add) → `removeCurrency` with **no yield in between** (`modules/shops/server.lua:256-290`). Both orders are safe only if nothing yields between check and both mutations; with an await in between, remove first and refund on failure. See integration I-5. |
| 28 | Atomic `UPDATE … SET cash = cash - ? WHERE … AND cash >= ?`, check affectedRows | fivem-mariadb | Yes | CONFIRMED | database-optimization.md §7.5 already. |
| 29 | MySQL 8 reserved words / no defaults on JSON/LONGTEXT; prefer MariaDB; no XAMPP | fivem-mariadb | Yes | CONFIRMED | Covered. |
| 30 | `MySQL.prepare` only `?`; no TINYINT→bool; "DATE does not come back as the usual datestring" | fivem-mariadb | Yes (more precise) | OUTDATED (date part) | Ours: dates are converted since 2.11.0 per source. |
| 31 | `mysql_transaction_isolation_level` 1–4, default 2; `oxmysql_debug add/remove` | fivem-mariadb | Yes | CONFIRMED | Covered. |
| 32 | State bags: server→client replication, client writes local unless `set(k,v,true)`; shallow nested set does not replicate; bag names `player:`/`entity:`/`localEntity:` | fivem-networking | Yes | CONFIRMED | Covered (onesync-entities.md). |
| 33 | Orphan modes 0/1/2, ~424-unit scope, lockdown strict/relaxed/inactive, culling-radius natives deprecated | fivem-networking | Yes | CONFIRMED | Covered. |
| 34 | `NetworkGetNetworkIdFromEntity` is client-only | fivem-core/references/natives.md | Yes | WRONG | Exists on server too (our natives refs). |
| 35 | NUI devtools at `http://localhost:13172/`, `nui_devtools`, `cfx-nui-<res>` URLs, Vite `base: './'`, always call `cb`, release focus on `onResourceStop` | fivem-nui | Yes | CONFIRMED | Covered (nui.md, tooling.md). |
| 36 | `nui://` "is no longer a secure context in current Chromium" | fivem-nui | — | UNVERIFIABLE | No primary source found. |
| 37 | `Wait(5)`/`Wait(10)` "behave inconsistently across refresh rates" | fivem-core/SKILL.md | — | UNVERIFIABLE | Opinion; `Wait(n<frame time)` simply yields one frame. |
| 38 | resmon: >0.5 ms "deserves attention", >2 ms "a problem" | fivem-server-ops | Conflicts mildly (ours: idle 0.00–0.02 ms) | UNVERIFIABLE | Rule of thumb; keep ours. |
| 39 | ESX API surface (`GetExtendedPlayers`, `getSSN`, `getPlayTime`, `togglePaycheck`, `RegisterCommand(name, group, cb, allowConsole, {validate, arguments})`, `SecureNetEvent`) | fivem-frameworks/references/esx.md | Yes | CONFIRMED | Covered. |
| 40 | `source` invalid after a yield; `local src = source` | security SEC-3 | Yes | CONFIRMED | Covered (runtimes.md, security.md). |

**Verdict counts** (rows #5 and #17 are counted in two columns because they split): CONFIRMED 23 (incl. #5 class part, #27) · OUTDATED 4 · WRONG 11 (incl. #5 advice, #17 detail) · UNVERIFIABLE 6. Genuinely new for our skill: #1, #13, #14 (nuance), #15, #19, #21, #25, #27 (nuance), #5 (export-colon warning), #9 (path drop).

### Recommended integrations

**I-1 → `references/convars-and-commands.md`** (near the `set`/quoting line) and one line in `server-ops.md` server.cfg section:
```markdown
- **`;` separates commands** in server.cfg and the console (Quake-style), exactly like a newline. `set foo a;b` runs `set foo a` and then a command `b`. Only double quotes protect it: `set mysql_connection_string "user=fivem;password=x;host=127.0.0.1;database=fivem"`. Comments are `#` — never `;`. Source: `Context::ExecuteBuffer` in https://github.com/citizenfx/fivem/blob/master/code/client/citicore/console/Console.cpp
```
And in `database-oxmysql.md` after the format table:
```markdown
The key/value form **must be quoted** in server.cfg: an unquoted `;` splits the line into separate console commands (see convars-and-commands.md).
```

**I-2 → `scripts/audit.py` CFG_RULES** (proposed rule; heuristic, quote-aware):
```python
("cfg-unquoted-semicolon", "medium", r'^(?:[^"#\n]|"[^"\n]*")*;',
 "Unquoted ';' in a cfg line: FiveM splits commands on it (it is not a comment). Quote the value or move it to its own line."),
```

**I-3 → `references/ox-lib-ui.md`** (replace the `lib.setClipboard` bullet):
```markdown
- `lib.setClipboard(text)` copies text to the player's clipboard through NUI. It silently does nothing if another NUI page currently holds focus, and line breaks must be written as `\t\n` (plain `\n` is dropped). Source: https://overextended.dev/docs/ox_lib (Interface → Clipboard)
```

**I-4 → `references/framework-qbcore.md` §3** (after "Since 2026-05 the player is a metatable class…"):
```markdown
Internally methods are defined as `function Player:AddMoney(...)`, but **from another resource always use the dot form** (`Player.Functions.AddMoney('cash', 5)` or, on the `exports['qb-core']:GetPlayer(src)` interface, `Player.AddMoney('cash', 5)`). Those are pre-bound wrappers (`buildMethodTable`/`buildInterface` in `server/player.lua`); calling them with a colon passes the table as the first argument (`moneytype`) and errors, and metatable methods do not survive the export boundary. Source: https://github.com/qbcore-fivem/qb-core/blob/main/server/player.lua
```

**I-5 → `references/security.md`** (replace the bullet "**Remove before add**; `CanCarryItem` before `AddItem`; give back on failure."):
```markdown
- **No yield between check and mutations.** Check (`CanCarryItem`, balance) and perform both mutations in one uninterrupted block: ox_inventory's own shops check `canAfford`, add the item, then remove the currency with no `Wait`/await in between (`modules/shops/server.lua`). If anything in between yields (DB await, callback), **remove first**, then add, and refund on failure — or use one atomic SQL statement (`… AND balance >= ?`). Source: https://github.com/overextended/ox_inventory/blob/main/modules/shops/server.lua
```

**I-6 → `references/runtimes.md`** (HTTP row, after `PerformHttpRequestAwait`):
```markdown
| `PerformHttpRequest(url, cb, method?, data?, headers?, options?)` | Server. Defaults `'GET'`, `''`, `{}`; `options.followLocation` defaults to `true`. `cb(status, body, headers, errorData)`; if the request cannot be dispatched, `cb(0, nil, {}, 'Failure handling HTTP request')`. `PerformHttpRequestAwait` returns the same four values. Source: `data/shared/citizen/scripting/lua/scheduler.lua` |
```

**I-7 → `references/database-oxmysql.md`** (§ MySQL.ready, after the example):
```markdown
Queries sent before the pool exists are not lost: `getConnection()` waits (`while (!pool) await sleep(0)`) until oxmysql has connected, so `MySQL.ready` is only needed to run one-time setup in order, not to make queries safe. `.await` still needs a coroutine. Source: https://github.com/overextended/oxmysql/blob/main/src/database/connection.ts
```

**I-8 → `references/ox-resources-misc.md`** (ox_banking row note):
```markdown
ox_banking is TypeScript; its only script API is client `exports.ox_banking:openBank()` and `exports.ox_banking:openAtm()`. Wages, fines and transfers go through ox_core accounts (ox-core.md §8), not ox_banking. Source: https://github.com/overextended/ox_banking/blob/main/src/client/index.ts
```
And replace the ox_commands row note with: `server /freeze, /thaw (lib.addCommand, restricted); client /goback, /tpm, /setcoords, /coords, /noclip, car menu`.

**I-9 → `references/tooling.md`** (after the `.luarc.json` block):
```markdown
**Headless / CI / AI-agent runs:** `checkThirdParty: "Ask"` raises a prompt nobody can answer. Instead point `workspace.library` at the addon's `library` folder (e.g. `C:/dev/lua-addons/fivem-lls-addon/library`), copy `runtime.version`/`nonstandardSymbol` from its `config.json`, and set `"workspace.checkThirdParty": "Disable"`. The addon declares no manifest directives, so `fxmanifest.lua` reports `fx_version`, `client_scripts`… as undefined globals — add them to `diagnostics.globals` (or a small `---@meta` file) rather than ignoring the file, so typos like `client_scirpts` stay visible. Sources: https://github.com/overextended/fivem-lls-addon · https://luals.github.io/wiki/settings/
```

**I-10 → `references/versions.md` §2** (Docs line): `Docs: https://overextended.dev/docs (coxdocs.dev 301-redirects to the **homepage**, dropping the path — rewrite old deep links by hand).`

**I-11 (optional, RedM) → `references/fxmanifest.md` table:**
```markdown
| `rdr3_warning '…'` | — | Required for `game 'rdr3'` resources; exact string: `'I acknowledge that this is a prerelease build of RedM, and I am aware my resources *will* become incompatible once RedM ships.'` (citizenfx `ext/system-resources/resources/chat/fxmanifest.lua`). |
```

**I-12 → `references/natives-essentials.md`** (SetPedConfigFlag row): append `35 = UseHelmet (auto-wear helmet on bikes) — not "no idle anims"` to pre-empt a common wrong claim.

### Structural ideas worth copying

1. **Extra audit.py rules** (from `mcp/src/audit.mjs`), all low-false-positive by design:
   - `source-after-yield`: inside a `RegisterNetEvent`/`AddEventHandler` body, `source` used after the first `.await(`/`Wait(` with no `local x = source` before it (high).
   - `command-ungated`: `lib.addCommand` without `restricted` (or `restricted = false`) or raw `RegisterCommand` without `IsPlayerAceAllowed`/`HasPermission`/`source == 0`, **only when the body calls a privileged action** (`AddMoney|addAccountMoney|:deposit|AddItem|addInventoryItem|SetJob|setGroup|SetEntityCoords|DropPlayer|SetPlayerRoutingBucket|GiveWeapon…`) — the privileged-action filter is what keeps noise down. Skip `ESX.RegisterCommand` (group is arg 2).
   - `broadcast-sensitive`: `TriggerClientEvent(name, -1, …)` whose args mention identifier/license/discord/token/money/bank/coords (medium).
   - `secret-literal` in client/shared: `\bsk-[A-Za-z0-9]{16,}`, `Bearer\s+[A-Za-z0-9._~+/-]{20,}`, `(api_?key|secret|password|token)\s*=\s*['"][^'"]{12,}` (we only match Discord webhooks).
   - `while true` without Wait: skip loops containing `break`/`return`/`goto` (avoids flagging algorithmic loops like ox_lib's heap).
   - Strip comments and string contents before matching, keep strings for secret rules.
2. **Server "doctor" pass** (`scripts/manifest.py` or a new `doctor.py`): resources `ensure`d in server.cfg but missing on disk; more than one framework core present (`es_extended` + `qb-core`/`qbx_core`); manifest script paths whose case differs from disk (Linux breakage).
3. **Symbol verification in CI** (`scripts/verify-docs.mjs`): extract every `exports.x:Y`, `lib.*`, `Ox.*`, `QBCore.Functions.*` symbol from the reference markdown and assert it exists in freshly cloned upstream sources; unknown → fail, cannot-check → fail ("a check that cannot check must fail"). Would harden our "never invent APIs" rule.
4. **Refute pass for audits** (`workflows/audit-server.js`): after collecting CRITICAL/HIGH findings, a second pass tries to disprove each; anything not covered is reported as "unaudited", never "clean". Worth adding as a sentence to our audit workflow in SKILL.md.
5. **Audit report format**: `[RULE · SEVERITY] path:line` + concrete exploit sentence + one-line fix; "if a rule does not genuinely apply, leave it out". Similar to ours; their "state the concrete exploit" phrasing is good.
6. MCP-side: official-docs corpora fetched per user (validated on content, not HTTP status — ESX docs return 200 HTML for any path). Useful caution if we ever add doc fetching to `natives.py`-style scripts.

---

## bworthy89/fivem-server-development — analysis (verified 2026-10-07)

### Summary
- **Purpose:** Claude skill for building on a **Qbox + ox_*** stack on **Windows**. It explicitly covers only eight failure modes that were *measured*, not the full platform: recalled APIs, client-trusted quantities, missing grade checks, secrets in `shared_scripts`, missing `dependencies`, guessed asset names, hardcoded builds, and NUI rebuild/focus problems.
- **Structure:** a router `SKILL.md` (4 rules, 5 house rules, a verification loop and an anti-pattern table) plus 10 references one level deep: server-setup, resource-anatomy, qbox-api, jobs, activities, content, performance, nui-react, mlo-mapping and troubleshooting. It also ships `scripts/install-qbox.ps1`, a resumable re-implementation of the txAdmin Qbox recipe, and `evals/` with 5 scenarios, verbatim **baseline** (no skill) runs, **green** (with skill) runs and a SCORECARD. CI (`validate-skill.ps1`) checks SKILL.md under 500 lines, the name/description limits, links one level deep and forward slashes.
- **Scope:** narrow by design. It is Qbox-only, has no ESX/QBCore, and only touches convars, OneSync entities and natives lightly. It deliberately avoids baking in APIs: "look it up live: installed source > Context7 qbox-docs > docs.fivem.net > overextended.dev > forge.plebmasters.de".
- **Quality:** high on security discipline. The derive-don't-clamp payout pattern and the start/complete single-use token are excellent. Some "verified" claims are already stale or wrong: IsGradeBoss, RegisterNetEvent for OnPlayerLoaded, `lua54` and the OneSync requirement.
- **Freshness:** last commit 2026-07-28. It predates OneSync being forced on (2026-08-16). The installer still lists `qbx_radio`, which is archived, and `qbx_smallresources`.

### Findings
| # | Claim | Repo file | In our skill? | Verdict | Source / notes |
|---|---|---|---|---|---|
| 1 | A client may report *that* something happened, never *how much*. Clamping a client quantity is not validation; derive the payout from state the server observed or recorded at job start | SKILL.md R2, jobs.md | Partial. security.md §4 says "type-check and **clamp**"; gameplay-patterns has `activeJobs[src]` | CONFIRMED (sound design) | Not a platform fact; consistent with docs.fivem.net "never trust the client". **Add** (see I-1) |
| 2 | Start/complete **single-use pending token** (record at start, `nil` at completion, elapsed-time floor, re-check distance, clear on `playerDropped`) | jobs.md, activities.md | Partial (security.md:115 elapsed time only) | CONFIRMED (pattern) | Add as a snippet (I-1) |
| 3 | Re-check job **and grade** (and onduty) on every privileged event; ox_target `groups` is client-side only | SKILL.md R3 | Yes (security.md §2 "Job/grade") | CONFIRMED / covered | — |
| 4 | Loot weights, prices and cooldowns in `shared_scripts` are public | SKILL.md R4 | Yes (security.md:29; `Config`/`ServerConfig` convention) | covered | — |
| 5 | `exports.qbx_core:IsGradeBoss` throws (`groupData[grade].IsBoss`) | jobs.md | Ours lists it as returning `boolean` | **OUTDATED** | Fixed in qbx_core c872afc (#710, 2025-09-06); main/v1.24.0: `return groupData.grades[grade].isboss`. Nuance for us: it still **errors** if `grade` doesn't exist and returns `nil` (not `false`) when `isboss` is unset. https://github.com/Qbox-project/qbx_core/blob/main/server/functions.lua |
| 6 | `RegisterNetEvent('QBCore:Client:OnPlayerLoaded')` "never fires"; you must use AddEventHandler | qbox-api.md, troubleshooting.md | Ours says either works | **WRONG** (ours is right) | qbx_core itself uses `RegisterNetEvent('QBCore:Client:OnPlayerLoaded', ...)` in client/events.lua:4. It is fired by a local `TriggerEvent` in client/character.lua:281/483, and `RegisterNetEvent(name, fn)` also registers a local handler |
| 7 | `CreateJob` is runtime-only and never persists | qbox-api.md, jobs.md | Ours: `CreateJob(name, job, commitToFile?)` | **OUTDATED** (ours right) | qbx_core server/groups.lua:181 `CreateJob(jobName, job, commitToFile)` rewrites shared/jobs.lua when the flag is true |
| 8 | `player.Functions.SetJobDuty` / `.SetPlayerData` are `---@deprecated`; use the `SetJobDuty` / `SetPlayerData` exports | jobs.md | Yes (framework-qbox) | CONFIRMED / covered | server/player.lua:804/810 |
| 9 | Qbox ships default jobs including `mechanic`, `taxi`, `tow`, `trucker`... Extend an existing job instead of duplicating it | jobs.md | Not stated | CONFIRMED | shared/jobs.lua: unemployed, police, bcso, sasp, ambulance, realestate, taxi, bus, cardealer, mechanic, judge, lawyer, reporter, trucker, tow, garbage, vineyard, hotdog. Add (I-4) |
| 10 | jobs.lua fields `type`, `defaultDuty`, `offDutyPay`, `isboss`, `bankAuth` (separate permissions) | jobs.md | Yes (framework-qbox:360) | covered | — |
| 11 | `lua54 'yes'` is "not optional"; without it there is no `//`, bitwise ops or goto | resource-anatomy.md, troubleshooting.md | Ours: deprecated no-op | **WRONG / OUTDATED** | Lua 5.3 removed 2025-06-24 (versions.md) |
| 12 | Without `set onesync on`, ox_lib fails with "OneSync needs to be enabled", which cascades into `global 'lib'` nil errors; the recipe's `$onesync: on` is injected as a launch arg, not written to server.cfg | troubleshooting.md, server-setup.md | Ours: OneSync forced; no `set onesync` | **OUTDATED** on artifacts ≥ 2026-08-16. The mechanism is CONFIRMED | ox_lib fxmanifest has `dependencies { ..., '/onesync' }`; the recipe has `$onesync: on` (Qbox-project/txAdminRecipe qbox.yaml). It matters only for old artifacts, which can't be joined after 2026-10-15 |
| 13 | "Read the first error": dozens of `global 'lib'` errors are one ox_lib start failure | troubleshooting.md | Yes ("first error wins", SKILL.md/debugging) | covered | — |
| 14 | Qbox install docs: "Do not use the buttons at the top. Download directly from the list." MySQL/XAMPP not supported; MariaDB ≥ 10.9 | server-setup.md | MySQL/XAMPP and 10.9: yes. "Buttons" advice: **no**. Ours recommends Recommended | CONFIRMED (Qbox docs say it). The repo's reason ("Qbox has not validated") is UNVERIFIABLE | https://docs.qbox.re/installation. Mention as a Qbox-specific instruction (I-5) |
| 15 | node-mysql2 (oxmysql, txAdmin) cannot negotiate MariaDB `ed25519` (or PARSEC); use a `mysql_native_password` account. MariaDB syntax `IDENTIFIED VIA mysql_native_password USING PASSWORD('…')`. `user@localhost` ≠ `user@127.0.0.1` | server-setup.md, troubleshooting.md | **Not covered** | CONFIRMED | mysql2 lib/auth_plugins/index.js exports only caching_sha2_password, mysql_clear_password, mysql_native_password, sha256_password. https://github.com/sidorares/node-mysql2/tree/master/lib/auth_plugins · https://mariadb.com/kb/en/create-user/ (I-2) |
| 16 | txAdmin error "database does not accept the required authentication method" can be misattributed; count tables in the schema to tell DB failure from download failure | troubleshooting.md | No | UNVERIFIABLE (anecdotal, one install) | The diagnostic step (`information_schema.tables` count) is sound. Include as a tip only |
| 17 | The recipe does "~40" unauthenticated GitHub downloads and is throttle-prone (`waste_time` step) | troubleshooting.md | Partial (txadmin.md: pin refs, waste_time listed) | PARTIAL | qbox.yaml has ~80 download actions and a `waste_time # prevent github throttling` at line 384. The 60 req/h figure applies to the REST API; archive downloads are rate-limited differently, so UNVERIFIED |
| 18 | PowerShell treats `[ox]` as a wildcard: `Test-Path 'resources/[ox]/x'` → False; use `-LiteralPath` | troubleshooting.md | **Not covered** | CONFIRMED (tested on PS 5.1.26100) | `Test-Path` False, `Test-Path -LiteralPath` True |
| 19 | "`New-Item` has no `-LiteralPath`; use `[IO.Directory]::CreateDirectory`" | troubleshooting.md | — | PARTIAL | New-Item indeed has no `-LiteralPath`, but `New-Item -Path '...\[qbx]\qbx_core'` worked literally in testing, so the workaround is unnecessary |
| 20 | Event payload: "16 KB hard, keep < 8 KB; 64 KB per tick" | performance.md | Ours documents measured limits (netEventSize 128 KiB/s etc.) | **UNVERIFIABLE / likely WRONG** | No such constants found in citizenfx source. Keep ours |
| 21 | Nested table depth limit of 16 for events | performance.md | **Not covered** | **CONFIRMED (with nuance)** | citizenfx/lua-cmsgpack `MP_MAX_NESTING 16`. Without `LUA_MSGPACK_ERROR_NESTING` (not defined in `code/vendor/lua-cmsgpack.lua`), tables at depth ≥ 16 are **silently packed as nil**, with no error. https://github.com/citizenfx/lua-cmsgpack/blob/f46b4a3a7f5fb9d9a05f994ae717a5bb9a3f7122/src/lua_cmsgpack.h (I-3) |
| 22 | `lib.points`: outer scan every 300 ms; `nearby` ticks only in range | performance.md | Yes (ox-lib-world:218) | CONFIRMED / covered | ox_lib imports/points/client.lua `Wait(300)` |
| 23 | Idle threshold > 0.05 ms = misbehaving | performance.md | Ours 0.00–0.02 ms | minor difference | keep ours |
| 24 | `lib.setNuiFocus(allowInput, disableCursor)`: the 2nd parameter is **inverted** vs `SetNuiFocus`, and `allowInput` maps to `SetNuiFocusKeepInput` | nui-react.md | Signature listed (ox-lib-ui:246); the inversion is not called out | CONFIRMED | ox_lib resource/interface/client/main.lua:13-17 (I-6) |
| 25 | NUI focus watchdog (UI pings, release after 10 s silence) + React error boundary that calls `close` in `componentDidCatch` | nui-react.md | No (ours: close/Esc/death/onResourceStop) | CONFIRMED as a design pattern (React error-boundary API is standard) | I-6 |
| 26 | `data_file 'DLC_ITYP_REQUEST'` takes a bare filename, and `.ytyp` in `stream/` needs no `files{}` entry | mlo-mapping.md | Ours uses `'stream/my_mlo.ytyp'` | CONFIRMED: **both forms work** | citizenfx/fivem LoadStreamingFile.cpp `ParseBaseName`: "parse dir/dir/blah.ityp into blah". Path stripped to base name, looked up in the `ytyp` streaming module (I-7) |
| 27 | Missing `DLC_ITYP_REQUEST` = interior streams but renders nothing; one line per `.ytyp` | mlo-mapping.md | Yes (mapping-streaming §3) | covered | — |
| 28 | Old building persists after `RemoveIpl` → interior proxy (`_milo_`) placed by another ymap; author a deletion ymap | mlo-mapping.md | No | UNVERIFIABLE (community practice; no primary doc) | Could be added as a hedged tip |
| 29 | Archive has only `.ymap`/`.ytyp`/`.ybn` and no `.ydr`/`.ytd` → incomplete download | mlo-mapping.md | No | CONFIRMED by file-type semantics (docs assets manual) | Small checklist line (I-7) |
| 30 | `EnableInteriorProp` + `RefreshInterior` | mlo-mapping.md | Ours uses `ActivateInteriorEntitySet` (current name) | Ours better; theirs uses the legacy alias | — |
| 31 | `nui_devtools`; rebuild NUI then `restart`; Vite `base:'./'` | nui-react.md | Yes (nui.md, debugging) | covered | — |
| 32 | Reload matrix (`refresh` only for new folders/manifests; `restart` for code/stream) | troubleshooting.md | Partly (debugging.md:68) | CONFIRMED (generic) | Optional table (I-8) |
| 33 | Ped spawn `z - 1.0`, `SetBlockingOfNonTemporaryEvents`, `IsModelValid` guard | content.md | Yes (gameplay-patterns:63-66) | covered | — |
| 34 | Set `vehicleid` state bag for owned vehicles; pass props into the spawn function | content.md | Yes (framework-qbox:269, rp-systems) | covered | — |
| 35 | Asset-name lookup via forge.plebmasters.de; grep installed resources for already-working prop names | content.md | Plebmasters: yes (natives-essentials). Grep tip: no | CONFIRMED (tip) | — |
| 36 | Installer resource list (qbx_radio, qbx_smallresources...) | install-qbox.ps1 | — | OUTDATED | qbx_radio archived (gh api). qbx_smallresources is **not** archived (pushed 2026-09-30) and is still in the official recipe, which conflicts with our versions.md "deprecated" label; worth re-checking (another group's scope) |

**Counts:** CONFIRMED 19 (6 not previously covered: #1/2, #9, #15, #18, #21, #24/25, #26) · OUTDATED 5 (#5, #7, #12, #36, plus the stale `lua54` half of #11) · WRONG 2 (#6, #11) · UNVERIFIABLE 4 (#16, #20, #28, #14's rationale) · PARTIAL 2 (#17, #19).

**Side finding in our own skill (not from the repo):** `security.md:161`, `use-vs-avoid.md:185` and `performance-server-scaling.md:83` still recommend `sv_endpointPrivacy true`, but versions.md, server-ops.md and convars-and-commands.md say it was removed on 2026-07-08. This is an internal inconsistency to fix.

### Recommended integrations

**I-1 → `references/security.md`** (after rule 4 "What?"):
```md
- **Clamping is not validation for privileged quantities.** A client may report *that* something finished, never *how much*. If a payout depends on a quantity (damage repaired, distance driven, items found), the server must have observed or recorded it. Pattern: on `start`, store `pending[src] = { startedAt = os.time(), netId = netId, before = <server-read value> }`; on `complete`, take `pending[src]` (nil → reject), set it to `nil` immediately (single use, blocks replays), reject if the elapsed time is below the minimum, re-check distance, compute the payout from the stored record plus `ServerConfig`, and clear `pending[src]` on `playerDropped`. Source: docs.fivem.net "never trust the client".
```

**I-2 → `references/database-oxmysql.md`** (troubleshooting) and a cross-link in `server-ops.md` install:
```md
- **"Your database does not accept the required authentication method"**: oxmysql and txAdmin use node-mysql2, which supports only `mysql_native_password`, `caching_sha2_password`, `sha256_password` and `mysql_clear_password`. It has no MariaDB `ed25519`/`parsec` (https://github.com/sidorares/node-mysql2/tree/master/lib/auth_plugins). Check with `SELECT user, host, plugin FROM mysql.user;`. Create a dedicated, non-root account:
  `CREATE USER 'fivem'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('…');` (MariaDB syntax; MySQL uses `IDENTIFIED WITH … BY`) and grant only the server database: `GRANT ALL ON qbox.* TO 'fivem'@'localhost';`. `user@localhost` and `user@127.0.0.1` are different accounts.
```
(Note: grant on `db.*`, not `*.* WITH GRANT OPTION` as the repo does.)

**I-3 → `references/events-and-callbacks.md` §11** and `runtimes.md` §8 (msgpack):
```md
- **Max table nesting 16.** Lua payloads are packed by citizenfx/lua-cmsgpack with `MP_MAX_NESTING 16`. Without `LUA_MSGPACK_ERROR_NESTING`, a table nested 16+ levels deep is **silently sent as `nil`**, with no error. Flatten deep structures. Source: https://github.com/citizenfx/lua-cmsgpack/blob/f46b4a3a7f5fb9d9a05f994ae717a5bb9a3f7122/src/lua_cmsgpack.h (`lua_pack_any`).
```

**I-4 → `references/framework-qbox.md`** (jobs config row and exports table):
```md
- qbx_core already ships these jobs in `shared/jobs.lua`: unemployed, police, bcso, sasp, ambulance, realestate, taxi, bus, cardealer, mechanic, judge, lawyer, reporter, trucker, tow, garbage, vineyard, hotdog. "Create a mechanic job" usually means extending `['mechanic']`, not adding a duplicate key.
- `IsGradeBoss(group, grade)` (fixed in #710, 2025-09) returns `grades[grade].isboss`, which is `nil` when unset, and **errors** if `grade` doesn't exist. Prefer `player.PlayerData.job.isboss` for the player's own grade.
```

**I-5 → `references/server-ops.md` §1** (selection rule):
```md
- Qbox's install guide says: "Do not use the buttons at the top. Download directly from the list" of the runtime.fivem.net artifacts index (https://docs.qbox.re/installation). Pick the Recommended build number from the API/download page and download that exact build from the list.
```

**I-6 → `references/nui.md` §5** (focus management):
```md
- `lib.setNuiFocus(allowInput, disableCursor)` is **not** `SetNuiFocus(hasFocus, hasCursor)`: it always focuses, the 2nd argument is inverted (`true` hides the cursor), and `allowInput` sets `SetNuiFocusKeepInput`. Pair it with `lib.resetNuiFocus()` (ox_lib resource/interface/client/main.lua).
- Make stuck focus impossible: route every focus change through one function. In React, wrap the app in an error boundary whose `componentDidCatch` calls `fetchNui('close')`. Optionally have the UI `ping` a NUI callback every few seconds while open, and let Lua release focus if no ping arrives for ~10 s. Emergency recovery: `SetNuiFocus(false, false)`.
```

**I-7 → `references/mapping-streaming.md` §3:**
```md
- `data_file 'DLC_ITYP_REQUEST'` is resolved by **base name**: the loader strips folders and the extension (`stream/sub/my_mlo.ytyp` → `my_mlo`, LoadStreamingFile.cpp `ParseBaseName`). So `'my_mlo.ytyp'` and `'stream/my_mlo.ytyp'` both work, `.ytyp` files under `stream/` need no `files{}` entry, and two resources shipping the same `.ytyp` name collide.
- A pack with only `.ymap`/`.ytyp`/`.ybn` and no `.ydr`/`.ydd`/`.ytd` is missing its geometry (incomplete download), not misconfigured.
```

**I-8 → `references/tooling.md`** (Windows section):
```md
- PowerShell treats `[ox]`, `[qbx]` in paths as wildcards: `Test-Path 'resources/[ox]/ox_lib'` returns False even when it exists. Use `-LiteralPath` with Test-Path, Get-ChildItem, Copy-Item, Remove-Item and Expand-Archive (New-Item has no -LiteralPath, but its -Path is taken literally).
```

### Structural ideas worth copying
1. **Eval-first discipline:** `evals/NN-*.md` (query + expected behaviours + an adversarial check such as `TriggerServerEvent('<res>:payForRepair', 999999)` must be rejected), verbatim `baseline/` (no skill) vs `green/` (with skill) runs, and a SCORECARD. This is a cheap way to prove each reference earns its context.
2. **"Do not document these" list:** an explicit list of things the model already does well, to keep SKILL.md lean.
3. **Adversarial step in the verification loop:** "fire the privileged event from F8 with a hostile payload and confirm the server refuses". Add it as step 7 of our "Create a resource" workflow.
4. **Unverifiable-API phrasing:** "Can't confirm the signature for X, so I'm flagging it rather than guessing. Everything else below is verified." This matches our rule 6 and could become a template line.
5. **Live-lookup order:** installed resource on disk (`grep -rn "exports('Name'" resources/`) before docs. We could add "grep the installed resource" as step 0 of rule 2.
6. **CI skill validator** (line and description limits, one-level links, forward slashes).

---

## MnkyArts/fivem-dev-kit — analysis (2026-10-07)

### Summary
- **Purpose:** a Claude Code plugin (with Codex and OpenCode adapters) that turns the agent into a FiveM resource developer for one person's server ("Liam", own `core` framework). It runs a plan → native-scout → implement → lint → review → deploy → in-game test-checklist pipeline.
- **Structure:** 6 skills (`fivem-scripting` is the rulebook, plus `fivem-build`, `fivem-review`, `fivem-reference`, `fivem-server`, `fivem-client`, `fivem-core`), 3 agents (scout on haiku, implementer and reviewer on opus), 5 Python CLIs in `bin/` (`fxref` is a SQLite FTS native and docs index built from alloc8or nativedb, CFX native-decls and fivem-docs; the others are `fxlint`, `fxnew`, `fxserver` and `fxclient`), a post-edit lint hook, and a dev-only in-game resource called `resources-dev/fivem-devtools` that handles screenshots, profiling, client logs and remote exec through a PowerShell agent.
- **Main claim source:** `skills/fivem-scripting/reference/runtime-facts.md` (540 lines). Every fact in it cites a `path:line` in citizenfx/fivem @`0d8a2a6f7` and fivem-docs @`e8113b6`, compiled 2026-09-11.
- **Adapters:** the `codex/` and `opencode/` folders are near-duplicates of the skills and agents. Only frontmatter and model names differ (a 90-line diff on fivem-build, mostly headers).
- **Scope:** strong on runtime internals (scheduler, events, exports, state bags, rate limits, manifest, RPC natives, KVP, JS timers, RCON). Weak on frameworks: generic ESX/QBCore/Qbox/ox snippets, because the project default is their private `core` framework. There is no DB tuning, no server scaling and no Enhanced coverage.
- **Quality:** high. It is source-cited, flags inferences as `(inferred)` or `UNVERIFIED`, and has a disciplined lint rule set (P/S/C, 30+ rules). A few claims are docs-based and lag the source: node_version, the JS vector shape, and json+vector. A couple of claims were derived from the wrong file (`json.lua` instead of the actual lua-rapidjson).
- **Freshness:** the last commit is 2026-09-18 and the facts date from 2026-09-11. Some details are now stale: "OneSync on by default" (it is now forced), Node 16 as the default, and `screenshot-basic` as a dependency (it is unmaintained, and screencapture replaces it).
- **Overlap with our skill:** about 85% is already covered, often in more depth (rate-limit table, lockdown modes, entityCreating semantics, CreatePed on the server, strict mode, export internals, profiler, `moo 31337`, KVP NoSync, PerformHttpRequestAwait 9515, string/Hash marshalling).

### Findings table
Legend for the coverage column: **Y** = covered, **P** = partial, **N** = not covered, **X** = conflicts with our skill.

| # | Claim | Repo file | Ours | Verdict | Source / notes |
|---|---|---|---|---|---|
| 1 | Client Lua has **no `io`/`os` libs**; the server gets custom permission-aware `io`/`os` (`lua_fx_openio/openos` under `#ifdef IS_FXSERVER`) | runtime-facts §15 | N (natives.md only implies it: client "Time: GetGameTimer") | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/code/components/citizen-scripting-lua/src/LuaScriptRuntime.cpp (L162-176) |
| 2 | `json.encode` has no vector support ("bundled json.lua") | SKILL §11, events.md, runtime-facts §15 | N | **WRONG** | Lua `json` is lua-rapidjson (`luaopen_rapidjson`). Its encoder handles `LUA_TVECTOR`: by default it emits `{"x":..,"y":..,"z":..[,"w"]}`, and with option `vectorarray = true` it emits `[x,y,z]`. https://github.com/citizenfx/lua-rapidjson/blob/grit/src/lua_rapidjson.hpp (L406, L961-987) |
| 3 | Lua vectors and quats travel as msgpack ext types 20/21/22/23 | events.md, runtime-facts §15 | P (runtimes.md:148 says "ext types", not the IDs) | CONFIRMED | https://github.com/citizenfx/lua-cmsgpack/blob/grit/src/lua_cmsgpack.h (L331-336) |
| 4 | "JS receives [Lua vectors] as arrays" | events.md | X (ours: JS has no unpacker; shape **UNVERIFIED**) | **WRONG** | `main.js` registers ext unpackers only for funcref 10/11 (plus Entity/Player packers). Nothing handles 20-23, so msgpack-lite yields a raw ext object, not an array. Native *returns* do arrive as arrays, which is a separate path. https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/v8/main.js (L44-51, L149-152) |
| 5 | The `exports.txAdmin` → `monitor` remap exists in **both Lua and JS** | runtime-facts §3 | P (ours: "JS alias" only) | CONFIRMED | scheduler.lua L627-631 (`resource = "monitor"`) and main.js L548-552 |
| 6 | A typo'd native or global returns `nil` silently and the miss is cached (`nilCache`). The error only appears at call time, possibly in a rare branch | SKILL §1, runtime-facts §1 | P (debugging.md maps the message, not the mechanism) | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/natives_loader.lua (L74-98) |
| 7 | `add_ace`/`remove_ace`/`add_principal` refuse to change the **currently executing principal's own** access: "Changing ones own access is not permitted." | runtime-facts §10/§15 | N | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/code/client/citicore/se/Security.cpp (L346, L391) |
| 8 | The ExecuteCommand doc says `add_acl`, but the only registered command is `add_ace` | runtime-facts §10 | N | CONFIRMED | Security.cpp L313 (`ConsoleCommand addAclCmd("add_ace", ...)`). Trivia, low value |
| 9 | `ExecuteCommand('set ...')` needs the resource to hold the `command.set` ACE; prefer `SetConvar*` natives | runtime-facts §11 | N | CONFIRMED | https://github.com/citizenfx/fivem-docs/blob/master/content/docs/scripting-reference/convars/_index.md (L47) |
| 10 | JS dispatcher sets `global.source = null` at the end of **every** dispatch, so a synchronous nested `emit` nulls the outer handler's `source` | runtime-facts §2/§15 | P (ours: "const src = source first") | CONFIRMED | main.js L486-539 |
| 11 | Lua dispatcher restores `source` right after **starting** the handler coroutine, so `source` is stale after the first `Wait` | SKILL §5 | Y | CONFIRMED | scheduler.lua L125-179 |
| 12 | Server refuses to start a resource that lacks `fx_version` ("does not specify an `fx_version`") **or** that declares both `game 'common'` and a specific game ("ill-formed") | runtime-facts §8 | N | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/ServerResources.cpp (L522-539) |
| 13 | Only `entity:` bags are auto-registered when a client writes to a not-yet-existing bag. Writes to unknown `player:`/`global` bags are dropped | runtime-facts §4 | N | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/packethandlers/StateBagPacketHandler.cpp (L154-177) |
| 14 | With `sv_stateBagStrictMode`, the server's client-write packet handlers return immediately (a silent no-op on the server) | runtime-facts §4 | Y (ours adds the client-side error text) | CONFIRMED | StateBagPacketHandler.cpp L18, L184 |
| 15 | A base-limit state-bag drop is logged "at most once per ~15 s" | runtime-facts §4 | N | WRONG (minor) | `KeyedRateLimiter<uint32_t,true> logLimiter{1.0, 1.0}` gives about 1 warning/s per client (`sbag-update-dropped`). StateBagPacketHandler.cpp L56, L104-107 |
| 16 | Assigning a field directly on `Entity(e)` or `Player(id)` (not `.state`) throws "Setting values on Entity/Player is not supported at this time." | runtime-facts §4 | N | CONFIRMED | scheduler.lua L866, L905 |
| 17 | Client `NetworkGetEntityFromNetworkId` / `GetEntityFromStateBagName` on a netId the client doesn't hold logs `GetNetworkObject: no object by ID <n>`. Guard with `NetworkDoesEntityExistWithNetworkId` | SKILL §6 (seen in-game 2026-09-12) | N | CONFIRMED (the warning exists in the client's net-object resolve hook. That state-bag name resolution goes through it is the repo's observation) | https://github.com/citizenfx/fivem/blob/master/code/components/extra-natives-five/src/EntityDeletionNatives.cpp (L93-99, hooked at L121) |
| 18 | Entity state bags replicate to clients that have the entity **out of scope** | SKILL §6 | N | UNVERIFIABLE (in-game observation only) | — |
| 19 | NUI: `backdrop-filter` renders as a solid black box in-game | SKILL §8 | P (ours: avoid for perf) | UNVERIFIABLE (single observation, 2026-09-12) | — |
| 20 | NUI can sample the **game back buffer** as a WebGL texture: set `TEXTURE_WRAP_T` to CLAMP_TO_EDGE → MIRRORED_REPEAT → REPEAT on a bound 2D texture, then draw it to a canvas and CSS-blur it (the main-menu technique) | SKILL §8 | N | CONFIRMED (hook exists) | https://github.com/citizenfx/fivem/blob/master/code/components/nui-core/src/NUIInitialize.cpp (L257-315, "'secret' activation sequence"). Note: on Legacy, CEF 103 runs V8 jitless since 2026-10-07, so keep the redraw rate low |
| 21 | `Wait(0)` is frame-bound: 60 fps ≈ 16.6 ms, 180 fps ≈ 5.5 ms. Per-frame work must use `Wait(0)`; `Wait(5/10)` skips frames at high fps | SKILL §4 | P | CONFIRMED | https://github.com/citizenfx/fivem-docs/blob/master/content/docs/scripting-reference/runtimes/lua/functions/Citizen.Wait.md |
| 22 | `onResourceStop` handlers must be synchronous (no `Wait`): the runtime is being torn down | SKILL §8, lint C011 | N | UNVERIFIABLE (sound inference, not stated in source/docs) | — |
| 23 | `RegisterNUICallback` (capitalised Lua global) is labelled **Legacy API** by docs; new code uses the `RegisterNuiCallback` native | runtime-facts §12 | P (nui.md: "older… still works") | CONFIRMED | https://github.com/citizenfx/fivem-docs/blob/master/content/docs/scripting-reference/runtimes/lua/functions/RegisterNUICallback.md |
| 24 | `node_version '22'` opts into Node 22; the default is 16 | SKILL §12, manifest.md, runtime-facts §8/§13 | X | OUTDATED | Docs still say so, but current source routes all server JS to Node 22 and Node 16 was removed in 2026-02 (our versions.md / runtimes.md, source-verified). **Our skill is right** |
| 25 | "OneSync is on by default" | SKILL §7, runtime-facts §6 | X | OUTDATED | Forced on since commit 19fa3d5 (2026-08-16), per our versions.md |
| 26 | `lua54 'yes'` is a dead no-op; never emit it | SKILL §3 | Y | CONFIRMED | Same as ours |
| 27 | `use_experimental_fxv2_oal` breaks vector auto-unpack; `is_cfxv2` is injected only for files named `fxmanifest.lua` | manifest.md, runtime-facts §8 | P (OAL covered; `is_cfxv2` not) | CONFIRMED | runtime-facts cites LuaMetaDataLoader.cpp L266-269 (not re-fetched). Low practical value |
| 28 | Lockdown 4th mode: C++ `no_dummy` vs docs `full` | runtime-facts §6 | Y | CONFIRMED | ServerGameState_Scripting.cpp L574-617 (`no_dummy`). Ours already notes both |
| 29 | RCON: per-IP limiter 0.2/s burst 5, reset after successful auth; plaintext UDP; password compared with `!=` (not constant-time); runs as `system.console` | runtime-facts §14/§15 | P (rate + plaintext covered) | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/include/outofbandhandlers/RconOutOfBand.h |
| 30 | JS timers: `setTimeout/setInterval` clamp to ≥ 1 ms; `setImmediate` = `setTimeout(fn, 0)` (not a microtask); rAF callbacks run in reverse order; timers are tick-driven | runtime-facts §13 | P (runtimes.md: "overridden to run on game thread") | CONFIRMED | https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/v8/timer.js (L16-18, L156-162, L213) |
| 31 | JS export errors are swallowed and re-thrown generically ("An error occurred while calling export … see above"); `exports('n', fn)` in JS throws without exactly 2 args | runtime-facts §3 | P | CONFIRMED (main.js) | main.js L597-622 |
| 32 | `GetPlayerPing` = mean RTT; `GetPlayerPeerStatistics` gives loss/variance (updates every 10 s / 5 s) | runtime-facts §11 | Y (assets/natives CFX-SERVER.md) | CONFIRMED | ext/native-decls/GetPlayerPeerStatistics.md |
| 33 | `profiler resource <name> <frames>` records one resource | fivem-client SKILL | Y | CONFIRMED | Profiler.cpp L437, L551 |
| 34 | `resmon`/`profiler` refused in production mode without `+set moo 31337` | fivem-client SKILL | Y | CONFIRMED | ours debugging.md (+ Enhanced `sv_devMode`) |
| 35 | Net event / state bag / latent rate-limit table | SKILL §4, events.md | Y | CONFIRMED | identical to ours |
| 36 | `entityCreating` cancel removes the clone; `entityCreated` (QueueEvent2) can't be cancelled | events.md | Y | CONFIRMED | ours events-and-callbacks.md |
| 37 | `CreateVehicleServerSetter` over server `CreateVehicle`; server `CreatePed` is really server-side; RPC natives are fallible | SKILL §5/§7 | Y | CONFIRMED | ours onesync-entities.md |
| 38 | `fivem-devtools` uses `screenshot-basic` | fivem-client SKILL | — | OUTDATED | screenshot-basic is unmaintained; use itschip/screencapture (`provide 'screenshot-basic'`), per our versions.md |
| 39 | Per-player cooldown defaults: 250 ms interactions, 1 s money/items, 5 s DB/HTTP | SKILL §5 | P | UNVERIFIABLE (house policy, sensible) | — |
| 40 | Validation order: types → ranges → existence → cooldown → distance → permission → rules → act (cheapest first) | SKILL §5 | P (ours: who/allowed/where/what/how-often) | UNVERIFIABLE (design advice) | — |

**Verdict counts (40 rows):** CONFIRMED 28 · WRONG 3 (#2, #4, #15) · OUTDATED 3 (#24, #25, #38) · UNVERIFIABLE 6 (#18, #19, #22, #39, #40; #17 is confirmed only in part). New or partial items worth adding: 14.

### Recommended integrations (ready to paste)

**1. `references/runtimes.md`, Lua section (near the stdlib/`json` notes):**
```markdown
- **Client Lua has no `io` or `os`** (`os.time`, `os.date`, `os.clock` are `nil` client-side). The server has custom, filesystem-permission-aware `io`/`os`. Client timing: `GetGameTimer()` (ms, monotonic) or `GetCloudTimeAsInt()` (unix s). Shared code must not call `os.*`. Source: https://github.com/citizenfx/fivem/blob/master/code/components/citizen-scripting-lua/src/LuaScriptRuntime.cpp (`lualibs`, `#ifdef IS_FXSERVER`).
```

**2. `references/runtimes.md:150` (append to the `json` bullet):**
```markdown
  Vectors/quats encode natively: `json.encode(vector3(1,2,3))` → `{"x":1.0,"y":2.0,"z":3.0}`; with `json.encode(v, { vectorarray = true })` → `[1.0,2.0,3.0]`. `json.decode` returns plain tables. Rebuild with `vec3(t.x, t.y, t.z)`. Source: https://github.com/citizenfx/lua-rapidjson/blob/grit/src/lua_rapidjson.hpp (`JSON_ENCODER_ARRAY_VECTOR`).
```

**3. `references/runtimes.md:148` (replace the UNVERIFIED tail):**
```markdown
- Lua vectors/quats are msgpack **extension types 20/21/22/23** (vector2/3/4/quat). They survive Lua ↔ Lua (and C#) events and exports. The JS runtime registers no unpacker for them (only funcref 10/11), so a JS handler receives a raw msgpack ext object, not an array. Send `{ x, y, z }` tables across Lua ↔ JS. Sources: https://github.com/citizenfx/lua-cmsgpack/blob/grit/src/lua_cmsgpack.h · https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/v8/main.js
```

**4. `references/runtimes.md:144` (replace "JS alias: `exports.txAdmin` resolves to `monitor`."):**
```markdown
- `exports.txAdmin` is remapped to the `monitor` resource in **both** Lua (`scheduler.lua`) and JS (`main.js`).
```

**5. `references/runtimes.md` §7 or §JS (events), new bullet:**
```markdown
- JS `source` is reset to `null` at the end of **every** event dispatch (Lua restores the previous value). A synchronous `emit()` inside a handler therefore nulls the outer `source`: `const src = source;` must be the first line. Source: https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/v8/main.js (setEventFunction).
- JS timers are tick-driven: `setTimeout`/`setInterval` clamp to ≥ 1 ms; `setImmediate` is `setTimeout(fn, 0)` (not a microtask); `requestAnimationFrame` callbacks queued in one tick run in reverse order. Source: https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/v8/timer.js
```

**6. `references/debugging.md` (error table, near `attempt to call a nil value`):**
```markdown
- Why a typo'd native doesn't fail at load: `_G.__index` resolves natives lazily through `Citizen.LoadNative` and caches misses in `nilCache`, returning `nil` silently. The error appears only when that line is *called*, possibly in a rare branch. Run `python scripts/natives.py check <res> --strict` instead of relying on testing. Source: https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/natives_loader.lua
- `Setting values on Entity is not supported at this time.` means the code assigned `Entity(e).foo = x`. Use `Entity(e).state.foo = x` (same for `Player`). Source: scheduler.lua.
```

**7. `references/fxmanifest.md` (after the `fx_version`/`game` rows):**
```markdown
- The server **refuses to start** a resource with no recognised `fx_version` ("does not specify an `fx_version` in fxmanifest.lua") or one that declares both `game 'common'` and a specific game ("considered ill-formed"). Source: https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/ServerResources.cpp
```

**8. `references/onesync-entities.md` (state bag section, after strict mode):**
```markdown
- When a client writes to a bag the server doesn't know yet, only `entity:<netId>` bags are auto-created. Writes to unknown `player:`/`global` bags are silently dropped. Under the base `stateBag` limit, excess updates are dropped with at most one `sbag-update-dropped` warning per second per client (no kick). Source: https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/packethandlers/StateBagPacketHandler.cpp
- Client-side, resolving a netId the client doesn't hold (`NetworkGetEntityFromNetworkId`, `GetEntityFromStateBagName` in a change handler for a far-away entity) prints `GetNetworkObject: no object by ID <n>` each time. Guard with `NetworkDoesEntityExistWithNetworkId(netId)` (parse `entity:(%d+)` from the bag name) to avoid console spam. Source: https://github.com/citizenfx/fivem/blob/master/code/components/extra-natives-five/src/EntityDeletionNatives.cpp
```

**9. `references/security.md` (ACE section) and `convars-and-commands.md`:**
```markdown
- `add_ace` / `remove_ace` / `add_principal` / `remove_principal` refuse to modify the principal that is currently executing them ("Changing ones own access is not permitted."). A resource can't self-grant through its own `resource.<name>` principal. Put grants in server.cfg. Source: https://github.com/citizenfx/fivem/blob/master/code/client/citicore/se/Security.cpp
- `ExecuteCommand('set name value')` needs `add_ace resource.<res> command.set allow`. Prefer `SetConvar` / `SetConvarReplicated` (server natives). Source: https://docs.fivem.net/docs/scripting-reference/convars/
- RCON compares the password with a plain string compare (not constant-time), over plaintext UDP, limited per IP to 0.2/s burst 5, and the limit resets after a successful login. Firewall the port or leave `rcon_password` unset. Source: https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/include/outofbandhandlers/RconOutOfBand.h
```

**10. `references/performance.md` (near line 73):**
```markdown
- `Wait(0)` resumes on the next frame, so cost scales with FPS (60 fps ≈ 16.6 ms/tick, 180 fps ≈ 5.5 ms). Per-frame work must use `Wait(0)`: `Wait(5)`/`Wait(10)` silently skips frames for high-FPS players. Everything else should use adaptive waits (≥ 250–1000 ms when far). Source: https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/Citizen.Wait/
```

**11. `references/nui.md` (§callbacks table, row for `RegisterNUICallback`):**
```markdown
| `RegisterNUICallback(name, fn)` | Docs label it **Legacy API** (kept for backwards compatibility). Use the `RegisterNuiCallback` native in new code. |
```
Also add under the HUD/visual notes:
```markdown
- Blurring the game behind a panel: CSS `backdrop-filter` can't see the game frame (the game isn't part of the CEF page; one report says it renders black in-game, **UNVERIFIED**). Cfx exposes the game back buffer to WebGL instead: bind a 2D texture and set `TEXTURE_WRAP_T` to `CLAMP_TO_EDGE` → `MIRRORED_REPEAT` → `REPEAT`; nui-core then binds the game render target. Draw it to a canvas at a low rate (≤ 30 fps) and blur the canvas. Costly on Legacy's jitless CEF 103. Source: https://github.com/citizenfx/fivem/blob/master/code/components/nui-core/src/NUIInitialize.cpp (`glTexParameterfHook`).
```

**12. `references/events-and-callbacks.md` (resource lifecycle rows):**
```markdown
- Keep `onResourceStop` / `onClientResourceStop` cleanup **synchronous**: no `Wait`, `await` or callbacks. The script runtime is being torn down and code after a yield may never run (**UNVERIFIED** in source, but a widely observed rule). Clear NUI focus, delete tracked entities and blips, and stop loops directly.
```

### Structural ideas worth copying
1. **New lint rules for `scripts/audit.py`.** Our `audit.py` lacks these fxlint rules (docs/fxlint.md):
   - **S010:** bare `source` read after `Wait`/`Await` in a handler. Our `net-event-no-source` only checks presence.
   - **P004:** `CreateThread` inside an event handler or loop body (leaks a thread per event).
   - **P006:** `TriggerClientEvent(name, -1, …)` inside a loop or timer (broadcast storm).
   - **S005:** server `RegisterCommand(name, fn, false)` with an admin-ish name (kick/ban/give/tp/noclip/revive/setjob).
   - **S003:** a payload param named `playerId`/`target`/`serverId` used as a `GetPlayerPed`/`DropPlayer`/`TriggerClientEvent` target.
   - **C009:** `TriggerServerEvent` in a server file, `TriggerClientEvent` in a client file, or `source` in a client file.
   - **C011:** `Wait` inside an `*ResourceStop` handler.
   - **C012:** `exports.<res>` used without `dependency '<res>'`.
   - **C006 / S004:** cross-file check that a `TriggerServerEvent` name has a `RegisterNetEvent` (or the reverse: a net-registered name that nothing triggers).
   - **P005:** `GetGamePool`/`GetActivePlayers`/`json.encode`/`TriggerServerEvent` inside per-frame loops.
2. **Post-edit lint hook.** Run the linter after every Write/Edit on `.lua`/`.js` inside a resource; never block, inject only a summary. This is optional for a skill, but we could document it in tooling.md as a Claude Code hook recipe.
3. **In-game test checklist template** (SKILL §13). Eight concrete steps: happy path, 4 m away, no money, restart with UI open, spam for 10 s, 2nd client targeting player 1, disconnect mid-action, resmon far/near. Worth adding verbatim to SKILL.md step 8 or to audit-checklist.md.
4. **Error-message → cause mapping.** Covers `attempt to call a nil value` (non-existent native or export before start), `attempt to index a nil value` (unvalidated payload), `attempt to compare nil with number` (missing type check), `was not safe for net` and `Reliable network event overflow`. Ours mostly has these; check debugging.md for "attempt to compare nil with number".
5. **Client observability harness** (`fivem-devtools` + PowerShell agent). A dev-server-only resource that queues commands from a file, gates on identifier/ACE, accepts uploads only from the player's own endpoint, and returns screenshots, `profiler resource` captures, CitizenFX log tails and an fps/coords snapshot. This is a good *idea* for an optional `assets/templates/devtools/`. Base it on screencapture, not screenshot-basic, and keep it dev-only.
6. **"Never print server.cfg / never echo `sv_licenseKey`" agent rule** (fivem-server skill). Worth one line in our SKILL.md output conventions or security.md.
7. **Role-tiered agents:** a cheap model for native scouting (verified native list, no code), a strong model for implementation and review, and the main session re-verifying subagent reports. Optional; relevant only if we ship agents.
