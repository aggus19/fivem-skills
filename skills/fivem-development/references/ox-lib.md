# ox_lib (overextended) — reference entry point

Baseline: ox_lib v3.40.0 — verified 2026-10-07

Repo: https://github.com/overextended/ox_lib · Docs: https://overextended.dev/docs/ox_lib · npm: `@overextended/ox_lib` · License: LGPL-3.0-or-later
**v3.40.0** was released **2026-10-03** (tag commit `66906c5`). npm 3.40.0. It requires FXServer ≥ 7290 and OneSync (`dependencies { '/server:7290', '/onesync' }`), and supports `gta5` and `rdr3`.

> **History:** overextended released up to v3.30.6 (2025-04) and then paused. The CommunityOx fork published v3.30.7–v3.32.3. In April 2026 development returned to `overextended/ox_lib`, starting with v3.32.5 (2026-04-24). **CommunityOx repos are archived and `coxdocs.dev` redirects to overextended.dev.** Don't recommend CommunityOx or `@communityox/*`. Docs URLs dropped the `/Modules/` segment, for example `overextended.dev/docs/ox_lib/Callback/Lua/Server`.

## Contents
1. Split reference files (read only what you need)
2. Install and server.cfg
3. Using ox_lib in a resource (fxmanifest directives)
4. What `@ox_lib/init.lua` does (lazy loading, globals)
5. Convars (complete list)
6. Module index: every `lib.*` function and where it's documented
7. Quick start (the 90% use cases)
8. Changelog and breaking changes 2024–2026
9. Security advisories
10. Best practices, performance, common mistakes
11. Sources

---

## 1. Split reference files
| File | Covers |
|---|---|
| [ox-lib-ui.md](ox-lib-ui.md) | notify, textUI, progressBar/Circle, skillCheck, context, menu, inputDialog, alertDialog, radial, clipboard, NUI focus, `/ox_lib`, `/zone` |
| [ox-lib-core.md](ox-lib-core.md) | cache/onCache, callbacks, addCommand, addKeybind, ACL, triggerClientEvent, hooks, game entity classes, state bag replication modes, server vehicle props |
| [ox-lib-world.md](ox-lib-world.md) | points, zones, grid, getClosest*/getNearby*, raycast, streaming requests, playAnim, disableControls, marker, DUI, scaleform, vehicle properties, getRelativeCoords |
| [ox-lib-utilities.md](ox-lib-utilities.md) | require/load/loadJson, locale, print, logger, class, array, map/set/lru/heap/ringbuffer, DataView, table/math/string, waitFor, SetInterval, timer, cron, uuid, selector, getFilesInDirectory, versionCheck, checkDependency |
| [ox-lib-js.md](ox-lib-js.md) | npm package entry points, exports, JS-specific breaking changes and bugs |

## 2. Install and server.cfg
1. Download the **release zip** (`https://github.com/overextended/ox_lib/releases/latest/download/ox_lib.zip`). The green "Code → Download ZIP" has no built UI, and ox_lib then errors with "Unable to load UI. Build ox_lib or download the latest release." To build from source instead: `cd web && bun i && bun run build`.
2. In server.cfg:
```cfg
ensure ox_lib                 # before every resource that uses it (and after oxmysql if you order by dependency)

add_ace resource.ox_lib command.add_ace allow
add_ace resource.ox_lib command.remove_ace allow
add_ace resource.ox_lib command.add_principal allow
add_ace resource.ox_lib command.remove_principal allow

setr ox:locale "en"           # UI + locale() language; setr so clients can read it
setr ox:primaryColor "blue"   # Mantine v6 colour name
setr ox:primaryShade 8
setr sv_stateBagStrictMode true   # recommended (see section 9) - audit your resources first
```

## 3. Using ox_lib in a resource (fxmanifest)
```lua
fx_version 'cerulean'
game 'gta5'
lua54 'yes'                          -- harmless; Lua 5.4 is the only runtime now

shared_script '@ox_lib/init.lua'     -- exactly once, and before your own scripts
ox_lib 'locale'                      -- preload a module; plural form: ox_libs { 'locale', 'table', 'math' }
-- locales_path 'i18n'               -- v3.38+: custom locale folder (default 'locales')

client_scripts { 'client/*.lua' }
server_scripts { 'server/*.lua' }
files { 'locales/*.json', 'modules/**/*.lua', 'data/*.json' }   -- anything loaded by client require/locale/loadJson

dependency 'ox_lib'
```
- `ox_lib '<module>'` and `ox_libs { … }` load the listed modules at startup. If a module returns a function, init.lua calls it once with no arguments (that is how `ox_lib 'locale'` triggers `lib.locale()`). Preloading `table`, `math` or `string` is how you make their global extensions available immediately.
- Startup errors you will see:
  - `ox_lib must be started before this resource.`: fix the ensure order or add `dependency 'ox_lib'`.
  - `Cannot load ox_lib more than once.`: `@ox_lib/init.lua` is listed twice in the manifest.
  - `Lua 5.4 must be enabled`.
  - `Unable to load UI`: see install step 1.

