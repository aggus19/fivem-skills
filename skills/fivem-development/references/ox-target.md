# ox_target reference

Baseline: ox_target v1.18.1 (released 2026-04-25) — verified 2026-10-07 against the source (`main` has only a README commit since) and overextended.dev docs.

Repo https://github.com/overextended/ox_target (MIT) · Docs https://overextended.dev/docs/ox_target

## Contents
1. Install and convars
2. Option fields (TargetOption)
3. Callback data and action priority
4. Exports (client)
5. Examples (zones, models, entities, sub-menus, server validation)
6. qtarget / qb-target compatibility
7. Server side, state bags, performance
8. Changes 2024–2026
9. Sources

## 1. Install and convars
- Depends on ox_lib (server checks **ox_lib ≥ 3.30.0**). Manifest: `provide 'qtarget'`, `nui_callback_strict_mode 'true'` (1.18.0+). Release zip ships the built web UI.
- Start after ox_lib and the framework, before resources that call it (and before ox_inventory when `inventory:target` is true).
- Optional framework integration (groups/items checks) via `client/framework/`: **ox_core, es_extended, qbx_core, ND_Core**. No QBCore (`qb-core`) file.

| Convar (`setr`) | Default (source) | Meaning |
|---|---|---|
| `ox_target:toggleHotkey` | `0` | 1 = press to toggle instead of hold |
| `ox_target:defaultHotkey` | `LMENU` | keyboard mapper key (players can rebind in Settings → Key Bindings) |
| `ox_target:leftClick` | `1` | 1 = left click selects (control 24), 0 = right click (25) |
| `ox_target:drawSprite` | `24` | max zone sprites drawn per frame (`SetDrawOrigin` limit 32); `0` disables. Docs describe it as 0/1 |
| `ox_target:defaults` | `1` | built-in options (vehicle doors, etc. in `client/defaults.lua`) |
| `ox_target:debug` | `0` | debug options, entity outlines, raycast indicator |

## 2. Option fields (TargetOption)
Every `options` argument is one option table or an array of them.

| Field | Type | Notes |
|---|---|---|
| `label` | string | required |
| `name` | string | id used by `remove*` functions |
| `icon` / `iconColor` | string | Font Awesome class, e.g. `'fa-solid fa-car'` |
| `distance` | number | max distance in metres (default 7) |
| `bones` | string \| string[] | entity bone names (`GetEntityBoneIndexByName`) |
| `offset` | vector3 | relative offset: fraction of model dimensions (0–1 per axis, from `GetModelDimensions` min→max) |
| `absoluteOffset` | boolean | treat `offset` as a plain local offset in metres (`GetOffsetFromEntityInWorldCoords`). **The docs call this `offsetAbsolute` (vector3); the 1.18.1 source reads `option.absoluteOffset` as a flag** — use `offset` + `absoluteOffset = true` |
| `offsetSize` | number | radius around the offset point (default 1) |
| `groups` | string \| string[] \| `{ [name] = minGrade }` | framework groups (job/gang) |
| `items` | string \| string[] \| `{ [name] = count }` | required items (framework/ox_inventory) |
| `anyItem` | boolean | one of `items` is enough |
| `canInteract` | `function(entity, distance, coords, name, bone) -> boolean` | runs every refresh; keep it cheap; errors hide the option |
| `menuName` | string | only shown inside that sub-menu |
| `openMenu` | string | selecting opens sub-menu `openMenu` (a "go back" option is added) |
| `onSelect` | `function(data)` | highest priority action |
| `export` | string | `exports[resource][export](nil, data)` — resource = registering resource unless `resource` is set |
| `event` | string | `TriggerEvent(event, data)` |
| `serverEvent` | string | `TriggerServerEvent(serverEvent, data)` with `data.entity` converted to a **network id** (0 if not networked) |
| `command` | string | `ExecuteCommand(command)` |
| `resource` | string | override the resource for `export` |

Zones also accept `drawSprite = false`.

## 3. Callback data and action priority
Exactly one action runs, in order **onSelect → export → event → serverEvent → command**. `data` is a copy of the option (minus icon/groups/items/canInteract/callbacks) plus:
- `entity` (handle; net id for serverEvent), `coords` (hit position), `distance`, `zone` (zone id, if any).

Everything in `data` for `serverEvent` comes from the client — **re-validate on the server** (entity exists, distance, job, cooldown).

## 4. Exports (client)
| Export | Notes |
|---|---|
| `addBoxZone({ coords, size?, rotation?, name?, debug?, drawSprite?, options })` | returns zone id (ox_lib `lib.zones.box`) |
| `addSphereZone({ coords, radius?, name?, debug?, drawSprite?, options })` | returns id |
| `addPolyZone({ points, thickness? (4), name?, debug?, drawSprite?, options })` | returns id |
| `zoneExists(idOrName)` | bool |
| `removeZone(idOrName, suppressWarning?)` | by id or `name` |
| `addGlobalOption(options)` / `removeGlobalOption(names)` | shown on everything |
| `addGlobalPed` / `addGlobalVehicle` / `addGlobalObject` / `addGlobalPlayer (options)` | + matching `removeGlobal*(names)`; GlobalPed excludes players |
| `addModel(models, options)` / `removeModel(models, names?)` | model names or hashes |
| `addEntity(netIds, options)` / `removeEntity(netIds, names?)` | networked entities (sets `hasTargetOptions` state server-side) |
| `addLocalEntity(handles, options)` / `removeLocalEntity(handles, names?)` | local / non-networked entities |
| `getTargetOptions(entity?, entityType?, model?)` | `{ global, model, entity, localEntity }` |
| `disableTargeting(state)` | `true` closes and blocks targeting |
| `isActive()` | bool |

