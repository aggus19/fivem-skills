# Console and txAdmin logs: what the messages mean and what to do

Use when the user pastes console output, says "it does not start / it lags / something broke after
a restart", or before an audit (runtime evidence beats static guesses). Start with the tool, then
read the matching row here.

```
python scripts/logs.py                 # from the server root or resources/: finds txData/<profile>/logs/fxserver.log
python scripts/logs.py <file> --last   # only the last server session
python scripts/logs.py --json          # for reports; secrets in examples are masked
```

Rules:
- **First error wins.** Fix the first error of each resource; later errors are often consequences (a nil framework object, a resource that never started).
- **Correlate, do not guess.** A hitch line says *that* the thread stalled, not *why*. Look at what started/ran just before it (resource start, query, restart) and measure ([hitch-diagnostics.md](hitch-diagnostics.md)).
- **Logs leak secrets.** Console logs often contain the license key, DB connection strings, webhooks or bot tokens (a `set` echoed by txAdmin, a startup print). Never ask users to paste raw logs publicly; `logs.py` masks them and reports `secret-in-log` so they can rotate.
- **Dev servers differ from production.** Escrow entitlements, endpoints, CDN and voice settings legitimately fail on a local copy; say so instead of reporting them as production bugs.

## Contents
1. Resource start
2. Script and module errors
3. Configuration (cfg, convars, commands)
4. Performance (hitches, database, assets)
5. Security advisories
6. Lifecycle (restarts, crashes)

## 1. Resource start
| Message | Meaning | Fix |
|---|---|---|
| `Couldn't find resource category [x].` | An `ensure [x]` names a category folder that does not exist (typo, renamed or moved folder). Nothing inside starts and there is no other error. | Fix the name in the cfg (`project.py` reports `ensure-missing-category` statically). |
| `Couldn't find resource x.` | `ensure/start x` with no such folder (or a duplicate name hides it). | Fix the cfg, or restore the folder. |
| `You lack the required entitlement to use x` + `Couldn't start resource x.` | Escrowed (Asset Escrow / Keymaster) resource not granted to this server's license key. Normal on dev servers that use another key. | Use the key the asset was bought for, transfer it in Keymaster, or test escrowed resources only on the licensed server. Never bypass escrow ([licensing-and-policy.md](licensing-and-policy.md)). |
| `Warning: x does not have a resource manifest (fxmanifest.lua)` | A non-resource folder (docs, tools, tests, deployment) lives inside `resources/`. Harmless but noisy, and it can expose files. | Move it out of `resources/`. |
| `Warning: could not load 'path'` (in `script:x:warning`) | The resource tried to load a file (often a locale or config JSON) that is not in the resource or not in `files {}`. | Add the file or the `files` entry; check `manifest.py`. |
| `Started resource x` repeated many times | Restart loops or a resource restarted by another (`ExecuteCommand('ensure ...')`). | Find who restarts it; avoid restarting dependencies at runtime. |

## 2. Script and module errors
| Message | Meaning | Fix |
|---|---|---|
| `SCRIPT ERROR: @res/file.lua:N: attempt to index a nil value (local 'Player')` | Runtime error at that line; the next `> fn (@res/file.lua:N)` lines are the stack. `nil` players/objects usually mean an offline/unknown source or a framework object fetched before it was ready. | Guard the lookup (`if not player then return end`), fetch the shared object after the framework started, check `source` capture. |
| `attempt to call a nil value (field 'x')` / `(global 'x')` | Calling an export/function that does not exist in the installed version (renamed API, wrong framework, resource not started). | Verify the installed API ([project-adaptation.md](project-adaptation.md)); never invent exports. |
| `attempt to compare number with nil` / `with string` | Client or DB value not converted/validated. | `tonumber` + validation at the boundary ([security.md](security.md)). |
| `Error loading script x in resource y: ...` / `Failed to load script x.` | The file did not load (syntax error, missing file, wrong side, JS exception at top level). | Read the message after the colon; run `manifest.py` on the resource. |
| `Cannot find module 'x'` (server JS) | `node_modules` missing or not shipped, or the package is not a dependency. | Build/install with the resource's lockfile (`bun install --frozen-lockfile` / `npm ci`), or bundle the dependency. |
| `Error parsing script` | Lua syntax error (or Lua 5.3-only syntax after the 5.4 move). | Fix the syntax; [runtimes.md](runtimes.md). |

