# Database design, tuning and scaling for FiveM

Baseline: oxmysql 2.14.3 · MariaDB LTS **12.3** (12.3.3, 2026-08-22; previous LTS 11.8.9 / 11.4.13 / 10.11) · MySQL LTS **8.4** (8.4.12) and **9.7** (9.7.3, LTS since 2026-04-21) · verified 2026-10-07.
API details (methods, placeholders, convars): [database-oxmysql.md](database-oxmysql.md). Server-side Lua performance in general: [performance.md](performance.md).

## Contents
1. Choosing the database server (MariaDB vs MySQL, versions)
2. Topology and hardware for 64 → 2000 players
3. my.cnf / my.ini tuning (with reasoning)
4. Schema design rules
5. Indexes for framework tables (ESX, QBCore, Qbox, ox_inventory)
6. Character sets, collations and time zones
7. Query patterns: EXPLAIN, N+1, batching, caching, write-behind
8. Transactions, locking and deadlocks
9. Slow query log and monitoring
10. Backups and restores
11. Schema changes on a live server, GUI tools
12. Do / don't summary
13. Sources

---

## 1. Choosing the database server

The oxmysql docs recommend **MariaDB** "for compatibility, and improved performance (over all versions of MySQL)" and say **not to use XAMPP** (a dev web stack) — install MariaDB directly. Reasons that matter for FiveM:
- Most community SQL was written for MySQL 5.7/MariaDB: MySQL 8+ adds reserved words (`group`, `rank`, `groups`) and rejects defaults on `LONGTEXT`/`JSON` columns (oxmysql docs).
- Framework migrations use MariaDB-only syntax: Qbox runs `CREATE INDEX IF NOT EXISTS` and `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (qbx_core). MySQL does not support `IF NOT EXISTS` on `CREATE INDEX` / `ADD COLUMN`, so those statements fail there.

| Line | Version to use (2026-10) | Support | Notes |
|---|---|---|---|
| MariaDB 12.3 LTS | **12.3.3** | to 2029-06-12 | Recommended for new installs. |
| MariaDB 11.8 LTS | 11.8.9 | to 2030-02-13 (mariadb.org API) | Fine; very common in 2025–26 guides. |
| MariaDB 11.4 / 10.11 LTS | 11.4.13 / 10.11.x | 2029-05 / 2028-02 | OK, plan upgrade. |
| MariaDB 10.6 | — | **EOL 2026-07-06** | Upgrade. |
| MariaDB 13.0 / 13.1 | rolling / RC | short | Avoid in production. |
| MySQL 8.4 LTS | 8.4.12 | premier to 2029-04 | Use if you must run MySQL. |
| MySQL 9.7 LTS | 9.7.3 | to 2031 premier | New LTS; less community testing with FiveM SQL. |
| MySQL 8.0 | — | **EOL 2026-04-30** | Upgrade. |

Version facts: MariaDB downloads REST API and endoflife.date (see Sources). Re-verify: `curl -s https://downloads.mariadb.org/rest-api/mariadb/` and `curl -s https://endoflife.date/api/mysql.json`.

Upgrade note: **MariaDB ≥ 11.6 changed the server default to `utf8mb4` / `utf8mb4_uca1400_ai_ci`** (previously latin1). Tables created after an upgrade can get a different collation from framework tables → "Illegal mix of collations" on joins and failed foreign keys. Pin the server collation (§3, §6).

## 2. Topology and hardware

| Size | Topology | Notes |
|---|---|---|
| ≤ 64 slots | DB on the FXServer host, bind 127.0.0.1 | 1–2 GB RAM for MariaDB is plenty. |
| 64–300 | Same host OK if RAM/NVMe are sufficient; isolate CPU cores if possible | Loopback latency ≈ 0.1 ms. |
| 300–2000 | **Dedicated DB host on the same LAN/datacenter** (< 0.5 ms RTT), NVMe, ECC RAM | Every query pays the round trip; a DB 20 ms away turns a 1 ms query into 21 ms. |

- Never point FXServer at a database in another region/hosting company: latency, not CPU, is the usual cause of "slow queries" on rented hosting. **UNVERIFIED** as a measured statistic; it follows directly from per-query round trips.
- NVMe storage matters more than CPU for write-heavy servers (inventory/vehicle saves are large `LONGTEXT` rewrites).
- One database per FXServer instance. Do not let a web panel, phone app API or Discord bot run heavy analytical queries on the production DB at peak; use a replica (`mariadb-backup` snapshot or replication) for stats.
- The oxmysql debug UI is for development/small servers; "for larger servers, look into builtin MySQL logging" (oxmysql docs) → §9.

