---
name: fivem-development
description: Builds, reviews, debugs, optimizes and secures FiveM (Cfx.re / GTA V) resources and servers — CfxLua 5.4, JS/TS and C# scripts, fxmanifest.lua, all natives, events and callbacks, OneSync entities and state bags, NUI (React/Vite), oxmysql and database tuning, ox_lib, ox_inventory, ox_target, ox_core, Qbox, QBCore, ESX Legacy, ND, vRP, server.cfg, convars, txAdmin, artifacts, GTA V Enhanced, vehicles/handling, MLO/streaming, RP systems design, anticheat and resource audits (backdoors, exploits, dupes). Use when the user mentions FiveM, FXServer, Cfx, CitizenFX, GTA RP/roleplay servers, a framework or ox resource above, a .lua resource with fxmanifest, or asks to create, convert, optimize, scale or audit a FiveM script or server — including requests in Spanish or Portuguese.
license: MIT
compatibility: Scripts need Python 3.8+ (standard library only); natives.py / build_natives_catalog.py need internet on first run. NUI template needs Node 22+.
metadata:
  author: fivem-skills
  version: "1.2.0"
  baseline-date: "2026-10-07"
---

# FiveM development

Baseline verified **2026-10-07** — details, sources and breaking-change timeline in [references/versions.md](references/versions.md):
FXServer Legacy Recommended **35245** / Latest 37150 (clients can't join older builds after **2026-10-15**) · game build **3889** · txAdmin 8.1.1 · CfxLua 5.4 only · Node 22 · OneSync forced on · CEF 103 (V8 JIT off) · **GTA V Enhanced early access** (Cfx Server 161) · ox_lib 3.40 · oxmysql 2.14.3 · ox_inventory 2.48 (≥ 2.47.6, no QBCore) · ox_target 1.18 · Qbox 1.24 · ESX 1.15.2 · QBCore 2026-05 refactor (repo `qbcore-fivem`).

## Non-negotiable rules

1. **Server is the authority.** Every net event, callback and export that changes state validates on the server: who (`local src = source` first), allowed (job/ACE/ownership), where (distance), what (types, ranges, whitelists, server-side prices), how often (cooldown). No yield/`Wait` between the check and the mutations; take/verify first, grant after, and refund or abort atomically on failure. → [security.md](references/security.md)
2. **Never invent natives, exports or framework APIs.** Verify natives with `python scripts/natives.py show <Name>` (or the catalogue in `assets/natives/`). If a framework function is not in the references, say so and link its docs instead of guessing.
3. **Detect the stack first.** Read `fxmanifest.lua`, `server.cfg`, `resources/` (or ask): framework, inventory, target, Legacy vs Enhanced, DB engine. Match it; don't mix frameworks. Portable code → bridge pattern ([framework-bridge.md](references/framework-bridge.md)).
4. **Use current APIs, never deprecated ones.** Check [use-vs-avoid.md](references/use-vs-avoid.md) whenever choosing an API, library or pattern. oxmysql placeholders only; ox_* from `overextended/*`; `RegisterNetEvent`; server-side entity creation; no secrets in client/shared files or `setr`.
5. **Performance budget.** Idle resource ≈ 0.00–0.02 ms in `resmon`; no `while true` without `Wait`; `Wait(0)` only while drawing/reading input; events/state bags/ox_lib points/zones/ox_target over polling. → [performance.md](references/performance.md)
6. **Be honest about versions and uncertainty.** Quote the baseline date when versions matter; keep **UNVERIFIED** markers from the references visible to the user instead of presenting them as fact.
7. **Respect the platform license.** No real-money gambling, loot boxes, currency sales, non-Tebex payments, escrow bypass or leaked resources. → [licensing-and-policy.md](references/licensing-and-policy.md)

## Choose the reference (read only what the task needs)

**Platform & server**
| Task | Read |
|---|---|
| Versions, deprecations, breaking changes | [versions.md](references/versions.md) |
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
| CfxLua syntax & extensions, threads, exports, JS/TS, C# | [runtimes.md](references/runtimes.md) |
| Events (all built-in), callbacks, commands, keybinds, rate limits | [events-and-callbacks.md](references/events-and-callbacks.md) |
| Natives guide, client vs server, identifiers, pitfalls | [natives.md](references/natives.md) |
| Most-used natives by task (verified signatures, control IDs, game references) | [natives-essentials.md](references/natives-essentials.md) |
| Any native at all (7,379, by namespace) | `assets/natives/README.md` → `assets/natives/<NAMESPACE>.md` |
| UI / HUD / menus in HTML (NUI), loading screens, DUI | [nui.md](references/nui.md) |
| Editor, LuaLS addon, lint, format, bundlers, CI | [tooling.md](references/tooling.md) |
| Errors, crashes, console commands, logs | [debugging.md](references/debugging.md) |

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
| Anticheat design (game events, heartbeats, honeypots, bans) | [anticheat.md](references/anticheat.md) |
| Auditing a resource / "is this safe?" / backdoors | [audit-checklist.md](references/audit-checklist.md) |
| Performance: measuring, budgets, standard values | [performance.md](references/performance.md) |
| Before/after optimization recipes | [performance-cookbook.md](references/performance-cookbook.md) |
| Large servers (200–2048 slots), hardware, network, streaming budgets | [performance-server-scaling.md](references/performance-server-scaling.md) |
| Monetisation, Tebex, escrow, Marketplace, licenses (PLA 2026-09-10) | [licensing-and-policy.md](references/licensing-and-policy.md) |

## Scripts (run them; read them only if they fail)

All in `scripts/`, Python 3.8+, standard library only; paths relative to this skill's directory.

| Command | Use |
|---|---|
| `python scripts/natives.py search <text> [--side client\|server] [--desc]` | Find natives (official DB incl. old names, cached in `~/.cache/fivem-skill`) |
| `python scripts/natives.py show <NameOrHash>` | Exact signature(s), side, hash, docs link |
| `python scripts/natives.py check <path> [--strict]` | Every native used exists and is on the right side (`--strict` flags unknown/hallucinated calls) |
| `python scripts/build_natives_catalog.py [--out DIR] [--refresh]` | Regenerate `assets/natives/` (full catalogue) |
| `python scripts/manifest.py <resource>` | fxmanifest vs files on disk, NUI coverage, side leaks, obsolete keys |
| `python scripts/audit.py <path> [--min high] [--json]` | Heuristic security/performance/compat scan incl. backdoor signatures and `.cfg` checks (exit 1 on high/critical) |
| `python scripts/rcon.py [--host H] [--port P] <command...>` | One RCON command over UDP (password from env `FIVEM_RCON_PASSWORD`, never argv; localhost unless `--allow-remote`) |
| `python scripts/server_info.py [host:port] [--resource NAME] [--getinfo] [--json]` | Summarise `/info.json`, `/players.json`, `/dynamic.json`; check a resource is started |
| `python scripts/scaffold.py <name> [--out DIR] [--nui]` | New resource: ox_lib + oxmysql + auto-detecting bridge (Qbox/ESX/QBCore/standalone) + optional React/Vite NUI |

## Workflows

### Create a resource
```
- [ ] 1. Confirm stack (framework, inventory, target, Legacy/Enhanced) and feature scope
- [ ] 2. python scripts/scaffold.py <name> --out <resources dir> [--nui]
- [ ] 3. Design data + events first (rp-systems-design.md for RP features)
- [ ] 4. Implement: shared config (public), server config (prices/limits), server logic with the 5 checks, client UX via ox_lib
- [ ] 5. python scripts/natives.py check <resource> --strict
- [ ] 6. python scripts/manifest.py <resource>
- [ ] 7. python scripts/audit.py <resource>  → fix high/critical, justify the rest
- [ ] 8. Tell the user: install steps, ensure order, convars, SQL, NUI build, how to test in game
```
Templates: `assets/templates/resource-lua/` (bridge + secure shop example), `assets/templates/nui-react-vite/` (React 19, Vite 8, TS, `chrome103`). Configs: `assets/configs/` (LuaLS, selene, StyLua, server.cfg, CI).

### Modify or fix existing code
1. Read the resource (manifest first); identify framework, versions and the side of each file.
2. Reproduce from the user's error (first error wins — [debugging.md](references/debugging.md)).
3. Minimal change in the existing style; don't migrate frameworks unless asked.
4. Re-run `natives.py check`, `manifest.py`, `audit.py` on the touched resource.

### Audit a resource
Follow [audit-checklist.md](references/audit-checklist.md): `audit.py`, `natives.py check --strict`, `manifest.py`, then confirm each finding in the code. Report file:line, severity, fix. Never call obfuscated or escrowed code "safe". If a backdoor is found, list credentials to rotate.

### Convert between frameworks
Map calls through the bridge contract; use the target framework file for exact APIs (QBCore → Qbox: [framework-qbox.md §16](references/framework-qbox.md)). Replace esx_menu / qb-menu / qb-input with ox_lib; qb-target with ox_target where available; never pair ox_inventory with QBCore.

### Optimize / scale
Measure first (`resmon`, `profiler`), then [performance.md](references/performance.md) → [performance-cookbook.md](references/performance-cookbook.md); DB → [database-optimization.md](references/database-optimization.md); big servers → [performance-server-scaling.md](references/performance-server-scaling.md). Report before/after numbers.

## Output conventions
- Lua: 4-space indent, `local` everything, single quotes, events `resource:side:action`, `Config` (shared) vs `ServerConfig` (server-only).
- State the file and side (client/server/shared) for every snippet, plus required `fxmanifest.lua` / `server.cfg` / SQL changes.
- Prefer ox_lib UI unless the server uses something else; locales via ox_lib `locale()` + `locales/*.json`.
- Answer in the user's language; code identifiers in English.
