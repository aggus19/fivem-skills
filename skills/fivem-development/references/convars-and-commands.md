# Convars and server commands (FXServer / Cfx Server)

Baseline: FXServer Recommended 35245 / Latest 37150 (source `citizenfx/fivem` master `a74c2cc`, 2026-10-07) · Cfx Server (Enhanced) build 161 · docs repo `citizenfx/fivem-docs` `c2b2125` (2026-10-01) — verified 2026-10-07.
Where docs and source disagree, the **source** wins and the row says so. Legacy = FXServer; Enh = Cfx Server (Enhanced; partly closed source, so docs only).

## Contents
1. How convars work (set / setr / sets / seta, flags, startup-only)
2. Reading convars from scripts
3. Core, identity and listing convars
4. Security and anti-cheat convars
5. OneSync / game state convars
6. Network, HTTP and proxy convars
7. Rate limiters
8. Enhanced-only convars
9. Server-list `sets` keys and common resource convars
10. Removed / deprecated / internal (2025–2026 changes)
11. Server console commands
12. Access-control (ACE) and sandbox commands
13. Sources

## 1. How convars work
| Command | Effect | Visible to |
|---|---|---|
| `set name value` | Plain convar | Server scripts (`GetConvar`) |
| `setr name value` | + `ConVar_Replicated` | Server **and clients** (`GetConvar` client-side) — never secrets |
| `sets name value` | + `ConVar_ServerInfo` | Public: server list, `/info.json` "vars" — never secrets |
| `seta name value` | + `ConVar_Archive` | Saved (client-side concept) |
| `name value` | Shorthand for `set` on an existing convar | — |
| `+set name value` | On the command line (startup) | — |
Flags in source (`citicore/console/Console.Variables.h`): `ReadOnly` = only settable at startup (`+set` or the startup cfg); `Internal` = cannot be changed at all; `ScriptRestricted` = scripts can't read. Names are **case-insensitive** (`sv_maxclients` = `sv_maxClients`). Startup-only list (`citizen-server-main/src/ServerInstance.cpp`): `onesync`, `onesync_enabled`, `onesync_population`, `netlib`, `onesync_enableInfinity`, `onesync_enableBeyond`, `gamename`, `sv_enforceGameBuild`, `sv_licenseKey`, `resources_useSystemChat`.
Print a value: type its name in the console. Quotes for spaces: `set my_var "a b c"`.
**`;` separates commands** in server.cfg and the console (Quake-style), exactly like a newline. `set foo a;b` runs `set foo a` and then a command `b`. Only double quotes protect it: `set mysql_connection_string "user=fivem;password=x;host=127.0.0.1;database=fivem"`. Comments are `#`, never `;` (`audit.py` rule `cfg-unquoted-semicolon`). Source: `Context::ExecuteBuffer` in https://github.com/citizenfx/fivem/blob/master/code/client/citicore/console/Console.cpp

## 2. Reading convars from scripts
```lua
-- server or client (client sees only setr convars)
local locale   = GetConvar('ox:locale', 'en')
local maxSlots = GetConvarInt('sv_maxclients', 48)
local debug    = GetConvarBool('my:debug', false)        -- verified native (shared)
local ratio    = GetConvarFloat('my:ratio', 1.0)

-- react to changes (shared native AddConvarChangeListener)
AddConvarChangeListener('my:*', function(name, reserved)
    print(('convar %s changed to %s'):format(name, GetConvar(name, '')))
end)

-- server only
SetConvar('my:runtime', 'x')               -- set
SetConvarReplicated('my:shared', 'y')      -- setr
SetConvarServerInfo('Discord', 'https://discord.gg/x') -- sets
```
Restrict reading of secrets to one resource: `add_convar_permission <resource> read <convar>` (§12).