## 3. my.cnf / my.ini tuning

Location: Linux `/etc/mysql/mariadb.conf.d/50-server.cnf` (Debian/Ubuntu) or `/etc/my.cnf.d/server.cnf` (RHEL); Windows MSI `C:\Program Files\MariaDB 12.3\data\my.ini`. Restart the service after editing (`systemctl restart mariadb`, or Services → MariaDB).

```ini
[mysqld]
# --- network / safety ---
bind-address              = 127.0.0.1        # DB on same host; use the LAN IP + firewall otherwise
skip-name-resolve         = ON               # no reverse DNS per connection; grant users by IP
max_connections           = 200              # see reasoning below
max_allowed_packet        = 64M              # large multi-row upserts / big JSON blobs

# --- character set (match framework tables: utf8mb4_unicode_ci) ---
character-set-server      = utf8mb4
collation-server          = utf8mb4_unicode_ci

# --- InnoDB memory ---
innodb_buffer_pool_size   = 4G               # see sizing table
# --- InnoDB durability / IO ---
innodb_flush_log_at_trx_commit = 1           # 2 = faster commits, may lose ~1 s on OS crash/power loss
innodb_log_file_size      = 1G               # MariaDB; MySQL 8.0.30+ uses innodb_redo_log_capacity
innodb_io_capacity        = 1000             # NVMe/SSD; leave default on HDD
innodb_file_per_table     = ON               # default; lets OPTIMIZE TABLE reclaim space
# innodb_flush_method     = O_DIRECT         # Linux only; avoids double buffering with the OS cache

# --- temp tables / caches ---
tmp_table_size            = 64M
max_heap_table_size       = 64M
table_open_cache          = 4000
query_cache_type          = 0                # MariaDB: keep the query cache off (removed in MySQL 8)
query_cache_size          = 0

# --- diagnostics ---
slow_query_log            = ON
slow_query_log_file       = /var/log/mysql/mariadb-slow.log   # Windows: omit, defaults to the data dir
long_query_time           = 0.5
```

| Setting | Reasoning for FiveM |
|---|---|
| `innodb_buffer_pool_size` | The single most important value. Keep the whole working set (players, vehicles, inventory, stashes) in RAM so reads never touch disk. MariaDB docs: up to ~80 % of RAM on a dedicated DB server. On a shared FXServer host, leave RAM for FXServer (often 4–16 GB at high slot counts) and the OS. Default 128 MiB is far too small for any live server. |
| `innodb_flush_log_at_trx_commit` | `1` = full durability (default). `2` writes the redo log at each commit but flushes about once a second — an OS crash or power loss can lose the last second (MariaDB docs). For RP data that is usually acceptable on slow disks; on NVMe keep `1`. Never `0` on a server with an economy (a mysqld crash loses up to 1 s → potential dupes/rollbacks). |
| `innodb_log_file_size` | Bigger redo log = fewer checkpoint flushes for write-heavy autosaves; costs longer crash recovery. Dynamic since MariaDB 10.9. 512M–2G is typical. |
| `max_connections` | Sum of: oxmysql pool (`connectionLimit`, default 10) × FXServer instances + txAdmin/panels/bots/backups + admin sessions. 100–200 covers nearly every server; huge values only waste per-thread memory. "Too many connections" usually means a leak in an external tool, not FiveM. |
| `skip-name-resolve` | Avoids DNS lookups on each new connection (oxmysql re-opens idle-closed pool connections). Users must then be granted by IP (`'fivem'@'127.0.0.1'`), not hostname. |
| Query cache off | Global mutex invalidated on every write; FiveM workloads write constantly. Cache in Lua instead (§7.4). |
| `tmp_table_size` | `GROUP BY`/`ORDER BY` on unindexed columns spill to disk temp tables; raise moderately, but fix the query first. |

Buffer pool sizing guide (rule of thumb, **UNVERIFIED** as hard numbers — measure `SELECT ROUND(SUM(data_length+index_length)/1024/1024) AS mb FROM information_schema.tables WHERE table_schema = DATABASE();`):

| Server | Typical DB size | `innodb_buffer_pool_size` |
|---|---|---|
| Dev / ≤ 32 slots | < 500 MB | 512M–1G |
| 64–200 slots | 0.5–3 GB | 2–4G |
| 200–600 slots | 2–10 GB | 4–12G |
| 600–2000 slots (dedicated DB host) | 5–40 GB | DB size × 1.2, up to ~70–80 % of host RAM |

