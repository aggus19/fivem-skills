# Group B analysis (2026-10-08)

## Summaries
- CodeCrafter98_fivem-agent-skills (2026-08-30): 43 tiny (~2 KB) skills in 00-orchestration..07-production; router (BUILD/FIX/AUDIT/REVIEW/EXPLAIN), inspector, per-domain Purpose/Workflow/Guardrails/Done-criteria. Quality: tidy process checklists, almost no concrete technical facts, no versions/sources. Mostly already covered by our SKILL.md routing + references.
- leminhhuy113_fivem-pro (2026-09-30): one SKILL + 13 refs (Iron Rules, CI/CD, testing checklist, troubleshooting FAQ, deployment). Decent beginner guidance; stale pins (checkout@v4, selene-action v1, sv_enforceGameBuild 3095, lua54 mandatory).
- melihbozkurt10_fivem-dev-plugin (2026-03-03): fetch-don't-memorize orchestrator + generic Lua/NUI/thread guides. Nothing new.
- b3sty191_b3sty-skill (2026-07-09): best of group. Rules for multi-resource boundaries, strict state bags, local vs networked props, native-bug memory with issue links. Huge native dumps skipped.
- Gdanycz_fivem-skills (2026-03-26): 3 DUI skills. Lifecycle natives correct; performance/AMD claims unsourced.

## Verdicts (candidates: 22)
CONFIRMED 8 | ALREADY IN SKILL 8 | OUTDATED 2 | WRONG 1 | UNVERIFIABLE 3
| # | Claim | Verdict | Source / note |
|---|---|---|---|
| 1 | GetEntityModel returns 0 in server entityCreating; do not reject on 0 | CONFIRMED (open reports) -> onesync-entities.md | github.com/citizenfx/fivem/issues/2924,4053,2944 |
| 2 | AddBlipForArea ignores SetBlipAsShortRange | CONFIRMED (open) -> natives-essentials.md | issues/3973 |
| 3 | Tag-triggered release workflow w/ softprops/action-gh-release | CONFIRMED v3.0.3 -> new ref | releases API |
| 4 | Zip = single folder named like resource; exclude node_modules/.env etc. | CONFIRMED (resource name = folder name, manifest docs) -> new ref | docs.fivem.net resource-manifest |
| 5 | dependency/GetResourceState instead of Wait races; export arg validation | CONFIRMED -> new ref | manifest docs |
| 6 | Boot-time config assert in onResourceStart; convar-gated debug | CONFIRMED (events docs) -> new ref | onResourceStart docs |
| 7 | Layered release gate / two-client test / permission-denied test | CONFIRMED as practice -> new ref | engineering guidance, no factual claim |
| 8 | Migrations idempotent, no "reversible" claim for lossy ones | CONFIRMED as practice -> new ref | - |
| 9 | CEF M103, IS_DUI_AVAILABLE before AddReplaceTexture, destroy on stop | ALREADY (nui.md) | |
| 10 | strict state bags, GetInvokingResource, routing-bucket lockdown, entity lifecycle, RegisterKeyMapping over polling, ox_lib locale fallback, stylua/selene | ALREADY | |
| 11 | selene-action@v1 / checkout@v4 | OUTDATED | selene-action last release 2021; checkout v7.0.1 |
| 12 | lua54 'yes' mandatory (leminh) | OUTDATED | Lua 5.3 removed 2025-06, lua54 optional (runtimes.md) |
| 13 | sv_enforceGameBuild 3095 | OUTDATED | baseline build 3889 |
| 14 | SetPedHeadBlendData + freemode mask crashes client (b3sty) | WRONG/misleading | issue #4037 closed: reporter used streamed custom head .ydd (fivem-greenscreener) |
| 15 | DUI: set about:blank before DestroyDui | UNVERIFIABLE | not in docs |
| 16 | NUI JS callbacks up to 9x slower than Lua; AMD OnAcceleratedPaint VRAM leaks delaying CEF upgrade | UNVERIFIABLE | no issue found |
| 17 | NUI cache-busting by query string | UNVERIFIABLE | |

## Wrong/outdated in the repos
lua54 'yes' as a rule (CodeCrafter says "do not use", leminh/b3sty say "must use"; truth: optional/no-op); old build 3095; stale GH action pins; head-blend mask crash attributed to the native; DUI AMD/9x claims unsourced; CodeCrafter lacks any versions.
