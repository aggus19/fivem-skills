# ox_inventory reference

Baseline: ox_inventory v2.48.0 (released 2026-10-03) — verified 2026-10-07 against the v2.48.0 source (`main` = tag, no newer commits) and overextended.dev docs.

Repo https://github.com/overextended/ox_inventory (GPL-3.0) · Docs https://overextended.dev/docs/ox_inventory

## Contents
1. Install, start order, framework support
2. Convars (complete list from source)
3. Item definitions (`data/items.lua`) and weapons data
4. Making items usable (client export, server export, framework usable items)
5. Server exports
6. Client exports, events, state bags
7. Hooks and post-hook events
8. Stashes, temporary stashes, drops, containers
9. Shops, crafting, evidence, licenses, vehicles, dumpsters
10. Metadata, durability, images
11. Inventory types and ids, persistence, database
12. Admin commands
13. Migration (ESX, QBCore/qb-inventory, Qbox)
14. Breaking and security changes 2024–2026
15. Performance and security notes
16. Sources

## 1. Install, start order, framework support
- Manifest dependencies: `/server:6116`, `/onesync`, `oxmysql`, `ox_lib`. On start it enforces **oxmysql ≥ 2.7.3** and **ox_lib ≥ 3.36.4** (`lib.checkDependency` in `init.lua`) and refuses to run if `web/build/index.html` is missing ("UI has not been built" → download the release `ox_inventory.zip`, not the source zip, or `cd web && bun i && bun run build`).
- Start order:
```cfg
ensure oxmysql
ensure ox_lib
ensure qbx_core      # or es_extended / ox_core / ND_Core
ensure ox_target     # optional, must start before ox_inventory if inventory:target is true
ensure ox_inventory
```
- `setr inventory:framework` accepts only the bridges shipped in `modules/bridge/`: **`ox`, `esx`, `qbx`, `nd`**. Default in source is `esx`. Anything else = "unsupported framework": copy `modules/bridge/ox` to `modules/bridge/<name>` and add your player/vehicle tables in `modules/mysql/server.lua`.
- **QBCore (`qb-core`) is not supported** — the `qb` bridge was deleted in v2.42.0 (2024-08). Use Qbox (`qbx`) or keep qb-inventory.
- qtarget is no longer supported: if `inventory:target` is true and `ox_target` is not started, targeting is disabled with a warning.

