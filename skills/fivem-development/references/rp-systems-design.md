# RP systems design: architecture, data models and secure flows

Baseline: Qbox 1.24 / ESX 1.15.2 / QBCore 1.3 / ox_lib 3.40 / oxmysql 2.14 / ox_inventory 2.48 — repos checked 2026-10-07 (baseline verified 2026-10-07).
Code uses the framework bridge from [framework-bridge.md](framework-bridge.md) (`Bridge.*`) so it is framework-agnostic; SQL targets MariaDB/MySQL InnoDB through oxmysql ([database-oxmysql.md](database-oxmysql.md)). Natives checked with `scripts/natives.py`.

## Contents
1. Architecture rules for every RP system
2. Open-source reference implementations (2026 status)
3. Jobs: duty, grades, society funds (police / EMS / mechanic)
4. Vehicles: ownership, garages, impound, keys
5. Housing / properties
6. Banking and transactions
7. Shops and crafting
8. Drugs and illegal activities
9. Dispatch, MDT and phone integration
10. Status (hunger / thirst / stress) and HUD
11. Character creation and appearance
12. Death and revive
13. Radio and voice
14. Logging and abuse detection
15. Sources

## 1. Architecture rules for every RP system
- **Server owns state; clients send intents.** A client event says "I want to X at Y"; the server decides whether X happens and computes every number (price, payout, roll, duration).
- **State placement:**

| Data | Where |
|---|---|
| durable (money, items, vehicles, properties) | DB (oxmysql) + framework/inventory APIs |
| live shared per entity (vehicle owner, fuel, locked, stash id) | entity state bag, set **server-side** (`Entity(veh).state:set(k, v, true)`) |
| live per player visible to others (isDead, onDuty, radio channel) | player state bag set server-side (`Player(src).state:set`) |
| live global (weather, police count, heist cooldowns) | `GlobalState` set server-side |
| UI-only | client locals / NUI |

- Clients may write **their own** player state bag unless you protect keys: treat client-writable bags as untrusted; with `sv_stateBagStrictMode` (see `onesync-entities.md`) clients can't create/replicate arbitrary bags. Never read authority-relevant values (job, money, isDead for loot) from a client-set bag.
- **Secure event flow template** (every system below follows it):
```lua
-- server
local cooldown = {}
lib.callback.register('myres:server:action', function(source, targetId, payload)
    local src = source                                            -- 1. who
    if not Bridge.HasJob(src, 'police') then return false end      -- 2. allowed
    local ped = GetPlayerPed(src)
    local cfg = ServerConfig.ActionPoints[targetId]
    if not cfg or #(GetEntityCoords(ped) - cfg.coords) > 3.0 then return false end -- 3. where
    if type(payload) ~= 'table' or type(payload.amount) ~= 'number' then return false end -- 4. what
    local amount = math.floor(payload.amount)
    if amount < 1 or amount > cfg.max then return false end
    local now = os.time()                                         -- 5. how often
    if (cooldown[src] or 0) > now then return false end
    cooldown[src] = now + cfg.cooldown
    -- remove → add → log
    return true
end)
AddEventHandler('playerDropped', function() cooldown[source] = nil end)
```
- **Atomicity:** money+item+DB changes either all happen or none: check capacity first (`CanCarryItem`), remove before add, use `MySQL.transaction`/`startTransaction` for multi-row writes, and guard re-entrancy with a per-player `busy[src]` flag across awaits.
- **Proximity between players** (cuff, search, revive, give): server checks both peds exist, distance ≤ 3 m, same routing bucket (`GetPlayerRoutingBucket`), and target state (e.g. target is dead / cuffed).