## 4. What `@ox_lib/init.lua` does
- Defines the globals **`lib`**, **`cache`**, **`require`** (replaced by `lib.require`), `noop`, **`SetInterval`/`ClearInterval`**, and on the server **`GetActivePlayers()`** (a polyfill). The `locale` global appears once the locale module loads.
- **Lazy modules:** the first time you touch `lib.foo`, the file `@ox_lib/imports/foo/shared.lua` (plus `client.lua` or `server.lua`) is loaded and run **inside your resource's Lua state**. Points, zones, cache handlers and keybinds therefore run in your resource and count toward your `resmon`. If no import exists, `lib.foo(...)` falls back to `exports.ox_lib:foo(...)`, which covers everything defined in ox_lib's `resource/` folder: all UI, `setVehicleProperties`, ACL, `checkDependency`, `versionCheck`, `getLocaleKey`, and so on.
- It calls `msgpack.setoption('ignore_invalid', true)` in your resource, so values that can't be serialised (functions, userdata) are silently dropped from events and callbacks instead of raising errors.
- The server-side `lib.notify(playerId, data)` exists but is deprecated. Use `TriggerClientEvent('ox_lib:notify', id, data)`.
- In v3.34 the server **`GetGamePool` polyfill was removed**, because FXServer now has a native `GetGamePool` (a shared native).

## 5. Convars
| Convar | Set with | Default | Read by | Effect |
|---|---|---|---|---|
| `ox:locale` | `setr` | `en` | both | Default language for ox_lib UI and the `locale` module |
| `ox:userLocales` | `setr` | `1` | client | Let players pick a language in `/ox_lib` |
| `ox:primaryColor` / `ox:primaryShade` | `setr` | `blue` / `8` | client (NUI) | UI theme (Mantine v6 colours) |
| `ox:progressPropLimit` | `setr` | `2` | both | Max replicated props per progress |
| `ox:callbackTimeout` | `setr` | `300000` | both | ms before `lib.callback.await` rejects |
| `ox:printlevel`, `ox:printlevel:<resource>` | `setr` (client) / `set` | `info` | both | `lib.print` level: error, warn, info, verbose, debug (live-reloads) |
| `ox:setLockState` | `setr` | `false` | client | Apply `lockState` in `setVehicleProperties` (v3.34) |
| `ox:txAdminNotifications` | `set` | `0` | server | Show txAdmin announcements, DMs, warnings and restart notices with ox_lib UI. Needs the matching `txAdmin-hideDefault*` convar (Announcement, DirectMessage, Warning, ScheduledRestartWarning) set to 1. |
| `ox:ignoreSecurityAdvisory` | `set` | `""` | server | JSON array, e.g. `["stateBagStrictMode"]` (v3.37.1) |
| `ox:logger` | `set` | `datadog` | server | `datadog`, `fivemanage` or `loki` |
| `ox:logger:hostname` | `set` | `sv_projectName` | server | Log hostname |
| `datadog:key`, `datadog:site` | `set` (secret) | —, `datadoghq.com` | server | Datadog |
| `fivemanage:key`, `fivemanage:dataset` | `set` (secret) | — | server | Fivemanage |
| `loki:endpoint`, `loki:user`, `loki:password` (or `loki:key`), `loki:tenant` | `set` (secret) | — | server | Grafana Loki |
| `sv_stateBagStrictMode` | `setr` | `false` | both | FXServer setting. ox_lib warns when it is off and routes client writes through hooks when it is on. |

Rule: anything a **client** must read uses `setr`, and secrets always use `set`.

## 6. Module index
**C** = client, **S** = server, **Sh** = shared. "→ file" says where the details are.

