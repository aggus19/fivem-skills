# ESX ecosystem: core resources and addons

Baseline: es_extended 1.15.2 — verified 2026-10-07 (`[core]` resources carry `version '1.15.2'`; ESX-Legacy-Addons `main` 2026-10-06)

Core framework (es_extended, esx_lib, esx_inventory): [framework-esx.md](framework-esx.md). This file covers the other resources in `esx_core/[core]` and the common addons in `ESX-Legacy-Addons/[esx_addons]`. All are GPL-3.0 unless noted.

## Contents
1. Resource map and start order
2. esx_multicharacter (flow, config, commands)
3. esx_identity
4. esx_skin and skinchanger
5. UI resources: esx_notify, esx_textui, esx_progressbar, esx_context, esx_menu_default/dialog/list
6. cron, esx_loadingscreen, esx_chat_theme
7. Society stack: esx_addonaccount, esx_addoninventory, esx_datastore, esx_society
8. esx_billing
9. esx_license, esx_status, esx_basicneeds
10. Replacing ESX UI with ox_lib
11. Security notes per resource
12. Sources

---

## 1. Resource map and start order

| Resource | Side | Purpose | Depends on |
|---|---|---|---|
| `esx_lib` | shared | xLib library (before es_extended) | — |
| `es_extended` | shared | framework | oxmysql, esx_lib |
| `esx_menu_default` / `esx_menu_dialog` / `esx_menu_list` | client | `ESX.UI.Menu` types `default`, `dialog`, `list` | es_extended |
| `esx_notify` | client | `ESX.ShowNotification` | es_extended |
| `esx_textui` | client | `ESX.TextUI` / `ESX.HideUI` | es_extended |
| `esx_progressbar` | client | `ESX.Progressbar` | es_extended, esx_lib |
| `esx_context` | client | `ESX.OpenContext` | es_extended |
| `esx_inventory` | client | F2 menu for the default inventory | es_extended, esx_menu_default/dialog |
| `esx_identity` | both | character identity registration | es_extended, oxmysql |
| `skinchanger` / `esx_skin` | both | ped appearance and editor | es_extended |
| `esx_multicharacter` | both | character selection | es_extended, esx_context, esx_identity, esx_skin |
| `cron` | server | scheduled tasks | — |
| `esx_loadingscreen` | client | loading screen (1.15) | — |
| `esx_chat_theme` | client | chat styling | chat |

Recipe order: `chat`, `oxmysql`, `esx_lib`, `es_extended`, `ensure [core]` (folder order inside is fine because each declares dependencies), `[standalone]`, `[esx_addons]`. Each core resource loads `@esx_lib/imports.lua` and `@es_extended/imports.lua`; most read their locale from `GetConvar('esx:locale', 'en')`.

## 2. esx_multicharacter

Presence alone switches es_extended into multichar mode (`Config.Multichar = GetResourceState('esx_multicharacter') ~= 'missing'`).
Flow:
1. `playerConnecting` checks; client sends `esx_multicharacter:SetupCharacters` once the session is active.
2. Server puts the player in routing bucket = their server id, loads `users` rows `char<N>:<identifier>` (slot count from `multicharacter_slots` or `Config.Slots`), sends `esx_multicharacter:SetupUI` (characters, slots).
3. `esx_multicharacter:CharacterChosen(charid, isNew)` — validated against the session (slot range, disabled flag, not already online).
   - existing → bucket 0, `TriggerEvent('esx:onPlayerJoined', src, 'charN')` → es_extended `loadESXPlayer`.
   - new → waits for esx_identity registration → `esx_identity:completedRegistration` → `esx:onPlayerJoined(src, 'charN', identityData)` → `createESXPlayer` (row inserted with SSN and identity columns).
4. Relog: client `esx_multicharacter:relog` → `esx:playerLogout` (save + remove xPlayer, client `esx:onPlayerLogout`). Resources that cache per-player data must clear it on `esx:playerDropped`/`esx:playerLogout` server-side and `esx:onPlayerLogout` client-side.
5. Delete: `esx_multicharacter:DeleteCharacter(charid)` when `Config.CanDelete`; deletes from every table that has an identifier/owner column (indexes added by migration v1.14.1).

