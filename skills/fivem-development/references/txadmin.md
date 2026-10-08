# txAdmin (bundled server manager)

Baseline: txAdmin **8.1.1** (2026-06-05), bundled with FXServer Recommended 35245 / Latest 37150 and with Cfx Server (Enhanced) build 161 — verified 2026-10-07 against `citizenfx/txAdmin` master (`8a9a414`) and its `docs/` folder.

## Contents
1. What it is, ports and data layout
2. First setup
3. Host configuration: TXHOST_* environment variables
4. Recipes and the recipe format
5. Admins and permissions
6. Allowlist modes
7. Bans, warns and the player database
8. Scheduled restarts, shutdown and health monitoring
9. Events for resources (`txAdmin:events:*`) with payloads
10. In-game menu and txAdmin convars
11. Discord bot
12. Logs, backups and maintenance
13. Security hardening
14. Version notes (8.0 / 8.1)
15. Automating txAdmin from tools (internal API)
16. Sources

## 1. What it is, ports and data layout
- Web panel + process manager shipped inside every FXServer/Cfx Server artifact (txAdmin joined Cfx.re in April 2025). Starting `FXServer.exe` / `run.sh` **without** `+exec` launches txAdmin, which then spawns FXServer with your `server.cfg`.
- Ports: panel **40120/tcp** (`TXHOST_TXA_PORT`), game **30120/tcp+udp**. txAdmin refuses FXServer ports in 40120–40150.
- Data: `txData/` (default Windows `<fxserver_root>/../txData`, Linux `<fxserver_root>/../../../txData` = the folder containing `run.sh`). Inside: `admins.json`, `<profile>/config.json`, `<profile>/data/playersDB.json`, `<profile>/logs/`.
- One txData per server is recommended; the `serverProfile` convar still works but is slated for deprecation.

