# Ecosystem resources (community scripts used on servers in 2026)

Baseline verified 2026-10-07 with the GitHub API (push dates, releases, licenses) and official docs. "Pushed" = last commit to the default branch. Paid/escrowed resources are described only from their official docs; their export names are not reproduced here unless checked — open the docs link and **never guess paid-resource exports**.

## Contents
1. How to evaluate a resource
2. Voice: pma-voice
3. Screenshots and video: screencapture (screenshot-basic successor)
4. Logs and media: Fivemanage SDK
5. Appearance / clothing
6. Phones and tablets
7. Banking and society money
8. Garages, vehicle keys, fuel
9. Housing
10. Dispatch and MDT
11. HUD
12. Admin menus (txAdmin, vMenu, EasyAdmin, framework menus)
13. Loading screens
14. Anticheat
15. Weather/time, doors, bridges
16. Use vs avoid (summary table)
Sources

## 1. How to evaluate a resource
- Activity: `gh api repos/<owner>/<repo> --jq '.pushed_at, .archived'` and `gh release list -R <owner>/<repo> -L 3`. Archived or no code for 18+ months = avoid for new installs.
- Framework fit: check `fxmanifest.lua` dependencies and the bridge/config (`Config.Framework`, `provide`).
- Security: open-source scripts can be audited (`python scripts/audit.py <res>`); escrowed ones cannot — trust only the official vendor (Tebex/Cfx portal), never "leaks" (often backdoored; see [security.md](security.md), [licensing-and-policy.md](licensing-and-policy.md)).
- Secrets: API keys/webhooks only via server-side `set` convars, never `setr`, client files or NUI.

## 2. Voice: pma-voice
Repo https://github.com/AvarianKnight/pma-voice · MIT · manifest `7.0.1`, latest tag `v7.0.2-rc3` (2025-05-30), pushed 2026-06-17 · `provides` `mumble-voip`, `tokovoip`, `toko-voip`, `tokovoip_script`. Uses FiveM's built-in Mumble — the de-facto standard (SaltyChat/TokoVOIP are legacy TeamSpeak-based).
Client exports: `setRadioChannel(ch)`, `addPlayerToRadio(ch)`, `removePlayerFromRadio()`, `setCallChannel(ch)`, `addPlayerToCall(ch)`, `removePlayerFromCall()`, `setVoiceProperty('radioEnabled'|'micClicks', v)`, `setRadioVolume(0-100)`, `getRadioVolume()`, `setCallVolume`, `toggleMutePlayer(serverId)`, `isPlayerMuted`, `overrideProximityRange(range, disableCycle)`, `clearProximityOverride()`, `setAllowProximityCycleState(bool)`, `addVoiceMode`/`removeVoiceMode`, `registerCustomSubmix`/`setEffectSubmix`, `toggleRadioAnim`, `addRadioDisableBit`/`removeRadioDisableBit`, `setVoiceState`, legacy `SetRadioChannel`/`SetCallChannel`/`SetMumbleProperty`/`SetTokoProperty`.
Server exports: `setPlayerRadio(src, ch)`, `setPlayerCall(src, ch)`, `getPlayersInRadioChannel(ch)`, `addChannelCheck(ch, fn(source) -> bool)`, `removeChannelCheck(ch)`, `overrideRadioNameGetter(ch, fn)`, `isValidPlayer(src)`.
```lua
-- server: only police may join radio 1-10 (clients can request any channel otherwise)
for ch = 1, 10 do
    exports['pma-voice']:addChannelCheck(ch, function(source)
        local player = exports.qbx_core:GetPlayer(source)   -- adapt to your framework
        return player and player.PlayerData.job.type == 'leo' or false
    end)
end
```
Convars (client-read ones need `setr`): `voice_useNativeAudio`, `voice_useSendingRangeOnly`, `voice_defaultCycle` (F11), `voice_defaultRadio` (LMENU), `voice_defaultVoiceMode` (2), `voice_enableRadios`, `voice_enableCalls`, `voice_enableUi`, `voice_enableSubmix`, `voice_enableRadioAnim`, `voice_defaultRadioVolume`, `voice_defaultCallVolume`, `voice_onClickVolume`/`voice_offClickVolume`, `voice_syncPlayerNames`, `voice_externalAddress`/`voice_externalPort` (external Mumble), `voice_hideEndpoints`, `voice_debugMode`. GTA V Enhanced uses a new VoIP backend — test before migrating.