## 2. Open-source reference implementations (2026 status)
| System | Qbox (Qbox-project) | QBCore (qbcore-fivem) | ESX (esx-framework/ESX-Legacy-Addons) | Standalone / other |
|---|---|---|---|---|
| Police | qbx_police | qb-policejob | esx_policejob | ox_police (overextended, stale since 2023) |
| EMS / death | qbx_ambulancejob + qbx_medical | qb-ambulancejob | esx_ambulancejob | — |
| Mechanic / customs | qbx_mechanicjob, qbx_customs | qb-mechanicjob | esx_mechanicjob, esx_lscustom | — |
| Garages / impound | qbx_garages (v1.1.4), qbx_vehicles | qb-garages | esx_garage | — |
| Keys | qbx_vehiclekeys (v1.0.2, active) | qb-vehiclekeys | — | — |
| Housing | qbx_properties | qb-houses, qb-apartments | esx_property | ps-housing (**archived** 2026) |
| Banking | Renewed-Banking (v2.1.4) in recipe | qb-banking | esx_banking | ox_banking (ox_core) |
| Society / boss menu | qbx_management (v1.4.0) | qb-management | esx_society | — |
| Shops | ox_inventory shops | qb-shops | esx_shops | ox_inventory |
| Crafting | ox_inventory hooks / custom | qb-crafting | — | — |
| Drugs | qbx_drugs, qbx_weed | qb-drugs, qb-weed | esx_drugs | — |
| Dispatch / MDT | ps-dispatch (3.0.0, 2026-08) / ps-mdt (3.1.4) | same | — | ox_mdt (ox_core) |
| Phone | npwd 3.16.0 + qbx_npwd | qb-phone | sd-phone (esx-framework, GPL-3.0) | lb-phone / others (paid, **UNVERIFIED**) |
| HUD / status | qbx_hud, qbx_seatbelt | qb-hud | esx_hud, esx_status + esx_basicneeds | — |
| Appearance | illenium-appearance (v5.7.0) | qb-clothing | esx_skin + skinchanger | fivem-appearance (unmaintained) |
| Radio | mm_radio + pma-voice | qb-radio + pma-voice | — | pma-voice |
| Weather/time | Renewed-Weathersync | qb-weathersync | esx_weather | — |
| Prison | xt-prison (recipe) | qb-prison | — | — |
| Doors | ox_doorlock | qb-doorlock | ox_doorlock | ox_doorlock |

Notes: `qbx_radio` and `qbx_weathersync` are **archived**; Renewed `Renewed-Vehiclekeys`/`Renewed-Garages` repos no longer exist; `ps-housing` is archived. Always read the target resource's README for its exports instead of guessing.

## 3. Jobs: duty, grades, society funds
**Data model** (frameworks already have jobs/grades; add only what's missing):
```sql
CREATE TABLE IF NOT EXISTS `society_accounts` (
  `job`      VARCHAR(50)  NOT NULL PRIMARY KEY,
  `balance`  BIGINT       NOT NULL DEFAULT 0 CHECK (`balance` >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `duty_log` (
  `id`        INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `charid`    VARCHAR(60)  NOT NULL,
  `job`       VARCHAR(50)  NOT NULL,
  `on_at`     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `off_at`    TIMESTAMP    NULL DEFAULT NULL,
  KEY `idx_duty_char` (`charid`, `job`)
) ENGINE=InnoDB;
```
- Duty: server toggles and publishes `Player(src).state:set('onDuty', true, true)` and a global counter `GlobalState.policeOnDuty` (used by robberies/drugs). Recount on job change, duty change, drop.
- Grades: never trust a grade from the client; resolve from `Bridge.GetJob(src)` on every privileged action.
- Paychecks: one server timer (`lib.cron.new('*/15 * * * *', fn)`) iterating on-duty players; pay from society if configured (`UPDATE society_accounts SET balance = balance - ? WHERE job = ? AND balance >= ?` → `affectedRows == 1`).
- **Police actions** (cuff, escort, search, put in vehicle, fine, jail): client asks with the target's **server id**; server validates job+duty, distance, target state (`Player(target).state.isCuffed`), then sets state and triggers the target client. Searching uses `exports.ox_inventory:openInventory`-style server functions (check your inventory's docs) only after the target is cuffed/hands-up.
- Fines/bills: server creates the invoice from a **server-side fine table** (code → amount); the client sends only the code.
- **EMS**: revive/heal flows in §12; charge the patient server-side.
- **Mechanic**: repair = server validates job + distance to vehicle + consumes item, then triggers the **vehicle owner client** (`NetworkGetEntityOwner`) to run `SetVehicleFixed`/`SetVehicleEngineHealth`; persist health on store. Customs prices come from the server, never from the NUI.

