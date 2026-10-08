# Changelog

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
