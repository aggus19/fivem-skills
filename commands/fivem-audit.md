---
description: Audit a FiveM resource (or a whole server / resources folder) for backdoors, exploits, dupes, performance and 2026 compatibility
argument-hint: <path to resource, resources folder or server root>
---

Use the `fivem-development` skill. Target: $ARGUMENTS

- One resource: follow `references/audit-checklist.md` exactly.
- More than one resource (a server root or a `resources/` folder): follow `references/server-audit.md` exactly.

Run, from `${CLAUDE_PLUGIN_ROOT}/skills/fivem-development/scripts/`, in this order:
- `python project.py <target>` (servers only: stack, launch cfg, versions vs baseline, ensure vs folders, cfg, data_file, assets, git)
- `python logs.py <target>` (servers only, when console logs exist: runtime errors, failed starts, hitches, slow queries)
- `python manifest.py <target>`
- `python audit.py <target> --json`
- `python surface.py <target> --ledger ledger.md`
- `python natives.py check <own resources> --strict`

Then triage every Backdoor/RCE, SQL and Trust-boundary hit of any severity, review every ledger row with audit-checklist.md §6 (points 1-13) and the exploit classes in server-audit.md §8, and write the report in the template of the file you followed (verdict, coverage counts, findings with file:line, fixes, versions with file:line, what was not reviewed). Never sample the inventories; if rows are left unreviewed, mark the report PARTIAL. Do not modify files unless the user asks.
