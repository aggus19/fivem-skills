---
description: Audit a FiveM resource (or a whole resources folder) for backdoors, exploits, dupes, performance and 2026 compatibility
argument-hint: <path to resource or resources folder>
---

Use the `fivem-development` skill and follow `references/audit-checklist.md` exactly.

Target: $ARGUMENTS

Run, from `${CLAUDE_PLUGIN_ROOT}/skills/fivem-development/scripts/`:
- `python audit.py <target>`
- `python natives.py check <target> --strict`
- `python manifest.py <each resource>`

Then confirm every critical/high finding by reading the code, review every net event / callback / export with the five server-side checks, and write the report in the checklist's format (verdict, findings with file:line, fixes, what was not reviewed). Do not modify files unless the user asks.