Config (`config.lua`): `Config.CanDelete = true`; server `Config.Slots = 3`, `Config.Prefix = "char"`; client `Config.Spawn` (selection scene coords), `Config.Relog = true`, `Config.Default` (default `m`/`f` appearance). New characters spawn at the `users.position` default / `Config.DefaultSpawns` of es_extended.
Commands (group `admin`): `/setslots <identifier> <slots>`, `/remslots <identifier>`, `/enablechar <identifier> <slot>`, `/disablechar <identifier> <slot>`, plus restricted (ACE) `/forcelog` which triggers `esx:playerLogout` for the caller.
SQL: `multicharacter_slots(identifier, slots)`, `users.disabled`.
Gotcha: identifiers in your own tables must use `xPlayer.getIdentifier()` (the `charN:` form), otherwise data is shared between characters; never build identifiers from `GetPlayerIdentifierByType` directly.

## 3. esx_identity

Registers firstname, lastname, dateofbirth, sex (`m`/`f`), height (cm). Columns are added by `esx_identity.sql`.
Config: `Config.EnableCommands` (= es_extended `EnableDebug`), `Config.DateFormat` (`DD/MM/YYYY` | `MM/DD/YYYY` | `YYYY/MM/DD`), `MaxNameLength = 20`, `MinHeight = 120`, `MaxHeight = 220`, `MaxAge = 100`, `FullCharDelete = true`.
Server callback `esx_identity:registerIdentity` validates every field server-side. Without multichar it shows the form on `esx:playerLoaded` if the row has no firstname; with multichar it fires `esx_identity:completedRegistration` (src, data).
Client events: `esx_identity:showRegisterIdentity`, `esx_identity:setPlayerData` (secure), `esx_identity:alreadyRegistered` (secure).
Reading identity in your code: `xPlayer.get('firstName')`, `get('lastName')`, `get('dateofbirth')`, `get('sex')`, `get('height')`, `xPlayer.getName()` (full RP name). Debug commands (only with `EnableCommands`): `/char`, `/chardel` (group `user` in 1.15.2 — keep EnableCommands off in production), `/xPlayerGetFirstName` etc.

## 4. esx_skin and skinchanger

skinchanger (client) exports: `GetSkin()`, `GetMaxVals()`, `LoadSkin(skin)`, `GetData(noMax?)` → components, maxValues, `LoadClothes(playerSkin, clothesSkin)`, `Change(key, val)`. Events: `skinchanger:loadSkin` (skin, cb), `skinchanger:loadClothes` (playerSkin, clothes), local `skinchanger:getSkin` (cb), `skinchanger:loadDefaultModel` (isMale, cb), `skinchanger:change` (key, val), `skinchanger:modelLoaded`, `skinchanger:getData` (cb). `Config.Components` lists every key (`sex`, `mom`, `dad`, `tshirt_1`, `torso_1`, `bags_1`, …).
esx_skin (client) events: `esx_skin:openMenu` / `openRestrictedMenu` / `openSaveableMenu` / `openSaveableRestrictedMenu` (submitCb, cancelCb, restrict?), local `esx_skin:getLastSkin` (cb), `esx_skin:setLastSkin` (skin), `esx_skin:playerRegistered`, `esx_skin:resetFirstSpawn`. Server: net `esx_skin:save` (skin) → `users.skin`, `esx_skin:setWeight` (skin), callback `esx_skin:getPlayerSkin`, command `/skin [playerId]` (admin). `Config.BackpackWeight = { [bags_1 drawable] = extra kg }` adjusts `xPlayer.setMaxWeight`.
```lua
-- client: open the saveable editor (e.g. at a clothing shop)
TriggerEvent('esx_skin:openSaveableMenu', function() print('saved') end, function() print('cancelled') end)
```

## 5. UI resources