## 3. Core, identity and listing convars
| Convar | Cmd | Default | Values | Production | Notes / status |
|---|---|---|---|---|---|
| `sv_hostname` | set | `default FXServer` | ≤ 120 chars shown (client limit 2026-02) | your name | ServerInfo; colour codes `^1`–`^9` allowed |
| `sv_projectName` | sets | — | ≤ 40 chars | community name | Not registered in source; read by server list UI |
| `sv_projectDesc` | sets | — | ≤ 250 chars | one sentence | Same |
| `sv_maxclients` | set | `30` | 1–2048 | your slots | ServerInfo. >48 needs Element Club tier |
| `sv_licenseKey` | set | — | `cfxk_…` | in `secrets.cfg` | Startup only; key from portal.cfx.re |
| `sv_enforceGameBuild` | set | mandated default (`3258` in source) | build number or alias (`mp2026_01` = 3889) | `3889` | Startup only. Enh: only latest or `1` |
| `gamename` | set (+set) | `gta5` | `gta5`, `rdr3`; Cfx Server (Enhanced) reports `gta5enhanced` (per esx_lib) | — | Startup only |
| `sv_lan` | set | `false` | bool | `false` | Skips ticket/license checks; not listed |
| `sv_master1` | set | Cfx ingress URL | URL or `""` | leave default | `""` → private (docs: disables join from browser; source: no listing heartbeat) |
| `sv_master2`, `sv_master3` | set | `""` | URL | — | Extra heartbeat targets |
| `sv_endpoints` | set | `""` | space-separated `ip[:port]` | only behind proxies | UDP endpoints given to clients |
| `sv_listingIpOverride` | set | `""` | IP | multi-IP hosts | Sent to master |
| `sv_listingHostOverride` | set | `""` | host | with proxies | Required by `sv_forceIndirectListing` |
| `sv_forceIndirectListing` | set | `false` | bool | `true` behind proxy | Don't advertise real IP |
| `sv_registerMulticastDns` | set | `true` | bool | `false` on public hosts | mDNS LAN discovery |
| `steam_webApiKey` | set | `""` | key | only if using `steam:` ids | Secret |
| `steam_webApiDomain` | set | `api.steampowered.com` | host | default | — |
| `sv_enforceSteamAuth` | set | `false` | bool | `false` | ServerInfo; **new 2026-01** (Steam auth optional by default) |
| `sv_tebexSecret` | set | `""` | key | in `secrets.cfg` | Tebex integration |
| `sv_kvsName` | set | `default` | name | default | KVP DB folder; startup |
| `rcon_password` | set | `""` (RCON off) | string | leave unset | ReadOnly; UDP RCON, plaintext |
| `sv_playersToken` | set | `""` | token | set if you use `/players.json` privately | Gates private player data (header `X-Players-Token` or `?token=`); without it `/players.json` returns placeholder entries (id 0, name "Player") — only the count is real |
| `sv_profileDataToken` | set | `""` | token | set if exposing profiler | Protects `/profileData.json` |
| `resources_useSystemChat` | +set | `true` (since 2026-09-04) | bool | `true` | Use system_resources `chat`; startup only |
| `sv_defaultGameBuild` | — | mandated | — | — | Internal (2026-06) |
| `sv_fxdkMode` | — | — | `1` in FxDK | — | Read-only signal for FxDK |
| `load_server_icon` | command | — | 96×96 PNG | yes | Fills internal `sv_icon` |

