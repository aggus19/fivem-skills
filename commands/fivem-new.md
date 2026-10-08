---
description: Create a FiveM resource adapted to the installed stack, with optional NUI, and implement the requested feature securely
argument-hint: <resource_name> [--nui] <what it should do>
---

Use the `fivem-development` skill.

Request: $ARGUMENTS

1. Detect the user's stack (framework, inventory, target, Legacy/Enhanced) from the workspace (`server.cfg`, `resources/`); ask only if it cannot be determined.
2. Match the project's language and layout. For a new Lua resource, optionally run `python "${CLAUDE_PLUGIN_ROOT}/skills/fivem-development/scripts/scaffold.py" <name> --out <resources dir> [--nui]`. This defaults to dependency-free Lua; select `--profile ox-shop` only for a compatible, explicitly needed integration example.
3. Implement the feature following the skill's "Create a resource" workflow (server authority, operation contracts, installed UI and only necessary dependencies).
4. Run `natives.py check --strict`, `manifest.py` and `audit.py` on the new resource and fix what they report.
5. Finish with install steps (`ensure` order, convars, SQL, NUI build) and how to test in game.
