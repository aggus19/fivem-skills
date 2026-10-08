# ox_lib — UI / interface modules (client)

Baseline: ox_lib v3.40.0 — verified 2026-10-07

Part of the ox_lib reference. Entry point and index: [ox-lib.md](ox-lib.md).
Everything here is **client-side** and lives in `ox_lib/resource/interface/client/*.lua`. You call these through `lib.*` in your resource, and ox_lib forwards the call to the `exports.ox_lib` function. Read from the v3.40.0 source, not only from the docs.

## Contents
1. Shared behaviour (NUI focus, icons, markdown, theme)
2. Notifications: `lib.notify`
3. TextUI: `lib.showTextUI` / `hideTextUI` / `isTextUIOpen`
4. Progress bar and circle
5. Skill check
6. Context menu: `lib.registerContext` / `showContext`
7. List menu: `lib.registerMenu` / `showMenu`
8. Input dialog: `lib.inputDialog`
9. Alert dialog: `lib.alertDialog`
10. Radial menu
11. Clipboard, NUI focus helpers, `/ox_lib` settings, `/zone` creator
12. Calling UI from the server
13. Common mistakes
14. Sources

---

## 1. Shared behaviour
- **Icons**: Font Awesome (the docs say FA 6). Pass a string (`'car'`, solid by default) or `{ 'fab', 'apple' }`. Allowed prefixes: `fas far fal fat fad fab fak fass`. `iconColor` takes any CSS colour. `iconAnimation` takes one of `spin spinPulse spinReverse pulse beat fade beatFade bounce shake` (fixed in v3.39).
- **Markdown** is rendered in notify `description`, context `title`, and alert `content`.
- **Theme**: `setr ox:primaryColor blue` and `setr ox:primaryShade 8` use Mantine v6 colour names (https://v6.mantine.dev/theming/colors/#default-colors). Restart ox_lib after changing them; no rebuild is needed.
- **Blocking calls**: `progressBar`, `progressCircle`, `skillCheck`, `inputDialog` and `alertDialog` wait on a promise (`Citizen.Await`). Call them from a thread or handler that is allowed to yield: a `CreateThread` callback, an event handler, a command, an `onSelect`, or a keybind `onPressed`. Don't call them from a `__gc` metamethod or another context that can't yield.
- **One at a time**: if a dialog, alert or skill check is already open, a second call returns `nil` straight away. A second `progressBar` call **waits** until the current one ends (it queues).

## 2. Notifications
```lua
lib.notify(data)                 -- client
```
| Field | Type | Default / notes |
|---|---|---|
| `id` | string | Optional. While a notification with this id is on screen, new ones with the same id are deduplicated. Use it for spam-prone messages. |
| `title` / `description` | string | Set at least one. `description` supports markdown. |
| `duration` | number | `3000` ms |
| `showDuration` | boolean | `true` (shows the countdown ring) |
| `position` | `'top' 'top-right' 'top-left' 'bottom' 'bottom-right' 'bottom-left' 'center-right' 'center-left'` | Defaults to the player's own setting from `/ox_lib`, which is `top-right` if they never changed it. |
| `type` | `'inform'` (docs) / `'info'` (Lua annotation), `'success'`, `'warning'`, `'error'` | Any value other than success/warning/error gets the default (inform) styling. |
| `style` | table | React CSS properties |
| `icon`, `iconColor`, `iconAnimation`, `alignIcon` (`'top'`/`'center'`) | | |
| `sound` | `{ bank?: string, set: string, name: string }` | Plays only if the **player** turned notification audio on in `/ox_lib`. |

```lua
lib.notify({ id = 'shop_buy', title = 'Shop', description = 'Bought **1x** bread', type = 'success', icon = 'basket-shopping' })
```
- `lib.defaultNotify({ title, description, status = 'inform'|'error'|'success'|'warning' })` is a v2 compatibility wrapper that maps `status` to `type`.
- Net events registered by ox_lib: `ox_lib:notify` and `ox_lib:defaultNotify`.

## 3. TextUI
```lua
lib.showTextUI(text, options?)   -- options: position, icon, iconColor, iconAnimation, style, alignIcon
lib.hideTextUI()
local isOpen, currentText = lib.isTextUIOpen()
```
- `position`: `'right-center'` (default), `'left-center'`, `'top-center'`, `'bottom-center'`.
- **Gotcha:** `showTextUI` does nothing if the same `text` is already showing, so a call with new `options` but the same text is ignored. Hide it first, or change the text.
- Pair it with `lib.points` or `lib.zones` `onEnter`/`onExit` rather than calling it every frame.

## 4. Progress bar and circle
```lua
local finished = lib.progressBar(data)      -- or lib.progressCircle(data)
lib.progressActive()                         -- boolean
lib.cancelProgress()                         -- errors ("No progress bar is active") if none
```
Return value: `true` = completed, `false` = cancelled or interrupted, `nil` = it never started because an interrupt condition was already true (for example the player was dead or ragdolling). Test `if finished then`, not `if finished == false`.

| Field | Notes |
|---|---|
| `duration` (required) | ms |
| `label` | progressBar label; optional for the circle |
| `position` | circle only: `'middle'` (default) or `'bottom'` |
| `useWhileDead`, `allowRagdoll`, `allowCuffed`, `allowFalling`, `allowSwimming` | All default `false`. If the matching condition becomes true, the progress is interrupted and returns `false`. |
| `canCancel` | Lets the player cancel with the **`cancelprogress`** command. Its key mapping defaults to **X** and players can rebind it. |
| `anim` | `{ dict, clip, flag = 49, blendIn = 3.0, blendOut = 1.0, duration = -1, playbackRate = 0, lockX, lockY, lockZ }` or `{ scenario, playEnter = true }` |
| `prop` | `{ model, bone = 60309, pos = vec3, rot = vec3, rotOrder = 0 }` or an array of those |
| `disable` | `{ move, sprint, car, combat, mouse }` (booleans) |

```lua
-- client: inside a thread / handler
if lib.progressCircle({
    duration = 2000, label = 'Drinking water', position = 'bottom',
    canCancel = true, disable = { car = true, combat = true },
    anim = { dict = 'mp_player_intdrink', clip = 'loop_bottle' },
    prop = { model = `prop_ld_flow_bottle`, pos = vec3(0.03, 0.03, 0.02), rot = vec3(0.0, 0.0, -1.5) },
}) then
    TriggerServerEvent('myres:server:drink')   -- the server must still validate the item, cooldown, etc.
end
```
Internals worth knowing:
- While a progress runs, **`LocalPlayer.state.invBusy = true`** is set, then restored afterwards. ox_inventory reads it to block inventory use.
- Props are replicated with the player state bag `lib:progressProps`. Every client spawns local props from it, up to `ox:progressPropLimit` per player (default 2; the server enforces the same cap). Since v3.37.2/v3.39 a prop is dropped with a warning if its model is invalid, is a ped or vehicle model, or is larger than 2.5 m.
- The animation is stopped with `StopAnimTask` (or `ClearPedTasks` for scenarios) when the progress ends.
- The progress loop runs `Wait(0)` and disables controls every frame while active. That costs nothing when no progress is running.

## 5. Skill check
```lua
local success = lib.skillCheck(difficulty, inputs?)   -- boolean; nil if a skill check is already running
lib.skillCheckActive()
lib.cancelSkillCheck()                                 -- errors if none active
```
- `difficulty`: `'easy'` (`{ areaSize = 50, speedMultiplier = 1 }`), `'medium'` (`40, 1.5`), `'hard'` (`25, 1.75`), a custom `{ areaSize, speedMultiplier }`, **or an array of these**. An array runs the checks in sequence, and every one must pass.
- `inputs`: an array of keys, for example `{ 'w', 'a', 's', 'd' }`. Each check picks one at random. The default is `'e'`.
```lua
local ok = lib.skillCheck({ 'easy', 'easy', { areaSize = 60, speedMultiplier = 2 }, 'hard' }, { 'w', 'a', 's', 'd' })
```

## 6. Context menu
```lua
lib.registerContext(menu | menu[])   -- stores by id (re-register to update)
lib.showContext(id)                  -- errors 'No context menu of such id found.'
lib.hideContext(onExit?)             -- onExit=true also runs the menu's onExit
lib.getOpenContextMenu()             -- string id | nil
```
Menu fields: `id`, `title` (markdown), `menu` (parent id, which shows a back arrow), `canClose` (set `false` to block ESC), `onExit()`, `onBack()`, and `options`.
`options` can be an **array** or a **hash** (the key becomes the title). Item fields:
`title`, `description`, `icon`, `iconColor`, `iconAnimation`, `image` (URL shown in the hover card), `progress` (0-100), `colorScheme`, `arrow`, `disabled`, `readOnly`, `menu` (submenu id), `metadata`, `onSelect(args)`, `event` (client `TriggerEvent`), `serverEvent` (`TriggerServerEvent`), `args`.
- `metadata` takes `{ 'line', ... }`, `{ { label = 'Price', value = '$5', progress = 40, colorScheme = 'green' } }`, or a hash `{ Price = '$5' }`.
- When an item is clicked, the actions run in this order: `onSelect(args)`, then `event`, then `serverEvent`. An item with none of these (and no `menu`) does nothing and leaves the menu open.
- The docs list a `position` field, but v3.40.0's `showContext` only forwards `title`, `canClose`, `menu` and `options` to the UI. Don't rely on `position` for context menus (**UNVERIFIED** whether the UI reads it from somewhere else).
```lua
lib.registerContext({
    id = 'garage_menu', title = 'Garage',
    options = {
        { title = 'Take out vehicle', icon = 'car', arrow = true, menu = 'garage_list' },
        { title = 'Fuel', progress = 72, colorScheme = 'green', readOnly = true },
        { title = 'Sell', icon = 'dollar-sign', serverEvent = 'myres:server:sell', args = { plate = 'ABC123' } },
    },
})
lib.showContext('garage_menu')
```
**Security:** `serverEvent` + `args` is an ordinary client-to-server net event, so any cheater can call it with arbitrary args. The server must re-check ownership, distance, price and cooldown.

## 7. List menu (keyboard menu)
```lua
lib.registerMenu(data, cb?)          -- errors if id/title/options missing
lib.showMenu(id, startIndex?)        -- errors on unknown id or empty options
lib.hideMenu(onExit?)                -- onExit=true runs onClose
lib.getOpenMenu()                    -- id | nil
lib.setMenuOptions(id, options, index?)  -- replace all options, or only options[index]
```
`data`: `id`, `title`, `options`, `position` (`'top-left'` default, `'top-right'`, `'bottom-left'`, `'bottom-right'`), `disableInput` (default `false`, so the player can still move), `canClose`, `onClose(keyPressed?: 'Escape'|'Backspace')`, `onSelected(selected, secondary, args)`, `onSideScroll(selected, scrollIndex, args)`, `onCheck(selected, checked, args)`.
Option fields: `label`, `description`, `icon`, `iconColor`, `iconAnimation`, `progress`, `colorScheme`, `values` (string list or `{ label, description }` list, which makes the option a side-scroll), `defaultIndex`, `checked` (makes it a checkbox), `args` (**must be a table** if you use `onSelected`), `close` (set `false` to keep the menu open on confirm).
`cb(selected, scrollIndex, args, checked)` runs on Enter. Indexes are 1-based.
```lua
lib.registerMenu({
    id = 'tuning', title = 'Tuning', position = 'top-right',
    options = {
        { label = 'Colour', values = { 'Red', 'Blue', 'Black' }, defaultIndex = 1, args = { kind = 'colour' } },
        { label = 'Neon', checked = false, args = { kind = 'neon' } },
        { label = 'Apply', close = true },
    },
    onSideScroll = function(selected, scrollIndex, args) end,
    onCheck = function(selected, checked, args) end,
}, function(selected, scrollIndex, args, checked)
    print(selected, scrollIndex, json.encode(args))
end)
lib.showMenu('tuning')
```
While a menu is open, ox_lib disables firing, the weapon wheel and control 140 every frame (unless `disableInput = false` was set explicitly).

## 8. Input dialog
```lua
local values = lib.inputDialog(heading, rows, options?)   -- array | nil (cancelled, or another dialog open)
lib.closeInputDialog()                                    -- resolves the pending call with nil
```
`options`: `{ allowCancel = true|false, size = 'xs'|'sm'|'md'|'lg'|'xl' }` (default size `xs`).
`rows`: an array of row tables, or plain strings (a string is shorthand for an `input` row). Common row fields: `type`, `label`, `description`, `placeholder`, `icon`, `iconColor`, `required`, `disabled`, `default`.

| type | Extra fields | Returned value |
|---|---|---|
| `input` | `password`, `min`/`max` (= min/max **length**) | string |
| `number` | `min`, `max`, `precision`, `step` | number |
| `checkbox` | `checked` | boolean |
| `select` | `options = { { value, label } }`, `clearable`, `searchable` | value string |
| `multi-select` | same + `maxSelectedValues`, `default` = array | array of values |
| `slider` | `min`, `max`, `step` | number |
| `color` | `format = 'hex'|'hexa'|'rgb'|'rgba'|'hsl'|'hsla'` | string |
| `date` | `format`, `returnString`, `clearable`, `min`, `max`, `default = true` (today) | **Unix ms timestamp** (number), or a formatted string when `returnString` |
| `date-range` | `format`, `returnString`, `clearable` | `{ startMs, endMs }` (or strings) |
| `time` | `format = '12'|'24'`, `clearable` | Unix ms timestamp |
| `textarea` | `min`/`max` (rows), `autosize`, `minLength`, `maxLength` | string |

```lua
local input = lib.inputDialog('Transfer money', {
    { type = 'number', label = 'Amount', icon = 'dollar-sign', min = 1, max = 100000, required = true },
    { type = 'select', label = 'Account', options = { { value = 'bank', label = 'Bank' }, { value = 'cash', label = 'Cash' } }, default = 'bank' },
    { type = 'input', label = 'Reason', max = 64 },
}, { allowCancel = true })
if not input then return end
local amount, account, reason = input[1], input[2], input[3]   -- reason may be nil
```
- Empty optional fields come back as JSON `null`, which is `nil` in Lua. The array can therefore have **holes**, so index it explicitly and don't rely on `#input` or `ipairs`.
- Client-side `min`/`max`/`required` are only UX. The server must validate the same limits again.
- Since v3.38 ox_lib copies your `rows` table instead of mutating it, and since v3.39 chained dialogs (open a new dialog right after closing one) work.

## 9. Alert dialog
```lua
local answer = lib.alertDialog(data, timeout?)   -- 'confirm' | 'cancel' | nil
lib.closeAlertDialog(reason?)
```
`data`: `header`, `content` (markdown), `centered`, `size` (`xs`-`xl`), `overflow`, `cancel` (show a cancel button), `labels = { confirm?, cancel? }`.
- Returns `nil` immediately if an alert is already open.
- **Gotcha:** when `timeout` fires, ox_lib calls `closeAlertDialog('timeout')`, which **rejects** the promise, so `lib.alertDialog` **throws** the error `timeout`. `lib.closeAlertDialog('reason')` has the same effect. If you pass a timeout or reason, wrap the call:
```lua
local ok, answer = pcall(lib.alertDialog, { header = 'Accept job?', content = 'Deliver 3 packages', cancel = true, centered = true }, 15000)
if not ok or answer ~= 'confirm' then return end
```

## 10. Radial menu
The global radial opens with the keybind `ox_lib-radial` (default **Z**, rebindable). It only opens when it has at least one item, no NUI has focus, and the pause menu is closed.
```lua
lib.addRadialItem(item | item[], parentMenuId?)  -- add or replace by id; parentMenuId since v3.38
lib.removeRadialItem(id, parentMenuId?)
lib.clearRadialItems()                           -- global menu only
lib.registerRadial({ id = 'police_menu', items = { ... } })   -- a submenu (or a root via showRadialMenu)
lib.showRadialMenu(id)    -- v3.40: open a registered radial as the root; calling it again while open closes it
lib.hideRadial()
lib.disableRadial(state)  -- true closes it and blocks opening (e.g. while handcuffed)
lib.getCurrentRadialId()  -- id of the submenu being shown, or nil
```
Item fields: `id` (needed for global items), `label` (use `'  \n'` for a line break), `icon` (FA name or an image URL; `iconWidth`/`iconHeight` size a URL icon), `menu` (submenu id), `onSelect(currentMenu, itemIndex)` **or a string export name**, which calls `exports[owningResource][name](currentMenu, itemIndex)`, and `keepOpen`.
```lua
lib.registerRadial({ id = 'vehicle_extras', items = {
    { label = 'Engine', icon = 'power-off', onSelect = function() toggleEngine() end },
    { label = 'Doors', icon = 'car-side', keepOpen = true, onSelect = function() toggleDoors() end },
}})

lib.onCache('vehicle', function(vehicle)
    if vehicle then
        lib.addRadialItem({ id = 'vehicle', icon = 'car', label = 'Vehicle', menu = 'vehicle_extras' })
    else
        lib.removeRadialItem('vehicle')
    end
end)
```
Global items are removed automatically when the resource that added them stops. While the radial is open, controls 1, 2, 142, 199 and 200 and firing are disabled.

## 11. Clipboard, NUI focus, settings, zone creator
- `lib.setClipboard(text)` copies text to the player's clipboard through NUI.
- `lib.setNuiFocus(allowInput, disableCursor?)` and `lib.resetNuiFocus()` are the focus helpers ox_lib uses for its own UI. `resetNuiFocus` restores the previous `SetNuiFocusKeepInput` state. Use them if you open ox_lib UI from inside your own NUI flow.
- **`/ox_lib`** is a player command. It opens a settings dialog for notification audio, notification position and, when `ox:userLocales` is 1, the UI language. The choices are stored in client KVP. A locale change fires `ox_lib:setLocale` on that client, and every resource that loaded the `locale` module reloads its strings.
- **`/zone poly|box|sphere [useLast]`** is a client zone creator restricted to ACE `command.zone`. It saves to `ox_lib/created_zones.lua` in three formats: `lib.zones.*` call, array, or `exports.ox_target:add*Zone`. The server also checks `IsPlayerAceAllowed(source, 'command')` before writing the file.

## 12. Calling UI from the server
- Notifications: `TriggerClientEvent('ox_lib:notify', src, { ... })` (use `-1` for everyone). The server-side `lib.notify(src, data)` still exists but is **deprecated**. It translates `title`/`description` through your locale keys without placeholders.
- Alert without needing the result: `TriggerClientEvent('ox_lib:alertDialog', src, data)`.
- Anything that needs the player's answer (input, alert, skill check): register a client callback and await it from the server. See [ox-lib-core.md](ox-lib-core.md#2-callbacks).
```lua
-- client
lib.callback.register('myres:client:askAmount', function(max)
    local input = lib.inputDialog('Amount', { { type = 'number', label = 'Amount', min = 1, max = max, required = true } })
    return input and input[1]
end)

-- server
local amount = lib.callback.await('myres:client:askAmount', src, 50)
if type(amount) ~= 'number' or amount < 1 or amount > 50 or math.type(amount) ~= 'integer' then return end
```

## 13. Common mistakes
- Calling a blocking UI function in a context that can't yield, which errors with "attempt to yield across a C-call boundary". Also, expecting `progressBar` to return immediately: it blocks the calling thread.
- Treating client UI limits (`min`, `max`, `required`, `disabled` items) as security.
- Using `#input` / `ipairs(input)` on `inputDialog` results that have optional fields.
- Calling `showTextUI` every frame from a loop. It is cheap because of the same-text check, but use points or zones instead.
- Forgetting `pcall` around `alertDialog` when you pass a timeout.
- Registering a context menu once with stale data. Re-register it (or rebuild `options`) before each `showContext`.
- Assuming `lib.notify` positions are global. The player's `/ox_lib` choice wins unless you pass `position`.

## 14. Sources
- Source code at tag v3.40.0: https://github.com/overextended/ox_lib/tree/v3.40.0/resource/interface/client (notify.lua, textui.lua, progress.lua, skillcheck.lua, context.lua, menu.lua, input.lua, alert.lua, radial.lua, clipboard.lua, main.lua), https://github.com/overextended/ox_lib/blob/v3.40.0/resource/interface/server/progress.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/resource/settings.lua, https://github.com/overextended/ox_lib/tree/v3.40.0/resource/zoneCreator
- Web UI source (return types, metadata rendering): https://github.com/overextended/ox_lib/tree/v3.40.0/web/src/features
- Release notes: https://github.com/overextended/ox_lib/releases
- Docs: https://overextended.dev/docs/ox_lib/Interface/Client/notify (and the sibling pages input, context, menu, progress, radial, skillcheck, textui, alert); docs source: https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_lib/Interface/Client