## 4. Security and anti-cheat convars
| Convar | Cmd | Default | Values | Production | Notes |
|---|---|---|---|---|---|
| `sv_scriptHookAllowed` | set | `false` | bool | `false` | ServerInfo |
| `sv_pureLevel` | set | `0` | 0 off, 1 block modified files except audio/known graphics mods, 2 block all mods/ASI | `1` (2 for competitive) | ServerInfo; clients restart to switch; Enh: always on |
| `sv_authMinTrust` | set | `1` | 1–5 | default | Min trust of identity providers |
| `sv_authMaxVariance` | set | `5` | 1–5 | default | Max identifier variance |
| `sv_requestParanoia` | set | `0` | 0 off; 1 block `Via` header; 2 + block `Upgrade-Insecure-Requests` (browsers get "Nope." on json endpoints); 3 + close socket | `1` behind no proxy | Anti HTTP-flood |
| `sv_enableNetworkedSounds` | set | `true` | bool | `false` if unused | Blocks `NETWORK_PLAY_SOUND_EVENT` routing |
| `sv_enableNetworkedPhoneExplosions` | set | `false` | bool | `false` | `REQUEST_PHONE_EXPLOSION_EVENT` |
| `sv_enableNetworkedScriptEntityStates` | set | `true` | bool | `false` if unused | `SCRIPT_ENTITY_STATE_CHANGE_EVENT` |
| `sv_filterRequestControl` | set | `0` | -1 (=2 + warn), 0 off, 1 settled player entities, 2 player entities, 3 = 2 + settled non-player, 4 never route | `2` | See onesync-entities.md §8 |
| `sv_filterRequestControlSettleTimer` | set | `30000` | ms | default | For modes 1 and 3 |
| `sv_entityLockdown` | set | `inactive` | `inactive`/`relaxed`/`strict`; Legacy source also `no_dummy`; Enh `full` | `relaxed` (or `strict` w/o ambient pop) | `strict` blocks ambient population too |
| `sv_stateBagStrictMode` | **setr** | `false` | bool | `true` | Server ≥ 12739. Only server writes state bags |
| `sv_protectServerEntities` | **setr** | `false` | bool | `true` (Legacy) | Added 2025-03; clients can't delete server entities. No effect on Enh |
| `sv_httpFileServerProxyOnly` | set | `false` | bool | `true` with file proxy | Only `sv_proxyIPRanges` may fetch `/files` |
| `sv_disableClientReplays` | set | — | bool | optional | Docs only (anti-cheat, closed source); disables Rockstar Editor |
| `sv_kick_players_cnl_timeout_sec`, `sv_kick_players_cnl_update_rate_sec`, `sv_kick_players_cnl_consecutive_failures`, `sv_pure_verify_client_settings` | set | on by default since 8450 | — | don't touch | Docs only (adhesive, closed source) |
| `adhesive_cdnKey` | set | — | secret | with caching proxy | Global file obfuscation key (proxy guide) |
| `sv_prometheusBasicAuthUser` / `sv_prometheusBasicAuthPassword` | set | `""` | strings | set both if `/perf` reachable | Also passed to txAdmin |

## 5. OneSync / game state convars
| Convar | Cmd | Default | Production | Notes / status |
|---|---|---|---|---|
| `onesync` | — | `on` | don't set | **Internal since 2026-08-16** (commit 19fa3d5); `off`/`legacy` impossible |
| `onesync_enabled` | — | `true` (auto) | don't set | Internal alias |
| `onesync_enableInfinity` / `onesync_enableBeyond` | — | `true` | don't set | Internal |
| `onesync_population` | set (startup) | `true` | `true` unless no NPCs wanted | ReadOnly |
| `onesync_distanceCulling` | set | `true` | `true` | — |
| `onesync_distanceCullVehicles` | set | `false` | optional | — |
| `onesync_forceMigration` | set | `true` | `true` | — |
| `onesync_radiusFrequency` | set | `true` | `true` | — |
| `onesync_automaticResend` | set | `false` | `false` | Legacy only; removed on Enh |
| `onesync_logFile` | set | `""` | empty | Debug log; huge files |
| `onesync_workaround763185` | set | `false` | `false` | Legacy workaround |
| `sv_useAccurateSends` | set | `true` | `true` (Legacy) | Deprecated on Enh (`sv_syncTickRate`) |
| `increase_pool_size` | command | — | only when needed | Startup only; limits in onesync-entities.md §13 |

## 6. Network, HTTP and proxy convars
| Convar | Cmd | Default | Production | Notes |
|---|---|---|---|---|
| `endpoint_add_tcp` / `endpoint_add_udp` | command | — | `"0.0.0.0:30120"` | Enh: one endpoint each |
| `netPort` | — | primary port | — | Read-out of primary port |
| `net_tcpConnLimit` | set | `16` (docs) | 16–32 | Concurrent TCP per IP |
| `sv_tcpConnectionTimeoutSeconds` | set | `5` | default | Idle TCP timeout |
| `sv_httpHandlerConnectionTimeoutSeconds` | set | `300` | default | HTTP handler timeout |
| `sv_proxyIPRanges` | set | `10.0.0.0/8 127.0.0.0/8 192.168.0.0/16 172.16.0.0/12` | your proxy CIDRs only | Trusted for X-Real-IP; bypass rate limits |
| `sv_threadedClientHttp` | set | `true` | default | `/client` on own thread |
| `sv_maxClientEndpointRequestSize` | set | `102400` | default | `/client` body limit |
| `sv_enableGetStatus` | set | `false` | `false` | UDP `getstatus` reply |
| `sv_returnClientsListInGetStatus` | set | `true` | — | Player list in getstatus |
| `sv_enableNetEventReassembly` | set | `true` | `true` | Latent/large events |
| `sv_netEventReassemblyMaxPendingEvents` | set | `100` | default | 0–254 |
| `sv_netEventReassemblyUnlimitedPendingEvents` | set | `false` | `false` | — |
| `netlib` | +set | `enet` | — | Ignored (ENet only) |
| `con_disableNonTTYReads` | set | `false` | `true` under systemd without TTY | Stops reading stdin |
| `sv_netHttp2` | set | `false` | `false` | Removed on Enh |
| `fileserver_add` / `fileserver_remove` / `fileserver_list` | command | — | with CDN proxy | `fileserver_add ".*" "https://host/files"` |