## 3. Screenshots and video: screencapture
Repo https://github.com/itschip/screencapture · AGPL-3.0 · **v0.17.2 (2026-09-24)** · `provide`s `screenshot-basic`. `citizenfx/screenshot-basic` (MIT) is unmaintained since 2023-02 — avoid.
Server exports: `serverCapture(src, opts, cb(data))`, `remoteUpload(src, url, opts, cb)`, `startVideoCapture(src, opts, cb)` → captureId, `stopVideoCapture(id)`, `startVideoCaptureUpload(src, url, opts, cb)`, `isVideoCaptureActive(id)`, live streaming `startLiveStream`, `createLiveStreamViewerToken`; compat `serverCaptureStream`, `remoteUploadStream`. Client compat exports: `requestScreenshot(opts, cb)`, `requestScreenshotUpload(url, field, opts, cb)`.
Do uploads **server-side** (`remoteUpload`) so the upload token never reaches clients; a client-side `requestScreenshotUpload` with an `Authorization` header leaks your API key.

## 4. Logs and media: Fivemanage SDK
Repo https://github.com/fivemanage/sdk · GPL-3.0 · **v3.2.0 (2026-08-06)** · resource `fmsdk` (TypeScript, Node 22) · Docs https://docs.fivemanage.com.
```cfg
set FIVEMANAGE_MEDIA_API_KEY "..."   # server-only set
set FIVEMANAGE_LOGS_API_KEY "..."
ensure screencapture
ensure fmsdk
```
```lua
exports.fmsdk:Log('economy', 'info', 'Sold item', { playerSource = src, item = 'bread', amount = 5 })  -- dataset, level, message, metadata
exports.fmsdk:Info('economy', 'msg', {}) ; exports.fmsdk:Warn(...) ; exports.fmsdk:Error(...)
local img = exports.fmsdk:takeServerImage(src, { metadata = { reason = 'report' } })  -- server
-- client: exports.fmsdk:takeImage(opts?) ; also uploadImage, requestPresignedUrl
```
Old `LogMessage` logs to the `default` dataset. Alternative: ox_lib `lib.logger` (Fivemanage/Datadog/Grafana Loki via convars).

## 5. Appearance / clothing
| Resource | Status | Notes |
|---|---|---|
| **illenium-appearance** https://github.com/iLLeniumStudios/illenium-appearance | MIT · v5.7.0 (2024-12-11), no commits since; still the default on Qbox/QB/ESX/ox_core servers | docs https://docs.illenium.dev/free-resources/illenium-appearance/installation/ ; client exports `startPlayerCustomization(cb, config)`, `getPedAppearance(ped)`, `setPlayerAppearance(appearance)`, `setPedAppearance(ped, appearance)`, `getPedModel`, `setPlayerModel(model)`, `getPedComponents/Props/HeadBlend/FaceFeatures/HeadOverlays/Hair`, `setPed*` ; replaces qb-clothing/esx_skin |
| pedr0fontoura/fivem-appearance | MIT, pushed 2023-02 | base of illenium; stale — avoid |
| qb-clothing (qbcore-fivem) | GPL-3.0, 1.2.0 | legacy QB menus; exports `IsCreatingCharacter`, `getOutfits`, `reloadSkin` |
| Paid: rcore_clothing, Quasar (qs-appearance)... | docs https://docs.rcore.cz · https://docs.quasar-store.com | follow vendor docs |

## 6. Phones and tablets
| Resource | Status | Notes |
|---|---|---|
| **npwd** https://github.com/project-error/npwd | custom license (NOASSERTION; check LICENSE) · 3.16.0 (2025-03-27), pushed 2026-08 · maintenance mode | React/TS; framework glue via `qbx_npwd` (Qbox), community bridges for ESX/QB; needs screencapture/screenshot-basic for camera. Docs https://projecterror.dev/docs/npwd/start/installation |
| **lb-phone** (paid, escrow) | docs https://docs.lbscripts.com/phone/ | server exports per docs, e.g. `GetEquippedPhoneNumber(src)`, `GetSourceFromNumber(number)`, `HasPhoneItem(src, number?)`, `SendNotification(target, data)`, `NotifyEveryone`, `AddContact`, `AddTransaction(number, amount, title, image?)`, `SendMail(data)`, `SendMessage(from, to, msg, attachments?)`, `GetSettings`, `GetConfig`; custom apps API; custom framework guide |
| **lb-tablet** (paid) | docs https://docs.lbscripts.com/tablet/ | MDT/dispatch tablet; client/shared/server exports and state bags per docs |
| qb-phone | GPL-3.0, 1.5.0, frozen | legacy — avoid for new servers |
| Other paid (Quasar qs-smartphone, okokPhone...) | https://docs.quasar-store.com · https://docs.okokscripts.io | vendor docs only |

