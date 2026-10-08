---
description: Look up FiveM/GTA V natives (exact signature, client/server side, hash, docs link)
argument-hint: <native name, hash or search text>
---

Query: $ARGUMENTS

If it looks like an exact name or hash, run `python "${CLAUDE_PLUGIN_ROOT}/skills/fivem-development/scripts/natives.py" show <query>`; otherwise run `... natives.py search <query>` (add `--desc` if nothing matches by name). Answer with the Lua signature, side, return values (pointer params are extra return values in Lua), the docs link and a short usage example. Never invent a native that the database does not contain.