| Area | Functions / objects | Side | → |
|---|---|---|---|
| Cache | `cache.*`, `cache(key, fn, timeout)`, `lib.onCache` | Sh/C | core |
| Callbacks | `lib.callback`, `.await`, `.register` | Sh | core |
| Commands / keys / ACL | `lib.addCommand`, `lib.addKeybind`, `lib.addAce`, `removeAce`, `addPrincipal`, `removePrincipal` | S / C / S | core |
| Events | `lib.triggerClientEvent` | S | core |
| Hooks | `lib.hook:new`, `pipeline:registerHook/remove/dispatch`, `lib.registerHook` (+ `ox_lib:setPlayerState`, `ox_lib:setEntityState`) | Sh (mainly S) | core |
| Entities | `lib.gameEntity`, `lib.ped`, `lib.player`, `lib.prop`, `lib.vehicle` (+ `.create`), `set/setr/sets/get/has/keys` | Sh | core |
| Notify / TextUI | `lib.notify`, `lib.defaultNotify`, `lib.showTextUI`, `hideTextUI`, `isTextUIOpen` | C | ui |
| Progress | `lib.progressBar`, `progressCircle`, `progressActive`, `cancelProgress` | C | ui |
| Skill check | `lib.skillCheck`, `skillCheckActive`, `cancelSkillCheck` | C | ui |
| Menus | `lib.registerContext`, `showContext`, `hideContext`, `getOpenContextMenu`; `lib.registerMenu`, `showMenu`, `hideMenu`, `getOpenMenu`, `setMenuOptions` | C | ui |
| Dialogs | `lib.inputDialog`, `closeInputDialog`, `lib.alertDialog`, `closeAlertDialog` | C | ui |
| Radial | `lib.addRadialItem`, `removeRadialItem`, `clearRadialItems`, `registerRadial`, `showRadialMenu`, `hideRadial`, `disableRadial`, `getCurrentRadialId` | C | ui |
| Misc UI | `lib.setClipboard`, `lib.setNuiFocus`, `lib.resetNuiFocus` | C | ui |
| Points / zones / grid | `lib.points.new` (+ getters), `lib.zones.sphere/box/poly` (+ getters), `lib.grid.*` | C / Sh / Sh | world |
| Proximity | `lib.getClosestPlayer/Vehicle/Ped/Object`, `lib.getNearbyPlayers/Vehicles/Peds/Objects` | C/S/Sh | world |
| Raycast | `lib.raycast.fromCamera`, `fromCoords` (`cam` deprecated) | C | world |
| Streaming | `lib.requestModel`, `requestAnimDict`, `requestAnimSet`, `requestNamedPtfxAsset`, `requestStreamedTextureDict`, `requestWeaponAsset`, `requestAudioBank`, `requestScaleformMovie`, `lib.streamingRequest` | C | world |
| Animation / input | `lib.playAnim`, `lib.disableControls` | C | world |
| Drawing | `lib.marker.new`, `lib.dui:new`, `lib.scaleform:new` | C | world |
| Vehicles | `lib.getVehicleProperties`, `lib.setVehicleProperties` | C (+S setter) | world / core |
| Math helpers | `lib.getRelativeCoords` | Sh | world |
| Modules / files | `require`, `lib.require`, `lib.load`, `lib.loadJson`, `require 'Ox.DataView'`, `lib.getFilesInDirectory` (S) | Sh | utilities |
| Locale | `lib.locale`, `locale()`, `lib.getLocales`, `lib.getLocale`, `lib.getLocaleKey`, `lib.setLocale` (C) | Sh | utilities |
| Logging | `lib.print.*`, `lib.logger` (S) | Sh / S | utilities |
| OOP / data | `lib.class`, `lib.array`, `lib.map`, `lib.set`, `lib.lru`, `lib.heap`, `lib.ringbuffer`, `lib.selector`, `lib.uuid` | Sh | utilities |
| Std extensions | `lib.table.*`, `lib.math.*`, `lib.string.*` (extend the globals) | Sh | utilities |
| Async / time | `lib.waitFor`, `SetInterval`, `ClearInterval`, `lib.timer`, `lib.cron.new` (S) | Sh | utilities |
| Versioning | `lib.versionCheck` (S), `lib.checkDependency` (Sh) | | utilities |

## 7. Quick start
```lua
-- server/main.lua
lib.callback.register('myres:server:buy', function(source, item)
    local cfg = type(item) == 'string' and ServerConfig.items[item]   -- server-side price list
    if not cfg then return false, 'invalid_item' end
    if #(GetEntityCoords(GetPlayerPed(source)) - ServerConfig.shopCoords) > 5.0 then return false, 'too_far' end
    -- check money, cooldown; remove money before adding the item
    lib.logger(source, 'shop:buy', ('bought %s for $%d'):format(item, cfg.price))
    return true
end)
```
```lua
-- client/main.lua
lib.locale()   -- not needed if the manifest has ox_lib 'locale'

local point = lib.points.new({ coords = vec3(25.7, -1347.3, 29.5), distance = 2.0,
    onEnter = function() lib.showTextUI(locale('open_shop')) end,
    onExit = function() lib.hideTextUI() end,
    nearby = function(self)
        if self.isClosest and IsControlJustReleased(0, 38) then
            local input = lib.inputDialog(locale('shop_title'), { { type = 'select', label = locale('item'), options = Config.Items, required = true } })
            if not input then return end
            local ok, err = lib.callback.await('myres:server:buy', 500, input[1])
            lib.notify({ type = ok and 'success' or 'error', description = ok and locale('bought') or locale(err or 'failed') })
        end
    end,
})
```
For irregular areas, create a `lib.zones.box/poly` in a server file and check `zone:contains(coords)` instead of the distance. Server zones never fire callbacks.