## 7. Banking and society money
| Resource | Status | Notes |
|---|---|---|
| **Renewed-Banking** https://github.com/Renewed-Scripts/Renewed-Banking | license NOASSERTION · v2.1.4 (2025-02-19), pushed 2025-05 · QBCore/ESX (ox_lib) | `provide`s `qb-management` and `esx_society`; server exports `getAccountMoney(acc)`, `addAccountMoney(acc, n)`, `removeAccountMoney(acc, n)`, `handleTransaction(acc, title, amount, msg, issuer, receiver, type, id?)`, `GetJobAccount`, `CreateJobAccount(job, balance)`, `addAccountMember`, `removeAccountMember`, `getAccountTransactions`, `changeAccountName` (server-only); grades need `bankAuth = true` in QB jobs/gangs |
| qb-banking 2.0.0 | GPL-3.0, active org | see [framework-qbcore.md §10](framework-qbcore.md) |
| ox_banking https://github.com/overextended/ox_banking | MIT · v1.0.6 (2026-04-24) | **ox_core only** |
| Qbox | qbx_management + Renewed-Banking / qbx banking resources | see framework-qbox.md |

## 8. Garages, vehicle keys, fuel
- Garages: qb-garages 2.0.0 (QB; 2026-08 ownership fix), qbx_garages (Qbox, pushed 2026-09), ND_Garages (ND, split 2026-03). Paid: **jg-advancedgarages** (docs https://docs.jgscripts.com). Avoid renzu_garage (archived).
- Keys: qb-vehiclekeys 1.6.0 (QB; 2026-09 security fix), qbx_vehiclekeys (Qbox), ND_Core built-in keys. Always give keys from the server.
- Fuel: **ox_fuel** v1.5.4 (2026-05-29, GPL-3.0, state bag `fuel`), qb-fuel 0.0.4 (2026-08 fix), cdn-fuel (2.2.0-beta 2023, stale), LegacyFuel (pushed 2024-01, stale). Garages/keys expect `GetFuel/SetFuel` exports — match `Config.FuelResource`.

## 9. Housing
- ps-housing (Project-Sloth) — **archived 2026-02**; avoid for new installs.
- qbx_properties (Qbox, GPL-3.0, active), qb-houses + qb-apartments (QB, maintained but basic).
- Paid (vendor docs only): Quasar qs-housing (https://docs.quasar-store.com), rcore housing (https://docs.rcore.cz), others. Shell-based housing needs streamed shells — check map conflicts ([mapping-streaming.md](mapping-streaming.md)).

## 10. Dispatch and MDT
| Resource | Status | Notes |
|---|---|---|
| **ps-dispatch** https://github.com/Project-Sloth/ps-dispatch | GPL-3.0 · **3.0.0 (2026-08-12)** · QBCore or Qbox + ox_lib | client exports for alerts (`CustomAlert(data)`, `Shooting`, `VehicleShooting`, `StoreRobbery`, `FleecaBankRobbery`, `OfficerDown`, `EmsDown`, `CarJacking`, `DrugSale`, `SuspiciousActivity`, ...) and `GetDispatchCalls`, `SendTargetedAlert`. `CustomAlert({ message, dispatchCode, code, icon, priority, coords, alertTime, information, jobs = {...} })` — job types must be `leo`/`ems` |
| **ps-mdt** https://github.com/Project-Sloth/ps-mdt | license NOASSERTION · 3.1.4 (2026-07-16) · QBCore/QBX via `ps_lib` (Svelte 5 rewrite) | run `sql/qbcore.sql`; exports such as `IsCidFelon` |
| ox_mdt | GPL-3.0, prerelease v0.3.0, pushed 2026-05 | **ox_core only** |
| lb-tablet (paid) | MDT + dispatch | vendor docs |
| Paid: rcore_dispatch, Quasar, wasabi | https://docs.rcore.cz · https://docs.wasabiscripts.com | vendor docs |
Server-side rule for any dispatch: alerts should be created/validated on the server (or rate-limited), otherwise clients can spam fake calls.

## 11. HUD
- qb-hud 2.2.0 (QB; server-side stress validation 2026-08), qbx_hud (Qbox, active).
- **minimal-hud** https://github.com/ThatMadCap/minimal-hud — v3.0.0 (2026-02-19), maintained fork of the archived vipexv/minimal-hud; multi-framework via `config/shared.lua`.
- ps-hud — **archived 2026-02**; avoid. renzu_hud (2023), mt-hud (2024) — stale.
- HUDs that poll in `Wait(0)` loops are the #1 resmon offender: prefer event/state-bag driven updates ([performance.md](performance.md)).

## 12. Admin menus
| Tool | Status | Notes |
|---|---|---|
| **txAdmin** https://github.com/citizenfx/txAdmin | MIT · **v8.1.1 (2026-06-05)**, bundled with FXServer | web panel, in-game menu (`/tx`), bans/warns, scheduler, recipes. Events: `txAdmin:events:serverShuttingDown`, `txAdmin:events:scheduledRestart`, `txAdmin:events:playerKicked`/`playerBanned`/`playerWarned`, `txAdmin:events:announcement` — see [server-ops.md](server-ops.md) |
| **vMenu** https://github.com/TomGrobbe/vMenu | custom license · **vMenu Enhanced v1.0.6 (GTA V Enhanced) + vMenu 3.8.67 (Legacy)**, released 2026-10-07 | C# trainer with ACE permissions (`vMenu.*`); docs https://docs.vespura.com/vmenu/enhanced and /legacy. Freeroam/non-RP servers |
| **EasyAdmin** https://github.com/Blumlaut/EasyAdmin | AGPL-3.0 · stable **7.53 (2026-06-18)**; 8.0.0-alpha.9 prerelease (2026-09-23) | standalone admin menu (bans, reports, screenshots); ACE `easyadmin.*` |
| Framework menus | qb-adminmenu 1.2.0, qbx_adminmenu, esx_adminplus etc. | prefer txAdmin + one in-game menu |
Rule: admin actions must be ACE-checked **server-side**; client-only menus (or `RegisterCommand` without `restricted`) are exploitable.

## 13. Loading screens
`loadscreen` + `loadscreen_manual_shutdown 'yes'` in fxmanifest (then `ShutdownLoadingScreenNui()` from the client, as QBCore does on player load). Free options: qb-loading (QB), bd_loadingscreen (GPL-3.0, 2025-03), nv_loadingscreen (2026-01). Keep them light (no autoplay 4K video), no remote trackers; loading screens run in CEF 103 (Legacy) — test modern CSS/JS features.

## 14. Anticheat
- Server-authoritative code is the real anticheat: validate every event ([security.md](security.md)). Use `sv_entityLockdown`, `sv_filterRequestControl`, routing buckets and event rate limits.
- Paid/escrowed client-side ACs: **Fiveguard** (docs https://docs.fiveguard.net), **WaveShield** (docs https://docs.waveshield.xyz) and others. They cannot be audited; expect false positives and resmon cost; never install "free/leaked" versions.
- Free: NotSomething0/Valkyrie (GPL-3.0, last release 2022, pushed 2026-05), Blumlaut/anticheese-anticheat (2024) — basic, easily bypassed; use only as extra logging.
- Do not ship "anticheat" code that runs `load()` on remote payloads — that pattern is identical to a backdoor.

## 15. Weather/time, doors, bridges
- Weather/time: qb-weathersync 2.3.0 (QB exports `setWeather`, `setTime`, `setBlackout`...), Renewed-Weathersync v1.1.8 (2025-12, GPL-3.0, state-bag based, multi-framework).
- Doors: **ox_doorlock** v1.22.1 (GPL-3.0) for ox/Qbox/ESX/QB; qb-doorlock 2.0.0 for QB-only.
- Bridges: community_bridge 0.13.6, Renewed-Lib 2.0.7, jim_bridge v2.1.09 (required by jim-* scripts, no license file) — see [framework-others.md §6](framework-others.md).
- Jobs packs: jim-* (jimathy; free scripts with jim_bridge, mostly no license file — check before redistributing), Project-Sloth ps-* (several archived 2026: ps-housing, ps-hud, ps-inventory, ps-ui), wasabi/okok/Quasar/rcore (paid; vendor docs).

## 16. Use vs avoid (summary)
| Category | Use (2026) | Avoid |
|---|---|---|
| Voice | pma-voice | TokoVOIP, mumble-voip (pma provides them), SaltyChat unless the community needs TS3 |
| Screenshots | screencapture | screenshot-basic (unmaintained), client-side uploads with API keys |
| Logs | Fivemanage SDK, ox_lib `lib.logger`, txAdmin logs | Discord webhooks from client code (leaked → spam) |
| Appearance | illenium-appearance (stale but standard) | pedr0 fivem-appearance, esx_skin/skinchanger on new servers |
| Phone | npwd (free), lb-phone (paid) | qb-phone, gcphone forks |
| Banking | Renewed-Banking (QB/ESX), qb-banking, ox_banking (ox_core) | storing society money in qb-management (old pre-2023 versions) |
| Garages/keys/fuel | framework-native (qbx_*/qb-* updated 2026), jg-advancedgarages (paid), ox_fuel | renzu_garage (archived), LegacyFuel/cdn-fuel (stale) |
| Housing | qbx_properties, paid vendors | ps-housing (archived) |
| Dispatch / MDT | ps-dispatch 3.0, ps-mdt 3.1 (QB/QBX), ox_mdt (ox_core), lb-tablet | old qb-policejob MEOS, unmaintained forks |
| HUD | framework HUD, minimal-hud | ps-hud (archived), vipexv/minimal-hud (archived) |
| Admin | txAdmin + vMenu (freeroam) / EasyAdmin / framework admin menu | client-trusted admin menus |
| Anticheat | server validation + reputable paid AC | leaked ACs, remote-`load` "protections" |
| Target / inventory / zones | ox_target, ox_inventory, ox_lib zones | qtarget/bt-target, PolyZone loops for new code |

## Sources
- https://github.com/AvarianKnight/pma-voice (fxmanifest.lua, client/**, server/**) · https://github.com/itschip/screencapture (README.md, releases) · https://github.com/citizenfx/screenshot-basic
- https://github.com/fivemanage/sdk (README.md, releases) · https://docs.fivemanage.com
- https://github.com/iLLeniumStudios/illenium-appearance · https://docs.illenium.dev/free-resources/illenium-appearance/installation/ · https://github.com/pedr0fontoura/fivem-appearance
- https://github.com/project-error/npwd · https://projecterror.dev/docs/npwd/start/installation · https://docs.lbscripts.com/phone/ · https://docs.lbscripts.com/phone/exports/server-exports/ · https://docs.lbscripts.com/tablet/
- https://github.com/Renewed-Scripts/Renewed-Banking · https://github.com/Renewed-Scripts/Renewed-Lib · https://github.com/Renewed-Scripts/Renewed-Weathersync · https://github.com/overextended/ox_banking · https://github.com/overextended/ox_mdt · https://github.com/overextended/ox_fuel · https://github.com/overextended/ox_doorlock
- https://github.com/Project-Sloth/ps-dispatch · https://github.com/Project-Sloth/ps-mdt · https://github.com/Project-Sloth/ps-housing · https://github.com/Project-Sloth/ps-hud · https://github.com/Project-Sloth/ps_lib
- https://github.com/ThatMadCap/minimal-hud · https://github.com/InZidiuZ/LegacyFuel · https://github.com/CodineDev/cdn-fuel · https://github.com/renzuzu/renzu_garage
- https://github.com/citizenfx/txAdmin/releases · https://github.com/TomGrobbe/vMenu/releases · https://github.com/Blumlaut/EasyAdmin/releases
- https://github.com/NotSomething0/Valkyrie · https://github.com/Blumlaut/anticheese-anticheat · https://docs.fiveguard.net · https://docs.waveshield.xyz
- https://docs.jgscripts.com · https://docs.rcore.cz · https://docs.okokscripts.io · https://docs.wasabiscripts.com · https://docs.quasar-store.com
- https://github.com/TheOrderFivem/community_bridge · https://github.com/jimathy/jim_bridge · https://github.com/jimathy/jim-consumables
