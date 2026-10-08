# {{RESOURCE_NAME}}

{{DESCRIPTION}}

Generated from the `fivem-development` skill template (baseline 2026-10-07).

## Requirements
- FXServer build 12913 or newer (Recommended 35245 at the time of writing)
- [ox_lib](https://github.com/overextended/ox_lib), [oxmysql](https://github.com/overextended/oxmysql)
- One of: Qbox (qbx_core), ESX Legacy, QBCore, or standalone
- Optional: ox_inventory, ox_target

## Install
1. Copy the folder to `resources/[custom]/{{RESOURCE_NAME}}`.
2. Run `sql/install.sql` if you use the purchase log table.
3. Add `ensure {{RESOURCE_NAME}}` after your framework in `server.cfg`.
4. Optional convars (server.cfg):
   - `setr {{RESOURCE_NAME}}:framework "auto"` (`qbx` | `esx` | `qb` | `standalone`)
   - `set {{RESOURCE_NAME}}:webhook "https://discord.com/api/webhooks/..."`
   - `setr ox:locale "es"`

## Structure
- `bridge/` framework adapters (business logic only calls `Bridge.*`)
- `config/shared.lua` public config, `config/server.lua` prices & limits (server-only)
- `client/`, `server/`, `locales/`, `sql/`, `web/` (NUI, optional)