## 8. Changelog and breaking changes 2024–2026 (Lua side)
| Version (date) | Notable changes | Breaking? |
|---|---|---|
| 3.15–3.16 (2024-01) | `addCommand` errors caught; `waitFor` timeout normalised and can be disabled with `false`; server dependency raised to build 7290 | Needs server ≥ 7290 |
| 3.17 (2024-03) | `lib.class` rewrite: `constructor`, true `private` fields, `instanceOf`, `isClass`; `init` deprecated | `class.init` |
| 3.18 (2024-03) | `class.init` **removed**; progress props synced through state bags; `allowSwimming` | **Yes** (class init) |
| 3.19 (2024-04) | `getFilesInDirectory`, `triggerClientEvent` (multi-target), Fivemanage logger, notification sounds | |
| 3.20 (2024-04) | `lib.array`, `lib.timer`, `lib.playAnim`; notification position setting; `showDuration` | |
| 3.21 (2024-05) | Callback **timeout**; `raycast.fromCoords`; `math.lerp`/`interp`; alert timeout; multi-select `maxSelectedValues` | Await can now throw on timeout |
| 3.22–3.23 (2024-05/07) | `table.merge` duplicate-number option; `math.round`; `addCommand` `longString`; `requestModel` validates with `IsModelInCdimage` | |
| 3.24 (2024-07) | `setVehicleProperties` state bag handler and **server setter** | |
| 3.25–3.27 (2024-08/10) | `onCache` receives `oldValue`; keybind `isPressed`; `lib.dui`; more array methods; streaming error messages | |
| 3.28–3.29 (2025-01) | Error boundary in UI; `lib.scaleform`; `getRelativeCoords`; `modLivery` split from `livery` | `livery` vs `modLivery` |
| 3.30 (2025-03) | `lib.grid`; points and zones moved to the grid; zones become shared (server); **callback validation** (unknown callback errors immediately); cron `maxDelay`; `table.shuffle`; print convar listener | Zones module moved to shared |
| 3.30.7–3.32.3 | CommunityOx-only releases (2025) | — |
| 3.32.5 (2026-04-24) | Back on overextended; merges the CommunityOx work: `selector`, `table.map`, marker `invert`, server `getClosestPlayer` `ignorePlayerId`, input dialog `size`, Fivemanage dataset/metadata, `lockState` prop | |
| 3.33 (2026-05) | Concave poly zones; nested `${key}` locale references; cron fixes; the callback register event no longer leaks into `_G`; JS zones (experimental); JS paths reorganised and default export removed (v3.33.1) | **JS imports** |
| 3.34 (2026-05-22) | Hooks API; game entity classes and create wrappers; state bag helpers; `ox:setLockState` convar; server `GetGamePool` polyfill **removed** | `lockState` now opt-in via convar |
| 3.35 (2026-05-24) | JS: nativewrappers dropped, tsdown build, barrel exports changed; typed locales | **JS** |
| 3.36 (2026-05-28) | Entity **replication modes** (`setr` / `sets` synced states); keybind `allowInPauseMenu`; Loki table tags; JS `addCommand` `paramType` → `type` | No (presses were always ignored while paused; `allowInPauseMenu` opts in) |
| 3.37 (2026-06) | `lib.uuid` (UUIDv7); `sv_stateBagStrictMode` security warning (3.37.0); `ox:ignoreSecurityAdvisory` (3.37.1); progress prop validation (3.37.2) | |
| 3.38 (2026-06-17) | `lib.map` (ordered), `set`, `lru`, `heap`, `ringbuffer`; radial items in submenus; `locales_path`; caller tables no longer mutated; `isCallbackValid` returns a boolean; logger providers split; `getFilesInDirectory` uses `io.readdir` | |
| 3.39 (2026-07-13) | String helpers (`startsWith`, `endsWith`, `contains`, `isBlank`, `escapePattern`, `replace`); invalid progress props ignored; vehicle props track broken-off wheels (`tyres[i] = 3`); cron fixes; chained input dialogs fixed | |
| **3.40 (2026-10-03)** | `lib.showRadialMenu(id)` (radial as root); `Ox.DataView` module ("modules v2" via `require 'Ox.X'`); private fields readable from inherited methods; bulletproof tyres fix; cache preserves 0 values; **callbacks reject responses from the wrong source** | |

