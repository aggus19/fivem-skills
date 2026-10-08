# NUI and DUI: browser UIs inside FiveM

Baseline: Legacy client CEF **M103** (Chromium 103.0.5060.141) with V8 `--jitless` (JIT disabled, merged 2026-10-07), React 19.3 / Vite 8.3 / TypeScript 7.0 — verified 2026-10-07.
Template: `assets/templates/nui-react-vite/` (React 19 + Vite 8 + TS, `chrome103` target).

## Contents
1. Runtime facts
2. Chromium 103 compatibility table
3. Lua ↔ NUI messaging
4. NUI callbacks (and strict mode)
5. Focus management
6. Build and manifest
7. Dev workflow and devtools
8. Boilerplates (2026-10)
9. Patterns: HUD vs menu, performance
10. Loading screens
11. DUI (browser textures)
12. Security and pitfalls
13. Sources

## 1. Runtime facts
- Each resource with `ui_page` gets a full-screen, transparent iframe in the root NUI page. Resources are stacked; the most recently focused is on top; there is **no click-through** between resource frames.
- URL schemes (fx_version `cerulean`): page and assets are served from `https://cfx-nui-<resource>/<path>`; legacy `nui://<resource>/<path>` still resolves but is not a secure context. Callbacks POST to `https://<resource>/<callbackName>`.
- Globals injected by CEF: `GetParentResourceName()` (current resource name), `window.invokeNative` (used to detect "in game"), `window.nuiTargetGame` (`gta5`/`rdr3`), `window.nuiTargetGameBuild`, `window.nuiTargetGamePureLevel`.
- **V8 JIT is disabled** (`--js-flags=--jitless`, citizenfx/fivem PR #4252, 2026-10-07): interpreter-only JS — heavy JS/frameworks run several times slower. Keep bundles small, avoid per-frame React re-renders, animate with CSS (compositor) instead of JS.
- Widevine/DRM unavailable; accelerated video decode disabled; media permissions are keyed to the server.
- GTA V Enhanced runs a different (newer) CEF — Chromium version not documented (**UNVERIFIED**): if you target both, build for Chromium 103.

## 2. Chromium 103 compatibility table
Vite 8's default target (`baseline-widely-available` ≈ Chrome 111+) is **too new**: always set `build.target`/`cssTarget` to `chrome103`. Syntax is transpiled; **APIs are not polyfilled**.

| Feature | Min Chrome | OK on 103? | Workaround |
|---|---|---|---|
| Optional chaining, `??`, class fields, top-level await, `Array.at`, `Object.hasOwn`, `structuredClone`, `findLast` | ≤ 98 | yes | — |
| `Array.prototype.toSorted/toReversed/with`, `toSpliced` | 110 | **no** | `[...a].sort()` |
| `Object.groupBy`, `Map.groupBy`, `Promise.withResolvers` | 117 / 119 | **no** | small helper |
| Set methods (`union`, `intersection`), `Array.fromAsync`, RegExp `v` flag | 122 / 121 / 112 | **no** | helpers |
| CSS `@layer`, `aspect-ratio`, flex `gap`, `inset`, `accent-color`, `@property` | ≤ 99 | yes | — |
| CSS `:has()`, container queries (`@container`, `cqw`) | 105 | **no** | JS class toggles / media queries |
| `dvh` / `svh` / `lvh` units | 108 | **no** | `vh` (NUI is fixed-size) |
| `color-mix()`, CSS nesting (native) | 111 / 112 | **no** | nesting is lowered by Vite/lightningcss with `cssTarget: 'chrome103'`; precompute colors |
| `text-wrap: balance`, subgrid, `@starting-style`, popover, View Transitions, scroll-driven animations | 114–117 | **no** | avoid |

- **Tailwind CSS v4** (4.3.3) officially needs Chrome 111+ (`color-mix`, `@property`-based utilities): opacity modifiers/colors can break on CEF 103. Use **Tailwind v3.4.19** (`tailwindcss@3`, dist-tag `v3-lts`) or plain CSS/CSS modules for Legacy.
- React 19, Vue 3.5 and Svelte 5 run on Chromium 103 when built with `chrome103`.

## 3. Lua ↔ NUI messaging
```lua
-- client/nui.lua
local isOpen = false

local function setOpen(open, data)
    isOpen = open
    SendNUIMessage({ action = open and 'open' or 'close', data = data })  -- table is JSON-encoded for you
    SetNuiFocus(open, open)                                                 -- keyboard, cursor
end

RegisterNuiCallback('close', function(_, cb)
    setOpen(false)
    cb({ ok = true })                         -- ALWAYS answer, or the browser fetch hangs/times out
end)

RegisterNuiCallback('buy', function(data, cb)
    -- data comes from the browser = client-controlled: forward intent only; the server validates
    if type(data) ~= 'table' or type(data.item) ~= 'string' then return cb({ ok = false }) end
    local ok = lib.callback.await('myres:server:buy', false, data.item)
    cb({ ok = ok == true })
end)

AddEventHandler('onResourceStop', function(res)
    if res == GetCurrentResourceName() and isOpen then SetNuiFocus(false, false) end
end)
```
```ts
// web/src: listen for SendNUIMessage
window.addEventListener('message', (e: MessageEvent<{ action: string; data: unknown }>) => {
  if (e.data?.action === 'open') { /* ... */ }
});
// call a Lua callback
const res = await fetch(`https://${GetParentResourceName()}/buy`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json; charset=UTF-8' },
  body: JSON.stringify({ item: 'bread' }),
}).then((r) => r.json());
```
- JS side of a script resource: `SendNuiMessage(JSON.stringify(obj))` (raw native takes a string; Lua `SendNUIMessage` encodes for you). C#: `API.SendNuiMessage(json)`.
- Payloads are JSON: no functions, no vectors (send `{ x, y, z }`), integer-keyed sparse tables become arrays with `null`s.
- Messages to a frame that isn't loaded yet are lost: have the UI send a `ready` callback on mount and only push data after it.

## 4. NUI callbacks (and strict mode)
| API | Notes |
|---|---|
| `RegisterNuiCallback(name, function(data, cb) end)` | Native-based (current docs). Lua wrapper catches errors and logs "error during NUI callback". |
| `RegisterNUICallback(name, fn)` | Older event-based wrapper (`__cfx_nui:<name>` + `RegisterNuiCallbackType`); still works, same signature. |
| `RegisterRawNuiCallback(name, fn)` / `UnregisterRawNuiCallback(name)` | Raw HTTP-style request/response (custom status/headers); request/response table shape **UNVERIFIED** — check the native page before use. |
| JS: `RegisterNuiCallback(name, (data, cb) => cb({...}))` | C#: `RegisterNuiCallback(name, new Action<IDictionary<string, object>, CallbackDelegate>(...))` |

- Callbacks run in a coroutine: `lib.callback.await`, `Wait` are allowed. Every code path must call `cb(...)` exactly once.
- **`nui_callback_strict_mode 'true'`** in `fxmanifest.lua`: the resource only accepts callback requests whose `Origin` is its own frame. Without it, *any* resource's page (including a compromised/remote `ui_page` or a DUI) can POST to `https://yourres/anything`. Turn it on for every UI resource that doesn't intentionally receive cross-resource calls.