## 2. Convars (complete list from source)
All read in `init.lua` (plus `inventory:cleartime` in `modules/inventory/server.lua`). Use `setr` for shared/client ones, `set` for server-only. Defaults below are **source defaults** (the docs' sample cfg shows some non-default values, e.g. `randomprices true`, `dropprops true`).

Shared (`setr`):
| Convar | Default | Meaning |
|---|---|---|
| `inventory:framework` | `"esx"` | `ox` / `esx` / `qbx` / `nd` |
| `inventory:slots` | `50` | player slots |
| `inventory:weight` | `30000` | player max weight in grams (framework may override) |
| `inventory:dropslots` | = slots | slots in drops |
| `inventory:dropweight` | = weight | drop max weight |
| `inventory:target` | `false` | use ox_target for stashes/shops/crafting/evidence instead of markers |
| `inventory:police` | `["police", "sheriff"]` | groups with evidence/armoury access (JSON array or single string) |
| `inventory:networkdumpsters` | `false` | networked dumpster inventories (not recommended) |

Client (`setr`):
| Convar | Default | Meaning |
|---|---|---|
| `inventory:imagepath` | `nui://ox_inventory/web/images` | base path for item images |
| `inventory:autoreload` | `false` | reload weapon at 0 ammo |
| `inventory:screenblur` | `true` | blur while open |
| `inventory:keys` | `["F2","K","TAB"]` | primary, secondary, hotbar keys |
| `inventory:enablekeys` | `[249]` | control actions allowed while open (249 = push-to-talk) |
| `inventory:aimedfiring` | `false` | must aim before shooting |
| `inventory:giveplayerlist` | `false` | show nearby player list when giving |
| `inventory:weaponanims` | `true` | draw/holster anims |
| `inventory:itemnotify` | `true` | add/remove item notifications |
| `inventory:weaponnotify` | `true` | equip/holster notifications |
| `inventory:dropprops` | `false` | spawn prop instead of marker for drops |
| `inventory:dropmodel` | `prop_med_bag_01b` | drop prop model |
| `inventory:weaponmismatch` | `true` | disarm if a weapon not from an item is held |
| `inventory:ignoreweapons` | `[]` | weapons exempt from mismatch (UNARMED, HANDCUFFS, GARBAGEBAG, HOSE, OBJECT always exempt) |
| `inventory:suppresspickups` | `true` | suppress GTA weapon/ammo pickups |
| `inventory:disableweapons` | `false` | disable weapons for everyone |
| `inventory:enablestealcommand` | `true` | register `/steal` |
| `inventory:disablesetupnotification` | `false` | hide "Inventory is ready" |
| `inventory:gloveboxseatrestriction` | `0` | `1` = only front seats can open glovebox (added 2.48.0; not in docs yet) |
| `inventory:dropmarker` / `shopmarker` / `evidencemarker` / `craftingmarker` | JSON `{type, colour[3], scale[3]}` | marker look; invalid JSON → grey fallback |

Server (`set`):
| Convar | Default | Meaning |
|---|---|---|
| `inventory:versioncheck` | `true` | GitHub version check |
| `inventory:clearstashes` | `"6 MONTH"` | delete stashes unchanged for this SQL interval |
| `inventory:bulkstashsave` | `true` | batch stash saves |
| `inventory:cleartime` | `5` | minutes before an unused, unopened inventory is unloaded from memory |
| `inventory:loglevel` | `1` | ox_lib logger: 0 off, 1 standard, 2 + AddItem/RemoveItem and all purchases |
| `inventory:loghookrejection` | `true` | print when a hook rejects an action (not in docs) |
| `inventory:webhook` | `""` | Discord webhook for `imageurl` metadata moderation |
| `inventory:validhosts` | `{"r2.fivemanage.com":true,"i.fmfile.com":true}` | allowed `imageurl` hosts (enforced only with a webhook) |
| `inventory:randomprices` | `false` | shop prices ±20 % (money currency only) |
| `inventory:randomloot` | `true` | loot in unowned vehicles / dumpsters |
| `inventory:vehicleloot` / `dumpsterloot` | JSON `[[name, min, max, chance?], ...]` | loot tables |
| `inventory:evidencegrade` | `2` | min grade to take from evidence lockers |
| `inventory:trimplate` | `true` | trim plate whitespace for vehicle inventory ids |
| `inventory:accounts` | `["money"]` | items synced with framework accounts |

`init.lua` says "do not modify this file" — configure only with convars.

## 3. Item definitions (`data/items.lua`) and weapons data
Key = item name (lowercase recommended). Server and client both load the file; functions in `client`/`buttons` only run client-side.

| Field | Type / default | Notes |
|---|---|---|
| `label` | string | required |
| `weight` | number, `0` | grams |
| `stack` | bool, `true` | `false` = one per slot |
| `close` | bool, `true` | close inventory on use |
| `description` | string | tooltip (supports markdown) |
| `consume` | number | count removed on use; default `1` if the item has `client.status/usetime/export` or `server.export`; `0` = never removed; `0 < x < 1` = consume that fraction of durability (0.2 = 20 %) |
| `degrade` | minutes | item degrades to 0 over this time (sets durability as an expiry timestamp) |
| `decay` | bool | delete when durability hits 0 |
| `durability` | bool | forced on when `degrade` or fractional `consume` |
| `allowArmed` | bool | allow use while holding a weapon |
| `client.status` | table | e.g. `{ hunger = 200000 }` (applied by the framework bridge: esx_status / qbx / nd) |
| `client.anim` | `{ dict, clip, flag? }` or preset string | presets in `data/animations.lua` (`'eating'`) |
| `client.prop` / `client.propTwo` | `{ model, pos, rot, bone?, rotOrder? }` or preset string (`'burger'`) | propTwo merges into a prop array |
| `client.scenario` | string | scenario during use |
| `client.disable` | `{ move, car, combat, mouse, sprint }` | during progress |
| `client.usetime` | ms | progress duration |
| `client.cancel` | bool | progress cancellable |
| `client.notification` | string | notify after use |
| `client.image` | string | file in `inventory:imagepath`, or full `scheme://` URL |
| `client.export` | `'resource.exportName'` | client callback (section 4) |
| `client.event` | string | client event fallback when no export |
| `client.add(total)` / `client.remove(total)` | function | fires when count changes |
| `client.useWhileDead` | bool | passed to `lib.progressBar` (read in `client.lua`; not in docs) |
| `server.export` | `'resource.exportName'` | server callback (section 4) |
| `buttons` | `{ { label, action = function(slot) end, group? } }` | right-click context buttons; `group` nests them |

```lua
-- ox_inventory/data/items.lua
['bandage'] = {
    label = 'Bandage',
    weight = 115,
    client = {
        anim = { dict = 'missheistdockssetup1clipboard@idle_a', clip = 'idle_a', flag = 49 },
        prop = { model = `prop_rolled_sock_02`, pos = vec3(-0.14, -0.14, -0.08), rot = vec3(-50.0, -50.0, 0.0) },
        disable = { move = true, car = true, combat = true },
        usetime = 2500,
    },
},
['water'] = {
    label = 'Water', weight = 500,
    client = { status = { thirst = 200000 }, anim = { dict = 'mp_player_intdrink', clip = 'loop_bottle' },
        prop = { model = `prop_ld_flow_bottle`, pos = vec3(0.03, 0.03, 0.02), rot = vec3(0.0, 0.0, -1.5) },
        usetime = 2500, cancel = true, notification = 'You drank some refreshing water' },
},
```
`ItemList.cash` is an alias of `money` internally.

**Weapons data** (`data/weapons.lua`) has sections `Weapons`, `Components`, `Ammo`:
- Weapons: `label`, `weight`, `durability` (loss per shot, default 0.05), `ammoname` (ammo item, e.g. `'ammo-9'`), `throwable` (stackable), `model`, `anim`, `client.image`. Weapons never stack (except throwables), get a `serial` and `registered` (buyer name) when bought.
- Components: `label`, `weight`, `type` (e.g. `'flashlight'`), `client = { component = { `COMPONENT_...`, ... }, usetime }` — first hash compatible with the held weapon is applied.
- Ammo: `label`, `weight`. Using ammo loads the current weapon.

## 4. Making items usable
1. **Client export** (UX checks, then hand back to ox_inventory):
```lua
-- items.lua: client = { export = 'myres.bandage' }
-- myres/client.lua
exports('bandage', function(data, slot)
    local ped = cache.ped
    local maxHealth = GetEntityMaxHealth(ped)
    local health = GetEntityHealth(ped)
    if health >= maxHealth then
        return lib.notify({ type = 'error', description = 'You do not need a bandage' })
    end
    exports.ox_inventory:useItem(data, function(result)
        if not result then return end -- server refused (count, durability, hooks...)
        SetEntityHealth(ped, math.min(maxHealth, math.floor(health + maxHealth / 16)))
    end)
end)
```
Calling `useItem` runs the server checks, progress bar, anim/prop and removal; skipping it means the item is never consumed.
2. **Server export** — signature `function(event, item, inventory, slot, data)`; `event` is `'usingItem'` (return `false` to cancel; any other non-nil return is sent to the client as `data.server`), `'usedItem'` (after consumption) or `'buying'` (shop purchase; `data` = shop):
```lua
-- items.lua: server = { export = 'myres.lockpick' }
exports('lockpick', function(event, item, inventory, slot, data)
    if event == 'usingItem' then
        local src = inventory.id                    -- player inventory id = server id
        if (Player(src).state.lockpickCooldown or 0) > os.time() then return false end
    elseif event == 'usedItem' then
        Player(inventory.id).state:set('lockpickCooldown', os.time() + 10, false)
    end
end)
```
3. **Framework usable items** still work for items with no `consume` logic: ESX `ESX.RegisterUsableItem`, Qbox `exports.qbx_core:CreateUseableItem` (called through `server.UseItem`).
4. `Item(name, cb)` inside `modules/items/server.lua` is **deprecated** — use exports, the `usingItem`/`buyItem` hooks or the `ox_inventory:usedItem` event.

## 5. Server exports
`inv` = player server id, inventory id string, or `{ id = 'stash', owner = 'x' }`. Cache once: `local ox_inventory = exports.ox_inventory`.

| Export | Returns / notes |
|---|---|
| `AddItem(inv, item, count, metadata?, slot?, cb?)` | `success, response` (or via `cb`); response = slot data or `'invalid_item'`, `'invalid_inventory'`, `'inventory_full'`. String metadata becomes `{ type = str }`. Use `CanCarryItem` first; for stash/trunk/glovebox ensure it is loaded (`GetInventory`). |
| `RemoveItem(inv, item, count, metadata?, slot?, ignoreTotal?, strict?)` | `success, response` (`'invalid_item'`, `'invalid_inventory'`, `'not_enough_items'`); `strict` defaults true |
| `SetItem(inv, item, count, metadata?)` | adds/removes to reach `count` (undocumented export) |
| `CanCarryItem(inv, item, count, metadata?)` | bool (weight + slots) |
| `CanCarryAmount(inv, item)` | number by weight |
| `CanCarryWeight(inv, weight)` | `canCarry, freeWeight` |
| `CanSwapItem(inv, firstItem, firstCount, testItem, testCount)` | bool |
| `GetItem(inv, item, metadata?, returnsCount?)` | item def + total `count`, or number |
| `GetItemCount(inv, itemName, metadata?, strict?)` | number |
| `Search(inv, 'slots'\|'count', items, metadata?)` | slots table / count; array of names → keyed by name |
| `GetItemSlots(inv, item, metadata?)` | `slots, totalCount, emptySlots` |
| `GetSlot(inv, slot)` | slot table or nil |
| `GetSlotForItem(inv, name, metadata?)` | matching stack slot or empty slot id |
| `GetSlotWithItem` / `GetSlotIdWithItem` / `GetSlotsWithItem` / `GetSlotIdsWithItem (inv, name, metadata?, strict?)` | first slot / id / all slots / all ids |
| `GetEmptySlot(inv)` | slot id or nil |
| `GetContainerFromSlot(inv, slotId)` | container inventory |
| `SetMetadata(inv, slot, metadata)` | replaces metadata (send the whole table) |
| `SetDurability(inv, slot, durability)` | 0–100 |
| `SetSlotCount(inv, slots)` / `SetMaxWeight(inv, maxWeight)` | resize |
| `SwapSlots(fromInv, toInv, slot1, slot2)` | low-level, expects inventory objects (undocumented) |
| `GetInventory(inv, owner?)` / `Inventory(inv)` | inventory object or nil |
| `GetInventoryItems(inv, owner?)` | items table |
| `GetInventories(invType, detailed?)` | ids (or full objects) of loaded inventories of a type — **new in 2.48.0** |
| `GetCurrentWeapon(inv)` | equipped weapon slot or nil |
| `RegisterStash(id, label, slots, maxWeight, owner?, groups?, coords?, instance?)` | section 8 |
| `CreateTemporaryStash(properties)` | inventory id |
| `CustomDrop(prefix, items, coords, slots?, maxWeight?, instance?, model?)` | creates a drop |
| `CreateDropFromPlayer(playerId)` | drop id |
| `RegisterShop(shopType, shopDetails)` | section 9 |
| `ClearInventory(inv, keep?)` | `keep` = name or array |
| `ConfiscateInventory(src)` / `ReturnInventory(src)` | moves to/from a hidden stash |
| `RemoveInventory(inv)` | unload (saves unless temp/dumpster/drop) |
| `UpdateVehicle(oldPlate, newPlate)` | rename trunk/glovebox refs in memory |
| `InspectInventory(viewerId, invId)` | source: `(playerId, invId)` — the first arg opens a read-only view of `invId` (docs label the args `target, source`; trust the source) |
| `forceOpenInventory(playerId, invType, data)` | opens without group/coords checks |
| `setPlayerInventory(player, data?)` | for custom bridges (`player = { source, identifier, name, groups?, sex?, dateofbirth? }`) |
| `ConvertItems(playerId, items)` | old `{name=count}` → slot array (bridge-dependent) |
| `Items(name?)` / `ItemList(name?)` | item definitions (avoid fetching all repeatedly) |
| `setContainerProperties(itemName, { slots, maxWeight, whitelist?, blacklist? })` | define container items at runtime |
| `registerHook(event, cb?, options?)` / `removeHooks(id?)` | section 7 |
| pefcl compat: `addCash`, `removeCash`, `getCash`, `getCards`, `giveCard`, `getBank` | only for pefcl integration |

```lua
-- server: give a reward safely
local ox_inventory = exports.ox_inventory
RegisterNetEvent('myjob:server:collect', function()
    local src = source
    if not ox_inventory:CanCarryItem(src, 'scrap', 3) then
        return TriggerClientEvent('ox_lib:notify', src, { type = 'error', description = 'Inventory full' })
    end
    local ok, resp = ox_inventory:AddItem(src, 'scrap', 3, { quality = math.random(60, 100) })
    if not ok then lib.print.warn(('AddItem failed for %s: %s'):format(src, resp)) end
end)
```

## 6. Client exports, events, state bags
Client exports (`exports.ox_inventory:`):
- `openInventory(invType, data)` — types `player`, `shop` (`{ type = 'General', id = 1 }`), `stash` (`'id'` or `{ id, owner }`), `crafting` (`{ id = 'bench', index = 1 }`), `container`, `drop`, `glovebox`/`trunk` (**`{ netid = NetworkGetNetworkIdFromEntity(veh) }`** — raw string ids for vehicle inventories are rejected since 2.48.0), `dumpster`, `policeevidence` (`1` or nil for a dialog). Returns `false` if the stash is not registered.
- `closeInventory()`, `openNearbyInventory()`, `useItem(data, cb)`, `useSlot(slot)`, `setStashTarget(id, owner?)`, `getCurrentWeapon()`, `giveItemToTarget(serverId, slotId, count?)`, `weaponWheel(state)`.
- Queries (UX only — never trust for rewards): `Search('slots'|'count', items, metadata?)`, `GetItemCount(name, metadata?, strict?)`, `GetPlayerItems()`, `GetPlayerWeight()`, `GetPlayerMaxWeight()`, `GetSlotWithItem`, `GetSlotIdWithItem`, `GetSlotsWithItem`, `GetSlotIdsWithItem`, `Items(name?)`.
- UI: `displayMetadata(key|table|array, label?)`, `notify(data)`, `suppressItemNotifications(bool)`, `setGetPlayerNameMethod(function(serverId) return name end)`.
- Legacy wrappers kept for compatibility: `Keyboard` (= `lib.inputDialog`), `Progress`, `CancelProgress`, `ProgressActive` — use ox_lib directly.

Client events you may handle: `ox_inventory:updateInventory(changes)` (slot → data/false), `ox_inventory:currentWeapon(weapon?)`, `ox_inventory:itemCount(name, total)` (not on ESX — use `esx:addInventoryItem`/`esx:removeInventoryItem`), `ox_inventory:updateWeaponComponent(action, hash, item)`, `ox_inventory:usedItem(name, slot, metadata?)`.
Safe to trigger from the server: `TriggerClientEvent('ox_inventory:disarm', id, noAnim)`, `TriggerClientEvent('ox_inventory:suppressItemNotifications', id, bool)`, `TriggerClientEvent('ox_inventory:openInventory', id, invType, data)`.
Server events (listen only): `ox_inventory:openedInventory(playerId, inventoryId)`, `ox_inventory:closedInventory(playerId, inventoryId)`, `ox_inventory:usedItem(playerId, name, slot, metadata?)`.

Player state bags: `invBusy` (set true to block opening), `invHotkeys` (false disables hotbar), `invOpen` (read), `canUseWeapons` (false blocks weapons), `instance` (drops/stashes isolation), `canSteal` (set by ox_inventory when the target is robbable). Set authoritative values **from the server** (`Player(src).state:set('instance', id, true)`); with `sv_stateBagStrictMode` clients cannot spoof them.

## 7. Hooks and post-hook events
```lua
local hookId = exports.ox_inventory:registerHook(event, function(payload) ... end, options)
```
- `options`: `print` (bool), `itemFilter` (`{ name = true }`), `inventoryFilter` (array of Lua patterns, matched against from/to inventory ids), `typeFilter` (`{ stash = true }`, matched against `inventoryType`/`shopType`/`fromType`).
- Returns `hookId` = `'<resource>:<event>:<index>'` (format since 2.47.0); the payload also carries `hookId`. Hooks are auto-removed when the registering resource stops; `removeHooks(id?)` removes your own.
- Return `false` to reject (except `createItem`, where returning a table replaces metadata). Callbacks taking ≥ 10 ms print a warning.
- **Since 2.47.0 hooks are validation-only**: no item changes, DB writes or rewards inside a hook — the action can still fail or be rejected by another hook. The callback may be `nil` when you only need filters + post-event.

| Event | Payload |
|---|---|
| `swapItems` | `source, action ('move'\|'stack'\|'swap'\|'give'), fromInventory, toInventory, fromType, toType, fromSlot, toSlot, count` (+ `dropId` when `toInventory == 'newdrop'`) |
| `openInventory` | `source, inventoryId, inventoryType` (+ `slot` for containers, `netId` for vehicles) |
| `openShop` | `source, shopId, shopType, label, slots, items, groups?, coords?, distance?` |
| `buyItem` | `source, shopType, shopId, toInventory, toSlot, fromSlot, itemName, metadata, count, price, totalPrice, currency?` |
| `createItem` | `inventoryId?, metadata, item, count, resource` (invoking resource, 2.47.0) |
| `craftItem` | `source, benchId, benchIndex, recipe{name,count,duration,ingredients,slot,weight}, toInventory, toSlot` |
| `usingItem` | `source, inventoryId, item{name,label,weight,count,stack,close,slot,metadata}, consume` |

**Post-hook events** (2.47.0+): the `hookId` is also an event name fired after all hooks ran and the action finished, ~50 ms later (2.47.3), with `success` false if rejected or failed:
```lua
-- server: block evidence lockers for non-police, log afterwards
local hookId = exports.ox_inventory:registerHook('swapItems', function(payload)
    if payload.toType == 'stash' and type(payload.toInventory) == 'string'
        and payload.toInventory:find('^evidence_') and not exports.qbx_core:HasGroup(payload.source, 'police') then
        return false
    end
end, { inventoryFilter = { '^evidence_[%w_]+' } })

AddEventHandler(hookId, function(success, payload)
    if success then lib.logger(payload.source, 'evidence', json.encode(payload.fromSlot)) end
end)
```

## 8. Stashes, temporary stashes, drops, containers
```lua
-- server (re-register when ox_inventory restarts)
local function registerStashes()
    exports.ox_inventory:RegisterStash('police_armory', 'Armory', 50, 200000, nil, { police = 2 }, vec3(452.3, -991.4, 30.7))
    exports.ox_inventory:RegisterStash('personal_locker', 'Locker', 30, 50000, true)          -- one per player
    exports.ox_inventory:RegisterStash('apt_12', 'Apartment 12', 40, 80000, nil, nil, nil, 'apt_12') -- instance-gated
end
AddEventHandler('onServerResourceStart', function(res)
    if res == 'ox_inventory' or res == cache.resource then registerStashes() end
end)
```
- `owner`: `nil`/`false` shared; `true` per player (id becomes `name:owner`, owner = player identifier/charId from the bridge); string = fixed owner. **`owner` is not access control** — use `groups`, `coords`, `instance` or the `openInventory` hook.
- `groups`: `{ police = 0 }` min grade, or a grade array `{ police = { 2, 4 } }` (exact grades, since 2.45.1).
- `coords`: vector3 or array; the player must be close.
- `instance` (2.47.0): only players whose `Player(src).state.instance` equals it can open; secure only with `sv_stateBagStrictMode true` so clients cannot set their own state.
- Client opens with `exports.ox_inventory:openInventory('stash', 'police_armory')` or `{ id = 'personal_locker', owner = ... }`.
- `CreateTemporaryStash({ label, slots, maxWeight, owner?, groups?, coords?, instance?, items = { { 'water', 2 }, { 'ammo-9', 30, { } } } })` → id `temp...`; never saved.
- `CustomDrop('Carcass', { { 'meat', 5, { grade = 2 } } }, coords, slots?, maxWeight?, instance?, model?)`.
- Containers: give an item `stack = false, consume = 0`, then `setContainerProperties('pizzabox', { slots = 1, maxWeight = 1000, whitelist = { 'pizza' } })` (or `modules/items/containers.lua`). The container id is stored in `metadata.container`, size in `metadata.size`.
- Static stashes can also live in `data/stashes.lua` (`coords, target{loc,length,width,heading,minZ,maxZ,label}, name, label, owner, slots, weight, groups`).

## 9. Shops, crafting, evidence, licenses, vehicles, dumpsters
**Shops** (`data/shops.lua` or runtime `RegisterShop(shopType, details)`):
```lua
exports.ox_inventory:RegisterShop('PoliceArmory', {
    name = 'Police Armory',
    groups = { police = 0 },
    inventory = {
        { name = 'WEAPON_PISTOL', price = 500, metadata = { registered = true }, license = 'weapon' },
        { name = 'ammo-9', price = 5 },
        { name = 'radio', price = 100, currency = 'black_money', count = 10, grade = 3 },
    },
    locations = { vec3(451.5, -980.0, 30.7) },
})
```
Item fields: `name, price, currency?` (item used as money), `count?` (stock), `license?`, `metadata?`, `grade?` (number or array; requires `groups`). Shop fields: `name, blip{id,colour,scale}?, groups?, inventory, locations? (markers), targets? (ox_target box zones `{loc,length,width,heading,minZ,maxZ,distance}` or peds `{ped,scenario,loc,heading}`), model? (vending models)`. Runtime shops get no blips/markers/zones and must use `locations`. Open: `openInventory('shop', { type = 'PoliceArmory', id = 1 })`. Prices are server-side; validate extra rules in `buyItem`/`openShop` hooks.

**Crafting** (`data/crafting.lua`): `{ name, items = { { name, ingredients = { garbage = 3, WEAPON_HAMMER = 0.1 }, duration, count (number or {min,max}), metadata } }, points = {vec3...}, zones = { {coords,size,rotation,distance,label,icon} }, groups, blip }`. Ingredient value ≥1 = count consumed, 0–1 = durability fraction, 0 = required only. Open: `openInventory('crafting', { id = 'crafting-bench', index = 1 })`. Since 2.47.0 ingredients are locked during crafting.

**Evidence**: `data/evidence.lua` lockers; ids `evidence-<n>`; access requires `inventory:police` groups; taking items requires `inventory:evidencegrade`. `/clearevidence <locker>` admin command.

**Licenses** (`data/licenses.lua`): `{ name = 'weapon', coords, price }` purchasable through the bridge (`server.buyLicense`, implemented by all four bundled bridges; a custom bridge without it warns "Licenses are not supported").

**Vehicles** (`data/vehicles.lua`): `Storage[model] = 0..3` (0 none, 1 no trunk, 2 no glovebox, 3 trunk in hood), `glovebox[class] = { slots, maxWeight }`, `trunk[class]`, plus `models` overrides. Glovebox requires being inside the vehicle; trunk requires lock status 0/1/8 and ≤16 m.

**Dumpsters**: non-networked by default (id `dumpster<netid>`), random loot from `inventory:dumpsterloot`.

## 10. Metadata, durability, images
Special metadata keys: `label`, `weight` (overrides item weight), `description`, `image` (file name), `imageurl` (external URL; moderated via webhook/validhosts), `type` (tooltip corner; string metadata in `AddItem` sets this), `durability` (0–100, or a Unix expiry timestamp for `degrade` items), `degrade`, `ammo`, `components` (array of component item names), `serial`, `registered`, `container`, `size`.
```lua
exports.ox_inventory:AddItem(src, 'WEAPON_CARBINERIFLE', 1, { ammo = 30, components = { 'at_flashlight', 'at_suppressor_heavy' } })
-- client: show custom keys in the tooltip
exports.ox_inventory:displayMetadata({ quality = 'Quality', vin = 'VIN' })
```
Metadata is matched with `strict` (exact) or partial matching in the `GetSlot*`/`GetItemCount` family. Images: PNG in `ox_inventory/web/images/<item>.png` (the manifest ships `web/images/*.png`), or change `inventory:imagepath` to a CDN.

## 11. Inventory types and ids, persistence, database
| Type | Id format |
|---|---|
| `player` | server id (number) |
| `stash` | stash name, or `name:owner` for owned stashes |
| `temp` | `temp…` (temporary stash; opened as `stash`) |
| `glovebox` / `trunk` | `glove<PLATE>` / `trunk<PLATE>` (trimmed plate) |
| `drop` / `newdrop` | generated `drop…` |
| `container` | `metadata.container` of the item |
| `policeevidence` | `evidence-<n>` |
| `dumpster` | `dumpster<netid>` |
| `shop`, `crafting` | shop / bench definitions |
The server rejects requests whose requested type differs from the real one (`LogExploit`).

Persistence: autosave every **5 minutes**, on txAdmin scheduled restart/shutdown, when online players reach 0, and with `/saveinv` (`saveinv 1` also locks inventories). A crash or plain `quit` loses up to 5 min.
Tables: `ox_inventory(owner, name, data, lastupdated)` for stashes (auto-created); player inventory in the framework table — ox: `character_inventory.inventory` (charid), esx: `users.inventory` (identifier), qbx: `players.inventory` (citizenid), nd: `nd_characters` (charid); vehicles: `trunk`/`glovebox` columns of `owned_vehicles` (plate) / `player_vehicles` (id) / `vehicles` (id) / `nd_vehicles` (id).

## 12. Admin commands
`/giveitem` (`/additem`) `<id> <item> [count] [type]`, `/removeitem`, `/setitem`, `/clearinv <invId>`, `/takeinv <id>`, `/returninv` (`/restoreinv`), `/saveinv [lock]`, `/viewinv <invId>`, `/clearevidence <locker>` (ox_lib commands, `group.admin`), console-only `convertinventory esx|esxproperty|linden`, and `/steal` (players, toggle with convar).

## 13. Migration
- **ESX Legacy (1.6.0+)**: start ox_inventory right after es_extended, run `convertinventory esx` (and optionally `esxproperty`) in the server console, restart. Loadouts disappear (weapons are items); esx_shops, esx_weaponshop, esx_policejob stashes, esx_inventoryhud, esx_trunkinventory are incompatible. `xPlayer.getInventoryItem/addInventoryItem` still work through the bridge but are deprecated — call ox_inventory exports directly. Whether the current ESX build needs an extra config flag to hand inventory over to ox_inventory is **UNVERIFIED** here — check the ESX docs.
- **QBCore / qb-inventory**: no bridge since v2.42.0 and no `qb` conversion argument. Realistic paths: migrate the server to **Qbox** (qbx_core, which uses ox_inventory) or stay on qb-inventory. Qbox-side migration tooling is **UNVERIFIED** here — see framework-qbox.md.
- **Qbox**: `setr inventory:framework "qbx"`, start right after qbx_core. Use `exports.qbx_core:CreateUseableItem` or ox_inventory exports.
- **ox_core / ND**: `ox` / `nd`.
- Typical rewrites: `xPlayer.getInventoryItem(x).count` → `ox_inventory:GetItemCount(src, x)`; `Player.Functions.AddItem` → `AddItem` + `CanCarryItem`; qb-target stash zones → `RegisterStash` + ox_target.

## 14. Breaking and security changes 2024–2026
| Version (date) | Change |
|---|---|
| 2.40.0 (2024-05) | convars `dropslots`/`dropweight`, `disableweapons` |
| 2.41.0 (2024-07) | `forceOpenInventory` export usable globally |
| **2.42.0 (2024-08)** | **QBCore bridge removed**; qbx_core support added |
| 2.43.0 (2024-11) | `usingItem` hook; vehicle inventory access tightened (plate no longer sent by client) |
| 2.44.0 (2025-01) | non-networked dumpsters (`inventory:networkdumpsters`), crafting benches keyed by name, `benchName` in craftItem |
| 2.45.1 (2026-04) | first release after the move back from CommunityOx: marker convars, `enablestealcommand`, `disablesetupnotification`, `suppressItemNotifications`, `setContainerProperties` export, `openShop` hook, crafting zone groups, grade arrays in `hasGroup`, player-inventory access security fixes, dupe fix on failed swap; web build uses bun |
| **2.46.0 (2026-05-03)** | **drop duplication exploit fixed**, `LogExploit` logging — update anything older |
| **2.47.0 (2026-05-14)** | stash `instance`; hooks declared validation-only; **post-hook events**; new hookId format; locks around useItem/crafting; `createItem` payload gets `resource` |
| 2.47.3 → **2.47.6** | post-hook events delayed; 2.47.3 introduced a dupe via swap delay, **fixed in 2.47.6** (atomic swapItems, no dirty saves from yielding hooks) — never run 2.47.3–2.47.5 |
| 2.47.4/2.47.5 | strict state bag support; requires ox_lib 3.36.0 → 3.36.4 |
| 2.47.8–2.47.9 | count normalised to positive integers; per-inventory saves awaited |
| **2.48.0 (2026-10-03)** | `GetInventories` export, `inventory:gloveboxseatrestriction`; **vehicle inventories can no longer be opened with a raw string id or client-supplied id** (use `{ netid = ... }`); items cannot be used / weapons unloaded while another item is in use |

## 15. Performance and security notes
- Cache `local ox_inventory = exports.ox_inventory`; prefer one `Search(src, 'count', { 'a', 'b' })` over several calls; avoid `Items()` with no argument in hot paths.
- Hooks run synchronously in the action path: always use `itemFilter`/`inventoryFilter`/`typeFilter`, keep callbacks <1 ms, no DB queries or `Wait` (a warning prints at 10 ms).
- Do side effects in post-hook events, not hooks.
- Never trust client counts, prices, slots or inventory ids in your own events; re-check with server exports and check distance/ownership.
- Use `forceOpenInventory` only after your own permission checks — it skips groups and coords.
- Enable `sv_stateBagStrictMode` (and set states server-side) when relying on `instance`, `invBusy` or `canUseWeapons` for security.
- Keep `inventory:loglevel` ≥1 and watch `LogExploit` output (2.46.0+).

## 16. Sources
- https://github.com/overextended/ox_inventory (tag v2.48.0: `init.lua`, `server.lua`, `client.lua`, `modules/hooks/server.lua`, `modules/inventory/server.lua`, `modules/items/shared.lua`, `modules/items/server.lua`, `modules/shops/server.lua`, `modules/crafting/server.lua`, `modules/mysql/server.lua`, `modules/bridge/*`, `setup/convert.lua`, `data/*.lua`)
- https://github.com/overextended/ox_inventory/releases (v2.38.0 – v2.48.0 notes)
- https://github.com/overextended/ox_inventory/commit/ (2024-08-05 "cure cancer" — QBCore bridge removal, via commits API on `modules/bridge/qb/server.lua`)
- https://overextended.dev/docs/ox_inventory and docs source https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_inventory (index, Functions/Server, Functions/Server/Hooks, Functions/Client, Events, Guides/creatingItems, metadata, shops, stashes, crafting, Frameworks/esx, Frameworks/qbx, issues)