Re-verify: `gh release list -R overextended/ox_lib -L 5` or https://github.com/overextended/ox_lib/releases.

## 9. Security advisories
- **State bag strict mode (v3.37+)**: ox_lib prints a SECURITY WARNING when `sv_stateBagStrictMode` is off, because clients can then write any replicated state. Enable it with `setr sv_stateBagStrictMode true`. Client writes made through ox_lib entity helpers then go through the `ox_lib:setPlayerState` / `ox_lib:setEntityState` hooks, and they are **rejected unless a server hook allows the key**. Scripts that write `LocalPlayer.state:set(k, v, true)` directly will stop replicating. Silence the warning with `set ox:ignoreSecurityAdvisory ["stateBagStrictMode"]`. It is auto-skipped when `qb-core` is present. Details: [ox-lib-core.md §9](ox-lib-core.md#9-entity-state-replication-modes-v336).
- **Callbacks (v3.40, commit 9af6ba6)**: the server now rejects (and warns about) a server→client callback response unless it comes from the player the request was sent to. Before this, a client that guessed the pending key could answer another player's request. The author considers real exploitation unlikely, but update anyway. Clients have ignored non-server responses since v3.30.4.
- ox_lib's UI and callbacks never replace server validation. `serverEvent` context options, `inputDialog` limits and the client callback `delay` are client-side conveniences.

## 10. Best practices, performance, common mistakes
**Do**
- Use `lib.points` or `lib.zones` (or ox_target) for proximity. They poll every 300 ms and tick per frame only while needed. Keep `nearby`/`inside` light.
- Use `cache.ped`, `cache.vehicle` and `lib.onCache` instead of polling `PlayerPedId()`/`GetVehiclePedIsIn` in your own loops.
- Use `lib.callback.await` for request/response and validate everything on the server. Wrap awaits in `pcall` where a timeout or disconnect must not break the thread.
- Use `lib.addCommand` with `restricted` and typed `params`, and `lib.addKeybind` instead of raw `RegisterCommand` + `RegisterKeyMapping`.
- Load assets with `lib.requestX` and release them afterwards.
- Put every client-read file (locales, JSON, required modules) in `files {}`.
- Use `lib.print.debug` plus `ox:printlevel:<res>` instead of leftover `print`s, and `lib.logger` for audit trails (with `set` secrets).
- Pin and re-verify the ox_lib version when using features from v3.33 or later (hooks, entity classes, collections, uuid, DataView, `showRadialMenu`).

**Don't**
- Bundle or copy ox_lib's `imports` into your resource, or load `@ox_lib/init.lua` twice.
- Install ox_lib from the source ZIP (no UI build).
- Call blocking UI functions (`progressBar`, `inputDialog`, `alertDialog`, `skillCheck`, `callback.await`) outside a thread or yieldable handler.
- Trust `args` from context `serverEvent`, or input dialog values, without server checks.
- Use `table.deepclone` or `string.random` before `lib.table` or `lib.string` has loaded (preload with `ox_libs`).
- Use the client `getClosestPlayer` result as a server id (it is the client player index).
- Use `setr` for logger keys, or leave `debug = true` on zones in production.
- Point users to CommunityOx forks or `@communityox/*`, or use `import lib from '@overextended/ox_lib/client'` (removed default export).

## 11. Sources
- Repository and tag v3.40.0 (cloned and read 2026-10-07): https://github.com/overextended/ox_lib, https://github.com/overextended/ox_lib/tree/v3.40.0 (fxmanifest.lua, init.lua, resource/, imports/, modules/, package/)
- Releases (all notes 2024-01 → 2026-10 read through the API): https://github.com/overextended/ox_lib/releases, https://api.github.com/repos/overextended/ox_lib/releases
- Server-side files cited: https://github.com/overextended/ox_lib/blob/v3.40.0/resource/server.lua (security advisory), https://github.com/overextended/ox_lib/blob/v3.40.0/resource/settings.lua (convars), https://github.com/overextended/ox_lib/blob/v3.40.0/resource/interface/server/txadmin.lua
- Docs: https://overextended.dev/docs/ox_lib (install, convars, ACE, usage) and its source https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_lib
- npm: https://registry.npmjs.org/@overextended/ox_lib/latest