## 7. Rate limiters
`set rateLimiter_<key>_rate <tokens/s>` and `set rateLimiter_<key>_burst <max>` (token bucket, per client/IP). Defaults from source (Legacy) — same values in the Enhanced docs table:

| Key | Rate / burst | Key | Rate / burst |
|---|---|---|---|
| `netEvent` | 50 / 200 | `stateBag` | 75 / 125 |
| `netEventFlood` | 75 / 300 | `stateBagFlood` | 150 / 175 |
| `netEventSize` | 131072 / 393216 B | `stateBagSize` | 131072 / 262144 B |
| `netCommand` | 7 / 14 | `latentEvent` (2026-04) | 75 / 125 |
| `netCommandFlood` | 25 / 45 | `latentEventFlood` | 150 / 175 |
| `netCommandSize` | 1024 / 8192 B | `arrayUpdate` | 75 / 125 |
| `http_info` / `http_players` | 4 / 10 | `http_perf` | 2 / 5 |
| `http_<resourceName>` | 10 / 25 | `rcon` | 0.2 / 5 (Enh docs: 2 / 5) |
| `getinfo` / `getstatus` | 2 / 10, 1 / 5 | Enh also: `challenge`, `handshake` 4/10, `handshakeUDP` 1/5, `http_dynamic` 4/10, `res_http_handler` 10/25, `resourceList` 10/25 | |
Raise a limit only when the console names it for legitimate traffic (e.g. big inventories syncing state bags); a client exceeding the flood limit is dropped.

## 8. Enhanced-only convars (Cfx Server, docs)
`sv_syncTickRate` (60, 1–120) · `sv_resourceFileDownloadTimeout` (2 min) · `sv_ioThreads` (0 = auto 2–4, startup) · `sv_clientConnectingTimeoutMilliseconds` (60000) · `sv_clientConnectedTimeoutMilliseconds` (120000) · `sv_pingIntervalMilliseconds` (5000) · `sv_voiceChat` (false) · `sv_mumble` (false, setr, deprecated) · `sv_devMode` (false; max 8 slots) · `onesync_migrateDataTimeout` (10000) · `onesync_compressionDictionarySamples` (false) · `onesync_mapBoundsMinX/MinY` (-10000) · `onesync_mapBoundsMaxX/MaxY` (65536) · `onesync_mapCellAreaSize` (100) · commands `voice_internal`, `voice_external_connect`, `voice_external_host`, `sync_start_recording`, `sync_stop_recording`, `replay_start`, `replay_stop`. Details: [gta5-enhanced.md](gta5-enhanced.md). Also (early access, see gta5-enhanced.md 5b): `sv_disconnectOnUnhandledNetEvent` (false) · `onesync_maxNearbyVehicles/Peds/Objects/Players/Other` (~256/256/512, defaults are the maximums) · `onesync_multithreadedPacketProcessing` (true) · `sv_enableCoreclrSandboxing` (dev mode only). None of these exist in the public Legacy source.

## 9. Server-list `sets` keys and common resource convars
| Key | Example | Notes |
|---|---|---|
| `sets tags` | `"roleplay, serious"` | Comma-separated |
| `sets locale` | `"es-ES"` | Real locale (not `root-AQ`) |
| `sets banner_detail` / `sets banner_connecting` | image URL | Server page / connect screen |
| `sets Discord` (any key) | URL | Shown on server page |
| `sets sv_appearAllowlisted` | `true` | Padlock in browser (2026-05); txAdmin sets it from allowlist mode |
| `sets sv_allowlistInstructions` | text | How to get allowlisted; needs the above |
| `setr sv_showBusySpinnerOnLoadingScreen` | `false` | Hide spinner on custom loading screens |
| `set mysql_connection_string` | `mysql://…` | oxmysql; secret |
| `set mysql_slow_query_warning` | `150` | oxmysql (ms) |
| `set mysql_debug` | `false` | oxmysql |
| `setr ox:locale` | `"es"` | ox_lib locale (replicated) |
| `txAdmin-*` | — | See [txadmin.md](txadmin.md) §10 |
Resource-specific convar names: always take them from the resource docs; never put secrets in `setr`/`sets`.