On `onClientResourceStop` ox_target removes that resource's zones, model/entity/local-entity options and global ped/vehicle/object/player options (`addGlobalOption` entries are not in that cleanup list in 1.18.1 — remove them yourself).

## 5. Examples
```lua
-- client.lua — duty toggle at a desk, police only
local dutyZone = exports.ox_target:addBoxZone({
    name = 'myres_mrpd_duty',
    coords = vec3(441.0, -981.1, 30.7),
    size = vec3(1.5, 1.5, 2.0),
    rotation = 0.0,
    options = {
        {
            name = 'myres:duty',
            label = 'Toggle duty',
            icon = 'fa-solid fa-clipboard',
            groups = { police = 0 },
            distance = 2.0,
            serverEvent = 'myres:server:toggleDuty',
        },
    },
})

AddEventHandler('onResourceStop', function(res)
    if res == cache.resource then exports.ox_target:removeZone(dutyZone) end
end)
```
```lua
-- server.lua — never trust the client payload
local DUTY_COORDS = vec3(441.0, -981.1, 30.7)
RegisterNetEvent('myres:server:toggleDuty', function(data)
    local src = source
    if not exports.qbx_core:HasGroup(src, 'police') then return end           -- Qbox example
    if #(GetEntityCoords(GetPlayerPed(src)) - DUTY_COORDS) > 3.0 then return end
    -- toggle duty here
end)
```
```lua
-- vehicles: trunk option near the rear, any job, needs a crowbar
exports.ox_target:addGlobalVehicle({
    {
        name = 'myres:pry_trunk',
        label = 'Pry trunk',
        icon = 'fa-solid fa-screwdriver',
        bones = { 'boot' },
        items = 'crowbar',
        distance = 1.5,
        canInteract = function(entity, distance)
            return GetVehicleDoorLockStatus(entity) == 2
        end,
        onSelect = function(data)
            TriggerServerEvent('myres:server:pryTrunk', NetworkGetNetworkIdFromEntity(data.entity))
        end,
    },
})

-- ATMs with a sub-menu
exports.ox_target:addModel({ `prop_atm_01`, `prop_atm_02`, `prop_atm_03` }, {
    { name = 'atm', label = 'ATM', icon = 'fa-solid fa-credit-card', openMenu = 'atm_menu' },
    { name = 'atm_withdraw', label = 'Withdraw', menuName = 'atm_menu', event = 'myres:client:withdraw' },
    { name = 'atm_deposit', label = 'Deposit', menuName = 'atm_menu', event = 'myres:client:deposit' },
})
```

## 6. qtarget / qb-target compatibility
- ox_target **provides `qtarget`** and implements its export names through `client/compat/qtarget.lua`: `AddBoxZone`, `AddPolyZone`, `AddCircleZone`, `RemoveZone`, `AddTargetBone`, `AddTargetEntity`, `RemoveTargetEntity`, `AddTargetModel`, `RemoveTargetModel`, `Ped`/`RemovePed`, `Vehicle`/`RemoveVehicle`, `Object`/`RemoveObject`, `Player`/`RemovePlayer`. Conversion: `action → onSelect` (receives the entity handle, not `data`), `job → groups`, `item`/`required_item → items`, `type = 'server'|'command'` → `serverEvent`/`command`, `name` defaults to `label`.
- It does **not** provide `qb-target`. Resources calling `exports['qb-target']` need porting (map `AddBoxZone(name, center, length, width, {heading, minZ, maxZ}, {options, distance})` → `addBoxZone({ coords, size = vec3(width, length, maxZ - minZ), rotation = heading, options })`, `job` → `groups`, `action` → `onSelect`, `type = 'server'` → `serverEvent`). Community qb-target shims exist but are **UNVERIFIED** here; Qbox's own compatibility layer for qb-target is also **UNVERIFIED** in this file (see framework-qbox.md).

## 7. Server side, state bags, performance
- Server script: version check, `ox_target:setEntityHasOptions` (sets `Entity(ent).state.hasTargetOptions` for `addEntity` targets, cleaned every 10 s when entities disappear → clients get `ox_target:removeEntity`), and `ox_target:toggleEntityDoor` (relays default door toggles to the entity owner).
- Zones use `lib.zones` with grid caching (1.17.2+). Prefer one zone with several options over many zones; keep `canInteract` free of heavy natives or server callbacks.
- ox_target only shows options; it is not authorisation. Groups/items checks are client-side UX — the server handler must re-check.

## 8. Changes 2024–2026
- 1.17.1 (2024-09), 1.17.2 (2025-03): `lib.zones` grid cache; refresh options when nearby zone hidden state changes.
- 1.18.0/1.18.1 (2026-04-25): repo moved back from CommunityOx to overextended; `nui_callback_strict_mode` enabled; invalid-entity warnings show the calling resource; options reset only on valid NUI messages. No export removals.

## 9. Sources
- https://github.com/overextended/ox_target (v1.18.1: `fxmanifest.lua`, `client/api.lua`, `client/main.lua`, `client/utils.lua`, `client/compat/qtarget.lua`, `server/main.lua`)
- https://github.com/overextended/ox_target/releases (v1.17.2, v1.18.1)
- https://overextended.dev/docs/ox_target and source https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_target (index, TargetOptions, Functions/Client)