## 4. Vehicles: ownership, garages, impound, keys
Frameworks ship their own tables (Qbox/QBCore `player_vehicles`, ESX `owned_vehicles`). Standalone schema:
```sql
CREATE TABLE IF NOT EXISTS `vehicles_owned` (
  `id`        INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `charid`    VARCHAR(60)  NOT NULL,
  `model`     VARCHAR(60)  NOT NULL,
  `plate`     VARCHAR(8)   NOT NULL,
  `props`     LONGTEXT     NOT NULL CHECK (JSON_VALID(`props`)),   -- no literal DEFAULT: MySQL 8 rejects it on TEXT
  `state`     ENUM('out','garaged','impounded') NOT NULL DEFAULT 'garaged',
  `garage`    VARCHAR(50)  NULL,
  `impound_fee` INT UNSIGNED NOT NULL DEFAULT 0,
  `impound_reason` VARCHAR(255) NULL,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_plate` (`plate`),
  KEY `idx_owner` (`charid`)
) ENGINE=InnoDB;
```
**Take out (secure flow):**
1. Client: garage menu → `lib.callback.await('garage:server:takeOut', false, vehicleId, garageId)`.
2. Server: who; garage exists and player within 10 m; row `WHERE id = ? AND charid = ? AND state = 'garaged' AND garage = ?`; set `state = 'out'` with `UPDATE ... WHERE ... AND state = 'garaged'` and require `affectedRows == 1` (prevents double spawn/dupe); spawn server-side at the garage's configured spot; give keys; return netId.
3. Client applies props; server stores `Entity(veh).state.vehicleId`.

**Store:** client sends netId → server resolves entity (`NetworkGetEntityFromNetworkId`), checks it exists, `Entity(veh).state.vehicleId` belongs to the player (or player has keys), player is the driver or near, vehicle within the garage zone; **props come from the client** (only the owner client can read mods) → sanitise: model must equal DB model, plate must equal DB plate, clamp health values, drop unknown keys; then save and `DeleteEntity`.

**Impound:** police/tow job command → server validates job and distance → sets `state = 'impounded'`, `impound_fee`, `impound_reason`, deletes entity. Retrieval charges the fee server-side. On server restart, a startup query moves `state = 'out'` rows to a default garage or impound (vehicles don't survive restarts).
```lua
-- server: startup recovery
MySQL.ready(function()
    MySQL.update.await("UPDATE `vehicles_owned` SET `state` = 'impounded', `impound_fee` = 0 WHERE `state` = 'out'")
end)
```
**Keys:**
- Model: keys are a server-side set per character (or temporary per session), published to the client only for UX (`Player(src).state.keysList` in qbx_vehiclekeys, keyed by a per-vehicle session id).
- Lock toggle: client asks → server checks `HasKeys`, distance ≤ 10 m → `SetVehicleDoorsLocked(veh, 2 or 1)` server-side, `Entity(veh).state:set('locked', bool, true)`.
- Hotwire/lockpick: server rolls success (`math.random`), consumes the lockpick, alerts dispatch, then grants keys — never a client "success" event.
- Giving keys to another player: target must be near; log it.

## 5. Housing / properties
```sql
CREATE TABLE IF NOT EXISTS `properties` (
  `id`        INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `label`     VARCHAR(100) NOT NULL,
  `owner`     VARCHAR(60)  NULL,
  `price`     INT UNSIGNED NOT NULL,
  `interior`  VARCHAR(50)  NOT NULL,          -- shell/MLO/IPL key from server config
  `entrance`  JSON         NOT NULL,          -- {x,y,z,w}
  `furniture` LONGTEXT     NULL CHECK (`furniture` IS NULL OR JSON_VALID(`furniture`)),
  `locked`    TINYINT(1)   NOT NULL DEFAULT 1,
  KEY `idx_owner` (`owner`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `property_keys` (
  `property_id` INT UNSIGNED NOT NULL,
  `charid`      VARCHAR(60)  NOT NULL,
  PRIMARY KEY (`property_id`, `charid`),
  CONSTRAINT `fk_pk_property` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;
```
- Interiors: shells (prop interiors spawned far below the map), MLOs, or vanilla IPLs (bob74_ipl). Shells/MLO copies → one **routing bucket per property** (`SetPlayerRoutingBucket`), population disabled.
- Enter: server checks key/owner or `locked = 0`, distance to entrance, then sets bucket and teleports (`SetEntityCoords` server-side) and remembers `insideProperty[src] = id`.
- Exit/drop: always restore bucket 0 and outside coords; on `playerDropped` save the outside position, not the interior one.
- Storage: `exports.ox_inventory:RegisterStash(('property_%d'):format(id), label, slots, weight, false)` and allow `openInventory` only for key holders (inventory hook or server-side open).
- Furniture: server validates model against a whitelist and price table; clamp positions to the interior bounds.
- Purchase: transaction (debit → set owner `WHERE id = ? AND owner IS NULL`, require `affectedRows == 1`).

## 6. Banking and transactions
Prefer the framework's accounts for balances; add an immutable ledger:
```sql
CREATE TABLE IF NOT EXISTS `bank_ledger` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `account`    VARCHAR(60)  NOT NULL,           -- charid or 'society:police'
  `amount`     BIGINT       NOT NULL,           -- + credit / - debit
  `balance_after` BIGINT    NOT NULL,
  `kind`       VARCHAR(30)  NOT NULL,           -- deposit, withdraw, transfer, paycheck, fine…
  `counterparty` VARCHAR(60) NULL,
  `note`       VARCHAR(255) NULL,
  `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_account_time` (`account`, `created_at`)
) ENGINE=InnoDB;
```
- Transfer: server-side only; amount integer > 0 and ≤ limit; target must exist (by account number/charid, **not** server id typed by the user); debit with `balance >= ?` guard, credit, write two ledger rows — all in one `MySQL.startTransaction`. If the framework keeps money in memory (Qbox/ESX player objects), use its `RemoveMoney`/`AddMoney` (bridge) and log; for offline targets update the DB row through the framework's documented method or queue the credit.
- ATMs/banks: distance check to configured ATM coords or the ATM prop the target resource reported; rate-limit withdrawals.
- Never expose "add money" net events; admin money commands go through ACE (`lib.addCommand` with `restricted`).

## 7. Shops and crafting
- Shops: prefer `exports.ox_inventory:RegisterShop` (server-side prices, groups/job locks, locations). Custom shops follow §1 template with prices from `ServerConfig`.
- Stock (optional): `shop_stock(shop_id, item, stock)`; decrement with `UPDATE ... SET stock = stock - ? WHERE shop_id = ? AND item = ? AND stock >= ?`.
- Crafting:
```lua
-- server/crafting.lua
local Recipes = {   -- server-only config
    lockpick = { inputs = { metalscrap = 3, plastic = 1 }, time = 5000, bench = 'workbench_1', count = 1 },
}
local busy = {}

lib.callback.register('craft:server:make', function(source, recipeId)
    local src = source
    local recipe = Recipes[recipeId]
    if not recipe or busy[src] then return false end
    local bench = ServerConfig.Benches[recipe.bench]
    if #(GetEntityCoords(GetPlayerPed(src)) - bench) > 3.0 then return false end
    for item, n in pairs(recipe.inputs) do
        if exports.ox_inventory:GetItemCount(src, item) < n then return false, 'missing_items' end
    end
    if not exports.ox_inventory:CanCarryItem(src, recipeId, recipe.count) then return false, 'cannot_carry' end
    busy[src] = true
    local charId = Bridge.GetIdentifier(src)
    for item, n in pairs(recipe.inputs) do exports.ox_inventory:RemoveItem(src, item, n) end
    SetTimeout(recipe.time, function()
        busy[src] = nil
        -- player may have left (and on Enhanced the id may already belong to someone else)
        if not DoesPlayerExist(src) or Bridge.GetIdentifier(src) ~= charId then
            lib.logger(src, 'craft_lost', ('%s lost %s craft (left)'):format(charId, recipeId))
            return
        end
        exports.ox_inventory:AddItem(src, recipeId, recipe.count)
    end)
    return true, recipe.time                                   -- client shows a progress bar of this duration
end)
AddEventHandler('playerDropped', function() busy[source] = nil end)
```
  The client progress bar is cosmetic; the server's timer decides. Cancel support: let the client request cancel → server refunds only if the timer hasn't fired.

## 8. Drugs and illegal activities
- Gate on `GlobalState.policeOnDuty >= Config.MinPolice` **server-side** (the client check is UX only).
- Selling to NPCs: client reports the NPC netId; server checks the ped exists, is not a player, distance ≤ 3 m, NPC not used recently (`Entity(ped).state.sold` set server-side), player has the item; server rolls price and police-alert chance.
- Field harvesting / processing: server-side spawn of interactable props or fixed points from server config; per-point cooldown in a server table; quantity rolled server-side.
- Robberies/heists: global cooldown in `GlobalState`/server table, minimum police, staged progression validated by time and position (same as the job template in `gameplay-patterns.md` §9), loot rolled on the server.
- Every illegal reward path logs who/what/where.

## 9. Dispatch, MDT and phone integration
- Dispatch alerts are created on the **server** from validated events (e.g. robbery stage 1 started), or client-side via the dispatch resource's own exports for ambient alerts (shots fired). ps-dispatch 3.x: `exports['ps-dispatch']:CustomAlert({...})` (client, README example) and server `exports['ps-dispatch']:SendTargetedAlert({ src }, {...})`; alert types are configured in its `Config.Blips` by `codeName`.
- Don't trust a client alert for rewards or for automatic punishments; alerts are information for players.
- MDT data (warrants, reports, BOLOs) is read/written server-side with job/grade checks on every callback; the NUI never queries SQL directly. Paginate searches and require ≥ 3 characters.
- Phone: integrate through the phone's documented server exports/events (npwd + `qbx_npwd`, sd-phone, or paid phones' docs). Phone numbers live in DB with a UNIQUE key; messages are server-routed, never peer-to-peer client events.

## 10. Status (hunger / thirst / stress) and HUD
- Authority: values live in framework metadata (Qbox `hunger`/`thirst`/`stress` metadata; ESX `esx_status`). Decay runs on the **server** (one timer for all players), not per client — e.g. qbx_core `server/loops.lua` subtracts `hungerRate`/`thirstRate` from `Player(src).state.hunger/thirst` for every logged-in player in staggered batches of 20 per frame and saves via `SetMetaData`.
- Consumables: `RegisterUsableItem`/ox_inventory item `server.export` → server validates and raises the status; client plays the anim only.
- Stress: gain from server-known events (shooting reported by game events, speeding sampled server-side) or client hints rate-limited and clamped; relief items server-side.
- HUD: client reads replicated values (player state bag or framework client data) and renders; update NUI at most a few times per second, only on change. Never send money/item values from HUD NUI back to the server.
- Effects at low values (screen shake, damage): client-side cosmetic; health damage from starvation applied by the server or by the owning client after a server instruction.

## 11. Character creation and appearance
- Multicharacter: characters table keyed by license + slot; the server picks the license via `GetPlayerIdentifierByType(src, 'license')` (never a client-sent identifier).
- Creation: place the player in a private routing bucket; the client edits ped (`SetPedHeadBlendData`, `SetPedComponentVariation`, `SetPedPropIndex`), then sends the appearance JSON; the server validates shape (ids are integers within sane ranges, model is `mp_m_freemode_01`/`mp_f_freemode_01` or whitelisted) and saves it; restore bucket 0 at spawn.
- Clothing shops: charge on the server; the server compares old/new appearance to price only changed slots.
- Use the established resource (illenium-appearance / esx_skin / qb-clothing) and its exports when the server already has one.

## 12. Death and revive
- Death detection: the client is the first to know (`gameEventTriggered` → `CEventNetworkEntityDamage`, or `IsPedDeadOrDying(cache.ped, true)`), but the server should confirm: `GetEntityHealth(GetPlayerPed(src)) <= 0` or `GetPedSourceOfDeath`/`GetPedCauseOfDeath` (available server-side).
- On death report: server sets `Player(src).state:set('isDead', true, true)` and starts a bleed-out timer; inventory looting of dead players allowed only if the server's state says dead.
- Revive by EMS:
```lua
-- server
lib.callback.register('ems:server:revive', function(source, targetId)
    local src = source
    targetId = tonumber(targetId)
    if not targetId or not Bridge.HasJob(src, 'ambulance') then return false end
    local tPed = GetPlayerPed(targetId)
    if tPed == 0 or not Player(targetId).state.isDead then return false end
    if GetPlayerRoutingBucket(src) ~= GetPlayerRoutingBucket(targetId) then return false end
    if #(GetEntityCoords(GetPlayerPed(src)) - GetEntityCoords(tPed)) > 3.0 then return false end
    if not exports.ox_inventory:RemoveItem(src, 'medikit', 1) then return false, 'no_medikit' end
    Player(targetId).state:set('isDead', false, true)
    TriggerClientEvent('ems:client:revive', targetId)
    return true
end)

-- client (target)
RegisterNetEvent('ems:client:revive', function()
    local ped = cache.ped
    local coords = GetEntityCoords(ped)
    NetworkResurrectLocalPlayer(coords.x, coords.y, coords.z, GetEntityHeading(ped), 0, false)
    ped = PlayerPedId()
    SetEntityHealth(ped, 200)
    ClearPedBloodDamage(ped)
end)
```
- `RegisterNetEvent` on the client accepts events only from the server; a cheater can still run local code to revive himself, so the server-side `isDead` state (not client health) decides loot, respawn fees and "dead" restrictions.
- Respawn at hospital: server checks bleed-out time elapsed, charges fee, clears `isDead`, teleports server-side, and (configurable) removes items server-side.
- Avoid `baseevents` death events as authority: they are client-triggered net events.

## 13. Radio and voice
- pma-voice is the standard (Mumble on FXServer). Restrict channels server-side:
```lua
-- server
exports['pma-voice']:addChannelCheck(1, function(source)
    return Bridge.HasJob(source, 'police') or Bridge.HasJob(source, 'ambulance')
end)
```
- Radio UI resources (mm_radio for Qbox, qb-radio) call pma-voice; the channel check is what enforces access. Item requirement (radio item) should also be checked server-side (remove from channel with `exports['pma-voice']:setPlayerRadio(src, 0)` when the item is lost).
- Phone calls: `exports['pma-voice']:setPlayerCall(src, callId)` from the phone's server code.
- Configure via `setr voice_*` convars (e.g. `voice_useSendingRangeOnly true`, `voice_useNativeAudio true` for submixes).

## 14. Logging and abuse detection
- Log every economy-changing action with `lib.logger(src, event, message, ...)` or Fivemanage SDK: who (license + charid), what, amount, where, before/after.
- Alert thresholds: money gained per hour, items crafted per minute, repeated failed validations (likely executor probing) → log + optional kick/ban via your admin resource.
- Rejections should be silent toward the client (return `false`) but logged with arguments.

## 15. Sources
- https://github.com/Qbox-project/txAdminRecipe (qbox.yaml: default resource set) · https://github.com/Qbox-project (qbx_* repos, archived qbx_radio / qbx_weathersync)
- https://github.com/Qbox-project/qbx_vehiclekeys (server/keys.lua: GiveKeys/RemoveKeys/HasKeys, `keysList` state bag)
- https://github.com/Qbox-project/qbx_vehicles (CreatePlayerVehicle, player_vehicles insert) · https://github.com/Qbox-project/qbx_core (server/loops.lua status decay)
- https://github.com/esx-framework/ESX-Legacy-Addons (esx_* addons) · https://github.com/esx-framework/esx_core (`[SQL]/legacy.sql` owned_vehicles) · https://github.com/esx-framework/sd-phone
- https://github.com/qbcore-fivem (qb-* resources)
- https://github.com/Renewed-Scripts/Renewed-Banking · https://github.com/Renewed-Scripts/Renewed-Weathersync · https://github.com/Renewed-Scripts/Renewed-Dutyblips
- https://github.com/Project-Sloth/ps-dispatch (README: CustomAlert, SendTargetedAlert) · https://github.com/Project-Sloth/ps-mdt · https://github.com/Project-Sloth/ps-housing (archived)
- https://github.com/AvarianKnight/pma-voice (README, docs/server-setters/addChannelCheck.md, setPlayerRadio.md)
- https://github.com/iLLeniumStudios/illenium-appearance · https://github.com/project-error/npwd · https://github.com/overextended/ox_mdt · https://github.com/overextended/ox_banking
- https://docs.fivem.net/docs/scripting-manual/networking/state-bags/ · https://docs.fivem.net/docs/scripting-reference/events/list/gameEventTriggered/
- https://overextended.dev/docs/ox_inventory · https://overextended.dev/docs/oxmysql
