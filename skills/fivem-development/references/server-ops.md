# Server operations: artifacts, install, server.cfg, ACE, updates

Baseline: FXServer (Legacy) Recommended **35245** / Latest **37150** · Cfx Server (Enhanced) build 161 · game build 3889 · txAdmin 8.1.1 · OneSync forced on · Lua 5.4 only · Node 22 — verified 2026-10-07.
Related: [convars-and-commands.md](convars-and-commands.md) (every convar/command) · [txadmin.md](txadmin.md) · [onesync-entities.md](onesync-entities.md) · [gta5-enhanced.md](gta5-enhanced.md).

## Contents
1. Artifacts: channels, support policy, selection
2. Directory layout
3. Install on Windows
4. Install on Linux (+ systemd)
5. Production server.cfg standard (with reasoning)
6. ACE / principal permission system
7. Sandbox permissions (filesystem, convars, workers, child processes)
8. Update procedure and rollback
9. Networking, proxies and ports
10. Database server
11. Backups
12. Monitoring
13. Removed / deprecated config you should delete
14. Sources

## 1. Artifacts: channels, support policy, selection
- Download page: https://docs.fivem.net/docs/server-download/ (selector FiveM/RedM vs FiveM for GTAV Enhanced, Windows/Linux, Recommended/Latest).
- JSON API (scriptable): `https://changelogs-live.fivem.net/api/changelog/versions/win32/server` and `/linux/server`. Fields: `recommended`, `latest`, `*_download`, `*_txadmin`, `support_policy` (end-of-support date per build), `support_policy_eol` (end-of-life date per build), and legacy `critical`/`optional` (currently `7290`; not the joinable minimum).
- On 2026-10-07: `recommended` 35245 (txAdmin 8.1.1), `latest` 37150 (txAdmin 8.1.1). Windows file `server.7z` on the download page (the API's `*_download` URLs point to `server.zip`); Linux `fx.tar.xz`. Enhanced: `cfx-server_win_x64` / `cfx-server-linux_x64`.
- Support policy (docs): Recommended supported until **6 weeks** after the next Recommended; Latest until **2 weeks** after the next build. Unsupported builds older than **3 months** are not joinable from the server browser; players see grey **EOS** (still joinable) or red **EOL** (connection fails) warnings.
- **Hard cutoff 2026-10-15**: from 35245 the client always runs the latest GTA V executable and loads only the DLCs requested by `sv_enforceGameBuild`; servers older than 35245 can't be joined after 2026-10-15 (`sv_replaceExeToSwitchBuilds` is fully deprecated).
- Selection rule: production = **Recommended** (or a Latest you've tested on staging if you need a specific fix); staging = Latest. Never run builds whose `support_policy_eol` date is near. Re-check the API before every update.

```bash
# show recommended/latest and download URLs (Linux)
curl -s https://changelogs-live.fivem.net/api/changelog/versions/linux/server \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['recommended'],d['recommended_download']);print(d['latest'],d['latest_download'])"
```

## 2. Directory layout
Keep binaries, data and txData separate so updates are a folder swap:
```
/opt/fivem/                       (C:\FXServer\ on Windows)
├── artifacts/
│   ├── 35245/                    extracted artifact (run.sh or FXServer.exe)
│   ├── 37150/
│   └── current -> 35245          symlink (Linux) / folder name in your .bat (Windows)
├── txData/                       TXHOST_DATA_PATH (txAdmin config, playersDB, logs)
└── server-data/                  git repo
    ├── server.cfg
    ├── secrets.cfg               gitignored: license key, DB string, API keys, webhooks
    ├── permissions.cfg           ACE groups
    └── resources/
        ├── [cfx]                 mapmanager, spawnmanager, chat, hardcap, sessionmanager...
        ├── [core]                oxmysql, ox_lib, framework
        ├── [ox] [standalone] [jobs] [maps] [vehicles] [custom]
```
Without `TXHOST_DATA_PATH`, txData defaults to a path **relative to the artifact** (`<artifact>/../txData` on Windows, the folder holding `run.sh` on Linux) — set it explicitly so artifact swaps never move it.

## 3. Install on Windows
1. Install Git (optional), 7-Zip; for Enhanced also VC++ 2017 x64 redistributable.
2. Create `C:\FXServer\artifacts\35245`, extract `server.7z` (or `server.zip`) there.
3. `git clone https://github.com/citizenfx/cfx-server-data.git C:\FXServer\server-data` (base `resources/[cfx]`), or deploy via a txAdmin recipe.
4. txAdmin mode (recommended):
```bat
@echo off
rem C:\FXServer\start.bat
set TXHOST_DATA_PATH=C:\FXServer\txData
set TXHOST_TXA_PORT=40120
cd /d C:\FXServer\artifacts\35245
FXServer.exe
```
   Vanilla mode (no txAdmin): `cd /d C:\FXServer\server-data` then `C:\FXServer\artifacts\35245\FXServer.exe +exec server.cfg`.
5. Firewall: allow 30120 TCP+UDP inbound; 40120 TCP only from admin IPs.
6. Run as a service: Windows has no built-in wrapper; common choices are NSSM or a Task Scheduler task "At startup" running `start.bat` as a dedicated user (**not official** Cfx guidance). Slow startups on Windows: see https://docs.fivem.net/docs/support/server-issues/ (Defender exclusions for the server folders).

## 4. Install on Linux (+ systemd)
Linux FXServer is a "courtesy port" (Alpine-based proot rootfs, runs on any x86_64 distro); Windows gets fixes faster. Requirements: `xz-utils`, `git`, `curl`/`wget`.
```bash
sudo useradd -r -m -d /opt/fivem -s /bin/bash fivem
sudo -iu fivem
mkdir -p ~/artifacts/35245 ~/txData && cd ~/artifacts/35245
wget "<recommended_download URL from the API>" -O fx.tar.xz && tar xf fx.tar.xz && rm fx.tar.xz
ln -sfn ~/artifacts/35245 ~/artifacts/current
git clone https://github.com/citizenfx/cfx-server-data.git ~/server-data
```
Vanilla run: `cd ~/server-data && bash ~/artifacts/current/run.sh +exec server.cfg`.

systemd unit (txAdmin mode; txAdmin 8+ handles SIGTERM gracefully):
```ini
# /etc/systemd/system/fivem.service
[Unit]
Description=FiveM server (txAdmin)
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=fivem
Group=fivem
WorkingDirectory=/opt/fivem/artifacts/current
Environment=TXHOST_DATA_PATH=/opt/fivem/txData
Environment=TXHOST_TXA_PORT=40120
ExecStart=/opt/fivem/artifacts/current/run.sh
Restart=on-failure
RestartSec=10
TimeoutStopSec=60
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now fivem
journalctl -u fivem -f            # console output (or use the txAdmin live console)
```
Firewall (ufw): `ufw allow 30120/tcp && ufw allow 30120/udp && ufw allow from <admin-ip> to any port 40120 proto tcp`.
If you prefer an interactive console without txAdmin, run vanilla inside `tmux`/`screen` instead of systemd.

## 5. Production server.cfg standard (with reasoning)
```cfg
## ---- network ----
endpoint_add_tcp "0.0.0.0:30120"         # bind all interfaces; change IP only on multi-NIC hosts
endpoint_add_udp "0.0.0.0:30120"         # Enhanced: one endpoint per command
# (no sv_endpointPrivacy: removed; player IPs are never exposed on HTTP endpoints now)

## ---- identity / listing ----
sv_hostname "^2My Server^7 | Serious RP" # <= 120 chars (2026-02 client limits)
sets sv_projectName "My Server"          # <= 40 chars, a name, not tags
sets sv_projectDesc "Serious Spanish RP, custom jobs, economy"   # <= 250 chars
sets tags "roleplay, serious, spanish"
sets locale "es-ES"                      # real locale, never root-AQ
sets Discord "https://discord.gg/xxxx"   # any `sets` key shows on the server page
load_server_icon logo96.png              # 96x96 PNG in server-data
# sets banner_detail "https://.../banner.png"
# sets banner_connecting "https://.../banner.png"
sv_maxclients 64                         # OneSync free up to 48; above that needs an Element Club tier

## ---- game ----
sv_enforceGameBuild 3889                 # latest (mp2026_01); startup only; required by many MLOs/vehicles
set sv_pureLevel 1                       # block modified game files except audio/known graphics mods (2 = block all)
sv_scriptHookAllowed 0                   # never allow ScriptHookV

## ---- security / OneSync policy ----
set sv_entityLockdown relaxed            # block client script entities, keep ambient traffic/peds;
                                         # strict = also no ambient population (server spawns everything)
setr sv_stateBagStrictMode true          # only the server writes networked state bags (setr: clients read it)
set sv_filterRequestControl 2            # block control requests on player-controlled entities
set sv_enableNetworkedSounds false       # block NETWORK_PLAY_SOUND_EVENT routing (abused by cheats)
set sv_enableNetworkedPhoneExplosions false
set sv_enableNetworkedScriptEntityStates false   # test: some scripts need it
setr sv_protectServerEntities true       # Legacy: clients can't delete server-created entities (no effect on Enhanced)
# sv_authMaxVariance 5 / sv_authMinTrust 1 are the defaults; tighten only after testing (see note below)
# set sv_requestParanoia 1               # anti HTTP-flood via proxies; 2+ breaks browser access to *.json
# set sv_disableClientReplays true       # disables Rockstar Editor, reduces cheat vectors

## ---- secrets (gitignored) ----
exec secrets.cfg                         # sv_licenseKey, mysql_connection_string, steam_webApiKey, sv_tebexSecret, webhooks

## ---- resource convars ----
set mysql_slow_query_warning 150
setr ox:locale "es"
set inventory:framework "qbx"            # example of a resource convar (server-only)

## ---- base resources ----
ensure mapmanager
ensure spawnmanager
# ensure sessionmanager                  # no longer auto-started (2026-09) nor needed with OneSync; only if a resource depends on it
ensure hardcap                           # enforces sv_maxclients during connect
ensure chat                              # the system_resources copy (resources_useSystemChat true by default);
                                         # a `chat` folder in resources/ is skipped unless you set it false
# rconlog only if you use `status`/`clientkick` from console

## ---- stack (order = dependencies) ----
ensure oxmysql
ensure ox_lib
ensure qbx_core                          # or es_extended / qb-core / ox_core
ensure ox_target
ensure ox_inventory
ensure pma-voice
ensure [standalone]
ensure [jobs]
ensure [maps]
ensure [custom]

## ---- permissions ----
exec permissions.cfg
```
`secrets.cfg`:
```cfg
sv_licenseKey "cfxk_xxxxxxxxxxxxxxxx"
set mysql_connection_string "mysql://fivem:STRONGPASS@127.0.0.1/fivem?charset=utf8mb4"
set steam_webApiKey ""                   # only if you need steam: identifiers
# sv_tebexSecret "xxxxxxxx"
# set rcon_password ""                   # leave unset: RCON (UDP) disabled
```
Why some lines are **not** there:
- No `set onesync on`, `onesync_enableInfinity`, `sv_experimental*`, `sv_replaceExeToSwitchBuilds` → removed/forced (§13).
- No `sv_master1 ""` unless you want a private server: docs say it only disables joining from the browser, the source (GameServer.cpp) skips listing heartbeats when it's empty — either way, not for public servers.
- No `rcon_password` → RCON disabled (txAdmin console is safer).
- Secrets never in `setr`/`sets` (those are sent to clients / the public `info.json`).
- `sv_authMaxVariance` (1–5, default 5) / `sv_authMinTrust` (1–5, default 1) filter identity providers by how stable/spoof-proof they are; 5 trust means e.g. external three-way auth, so high values can lock out everyone. Keep defaults unless you have tested; the exact provider → level mapping is **UNVERIFIED**.
- `set inventory:framework` is just an example of a resource convar — use each resource's documented names.

## 6. ACE / principal permission system
Terms:
- **Principal**: who. `identifier.<type>:<value>` (`identifier.license:abc…`, `identifier.fivem:123`, `identifier.discord:…`, `identifier.steam:…`), groups (`group.admin`, any name), `resource.<name>`, `system.console`, and `builtin.everyone` (every player).
- **Object (ACE)**: what. Dotted strings; `command.<name>` for commands, `command` = all commands; your own nodes (`myres.police`, `job.police`). Granting `x` also grants `x.*` (wildcard by prefix).
- **Inheritance**: `add_principal <child> <parent>` — child gets all of parent's ACEs.
- Results: allow, deny, unset (= deny). An explicit `deny` overrides an inherited/wildcard `allow` (official pattern: `add_ace group.admin command allow` + `add_ace group.admin command.quit deny`).

Commands: `add_ace <principal> <object> allow|deny`, `remove_ace …`, `add_principal <child> <parent>`, `remove_principal …`, `test_ace <principal> <object>`, `list_aces`, `list_principals`.

`permissions.cfg`:
```cfg
# groups
add_ace group.admin command allow            # all commands
add_ace group.admin command.quit deny        # except quit
add_ace group.admin admin allow              # your own admin.* nodes
add_ace group.mod command.kick allow
add_ace group.mod admin.spectate allow
add_principal group.admin group.mod          # admins inherit mod

# job-ish nodes used by resources
add_ace group.police job.police allow

# people (prefer license or fivem ids; never IP)
add_principal identifier.fivem:1234567 group.admin
add_principal identifier.license:0123456789abcdef group.mod

# resources that run commands (ExecuteCommand needs command.<name>)
add_ace resource.qbx_core command.add_principal allow
add_ace resource.qbx_core command.remove_principal allow
```
Server-side checks:
```lua
-- server.lua
if not IsPlayerAceAllowed(source, 'admin.spectate') then return end
local ok = IsPrincipalAceAllowed('group.police', 'job.police')      -- shared native
RegisterCommand('heal', function(src, args) --[[ ... ]] end, true)    -- restricted: needs command.heal
```
- Restricted commands (`RegisterCommand(name, fn, true)`) require `command.<name>`. The console (`source == 0`) always passes.
- Runtime grants (e.g. framework job duty): `ExecuteCommand(('add_principal player.%d group.police'):format(src))` — the resource needs `command.add_principal`; IDs differ between frameworks, check their docs. Remove on drop.
- ACE ≠ txAdmin admin permissions (see [txadmin.md](txadmin.md)). Qbox recommends ACE for permissions (its permission exports are deprecated).
- Debug: `test_ace identifier.license:abc admin.spectate`, `list_aces`, `list_principals`.

## 7. Sandbox permissions (filesystem, convars, workers, child processes)
Resources run in a sandbox: Lua `io`/`os` limited (no `os.execute`, no `io.popen` except emulated `ls`/`dir`, no symlinks, no `..`, writes only inside the same resource; error 13 "Permission denied"). Node child processes and workers are blocked by default. Opt-in per resource in `server.cfg`:
```cfg
add_filesystem_permission resourceA write resourceB    # resourceA may write into resourceB
add_convar_permission screencapture read sv_licenseKey # once any permission exists for a convar, only listed resources can read it
add_unsafe_worker_permission "my_worker_res"           # allow worker threads
add_unsafe_child_process_permission "my_tool_res"      # allow child_process (e.g. builders) — trusted code only
```
Use `add_convar_permission` to hide secrets (`mysql_connection_string`, webhooks) from all but the resource that needs them.

## 8. Update procedure and rollback
1. Read the changelog/forum for breaking changes; check the API for the new Recommended.
2. Test on staging (same resources, copy of DB).
3. Backup: `mysqldump`, `server-data` (git commit), `txData`.
4. Download/extract the new artifact into a **new** folder (`artifacts/37150`). Don't extract over the running one.
5. Announce, stop via txAdmin (players get `serverShuttingDown`) or `systemctl stop fivem`.
6. Point `current` to the new folder (Linux `ln -sfn`; Windows edit `start.bat`), start, watch console for resource errors.
7. Rollback = point back to the previous folder (keep the last 2–3).
8. Then update resources in dependency order: oxmysql → ox_lib → framework → inventory/target → others. Bump `sv_enforceGameBuild` only after map/vehicle packs are verified for the new build.
txAdmin itself updates with the artifact (it's bundled as the `monitor` resource).

## 9. Networking, proxies and ports
- Ports: 30120 TCP (HTTP: `info.json`, `players.json`, `dynamic.json`, file downloads) + 30120 UDP (game); 40120 TCP txAdmin. Change both endpoint lines together for a different port.
- `net_tcpConnLimit` (16 per IP) — raise only behind proxies/NAT-heavy players.
- Reverse proxy / DDoS frontends (Cloudflare + nginx): `set sv_forceIndirectListing true`, `set sv_listingHostOverride "server1.example.com"`, `set sv_proxyIPRanges "<proxy CIDRs>"` (trusts X-Real-IP, bypasses rate limiter), `set sv_endpoints "<public ip:port>"`; caching file proxy: `set adhesive_cdnKey "<secret>"` + `fileserver_add ".*" "https://server1.example.com/files"`; optionally `set sv_httpFileServerProxyOnly true`. Full guide: https://docs.fivem.net/docs/server-manual/proxy-setup/.
- The old `*.users.cfx.re` reverse proxy was shut down on **2026-03-31**; host your own.
- Enhanced: new handshake (no UDP until connected, deferrals over WebSocket) — re-test DDoS filters.

## 10. Database server
MariaDB ≥ 10.6 (or MySQL ≥ 8), `utf8mb4`, on the same host or LAN (every `await` query adds latency). Dedicated user with rights only on the server DB; bind to 127.0.0.1 unless remote access is needed. Tune `innodb_buffer_pool_size` (~50–70 % RAM on a dedicated DB box). oxmysql reads `mysql_connection_string` (URI or `key=value;` form).

## 11. Backups
- DB: daily `mysqldump --single-transaction --routines --triggers fivem | gzip > fivem-$(date +%F).sql.gz`, keep 7–30 days off-host; test restores.
- `server-data`: git (exclude `secrets.cfg`, `cache/`); txData: copy (contains playersDB and admins).
- Don't back up `cache/` (regenerated).

## 12. Monitoring
- txAdmin: crash/hang auto-restart, CPU/RAM, live console, player counts.
- In-game/console: `resmon` (client), `profiler record 300` → `profiler save` / `profiler view`, `netgraph`.
- Prometheus: `/perf` endpoint on the server HTTP port; protect with `sv_prometheusBasicAuthUser`/`sv_prometheusBasicAuthPassword` (Legacy exposes svMain/svNetwork/svSync tick histograms; Enhanced 80+ metrics).

## 13. Removed / deprecated config you should delete
| Line | Why |
|---|---|
| `set onesync on/legacy`, `onesync_enabled`, `onesync_enableInfinity` | OneSync forced on (2026-08) |
| `sv_experimentalStateBagsHandler`, `sv_experimentalOneSyncPopulation`, `sv_experimentalNetGameEventHandler` | Removed, always on (docs still list them) |
| `sv_replaceExeToSwitchBuilds` | Fully deprecated with 35245 |
| `onesync_enableBeyond`, `sv_enhancedHostSupport` | No effect (`sv_protectServerEntities` works on Legacy, not on Enhanced) |
| `sv_endpointPrivacy`, `sv_exposePlayerIdentifiersInHttpEndpoint` | Removed (warning at boot); endpoints/identifiers never exposed |
| `sv_master1 ""` on a public server | Makes the server private/unlisted |
| `lua54 'yes'` everywhere / Lua 5.3 assumptions | Lua 5.3 runtime removed 2025-06-24 (5.4.8 only) |
| `xbl:` / `live:` identifiers in ACE or bans | Removed 2026-04-27 |
| `*.users.cfx.re` URLs | Nucleus proxy shut down 2026-03-31 |
| `+set txAdminPort/txAdminInterface/txDataPath` | Use `TXHOST_*` env vars (txAdmin 8) |
| Enhanced only: `sv_netHttp2`, `onesync_automaticResend`, `sv_useAccurateSends`, `+set moo 31337` | Removed/deprecated on Cfx Server |

## 14. Sources
- https://docs.fivem.net/docs/server-download/ · https://changelogs-live.fivem.net/api/changelog/versions/win32/server · https://changelogs-live.fivem.net/api/changelog/versions/linux/server (queried 2026-10-07)
- https://docs.fivem.net/docs/server-manual/end-of-support-end-of-life/
- https://docs.fivem.net/docs/server-manual/setting-up-a-server-vanilla/ · https://docs.fivem.net/docs/server-manual/setting-up-a-server-txadmin/ · https://docs.fivem.net/docs/server-manual/proxy-setup/
- https://docs.fivem.net/docs/server-manual/server-commands/ · https://docs.fivem.net/docs/scripting-reference/convars/ · https://docs.fivem.net/docs/developers/sandbox/ · https://docs.fivem.net/docs/developers/server-security/
- Example cfg: https://github.com/citizenfx/fivem-docs/blob/master/static/examples/config/server.cfg (docs repo commit c2b2125)
- https://forum.cfx.re/t/90917 (ACE & principals guide) · https://forum.cfx.re/t/5422124 (35245 / 2026-10-15 cutoff) · https://forum.cfx.re/t/5377566 (listing length limits) · https://forum.cfx.re/t/5387399 (Nucleus proxy deprecation) · https://forum.cfx.re/t/5397645 (xbl/live removal) · https://forum.cfx.re/t/5335232 (Lua 5.3 removal) · https://forum.cfx.re/t/5405819 (allowlist padlock convars)
- https://github.com/citizenfx/txAdmin (`docs/env-config.md`)
