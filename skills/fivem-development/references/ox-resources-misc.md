# ox_doorlock, ox_fuel and other overextended resources

Baseline: ox_doorlock v1.22.1 (2026-04-25) and ox_fuel v1.5.4 (2026-05-29) — verified 2026-10-07 against their sources, releases and overextended.dev docs. Other resources: GitHub org listing of 2026-10-07.

## Contents
1. ox_doorlock: install, config, UI
2. ox_doorlock: exports, events, hooks, state
3. ox_fuel: install, config
4. ox_fuel: state bag, exports, security note
5. Other overextended resources (status)
6. Sources

## 1. ox_doorlock: install, config, UI
- Dependencies: `oxmysql`, `ox_lib`; optional `ox_target` (lockpicking via target). Works standalone or with ox_core, qbx_core, es_extended, ND_Core (`server/framework/*.lua`). License GPL-3.0.
- Use the release zip (built UI) or `cd web && bun i && bun run build`.
- Table `ox_doorlock(id, name, data longtext)` — `sql/ox_doorlock.sql` (plus `default.sql`, `community_mrpd.sql` sample doors).
- `/doorlock` opens the editor UI; requires ACE `command.doorlock` (granted to `Config.CommandPrincipal`). Test with `test_ace player.1 command.doorlock`.
- Converting nui_doorlock configs: drop `.lua` files into `ox_doorlock/convert/` and start the resource (best effort).
- Config is a Lua file, `config.lua` (not convars):

| Key | Default | Meaning |
|---|---|---|
| `Config.Notify` | `false` | notify on state change |
| `Config.DrawTextUI` | `false` | persistent lock/unlock prompt in range |
| `Config.DrawSprite` | lock_open / lock_closed sprites | `DrawSprite` args per state |
| `Config.CommandPrincipal` | `'group.admin'` | principal allowed `command.doorlock` |
| `Config.PlayerAceAuthorised` | `false` | `command.doorlock` holders can use any door |
| `Config.LockDifficulty` | `{ 'easy', 'easy', 'medium' }` | ox_lib skill check |
| `Config.CanPickUnlockedDoors` | `false` | lockpick can also lock |
| `Config.LockpickItems` | `{ 'lockpick' }` | items counted as lockpicks |
| `Config.NativeAudio` | `true` | game audio (`audio/dlc_oxdoorlock`) instead of NUI `.ogg` |

Door settings (UI): name, passcode, autolock (seconds), interact distance, door rate, locked, double, automatic (sliding/garage), lockpick, hide UI, hold open; access by `characters` (framework char ids), `groups` (`{ name = minGrade }`), `items` (`{ name, metadata type?, remove? }`); lockpick difficulty/area/speed; lock/unlock sounds.