## 3. Configuration
| Message | Meaning | Fix |
|---|---|---|
| ``Warning: `x` has been removed`` | The convar no longer exists (e.g. `sv_endpointPrivacy`, `sv_exposePlayerIdentifiersInHttpEndpoint`). | Delete the line ([convars-and-commands.md](convars-and-commands.md)). |
| `Warning: 'x' is an internal ConVar and cannot be changed.` | Set by the platform (e.g. `onesync_enableInfinity` now that OneSync is forced). | Delete the line. |
| `No such command x.` | A cfg/console line calls a command that does not exist: typo, a resource command used before the resource started, or a removed command. | Fix or remove it; move resource commands after their `ensure`. |
| `No such config file: x` | `exec` path not found. Paths are relative to the server data folder (FXServer working directory), not to the cfg that contains the `exec`. | Fix the path; `project.py` follows the exec chain and reports `exec-missing`. |
| `Argument count mismatch (passed 1, wanted 2)` | A cfg line has too few arguments, typically `set name` with no value or a value lost to an unquoted `;`. | Give the value or remove the line; quote values with `;` ([audit-checklist.md](audit-checklist.md) `cfg-unquoted-semicolon`). |
| `Force indirect listing is enabled, but no host override is set` | `sv_forceIndirectListing true` without `sv_listingHostOverride`. | Set both (proxy setups) or remove the first. |
| `This server does not have a license key specified` | `sv_licenseKey` missing for this launch (cfg not exec'd, wrong txAdmin cfgPath, secrets cfg missing). | Check the launch chain (`project.py` shows the txAdmin cfgPath and exec chain). |

## 4. Performance
| Message | Meaning | Fix |
|---|---|---|
| `server thread hitch warning: timer interval of N milliseconds` | The main server thread did not tick for N ms (Legacy warns above ~150 ms). Startup hitches of seconds while assets/DB load are common; hitches during play are not. | Correlate with the lines before it; profile ([hitch-diagnostics.md](hitch-diagnostics.md)). Usual causes: synchronous DB calls (`MySQL.Sync`, `.await` in hot paths), huge JSON encode/decode, file I/O, loops over all players. |
| `sync thread hitch warning` / `network thread hitch warning` | OneSync sync or network thread stalled: entity/population pressure, bandwidth, host CPU. | [onesync-entities.md](onesync-entities.md), [performance-server-scaling.md](performance-server-scaling.md). |
| `[db] res took Nms to execute a query!` (oxmysql) | Slow query from `res`. The threshold is `mysql_slow_query_warning`. | Find it with oxmysql's debug/UI, add indexes, select fewer columns, move it off hot paths ([database-optimization.md](database-optimization.md)). |
| `res executed a query with an oversized result set (N results)!` | A query returned N rows (often `SELECT ... FROM users` loading every account at startup). | Filter in SQL, paginate, load per player on join. |
| `Asset res/x.ytd uses N MiB of physical memory.` / `virtual memory` | Streamed asset over the warning threshold. "Oversized assets can and WILL lead to streaming issues" = models/textures that fail to load or flicker. | Resize textures (vehicles rarely need more than 1024-2048 px), remove unused LODs, split packs; [mapping-streaming.md](mapping-streaming.md), [vehicles-and-handling.md](vehicles-and-handling.md). Count per resource with `logs.py`; sizes on disk with `project.py`. |

## 5. Security advisories
| Message | Meaning | Fix |
|---|---|---|
| ox_lib `SECURITY WARNING` + `sv_stateBagStrictMode is currently DISABLED` | Clients can write replicated state bags. | Enable `sv_stateBagStrictMode` after testing the resources that write bags from the client ([convars-and-commands.md](convars-and-commands.md)); do not silence the advisory instead. |
| A license key, webhook, bot token or DB password visible in the console | The secret is now in every copy of the log (txAdmin, support tickets, screenshots). | Rotate it; move secrets to a non-replicated `set` in a private cfg; stop printing them. |

## 6. Lifecycle
| Message | Meaning | Fix |
|---|---|---|
| `FXServer Starting` (txAdmin banner) | One server start. Many starts in a short log = restart loop or frequent manual restarts. | Look at what precedes each start. |
| `Server shutting down. Kicking all players.` | Graceful shutdown/restart: frameworks should save players here (`txAdmin:events:serverShuttingDown`). | Verify the framework saves on this event, not only on a timer. |
| `Restarting server: Server process close detected.` | The process exited without a graceful shutdown (crash, kill, fatal error). | Read the lines before it; check crash dumps; check data saved since the last periodic save. |
