# Adapt the skill to the actual project

Use on first contact with a server, when choosing dependencies, or when the requested
feature crosses resources. This is a discovery procedure, not a preferred server recipe.

## Establish only the context the task needs

1. Locate the project instructions and the actual resources directory. A txAdmin
   profile, its data directory and the FXServer executable directory can differ.
   Resolve skill helpers relative to this skill's `SKILL.md`; do not assume the
   host project contains `skills/fivem-development/scripts/`.
2. Start with the affected `fxmanifest.lua`: client/server/shared files, runtime,
   dependencies, `provide` aliases, NUI downloads and runtime-loaded modules. A
   directory named `qb-core` alone does not prove which API implementation is active.
3. Inspect the relevant `server.cfg` and its `exec` includes, without printing
   credentials. Distinguish **present on disk**, **configured to start**, and
   **observed running**. A category `ensure [custom]` or dynamic config needs
   inspection of its contents; a manifest version can be stale on a fork.
4. Identify owners of the touched data: character session, accounts, inventory,
   vehicles, permissions and persistence. Follow callers and consumers across
   resources; a framework bridge can conceal different return/yield contracts.
5. Record the evidence needed for the task: relevant paths, installed version or
   commit, known overrides, and unresolved facts. A new blip does not require
   database discovery; a transfer or hitch investigation usually does.

| Context | Evidence to inspect | Do not infer |
|---|---|---|
| Framework / inventory / target | Manifest, dependency order, installed exports and callers | Resource name or upstream latest equals installed behavior |
| Lua / JS / TS / C# | Actual source, build files, manifest and bundled runtime | Lua templates are mandatory for another language |
| NUI | Existing app, CEF target, package manifest and lockfile | Bun used to build the UI replaces FXServer's server JS runtime |
| Database | Driver and connection options; authorized read-only `SELECT VERSION(), @@version_comment;` | An oxmysql version identifies the DB engine or its performance |
| Server edition / artifact | Runtime startup/version evidence and configured game build | GTA game build, FXServer artifact and framework version are interchangeable |
| Hosting / load | OS, shared processes, real concurrent workload, relevant metrics | Slots alone determine CPU, RAM, pool size or a safe save interval |

When a required contract remains unknown, inspect local source and matching primary
documentation. Ask a narrow question only when the missing fact changes correctness;
continue independent work. Never fabricate a compatible adapter for a custom/escrowed API.

## Choose an implementation that fits

- **Existing resource:** preserve its language, framework, UI and persistence owner.
  Add dependencies only when the feature benefits and compatibility is established.
- **New Lua resource:** the optional scaffold defaults to `--profile minimal`, with
  no framework, DB or idle loop. Add only the components the feature uses.
- **Economy example:** `--profile ox-shop` is an explicit integration exercise for
  a compatible ox stack, not the default architecture. Its bridge is an example;
  verify installed adapters and durable recovery before enabling purchases.
- **JS/C# project:** use the installed project structure and runtime reference.
  The lexical Lua native checker does not validate JS/C# calls; use the language's
  build checks, inspect native contracts, and report this coverage limit.
- **Unknown or mixed framework:** trace the real data owner and compatibility
  layer. Do not install a second inventory or framework to fit a skill example.
- **UI or localization:** preserve the project's UI and translation tooling.
  Standalone features do not need ox_lib solely to display text or hold a locale.

## Route the user's request

| Request | Required reasoning | Relevant references |
|---|---|---|
| Create/fix a small feature | Side, native/API contracts, lifecycle, affected trust boundary | Manifest, runtimes, feature-specific file |
| Money, items, ownership, permissions | Entry points to sinks; concurrency, retries and recovery | `security.md`, `security-validation.md`, `design-and-validation.md` |
| Optimize scripts/UI | Reproduce workload; client/server/NUI cost and behavior | `performance.md`, `performance-cookbook.md`, `nui.md` |
| Hitch / lag / slow save | Identify delayed subsystem; correlate traces and queues | `hitch-diagnostics.md`, then DB or scaling references |
| Choose or upgrade DB | Supported release, installed SQL compatibility, restore/migration test | `database-optimization.md`, `versions.md` |
| Audit an entire server | Tool-generated inventory (`project.py`, `surface.py` ledger), every row reviewed, opaque code limits | `server-audit.md`, `audit-checklist.md`, `security-validation.md` |

Apply security checks to the affected operation. A cosmetic change is not a request
to migrate the server, install a new engine, or conduct an unrelated full audit.
For a broad audit, report uninspected areas rather than describing the whole server
as safe because its scanned files produced no high-severity findings.

## Completion evidence

Report the requested behavior, relevant integration/configuration changes, checks
actually executed, and unresolved runtime dependencies. For performance changes,
include the workload and before/after evidence or explicitly say **unmeasured**.
For security work, include the entry points and mutation paths reviewed plus the
negative tests run. Preserve the distinction between a recommendation and a tested
property of the user's server.