Check effectiveness: `SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read%';` — `Innodb_buffer_pool_reads` (disk) should be < 1 % of `Innodb_buffer_pool_read_requests`.

Dedicated DB user (never `root` from FXServer):
```sql
CREATE USER 'fivem'@'127.0.0.1' IDENTIFIED BY 'LongAlphanumericPassword123';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES ON fivem.* TO 'fivem'@'127.0.0.1';
-- Scripts that auto-migrate need CREATE/ALTER/INDEX; remove DROP once the schema is stable if you can.
```
Never expose port 3306 to the internet; if a remote panel needs access, use an SSH tunnel/VPN or a firewall allow-list.

## 4. Schema design rules

1. **InnoDB everywhere** (row locks, crash safety). Convert legacy MyISAM: `ALTER TABLE t ENGINE=InnoDB;`
2. **Every table has a primary key.** ESX `owned_vehicles` uses `plate`; QBCore/Qbox use `citizenid` on players and `id` on vehicles. Tables without a PK (some add-on logs) make replication, upserts and deletes slow.
3. **Short, typed keys.** `VARCHAR(60)` identifiers are fine; avoid `VARCHAR(255)`/`TEXT` keys (`players.license` is 255 in QBCore — works, but larger indexes).
4. **Hot query columns are real columns**, not JSON fields. Keep JSON blobs (`inventory`, `mods`, `metadata`, `charinfo`) for data you always load and save as a whole.
5. **Match types across joins/FKs**: same type, length and collation (`citizenid VARCHAR(50) utf8mb4_unicode_ci` on both sides). A mismatch prevents index use and FK creation (errno 150).
6. **Timestamps**: `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`, `updated_at … ON UPDATE CURRENT_TIMESTAMP` — QBCore's `last_updated` and ox_inventory's `lastupdated` follow this, which enables purging stale rows.
7. **Money**: integers (`INT`/`BIGINT`), never `FLOAT`. `DECIMAL` returns strings in oxmysql unless `decimalNumbers=true`.
8. **Logs/history tables grow forever**: index `(owner, created_at)`, purge with a scheduled `DELETE … WHERE created_at < NOW() - INTERVAL 30 DAY LIMIT 5000` loop, or ship logs to an external service (Fivemanage, Loki) instead of the game DB.
9. **Foreign keys** with `ON DELETE CASCADE` (Qbox `player_groups`, `player_vehicles`) keep character deletion consistent; InnoDB auto-creates an index on the FK column.
10. Ship migrations idempotently (`CREATE TABLE IF NOT EXISTS` in `MySQL.ready`) and document the minimum DB (MariaDB-only syntax vs portable).

### JSON column vs normalized table

| Use JSON (`LONGTEXT` + `json.encode`) when | Use a normalized table when |
|---|---|
| Always read/written as one unit with the owner (skin, vehicle mods, inventory snapshot) | You search/filter/aggregate by the field (job, gang, phone number, item name) |
| Shape changes often | Many rows per owner change independently (phone messages, transactions, bills) |
| Size is bounded (≤ ~64 KB) | Concurrent writers touch different parts (shared stashes edited by many players) |

Middle ground — index one JSON field with a generated column (works on MariaDB and MySQL 8.0.21+):
```sql
ALTER TABLE `players`
  ADD COLUMN `job_name` VARCHAR(50) AS (JSON_VALUE(`job`, '$.name')) STORED,
  ADD INDEX `idx_players_job_name` (`job_name`);
-- SELECT citizenid FROM players WHERE job_name = 'police';   -- uses the index
```
MariaDB `JSON` is an alias of `LONGTEXT` with a `JSON_VALID` check; MySQL `JSON` is a binary type. oxmysql returns both as strings (`jsonStrings=true`).

## 5. Indexes for framework tables

Read from the current SQL files (Sources). ✓ = already in the official schema.