**esx_notify** — export `Notify(type, length, message, title?, position?)`; net event `ESX:Notify` (same args). Types are free strings styled by the NUI (`info`, `success`, `error`, …); positions `top-right|top-left|top-middle|bottom-right|bottom-left|bottom-middle|middle-left|middle-right`. Config: `Config.position = "middle-right"`, `Config.notificationSoundEnabled = true`. `~br~` → line break. Use `ESX.ShowNotification(msg, type, length, title, position)` (client) or `xPlayer.showNotification(...)` (server).

**esx_textui** — exports `TextUI(message, type?)`, `HideUI()`; secure net events `ESX:TextUI`, `ESX:HideUI`. Call `HideUI` when leaving the zone; showing every frame is unnecessary (it is a persistent NUI element).

**esx_progressbar** — exports `Progressbar(message, ms, options)` → `false` if one is already running, `CancelProgressbar()`. Options: `FreezePlayer`, `animation = { type = 'anim', dict, lib }` or `{ type = 'Scenario', Scenario = 'WORLD_HUMAN_...' }`, `onFinish()`, `onCancel()`. Cancel keybind "cancelprog" (default BACKSPACE). Purely client-side: the server must still verify time/distance before rewarding.
```lua
ESX.Progressbar('Repairing…', 8000, {
    FreezePlayer = true,
    animation = { type = 'anim', dict = 'mini@repair', lib = 'fixing_a_player' },
    onFinish = function() TriggerServerEvent('myres:server:finishRepair') end,
    onCancel = function() ESX.ShowNotification('Cancelled', 'error') end,
})
```

**esx_context** — exports `Open(position, elements, onSelect, onClose, canClose?)` (takes focus), `Preview(position, elements)` (no focus), `Close()`, `Refresh(elements?, position?)`, `focusPreview()`. Positions `right`, `left`, `center`. Element fields: `title`, `description`, `icon` (Font Awesome class), `unselectable`, `disabled`, `name`/`value` (yours), inputs `input = true, inputType = 'text'|'number'|…, inputPlaceholder, inputValue`. `onSelect(menu, element)`; read inputs from `menu.eles[i].inputValue`. `LocalPlayer.state['context:active']` is true while open.
```lua
ESX.OpenContext('right', {
    { unselectable = true, icon = 'fas fa-store', title = 'Shop' },
    { icon = 'fas fa-bread-slice', title = 'Bread', description = '$5', name = 'bread' },
}, function(menu, element)
    if element.name then TriggerServerEvent('myres:server:buy', element.name) end   -- server decides price
    ESX.CloseContext()
end)
```

**esx_menu_default / esx_menu_dialog / esx_menu_list** — legacy NUI menus behind `ESX.UI.Menu.Open(type, namespace, name, data, submit, cancel, change?, close?)`. `default`: `data = { title, align, elements = { {label, value, ...} } }`, submit `data.current`; `dialog`: `data = { title }`, submit `data.value` (string — `tonumber` and validate); `list`: `data = { head = {...}, rows = { {data=..., cols={...}} } }`. Menus close automatically when esx_menu_default stops. Fine for compatibility; prefer esx_context or ox_lib for new UIs.

## 6. cron, esx_loadingscreen, esx_chat_theme

**cron** (server): `TriggerEvent('cron:runAt', hour, minute, function(weekday, h, m) end)`. Uses server local time (`os.time`). `weekday` is `os.date('*t').wday` → **1 = Sunday, 2 = Monday** (the README example claims `d == 1` is Monday; it is wrong). Jobs missed across midnight are caught up (1.14.1); an erroring job no longer kills the scheduler. In 1.15.2 the tick is a 60 s `SetTimeout` that can drift (the unreleased 1.16 branch aligns it to the minute).
```lua
TriggerEvent('cron:runAt', 4, 0, function(d) if d == 2 then WeeklyMondayReset() end end)
```
**esx_loadingscreen** (1.15): `loadscreen 'web/index.html'` with `loadscreen_manual_shutdown 'yes'`; the NUI posts `loadingComplete` and the client calls `ShutdownLoadingScreenNui()` 2.5 s later; es_extended/multichar also shut it down after spawn (`esx:loadingScreenOff` local event). Replace by stopping this resource and adding your own loadscreen resource; keep `loadscreen_manual_shutdown` semantics in mind.
**esx_chat_theme**: CSS theme for the default `chat` resource.

