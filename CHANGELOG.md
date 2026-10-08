# Changelog

## 1.3.0 — 2026-10-08 — deterministic whole-server audits

Motivation: two different models audited the same 35-resource ESX server with this skill and reported different findings. Both sampled handlers by hand; one never checked `data_file` paths, one called oxmysql 2.12.3 "up to date". The skill had the knowledge (baseline, authority checks) but no tool that enumerated the work, no coverage contract and no stop rule.

- New `scripts/surface.py`: every client-reachable server entry point (net events in both forms, `lib.callback`, ESX/QBCore callbacks, custom `*.Register*Event/Callback` wrappers, commands, exports, `SetHttpHandler`, JS `onNet`), the sinks each reaches (money, items, vehicles, jobs/permissions, SQL writes, coords/buckets, spawns, `ExecuteCommand`, broadcasts, state bags) through same-resource helpers and aliases, and fixed-meaning risk tags (`credit-before-guard`, `client-position`, `client-target`, `non-integer-amount`, `no-balance-check`, `unchecked-removal`, `yield-before-mutation`, `not-eq-precedence`, `fanout`, `no-rate-limit`, ...). Writes a Markdown coverage ledger; stable IDs; deterministic `--shard K/N` for parallel reviewers; flags escrowed (`FXAP`/`.fxap`) and obfuscated files as opaque.
- New `scripts/project.py`: cfg `exec` chain, conflicting/removed convars, `ensure` targets vs folders (categories expanded), duplicate and never-started resources, installed versions vs `assets/baseline.json` with `file:line`, `data_file` existence, streamed files > 16 MiB and duplicated names, git state, nested `.git`/`node_modules`, scripts referencing missing files. Never prints convar values.
- New `assets/baseline.json` (machine-readable baseline with min-safe versions) and `references/server-audit.md` (contract, phases, sharding, economy exploit classes, severity rubric, known false positives, report template with coverage table). SKILL.md gains an "Audit a server" workflow and routing; agent and `/fivem-audit` command follow it.
- Fix: `glob_match` treated `[category]` folder names as glob character classes, so any manifest path under a bracket folder resolved wrong (e.g. 126/126 instead of 118/126 missing `data_file` paths). `manifest.py` now checks `data_file` paths and accepts a resources folder.
- `audit.py`: `lua-not-eq-precedence` (`not x == y`) and `client-reported-position` (client sends its own distance/coords).
- Consistency pass over references: one canonical value for `sv_entityLockdown` (relaxed by default), `sv_filterRequestControl`, `sv_stateBagStrictMode` date, `sv_protectServerEntities`, net-event limits and ESX ensure order; ESX `round = true` fractional-amount warning; `math.tointeger` validation (rejects `math.huge`); orphan `ox-inventory-target.md` removed; audit checklist triages every Backdoor/SQL/Trust-boundary hit regardless of severity, never blocks on unknown provenance, and treats resmon targets as illustrative.
- Tests: new `tests/fixtures/server_project` and `tests/test_server_audit.py` (108 tests pass, 32 optional skipped). Eval 19 covers a whole-server audit. On the real server that motivated this release, `surface.py` lists 512 entry points (185 to review) in ~4 s, byte-identical across runs, and tags every exploit either model found.

## Unreleased — project adaptation, security and hitch diagnosis (2026-10-08)