| Table (framework) | Hot queries | Index state / recommendation |
|---|---|---|
| `users` (ESX) | `WHERE identifier = ?` (load/save every 10 min via one batched `prepare`), `WHERE identifier IN (…)` (multicharacter), `WHERE ssn = ?` | ✓ PK `identifier`, ✓ UNIQUE `id`, ✓ UNIQUE `ssn`. Nothing to add. |
| `owned_vehicles` (ESX) | `WHERE owner = ?`, `WHERE plate = ?` (ox_inventory trunk/glovebox) | ✓ PK `plate`, ✓ KEY `owner`. If your garage filters `owner + type/stored/parking`, add `KEY (owner, type)` or `(owner, parking)`. |
| `banking` (ESX) | history by `identifier` | **No index on `identifier`** in legacy.sql → `ALTER TABLE banking ADD INDEX idx_banking_identifier (identifier, time);` |
| `addon_account_data`, `datastore_data`, `addon_inventory_items` (ESX) | by `owner` / name | ✓ indexed. |
| `players` (QBCore/Qbox) | `WHERE citizenid = ?`, `WHERE license = ? OR license = ?` | ✓ PK `citizenid`, ✓ KEY `license`, ✓ KEY `last_updated`. |
| `users` (Qbox) | connect lookup by `license`/`license2`/`fivem`/`discord` | Qbox now creates `idx_users_*` at start; its comment: without them the lookup "is a full scan of `users`… and turns the connect deferral into a 1s+ stall". |
| `player_groups` (Qbox) | by citizenid; by `group`+`type` | ✓ PK `(citizenid, type, group)`. For "members of job X" add `KEY (`group`, type)`. |
| `player_vehicles` (QBCore) | `WHERE citizenid = ?`, `WHERE plate = ?`, `citizenid + garage + state` | ✓ KEY `citizenid`, `plate`, `license`. If `vehshop.sql` ran, `plate` has **both** a plain KEY and `UK_playervehicles_plate` → drop the redundant non-unique one: `ALTER TABLE player_vehicles DROP INDEX plate;` (check `SHOW INDEX FROM player_vehicles` first). Consider `KEY (citizenid, garage)`. |
| `player_vehicles` (Qbox, qbx_vehicles) | by `id`, `plate`, `citizenid` | ✓ PK `id`, ✓ UNIQUE `plate`, ✓ FK index `citizenid`. |
| `bans` (QB/Qbox) | `license`, `discord`, `ip` | ✓ indexed. |
| `ox_inventory` | `WHERE owner = ? AND name = ?`; start-up `DELETE … WHERE lastupdated < NOW() - INTERVAL 6 MONTH` | ✓ UNIQUE `(owner, name)` (used by the upsert). Big servers: `ALTER TABLE ox_inventory ADD INDEX idx_lastupdated (lastupdated);` so the purge is not a full scan. |
| Phone / MDT / logs (third-party) | by owner, by date, by phone number | Usually the worst offenders — check `EXPLAIN` on every query they run at join. |

Find unindexed lookups quickly:
```sql
-- MariaDB/MySQL: tables with no secondary indexes and many rows
SELECT t.table_name, t.table_rows
FROM information_schema.tables t
LEFT JOIN information_schema.statistics s
  ON s.table_schema = t.table_schema AND s.table_name = t.table_name AND s.index_name <> 'PRIMARY'
WHERE t.table_schema = DATABASE() AND s.index_name IS NULL
ORDER BY t.table_rows DESC;
```

Index rules: leftmost-prefix (index `(owner, type)` serves `owner = ?` and `owner = ? AND type = ?`, not `type = ?` alone); `LIKE '%abc'` cannot use an index; functions on the column (`WHERE LOWER(plate) = ?`, `WHERE DATE(created_at) = ?`) disable the index — compare raw columns with ranges instead; every extra index slows writes slightly, so don't index columns you never filter on.

## 6. Character sets, collations and time zones

- Use `utf8mb4` (emoji and non-Latin names in character names, phone messages). `utf8`/`utf8mb3` breaks on 4-byte characters.
- Pick **one** collation for the whole DB. Framework files use `utf8mb4_unicode_ci` (Qbox, QBCore garages, ESX database default). MariaDB ≥ 11.6 defaults new objects to `utf8mb4_uca1400_ai_ci`; MySQL 8+ defaults to `utf8mb4_0900_ai_ci`. Mixing them yields `Illegal mix of collations` errors on joins/comparisons. Exception: Qbox/QB store `mods` as `utf8mb4_bin` (byte comparison) on purpose.
- Audit and fix:
```sql
SELECT table_name, table_collation FROM information_schema.tables WHERE table_schema = DATABASE();
ALTER DATABASE fivem CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;            -- default for new tables
ALTER TABLE some_table CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; -- rewrites the table: off-peak
```
- oxmysql connection default is `utf8mb4_unicode_ci`; `?charset=utf8mb4` selects `utf8mb4_general_ci` for the session (literals only; columns keep their own collation).
- **Time zones**: `TIMESTAMP` is stored in UTC and shown in the session `time_zone` (default `SYSTEM`); `DATETIME` is stored as written. oxmysql converts both to epoch milliseconds using the FXServer host's local zone. Keep DB host and FXServer host on the same zone, or avoid ambiguity: return `UNIX_TIMESTAMP(col)` from SQL (Qbox pattern) or store `BIGINT` epoch seconds from `os.time()` (ESX `banking.time`).

