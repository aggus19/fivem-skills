# {{RESOURCE_NAME}}

{{DESCRIPTION}}

Generated from the `fivem-development` skill template (baseline 2026-10-07).

## Integration status
The shop is an integration example, not a certified cross-framework transaction.
Purchases default to disabled (`ServerConfig.PurchasesEnabled = false`). Before enabling:
- Verify the installed adapters' true/false/error and yield contracts, including framework hooks.
- Wire a durable operation ID/result journal and `ServerConfig.RecordRecovery` to the project's recovery service. A print callback alone is insufficient; crashes can occur between any two mutations.
- Bind operations to connection and character generations; integrate the framework's logout/character-switch hooks. The example handles playerDropped and identifier changes, but a same-character relog also needs a generation change.
- Shops are public within the configured server-owned `ShopBucket` (default 0). For restricted/instanced shops, implement the corresponding server permission and bucket policy; coordinates alone are insufficient.
- Recover outstanding operations before accepting new purchases after restart; never retry an ambiguous debit/grant/refund blindly.
- Test simultaneous requests, full inventory, failed grant/refund, export exceptions, disconnect during yield, character switch/source reuse and dependency/server restart.

`server/purchase.lua` checks definitive failures and distinguishes ambiguous results. Its compensation is not atomic with inventory/framework persistence; prefer an inventory-owned shop when it meets the requirements. `RecordRecovery` is an application-defined callback, not a FiveM or framework export.

## NUI build (when generated with --nui)
In `web/`, run `bun install --frozen-lockfile` and `bun run --bun build` (validated with Bun 1.4.2). Keep `bun.lock` committed. Existing npm projects can use a reviewed package-lock and `npm ci` / `npm run build`; keep a single package manager/lockfile. Bun builds assets; FiveM still runs its embedded runtimes.

The UI waits for listener readiness before taking focus and bounds callback waits. Test open/reload/close and stop in actual CEF; compilation and mocked lifecycle tests do not validate game integration. The `<resource>_ui` command toggles focus as a fallback after a UI failure.

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
