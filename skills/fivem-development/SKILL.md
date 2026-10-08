---
name: fivem-development
description: Builds, reviews, debugs, optimizes and secures FiveM (Cfx.re / GTA V) resources and whole servers — CfxLua 5.4, JS/TS and C#, fxmanifest.lua, natives, events and callbacks, OneSync and state bags, NUI, oxmysql and databases, ox_lib/ox_inventory/ox_target/ox_core, Qbox, QBCore, ESX, ND, vRP/Creative and custom frameworks, server.cfg, convars, txAdmin, console log analysis, GTA V Enhanced, vehicles, MLO/streaming, RP systems, anticheat and audits (backdoors, exploits, dupes, endpoint coverage). Use when the user mentions FiveM, FXServer, Cfx, CitizenFX, GTA RP/roleplay servers, a framework or ox resource above, a resource with fxmanifest.lua, server console errors, or asks to create, convert, optimize, scale, debug or audit a FiveM script or server, in any language.
license: MIT
compatibility: Scripts need Python 3.8+ (standard library only); native lookup needs internet on first run. NUI builds with Bun 1.4.2 or compatible Node/npm; see its package.json.
metadata:
  author: fivem-skills
  version: "1.2.0"
  baseline-date: "2026-10-07"
---

# FiveM development

Baseline verified **2026-10-07** — details, sources and breaking-change timeline in [references/versions.md](references/versions.md):
FXServer Legacy Recommended **35245** / Latest 37150 (clients can't join older builds after **2026-10-15**) · game build **3889** · txAdmin 8.1.1 · CfxLua 5.4 only · Node 22 · OneSync forced on · CEF 103 (V8 JIT off) · **GTA V Enhanced early access** (Cfx Server 161) · ox_lib 3.40 · oxmysql 2.14.3 · ox_inventory 2.48 (≥ 2.47.6, no QBCore) · ox_target 1.18 · Qbox 1.24 · ESX 1.15.2 · QBCore 2026-05 refactor (repo `qbcore-fivem`).

## Non-negotiable rules

1. **Server is the authority.** Validate who (`local src = source` first), permission/ownership, location/bucket, bounded input/server prices and rate. Identify the data owner and possible yields, including inside exports; check mutation and compensation results. Unknown outcomes require reconciliation, not blind retries. → [security.md](references/security.md), [design-and-validation.md](references/design-and-validation.md)
2. **Never invent natives, exports or framework APIs.** Verify natives with `python scripts/natives.py show <Name>` (or the catalogue). For an API absent from the references, inspect installed source and matching official docs; state unresolved contracts instead of guessing. Distinguish application-defined interfaces from framework exports.
3. **Adapt to the project and request.** Read the relevant manifests, configuration and installed APIs; distinguish present, configured and running resources. Preserve language, framework, data owners and package manager; add only needed dependencies. Resolve helpers relative to this skill's location. → [project-adaptation.md](references/project-adaptation.md); portable code → [framework-bridge.md](references/framework-bridge.md).
4. **Choose APIs compatible with the installed stack.** Use [use-vs-avoid.md](references/use-vs-avoid.md) and matching source/docs; preserve an older supported API when compatibility requires it and explain the constraint. Do not silently migrate frameworks. SQL placeholders; server-owned entity lifecycle; no secrets in any client-downloadable file or `setr`.
5. **Measure performance with a correctness budget.** Establish workload and before/after measurements, including shared-library, NUI, network and DB costs. Numerical targets are contextual; a rounded `0.00 ms` is not zero cost. Bound loops and use per-frame work only for actual per-frame requirements. → [performance.md](references/performance.md), [design-and-validation.md](references/design-and-validation.md)
6. **Separate evidence levels.** Distinguish documented, source-reviewed, logic-tested, integration-tested and measured claims. Quote baseline date when versions matter; keep **UNVERIFIED** markers visible. Never turn missing runtime tests into a production-readiness or speedup claim.
7. **Respect the platform license.** No real-money gambling, loot boxes, currency sales, non-Tebex payments, escrow bypass or leaked resources. → [licensing-and-policy.md](references/licensing-and-policy.md)

## Choose the reference (read only what the task needs)

**Platform & server**
| Task | Read |
|---|---|
| Versions, deprecations, breaking changes | [versions.md](references/versions.md) |
| First contact, custom/mixed stack, dependency choice, scope and installed-skill paths | [project-adaptation.md](references/project-adaptation.md) |
| server.cfg, install (Windows/Linux), updates, ACE, artifacts | [server-ops.md](references/server-ops.md) |
| Any convar or server command (defaults, recommended values, removed ones) | [convars-and-commands.md](references/convars-and-commands.md) |
| txAdmin (recipes, events, env vars, permissions, restarts, whitelist) | [txadmin.md](references/txadmin.md) |
| Entities, ownership, state bags, routing buckets, entity lockdown, population | [onesync-entities.md](references/onesync-entities.md) |
| GTA V Enhanced / Cfx Server, migration | [gta5-enhanced.md](references/gta5-enhanced.md) |
| Testing from an AI agent: RCON, server HTTP endpoints, txAdmin API, community MCP servers (comparison + risks) | [ai-dev-workflow-and-mcp.md](references/ai-dev-workflow-and-mcp.md) |

**Scripting**
| Task | Read |
|---|---|
| New resource / manifest directives / data_file types | [fxmanifest.md](references/fxmanifest.md) |
| Resource architecture, packaging, release workflow, pre-release gate | [resource-architecture-and-release.md](references/resource-architecture-and-release.md) |
| Stateful/async feature design, identity, failure handling, evidence and performance experiments | [design-and-validation.md](references/design-and-validation.md) |
| CfxLua syntax & extensions, threads, exports, JS/TS, C# | [runtimes.md](references/runtimes.md) |
| Events (all built-in), callbacks, commands, keybinds, rate limits | [events-and-callbacks.md](references/events-and-callbacks.md) |
| Natives guide, client vs server, identifiers, pitfalls | [natives.md](references/natives.md) |
| Most-used natives by task (verified signatures, control IDs, game references) | [natives-essentials.md](references/natives-essentials.md) |
| Any native at all (7,379, by namespace) | `assets/natives/README.md` → `assets/natives/<NAMESPACE>.md` |
| UI / HUD / menus in HTML (NUI), loading screens, DUI | [nui.md](references/nui.md) |
| Editor, LuaLS addon, lint, format, bundlers, CI | [tooling.md](references/tooling.md) |
| Errors, crashes, console commands, logs | [debugging.md](references/debugging.md) |
| Reading console / txAdmin logs (script errors, load failures, escrow entitlement, hitches, slow queries, oversized assets, removed convars) | [console-logs.md](references/console-logs.md) |

**Libraries (overextended)**
| Task | Read |
|---|---|
| ox_lib overview, install, convars, changelog | [ox-lib.md](references/ox-lib.md) |
| ox_lib UI: notify, textUI, progress, skillCheck, context, menu, input, alert, radial | [ox-lib-ui.md](references/ox-lib-ui.md) |
| ox_lib core: cache, callbacks, commands, keybinds, ACE, hooks, entity replication | [ox-lib-core.md](references/ox-lib-core.md) |
| ox_lib world: points, zones, closest/nearby, raycast, streaming, markers, DUI, scaleform, vehicle props | [ox-lib-world.md](references/ox-lib-world.md) |
| ox_lib utilities: require, locale, print, logger, class, collections, table/math/string, timers, cron | [ox-lib-utilities.md](references/ox-lib-utilities.md) |
| ox_lib in JS/TS | [ox-lib-js.md](references/ox-lib-js.md) |
| oxmysql API, convars, transactions, migration from mysql-async | [database-oxmysql.md](references/database-oxmysql.md) |
| Schema design, indexes, query optimization, my.cnf tuning, backups, MariaDB/MySQL choice | [database-optimization.md](references/database-optimization.md) |
| ox_inventory (items, exports, hooks, stashes, shops, crafting, convars) | [ox-inventory.md](references/ox-inventory.md) |
| ox_target | [ox-target.md](references/ox-target.md) |
| ox_core | [ox-core.md](references/ox-core.md) |
| ox_doorlock, ox_fuel, other ox resources | [ox-resources-misc.md](references/ox-resources-misc.md) |

**Frameworks & ecosystem**
| Task | Read |
|---|---|
| Qbox (qbx_core exports, events, PlayerData, lib, bridge, migration from QBCore §16) | [framework-qbox.md](references/framework-qbox.md) |
| Qbox resources (qbx_* ecosystem) | [qbox-ecosystem.md](references/qbox-ecosystem.md) |
| ESX Legacy (ESX.*, xPlayer, esx_lib, callbacks, events, config) | [framework-esx.md](references/framework-esx.md) |
| ESX core resources (society, billing, multichar, identity, skin...) | [esx-ecosystem.md](references/esx-ecosystem.md) |
| QBCore (functions, Player object, events, qb-inventory/target/menu) | [framework-qbcore.md](references/framework-qbcore.md) |
| ND_Core, vRP / Creative / vRPEX, standalone, stack choice | [framework-others.md](references/framework-others.md) |
| Multi-framework resource, converting between frameworks | [framework-bridge.md](references/framework-bridge.md) + framework files |
| Community resources by category (voice, phone, appearance, garages, housing, dispatch, MDT, HUD, admin, anticheat) with use/avoid | [ecosystem-resources.md](references/ecosystem-resources.md) |

**Gameplay & content**
| Task | Read |
|---|---|
| Gameplay recipes (vehicles spawn, NPCs, anims, props, blips, interactions) | [gameplay-patterns.md](references/gameplay-patterns.md) |
| Designing RP systems (jobs, garages, keys, housing, banking, shops, crafting, drugs, dispatch, death, status) | [rp-systems-design.md](references/rp-systems-design.md) |
| Vehicles, add-on cars, handling.meta, mods, data files | [vehicles-and-handling.md](references/vehicles-and-handling.md) |
| MLOs, YMAP/YTYP, IPLs, clothing, streaming budgets, asset tools | [mapping-streaming.md](references/mapping-streaming.md) |

**Quality, security & policy**
| Task | Read |
|---|---|
| What to use vs avoid (APIs, libs, patterns, resources) | [use-vs-avoid.md](references/use-vs-avoid.md) |
| Secure coding, exploit classes, server.cfg hardening | [security.md](references/security.md) |
| Trigger/callback/export/command security, money/items, replay, failure and concurrency tests | [security-validation.md](references/security-validation.md) |
| Anticheat design (game events, heartbeats, honeypots, bans) | [anticheat.md](references/anticheat.md) |
| Auditing a resource / "is this safe?" / backdoors | [audit-checklist.md](references/audit-checklist.md) |
| Auditing a whole server or resources folder: inventory, versions vs baseline, ensure/data_file checks, endpoint coverage ledger, economy exploit classes, report | [server-audit.md](references/server-audit.md) |
| Performance: measuring, budgets, standard values | [performance.md](references/performance.md) |
| Hitch warnings, slow actions, DB versus script/host latency, diagnostic experiments | [hitch-diagnostics.md](references/hitch-diagnostics.md) |
| Before/after optimization recipes | [performance-cookbook.md](references/performance-cookbook.md) |
| Large servers (200–2048 slots), hardware, network, streaming budgets | [performance-server-scaling.md](references/performance-server-scaling.md) |
| Monetisation, Tebex, escrow, Marketplace, licenses (PLA 2026-09-10) | [licensing-and-policy.md](references/licensing-and-policy.md) |

## Scripts (run them; read them only if they fail)

All in `scripts/`, Python 3.8+, standard library only; paths relative to this skill's directory.

| Command | Use |
|---|---|
| `python scripts/natives.py search <text> [--side client\|server] [--desc]` | Find natives (official DB incl. old names, cached in `~/.cache/fivem-skill`) |
| `python scripts/natives.py show <NameOrHash>` | Exact signature(s), side, hash, docs link |
| `python scripts/natives.py check <path> [--strict]` | Lexical Lua native names and manifest-declared sides; filename fallback/unknown side reported. No signature/control-flow/runtime proof |
| `python scripts/build_natives_catalog.py [--out DIR] [--refresh]` | Regenerate `assets/natives/` (full catalogue) |
| `python scripts/manifest.py <resource\|resources dir>` | Literal manifest vs resolved files/globs, `data_file` paths, NUI downloads and server-file exposure; a folder checks every resource below it; dynamic manifests explicitly unsupported |
| `python scripts/audit.py <path> [--min high] [--json]` | Heuristic code/config/build-output scan; exit 1 on any high/critical regardless of display filter. Dependencies excluded; findings need review |
| `python scripts/project.py [path] [--cfg FILE] [--json] [--section S]` | Whole-server facts from the server root, `resources/` or any folder inside it (default: current dir): installed stack and the reference to read, launch cfg (txAdmin `cfgPath`) and exec chain, convar conflicts, ensure vs folders, versions vs `assets/baseline.json` (file:line), data_file and asset checks, git state; exit 1 on high |
| `python scripts/logs.py [path\|log ...] [--last] [--json]` | Finds and summarises FXServer/txAdmin console logs: script errors with stack frame, load failures, resources that did not start (escrow entitlement, missing category), hitches, slow queries, oversized assets, config warnings, leaked secrets (masked) |
| `python scripts/surface.py <path> [--ledger FILE] [--shard K/N] [--json]` | Every client-reachable server entry point, the sinks it reaches (money, items, SQL, buckets, spawns...) and fixed risk tags; writes the coverage ledger; stable IDs |
| `python scripts/rcon.py [--host H] [--port P] <command...>` | One RCON command over UDP (password from env `FIVEM_RCON_PASSWORD`, never argv; localhost unless `--allow-remote`) |
| `python scripts/server_info.py [host:port] [--resource NAME] [--getinfo] [--json]` | Summarise `/info.json`, `/players.json`, `/dynamic.json`; check a resource is started |
| `python scripts/scaffold.py <name> [--out DIR] [--nui] [--profile minimal\|ox-shop]` | Default: dependency-free Lua; optional NUI. Explicit ox-shop profile: ox stack + bridge/economy integration example |

## Workflows

### First contact with a server (any framework, any layout)
Works from the user's `resources/` folder (or any folder inside it); every script defaults to the current directory.
```
- [ ] 1. python scripts/project.py      -> stack (framework/inventory/target/DB/voice...), launch cfg, versions, ensure/data_file/asset facts
- [ ] 2. python scripts/logs.py         -> what actually fails at runtime (first error per resource wins)
- [ ] 3. Read the references the stack row points to; adapt to what is installed (project-adaptation.md), never to a template
- [ ] 4. Continue with the matching workflow below; for "analyse/audit my server" use Audit a server
```

### Create a resource
```
- [ ] 1. Establish feature scope and relevant installed stack (project-adaptation.md)
- [ ] 2. Match the project's runtime/layout; optional Lua scaffold: python scripts/scaffold.py <name> --out <resources dir> [--nui] (minimal by default)
- [ ] 3. Design ownership, identity, events, interleaving, persistence and failures (design-and-validation.md; RP details in rp-systems-design.md)
- [ ] 4. Implement with the installed APIs/UI; keep private config server-only. For sensitive operations, map all entry points to effects and apply security-validation.md
- [ ] 5. python scripts/natives.py check <resource> --strict
- [ ] 6. python scripts/manifest.py <resource>
- [ ] 7. python scripts/audit.py <resource>  → fix high/critical, justify the rest
- [ ] 8. Build NUI with the existing package manager/lockfile; test relevant failure paths; run or explicitly mark pending FXServer acceptance
- [ ] 9. Report install/ensure/convars/SQL, actual checks, evidence and runtime limitations
```
Templates: `assets/templates/resource-minimal/` (dependency-free default), `resource-lua/` (explicit ox-shop profile; purchases disabled until durable recovery/contracts are wired), `nui-react-vite/` (optional React/Vite/TS, `chrome103`, Bun lockfile). These are choices, not a required server stack. Tested logic building blocks: `assets/examples/` (versioned progress writes and custom-account transfer body). Configs: `assets/configs/`.

### Modify or fix existing code
1. Read the resource (manifest first); identify installed API contracts and the side of each file. Follow project-adaptation.md for unknown/custom stacks.
2. Reproduce from the user's error (first error wins — [debugging.md](references/debugging.md)).
3. Minimal change in the existing style; don't migrate frameworks unless asked.
4. Re-run `natives.py check`, `manifest.py`, `audit.py` on the touched resource.

### Audit a resource
Follow [audit-checklist.md](references/audit-checklist.md) §1 (its order is canonical): `manifest.py`, `audit.py --json`, `surface.py --ledger`, `natives.py check --strict`; confirm or dismiss every Backdoor/SQL/Trust-boundary hit and review every ledger row. For protected state, test relevant cases in security-validation.md. Report file:line, severity, fix and coverage. Never call obfuscated or escrowed code "safe". If a backdoor is found, list credentials to rotate.

### Audit a server (more than one resource)
Follow [server-audit.md](references/server-audit.md). Enumerate with tools, never by sampling:
```
- [ ] 1. Scope: path, git HEAD, uncommitted changes; provenance unknown = record and continue
- [ ] 2. python scripts/project.py <server>                 -> versions/ensure/cfg/data_file/assets/repo facts (cite file:line)
- [ ] 3. python scripts/audit.py <resources> --json          -> triage every Backdoor/SQL/Trust-boundary hit (server-audit.md §4, §10)
- [ ] 4. python scripts/surface.py <resources> --ledger L.md  -> review EVERY row (audit-checklist §6 1-13 + server-audit §8); --shard K/N for parallel reviewers
- [ ] 5. python scripts/manifest.py <resources>; natives.py check on the owner's own resources
- [ ] 6. Static performance review (unmeasured unless profiled)
- [ ] 7. Report with the server-audit.md §11 template: coverage counts, no TODO rows, or mark PARTIAL
```

### Convert between frameworks
Map calls through the actual owner/bridge contract; verify installed target APIs (QBCore → Qbox: [framework-qbox.md §16](references/framework-qbox.md)). Preserve compatible UI/target dependencies unless the requested migration requires their replacement. Verify inventory support; the baseline ox_inventory does not support QBCore.

### Optimize / scale
For hitches or unclear latency, start with [hitch-diagnostics.md](references/hitch-diagnostics.md). Measure the affected subsystem, then [performance.md](references/performance.md) → [performance-cookbook.md](references/performance-cookbook.md); DB → [database-optimization.md](references/database-optimization.md); scale → [performance-server-scaling.md](references/performance-server-scaling.md). Re-verify vendor releases/support when recommending a DB today; versions or copied tuning presets do not guarantee no hitches. Report reproducible before/after numbers or **unmeasured**, using the experiment contract in design-and-validation.md.

## Output conventions
- Lua: 4-space indent, `local` everything, single quotes, events `resource:side:action`, `Config` (shared) vs `ServerConfig` (server-only).
- State the file and side (client/server/shared) for every snippet, plus required `fxmanifest.lua` / `server.cfg` / SQL changes.
- Follow the project's language, UI and localization conventions. Use ox_lib when selected and compatible; do not introduce it solely to fit a template.
- Answer in the user's language; code identifiers in English.
- **Code written into the user's project carries no explanatory comments** (Lua, JS, cfg): client files are downloaded by every player and server files leak in dumps, so never describe validation, anticheat, economy or permission logic in comments. Explain the change in the reply, PR or commit message instead. Keep the project's existing comments untouched. `scaffold.py` strips template comments (`--keep-comments` only for learning).
- Never print or copy secrets (license keys, DB strings, webhooks, tokens) into answers, reports, code or logs; cite `file:line` and say what to rotate.