## 7. Query patterns

### 7.1 EXPLAIN
```sql
EXPLAIN SELECT plate, glovebox FROM owned_vehicles WHERE owner = 'char1:abc';
-- MariaDB: ANALYZE FORMAT=JSON SELECT …   (runs it, real row counts)
-- MySQL 8.0.18+: EXPLAIN ANALYZE SELECT …
```
| Column | Good | Bad |
|---|---|---|
| `type` | `const`, `eq_ref`, `ref`, `range` | `ALL` (full scan), `index` (full index scan) |
| `key` | an index name | `NULL` |
| `rows` | small | ≈ table size |
| `Extra` | `Using index` | `Using filesort`, `Using temporary` on big tables |

### 7.2 Avoid N+1
```lua
-- BAD: one query per vehicle (N round trips, N log lines)
for i = 1, #plates do
    local row = MySQL.single.await('SELECT owner FROM owned_vehicles WHERE plate = ?', { plates[i] })
end

-- GOOD: one query
if #plates > 0 then
    local rows = MySQL.query.await('SELECT plate, owner FROM owned_vehicles WHERE plate IN (?)', { plates })
    local ownerByPlate = {}
    for i = 1, #rows do ownerByPlate[rows[i].plate] = rows[i].owner end
end
```
Also: never query inside a per-frame/per-second loop or inside `playerConnecting` for data you can preload once at resource start (items, jobs, shops — ESX loads `jobs`, `job_grades` and `items` once).

### 7.3 Batch writes
Real framework patterns:
- **ESX** `Core.SavePlayers` (every 10 min): builds one parameter array per player and calls `MySQL.prepare` **once** with all sets.
- **ox_inventory** `db.saveInventories`: one `prepare.await` batch per category (players, trunks, gloveboxes) in parallel threads; stashes with a single multi-row `INSERT … VALUES (?, ?, ?), (?, ?, ?) … ON DUPLICATE KEY UPDATE` when `inventory:bulkstashsave` is true (default).
- **Qbox** saves each player on an interval (`updateInterval = 5` minutes) with an `UPDATE … WHERE citizenid = :citizenid`.

```lua
-- server: batch upsert of N rows in one round trip, chunked to stay under max_allowed_packet
local function bulkUpsertStashes(rows) -- rows = { { owner, name, dataJson }, ... }
    local CHUNK = 500
    for first = 1, #rows, CHUNK do
        local last = math.min(first + CHUNK - 1, #rows)
        local values, params = {}, {}
        for i = first, last do
            values[#values + 1] = '(?, ?, ?)'
            local r = rows[i]
            params[#params + 1] = r[1]
            params[#params + 1] = r[2]
            params[#params + 1] = r[3]
        end
        MySQL.query.await(('INSERT INTO `ox_inventory` (`owner`, `name`, `data`) VALUES %s ON DUPLICATE KEY UPDATE `data` = VALUES(`data`)')
            :format(table.concat(values, ', ')), params)
    end
end
```
`VALUES(col)` in `ON DUPLICATE KEY UPDATE` works on MariaDB and MySQL (deprecated on MySQL 8.0.20+ in favour of a row alias, which MariaDB does not support) — keep `VALUES()` for portability.

| Approach | Round trips | Use |
|---|---|---|
| Loop of `MySQL.update` | N, N pool checkouts | never for > 10 rows |
| `MySQL.prepare` with N parameter sets | N on one connection, statement parsed once | different rows, same statement (ESX, ox_inventory) |
| Multi-row `VALUES (…),(…)` | 1 per chunk | inserts/upserts of many rows |
| `MySQL.transaction` | N in one transaction | must be atomic |

### 7.4 Cache in Lua, write behind
For 200–2000 players the DB should mostly see: one load at join, periodic dirty saves, one save at drop. Reads during play come from memory.