## 10. Removed / deprecated / internal (2025–2026 changes)
| Date | Change | Commit |
|---|---|---|
| 2025-01-27 | **Added** `sv_stateBagStrictMode` | 49943778 |
| 2025-02-10 | `sv_replaceExeToSwitchBuilds` default → `false` | 3850efdc |
| 2025-03-16 | **Added** `sv_protectServerEntities` | d6842fe2 |
| 2025-06-23/26 | **Added** `block_net_game_event` / `unblock_net_game_event` (by name) | 9b41a98a / 3f3fa551 |
| 2025-06-24 | Lua 5.3 runtime removed (Lua 5.4.8 only) | a2a71bd1 |
| 2026-01-21 | **Added** `sv_enforceSteamAuth` (Steam auth optional) | 89a6bc71 |
| 2026-02-17 | Node 16 removed; **added** `add_unsafe_worker_permission`, `add_unsafe_child_process_permission` | 6eeab32f / a6a85cbd |
| 2026-04-14 | **Removed** `sv_experimentalStateBagsHandler`, `sv_experimentalOneSyncPopulation`, `sv_experimentalNetGameEventHandler`, `sv_experimentalNetEventReassemblyHandler` (always on) | 65d353d7 |
| 2026-04-28 | **Added** `rateLimiter_latentEvent*` | ae540b0c |
| 2026-06 | **Added** internal `sv_defaultGameBuild`; `sv_replaceExeToSwitchBuilds` → internal (fully deprecated with 35245, 2026-08-20) | 4d8287db / 7e2e16fa |
| 2026-06-24 | Nucleus (`*.users.cfx.re`) removed; `web_baseUrl` mocked | 9443acab |
| 2026-07-08 | **Removed** (warn-only) `sv_endpointPrivacy`, `sv_exposePlayerIdentifiersInHttpEndpoint` — player IPs/identifiers never exposed on HTTP endpoints | d52296e0 |
| 2026-08-16 | **OneSync forced**: `onesync` internal `on`; `onesync_enableInfinity/Beyond` internal | 19fa3d5b |
| 2026-09-04 | `sessionmanager` no longer auto-started; `resources_useSystemChat` → `true` | 18fca04f / a320ef07 |
Docs still list the removed `sv_experimental*` (default true) and describe `sv_endpointPrivacy`/`sv_replaceExeToSwitchBuilds` as active — they are stale. Also stale: `onesync [on/off/legacy]`. No-op everywhere: `sv_enhancedHostSupport`. Enhanced removes `sv_netHttp2`, `onesync_automaticResend`, `svgui`, `+set moo 31337`; `onesync_enableBeyond`/`sv_protectServerEntities` are no-ops there.

## 11. Server console commands
| Command | Args | Purpose |
|---|---|---|
| `start` / `stop` / `restart` / `ensure` | `<resource>` or `[category]` | Resource control (`ensure` = restart if running, else start) |
| `refresh` | — | Rescan `resources/` |
| `exec` | `<file.cfg>` or `@resource/file.cfg` | Run a cfg |
| `quit` | `[reason]` | Stop server (kicks with reason) |
| `open` | `<resource>` | Open resource folder (Windows) |
| `status` | — | Player list (from `rconlog` resource) |
| `clientkick` | `<id> <reason>` | Kick (from `rconlog`) |
| `say` | `<message>` | Chat as console (from `chat`) |
| `heartbeat` | — | Force server-list heartbeat |
| `load_server_icon` | `<file.png>` | 96×96 icon |
| `increase_pool_size` | `<pool> <n>` | Startup only |
| `endpoint_add_tcp` / `endpoint_add_udp` | `"ip:port"` | Listeners |
| `fileserver_add` / `fileserver_remove` / `fileserver_list` | `<pattern> <url>` | External file servers |
| `block_net_game_event` / `unblock_net_game_event` | `<EVENT_NAME>` | Drop game events server-wide |
| `onesync_clearArea` | `x1 y1 x2 y2` | Delete entities in an area |
| `onesync_showObjectIds` | — | Object id usage |
| `force_enet_disconnect` | `<netId>` | Drop a peer at network level |
| `profiler` | `record <frames\|seconds>`, `status`, `resource <name>`, `save <file>`, `saveJSON <file>`, `dump`, `view [file]` | Script profiler (Enh: Perfetto JSON) |
| `con_addChannelFilter` / `con_removeChannelFilter` | `<regex> <noprint\|drop\|devonly>` | Console filters |
| `con_channelFilters` | — | List filters |
| `cmdlist` | — | List commands |
| `wait` | `<ms>` | Delay in cfg scripts |
| `toggle`, `vstr` | — | Convar helpers |
| `set` / `setr` / `sets` / `seta` | `<name> <value>` | Convars |
| `svgui` | — | Windows server GUI (Legacy; removed on Enh) |
| `_crash` | — | Deliberate crash (debug; never in prod) |
| `rcon_password` | convar | Enables UDP RCON (prefer txAdmin console) |
Enhanced extra: `sync_start_recording`, `sync_stop_recording`, `replay_start`, `replay_stop`, `voice_internal`, `voice_external_*`. Resources add their own (`RegisterCommand`). txAdmin adds `/tx` in game and its own panel commands.

