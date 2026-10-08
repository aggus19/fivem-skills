# Framework detection and the bridge (adapter) pattern

Baseline: qbx_core 1.24.0 · es_extended 1.15.2 · qb-core (2026-05 refactor) · ox_inventory 2.48.0 — verified 2026-10-07.

Goal: one resource that runs on **Qbox, QBCore, ESX, ox_core or standalone** without framework calls scattered through the code. The template in `assets/templates/resource-lua/bridge/` implements this pattern.

## Contents
1. Detecting the framework
2. Bridge contract
3. Layout
4. Rules
5. Inventory and target detection

## 1. Detecting the framework
Order matters: **qbx_core before qb-core** (Qbox `provide`s `qb-core`, so `GetResourceState('qb-core')` can report started on Qbox).
```lua
local function detect()
    local forced = GetConvar('myres:framework', 'auto')            -- allow override: setr myres:framework "esx"
    if forced ~= 'auto' then return forced end
    if GetResourceState('qbx_core') == 'started' then return 'qbx' end
    if GetResourceState('es_extended') == 'started' then return 'esx' end
    if GetResourceState('qb-core') == 'started' then return 'qb' end
    if GetResourceState('ox_core') == 'started' then return 'ox' end
    if GetResourceState('ND_Core') == 'started' then return 'nd' end
    return 'standalone'
end
```
Use `'starting'` too if your resource can start before the framework (or declare the dependency).
Also inspect the user's `server.cfg`/resources folder when writing code for them — ask if unclear.

## 2. Bridge contract (keep it small)
Server:
| Function | Purpose |
|---|---|
| `Bridge.GetPlayer(src)` | raw framework player or nil |
| `Bridge.GetIdentifier(src)` | stable character id (citizenid / ESX identifier / charId / license) |
| `Bridge.GetName(src)` | character name |
| `Bridge.GetJob(src)` | `{ name, grade, label, onDuty }` |
| `Bridge.HasJob(src, name, minGrade?)` | |
| `Bridge.GetMoney(src, account)` | `account`: `cash` / `bank` (map ESX `money`) |
| `Bridge.AddMoney(src, account, amount, reason)` / `Bridge.RemoveMoney(...)` | return boolean |
| `Bridge.AddItem(src, item, count, metadata?)` / `Bridge.RemoveItem(...)` / `Bridge.HasItem(...)` | prefer ox_inventory if started |
| `Bridge.Notify(src, msg, type)` | |
| `Bridge.RegisterUsableItem(name, fn)` | |
Client:
| `Bridge.GetPlayerData()`, `Bridge.IsLoggedIn()`, `Bridge.Notify(msg, type)`, `Bridge.OnPlayerLoaded(fn)`, `Bridge.OnPlayerUnload(fn)`, `Bridge.OnJobUpdate(fn)` |

## 3. Layout
```
bridge/
├── init.lua              # shared: detect(), Bridge = {}, load side+framework module
├── server/qbx.lua  server/qb.lua  server/esx.lua  server/standalone.lua  server/oxinventory.lua (shared item helpers)
└── client/qbx.lua  client/qb.lua  client/esx.lua  client/standalone.lua
```
`init.lua` loads the right file with ox_lib `require` (client files must be in `files {}`) — see the template. The template ships no ox_core / ND adapter: add `server/ox.lua` + `client/ox.lua` following the same contract after checking their docs (`ox-inventory-target.md` §6, `framework-others.md` §1), and extend `detectFramework()`.

## 4. Rules
- Business logic never calls `exports.qbx_core`, `ESX.*` or `QBCore.*` directly: only `Bridge.*`.
- Normalise data shapes (job table, account names) in the bridge.
- Every bridge function is server-authoritative; client bridge is for UX (showing/hiding options).
- Unsupported operations in a framework: return `false` and log once, never error at runtime.
- Keep the bridge thin; prefer ox_lib for UI/callbacks/zones so those need no bridging.

## 5. Inventory and target detection
Facts that shape the adapters (2026):
- **ox_inventory supports ox, esx, qbx and nd only** — the QBCore bridge was removed in v2.42.0. On QBCore use **qb-inventory exports** (`CanAddItem`, `AddItem`, `RemoveItem`, `GetItemCount`, `HasItem`), never ox_inventory.
- Qbox always runs ox_inventory (mandatory since qbx_core 1.18).
- ESX: `xPlayer.addInventoryItem` ignores weight (check `canCarryItem` first) and `removeAccountMoney` can go negative (check the balance first) — the template's ESX adapter does both.
- ox_target `provide`s `qtarget`, not `qb-target`.

```lua
Bridge.inventory = GetResourceState('ox_inventory') == 'started' and 'ox'
    or GetResourceState('qb-inventory') == 'started' and 'qb'
    or GetResourceState('esx_inventory') == 'started' and 'esx_inventory'
    or 'framework'
Bridge.target = GetResourceState('ox_target') == 'started' and 'ox'
    or GetResourceState('qb-target') == 'started' and 'qb'
    or nil   -- fallback: lib.points + textUI
```

## Sources
- https://github.com/overextended/ox_inventory/releases (v2.42.0 QBCore bridge removal)
- https://docs.qbox.re · https://github.com/Qbox-project/qbx_core
- https://github.com/esx-framework/esx_core (1.15.2 source)
- https://github.com/qbcore-fivem/qb-inventory