```lua
-- server/cache.lua — write-behind cache for a custom per-character table
local cache = {}      -- [citizenid] = { data = table, dirty = boolean }
local SAVE_INTERVAL = 5 * 60 * 1000

local function load(citizenid)
    local entry = cache[citizenid]
    if entry then return entry.data end
    local raw = MySQL.scalar.await('SELECT `data` FROM `my_progress` WHERE `citizenid` = ?', { citizenid })
    entry = { data = raw and json.decode(raw) or {}, dirty = false }
    cache[citizenid] = entry
    return entry.data
end

local function markDirty(citizenid)
    local entry = cache[citizenid]
    if entry then entry.dirty = true end
end

local function flush(onlyCitizenid)
    local sets = {}
    for citizenid, entry in pairs(cache) do
        if entry.dirty and (not onlyCitizenid or citizenid == onlyCitizenid) then
            sets[#sets + 1] = { citizenid, json.encode(entry.data) }
            entry.dirty = false
        end
    end
    if #sets == 0 then return end
    local ok, err = pcall(MySQL.prepare.await,
        'INSERT INTO `my_progress` (`citizenid`, `data`) VALUES (?, ?) ON DUPLICATE KEY UPDATE `data` = VALUES(`data`)', sets)
    if not ok then
        print(('^1[my_progress] save failed: %s^0'):format(err))
        for i = 1, #sets do                       -- re-mark so the next flush retries
            local entry = cache[sets[i][1]]
            if entry then entry.dirty = true end
        end
    end
end

CreateThread(function()
    while true do
        Wait(SAVE_INTERVAL)
        flush()
    end
end)

-- save + evict on drop (playerDropped gives the server id; map it to your citizenid)
AddEventHandler('my_progress:server:characterUnloaded', function(citizenid)
    flush(citizenid)
    cache[citizenid] = nil
end)

-- txAdmin scheduled restart / shutdown
AddEventHandler('txAdmin:events:serverShuttingDown', function()
    flush()
end)

exports('getProgress', load)
exports('setProgress', function(citizenid, key, value)
    local data = load(citizenid)
    data[key] = value
    markDirty(citizenid)
end)
```
Notes:
- Only **dirty** rows are written; most players have nothing new every interval.
- Stagger big periodic jobs (don't run every resource's autosave at the same minute).
- Flushing in `onResourceStop` is best-effort: whether queued async queries finish during a full server stop is **UNVERIFIED** — rely on txAdmin's shutdown event and periodic saves.
- Money/items that can be duplicated must be saved on every change or validated transactionally — don't write-behind an economy without understanding the crash window.

### 7.5 Atomic updates instead of read-modify-write
```lua
-- one statement, no race, no FOR UPDATE needed
local affected = MySQL.update.await(
    'UPDATE `society_accounts` SET `balance` = `balance` - ? WHERE `name` = ? AND `balance` >= ?',
    { amount, society, amount })
if affected ~= 1 then return false end   -- insufficient funds (or no such row)
```

### 7.6 Pagination and big reads
- Use `LIMIT` with keyset pagination (`WHERE id > ? ORDER BY id LIMIT 50`) instead of large `OFFSET`s in MDT/phone UIs.
- oxmysql warns at ≥ 1000 rows (`mysql_resultset_warning`); a 10k-row result crosses Node → Lua via msgpack and costs server-thread time.

## 8. Transactions, locking and deadlocks

- InnoDB locks **rows** it touches through an index. An `UPDATE … WHERE unindexed_col = ?` scans and locks far more rows → lock waits at peak. Index the columns in `WHERE` of every `UPDATE`/`DELETE`.
- oxmysql sets **READ COMMITTED** on all pool connections by default (`mysql_transaction_isolation_level 2`), which takes fewer gap locks than InnoDB's default REPEATABLE READ.
- `SELECT … FOR UPDATE` inside `MySQL.startTransaction` locks rows until commit — use for "check balance then debit across tables". `LOCK IN SHARE MODE` / `FOR SHARE` for read-only consistency.
- Keep transactions short: oxmysql aborts `startTransaction` after 30 s and holds one pool connection for its duration.
- **Deadlocks** (error 1213, `ER_LOCK_DEADLOCK`) happen when two transactions lock the same rows in different orders. InnoDB rolls one back. Prevent: lock rows in a consistent order (e.g. sort the two citizenids before a transfer), touch as few rows as possible, avoid long transactions. Handle: retry a small number of times.
```lua
local function transfer(fromCid, toCid, amount)
    local a, b = fromCid, toCid
    if b < a then a, b = b, a end                         -- consistent lock order
    for attempt = 1, 3 do
        local insufficient = false
        local ok = MySQL.startTransaction(function(query)
            query('SELECT citizenid FROM bank_accounts WHERE citizenid IN (?, ?) ORDER BY citizenid FOR UPDATE', { a, b })
            local res = query('UPDATE bank_accounts SET balance = balance - ? WHERE citizenid = ? AND balance >= ?',
                { amount, fromCid, amount })
            if res.affectedRows ~= 1 then
                insufficient = true
                return false                                  -- business rule: rollback, no retry
            end
            query('UPDATE bank_accounts SET balance = balance + ? WHERE citizenid = ?', { amount, toCid })
        end)
        if ok then return true end
        if insufficient then return false end
        -- otherwise an SQL error (deadlock, lock wait timeout...) was logged via oxmysql:error; retry briefly
        Wait(50 * attempt)
    end
    return false
end
```
- Inspect: `SHOW ENGINE INNODB STATUS\G` (section LATEST DETECTED DEADLOCK); `innodb_print_all_deadlocks = ON` logs all of them; lock waits: `SELECT * FROM information_schema.innodb_trx;` (MariaDB) / `performance_schema.data_lock_waits` (MySQL).
- `innodb_lock_wait_timeout` (default 50 s) is far too long for a game server request; consider 5–10 s at session/global level so stuck requests fail fast. **UNVERIFIED** as a community norm; it is a judgment call.