## 12. Access-control (ACE) and sandbox commands
| Command | Example |
|---|---|
| `add_ace <principal> <object> <allow\|deny>` | `add_ace group.admin command allow` |
| `remove_ace <principal> <object> <allow\|deny>` | `remove_ace group.mod command.kick allow` |
| `add_principal <child> <parent>` | `add_principal identifier.fivem:123 group.admin` |
| `remove_principal <child> <parent>` | — |
| `test_ace <principal> <object>` | `test_ace group.admin command.quit` |
| `list_aces` / `list_principals` | — |
| `set se_debug true` | Log every ACE check (debug) |
| `add_convar_permission <resource> <read\|write> <convar>` | Startup only; once set, only listed resources can access the convar |
| `add_filesystem_permission <resA> write <resB>` | Cross-resource writes |
| `add_unsafe_worker_permission <resource>` | Node workers |
| `add_unsafe_child_process_permission <resource>` | Node child processes |
- `add_ace` / `remove_ace` / `add_principal` / `remove_principal` refuse to modify the principal that is currently executing them ("Changing ones own access is not permitted."); a resource cannot self-grant through its own `resource.<name>` principal. `ExecuteCommand('set ...')` from a resource needs `add_ace resource.<res> command.set allow`.
Concepts and examples: [server-ops.md](server-ops.md) §6–7.

## 13. Sources
- https://docs.fivem.net/docs/server-manual/server-commands/ · https://docs.fivem.net/docs/scripting-reference/convars/ · https://docs.fivem.net/docs/developers/sandbox/ · https://docs.fivem.net/docs/developers/server-security/ · https://docs.fivem.net/docs/server-manual/proxy-setup/ · https://docs.fivem.net/docs/developers/legacy-vs-enhanced/ (via https://github.com/citizenfx/fivem-docs, commit c2b2125)
- Source (master a74c2cc): https://github.com/citizenfx/fivem/blob/master/code/client/citicore/console/Console.Variables.h · …/code/components/citizen-server-impl/src/GameServer.cpp · …/InfoHttpHandler.cpp · …/InitConnectMethod.cpp · …/state/ServerGameState.cpp · …/ServerResourceList.cpp · …/packethandlers/StateBagPacketHandler.cpp · …/packethandlers/ServerEventPacketHandler.cpp · …/citizen-server-net/src/TcpListenManager.cpp · …/citizen-server-net/src/ProxyAddressList.cpp · …/citizen-server-main/src/ServerInstance.cpp · …/citizen-scripting-core/src/ConsoleScriptFunctions.cpp · …/citizen-scripting-core/src/Profiler.cpp · …/client/citicore/se/Security.cpp
- Commits: https://github.com/citizenfx/fivem/commit/19fa3d5bcf69 (force OneSync) and the SHAs in §10
- Forum: https://forum.cfx.re/t/90917 (ACE guide) · https://forum.cfx.re/t/5377566 (listing limits) · https://forum.cfx.re/t/5405819 (allowlist convars) · https://forum.cfx.re/t/5422124 (35245, exe switching) · https://forum.cfx.re/t/5335232 (Lua 5.3 removal)
