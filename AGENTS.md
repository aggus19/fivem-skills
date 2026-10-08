# AGENTS.md

This repository packages the `fivem-development` Agent Skill.

- For any FiveM / Cfx.re / GTA V roleplay server task, load `skills/fivem-development/SKILL.md` and follow it; read only the references it routes you to.
- Verify natives with `python skills/fivem-development/scripts/natives.py show <Name>` before using one you are unsure about. Never invent natives or framework APIs.
- Before finishing work on a resource, run `natives.py check --strict`, `manifest.py` and `audit.py` from `skills/fivem-development/scripts/` on it.
- Version facts in the skill are a baseline dated 2026-10-07 (`references/versions.md`).

Working on the skill itself:
- Keep `SKILL.md` under 500 lines; references one level deep; frontmatter limited to Agent Skills spec fields (`name`, `description`, `license`, `compatibility`, `metadata`).
- Scripts must stay standard-library Python 3.8+.
- Run `python -m unittest discover -s tests -v` after changes.
