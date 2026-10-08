# Resource audit procedure (security · performance · compatibility)

Baseline: FXServer Legacy 35245, txAdmin 8.1.1, oxmysql 2.14.3, ox_inventory 2.48, ox_lib 3.40; backdoor indicators from public advisories up to 2026-07 — verified 2026-10-07. Defensive use only: these are **detection signatures**, not payloads.

Use for: reviewing third-party/leaked resources before installing, code review of the user's own resources, "is this script safe?", "my server got hacked", "why is my server lagging?".

## Contents
1. Workflow
2. Provenance and supply-chain review
3. Known backdoor families: indicators (Cipher / Blum / Warden / GFX)
4. Triage commands (read-only)
5. Incident response (server already infected)
6. Server authority review
7. Performance review
8. Compatibility review (2026 platform)
9. `audit.py` rule reference
10. Report format
11. Sources

## 1. Workflow
```
- [ ] 1. Provenance: where did it come from? (section 2) — leaks = stop here, treat as malware
- [ ] 2. Inventory: python scripts/manifest.py <resource>   (sides, files, unexpected server_scripts)
- [ ] 3. Automated: python scripts/audit.py <path> --min low  (also scans *.cfg and dropper file names)
- [ ] 4. Natives:   python scripts/natives.py check <path> --strict
- [ ] 5. Manual review of every critical/high finding (read the code, confirm or dismiss)
- [ ] 6. Manual review of every RegisterNetEvent / callback / server export (section 6)
- [ ] 7. Performance review (section 7) and compatibility review (section 8)
- [ ] 8. Report (section 10) with file:line evidence, severity and fix
```
Scripts produce candidates, not verdicts. Never report an unconfirmed finding; never call obfuscated, minified-without-source or escrowed code "safe" — say "not reviewable".

## 2. Provenance and supply-chain review
Ask first:
- Source: official GitHub release / Cfx Portal (Keymaster) / Tebex purchase from the author = OK. Leak forums, "free premium", "cracked/escrow-bypassed", Discord zip from a stranger, "server packs" = **assume compromised** (this is how Cipher/Blum spread).
- Is the resource escrowed when the author claims it should be? A "paid" resource with readable Lua but extra obfuscated files is a red flag.
- Does a UI/map/vehicle/clothing resource have `server_scripts`? Why?
- Does `fxmanifest.lua` list files that don't match the resource purpose (`yarn_builder.js`, `babel_config.js`, `version.lua`, `sv_*.js` in a Lua-only resource)?

Code red flags (any one = treat as compromised until proven otherwise):
- HTTP response passed to `load` / `loadstring` / `assert(load(...))` / `eval` / `new Function` / `vm`.
- Hex/byte-escaped strings, `string.char` chains, `String.fromCharCode` + XOR loops, `\u00xx` blobs, giant single-line files, `_G['\x..']` indexing, "Luraph Obfuscator" headers.
- Server JS using `child_process`, `vm`, raw `require('https')`/`net`, `setTimeout` with long delays before network calls, writing files outside the resource.
- `SaveResourceFile` / `fs.writeFile` targeting other resources, `fxmanifest.lua` or `server.cfg` (self-replication).
- `ExecuteCommand` with remote input; `add_ace`/`add_principal` from code.
- Outbound HTTP to unknown domains; webhooks receiving `sv_licenseKey`, `rcon_password`, `mysql_connection_string`, txAdmin tokens or player identifiers.
- `GlobalState` keys with odd names used as "already infected" markers.

## 3. Known backdoor families: indicators
Community-sourced (Cfx forum advisory 2026-07-21 + an independent analysis repo); attribution between families is a single researcher's claim. New variants change names — patterns in §2 matter more than exact strings.

