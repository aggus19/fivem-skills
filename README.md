# FiveM Skills — `fivem-development`

**English** · [Español](README.es.md)

`fivem-development` is an open [Agent Skill](https://agentskills.io/specification) that gives AI coding agents current, source-checked knowledge of FiveM (Cfx.re / GTA V) development, plus standard-library Python tools that inspect a real server the same way every time. It is meant to work on any FiveM server — ESX, QBCore, Qbox, ox_core, ND, vRP/Creative or standalone, any folder layout, Windows or Linux, with or without txAdmin — and with any agent that can read a `SKILL.md` or project instructions. Version facts are a baseline verified against primary sources on **2026-10-07** ([`references/versions.md`](skills/fivem-development/references/versions.md)).

## What it does

- **Create** resources adapted to the installed stack (Lua, JS/TS, C#; optional React/Vite NUI), with server-side validation by default.
- **Modify and convert** existing resources while preserving the framework, data owners, UI and package manager already in use.
- **Debug** script errors, load failures, escrow entitlement errors and hitches from the server console log.
- **Optimize** client, server, NUI and database work with measured before/after comparisons instead of blanket rules.
- **Audit** a single resource or a whole server: backdoors, SQL injection, client-trust exploits, item/money dupes, outdated dependencies, broken `ensure`/`data_file` entries and oversized assets, with an explicit coverage contract ([`references/server-audit.md`](skills/fivem-development/references/server-audit.md)).

Generated Lua is shipped **without explanatory comments**: `scaffold.py` strips them from templates, because client scripts are downloaded by players and should not explain server logic. Pass `--keep-comments` when you want the annotated version for learning.

## Quick start from your server

The scripts need only Python 3.8+. Run them from your server's `resources/` folder (or the server root) with no arguments; they find the server root, the launch cfg and the logs themselves. Below, `<skill>` is the path where you placed `skills/fivem-development`.

```bash
cd /path/to/your/server/resources

python <skill>/scripts/project.py      # inventory of the whole server
python <skill>/scripts/logs.py         # problems from the console log, grouped and counted
python <skill>/scripts/surface.py --ledger ledger.md   # every client-reachable server entry point
python <skill>/scripts/audit.py        # heuristic security / performance / compatibility scan
python <skill>/scripts/manifest.py     # validates every fxmanifest.lua below the current folder
```

- **`project.py`** — detected stack (framework, inventory, target, DB driver, voice, phone…), the cfg `exec` chain from the launch cfg (txAdmin `cfgPath` when a txAdmin profile points at this server, else `server.cfg`), removed or conflicting convars, `ensure` targets vs actual folders (categories expanded), duplicate and never-started resources, installed versions vs [`assets/baseline.json`](skills/fivem-development/assets/baseline.json) with `file:line`, `data_file` paths, streamed files over 16 MiB, and git state. It never prints convar values.
- **`logs.py`** — finds `txData/<profile>/logs/fxserver.log` (or `logs/*.log` next to the server) by itself and streams it, so large logs are fine. Groups script errors (resource, `file:line`, first stack frame), load failures, resources that failed to start (including escrow entitlement), thread hitches, slow queries, oversized streamed assets, removed or unknown convars, startup security advisories and crashes. Values that look like keys, tokens or webhooks are masked.
- **`surface.py`** — lists every client-reachable server entry point (net events, `lib.callback`, ESX and QBCore/Qbox callbacks and commands, custom register wrappers, exports, `SetHttpHandler`, JS `onNet`, vRP/Creative tunnels) with the sinks each one reaches (money, items, vehicles, jobs, SQL writes, coords/buckets, spawns, `ExecuteCommand`…) across ESX, QBCore/Qbox, ND, ox_core and vRP/Creative, plus fixed-meaning risk tags. `--ledger` writes a Markdown coverage ledger with stable IDs; `--shard K/N` splits it for parallel reviewers.
- **`audit.py`** and **`manifest.py`** — both default to the current folder. `audit.py` reports candidates to confirm by reading the code; `manifest.py` checks scripts, `files`, `ui_page`, dependencies and `data_file` paths against the disk.

Then ask your agent:

> Audit my server following `references/server-audit.md`.

The agent uses these outputs as the inventory, reviews every ledger row and reports coverage counts instead of sampling.

Other scripts: `natives.py` (look up and verify natives, detect invented or wrong-side natives), `build_natives_catalog.py` (regenerate the native catalogue), `scaffold.py` (create a resource; `--profile ox-shop`, `--nui`), `rcon.py` (send one RCON command to a development server; password only from `FIVEM_RCON_PASSWORD`) and `server_info.py` (summarise a running server from its public HTTP endpoints).

```bash
python <skill>/scripts/natives.py update                 # download the official native DB once (cached)
python <skill>/scripts/natives.py show GetEntityCoords
python <skill>/scripts/natives.py check ./my_resource --strict
python <skill>/scripts/scaffold.py my_resource --out "./[custom]"
python <skill>/scripts/scaffold.py my_shop --profile ox-shop --nui --out "./[custom]"
```

## Use it with your agent

The skill is the folder [`skills/fivem-development/`](skills/fivem-development/). Keep `SKILL.md`, `references/`, `scripts/` and `assets/` together; the scripts resolve their data relative to their own location. The skill is not an FXServer resource: do not `ensure` it.

### Claude Code

As a plugin (adds the `/fivem-new`, `/fivem-audit` and `/fivem-native` commands and the read-only `fivem-auditor` subagent):

```bash
/plugin marketplace add aggus19/fivem-skills
/plugin install fivem-development@fivem-skills
```

From a local clone: `/plugin marketplace add ./path/to/fivem-skills`, then the same install command.

Skill only: copy `skills/fivem-development/` to `~/.claude/skills/fivem-development/` (all projects) or `.claude/skills/fivem-development/` inside a project.

### Agents that support the Agent Skills format

Any agent that loads skills from a `SKILL.md` with `name`/`description` frontmatter can use the folder as is: copy `skills/fivem-development/` into that agent's skills directory (for example a project-level `.agents/skills/fivem-development/`). Skills directories differ between agents; check your agent's documentation for the right location.

### Agents without skill support

For Codex, Cursor, Gemini CLI or any other agent that reads project instructions but not skills, point it to [`AGENTS.md`](AGENTS.md) and [`skills/fivem-development/SKILL.md`](skills/fivem-development/SKILL.md) as project instructions (for example by referencing them from your existing instruction file, without replacing your own rules). `SKILL.md` routes the agent to the reference it needs, so it reads only what the task requires. Check your agent's documentation for how it loads instruction files.

## Requirements

- **Python 3.8+, standard library only.** No `pip install` is needed to run the scripts.
- **Works offline**, except `natives.py update` / `build_natives_catalog.py`, which download the official native database from Cfx.re (cached in `~/.cache/fivem-skill` or `$FIVEM_SKILL_CACHE`). A full native catalogue (7,379 natives) also ships in `assets/natives/`.
- **Bun** (1.4.2 or compatible Node/npm) only to build the optional NUI template.

## What is included

| Area | Contents |
|---|---|
| `SKILL.md` | Non-negotiable rules (server authority, never invent natives or APIs, adapt to the installed stack, measured performance, evidence levels, platform license), reference routing table and workflows (create, modify, audit a resource, audit a server, convert, optimize). |
| `references/` | Platform (versions, server.cfg, convars, txAdmin, OneSync, GTA V Enhanced, console logs), scripting (fxmanifest, runtimes, events, natives, NUI, tooling, debugging), overextended libraries (ox_lib, oxmysql, ox_inventory, ox_target, ox_core), frameworks (Qbox, ESX Legacy, QBCore, ND/vRP, multi-framework bridge), gameplay and RP systems, security, anticheat, audit checklists, performance and scaling, licensing. |
| `assets/` | Native catalogue by namespace, `baseline.json`, templates (dependency-free Lua, optional `ox-shop` profile with a framework bridge, React 19 + Vite + TypeScript NUI targeting CEF 103), configs (LuaLS, selene, StyLua, `server.cfg.example`, GitHub Actions workflow). |
| `scripts/` | The tools described above, plus the shared `resource_files.py` helper. Manifests are parsed statically and never executed. |
| Claude Code plugin | `commands/`, `agents/`, `.claude-plugin/`. |
| `evals/`, `tests/` | Evaluation scenarios (specifications, not executed agent runs) and offline tests with fixtures. |

## What is verified

```bash
python -m unittest discover -s tests -v
```

On Windows with Python 3.12 the suite currently runs **119 tests: 87 pass and 32 are skipped**. The skipped ones are optional Lua 5.4 logic tests (need `lupa`) and real NUI builds (need Bun); enable them with `FIVEM_REQUIRE_LUA_TESTS=1` and `FIVEM_TEST_NUI_BUILD=1`. Skipped tests are not counted as passed. The GitHub Actions workflow runs Python 3.8 and 3.12 and the Lua/NUI jobs separately.

These tests cover the scripts, templates and mocked logic. They are not FXServer integration tests, database integration tests or performance benchmarks, and no runtime speedup is claimed. See [`design-and-validation.md`](skills/fivem-development/references/design-and-validation.md) for evidence levels.

## Privacy and safety

- Scripts are **read-only by default**. Only `scaffold.py` (creates a resource where you ask), `surface.py --ledger` (writes the ledger file you name) and the native tools (`natives.py update` writes its cache; `build_natives_catalog.py` regenerates `assets/natives/`) write files.
- Scripts **never print secrets**: `project.py` does not print convar values, `logs.py` masks values that look like keys, tokens or webhooks, and `rcon.py` reads its password only from an environment variable.
- **No telemetry.** The only network access is the native database download and, if you run them, `rcon.py` / `server_info.py` against a server you choose (`rcon.py` refuses non-local hosts unless `--allow-remote`).

## Responsible use

The audit features are for **defensive security**: reviewing servers and resources you own or are authorised to review. The skill follows the Cfx.re Creator Platform License Agreement: no escrow bypass, no leaked resources, no real-money gambling or loot boxes, no currency sales and no payments outside Tebex. See [`references/licensing-and-policy.md`](skills/fivem-development/references/licensing-and-policy.md) and the official terms at https://fivem.net/terms.

## Contributing

- Version facts age. Re-verify following "How to re-verify" in [`references/versions.md`](skills/fivem-development/references/versions.md), update the baseline date (`metadata.baseline-date` in `SKILL.md`), and keep `assets/baseline.json` and `versions.md` in sync.
- Every new detection in `audit.py`, `surface.py`, `project.py` or `logs.py` needs a fixture under `tests/fixtures/` and a test.
- Scripts stay standard-library Python 3.8+; `SKILL.md` stays under 500 lines with references one level deep (see [`AGENTS.md`](AGENTS.md)).
- Run `python -m unittest discover -s tests -v` and record changes in [`CHANGELOG.md`](CHANGELOG.md).

## Main sources

- Cfx.re docs: https://docs.fivem.net/docs/ · natives: https://docs.fivem.net/natives/ · server download: https://docs.fivem.net/docs/server-download/
- overextended: https://overextended.dev/docs · Qbox: https://docs.qbox.re · ESX: https://docs.esx-framework.org/en · QBCore: https://qbcore.org/docs
- txAdmin: https://github.com/citizenfx/txAdmin/releases · PLA: https://fivem.net/terms
- Agent Skills: https://agentskills.io/specification · Claude Code plugins: https://code.claude.com/docs/en/plugins-reference

## License

[MIT](LICENSE). FiveM, Cfx.re and GTA V are trademarks of their respective owners. This project is not affiliated with Rockstar Games, Take-Two or Cfx.re.
