# Database design, tuning and scaling for FiveM

Engine releases/support and tuning guidance re-reviewed **2026-10-08** against vendor sources. Driver/framework API baseline: 2026-10-07. Exact releases are a dated snapshot, not a permanent recommendation.
API details (methods, placeholders, convars): [database-oxmysql.md](database-oxmysql.md). Server-side Lua performance in general: [performance.md](performance.md).

## Contents
1. Choosing the database server (MariaDB vs MySQL, versions)
2. Topology and workload evidence
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

Choose from the project's driver, SQL migrations, plugins, hosting support and tested
upgrade path. The oxmysql documentation favors MariaDB for compatibility; its broad
performance claim is not a comparative benchmark of your workload. Preserve a healthy,
supported MySQL installation when its scripts are compatible. Do not switch engines
or install a DB for a feature that does not need one.

Vendor snapshot checked **2026-10-08**:

| Engine line | Patch observed | Support / decision |
|---|---|---|
| MariaDB 12.3 LTS | 12.3.3 | Community maintenance to 2029-06-12; candidate for new compatible deployments |
| MariaDB 11.8 LTS | 11.8.9 | Community maintenance to **2028-06-04**, not an Enterprise/Extended date |
| MariaDB 11.4 LTS | 11.4.13 | Community maintenance to 2029-05-29; retain when supported and compatible |
| MariaDB 10.11 LTS | 10.11.19 | Community maintenance to 2028-02-16; assess the project's upgrade path |
| MariaDB 10.6 | — | Community maintenance ended 2026-07-06; commercial/distribution support is a separate contract |
| MySQL 8.4 LTS | 8.4.12 | Supported LTS candidate for compatible SQL; verify Oracle/package support policy |
| MySQL 9.7 LTS | 9.7.3 | Supported LTS candidate; validate driver, SQL and operational tooling before migration |