## 9. Slow query log and monitoring

```sql
-- runtime (until restart); make it permanent in my.cnf (§3)
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 0.5;
-- MariaDB extras: include plan info
SET GLOBAL log_slow_verbosity = 'query_plan,explain';
-- optional & noisy:
-- SET GLOBAL log_queries_not_using_indexes = 1;
```
Analyse: `mariadb-dumpslow -s t /var/log/mysql/mariadb-slow.log | head -50` (or `mysqldumpslow`), or Percona Toolkit `pt-query-digest`.

oxmysql side: `set mysql_slow_query_warning 100` in production prints offenders with resource name and parameters. Remember the oxmysql number includes queueing and server hitches ("slow queries may not indicate a database issue", docs) — confirm in the DB slow log.

Quick health queries:
```sql
SHOW GLOBAL STATUS LIKE 'Threads_connected';       -- vs max_connections
SHOW GLOBAL STATUS LIKE 'Innodb_row_lock_waits';
SHOW FULL PROCESSLIST;                              -- long-running / stuck queries
SELECT table_name, ROUND((data_length+index_length)/1024/1024) AS mb
FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY mb DESC LIMIT 15;
```

## 10. Backups and restores

| Tool | Type | Use |
|---|---|---|
| `mariadb-dump` / `mysqldump` | logical SQL | small–medium DBs, portable, schema diffs |
| `mariadb-backup` (MariaDB) / Percona XtraBackup (MySQL) | physical hot copy | large DBs (> 5–10 GB), fast restore |
| MySQL Shell `util.dumpInstance()` | parallel logical | MySQL 8.4/9.7 |

```bash
# Logical, consistent for InnoDB without locking the game (--single-transaction)
mariadb-dump --single-transaction --quick --routines --triggers --events \
  -u backup -p'***' fivem | gzip > /backups/fivem_$(date +%F_%H%M).sql.gz

# Physical (MariaDB)
mariadb-backup --backup --target-dir=/backups/full_$(date +%F) --user=backup --password='***'
mariadb-backup --prepare --target-dir=/backups/full_2026-10-07
# restore: stop MariaDB, empty datadir, then
mariadb-backup --copy-back --target-dir=/backups/full_2026-10-07 && chown -R mysql:mysql /var/lib/mysql
```
Windows: `"C:\Program Files\MariaDB 12.3\bin\mariadb-dump.exe"` scheduled with Task Scheduler.

