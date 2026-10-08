# overextended resources — index

Baseline: ox_inventory v2.48.0 · ox_target v1.18.1 · ox_core v1.5.14 · ox_doorlock v1.22.1 · ox_fuel v1.5.4 — verified 2026-10-07.

This file used to hold a short summary; the content now lives in dedicated references. Read only the one the task needs.

| Section (old numbering) | Topic | Read |
|---|---|---|
| §1–4 | ox_inventory: convars, items, weapons, server/client exports, hooks + post-hook events, stashes (`instance`), shops, crafting, metadata, DB, migration, 2024–2026 changes | [ox-inventory.md](ox-inventory.md) |
| §5 | ox_target: convars, option fields, exports, qtarget/qb-target compatibility | [ox-target.md](ox-target.md) |
| §6 | ox_core: Lua/TS usage, `Ox.*`, OxPlayer, groups, OxVehicle, OxAccount, events, state bags, schema | [ox-core.md](ox-core.md) |
| — | ox_doorlock, ox_fuel, ox_banking, ox_mdt and other overextended repos | [ox-resources-misc.md](ox-resources-misc.md) |

Quick facts most tasks need:
- ox_inventory frameworks: `setr inventory:framework` = `ox` | `esx` | `qbx` | `nd` (QBCore bridge removed in v2.42.0). Requires oxmysql ≥ 2.7.3, ox_lib ≥ 3.36.4, built UI.
- Update ox_inventory below **2.47.6** (dupe fixes in 2.46.0 and 2.47.6). Hooks are validation-only since 2.47.0 — side effects go in post-hook events (`AddEventHandler(hookId, function(success, payload) end)`).
- Vehicle inventories open with `{ netid = ... }` only (2.48.0).
- ox_target provides `qtarget`, not `qb-target`; `serverEvent` data comes from the client — validate on the server.
- ox_core needs MariaDB ≥ 11.4 and Node 22; Lua: `local Ox = require '@ox_core.lib.init'`, methods with dot syntax (`player.getGroup('police')`).
- ox_fuel stores fuel in `Entity(veh).state.fuel`; ox_doorlock server exports `getDoor`, `getDoorFromName`, `editDoor`, `setDoorState`.

Sources: see the "Sources" section of each linked file; versions table in [versions.md](versions.md).