Sources: [MariaDB maintenance policy](https://mariadb.org/about/#maintenance-policy),
[Q3 maintenance releases](https://mariadb.org/mariadb-server-12-3-11-8-11-4-and-10-11-q3-2026-maintenance-releases-and-goodbye-10-6/),
[MySQL 8.4 release notes](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/),
[MySQL 9.7 release notes](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/) and
[MySQL release policy](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html).

Before recommending a version **today**, re-open vendor release/download and support
pages; confirm GA availability in the selected OS/package channel. Record date, engine,
edition, patch, support channel and compatibility reason. Release notes can list a
not-yet-downloadable version. Prefer an appropriate maintained LTS for conservative
operations; a higher number or rolling channel alone is not a performance argument.

Compatibility gates:
- Inspect actual migrations. Qbox migrations in the baseline use MariaDB-specific
  `CREATE INDEX IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`; test the installed fork.
- MySQL's expression defaults can support TEXT/JSON: `DEFAULT ('{}')` is different
  from an unparenthesized literal. Do not claim MySQL 8+ forbids all TEXT/JSON defaults.
- MariaDB 12.3 changed `innodb_snapshot_isolation` to ON by default. Test transaction
  conflicts/rollback/retry behavior under the new isolation behavior before upgrading.
- MariaDB >= 11.6 changed default charset/collation to utf8mb4/uca1400. Inspect existing
  tables and explicitly select compatible collations instead of assuming defaults match.
- Verify authentication/TLS support in the installed driver, reserved words, JSON types,
  SQL modes, transaction isolation and migration syntax on the target engine.

For a new compatible ox deployment, evaluate MariaDB 12.3 LTS and the project's tested
maintained alternatives. For an existing deployment, first explain the measured problem
or support need. Test backup restore, migrations and application operations in staging;
major upgrades/downgrades need a recovery plan, not an assumed reversible package switch.
**No engine version guarantees the absence of FXServer hitches.** See `hitch-diagnostics.md`.

## 2. Topology and workload evidence

Player slots are not a capacity model. Record query arrival rate, concurrent operations,
hot data/index size, result sizes, writes/second, lock waits, memory/IO pressure, pool
queue time and application latency at representative load.

| Option | Evaluate |
|---|---|
| DB on FXServer host | Low transport overhead; contention for CPU, RAM and storage, including backups |
| Separate DB on nearby private network | Isolation and operations cost versus measured RTT, bandwidth and availability |
| Managed DB | Supported engine/features, connection/TLS limits, maintenance/failover behavior and cost |
| Read replica for analytics | Replication lag and consistency; never use stale balance/permission reads to authorize mutations |

A remote query includes network and driver overhead; several sequential round trips
accumulate latency. Measure it rather than asserting a universal 0.1/0.5 ms threshold.
NVMe may help IO-bound work; it cannot fix an unindexed query or serialized lock contention.
Use separate schema/credentials per server unless deliberate shared ownership is designed.
Schedule heavy analytics/backups with observed headroom; measure them under load.

## 3. my.cnf / my.ini tuning with a correctness budget

Inspect the **effective** configuration and service startup arguments first. Distribution,
container and Windows service paths differ. Verify each setting's availability, units,
scope and restart requirements for the exact engine/version before editing it. Preserve
the original configuration and change one justified variable or related group at a time.

| Setting / concern | Decision and validation |
|---|---|
| Buffer pool | Size for the active InnoDB working set and available memory after OS, FXServer, connections and other caches. Avoid paging; dataset size alone is not the working set. The vendor's dedicated-DB percentage is not for a shared game host. |
| Connections / driver pool | Budget all FXServer pools, panels, jobs and admin headroom; observe busy connections and wait time. A larger pool can increase contention and tail latency. Bound application admission/queues before increasing capacity. |
| Redo capacity | Tune from write/checkpoint pressure and recovery objectives; MariaDB and MySQL use different variables. Do not copy `innodb_log_file_size` into every version. |
| IO capacity / flush method | Match actual sustained storage behavior and platform/version defaults. No universal NVMe IOPS setting. |
| Temporary tables / caches | Fix query shape and indexes first; account for concurrent allocations. Raising every per-session buffer risks exhausting shared host RAM. |
| Charset / collation | Match existing key/join semantics and migrations; case/accent folding can change uniqueness. Changing the server default does not convert existing tables. |
| Slow logs | Set a threshold appropriate to the observed workload and capture duration; correlate with query digests/locks and FXServer timings. Rotate and protect logs. |
| Packet / batch limits | Bound bytes as well as rows. Increasing packet limits does not make unlimited JSON or huge transactions efficient. |

Keep durable commits as the default for money, inventory and ownership. With conventional
InnoDB/binlog configuration, use `innodb_flush_log_at_trx_commit=1` and, when binary
logging is enabled, `sync_binlog=1` for crash durability/consistency, subject to the
storage system honoring flushes. MariaDB's optional InnoDB-based binlog uses a different
mechanism: `sync_binlog` is ignored there; inspect the selected binlog engine.

`innodb_flush_log_at_trx_commit=2` defers redo flushing and can lose acknowledged
transactions after an OS crash/power loss. The periodic flush is not a strict one-second
loss bound. Do not offer it as a routine hitch fix or decide that losing RP data is
acceptable. A relaxation requires the owner's explicit recovery-point objective and
crash/recovery tests, including reconciliation with other data owners and replicas.

Read-only initial inspection, using an authorized connection:

```sql
SELECT VERSION(), @@version_comment;
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit';
SHOW VARIABLES LIKE 'sync_binlog';
SHOW VARIABLES LIKE 'max_connections';
SHOW GLOBAL STATUS LIKE 'Threads%';
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read%';
SHOW GLOBAL STATUS LIKE 'Innodb_row_lock%';
```

Compare **counter deltas over the same interval**, not lifetime ratios or absolute
counts alone. A high cache hit ratio can coexist with expensive scans/locks; connect it
to latency, physical reads and workload. No single ratio establishes DB health.

Use a dedicated runtime account with needed DML privileges. Give schema migration
privileges through a separate deployment identity where supported; auto-migrating
resources need their documented DDL privileges at migration time. Do not prescribe
DROP/ALTER grants to every runtime by default. Bind/firewall access to required hosts;
for remote connections verify encrypted transport and certificate validation supported
by the driver. Keep passwords out of examples, command-line arguments and shared files.

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
| `Extra` | Covering access can reduce reads | Sort/temp work needs cost analysis, not an automatic failure verdict |

These are clues, not binary pass/fail rules: a small-table scan may be cheaper than
an index; filesort does not necessarily mean a disk sort. Check cardinality, selectivity,
rows examined and workload. Composite/covering indexes trade reads for write/storage
cost; inspect existing indexes before adding or removing one. `ANALYZE` executes the
statement (including writes for MariaDB UPDATE/DELETE); use controlled data and an
authorized workload, not an assumed read-only diagnostic.

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
Bound and deduplicate the server-authorized plate list before batching; split large lists by measured byte/parameter/work limits. Cache stable definitions with an explicit invalidation policy. Avoid redundant polling; connection-time authorization that needs current DB state must not be replaced by an indefinitely stale preload.

### 7.3 Batch writes
Real framework patterns:
- **ESX** `Core.SavePlayers` (every 10 min): builds one parameter array per player and calls `MySQL.prepare` **once** with all sets.
- **ox_inventory** `db.saveInventories`: one `prepare.await` batch per category (players, trunks, gloveboxes) in parallel threads; stashes with a single multi-row `INSERT … VALUES (?, ?, ?), (?, ?, ?) … ON DUPLICATE KEY UPDATE` when `inventory:bulkstashsave` is true (default).
- **Qbox** saves each player on an interval (`updateInterval = 5` minutes) with an `UPDATE … WHERE citizenid = :citizenid`.

For custom data owned by this resource, design a bounded batch:
1. Snapshot immutable payloads with per-key versions; retain dirty state until confirmed.
2. Bound both rows **and encoded bytes/parameters** per chunk. A 500-row limit alone
   does not keep large JSON under `max_allowed_packet` or bound script serialization time.
3. Use placeholders for values and fixed/whitelisted SQL identifiers.
4. Check each chunk result; acknowledge only the versions actually submitted. A later
   chunk failing does not roll back earlier independently committed chunks.
5. Use one explicit transaction only where the business operation requires atomicity;
   keep it bounded and avoid external calls inside its locks.

Do not write directly to framework/inventory-owned tables while their memory state can
later overwrite your changes. Use their persistence owner. See the tested versioned
progress queue below for non-economic data and its explicit crash-loss limits.

`VALUES(col)` in `ON DUPLICATE KEY UPDATE` works on MariaDB and MySQL (deprecated on MySQL 8.0.20+ in favour of a row alias, which MariaDB does not support) — keep `VALUES()` for portability.

| Approach | Round trips | Use |
|---|---|---|
| Loop of `MySQL.update` | N queries/checkouts | Small independent operations where measured cost fits; otherwise bound/batch the workload |
| `MySQL.prepare` with N parameter sets | N on one connection, statement parsed once | different rows, same statement (ESX, ox_inventory) |
| Multi-row `VALUES (…),(…)` | 1 per chunk | inserts/upserts of many rows |
| `MySQL.transaction` | N in one transaction | must be atomic |

### 7.4 Cache in Lua, write behind
Use only for custom, non-economic progress with an explicitly accepted crash-loss window. One resource/process must own each key. Framework money and inventory keep their existing persistence owner.

Copy [versioned_store.lua](../assets/examples/versioned_store.lua) into `server/versioned_store.lua` and load it with ox_lib's `require` (server file; do not put it in `files`). The module stores serialized snapshots, not mutable table references. It has a bounded queue, permits only one in-flight write per key, acknowledges exactly the submitted generation, and retains unsaved released entries for retry.

```lua
-- server; MySQL schema: my_progress(citizenid PRIMARY KEY, data LONGTEXT NOT NULL)
local newStore = require 'server.versioned_store'
local saves = newStore(function(citizenid, payload)
    local result = MySQL.update.await(
        'INSERT INTO my_progress (citizenid, data) VALUES (?, ?) ON DUPLICATE KEY UPDATE data = VALUES(data)',
        { citizenid, payload })
    return type(result) == 'number' -- 0 can be a successful no-change upsert
end, 4096)

-- After validating a custom progress mutation, enqueue an immutable snapshot.
-- Check the result BEFORE reporting that the mutation was accepted.
local function queueProgress(citizenid, data)
    return saves.put(citizenid, json.encode(data))
end

-- On character unload: stop admitting that session's mutations first.
-- A failed flush stays pending; release does not discard it.
local function unloadProgress(citizenid)
    saves.flush(citizenid)
    saves.release(citizenid)
end
```

Call `flushAll()` periodically with a workload-appropriate interval; record queue age, failures and backpressure. `queue_full` must reject/defer the mutation, never silently drop an older entry. Drain after stopping new mutations during a graceful shutdown. `onResourceStop` is not a durability guarantee; process crashes lose pending memory even with correct retry handling.

This is a **write queue**, not a complete read cache or distributed lock. Coalesce concurrent loads separately; do not return live mutable tables to callers, reload stale DB values over newer pending state, or let a second process write the same keys. Reconnecting characters must reuse the authoritative in-memory state until pending writes are acknowledged. Test your framework's unload/load hooks and actual oxmysql error behavior in FXServer.

Evidence: module logic is exercised with Lua 5.4 and injected yielding/failing writers. SQL adapter, framework integration and crash durability require a real database/server test; no speedup is asserted.

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
- **Deadlocks** (error 1213, `ER_LOCK_DEADLOCK`) happen when two transactions lock the same rows in different orders. InnoDB rolls one back. Prevent: lock rows in a consistent order (e.g. sort the two citizenids before a transfer), touch as few rows as possible, avoid long transactions. Handle: retry a bounded number of times only when rollback is confirmed; ambiguous commits require reconciliation by operation ID.
The transaction body in [transfer.lua](../assets/examples/transfer.lua) validates bounded positive integer amounts, locks both existing accounts in a consistent order, and checks **both** affected-row counts. A missing receiver or rejected credit rolls the whole transaction back.

```lua
-- Copy the example to server/transfer.lua; this is a local module, not a framework API.
local transferBody = require 'server.transfer'
local ok, reason = transferBody(MySQL.startTransaction, fromCid, toCid, amount)
```

This is an illustrative transaction body for **custom InnoDB `bank_accounts`**, with unique `citizenid` and bounded integer `balance`. It is not a complete banking endpoint. The service must authenticate ownership, enforce permissions/rate limits, and atomically store a durable operation ID plus debit/credit ledger records in that same transaction before deployment. Do not use SQL to overwrite live framework-owned balances.

There is deliberately no automatic retry: `startTransaction` returns a boolean without classifying deadlocks versus connection/commit uncertainty. Retry only a classified rolled-back transaction, or reconcile using the durable operation ID and reuse it. An ambiguous result must not lead to a second untracked transfer. Lua tests use an injected transaction adapter; actual InnoDB locking, constraints and commit-failure behavior remain integration tests.

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

oxmysql side: choose `mysql_slow_query_warning` for the capture (e.g. 100 ms when investigating that latency class). Logs can contain resource names and parameters; limit retention/access and restore temporary settings. Driver timing can include scheduling/transport overhead; confirm what the installed version times and correlate with DB logs. A driver warning alone does not prove a slow SQL execution or a blocked FXServer thread.

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
mariadb-dump --defaults-extra-file=/secure/backup-client.cnf \
  --single-transaction --quick --routines --triggers --events fivem | gzip > /backups/fivem_$(date +%F_%H%M).sql.gz

# Physical (MariaDB)
mariadb-backup --defaults-extra-file=/secure/backup-client.cnf --backup --target-dir=/backups/full_$(date +%F)
mariadb-backup --prepare --target-dir=/backups/full_2026-10-07
# restore: stop MariaDB, empty datadir, then
mariadb-backup --copy-back --target-dir=/backups/full_2026-10-07 && chown -R mysql:mysql /var/lib/mysql
```
Store backup credentials in a restricted option file; validate tool/engine compatibility and capture command exit status. A pipeline producing a file is not proof of a complete backup. `--single-transaction` requires transactional tables and coordination with concurrent DDL.

Windows: `"C:\Program Files\MariaDB 12.3\bin\mariadb-dump.exe"` scheduled with Task Scheduler.

Rules: schedule at least daily + before every framework/resource update; keep copies off the machine (3-2-1); a backup user with `SELECT, SHOW VIEW, TRIGGER, LOCK TABLES, EVENT, RELOAD, PROCESS` only; **test restores** on a dev DB; binary log (`log_bin`) enables point-in-time recovery after a dupe exploit or a bad script wiped tables. oxmysql keeps `multipleStatements` off precisely because of injected `DROP TABLE` incidents (oxmysql #154 links the Cfx forum thread "database tables are deleted").

## 11. Schema changes on a live server, GUI tools

- `ALTER TABLE` on a big table needs a metadata lock: if a long query/transaction (or an idle DBeaver tab with an open transaction) holds the table, the ALTER waits **and every new query on that table queues behind it** → whole server freezes. Run migrations during restarts, or with `ALGORITHM=INPLACE, LOCK=NONE` where supported, and check `SHOW PROCESSLIST` first.
- **HeidiSQL** (Windows, bundled with the MariaDB MSI) and **DBeaver** (cross-platform) are fine for browsing and EXPLAIN. DBeaver in manual-commit mode keeps transactions open → locks; use auto-commit on production. Don't edit JSON blobs of online players by hand (the framework overwrites them at next save).
- Run framework SQL files only once; re-running `CREATE TABLE` files without `IF NOT EXISTS` errors, and some `INSERT`s duplicate data.

## 12. Do / don't summary

| Do | Don't |
|---|---|
| Maintained compatible engine, dated vendor verification, dedicated user | Treat latest engine or an engine switch as a hitch cure |
| Size the buffer pool from workload and available memory | Copy a slot-based memory preset or cause host paging |
| Design useful composite indexes from hot query plans and selectivity | Index every WHERE column blindly or ignore write/storage cost |
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
- MariaDB releases/support: https://mariadb.org/about/#maintenance-policy · https://mariadb.org/mariadb-server-12-3-11-8-11-4-and-10-11-q3-2026-maintenance-releases-and-goodbye-10-6/ · https://mariadb.org/mariadb-server-12-3-lts-released/
- MySQL versions/policy: https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html · https://dev.mysql.com/doc/relnotes/mysql/9.7/en/ · https://dev.mysql.com/doc/relnotes/mysql/8.4/en/
- MariaDB InnoDB variables: https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-system-variables · buffer pool: https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-buffer-pool
- MariaDB slow query log: https://mariadb.com/docs/server/server-management/server-monitoring-logs/slow-query-log/slow-query-log-overview
- MariaDB EXPLAIN: https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/explain
- MariaDB character sets (11.6 default change): https://mariadb.com/docs/server/reference/data-types/string-data-types/character-sets/setting-character-sets-and-collations · time zones: https://mariadb.com/docs/server/reference/data-types/string-data-types/character-sets/internationalization-and-localization/time-zones
- Backups: https://mariadb.com/docs/server/server-usage/backup-and-restore/mariadb-backup/mariadb-backup-overview · https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump
- MySQL InnoDB: https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html · https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html · https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html
- Tools: https://www.heidisql.com/ · https://dbeaver.io/
- mysql2 pool defaults: https://github.com/sidorares/node-mysql2/blob/v3.24.5/lib/pool_config.js

- Commit durability: https://mariadb.com/docs/server/server-management/server-monitoring-logs/binary-log/group-commit-for-the-binary-log · https://mariadb.com/docs/server/server-management/server-monitoring-logs/binary-log/innodb-based-binary-log
- MySQL expression defaults: https://dev.mysql.com/doc/refman/8.4/en/data-type-defaults.html
- MariaDB ANALYZE execution semantics: https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/analyze-statement
