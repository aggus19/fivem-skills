# FiveM for GTA V Enhanced (Cfx Server)

Baseline: Cfx Server **build 161** (early access since **2026-07-21**), game build 3889 (The Kortz Center Heist), txAdmin 8.1.1 embedded; Legacy FXServer Recommended 35245 / Latest 37150 — verified 2026-10-07.

## Contents
1. What it is and status
2. Should a server move now?
3. Installing Cfx Server
4. Everything that differs (table)
5. Enhanced-only convars and commands (5b early-access changes, 5c known open issues)
6. Voice (new VoIP, Mumble compatibility)
7. Developer mode and dev tools
8. Assets: `stream_enhanced` and Alchemist
9. Runtimes: .NET 10, Node 26, V8 14.6
10. Writing dual-edition resources
11. Migration plan (Legacy → Enhanced)
12. Compatibility checklist for a resource
13. Sources

## 1. What it is and status
- A second FiveM platform on GTA V **Enhanced** (the 2025 PC edition, "Gen9"), with a separate client launcher ("Download FiveM for GTAV Enhanced" on fivem.net) and a new server binary **Cfx Server**. Legacy (GTA V Legacy/"Gen8", FXServer) remains supported; the long-term goal is one combined server list.
- Early access "will contain bugs and missing features". Asset Escrow is **not available** yet → most production servers using escrowed (Tebex) assets cannot move yet. Cfx.re ran public stress tests (2026-08-14, 2026-09-04).
- Some parts of the Enhanced codebase are **closed source** (Dev Update #1) — you can't always read the source for behaviour.
- Bug reports/feedback: GitHub Discussions in https://github.com/citizenfx/rfc.
- Edition is chosen by **which server binary you run**; no manifest key or convar switches it. Clients use the matching launcher.

## 2. Should a server move now?
| Situation | Recommendation |
|---|---|
| Production RP server with escrowed assets (MLOs, scripts) | Stay on Legacy; plan and test in staging. |
| Open-source stack only (ox/Qbox/ESX + own scripts), no escrow | Staging server on Enhanced now; move when stable for your players. |
| New project / PvP / high-pop where tick rate matters | Consider Enhanced (60–120 Hz sync), accept early-access risk. |
| Heavy custom C# (Mono-specific code) | Test on .NET 10 first. |

## 3. Installing Cfx Server
- Download: https://docs.fivem.net/docs/server-download/ → select "FiveM for GTAV Enhanced". Files: Windows `cfx-server_win_x64` (instead of `server.7z`), Linux `cfx-server-linux_x64` (instead of `fx.tar.xz`); executable `cfx-server.exe` (instead of `FXServer.exe`).
- Windows prerequisite: **Microsoft Visual C++ 2017 Redistributable (x64)** (https://aka.ms/vs/17/release/vc_redist.x64.exe).
- Linux builds still use the Alpine rootfs (same requirements as Legacy). An official Docker image is planned (**UNVERIFIED** availability).
- txAdmin is embedded and works the same (run the binary without `+exec`); recipes index `indexv5.json` has Enhanced variants (e.g. "Basic FiveM (enhanced)").
- The official `default-fivem-enhanced` recipe ships only mapmanager, spawnmanager, basic-gamemode and two maps. Its cfg has no `sv_enforceGameBuild`, onesync, chat, hardcap or sessionmanager (https://github.com/citizenfx/txAdmin-recipes/tree/main/default-fivem-enhanced).
- Same `server.cfg` structure, same license key (portal.cfx.re). `endpoint_add_tcp`/`endpoint_add_udp` accept **one** endpoint each.
- New handshake: no UDP until connected, deferrals over WebSocket — DDoS filters/firewall rules tuned for Legacy must be re-checked.
- Ports: game 30120 (tcp/udp), txAdmin 40120, client remote console (DevCon) 29200 (off by default), voice external server ports if used (§6).

## 4. Everything that differs (table)
| Area | Legacy (FXServer) | Enhanced (Cfx Server) |
|---|---|---|
| Server binary | `FXServer.exe` / `run.sh` | `cfx-server.exe` / Linux equivalent |
| Game build | `sv_enforceGameBuild` any listed build | Only latest (3889) by default, or `1` (no DLC) |
| OneSync | forced on | "big" mode only; P2P sync removed |
| Sync transport | ENet | raw UDP for sync frames (ENet for events) |
| Sync tick rate | ~30 Hz (`sv_useAccurateSends` → 40) | `sv_syncTickRate` 1–120, default 60; `sv_useAccurateSends` deprecated |
| Culling | single thread (~16 players/tick) | multi-core in sync pipeline |
| Player server ids | increment, wrap at 65535 | **reused** after disconnect; staff: "we will only reuse them up to 4k" (https://github.com/citizenfx/rfc/discussions/136); the 2026-08-31 patch made reuse less likely. Never key data by server id |
| Other players' join/leave | always | only when in range |
| Entity lockdown | inactive/relaxed/strict | + `full` (no dummy objects); `relaxed` population only in owned grid cells |
| `sv_protectServerEntities` | — | not implemented (use lockdown) |
| State bags | handlers may fire before entity exists; all values replicated | only when entity exists; only explicitly replicated values sent; ~10× faster sets; **max 32 KB per value**, keys <= 1024 chars (2026-09-30) |
| Pure mode | `sv_pureLevel` 0/1/2 | always on; graphics mods not allowed in early access |
| Dev tools | `+set moo 31337` / `developer` | `sv_devMode true` (8 slots max) or per-player via `deferrals.handover` |
| Voice | Mumble | new VoIP; Mumble natives via `setr sv_mumble true` (deprecated) |
| C# | Mono (CitizenFX.Core; `mono_rt2` expired 2026-06-30) | **.NET 10** (old API kept) |
| Server JS / client JS | Node 22 / CEF V8 | **Node 26** / V8 14.6.202 |
| Profiler | legacy profiler | Perfetto backend, same `profiler record/save` commands |
| Metrics (`/perf`) | 3 tick histograms | 80+ Prometheus metrics (`sv_prometheusBasicAuthUser/Password`) |
| KVP | `sv_kvsName` DB | files **must be migrated** with the official tool https://github.com/citizenfx/kvdb-migrator (v1.0.0, 2026-07-21; input = Legacy `db/<sv_kvsName>` folder). Since 2026-08-31 KVP DBs are no longer keyed by server URL (survive IP/proxy changes). |
| Remote commands | full log returned | call `PrintRemoteCommandLog(message)` to return output |
| Commands | — | `UnregisterCommand(id)` (`RegisterCommand` returns an id) |
| Resource builders | allowed | not allowed |
| Server ImGui (`svgui`) | yes | removed |
| `sv_netHttp2`, `onesync_automaticResend` | exist | removed |
| `onesync_enableBeyond`, `sv_enhancedHostSupport` | — | no effect |
| `-cl2` second client | yes | removed; use dev menu "Launch Additional Client" (needs `sv_devMode`) |
| Asset Escrow | yes | not yet |
| Streaming | `stream/` | `stream_enhanced/` preferred (falls back to `stream/`, deprecated) |
| Client cache | grows forever | files no longer served are cleaned automatically |
| RAM per player/entity | — | up to ~50 % lower |

`UnregisterCommand` and `PrintRemoteCommandLog` are documented on the legacy-vs-enhanced page but are **not** in the natives DB used by `scripts/natives.py` (Enhanced-only).

## 5. Enhanced-only convars and commands
| Name | Default | Notes |
|---|---|---|
| `sv_syncTickRate` | `60` | 1–120. Higher = lower latency, more CPU/bandwidth. 60 for RP, up to 120 for PvP after load testing. |
| `sv_resourceFileDownloadTimeout` | 2 min (ms) | HTTP resource download timeout. |
| `sv_ioThreads` | `0` (auto: cores, clamped 2–4) | Startup only. |
| `sv_clientConnectingTimeoutMilliseconds` | `60000` | Time to finish connecting. |
| `sv_clientConnectedTimeoutMilliseconds` | `120000` | Silence before drop. |
| `sv_pingIntervalMilliseconds` | `5000` | Keep-alive interval. |
| `sv_voiceChat` | `false` | Voice chat on/off (see §6). |
| `sv_mumble` | `false` | Legacy Mumble API compatibility (`setr`); insecure, deprecated. |
| `sv_devMode` | `false` | Dev mode for all clients; max 8 slots. Never in production. |
| `onesync_migrateDataTimeout` | `10000` | Force migration if owner stops syncing. |
| `onesync_mapBoundsMinX/MinY/MaxX/MaxY` | `-10000/-10000/65536/65536` | Startup only. |
| `onesync_mapCellAreaSize` | `100` | World-grid cell size; startup only. |
| `onesync_compressionDictionarySamples` | `false` | Internal. |
| `rateLimiter_<name>_rate` / `_burst` | see table in [convars-and-commands.md](convars-and-commands.md) | Token buckets: `netEvent` 50/200, `stateBag` 75/125, `rcon` 2/5... |
| `sync_start_recording <netId> [compressed]`, `sync_stop_recording <netId>` | — | Record an entity's sync to a file. |
| `replay_start <file> <0 once|1 loop|2 perfect loop>`, `replay_stop <id>` | — | Replay recordings. |
| `voice_internal` | — | Enable built-in voice server (command in server.cfg). |
| `voice_external_connect` / `voice_external_host` | — | External voice server (experimental). |
Client-only Enhanced convars (F8): `cl_drawResTimeGraphs`, `cl_drawResTimeWarnings`, `con_poolInspector`, `con_streamingMonitor`, `netobjlabeling`, `game_enableAdvancedPopulation`, `game_setDefaultEntityCapLimitToLow`, `voice_enableEchoCancellation`, `voice_enableVoiceNormalization`.

### 5b. Early-access behaviour changes (patch notes, citizenfx/rfc)
- Protocol bumps (2026-08-31, 09-22, 09-30): an outdated cfx-server gives clients handshake/connection errors; update cfx-server first when "nobody can connect" after a Cfx patch.
- Client start events (08-31, #474): match Legacy. `onClientResourceStart` fires for every resource; `onResourceStarting`/`onResourceStart` fire only on restart. Threads created during load get their first tick after `onClientResourceStart` (09-24, #545).
- State bags (09-30, #564): max **32 KB per value** (was 256 KB), keys <= 1024 chars; warnings above 256-char keys or 1 KB values.
- `sv_disconnectOnUnhandledNetEvent` (09-22, #530, default off): disconnects clients that send a reliable net event with no handler.
- Rate limiters: new `netGameEvent` / `netGameEventFlood` (09-30); script event limit relaxed to ~75/s (09-24). Tune with `rateLimiter_<name>_rate|_burst`.
- `onesync_maxNearbyVehicles|Peds|Objects|Players|Other` (08-04, #360): priority streaming caps ~256 / 256 / 512 objects. The defaults are also the maximums ("Value out of range"; intentional per staff, #368).
- `onesync_multithreadedPacketProcessing` (default true, 09-30): parallel sync; `set onesync_multithreadedPacketProcessing false` to disable.
- `sv_entityLockdown no_dummy` accepted again (08-31), also for routing buckets.
- Pools auto-extend (08-31/09-22): StaticBounds, MapTypesStore, MapDataStore, TxdStore, InteriorProxy, FragmentStore, DrawableStore, MaxExtraVehicleModelInfos, dwdStore. `increase_pool_size` is still ineffective for `CWeaponComponentInfo` (#524).
- New server native `SetPlayerName` (usable from `playerConnecting`) + events `onPlayerNameChanged`, `onPedDeath`, `onPedHealthChanged` (Hotfix 9, #404). Built-in colshape natives exist on Enhanced only (search "Colshape" in the native reference).
- Client needs Microsoft **WebView2** (Hotfix 6, #312).
Patch notes: https://github.com/citizenfx/rfc/discussions/categories/patch-notes

### 5c. Known open issues (2026-10-07; re-check before quoting)
| Issue | Workaround | Thread |
|---|---|---|
| Client freezes at 100 % loading when the server mounts `data_file`s (regression b157, still on b161) | run server b156 | https://github.com/citizenfx/rfc/discussions/567 |
| Custom ped models invisible | none | /543 |
| `SetNuiFocusKeepInput` has no effect | none | /555 |
| Loading screen only gets `loadProgress` (no Legacy granular events/`onLogLine`) | plain 0-100 % bar | /427 |
| `increase_pool_size` ignored for `CWeaponComponentInfo` | keep custom weapon components within free slots | /524 |

## 6. Voice (new VoIP, Mumble compatibility)
- New voice stack (noise/echo cancellation, packet-loss handling). Enable the internal server with `voice_internal` in `server.cfg`; external voice server (experimental): voice host `voice_external_host 0.0.0.0:30123 <gameServerIP>:30122`, game server `voice_external_connect 0.0.0.0:30122 <voiceHostIP>:30123`, same license key on both. Relation between `voice_internal` and `sv_voiceChat` (both documented) is **UNVERIFIED** — set both while testing.
- Mumble natives still work through a compatibility layer only with `setr sv_mumble true` — insecure (any client can join any channel) and voice targets collapse to one. pma-voice relies on Mumble natives: test it with `sv_mumble` and watch for an official migration.
- Removed client convars: `voice_use2dAudio`, `voice_use3dAudio`, `voice_useSendingRangeOnly`, `voice_useNativeAudio` (`voice_inBitrate` still works).
- New **server-side** API (Enhanced; not in natives DB): `CreateVoiceChannel(mode, maxDistance)` (modes 0 non-spatial, 1 spatial, 2 custom, 3 temporary), `DeleteVoiceChannel(id)`, `AddPlayerToVoiceChannel(id, src)`, `RemovePlayerFromVoiceChannel(id, src)`, `SetPlayerMutedInVoiceChannel(id, src, bool)`, `SetPlayerDeafInVoiceChannel(id, src, bool)`.
```lua
-- server.lua (Enhanced only): police radio owned by the server
local radio = CreateVoiceChannel(0, 0.0)

RegisterNetEvent('radio:server:join', function()
    local src = source
    if not IsPlayerAceAllowed(src, 'job.police') then return end
    AddPlayerToVoiceChannel(radio, src)
end)

RegisterNetEvent('radio:server:leave', function()
    RemovePlayerFromVoiceChannel(radio, source)
end)
```

## 7. Developer mode and dev tools
- Client dev tools (resource monitor graphs, pool inspector, NUI devtools, extra client) are only available on servers with dev mode.
- Whole server: `set sv_devMode true` → every joining client gets dev mode; `sv_maxclients` capped at **8**. Replaces `+set moo 31337` (removed).
- Per player in production: grant inside `deferrals.handover` during `playerConnecting` (exact handover key **UNVERIFIED** — check docs.fivem.net/docs/developers/legacy-vs-enhanced/ when it's documented).
- Profiling: `profiler record <seconds>` then `profiler save <name>.json`, open in https://ui.perfetto.dev.
- Second local client: F8 → Debug → "Launch Additional Client" (needs `sv_devMode true`).

## 8. Assets: `stream_enhanced` and Alchemist
- Resources can ship `stream_enhanced/` next to `stream/`. On Enhanced, if `stream_enhanced/` exists it is loaded **instead of** `stream/`; otherwise `stream/` is used (deprecated on Enhanced). Legacy ignores `stream_enhanced/`. One resource can therefore serve both editions.
- **Alchemist** (download from https://portal.cfx.re/downloads; Windows 11): converts Legacy (Gen8) assets to Enhanced (Gen9), or *refines* Legacy assets. Types: YDR, YTD, YFT, YPT, YDD.
  - GUI: choose *Asset Conversion* / *Asset Refinement*, input and output folders; pointing it at your `resources/` folder produces a drop-in Enhanced resources folder. *Relaxed mode* skips some validations (output may differ slightly).
  - CLI: `AlchemistCli.exe <input> <output> [--refine] [--relaxed] [-f] [-jN] [--fail-on-error]` (default 10 threads). The GUI stops on escrowed assets; the CLI skips and reports them.
- Escrowed assets: Enhanced versions are to be downloaded from the Cfx Portal once escrow ships (not yet).
- Sollumz (Blender add-on) uses the Alchemist library to export Enhanced assets (https://forum.cfx.re/t/5367428).
- Gen9 limits (Sollumz wiki, community-verified): max **128 materials/geometries** per drawable (more = client crash on approach); `script_rt_*` textures must be uncompressed `D3DFMT_A8R8G8B8` (DXT5/BC3 = `ERR_GFX_STATE` crash when entering the vehicle). https://github.com/Sollumz/wiki/blob/main/tutorials/asset-conversion-for-gtav-enhanced.md
- Alchemist copies non-model files (scripts, NUI, configs, `.ymap`/`.ytyp`/meta) unaltered; whether specific map/meta files need manual changes on Enhanced is **UNVERIFIED** — test them.

## 9. Runtimes: .NET 10, Node 26, V8 14.6
- **Lua**: CfxLua 5.4 on both editions; no changes needed for typical scripts.
- **C#**: .NET 10 replaces Mono; old API kept for compatibility plus a new API/NuGet package. Requirement: .NET 10 SDK to build. Remove Mono-only APIs and test reflection/`System.*` usage.
  Sandbox: dev-only escape `sv_devMode 1` + `sv_enableCoreclrSandboxing 0`; whitelisted NuGets include Microsoft.Extensions.Logging.Abstractions, Microsoft.Extensions.DependencyInjection, Microsoft.EntityFrameworkCore, Npgsql; Legacy `CitizenFX.Core.*` NuGets load; the new module adds a StateBag API, `API.EveryTick`, `[OnTick]`, ColShape API (C# patch 2026-08-20, https://github.com/citizenfx/rfc/discussions/439). Open bug: cancelling a pending HTTP/WebSocket op crashes the server (`CancelIoEx` not implemented, #572); avoid cancellation tokens on HTTP calls for now.
- **JS**: server Node 26 (Legacy Node 22), client V8 14.6.202. Avoid Node APIs removed between 22 and 26; keep builds targeting ES2022 to run on both.
- **NUI**: different CEF build than Legacy's CEF 103 (version not published) — test UIs in both clients.

## 10. Writing dual-edition resources
```lua
-- shared/edition.lua (client side)
Edition = {}
Edition.isEnhanced = IsGameEnhancedVersion()   -- client native, verified; false on Legacy
```
```lua
-- server side: Cfx Server reports gamename = 'gta5enhanced' (esx_lib also accepts 'gta5_enhanced')
local isEnhanced = ({ gta5enhanced = true, gta5_enhanced = true })[GetConvar('gamename', 'gta5')] == true
-- client side (guard for old Legacy builds that lack the native):
-- local isEnhanced = type(IsGameEnhancedVersion) == 'function' and IsGameEnhancedVersion()
```
Source: esx_lib `imports/isEnhanced/shared.lua` (https://github.com/esx-framework/esx_core/blob/main/%5Bcore%5D/esx_lib/imports/isEnhanced/shared.lua). The `gamename` value is not documented by Cfx: verify on your build.
Rules that work on both:
- Manifest for dual-edition resources: `games { 'gta5', 'gta5enhanced' }` (used by Cfx's own map resources, cfx-server-data commit e265cb2, 2026-07-20; not on docs.fivem.net). `game 'gta5'`-only resources still load on Enhanced (the official Enhanced recipe ships spawnmanager/mapmanager).
- Never key data by server id (ids are reused on Enhanced); use `license`/citizen id.
- State bag handlers: tolerate `GetEntityFromStateBagName(bag) == 0`; always pass `replicated = true` when clients need the value.
- Spawn entities server-side; work with `strict` lockdown.
- Ship assets in `stream/` (Legacy) and `stream_enhanced/` (converted with Alchemist).
- No reliance on `svgui`, `sv_netHttp2`, Mumble-only features, resource builders, or KVP file layout.
- Remote command handlers: call `PrintRemoteCommandLog` when available:
```lua
local function reply(msg)
    if PrintRemoteCommandLog then PrintRemoteCommandLog(msg) else print(msg) end
end
```

## 11. Migration plan (Legacy → Enhanced)
1. **Inventory**: list resources; mark escrowed, C#, JS, voice, streaming-heavy (MLOs, vehicles, clothing), KVP users, NUI.
2. **Blockers**: escrowed assets → wait or replace; Mumble-dependent voice → test pma-voice with `sv_mumble`, plan migration to the server voice API.
3. **Staging box**: install VC++ 2017 redist, Cfx Server, txAdmin with a copy of `server.cfg`; remove `sv_useAccurateSends`, `sv_netHttp2`, `onesync_*` legacy flags; add `sv_syncTickRate 60`.
4. **Assets**: run AlchemistCli on a copy of `resources/` (or per resource into `stream_enhanced/`), keep the report, fix failures (`--relaxed` as last resort).
5. **Code audit**: server-id persistence, state bag handlers, client-side spawning (use `strict`/`full` lockdown), `RegisterCommand` remote output, C# build on .NET 10, JS on Node 26.
6. **KVP**: migrate with `citizenfx/kvdb-migrator` or move data to SQL.
7. **Database**: same MariaDB; no schema change from the edition itself.
8. **Load test**: join with devs (`sv_devMode true`, ≤ 8 slots) → then disable dev mode and run a closed playtest; compare `/perf` metrics and `sv_syncTickRate` 60 vs higher.
9. **Cutover**: announce that players need the Enhanced launcher and GTA V Enhanced; keep the Legacy server available during transition (separate license key/listing).
10. **Monitor**: Prometheus `/perf`, txAdmin; report issues on citizenfx/rfc Discussions.

## 12. Compatibility checklist for a resource
- [ ] No server-id persistence across reconnects.
- [ ] State bag handlers handle missing entities; replicated flags explicit.
- [ ] All networked entities created server-side.
- [ ] No removed convars/commands in docs or config.
- [ ] Assets in `stream_enhanced/` (Alchemist) or edition-specific resource.
- [ ] C# builds on .NET 10; JS runs on Node 22 and 26.
- [ ] NUI tested on both CEF builds.
- [ ] Voice works without client-controlled Mumble channels (or documented `sv_mumble` need).
- [ ] Not escrowed (until Enhanced escrow ships).

## 13. Sources
- https://docs.fivem.net/docs/developers/legacy-vs-enhanced/ (repo file `content/docs/developers/legacy-vs-enhanced.md`, citizenfx/fivem-docs commit c2b2125, 2026-10-01)
- https://docs.fivem.net/docs/server-manual/onboarding-guide-fivem-for-gtav-enhanced/
- https://docs.fivem.net/docs/server-manual/server-commands/ ("Console commands exclusive to FiveM for GTAV Enhanced")
- https://docs.fivem.net/docs/scripting-manual/voice/ (Enhanced voice section)
- https://docs.fivem.net/docs/alchemist/
- https://docs.fivem.net/docs/client-manual/console-commands/ · https://docs.fivem.net/docs/client-manual/running-two-fivem-clients/
- https://docs.fivem.net/docs/server-manual/setting-up-a-server-vanilla/ · https://docs.fivem.net/docs/server-manual/setting-up-a-server-txadmin/ · https://docs.fivem.net/docs/server-download/
- Forum: https://forum.cfx.re/t/5412858 (early access, 2026-07-21), https://forum.cfx.re/t/5415045 (Dev Update #3), https://forum.cfx.re/t/5412576 (Dev Update #2), https://forum.cfx.re/t/5391635 (Dev Update #1), https://forum.cfx.re/t/5420662 (stress tests), https://forum.cfx.re/t/5366795 (Alchemist), https://forum.cfx.re/t/5367428 (Sollumz)
- https://github.com/citizenfx/txAdmin-recipes (`indexv5.json`) · https://github.com/citizenfx/kvdb-migrator · https://github.com/citizenfx/rfc/discussions/categories/patch-notes