## 2. First setup
1. Download artifact (see [server-ops.md](server-ops.md)), run the binary with no arguments.
2. Open `http://<host>:40120`, enter the PIN printed in the console, link your Cfx.re account (or create a password-only master account), set a backup password.
3. Choose **Popular Recipes** (deploy a new server), **Local server data** (existing `server-data` + `server.cfg`), or **Custom template** (recipe URL).
4. Deployer: enter license key (`cfxk_…` from https://portal.cfx.re), database credentials if the recipe needs them, review the generated `server.cfg`, *Save & Run*.
5. Afterwards: Settings → FXServer (cfg path, startup args, autostart), Restarter (schedule), Allowlist, Bans, Discord, Game (menu options).

Official recipes (index https://github.com/citizenfx/txAdmin-recipes, `indexv4.json`; `indexv5.json` adds Enhanced variants): Basic FiveM (Legacy and Enhanced), Basic RedM, ESX Legacy, Qbox, QBCore, vMenu, StreetKings, Warfare Tactics V, VORP Core.

## 3. Host configuration: TXHOST_* environment variables
Since 8.0 host-level settings are **environment variables** (set before launching), replacing the `+set txAdminPort/txAdminInterface/txDataPath` convars (still read with a warning; env var wins; silence with `TXHOST_IGNORE_DEPRECATED_CONFIGS=true`).

| Variable | Default | Meaning |
|---|---|---|
| `TXHOST_DATA_PATH` | see §1 | Absolute path of txData (replaces `txDataPath`). |
| `TXHOST_GAME_NAME` | any | `fivem` or `redm`; restricts game and recipe list. |
| `TXHOST_MAX_SLOTS` | — | Enforces `sv_maxclients ≤ N`; deployer `{{maxClients}}`. |
| `TXHOST_QUIET_MODE` | `false` | `'true'` = FXServer output not piped to stdout. |
| `TXHOST_API_TOKEN` | undefined | Enables `GET /host/status`: undefined = disabled, `disabled` = public, else 16–48 chars `[A-Za-z0-9_-]` sent as `x-txadmin-envtoken` header or `?envtoken=`. |
| `TXHOST_TXA_URL` | — | Public URL shown in boot message. |
| `TXHOST_TXA_PORT` | `40120` | Panel port (replaces `txAdminPort`); cannot be 30120. |
| `TXHOST_FXS_PORT` | — | Forces/rewrites `endpoint_add_*` in server.cfg (not 40120–40150). |
| `TXHOST_INTERFACE` | `0.0.0.0` | IPv4 to bind txAdmin and FXServer (replaces `txAdminInterface`). |
| `TXHOST_PROVIDER_NAME` / `TXHOST_PROVIDER_LOGO` | `Host Config` | Branding for hosting providers (logo URL ≤ 224×96, `{theme}` placeholder). |
| `TXHOST_DEFAULT_DBHOST/DBPORT/DBUSER/DBPASS/DBNAME` | — | Prefill deployer DB fields. |
| `TXHOST_DEFAULT_CFXKEY` | — | Prefill license key. |
| `TXHOST_DEFAULT_ACCOUNT` | — | Create master on first boot: `username:fivemId[:bcryptHash]`. |
| `TXHOST_IGNORE_DEPRECATED_CONFIGS` | `false` | Ignore old convars/`txAdminZapConfig.json`. |

```bash
# Linux (systemd unit or shell) — second server on the same box
export TXHOST_DATA_PATH=/opt/fivem/server2/txData
export TXHOST_TXA_PORT=40125
export TXHOST_INTERFACE=0.0.0.0
/opt/fivem/artifacts/run.sh
```
```bat
:: Windows .bat
set TXHOST_DATA_PATH=C:\FXServer\server2\txData
set TXHOST_TXA_PORT=40125
C:\FXServer\artifacts\FXServer.exe
```
txAdmin handles SIGINT/SIGHUP/SIGTERM gracefully (8.0+): it fires `serverShuttingDown` and stops FXServer — `systemctl stop` is safe.

## 4. Recipes and the recipe format
YAML file with metadata + `tasks`. Deploy is jailed to the target folder; at the end `server.cfg` and `resources/` must exist; failures leave `_DEPLOY_FAILED_DO_NOT_USE`.

```yaml
name: My RP base
author: me
description: Qbox + ox stack
$engine: 3                # deployer version (must be >= 3)
$minFxVersion: 35245      # refuse older artifacts
$onesync: on              # off | legacy | on (OneSync is forced on anyway)
$steamRequired: false
variables:
  locale: es
tasks:
  - action: connect_database          # creates DB if needed (random name unless set)
  - action: download_github
    src: overextended/oxmysql
    ref: v2.14.3                      # pin refs (avoid GitHub rate limits)
    dest: ./resources/[ox]/oxmysql
  - action: download_file
    url: https://example.com/release.zip
    path: ./tmp/release.zip
  - action: unzip
    src: ./tmp/release.zip
    dest: ./tmp/release
  - action: move_path
    src: ./tmp/release/my_res
    dest: ./resources/[custom]/my_res
  - action: query_database
    file: ./resources/[custom]/my_res/install.sql
  - action: download_file
    url: https://example.com/server.cfg
    path: ./server.cfg
  - action: replace_string
    file: ./server.cfg
    search: 'LOCALE_HERE'
    replace: '{{locale}}'             # mode: template (default, renders {{vars}}) | all_vars | literal
  - action: remove_path
    path: ./tmp
```
| Task | Options (default timeout) |
|---|---|
| `download_github` | `src` (URL or `owner/repo`), `ref?`, `subpath?`, `dest` (180 s) |
| `download_file` | `url`, `path` (180 s) |
| `unzip` | `src`, `dest` — zip only (180 s) |
| `move_path` | `src`, `dest`, `overwrite?` (180 s) |
| `copy_path` | `src`, `dest`, `overwrite?` (true), `errorOnExist?` (false) (180 s) |
| `remove_path` / `ensure_dir` | `path` (not `./`) (15 s) |
| `write_file` | `file`, `data`, `append?` (15 s) |
| `replace_string` | `file` (string or list), `search`, `replace`, `mode?` (15 s) |
| `connect_database` | none; uses context DB vars (30 s) |
| `query_database` | `file` **or** `query` (90 s) |
| `load_vars` | `src` JSON file (5 s) |
| debug: `waste_time` (`seconds`), `fail_test`, `dump_vars` | undocumented |
Every task accepts `timeoutSeconds`.

Context variables (`{{name}}`): `deploymentID`, `serverName`, `recipeName`, `recipeAuthor`, `recipeDescription`, `svLicense`, `dbHost`, `dbPort`, `dbUsername`, `dbPassword`, `dbName`, `dbDelete`, `dbConnectionString` (`mysql://user:pass@host[:port]/db?charset=utf8mb4`), `maxClients` (TXHOST_MAX_SLOTS or 48), `serverEndpoints` (the two `endpoint_add_*` lines), `addPrincipalsMaster` (`add_principal identifier.<id> group.admin` lines for the master), plus your `variables`. Reserved names you can't redefine: `licenseKey`, `dbHost`, `dbUsername`, `dbPassword`, `dbName`, `dbConnection`, `dbPort`. `recipeVersion` is documented but **UNVERIFIED** (not set in code). Recipe repo guidelines: server.cfg must contain `{{maxClients}}`, `{{addPrincipalsMaster}}`, `{{serverEndpoints}}`, `{{svLicense}}`; DB tasks first; pin `ref`.

## 5. Admins and permissions
txAdmin admins (stored in `txData/admins.json`) are **separate from ACE**. Linking a Cfx.re (fivem:) and/or Discord identifier lets the in-game menu recognise the admin. The deployer adds `add_principal identifier.<id> group.admin` for the master, which is ACE.

| Permission | Allows |
|---|---|
| `all_permissions` | Everything (removes others) |
| `manage.admins` | Create/edit/delete admins |
| `settings.view` / `settings.write` | View settings (no tokens) / change settings |
| `console.view` / `console.write` | Live console / send commands |
| `control.server` | Start/stop/restart server, scheduler |
| `announcement` | Announcements |
| `commands.resources` | Start/stop resources |
| `server.cfg.editor` | Read/write server.cfg |
| `txadmin.log.view` / `server.log.view` | System logs / server logs |
| `players.remove_ids` | Delete player IDs/HWIDs (8.1) |
| `menu.vehicle`, `menu.clear_area`, `menu.viewids` | Menu: vehicles, reset area, show IDs |
| `players.direct_message`, `players.whitelist`, `players.warn`, `players.kick`, `players.ban` | Player actions |
| `players.freeze`, `players.heal`, `players.playermode`, `players.spectate`, `players.teleport`, `players.troll` | Menu player actions |
Master-only: DB backup download, database cleanup, revoke allowlists. Least privilege: moderators rarely need `console.write`, `server.cfg.editor`, `settings.write` (console write = arbitrary server commands).

## 6. Allowlist modes
Setting `whitelist.mode` (UI calls it allowlist since 8.1):

| Mode | Who can join |
|---|---|
| `disabled` (default) | Everyone (ban check only) |
| `adminOnly` | Only txAdmin admins (maintenance) |
| `approvedLicense` | Players whose `license:` was approved (Allowlist page or `/allowlist` bot command); unknown players get a request id `Rxxxx` |
| `discordMember` | Members of the configured guild (bot required) |
| `discordRoles` | Members with one of the configured role ids |
| `external` (8.1) | txAdmin doesn't check; a third-party resource does. txAdmin still sets the server-list lock |
txAdmin sets `sets sv_appearAllowlisted true` (any mode ≠ disabled) and `sv_allowlistInstructions` (rejection message; not in adminOnly) so the server browser shows the padlock. Don't set those convars manually when txAdmin manages them.

## 7. Bans, warns and the player database
- Player DB: `txData/<profile>/data/playersDB.json` (lowdb, DB v5): players, play time, notes, actions (bans/warns), HWIDs, allowlist. No MySQL needed and not your framework DB.
- Bans match identifiers and HWIDs (`requiredHwidMatches`, default 1; 0 disables HWID matching). Durations: hours/days/weeks/months or permanent. **Ban templates** (`banlist.templates`) give preset reasons/durations.
- `txAdmin-checkPlayerJoin` makes the bundled `monitor` resource check bans/allowlist during `playerConnecting`.
- Ban from your own resource: don't write to playersDB; trigger the admin through txAdmin or use your own ban table. Listening to `playerBanned` lets you mirror bans.

## 8. Scheduled restarts, shutdown and health monitoring
- Settings → Restarter: list of `HH:MM` times (server local time). Warnings at 30/15/10/5/4/3/2/1 min (chat + Discord + `scheduledRestart` event). Temporary one-off restart: `+N` minutes or `HH:MM`. If you stop the server manually, a scheduled restart < 2 h away is skipped.
- FXServer settings: `shutdownNoticeDelayMs` (5000; time between `serverShuttingDown` and kill — raise to ~10000 if saves are slow), `restartSpawnDelayMs` (500), `bootGracePeriod` (45 s), `resourceStartingTolerance` (90 s), `autoStart`, `startupArgs`, `cfgPath`, `quiet`.
- Health: txAdmin polls the server HTTP endpoint every second and watches a heartbeat; after boot, ~60 s without heartbeat or ~180 s failed HTTP → restart (partial hang → announcement `partial_hang_warn`). Constants are hard-coded; exact restart logic **UNVERIFIED** in detail.
- Restart policy recommendation: 1–4 scheduled restarts/day for RP servers; save data on `serverShuttingDown` rather than on each warning.

## 9. Events for resources (`txAdmin:events:*`)
Server-side, local events (`AddEventHandler`, not net events), one table argument. Events are not replayed: actions taken while the server is offline fire nothing.

| Event | Payload |
|---|---|
| `announcement` | `{ author, message }` |
| `serverShuttingDown` | `{ delay (ms), author, message }` — any stop/restart |
| `scheduledRestart` | `{ secondsRemaining, translatedMessage }` — at 1800/900/600/300/240/180/120/60 s |
| `scheduledRestartSkipped` | `{ secondsRemaining, temporary, author }` |
| `playerBanned` | `{ author, reason, actionId, expiration (unix s or false), durationInput, durationTranslated, targetNetId (or nil), targetIds, targetHwids, targetName, kickMessage }` |
| `playerWarned` | `{ author, reason, actionId, targetNetId (nil if offline), targetIds, targetName }` |
| `playerKicked` | `{ target (netid or -1 = all), author, reason, dropMessage }` |
| `playerDirectMessage` | `{ target, author, message }` |
| `playerHealed` | `{ target (netid or -1 = all), author }` |
| `actionRevoked` | `{ actionId, actionType, actionReason, actionAuthor, playerName (or false), playerIds, playerHwids, revokedBy }` |
| `whitelistPlayer` | `{ action ('added'|'removed'), license, playerName, adminName }` |
| `whitelistPreApproval` | `{ action, identifier, playerName?, adminName }` |
| `whitelistRequest` | `{ action ('requested'|'approved'|'denied'|'deniedAll'), playerName?, requestId?, license?, adminName? }` |
| `adminAuth` | `{ netid (-1 = all), isAdmin, username? }` |
| `adminsUpdated` | array of online admin netids |
| `configChanged` | none (e.g. language change) |
| `consoleCommand` | `{ author, channel = 'txAdmin', command }` (8.0+) |
Deprecated (still fired, don't use): `healedPlayer` (`{ id }`), `skippedNextScheduledRestart`, `playerWhitelisted`.

```lua
-- server.lua: flush data before txAdmin restarts/stops the server
local saving = false

local function saveAll(reason)
    if saving then return end
    saving = true
    print(('[my_res] saving all players (%s)'):format(reason))
    for _, src in ipairs(GetPlayers()) do
        -- call your framework's own save function here (see the framework reference)
        TriggerEvent('my_res:server:savePlayer', tonumber(src))
    end
    saving = false
end

AddEventHandler('txAdmin:events:scheduledRestart', function(data)
    if data.secondsRemaining == 60 then saveAll('restart in 60s') end
end)

AddEventHandler('txAdmin:events:serverShuttingDown', function(data)
    saveAll(('shutdown by %s, %d ms'):format(data.author, data.delay))
end)

AddEventHandler('txAdmin:events:playerBanned', function(data)
    -- mirror to Discord/your DB; data.targetIds is a list of identifiers
    print(('[bans] %s banned %s: %s'):format(data.author, data.targetName, data.reason))
end)
```
Custom command logging to txAdmin's Server Log: client `TriggerServerEvent('txaLogger:CommandExecuted', rawCommand)`.

## 10. In-game menu and txAdmin convars
Menu: `/tx` or `/txadmin [id]` (keybind "(txAdmin) Menu: Open Main Page"); `/txAdmin-reauth` retries admin auth. Admin needs a linked fivem or discord identifier.

Set by txAdmin from Settings (don't hand-edit): `txAdmin-menuEnabled` (true, restart needed), `txAdmin-menuAlignRight` (false), `txAdmin-menuPageKey` (`Tab`), `txAdmin-playerModePtfx` (true), `txAdmin-hideAdminInPunishments` (true), `txAdmin-hideAdminInMessages` (false), `txAdmin-hideDefaultAnnouncement`, `txAdmin-hideDefaultDirectMessage`, `txAdmin-hideDefaultWarning`, `txAdmin-hideDefaultScheduledRestartWarning` (all false — set true when your own UI handles the events), `txAdmin-locale`, `txAdmin-serverName`, `txAdmin-checkPlayerJoin`, `sv_appearAllowlisted`, `sv_allowlistInstructions`.

Manual convars (server.cfg): `setr txAdmin-debugMode false`, `set txAdmin-menuPlayerIdDistance 150`, `set txAdmin-menuDrunkDuration 30`, `set txAdmin-menuAnnounceNotiPos top-center` (`top-left|top-right|bottom-center|bottom-left|bottom-right`).

Internal (never touch): `txAdmin-luaComHost`, `txAdmin-luaComToken`, `txAdmin-version`, `txAdminServerMode`. "Invalid Request: source" in the menu → `webServer.disableNuiSourceCheck` in config.json.

## 11. Discord bot
Settings → Discord: bot token, guild id, warnings channel; enable the Server Members intent for member/role allowlists. Slash commands: `/status add|remove` (persistent auto-updated status embed), `/allowlist member <member>` / `/allowlist request <Rxxxx>` (alias `/whitelist`), `/info self|member|id`. Embed JSON placeholders: `{{serverCfxId}}`, `{{serverJoinUrl}}`, `{{serverBrowserUrl}}`, `{{serverClients}}`, `{{serverMaxClients}}`, `{{serverName}}`, `{{statusColor}}`, `{{statusString}}`, `{{uptime}}`, `{{nextScheduledRestart}}`; up to 5 buttons.

## 12. Logs, backups and maintenance
- Logs in `txData/<profile>/logs/`: admin (7-day rotation), fxserver (daily, 7 files), server (daily, 7 files). Configure via `logger.*` keys in config.json.
- playersDB: autosaved (15 s–5 min by priority), `playersDB.backup.json` every 5 min, versioned backup on migrations; master can download a JSON backup. Daily optimizer prunes players inactive 16 days with < 120 min played and old allowlist requests (txAdmin DB only).
- cfg editor writes `server.cfg.bkp` before saving.
- **txAdmin does not back up MySQL or resources.** Schedule `mysqldump` and a git/rsync backup yourself (see [server-ops.md](server-ops.md)).

## 13. Security hardening
- Firewall 40120 to admin IPs/VPN, or put it behind a TLS reverse proxy; brute-force limiter defaults: 10 attempts / 15 min.
- Use Cfx.re login + strong backup password; remove unused admins; least privilege (no `console.write`/`all_permissions` for moderators).
- Keep txAdmin updated by updating the artifact (it's bundled; don't replace `monitor` manually).
- `TXHOST_API_TOKEN` only if you need `/host/status`, never `disabled` on a public host.
- Never paste the panel URL + PIN publicly during setup.

## 14. Version notes (8.0 / 8.1)
- **8.0.0** (2025-03-06): TXHOST_* env vars; graceful signals; `consoleCommand` event; `author` on events; kick-all → `playerKicked` with `-1`; deprecated `healedPlayer`, `skippedNextScheduledRestart`, `txaKickAll`; new config format; reset server data button.
- **8.1.0** (2026-06-03): `external` allowlist mode; "whitelist" → "allowlist" in UI (config keys/events unchanged); delete player IDs (`players.remove_ids`); `printFxResourcesBootLog` command; PWA; new recipe index URL.
- **8.1.1** (2026-06-05): allowlist renames; `sv_allowlistInstructions` not set in adminOnly.

## 15. Automating txAdmin from tools (internal, unversioned API)
txAdmin has no public REST API. Its panel routes can be scripted but may change between releases (verified against citizenfx/txAdmin master, `core/modules/WebServer/router.ts`, 2026-10-07):
- Login: `POST /auth/password` JSON `{ "username", "password" }` → session cookie + `csrfToken` in the JSON body. Send it back as header `x-txadmin-csrftoken` on every authenticated POST (reverse proxies must not strip it). Login is behind a rate limiter (repeated failures lock the IP for a while).
- Resources: `POST /fxserver/commands` `{ "action": "ensure_res"|"restart_res"|"start_res"|"stop_res"|"refresh_res", "parameter": "<resource>" }`. Needs permission `commands.resources`; start/restart/ensure of `runcode` is refused. Run `refresh_res` after editing an `fxmanifest.lua`.
- Server: `POST /fxserver/controls` `{ "action": "start"|"stop"|"restart" }` (permission `control.server`).
- Players: `GET /player/search`; `POST /player/kick` etc. (permissions `players.kick`, `players.warn`, `players.ban`, ...).
- Live console: socket.io at `/socket.io` with handshake query `rooms=liveconsole`, **long-polling only** (the panel handles no websocket upgrade); server emits `consoleData` (recent buffer first), client emits `consoleCommand` (needs `console.write`; viewing needs `console.view`). No ack; newlines in commands become spaces; the command is logged under the admin's name. Details and risks: [ai-dev-workflow-and-mcp.md](ai-dev-workflow-and-mcp.md).
- Use a dedicated admin account with only these permissions; keep credentials in environment variables. `/host/status` with `TXHOST_API_TOKEN` (§3) is the only token-based route.
- Sources: https://github.com/citizenfx/txAdmin — `core/modules/WebServer/router.ts`, `core/routes/authentication/verifyPassword.ts`, `core/modules/WebServer/middlewares/authMws.ts`, `core/modules/WebServer/webSocket.ts`, `core/modules/WebServer/wsRooms/liveconsole.ts`
## 16. Sources
- https://github.com/citizenfx/txAdmin (docs: `events.md`, `env-config.md`, `permissions.md`, `menu.md`, `recipe.md`, `discord-status.md`, `custom-server-log.md`, `logs.md`; source: `core/modules/ConfigStore/schema/*.ts`, `core/modules/AdminStore/index.js`, `core/deployer/*`, `core/modules/FxScheduler.ts`, `core/modules/FxMonitor/index.ts`, `core/boot/getHostVars.ts`, `resource/*.lua`)
- https://github.com/citizenfx/txAdmin/releases (v8.0.0, v8.0.1, v8.1.0, v8.1.1)
- https://github.com/citizenfx/txAdmin-recipes (README, `indexv4.json`, `indexv5.json`)
- https://docs.fivem.net/docs/resources/txAdmin/ · https://docs.fivem.net/docs/resources/txAdmin/permissions/ · https://docs.fivem.net/docs/server-manual/setting-up-a-server-txadmin/
- https://forum.cfx.re/t/5319010 (txAdmin joins Cfx.re) · https://forum.cfx.re/t/5427091 (vMenu/Warfare Tactics V recipes) · https://forum.cfx.re/t/5405819 (allowlist padlock convars)