| Indicator type | Values |
|---|---|
| Panel / brand strings | `cipher-panel`, `ciphercorp`, `blum-panel`, `warden-panel`, `gfxpanel` |
| C2 domains (block at egress) | `blum-panel.me`, `warden-panel.me`, `9ns1.com`, `fivems.lt`, `jking.lt`, `gfxpanel.org`, `kutingplays.com`, `2ns3.net`, `giithub.net` (+ ~20 fallbacks in the analysis repo's `iocs/domains.txt`) |
| Infection markers | `GlobalState.miauss` / thread name `miaus`/`miauss` (dropper), `GlobalState.ggWP` (replicator), strings `bertjj`, URL paths ending `JJ` |
| Dropper file names | `yarn_builder.js`, `webpack_builder.js`, `babel_config.js` (note: underscore, not `babel.config.js`) |
| txAdmin tampering | modified `monitor/resource/sv_main.lua`, `sv_resources.lua`, `cl_playerlist.lua`; strings `helpEmptyCode`, `onServerResourceFail`, `RESOURCE_EXCLUDE`, `isExcludedResource` |
| Rogue txAdmin admin | account `JohnsUrUncle` in `txData/admins.json` |
| Persistence | extra `server_scripts` lines in many `fxmanifest.lua`; `server.cfg` line injected at a random position; on Windows: scheduled tasks, services, Run keys, Defender exclusions |
| Behaviour | ~20 s after start fetches JS from C2 and runs it with `eval`; steals browser logins / Discord tokens / files; can run OS commands; hides resources from the txAdmin UI |

`audit.py` covers these under rule `known-backdoor` (strings + dropper file names), `js-charcode-decoder`, `write-manifest`, `rce-*`, `node-child-process`.

## 4. Triage commands (read-only)
Linux (from the server root):
```bash
grep -rnIE "cipher-panel|blum-panel|warden-panel|gfxpanel|miauss|ggWP|bertjj|helpEmptyCode|JohnsUrUncle" resources/ txData/ 2>/dev/null
grep -rnIE "assert\(load\(|loadstring\(|new Function\(|require\(['\"]child_process|fromCharCode\([^)]*\^" resources/ --include=*.lua --include=*.js
find resources/ -name "yarn_builder.js" -o -name "webpack_builder.js" -o -name "babel_config.js"
find resources/ -type f \( -name "*.lua" -o -name "*.js" \) -newer server.cfg -mtime -14   # recently changed code
git -C resources status --short                                                           # if under Git
```
Windows PowerShell:
```powershell
Get-ChildItem resources -Recurse -Include *.lua,*.js | Select-String -Pattern 'cipher-panel|blum-panel|warden-panel|miauss|ggWP|helpEmptyCode|assert\(load\(' | Select-Object Path, LineNumber
Get-ChildItem resources -Recurse -Include yarn_builder.js,webpack_builder.js,babel_config.js
```
Then: `python scripts/audit.py resources --min high` and check `txData/admins.json` for unknown accounts. From any trusted server script: `print(GlobalState.miauss, GlobalState.ggWP)` should print `nil nil`.

## 5. Incident response (server already infected)
1. **Stop the server** (a live loader keeps pulling instructions). Snapshot disk/logs for evidence if you need them.
2. **Treat the host as compromised**, not just the resource: loaders spread into other resources and txAdmin; second stages may have stolen browser/Discord credentials on that machine.
3. **Rebuild resources from clean sources** (author releases/Portal downloads), not in-place cleaning. Reinstall **txAdmin/FXServer from an official artifact** of the same version; never copy single files from `master`.
4. Remove rogue txAdmin admins; review `admins.json`, `server.cfg`, every `fxmanifest.lua` diff.
5. **Rotate every credential** from a clean device (security.md §12): `sv_licenseKey`, DB, txAdmin, RCON (remove), webhooks, bot tokens, `sv_tebexSecret`, API keys, SSH/RDP/SFTP, Discord/Steam/Google accounts used on that host.
6. **Block C2** domains/IPs at the firewall; add an egress allow-list.
7. **Audit the database** for injected money/items/admin groups; be careful restoring backups that predate detection but postdate infection.
8. Harden (security.md §14): FXServer as non-admin user, Git for `resources/`, intake review for every new resource. If FXServer ran as Administrator with personal browser sessions, consider an OS rebuild.

## 6. Server authority review
For each `RegisterNetEvent`, `lib.callback.register`, framework callback, NUI→server path and server export:
1. Captures `source` first; validates the player exists?
2. Permission/job/ownership check on the server?
3. Distance/location check when physical?
4. Argument types/ranges/whitelists; prices from server config; NaN/inf rejected?
5. Rate limit / busy lock; remove-before-add; DB transaction for multi-step changes?
6. Parametrised SQL only (Lua and JS template literals)?
7. Sensitive server exports check `GetInvokingResource()`?
8. Client-written state bags never trusted; works with `sv_stateBagStrictMode true`?
9. Entities spawned server-side; works with `sv_entityLockdown strict`?

Severity guide: arbitrary money/items/admin/RCE → **critical**; exploitable dupes, teleports, kill/strip other players → **high**; info leaks, spam, missing rate limits → **medium**; hygiene → **low**.

## 7. Performance review
- `resmon` idle ≤ 0.02 ms target; loops with `Wait(0)` outside drawing/input.
- Per-frame natives that could be cached; pool scans; `GetDistanceBetweenCoords` instead of `#(a - b)`.
- Server: synchronous heavy work, per-tick DB queries, broadcasts in loops, entity leaks, heavy work inside game-event handlers.
- NUI: always-visible heavy UI, unthrottled `SendNUIMessage`.
Fixes: `performance.md`.

## 8. Compatibility review (2026 platform)
- `fx_version 'cerulean'`, `game 'gta5'`; no `__resource.lua`; `node_version` not `16`.
- No `mysql-async`/`ghmattimysql`; oxmysql ≥ 2.14.0 (sqlstring SQL-injection fix).
- ox_inventory ≥ 2.47.6 (dupe fixes 2.46.0 / 2.46.1 / 2.47.0 / 2.47.6); hooks validation-only.
- ox resources from `overextended/*`, not archived CommunityOx forks.
- No reliance on removed things: `sv_experimental*` convars, `xbl:`/`live:` identifiers, `sv_replaceExeToSwitchBuilds`, Lua 5.3 behaviour.
- Framework calls match installed versions (Qbox exports vs `Player.Functions`, ESX 1.15, QBCore repo moved).
- Enhanced targets: `gta5-enhanced.md` checklist (no escrow, no NUI escrow, lockdown `full`).

## 9. `audit.py` rule reference
| Area | Rule ids (severity) |
|---|---|
| Backdoor / RCE | `known-backdoor` (C), `rce-load-http` (C), `rce-assert-load` (C), `os-exec` (C), `node-child-process` (C), `write-manifest` (C), `rce-load` (H), `obfuscation-hex` (H), `obfuscation-bytes` (H), `js-charcode-decoder` (H), `minified-or-obfuscated` (H), `execute-command` (H), `ace-from-code` (H), `js-raw-network` (M), `http-exfil` (M), `save-other-resource` (M), `convar-secret` (M) |
| SQL | `sql-concat` (C), `sql-format` (C), `sql-template-literal` (C), `sql-mysql-async` (M) |
| Trust boundary | `client-money-event` (H), `client-trusted-price` (H), `webhook-exposed` (H), `server-event-giveitem` (M), `client-setcoords-from-net` (M), `client-replicated-statebag` (M), `nui-unsafe-html` (M), `nui-to-server-direct` (M), `net-event-no-source` (M), `deprecated-register-server-event` (L) |
| server.cfg | `cfg-public-secret` (H), `cfg-lockdown-inactive` (M), `cfg-scripthook-allowed` (M), `cfg-statebag-not-strict` (L) |
| Legacy / perf | `loop-without-wait` (H), `manifest-*`, `esx-getsharedobject-event` (M), `wait-zero-loop` (M), low-severity hygiene rules |
Exit code 1 when any high/critical finding remains. `--json` for CI.

## 10. Report format
```markdown
# Audit: <resource> (<date>)
**Verdict:** SAFE TO RUN | FIX BEFORE RUNNING | DO NOT RUN (malware) | NOT REVIEWABLE (obfuscated/escrowed)
**Provenance:** <where it came from>
## Critical
- [file:line] <what> — <why exploitable / impact> — <fix>
## High / Medium / Low
...
## Performance
- [file:line] <measurement or reasoning> — <fix>
## Compatibility
...
## Not reviewed
- <obfuscated/escrowed files, out-of-scope parts>
## If malware: incident steps taken / required (section 5)
```

## 11. Sources
- Blum Panel advisory (Cfx forum, 2026-07-21): https://forum.cfx.re/t/warning-blum-panel-blum-panel-me-warden-panel-me-is-a-malicious-backdoor-remote-code-loader-hidden-in-resources/5415839
- Blum/Cipher analysis and IOCs (community, single researcher): https://github.com/ImJer/blum-panel-fivem-backdoor-analysis
- Cipher panel overview and recovery (third-party guide): https://fivesecured.com/guides/fivem-cipher-panel
- oxmysql 2.14.0 release: https://github.com/overextended/oxmysql/releases/tag/v2.14.0
- ox_inventory releases: https://github.com/overextended/ox_inventory/releases
- txAdmin permissions: https://github.com/citizenfx/txAdmin/blob/master/docs/permissions.md
- Secure your events: https://docs.fivem.net/docs/developers/server-security/