## 2. ox_doorlock: exports, events, hooks, state
Server exports (`exports.ox_doorlock:`):
| Export | Notes |
|---|---|
| `getDoor(id)` | door data table (id, name, state, coords, characters, groups, items, maxDistance, …) |
| `getDoorFromName(name)` | same, by name |
| `getAllDoors()` | array (not in docs) |
| `editDoor(id, data)` | merges fields (type-checked), saves to DB, syncs clients |
| `setDoorState(id, state, lockpick?)` | `state` = `true`/`1` lock, `false`/`0` unlock; returns bool. When called from an export there is no `source`, so it is authorised |
| `registerHook('doorAuthorization', cb, { print?, nameFilter? })` | returns numeric hookId |
| `removeResourceHook(id?)` | **source name**; the docs call it `removeHooks`, which does not exist in v1.22.1 |
| `createDoor(data)` / `removeDoor(id)` | **only on `main` after v1.22.1 (2026-06-28, PR #228) — not in any release yet** |

Client exports: `useClosestDoor()`, `pickClosestDoor()`, `getClosestDoor()` (door table), `getClosestDoorId()`, `getDoorIdFromEntity(entity)` (also `Entity(entity).state.doorId`, a client-local state set on door entities).

Events (listen only): server `ox_doorlock:stateChanged(source?, doorId, state, usedItem?)` (`source` nil for autolock/exports), `ox_doorlock:loaded`.
Hook `doorAuthorization` payload: `source`, `door`, `lockpick`, `authorised`. The last non-nil hook return is used, but v1.22.1 computes `authorised or hookResult` — **a hook can grant access, it cannot revoke access the built-in checks already granted**. Lockpick attempts return before the hook (item check only).
Authorisation order (`isAuthorised`): `Config.PlayerAceAuthorised` + `command.doorlock` → ACE `doorlock.<door name>` (e.g. `add_ace group.police "doorlock.mrpd locker rooms" allow`) → characters → groups → items → passcode prompt → hooks.
```lua
-- server: let property owners use their own doors
exports.ox_doorlock:registerHook('doorAuthorization', function(payload)
    local property = payload.door.name:match('^property_(%d+)$')
    if not property then return end
    return exports.myproperties:isOwner(payload.source, tonumber(property)) -- your own export
end, { nameFilter = '^property_%d+$' })

-- server: lock all bank doors on alarm
local door = exports.ox_doorlock:getDoorFromName('pacific_vault')
if door then exports.ox_doorlock:setDoorState(door.id, true) end
```
Security: the client net event `ox_doorlock:setState` is authorised server-side (`isAuthorised`: characters, groups, items, passcode, lockpick); never add your own unauthenticated "open door" net event — call `setDoorState` from your validated server code.

## 3. ox_fuel: install, config
- Dependencies: `ox_lib` (≥ 3.22.0) and **`ox_inventory` (≥ 2.30.0)** — petrol can is the `WEAPON_PETROLCAN` item, payment uses the `money` item by default. Optional ox_target. License GPL-3.0.
- `config.lua` (Lua, not convars): `versionCheck`, `ox_target` (false), `showBlips` (0 none / 1 nearest / 2 all), `refillValue` (0.50 % per tick), `refillTick` (250 ms), `priceTick` (5 per tick), `durabilityTick` (1.3 can durability per tick), `petrolCan = { enabled, duration, price, refillPrice }`, `globalFuelConsumptionRate` (10.0 → `SetFuelConsumptionRateMultiplier`), `pumpModels`. Stations in `data/stations.lua`.

## 4. ox_fuel: state bag, exports, security note
- Fuel is stored in the vehicle state bag **`fuel`** (0–100), set server-side and replicated; the client applies it with `SetVehicleFuelLevel`. 1.5.3/1.5.4 support strict state bags.
```lua
-- server (or client for reading)
local fuel = Entity(vehicle).state.fuel
-- server: set fuel (replicated)
Entity(vehicle).state:set('fuel', 100.0, true)
```
Other resources (garages, HUDs) should read/write this state instead of LegacyFuel exports; ox_fuel has no `GetFuel/SetFuel` exports.
- Client export `setMoneyCheck(function() return number end)` — replaces the money check (UX).
- Server export `setPaymentMethod(function(playerId, amount) return true|nil end)` — replaces payment (default: `RemoveItem(playerId, 'money', amount)`).
- Net events: `ox_fuel:pay(price, fuel, netid)`, `ox_fuel:fuelCan(hasCan, price)`, `ox_fuel:updateFuelCan(durability, netid, fuel)`, `ox_fuel:setFuel(fuel)`.
- **Security note (from source v1.5.4):** `ox_fuel:pay` and `ox_fuel:fuelCan` take `price` (and `fuel`) from the client; the server only asserts `price` is a number. A modified client can refuel cheaply. If that matters, enforce prices in your `setPaymentMethod` callback (recompute from the vehicle's previous `state.fuel` and the server config, clamp negatives) or patch the events. `ox_fuel:setFuel` can only reduce fuel (except for uninitialised vehicles).

## 5. Other overextended resources (status on 2026-10-07)
| Repo | Status |
|---|---|
| `ox_lib` 3.40.0, `oxmysql` 2.14 | maintained (see ox-lib.md, database-oxmysql.md) |
| `ox_banking` v1.0.6 (2026-04-24, MIT) | maintained; banking UI for **ox_core only** (shared/group accounts, transactions, invoices). TypeScript; its only script API is client `exports.ox_banking:openBank()` and `exports.ox_banking:openAtm()`. Wages, fines and transfers go through ox_core accounts (ox-core.md section 8), not ox_banking (source: `src/client/index.ts`) |
| `ox_mdt` | **work in progress**, only 2023 pre-releases (v0.3.0), ox_core only — not production-ready |
| `ox_commands` | no releases (`version '0.0.0'`), admin/utility commands; pushed 2026-04. Server `/freeze`, `/thaw` (`lib.addCommand`, restricted); client `/goback`, `/tpm`, `/setcoords`, `/coords`, `/noclip`, car menu |
| `ox_types`, `fivem-lls-addon`, `cfxlua-vscode`, `rage-lua-natives`, `fivem-ts`, `ox`, `fx-utils` | tooling (types, LLS natives, TS boilerplate) |
| `txAdminRecipe` | ox_core server recipe |
| `ox_inventory_v3` | TS/Svelte rewrite "for testing purposes only" (last push 2025-04) |
| `ox_vehicledealer`, `ox_property`, `ox_police`, `ox_identityapp`, `ox_core-example`, `ox_inventory_examples` | stale (last push 2022–2024) — treat as examples only |
| `qtarget` | deprecated: "Use ox_target instead." |
| `ox_appearance` | **not found** under `github.com/overextended` (HTTP 404). ox_core docs recommend illenium-appearance instead |

## 6. Sources
- https://github.com/overextended/ox_doorlock (v1.22.1 tag: `fxmanifest.lua`, `config.lua`, `server/main.lua`, `server/hooks.lua`; `main` for `createDoor`/`removeDoor`), https://github.com/overextended/ox_doorlock/releases
- https://overextended.dev/docs/ox_doorlock and https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_doorlock (index, settings, Client/functions, Server/events, Server/functions, Hooks)
- https://github.com/overextended/ox_fuel (v1.5.4: `fxmanifest.lua`, `config.lua`, `server.lua`, `client/*.lua`), https://github.com/overextended/ox_fuel/releases
- https://overextended.dev/docs/ox_fuel and https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_fuel
- https://github.com/overextended (repo list via `gh repo list overextended`), https://github.com/overextended/ox_banking, https://github.com/overextended/ox_mdt, https://github.com/overextended/ox_commands