- Reworked the staged plan in `docs/roadmap.md` around general project adaptation, operation security, client/server/NUI performance, databases/hitches, real integration and evidence maintenance. Runtime/benchmark stages remain explicitly pending.
- Added `project-adaptation.md`, `security-validation.md` and `hitch-diagnostics.md` (53 references total). The skill preserves installed runtimes, custom forks, UI, package managers and data owners; security follows all entry points to effects and includes an adversarial acceptance matrix.
- `scaffold.py` defaults to dependency-free Lua. The previous ox stack/shop is explicit `--profile ox-shop`; optional NUI works with either. Updated plugin command and installation guidance; verified overwrite targets reject symlinks/junction redirection and non-directory targets before deletion.
- Removed the ledger-plus-export atomicity implication, unsafe retry wording and unbounded webhook alert queue from security guidance. Optional shop checks server-owned routing bucket/entity existence and bounds names, with added Lua logic cases for unauthorized contexts and stale identity.
- Rechecked primary DB vendors: corrected MariaDB 11.8 **Community** maintenance to 2028-06-04; distinguished support channels, MySQL expression defaults and MariaDB 12.3 snapshot-isolation changes. Replaced slot-based DB presets and routine durability relaxation with workload, compatibility and recovery requirements.
- Hitch guidance distinguishes Legacy timer intervals (main/network >150 ms; sync >100 ms in pinned source) from execution/query duration. Removed blanket tick/save/restart prescriptions and added correlated profiling, queue/host/DB hypotheses and before/after acceptance criteria.
- Expanded evaluation scenarios from 12 to 18. These are specifications, not executed agent evaluations. No FXServer, real database integration or measured FiveM speedup is claimed.
- Validation: **94/94 Python tests passed** on Windows/Python 3.12, including 30 Lua 5.4 logic tests and frozen-lock Bun builds for both profiles; **5/5 Bun fetch tests passed**. Python 3.8.10 portable passed 62 standard-library tests with 32 optional Lua/build tests explicitly skipped. Both generated profiles passed native/manifest checks; audit reported zero high/critical, with the shop's two grant/refund review candidates inspected. Internal Markdown targets resolve; SKILL.md is 157 lines. These results cover local tooling and mocked logic, not deployed framework/DB/CEF behavior.

## Unreleased — reliability pass (2026-10-08)

- Manifest-aware Lua native sides and audit routing; literal manifest parsing without executing Lua; resolved glob/download exposure checks. Invalid/empty input fails explicitly. Audit now scans individual files and shipped dist/build/stream code; display filters no longer hide failure status.
- New offline regressions plus optional executed Lua 5.4 failure/interleaving tests and a real Bun NUI build. Repository CI covers Python 3.8/3.12, Lua logic and Bun. CI workflow is configured; remote CI and FXServer integration have not been run.
- Replaced lossy money write-behind and unchecked crafting examples. Added a bounded versioned progress-write queue and checked custom-account transfer body; these are tested building blocks, not complete economy services.
- Shop compensation checks definitive/unknown results and failed refunds. **Generated purchases now default to disabled** until the project wires durable operation/recovery and verifies adapter/session contracts. Removed the production-ready claim.
- NUI includes Vite types, Bun lockfile, readiness handshake, callback deadlines and error handling. Corrected event-side/identity/anticheat-log-mode contradictions, unsupported timing claims and Python 3.8 catalog generation.
- Added design-and-validation.md: ownership, session identity, interleaving, failure contracts, evidence levels and reproducible performance experiments. No FXServer benchmark improvement is claimed; the upstream version baseline remains 2026-10-07.
- The bundled skill-creator quick validator rejects the existing `compatibility` field; the current Agent Skills specification and repository AGENTS.md allow it. Preserved the field and validate the repository's allowed fields/lengths in structural tests (https://agentskills.io/specification).
- Local validation: Windows, Python 3.12 + test-only lupa 2.8 (`lua54`), **81/81 tests executed and passed**, including the frozen-lock Bun build; **5/5 Bun fetch tests passed** (Bun 1.4.2). Python 3.8.10 portable: 54 standard-library tests passed, 27 optional Lua/build cases explicitly skipped; catalog regeneration also produced 7,379 natives. Generated-resource native/manifest checks passed; audit had no high/critical findings. Its five medium candidates were reviewed: the intended grant/refund calls, production minification, and React DOM's HTML machinery (the app does not supply raw HTML). No remote CI, independent agent evals, FXServer/MySQL integration or performance benchmarks were executed.