Rules: schedule at least daily + before every framework/resource update; keep copies off the machine (3-2-1); a backup user with `SELECT, SHOW VIEW, TRIGGER, LOCK TABLES, EVENT, RELOAD, PROCESS` only; **test restores** on a dev DB; binary log (`log_bin`) enables point-in-time recovery after a dupe exploit or a bad script wiped tables. oxmysql keeps `multipleStatements` off precisely because of injected `DROP TABLE` incidents (oxmysql #154 links the Cfx forum thread "database tables are deleted").

## 11. Schema changes on a live server, GUI tools

- `ALTER TABLE` on a big table needs a metadata lock: if a long query/transaction (or an idle DBeaver tab with an open transaction) holds the table, the ALTER waits **and every new query on that table queues behind it** → whole server freezes. Run migrations during restarts, or with `ALGORITHM=INPLACE, LOCK=NONE` where supported, and check `SHOW PROCESSLIST` first.
- **HeidiSQL** (Windows, bundled with the MariaDB MSI) and **DBeaver** (cross-platform) are fine for browsing and EXPLAIN. DBeaver in manual-commit mode keeps transactions open → locks; use auto-commit on production. Don't edit JSON blobs of online players by hand (the framework overwrites them at next save).
- Run framework SQL files only once; re-running `CREATE TABLE` files without `IF NOT EXISTS` errors, and some `INSERT`s duplicate data.

## 12. Do / don't summary

| Do | Don't |
|---|---|
| MariaDB 12.3/11.8 LTS, dedicated user, bind localhost/LAN | XAMPP, `root` without password, port 3306 open to the internet |
| Size `innodb_buffer_pool_size` to the data set | Leave the 128 MiB default on a live server |
| Index every column in `WHERE`/`JOIN` of hot queries; `EXPLAIN` new queries | Add indexes blindly to every column |
| Load once, cache in Lua, save dirty rows in batches | Query per frame/tick or save every player every few seconds |
| `prepare` batches / multi-row upserts | Loops of single queries |
| Atomic `UPDATE … WHERE balance >= ?` | Read, compute in Lua, write back (race) |
| Short transactions, consistent lock order | `Wait`/HTTP/client callbacks inside a transaction |
| One collation (`utf8mb4_unicode_ci`) | Mixed defaults after a MariaDB ≥ 11.6 / MySQL 8 upgrade |
| Slow query log + `mysql_slow_query_warning` | `mysql_debug true` / `mysql_ui` on a full production server |
| Daily tested backups, binlog for PITR | Only a weekly HeidiSQL export kept on the same disk |
| Purge logs/stale stashes on a schedule | Unbounded log tables in the game DB |

## 13. Sources
- oxmysql docs (MariaDB recommendation, XAMPP, upsert, UI guidance): https://overextended.dev/docs/oxmysql · https://overextended.dev/docs/oxmysql/ui
- oxmysql source and issues: https://github.com/overextended/oxmysql · https://github.com/overextended/oxmysql/issues/154
- ESX schema and save loop: https://github.com/esx-framework/esx_core/blob/main/%5BSQL%5D/legacy.sql · https://github.com/esx-framework/esx_core/blob/main/%5Bcore%5D/es_extended/es_extended.sql · https://github.com/esx-framework/esx_core/blob/main/%5Bcore%5D/es_extended/server/functions.lua · https://github.com/esx-framework/esx_core/blob/main/%5Bcore%5D/es_extended/server/common.lua
- QBCore: https://github.com/qbcore-fivem/qb-core/blob/main/qbcore.sql · https://github.com/qbcore-fivem/qb-vehicleshop/blob/main/vehshop.sql · https://github.com/qbcore-fivem/qb-garages/blob/main/player_vehicles.sql
- Qbox: https://github.com/Qbox-project/qbx_core/blob/main/qbx_core.sql · https://github.com/Qbox-project/qbx_core/blob/main/server/storage/players.lua · https://github.com/Qbox-project/qbx_core/blob/main/config/server.lua · https://github.com/Qbox-project/qbx_vehicles/blob/main/vehicles.sql
- ox_inventory DB module: https://github.com/overextended/ox_inventory/blob/main/modules/mysql/server.lua · https://github.com/overextended/ox_inventory/blob/main/init.lua
- MariaDB versions: https://downloads.mariadb.org/rest-api/mariadb/ · https://endoflife.date/mariadb
- MySQL versions: https://endoflife.date/mysql · https://dev.mysql.com/doc/relnotes/mysql/9.7/en/ · https://dev.mysql.com/doc/relnotes/mysql/8.4/en/
- MariaDB InnoDB variables: https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-system-variables · buffer pool: https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-buffer-pool
- MariaDB slow query log: https://mariadb.com/docs/server/server-management/server-monitoring-logs/slow-query-log/slow-query-log-overview
- MariaDB EXPLAIN: https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/explain
- MariaDB character sets (11.6 default change): https://mariadb.com/docs/server/reference/data-types/string-data-types/character-sets/setting-character-sets-and-collations · time zones: https://mariadb.com/docs/server/reference/data-types/string-data-types/character-sets/internationalization-and-localization/time-zones
- Backups: https://mariadb.com/docs/server/server-usage/backup-and-restore/mariadb-backup/mariadb-backup-overview · https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump
- MySQL InnoDB: https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html · https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html · https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html
- Tools: https://www.heidisql.com/ · https://dbeaver.io/
- mysql2 pool defaults: https://github.com/sidorares/node-mysql2/blob/v3.24.5/lib/pool_config.js
