# Database: oxmysql API reference

Baseline: oxmysql **2.14.3** (released 2026-10-06; driver mysql2 3.24.5, Node 22, requires FXServer ≥ 12913), verified 2026-10-07 against the source of `overextended/oxmysql@main` and the docs at overextended.dev.
Repo: https://github.com/overextended/oxmysql · Docs: https://overextended.dev/docs/oxmysql · npm: `@overextended/oxmysql` 2.14.3 · License: LGPL-3.0
Schema design, indexes, server tuning, backups and large-server patterns: [database-optimization.md](database-optimization.md).

## Contents
1. Install and load order
2. Connection string (formats, options, pool)
3. Convars, commands and events
4. Lua API overview (callback / await / promise forms)
5. Method reference and result shapes
6. Placeholders (`?`, `??`, named, `IN`, bulk)
7. Transactions (`transaction`, `startTransaction`)
8. Type conversion (dates, booleans, JSON, BIGINT, DECIMAL)
9. Error handling
10. JavaScript / TypeScript (exports, npm wrapper)
11. mysql-async / ghmattimysql compatibility and migration table
12. Version history and breaking changes (2.x)
13. Pitfalls (do / don't)
14. Sources

---

## 1. Install and load order

```cfg
# server.cfg — `set`, never `setr` (setr replicates the password to every client)
set mysql_connection_string "mysql://fivem:S3cretPass@127.0.0.1:3306/fivem?charset=utf8mb4"
set mysql_slow_query_warning 150
ensure oxmysql            # before every resource that queries the DB
ensure ox_lib
ensure qbx_core           # etc.
```

```lua
-- fxmanifest.lua of YOUR resource
server_script '@oxmysql/lib/MySQL.lua'   -- above your own server scripts
server_script 'server/main.lua'
dependency 'oxmysql'
-- optional, per resource (read by lib/MySQL.lua from the *calling* resource's manifest):
-- mysql_option 'return_callback_errors'
```

- Use the release zip (`releases/latest/download/oxmysql.zip`). Cloning the repo gives unbuilt TypeScript and the error *"No such export … in resource oxmysql"* (oxmysql issue #154).
- The generated fxmanifest declares `provide 'mysql-async'` and `provide 'ghmattimysql'`, `node_version '22'`, and `dependencies { '/server:12913' }`.
- `lib/MySQL.lua` is **server-only**. Never query from the client; send a validated net event / ox_lib callback to the server.

## 2. Connection string

Read once at start from convar `mysql_connection_string`; fallback env var `DB_CONNECTION`; default `mysql://root@localhost`.

| Format | Example |
|---|---|
| URI | `mysql://user:pass@host:3306/database?charset=utf8mb4&connectionLimit=20` |
| Key/value (semicolon) | `user=fivem;password=S3cret;host=127.0.0.1;port=3306;database=fivem;charset=utf8mb4` |

The key/value form **must be quoted** in server.cfg: an unquoted `;` splits the line into separate console commands (see convars-and-commands.md section 1).

Key/value aliases accepted (source `src/config.ts`): `host`/`hostname`/`ip`/`server`/`data source`/`address`/`addr` → host; `user`/`user id`/`username`/`uid` → user; `password`/`pwd`/`pass` → password; `database`/`db` → database.

**Special characters**: the URI parser splits on `:` and `@` and does **not** URL-decode, so avoid `; , / ? : @ & = + $ #` in the password, or switch format (official docs advice). Easiest: generate an alphanumeric password.

Any extra key is passed to mysql2 `createPool` (values arrive as **strings**). Defaults oxmysql sets: `connectTimeout=60000`, `supportBigNumbers=true`, `jsonStrings=true`, `trace=false`, custom `typeCast`, own named-placeholder parser. `dateStrings`, `flags` and `ssl` values are JSON-parsed.

| Option | Default | Notes |
|---|---|---|
| `charset` | mysql2 default `UTF8MB4_UNICODE_CI` | `charset=utf8mb4` maps to `utf8mb4_general_ci` (45). Match your table collation (see optimization §6). |
| `connectionLimit` | **10** | Pool size (mysql2 `PoolConfig`). Raise only if queries queue (see §2.1). |
| `queueLimit` | 0 (unlimited) | Requests wait for a free connection. |
| `waitForConnections` | true | |
| `maxIdle` / `idleTimeout` | = connectionLimit / 60000 ms | Idle connections closed after 60 s. |
| `enableKeepAlive` | true | TCP keep-alive. |
| `connectTimeout` | 60000 | ms. |
| `multipleStatements` | off | oxmysql prints *"multipleStatements is enabled… may cause SQL injection"*. **Never pass `multipleStatements=false`** — the string `"false"` is truthy and enables it. Omit the key. |
| `decimalNumbers` | off | `DECIMAL` returned as string unless enabled (precision loss possible). |
| `namedPlaceholders` | on | `namedPlaceholders=false` disables `@name`/`:name` conversion (useful if queries contain `@user_variables`). |
| `ssl` | off | JSON, e.g. `ssl={"rejectUnauthorized":false}` for a remote managed DB. |
| `timezone` | `local` | Only affects JS `Date` parameters; Lua sends numbers, so it rarely matters (see §8). |

Unknown keys make mysql2 print *"Ignoring invalid configuration option passed to Connection"*.

On connect oxmysql prints `[<db version>] Database server connection established!` and runs `SET TRANSACTION ISOLATION LEVEL <level>` on every new pool connection. If it fails it retries every 30 s and prints the config with the password masked.

### 2.1 Pool sizing
Node is single-threaded; the pool just lets several queries be in flight at once. Ten connections are enough for most servers because typical FiveM queries take 0.2–5 ms. Raise to 20–30 only when the slow-query warnings show many *fast* queries becoming slow at peak (queueing), never as a fix for a slow query. Every FXServer, txAdmin, web panel, Discord bot and backup job uses its own connections — the DB's `max_connections` must cover the sum (optimization §3).

## 3. Convars, commands and events

All `mysql_*` convars except the connection string, isolation level, result-set warning and logger are re-read **every second**, so `set mysql_debug true` in the live console takes effect without restart.

| Convar | Default (source) | Purpose |
|---|---|---|
| `mysql_connection_string` | `mysql://root@localhost` | See §2. |
| `mysql_slow_query_warning` | **200** ms in code (docs say 150) | Prints `<resource> took X ms to execute a query!` with query + params. Set it explicitly. |
| `mysql_debug` | `false` | `true` = log every query; or a JSON array of resources: `set mysql_debug ["ox_inventory","qbx_core"]`. Uses MySQL `SET profiling` for exact timings (auto-disabled on servers without it, e.g. TiDB). Dev only. |
| `mysql_ui` | `false` | Enables in-game `/mysql` query viewer. Needs ACE `command.mysql` (or `command`). Keeps the last `mysql_log_size` queries per resource in memory. Docs: dev / small servers only. |
| `mysql_log_size` | 100 (10000 while debug) | Per-resource log cap for the UI. |
| `mysql_transaction_isolation_level` | **2** | 1 = REPEATABLE READ, 2 = READ COMMITTED, 3 = READ UNCOMMITTED, 4 = SERIALIZABLE. Applied to every pool connection (not only transactions). Note InnoDB's own default is REPEATABLE READ. |
| `mysql_resultset_warning` | 1000 | Warns `executed a query with an oversized result set (N results)`. |
| `mysql_versioncheck` | 1 | `0` disables the GitHub update check. |
| `mysql_logger_service` | `''` | `fivemanage` (built-in, needs `set FIVEMANAGE_LOGS_API_KEY`) or `@resource/path/file` (loads `path/file.js` from that resource; the JS file body must `return` a function that receives `{ level, resource, message, metadata }` — see `logger/fivemanage.js`). |

Commands: `oxmysql_debug add <resource>` / `oxmysql_debug remove <resource>` (server console only, not persistent) · `mysql` (in-game UI).

Server events (local, `AddEventHandler`) — useful for Sentry/Discord alerting:
```lua
AddEventHandler('oxmysql:error', function(data)
    -- data.query, data.parameters, data.message, data.err, data.resource
end)
AddEventHandler('oxmysql:transaction-error', function(data)
    -- data.query (all statements), data.parameters, data.message, data.err, data.resource
end)
```

## 4. Lua API overview

`lib/MySQL.lua` defines a global `MySQL` table. Each of `query, single, scalar, insert, update, prepare, rawExecute, transaction` exists in two forms:

```lua
-- 1) Callback (non-blocking). Callback receives the result; with
--    mysql_option 'return_callback_errors' it receives (result, err).
MySQL.query('SELECT 1 AS one', {}, function(rows) print(rows[1].one) end)
MySQL.query('SELECT 1 AS one', function(rows) end)          -- parameters may be omitted

-- 2) Await (yields the current coroutine; returns the result; raises a Lua error on failure)
local rows = MySQL.query.await('SELECT 1 AS one')
```

- `.await` must run inside a coroutine: net/event handlers, `CreateThread`, `lib.callback` handlers, commands. Not at file scope during resource start — wrap in `CreateThread` or `MySQL.ready`.
- "Promise form" = the JS side (`exports.oxmysql.<method>_async`, npm wrapper). In Lua, `.await` is the promise form.
- `MySQL.Async.*` / `MySQL.Sync.*` aliases exist for mysql-async code (§11).

Readiness helpers:
```lua
MySQL.ready(function()                -- runs in a new thread once oxmysql started AND the pool is connected
    MySQL.query.await([[CREATE TABLE IF NOT EXISTS `my_res_data` (
        `id` INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        `owner` VARCHAR(60) NOT NULL,
        `data` LONGTEXT NULL,
        KEY `idx_owner` (`owner`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci]])
end)

CreateThread(function()
    MySQL.ready.await()               -- blocking variant
    local isUp = exports.oxmysql:isReady()   -- boolean; exports.oxmysql:awaitConnection() also exists
end)
```
Queries sent before the pool exists are not lost: `getConnection()` waits (`while (!pool) await sleep(0)`) until oxmysql has connected, so `MySQL.ready` is only needed to run one-time setup in order, not to make queries safe. `.await` still needs a coroutine. Source: https://github.com/overextended/oxmysql/blob/main/src/database/connection.ts

## 5. Method reference and result shapes

| Lua | Returns | Typical use |
|---|---|---|
| `MySQL.query(q, p)` | SELECT: array of row tables (`{}` when none). Other statements: result header `{ affectedRows, insertId, changedRows, fieldCount, info, serverStatus, warningStatus }` | Anything; DDL; multi-row statements |
| `MySQL.single(q, p)` | first row table or `nil` | `... WHERE id = ? LIMIT 1` |
| `MySQL.scalar(q, p)` | first column of first row or `nil` | `SELECT money ...`, `SELECT COUNT(*) ...`, `SELECT 1 ... LIMIT 1` |
| `MySQL.insert(q, p)` | `insertId` (0 if the table has no AUTO_INCREMENT) | INSERT |
| `MySQL.update(q, p)` | `affectedRows` | UPDATE / DELETE |
| `MySQL.prepare(q, p)` | server-side prepared statement (binary protocol); see below | hot queries, batches |
| `MySQL.rawExecute(q, p)` | like prepare but never unpacked: SELECT → always array of rows; DML → result header(s) | batches where you need every header |
| `MySQL.transaction(queries, p)` | `true` / `false` | all-or-nothing writes (§7) |
| `MySQL.startTransaction(fn)` | `true` / `false` (call from a thread) | interactive transaction (§7) |
| `MySQL.Async.store(q)` / `MySQL.Sync.store(q)` | number id usable as the query argument | legacy; avoid |

Notes from the source (`src/database/rawExecute.ts`, `src/utils/parseExecute.ts`):
- **`prepare` unpacking** with one parameter set: SELECT returning one row with one column → the value; one row with several columns → that row; several rows → array of rows; no rows → `nil`. INSERT → insertId, UPDATE/DELETE → affectedRows.
- **`prepare` batch**: pass an array of parameter arrays to run the same statement once per set on one connection; result is an array (one entry per set).
  ```lua
  local saved = MySQL.prepare.await('UPDATE players SET money = ? WHERE citizenid = ?', {
      { json.encode(p1.money), p1.citizenid },
      { json.encode(p2.money), p2.citizenid },
  })  -- { 1, 1 }  (affectedRows per set)
  ```
- **`prepare` detects the statement type from the first word, case-sensitive**: only a query that literally starts with `INSERT `, `UPDATE ` or `DELETE ` gets insertId/affectedRows. `insert into …` (lowercase) or a leading newline/space returns `nil`. Write SQL keywords in uppercase with no leading whitespace.
- `prepare` / `rawExecute` accept only `?` placeholders (named/`??` throw). TINYINT(1)/BIT are **not** converted to booleans there (dates are, since 2.11.0) — docs pages still say dates are not; source says they are.
- Missing parameters are padded with `NULL` (since 2.14.1/2.14.2 also `nil`/undefined → `NULL`). Too many parameters for `query`-family methods throws *"Expected N parameters, but received M"*.

## 6. Placeholders

```lua
-- Positional (recommended)
MySQL.single.await('SELECT `firstname` FROM `users` WHERE `identifier` = ? AND `group` = ?', { identifier, group })

-- Named — the docs label this syntax "deprecated"; still supported in 2.14.3.
-- Keys may be written as name, @name or :name.
MySQL.update.await('UPDATE players SET name = :name WHERE citizenid = :cid', { name = newName, cid = citizenid })
MySQL.update.await('UPDATE players SET name = @name WHERE citizenid = @cid', { ['@name'] = newName, ['@cid'] = citizenid })
-- The same name may appear several times (Qbox uses this for ON DUPLICATE KEY UPDATE).

-- Identifier placeholder (query/single/scalar/insert/update only), escapes as `col`:
MySQL.query.await('SELECT ?? FROM ?? WHERE id = ?', { 'money', 'accounts', id })
-- …but NEVER take identifiers from client input; whitelist them in Lua instead.

-- IN list: pass ONE parameter that is an array (text protocol expands it to 'a', 'b', 'c')
local rows = MySQL.query.await('SELECT plate, owner FROM owned_vehicles WHERE plate IN (?)', { plates })
-- Guard: an empty array produces invalid SQL `IN ()` — check `#plates > 0` first.

-- Alternative that also works with prepare (ESX multicharacter uses this): build "?, ?, ?"
local marks = string.rep('?', #ids, ', ')
local rows2 = MySQL.query.await(('SELECT identifier FROM users WHERE identifier IN (%s)'):format(marks), ids)

-- Bulk multi-row insert, one round trip: an array of row-arrays as ONE parameter
MySQL.query.await('INSERT INTO logs (who, action, amount) VALUES ?', { { { 'a', 'buy', 10 }, { 'b', 'sell', 5 } } })
```

Rules:
- `@name` / `:name` conversion happens only when parameters is a **key/value table** and the SQL contains `@` or `:`. A placeholder directly after a quote is ignored, but `@uservar` in SQL plus a named-parameter table will be misparsed → use positional params or `namedPlaceholders=false`.
- Named keys not provided become `NULL` (no error) — typos silently write NULL.
- **Validate types before binding client data.** v2.14.0 updated mysql2 to fix an SQL-injection issue in its escaping dependency (sqlstring). In text-protocol escaping, a *table* bound where a string is expected becomes `key = value` pairs, which is the classic injection vector. `if type(plate) ~= 'string' or #plate > 8 then return end` before every query fed by a net event.
- Never build SQL with `..` or `string.format` from user data. Formatting is acceptable only for values you control (table names from config, generated `?` lists).

## 7. Transactions

### 7.1 `MySQL.transaction` (batch, all-or-nothing)
Three accepted formats (source `parseTransaction.ts`):
```lua
-- a) objects (key `values` or `parameters`)
local ok = MySQL.transaction.await({
    { query = 'UPDATE users SET accounts = ? WHERE identifier = ?', values = { accountsJson, identifier } },
    { query = 'INSERT INTO owned_vehicles (owner, plate, vehicle) VALUES (?, ?, ?)', values = { identifier, plate, propsJson } },
})

-- b) tuples
local ok2 = MySQL.transaction.await({
    { 'INSERT INTO test (id) VALUES (?)', { 1 } },
    { 'INSERT INTO test (id, name) VALUES (?, ?)', { 2, 'bob' } },
})

-- c) list of SQL strings + one shared named-parameter table
local ok3 = MySQL.transaction.await({
    'INSERT INTO test (id, name) VALUES (@id, @name)',
    'UPDATE test SET name = @newname WHERE id = @id',
}, { id = 2, name = 'John', newname = 'Jane' })
```
- Returns `false` on any failure (rolls back, prints the failing statement, fires `oxmysql:transaction-error`); it does **not** raise.
- **A conditional statement that matches 0 rows is not a failure.** `UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?` with too little balance updates 0 rows, and the batch still **commits** the remaining statements (e.g. the credit). oxmysql rolls back only when a query throws (`src/database/rawTransaction.ts`). For "check then debit/credit" logic use `MySQL.startTransaction` and `return false` when `affectedRows ~= 1` (section 7.2, database-optimization.md section 8).
- You cannot read intermediate results (e.g. an insertId) — use `LAST_INSERT_ID()` in the next statement or `startTransaction`.

### 7.2 `MySQL.startTransaction` (interactive, since 2.12.0; "experimental" label removed in 2.14.2)
```lua
-- server, inside a thread / handler
local function buyVehicle(identifier, plate, model, price)
    local success = MySQL.startTransaction(function(query)
        -- lock the buyer row until commit/rollback
        local rows = query('SELECT `accounts` FROM `users` WHERE `identifier` = ? FOR UPDATE', { identifier })
        local row = rows[1]
        if not row then return false end                       -- explicit false => ROLLBACK

        local accounts = json.decode(row.accounts)
        if (accounts.bank or 0) < price then return false end
        accounts.bank = accounts.bank - price

        query('UPDATE `users` SET `accounts` = ? WHERE `identifier` = ?', { json.encode(accounts), identifier })
        local res = query('INSERT INTO `owned_vehicles` (`owner`, `plate`, `vehicle`) VALUES (?, ?, ?)',
            { identifier, plate, json.encode({ model = model, plate = plate }) })
        return res.affectedRows == 1                            -- nil or truthy => COMMIT
    end)
    return success
end
```
- `query(sql, params)` returns the raw driver result: array of rows for SELECT, header table for DML. Supports `?` and named placeholders.
- Commit unless the function returns exactly `false`. Any SQL error or Lua `error()` rolls back and returns `false` (logged via `oxmysql:error`).
- Hard **30 s timeout**: after it, further `query` calls fail and the transaction rolls back. The connection is held for the whole function — never `Wait`, call client callbacks, HTTP, or other slow work inside.
- Since 2.14.2 an unfinished transaction is rolled back (never silently committed) when the connection is released.
- Note: with framework player objects (ESX/QB/Qbox) money lives in memory and is saved later; editing the money column directly in SQL while the player is online gets overwritten at the next save. Use the framework API for online players, SQL for offline ones.

## 8. Type conversion (Lua side)

| SQL type | `query`/`single`/`scalar` | `prepare`/`rawExecute` |
|---|---|---|
| `DATETIME`, `TIMESTAMP`, `DATE` | number, **milliseconds** since epoch (`os.date('%Y-%m-%d', ts // 1000)`) | same (since 2.11.0) |
| `TINYINT(1)`, `BIT(1)` | boolean | number (not boolean) |
| `JSON` / `LONGTEXT` | string → `json.decode` yourself (`jsonStrings=true`) | string |
| `BIGINT` | number; string if beyond 2^53 (`supportBigNumbers`) | same |
| `DECIMAL` | string (unless `decimalNumbers=true`) | string |
| binary `BLOB` | array of byte numbers | array of byte numbers |
| `NULL` | key absent from the Lua row (`row.col == nil`) | same |

Dates are parsed by Node with the **FXServer host's local timezone**. If the DB host uses another timezone, convert in SQL: `SELECT UNIX_TIMESTAMP(last_logged_out) AS lastLoggedOutUnix` (Qbox does exactly this) or store epoch seconds in `BIGINT`.

## 9. Error handling

| Form | On SQL error |
|---|---|
| `.await` / JS `_async` / npm wrapper | raises (Lua error / rejected promise). Wrap with `pcall`. |
| Callback, default | error printed to console, `oxmysql:error` fired, **callback never called** — code waiting on it hangs. |
| Callback + `mysql_option 'return_callback_errors'` | callback called as `cb(nil, errMessage)`. |
| `transaction` | returns `false`. |
| `startTransaction` | returns `false`. |

```lua
local ok, result = pcall(MySQL.scalar.await, 'SELECT 1 FROM ox_inventory LIMIT 1')
if not ok then
    -- table missing, permission denied, syntax error... (result is the error string)
    lib.print.error(('DB check failed: %s'):format(result))
end
```
- **"Your database does not accept the required authentication method"**: oxmysql and txAdmin use node-mysql2, which supports only `mysql_native_password`, `caching_sha2_password`, `sha256_password` and `mysql_clear_password`. It has no MariaDB `ed25519`/`parsec` (https://github.com/sidorares/node-mysql2/tree/master/lib/auth_plugins). Check with `SELECT user, host, plugin FROM mysql.user;`. Create a dedicated, non-root account: `CREATE USER 'fivem'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('...');` (MariaDB syntax; MySQL uses `IDENTIFIED WITH ... BY`) and grant only the server database: `GRANT ALL ON qbox.* TO 'fivem'@'localhost';`. `user@localhost` and `user@127.0.0.1` are different accounts.

Common messages: `ER_NO_SUCH_TABLE`, `ER_DUP_ENTRY` (unique key — use upsert), `ER_LOCK_DEADLOCK` / `ER_LOCK_WAIT_TIMEOUT` (retry, see optimization §8), `Unknown column`, *"Unable to establish a connection"* (check string, DB running, reserved characters), `AUTH_SWITCH_PLUGIN_ERROR (auth_gssapi_client)` (oxmysql issue #213; typically a Windows MariaDB `root` without password — create a dedicated user with a password).

## 10. JavaScript / TypeScript

Raw exports (no dependency). Every method `X` is exported as `X` (callback), `X_async` (promise) and deprecated `XSync`:
```js
// server.js
const rows = await exports.oxmysql.query_async('SELECT * FROM users WHERE identifier = ?', [id]);
const money = await exports.oxmysql.scalar_async('SELECT money FROM players WHERE citizenid = ?', [cid]);
const insertId = await exports.oxmysql.insert_async('INSERT INTO logs (msg) VALUES (?)', ['hi']);
const ok = await exports.oxmysql.transaction_async([{ query: 'DELETE FROM a WHERE id = ?', values: [1] }]);
exports.oxmysql.query('SELECT 1', [], (result) => console.log(result));
```
Exports list: `query single scalar update insert prepare rawExecute transaction startTransaction isReady awaitConnection store` (+ deprecated `execute`/`fetch` = query).

npm wrapper (types + same shape as Lua):
```ts
import { oxmysql as MySQL } from '@overextended/oxmysql';

MySQL.ready(async () => {
  const row = await MySQL.single<{ firstname: string }>('SELECT firstname FROM users WHERE identifier = ? LIMIT 1', [id]);
  const ok = await MySQL.startTransaction(async (query) => {
    await query('UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?', [10, 1, 10]);
    return true;
  });
});
```
Wrapper methods reject on error (they always pass `isPromise = true`).

C#: no official wrapper; call exports (`Exports["oxmysql"].query_async(...)`) — **UNVERIFIED** in this skill; test before relying on it.

## 11. mysql-async / ghmattimysql compatibility

oxmysql `provide`s both resource names, so `dependency 'mysql-async'` still resolves. Delete the old resources and change includes:

```diff
- server_script '@mysql-async/lib/MySQL.lua'
+ server_script '@oxmysql/lib/MySQL.lua'
```

| Legacy call | oxmysql equivalent (preferred) | Returns |
|---|---|---|
| `MySQL.Async.fetchAll(q, p, cb)` / `MySQL.Sync.fetchAll` | `MySQL.query(q, p, cb)` / `MySQL.query.await` | rows |
| `MySQL.Async.fetchScalar` / `Sync.fetchScalar` | `MySQL.scalar` | value |
| `MySQL.Async.fetchSingle` / `Sync.fetchSingle` | `MySQL.single` | row |
| `MySQL.Async.execute` / `Sync.execute` | `MySQL.update` | affectedRows |
| `MySQL.Async.insert` / `Sync.insert` | `MySQL.insert` | insertId |
| `MySQL.Async.transaction` / `Sync.transaction` | `MySQL.transaction` | boolean |
| `MySQL.Async.prepare` / `Sync.prepare` | `MySQL.prepare` | see §5 |
| `MySQL.Async.store` / `Sync.store` | inline the SQL string | id |
| `MySQL.ready(cb)` | `MySQL.ready(cb)` | — |
| `exports['mysql-async']:mysql_fetch_all` / `mysql_execute` / `mysql_insert` / `mysql_fetch_scalar` / `mysql_transaction` / `mysql_store` | provided (C#/closed-source) | |
| `exports.ghmattimysql:execute(q, p, cb)` | `MySQL.query` | rows / header |
| `exports.ghmattimysql:executeSync` | `MySQL.query.await` | |
| `exports.ghmattimysql:scalar` / `scalarSync` | `MySQL.scalar` | |
| `exports.ghmattimysql:transaction` / `transactionSync` | `MySQL.transaction` | |
| `exports.ghmattimysql:store` | inline SQL | |

Behaviour differences to check when migrating:
- `@name` keys: mysql-async code like `{ ['@id'] = id }` works unchanged.
- Dates come back as millisecond numbers (mysql-async compatible typecast), TINYINT(1) as booleans.
- Callback-style code that never handled errors may now hang silently on a failed query (§9) — add `return_callback_errors` or move to `.await` + `pcall`.
- MySQL 8 reserved words (`group`, `rank`, `groups`…) need backticks; old MySQL 5.7-era SQL files may fail on MySQL 8 (docs).

## 12. Version history and breaking changes (2.x)

| Version | Date | Change |
|---|---|---|
| 2.0.0 | 2022-02-18 | **Breaking**: old exports removed; Lua must use `lib/MySQL.lua`; JS export names changed. In-game UI added. |
| 2.3.0 | 2022-04-29 | Tuple transaction format; `prepare` no longer wraps INSERT/UPDATE in a transaction. |
| 2.3.4 | 2022-06-27 | `oxmysql:error` event. |
| 2.4.0 | 2022-07-28 | ghmattimysql exports provided; npm package `@overextended/oxmysql`. |
| 2.5.0 | 2022-08-24 | `mysql_debug` JSON array + `oxmysql_debug add/remove`. |
| 2.7.0 | 2023-06-17 | `rawExecute`; `isReady` / `awaitConnection` exports. |
| 2.8.0 | 2024-02-02 | UI log size limit (`mysql_log_size`). |
| 2.9.x | 2024-02/03 | experimental interactive transaction export, 30 s timeout. |
| 2.10.0 | 2024-05-08 | Oversized result-set warning (`mysql_resultset_warning`). |
| 2.11.0 | 2024-08-09 | Fivemanage logger; date typecasting for `prepare` (binary protocol) — dates from `prepare` changed type. |
| 2.12.0 | 2024-10-27 | `MySQL.startTransaction`; `mysql_option 'return_callback_errors'`; `mysql_logger_service '@res/path'`. |
| 2.13.0 | 2025-02-17 | Node 22, **requires FXServer ≥ 12913** (pre-release at the time). |
| 2.13.2 | 2026-04-24 | Node 22 build re-released as stable. |
| 2.14.0 | 2026-04-25 | **Caution release**: large mysql2 upgrade, fixes SQL injection via sqlstring; "no guarantee this release works without any changes". Test before updating production. |
| 2.14.1 | 2026-05-04 | `undefined`/`nil` params bound as NULL instead of throwing. |
| 2.14.2 | 2026-10-03 | Params padded at correct indices; shared transaction params no longer corrupted; `store()` fixed; unfinished transactions rolled back on dispose; explicit TINY/BIT boolean typecast; profiler fallback; startTransaction no longer "experimental". |
| 2.14.3 | 2026-10-06 | mysql2 dependency update. |

Re-verify: `gh release list -R overextended/oxmysql -L 5`.

## 13. Pitfalls (do / don't)

| Don't | Do |
|---|---|
| `'... WHERE id = ' .. id` | `'... WHERE id = ?', { id }` |
| Bind client values without type checks | `type(x) == 'string'`, length/range checks, then bind |
| `.await` at file scope | inside `CreateThread`, handlers or `MySQL.ready` |
| `SELECT *` on wide JSON tables in hot paths | select only needed columns; cache in Lua (optimization §5) |
| Loop of single INSERT/UPDATE per row | `prepare` with array of parameter sets, multi-row `VALUES ?`, or `transaction` |
| Check-then-insert (`SELECT` then `INSERT`) | `INSERT ... ON DUPLICATE KEY UPDATE` on a unique key (official docs) |
| `REPLACE INTO` | upsert (REPLACE deletes and re-inserts: new ids, cascades) |
| `set mysql_debug true` / `mysql_ui true` on a 300-slot live server | enable for one resource briefly; use the DB slow query log |
| `multipleStatements=false` in the string | omit the key |
| Lowercase `insert`/leading newline with `prepare` | uppercase keyword first |
| `Wait()` / client callbacks inside `startTransaction` | gather data first, keep the transaction < 100 ms |
| `single` on a non-unique column without `LIMIT 1` | add `LIMIT 1` (stops scanning early) |
| `setr mysql_connection_string` | `set` |

## 14. Sources
- https://github.com/overextended/oxmysql (README, `lib/MySQL.lua`, `lib/MySQL.ts`, `src/config.ts`, `src/index.ts`, `src/database/*.ts`, `src/utils/*.ts`, `src/logger/index.ts`, `src/profiler/index.ts`, `build.js`, `patches/*.patch`, `package.json`)
- https://github.com/overextended/oxmysql/releases (v2.0.0 – v2.14.3 notes)
- https://github.com/overextended/oxmysql/issues/154 (common issues) · https://github.com/overextended/oxmysql/issues/213
- https://overextended.dev/docs/oxmysql (and `/Functions/query`, `/single`, `/scalar`, `/insert`, `/update`, `/prepare`, `/rawExecute`, `/transaction`, `/placeholders`, `/ui`, `/benchmark`) — source: https://github.com/overextended/overextended.github.io/tree/main/content/docs/oxmysql
- https://www.npmjs.com/package/@overextended/oxmysql (registry: 2.14.3)
- https://github.com/sidorares/node-mysql2/blob/v3.24.5/lib/pool_config.js · https://github.com/sidorares/node-mysql2/blob/v3.24.5/lib/connection_config.js
- https://github.com/esx-framework/esx_core (`esx_multicharacter/server/modules/database.lua`, `es_extended/server/functions.lua`)
- https://github.com/Qbox-project/qbx_core/blob/main/server/storage/players.lua