## 1.2.0 — 2026-10-08
Community-skill review: about 40 public GitHub repos (FiveM skills, rules, plugins, MCP servers) were cloned and read; ~400 of their claims were checked against primary sources. Only CONFIRMED items were merged; wrong or outdated claims were recorded as "common wrong advice" in `use-vs-avoid.md`. Full evidence trail: `docs/community-analysis/`.

- New references: `ai-dev-workflow-and-mcp.md` (RCON, server HTTP endpoints, txAdmin API, MCP comparison and risks), `resource-architecture-and-release.md`. References: 47 → 49.
- New scripts: `rcon.py`, `server_info.py` (stdlib only, offline tests).
- `audit.py`: +24 rules (73 in total): newer backdoor IOC families, dropper-name false-positive fix, split `RegisterNetEvent`/`AddEventHandler` detection, `.cfg` semicolon splitting, HTML scan.
- Corrections: `sv_endpointPrivacy` is removed (2026-07-08); "remove before add" replaced by "no yield between check and mutations"; Enhanced detection via `gamename`, `kvdb-migrator` exists; oxmysql batch transactions commit on 0 affected rows; oxmysql cannot use MariaDB ed25519 auth; Lua nesting limit for event payloads; `;` splitting in server.cfg.
- Tests: 14 → 35 passing.

## 1.1.0 — 2026-10-07
Deep research expansion (12 parallel research passes over primary sources: GitHub source/releases, npm, docs.fivem.net, forum.cfx.re, official framework docs).

- References: 25 → 47 files (~11,900 lines). New: ox-lib-ui/core/world/utilities/js, database-optimization, ox-inventory, ox-target, ox-core, ox-resources-misc, qbox-ecosystem, esx-ecosystem, ecosystem-resources, natives-essentials (699 verified natives), performance-cookbook, performance-server-scaling, convars-and-commands, txadmin, anticheat, use-vs-avoid, vehicles-and-handling, rp-systems-design. All other references rewritten from source.
- Full native catalogue: `assets/natives/` (7,379 natives, 47 namespace files) + `scripts/build_natives_catalog.py`.
- natives.py: indexes DB aliases (old names), runtime helpers no longer flagged, GetConvar/LoadResourceFile side-checked.
- audit.py: new backdoor signatures, 10 code rules (JS decoders, raw network, manifest writes, cross-resource writes, ACE from code, SQL template literals, exposed webhooks, client replicated state bags, NUI XSS) and `.cfg` checks; scans JSX/TSX/Vue/Svelte.
- Template: QBCore adapter uses qb-inventory exports (ox_inventory has no QBCore support since 2.42); `nui_callback_strict_mode` for NUI resources.
- Configs: StyLua `syntax = "CfxLua"`, LuaLS addon setup, CI actions bumped, cfx.yml globals.
- versions.md: databases, ecosystem, asset tools, deprecations and a 2024–2026 breaking-change timeline.

## 1.0.0 — 2026-10-07
Initial release. Baseline verified against primary sources on 2026-10-07.

- Skill `fivem-development` (SKILL.md + 23 references).
- Platform: FXServer Recommended 35245 / Latest 37150, game build 3889, txAdmin 8.1.1, Lua 5.3 removal, Node 22, OneSync forced, CEF M103 (JIT off), GTA V Enhanced early access (Cfx Server 161), PLA 2026-09-10.
- Libraries: ox_lib 3.40.0, oxmysql 2.14.3, ox_inventory 2.48.0, ox_target 1.18.1, ox_core 1.5.14 (back under `overextended/*`; CommunityOx archived), Qbox 1.24.0, ESX 1.15.2, QBCore (moved to `qbcore-fivem`).
- Scripts: `natives.py` (official native DB, dual client/server names, Lua name codegen parity), `manifest.py`, `audit.py`, `scaffold.py`.
- Templates: Lua resource with framework bridge (Qbox/ESX/QBCore/standalone) and secure shop example; NUI React 19 + Vite 8 + TS 7 (`chrome103`).
- Claude Code plugin: marketplace, `/fivem-new`, `/fivem-audit`, `/fivem-native`, `fivem-auditor` agent.
- Offline unit tests and evals.
