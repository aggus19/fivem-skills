# AGENTS.md

This repository packages the `fivem-development` Agent Skill.

- For any FiveM / Cfx.re / GTA V roleplay server task, load `skills/fivem-development/SKILL.md` and follow it; read only the references it routes you to.
- Verify natives with `python skills/fivem-development/scripts/natives.py show <Name>` before using one you are unsure about. Never invent natives or framework APIs.
- Before finishing work on a resource, run `natives.py check --strict`, `manifest.py`, `audit.py` and `surface.py` from `skills/fivem-development/scripts/` on it.
- First contact with any server: run `project.py` and `logs.py` from its `resources/` folder (no arguments needed) and read the references the detected stack points to.
- Code you write into a user's project has no explanatory comments (client files are downloaded, server files leak in dumps); explain changes in the reply/PR instead. Never print secrets.
- To audit a whole server, follow `skills/fivem-development/references/server-audit.md`: inventories come from `project.py`, `audit.py --json` and `surface.py --ledger` and are never sampled; the report states coverage counts.
- Version facts in the skill are a baseline dated 2026-10-07 (`references/versions.md`, machine-readable copy `assets/baseline.json`; keep both in sync).

Working on the skill itself:
- Keep `SKILL.md` under 500 lines; references one level deep; frontmatter limited to Agent Skills spec fields (`name`, `description`, `license`, `compatibility`, `metadata`).
- Scripts must stay standard-library Python 3.8+.
- Run `python -m unittest discover -s tests -v` after changes.