## 7. Society stack

Tables: `addon_account` (name, label, shared), `addon_account_data` (account_name, money, owner), `addon_inventory` (name, label, shared), `addon_inventory_items` (inventory_name, name, count, owner), `datastore` (name, label, shared), `datastore_data` (name, owner, data JSON). A society needs rows `society_<job>` (shared = 1) in the three registries; `legacy.sql` seeds police, ambulance, mechanic, taxi, cardealer.

**esx_addonaccount** (server): `server_exports { GetSharedAccount, AddSharedAccount, GetAccount }`; events `esx_addonaccount:getSharedAccount` (name, cb), `esx_addonaccount:getAccount` (name, owner, cb), `esx_addonaccount:refreshAccounts`. Account object: `.name`, `.owner`, `.money`, `addMoney(n)`, `removeMoney(n)` (no balance check), `setMoney(n)`, `save()`. Personal (non-shared) accounts are created on `esx:playerLoaded` and exposed via `xPlayer.get('addonAccounts')`. `AddSharedAccount({ name = 'society_x', label = 'X' }, startMoney?)` creates rows at runtime.
```lua
local account = exports.esx_addonaccount:GetSharedAccount('society_police')
if account and account.money >= amount then account.removeMoney(amount) end   -- check first
```
**esx_addoninventory** (server): exports `GetSharedInventory(name)`, `AddSharedInventory({name,label})`; events `esx_addoninventory:getInventory` (name, owner, cb), `:getSharedInventory` (name, cb). Object: `addItem(name, n)`, `removeItem(name, n)`, `setItem(name, n)`, `getItem(name)` → `{name, count, label}`, `.items`.
**esx_datastore** (server): events `esx_datastore:getDataStore` (name, owner, cb), `:getDataStoreOwners` (name, cb), `:getSharedDataStore` (name, cb). Object: `set(key, val)`, `get(key, index?)` (dot paths), `count(key, index?)`, `save()` (debounced 10 s write).
**esx_society**:
```lua
-- server: register (once, at resource start)
exports.esx_society:registerSociety('mechanic', 'Mechanic', 'society_mechanic', 'society_mechanic', 'society_mechanic', { type = 'private' })
local society = exports.esx_society:GetSociety('mechanic')      -- {name, label, account, datastore, inventory, data}
-- client: boss menu (options default true: checkBal, withdraw, deposit, wash, employees, salary, grades; uniforms per Config)
TriggerEvent('esx_society:openBossMenu', 'mechanic', function() ESX.CloseContext() end, { wash = false })
```
Events: `esx_society:getSocieties` (cb), `esx_society:getSociety` (name, cb); net (validated with boss checks): `checkSocietyBalance`, `withdrawMoney`, `depositMoney`, `washMoney`, `putVehicleInGarage`, `removeVehicleFromGarage`. Callbacks `esx_society:getSocietyMoney`, `getEmployees`, `getJob`, `setJob`, `setJobSalary`, `setJobLabel`, `setJobUniform`, `getOnlinePlayers`, `getVehiclesInGarage`, `isBoss`. Config: `Config.BossGrades = { boss = true }`, `MaxSalary = 3500`, `MaxJobGradeLabelLength`, `JobGradeUpdateCooldown`, `SocietyGarageZones`, `SocietyGarageDistance`, `EnableUniformManagement`, `UniformSaveCooldown`. Money washing runs through cron (`WashMoneyCRON`). Salary payouts from society need es_extended `Config.EnableSocietyPayouts = true`.

## 8. esx_billing