## 5. Focus management
| Native | Use |
|---|---|
| `SetNuiFocus(hasFocus, hasCursor)` | Give this resource's frame keyboard and/or cursor focus (moves it to the top of the focus stack). |
| `SetNuiFocusKeepInput(keepInput)` | Game still receives input while focused (walk while menu open); then disable conflicting controls each frame with `DisableControlAction(0, control, true)` while open. |
| `IsNuiFocused()`, `IsNuiFocusKeepingInput()` | Query state. |
| `SetNuiZindex(z)` | Order resource frames. |
| `local x, y = GetNuiCursorPosition()` | Cursor position (pointer args become return values in Lua). |

Always release focus on close, Escape, death/ragdoll (if relevant) and `onResourceStop`; a stuck `SetNuiFocus(true, true)` leaves the player unable to play. Escape handling: listen for `keydown` in the page and call your `close` callback.

## 6. Build and manifest
```lua
ui_page 'web/dist/index.html'
nui_callback_strict_mode 'true'
files { 'web/dist/**/*' }
```
- Vite: `base: './'` (relative URLs), `build.target: 'chrome103'`, `build.cssTarget: 'chrome103'`, `outDir: 'dist'`. Absolute `/assets/x.js` URLs 404 under `cfx-nui-`.
- Ship the built `dist/` (servers don't run npm); `.gitignore` only `node_modules/`. Vite 8 needs Node `^20.19 || >=22.12` on the dev machine.
- Fonts/images: bundle locally (remote CDNs slow loading, may be blocked offline). Images from other resources: `https://cfx-nui-ox_inventory/web/images/bread.png` (or legacy `nui://ox_inventory/web/images/bread.png`).
- `ui_page 'https://...'` (remote page) works but the page then talks to your callbacks — combine with strict mode and treat it as untrusted.

## 7. Dev workflow and devtools
- Browser preview: `npm run dev` → http://localhost:5173. `isEnvBrowser()` (= no `window.invokeNative`) shows the UI and `fetchNui` returns mocks. Fake a message from the console: `window.postMessage({ action: 'open', data: { title: 'x' } })`.
- In game: `npm run watch` (`vite build --watch`) + `restart myres` (or `ensure myres`) after each build.
- DevTools: open http://localhost:13172/ in any Chromium browser while the game runs (CEF remote debugging), or F8 → `nui_devtools` (needs developer mode; on Enhanced dev mode requires `sv_devMode true` on the server). `nui_devtools <windowName>` targets a specific window (e.g. `mpMenu`).
- `ui_page 'http://localhost:5173'` for in-game HMR is possible but callback fetches come from a non-`cfx-nui` origin (CORS/strict-mode failures) — **UNVERIFIED**, not recommended; never ship it.

## 8. Boilerplates (2026-10)
| Repo | State | Notes |
|---|---|---|
| `project-error/fivem-react-boilerplate-lua` | **v4.1.0** (2026-08-02), MIT | React ^19.2, Vite ^8.2, TS ~6.0, ESLint 10; output `web/build`. Does **not** set a `chrome103` target — add `build.target`/`cssTarget` yourself. |
| This skill: `assets/templates/nui-react-vite/` | 2026-10 | React 19.3, Vite 8.3, TS 7.0, `chrome103`, `useNuiEvent`/`fetchNui`. Use `scripts/scaffold.py --nui`. |
| `alenvalek/fivem-vuejs-boilerplate` | pushed 2026-08 | Vue 3.4 / Vite 5 / TS 5 in `html/` — dependencies outdated. |
| `kCore-framework/fivem-svelte-boilerplate-lua` | pushed 2025-04 | Svelte 5 / Vite 6. |
| `overextended/fivem-typescript-boilerplate` | pushed 2026-05 | TypeScript **script** (client/server) template, not NUI. |

For Vue/Svelte, `npm create vite@latest web -- --template vue-ts` (or `svelte-ts`) and apply: `base: './'`, `chrome103` targets, the `fetchNui`/message helpers, `files { 'web/dist/**/*' }`.

## 9. Patterns: HUD vs menu, performance
- **HUD** (always visible, no focus): push updates from Lua only when values change, throttled to ≤ 4–10 Hz; minimal DOM; no `backdrop-filter`/large `box-shadow`/blur (expensive in CEF).
- **Menu/app** (focused): render nothing when hidden (`return null` / unmount), lazy-load heavy views, release focus on close.
- Transparent `html, body` background; one root element; `user-select: none`; size with `vh`/`clamp()`; test 1080p, 1440p, 4K, ultrawide.
- Measure with devtools Performance tab and `resmon` (NUI cost shows on the client as CEF/GPU time, not in the resource row).

## 10. Loading screens
- `loadscreen 'web/loading.html'` + `files`, optional `loadscreen_cursor 'yes'`, `loadscreen_manual_shutdown 'yes'` (then call `ShutdownLoadingScreenNui()` from a client script, e.g. after spawn).
- Data from `playerConnecting`: `deferrals.handover({ name = ... })` → `window.nuiHandoverData` (+ `serverAddress`).
- The page receives `message` events with `event.data.eventName`: `loadProgress` (`loadFraction`), `onLogLine`, `startInitFunction`, `startInitFunctionOrder`, `initFunctionInvoking`, `initFunctionInvoked`, `endInitFunction`, `startDataFileEntries`, `onDataFileEntry`, `endDataFileEntries`, `performMapLoadFunction`.
- `setr sv_showBusySpinnerOnLoadingScreen false` hides the spinner. Use `innerText`, not `innerHTML`, for player names.

## 11. DUI (browser textures)
Natives (client): `CreateDui(url, w, h)` → dui, `IsDuiAvailable(dui)`, `GetDuiHandle(dui)` → handle string, `SetDuiUrl(dui, url)`, `SendDuiMessage(dui, json)`, `SendDuiMouseMove(dui, x, y)`, `SendDuiMouseDown(dui, 'left')`, `SendDuiMouseUp(dui, 'left')`, `SendDuiMouseWheel(dui, deltaY, deltaX)`, `DestroyDui(dui)`; textures: `CreateRuntimeTxd(name)`, `CreateRuntimeTextureFromDuiHandle(txd, txn, handle)`, `AddReplaceTexture(origTxd, origTxn, newTxd, newTxn)`, `RemoveReplaceTexture(origTxd, origTxn)`.
```lua
-- client/screen.lua
local dui, replaced

local function showScreen()
    dui = CreateDui(('https://cfx-nui-%s/web/dist/screen.html'):format(GetCurrentResourceName()), 1024, 512)
    while not IsDuiAvailable(dui) do Wait(0) end
    local txd = CreateRuntimeTxd('myres_txd')
    CreateRuntimeTextureFromDuiHandle(txd, 'screen', GetDuiHandle(dui))
    AddReplaceTexture('prop_tv_flat_01', 'script_rt_tvscreen', 'myres_txd', 'screen')
    replaced = true
    SendDuiMessage(dui, json.encode({ action = 'show' }))
end

local function hideScreen()
    if replaced then RemoveReplaceTexture('prop_tv_flat_01', 'script_rt_tvscreen'); replaced = false end
    if dui then DestroyDui(dui); dui = nil end
end

AddEventHandler('onResourceStop', function(res) if res == GetCurrentResourceName() then hideScreen() end end)
```
- 2D overlay: draw the runtime texture with `DrawSprite('myres_txd', 'screen', x, y, w, h, 0.0, 255, 255, 255, 255)` every frame while visible.
- Each DUI is a full browser instance (memory + CPU, and now JIT-less): create on demand when the player is near, destroy when far; reuse one DUI with `SetDuiUrl`.
- The DUI page must be in `files`. DUI pages receive `SendDuiMessage` as `message` events, like NUI.
- Texture dictionary/name of the target model must match exactly (find them in OpenIV/CodeWalker).

## 12. Security and pitfalls
- Everything from NUI is client-controlled: validate on the server; never send secrets/prices-of-record to the UI as authority.
- XSS: never inject player text with `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, `{@html}`; chat/phone UIs are classic XSS → token-grabbing vectors.
- Enable `nui_callback_strict_mode 'true'`; don't load remote scripts you don't control.
- Forgetting `cb()` → frozen UI awaiting fetch. `ui_page` not in `files` → blank page. Absolute asset paths → 404.
- Leaving a hidden UI mounted with `opacity: 0` still costs CPU; unmount or `display: none`.
- Calling `SendNUIMessage` every frame (e.g. coords in a `Wait(0)` loop) → JSON + IPC every frame; send deltas at low frequency.

## 13. Sources
- https://docs.fivem.net/docs/scripting-manual/nui-development/full-screen-nui/ · https://docs.fivem.net/docs/scripting-manual/nui-development/nui-callbacks/ · https://docs.fivem.net/docs/scripting-manual/nui-development/dui/ · https://docs.fivem.net/docs/scripting-manual/nui-development/loading-screens/
- https://docs.fivem.net/docs/scripting-reference/resource-manifest/resource-manifest/ (fx_version `cerulean` secure context)
- https://github.com/citizenfx/fivem — `vendor/cef/cef_build_name.txt` (CEF 103.0.0-cfx-m103.2605, Chromium 103.0.5060.141), `code/components/nui-core/src/NUIApp.cpp` (`--jitless`, injected globals), `code/components/nui-core/src/NUIInitialize.cpp` (devtools port 13172, `nui_devtools`), `code/components/nui-resources/src/ResourceUI.cpp` (strict mode, `ui_page_preload`, scheme prefixes), `data/shared/citizen/scripting/lua/scheduler.lua` (NUI callback wrappers)
- https://github.com/project-error/fivem-react-boilerplate-lua/releases/tag/v4.1.0 · https://github.com/alenvalek/fivem-vuejs-boilerplate · https://github.com/kCore-framework/fivem-svelte-boilerplate-lua
- https://www.npmjs.com/package/vite · https://www.npmjs.com/package/tailwindcss (v3-lts 3.4.19, latest 4.3.3) · https://tailwindcss.com/docs/compatibility