Table `billing` (identifier, sender, target_type `player|society`, target, label, amount).
```lua
-- server, from another resource (server-to-server, trusted)
exports.esx_billing:BillPlayer(targetServerId, xPlayer.getIdentifier(), 'society_police', 'Speeding', 250)
exports.esx_billing:BillPlayerByIdentifier(targetIdentifier, senderIdentifier, 'society_police', 'Fine', 500)
TriggerEvent('esx_billing:sendBillToIdentifier', targetIdentifier, 'society_police', 'Fine', 500)  -- sender 'server'
```
Client-facing net event `esx_billing:sendBill(targetId, sharedAccountName, label, amount)` is validated (society permission, proximity, cooldown `Config.BillingCooldown`, daily quota, high-bill confirmation at `Config.HighBillConfirmationAmount` with token and timeout). Callbacks: `esx_billing:getBills`, `getTargetBills`, `payBill(billId)`, `respondHighBill(token, accepted)`.

## 9. esx_license, esx_status, esx_basicneeds

**esx_license** (server, tables `licenses`, `user_licenses`): events `esx_license:addLicense` (target, type, cb), `removeLicense` (target, type, cb — registered as a **net** event, guard it or call only server-side), `getLicense` (type, cb), `getLicenses` (target, cb), `checkLicense` (target, type, cb), `getLicensesList` (cb); matching callbacks `esx_license:getLicense`, `getLicenses`, `checkLicense`, `getLicensesList`.
**esx_status** (client-ticked statuses, saved in `users.status`): client `esx_status:registerStatus` (name, default, color, visible, tickCallback), `unregisterStatus`, `getStatus` (name, cb), `getAllStatus` (cb), `setDisplay` (val); net `esx_status:set/add/remove` (name, value) from the server; server `esx_status:getStatus` (src, name, cb), net `esx_status:update` (client → server, untrusted). Status values range 0–1000000.
**esx_basicneeds**: hunger/thirst on esx_status; usable items registered with `ESX.RegisterUsableItem`; `/heal [id]` (admin); handles `txAdmin:events:healedPlayer`.
Note: because esx_status values are ticked on the client and reported back, never use them for anything economically important.

## 10. Replacing ESX UI with ox_lib

| ESX | ox_lib equivalent |
|---|---|
| `ESX.ShowNotification(msg, type, ms)` | `lib.notify({ description = msg, type = type, duration = ms })` |
| `ESX.TextUI` / `ESX.HideUI` | `lib.showTextUI` / `lib.hideTextUI` |
| `ESX.Progressbar(msg, ms, opts)` | `lib.progressBar({ duration, label, anim, disable })` (returns bool, awaitable) |
| `ESX.OpenContext` / `ESX.UI.Menu 'default'` | `lib.registerContext` + `lib.showContext` / `lib.registerMenu` |
| `ESX.UI.Menu 'dialog'` | `lib.inputDialog` |
| `ESX.TriggerServerCallback` | `lib.callback` |
| `ESX.RegisterInput` | `lib.addKeybind` |
| `ESX.Point` | `lib.points.new` / `lib.zones` |
Keep the ESX resources started even if unused when other addons call `ESX.ShowNotification` etc.: the wrappers throw `Resource [esx_notify] is Missing!` when the resource is absent.

## 11. Security notes per resource

- `esx_skin:setWeight` trusts the client-sent skin to pick a backpack bonus (bounded by `Config.BackpackWeight`, so at most +25 kg by default).
- `esx_identity` debug commands (`/chardel` as `user`) must stay disabled (`EnableCommands` follows `EnableDebug`).
- `esx_addonaccount` `removeMoney` has no balance check and broadcasts balances to all clients.
- `esx_license:removeLicense` is a net event in the addon — audit before exposing.
- `esx_status:update` and progressbar completion are client-reported.
- Medal.tv integration in esx_lib is enabled by default (`esx_lib/config.lua`).

## 12. Sources

- https://github.com/esx-framework/esx_core (`[core]/*`, tag 1.15.2 / `main` fe59ca0)
- https://github.com/esx-framework/ESX-Legacy-Addons (`[esx_addons]/*`, `main` 2026-10-06)
- https://github.com/esx-framework/esx-recipes
- https://github.com/esx-framework/esx-legacy-documentation (pages `esx_core/*.mdx`, `esx_addons/*.mdx`)
- https://docs.esx-framework.org/en/tutorial/install
- https://github.com/esx-framework/esx_core/compare/main...v1.16.0
