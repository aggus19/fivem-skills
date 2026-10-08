# ox_lib — utilities: require, locale, print, logger, class, collections, table/math/string, timers, cron, misc

Baseline: ox_lib v3.40.0 — verified 2026-10-07

Part of the ox_lib reference. Entry point and index: [ox-lib.md](ox-lib.md).

## Contents
1. `require`, `lib.require`, `lib.load`, `lib.loadJson`, modules v2 (`Ox.*`)
2. Locales: `lib.locale`, `locale()`, `lib.getLocale`
3. `lib.print`
4. `lib.logger` (Datadog / Fivemanage / Grafana Loki)
5. `lib.class`
6. `lib.array`
7. Collections: `lib.map`, `lib.set`, `lib.lru`, `lib.heap`, `lib.ringbuffer`, `Ox.DataView`
8. `lib.table`, `lib.math`, `lib.string` (global extensions)
9. `lib.waitFor`, `SetInterval`/`ClearInterval`, `lib.timer`
10. `lib.cron` (server)
11. `lib.uuid`, `lib.selector`
12. Server misc: `lib.getFilesInDirectory`, `lib.versionCheck`, `lib.checkDependency`
13. Common mistakes
14. Sources

---

## 1. require and friends (shared)
`@ox_lib/init.lua` replaces the global `require` with `lib.require`, which loads files **from resources** through `LoadResourceFile`, not from disk.
```lua
local config = require 'config.shared'           -- @thisresource/config/shared.lua (or config/shared/init.lua)
local utils  = require '@other_res.modules.utils' -- a module from another resource (the file must be in its `files`/scripts)
local glm    = require 'glm'                      -- built-in CfxLua libraries still resolve via the native require
local DataView = require 'Ox.DataView'           -- ox_lib "modules v2" (v3.40): @ox_lib/modules/DataView/init.lua
local data   = lib.loadJson('data.vehicles')      -- @thisresource/data/vehicles.json, decoded
local result = lib.load('scripts.once', env?)     -- runs the file each time (not cached)
```
- Dots in a module name map to `/`. The search path is `./?.lua;./?/init.lua`.
- Modules are cached per resource in `package.loaded`, which is read-only from outside. A module that returns `nil` is cached as `true`. A circular require raises a "circular-dependency" error.
- **Client files must be listed in the manifest** (`files {}` or client scripts). `LoadResourceFile` can only read files that are sent to clients. Server-only modules don't need `files`.
- Paths are resolved relative to the resource **that called `require`** (found from the call stack), so a shared module required from another resource still loads its own siblings correctly.
- `Ox.<Name>` is the v3.40 pattern for new ox_lib modules ("modules v2"). They are loaded with `require` instead of being added to the `lib.*` namespace. `DataView` is the first one.

## 2. Locales (shared)
Manifest and file layout:
```lua
-- fxmanifest.lua
ox_lib 'locale'                  -- loads the locale module and calls lib.locale() at startup
files { 'locales/*.json' }       -- required for client-side locales
-- locales_path 'i18n'           -- v3.38+: custom folder (default 'locales')
```
`locales/en.json`:
```json
{
  "shop": { "title": "Shop", "bought": "You bought %sx %s" },
  "greeting": "Welcome to ${shop.title}"
}
```
```lua
lib.notify({ title = locale('shop.title'), description = locale('shop.bought', 2, 'bread') })
```
- `locale(key, ...)` returns the string, formatted with `string.format` when you pass arguments. **It returns the key itself if the key is missing** (no error).
- Nested JSON objects are flattened into dot keys. `${other.key}` references are expanded at load time (v3.33+).
- `en.json` is always loaded first, and the selected language is merged over it, so missing translations fall back to English.
- Language selection: on the **server**, `GetConvar('ox:locale', 'en')`. On the **client**, the player's choice from `/ox_lib` (when `ox:userLocales` is 1, the default), otherwise `ox:locale`. Set it with `setr ox:locale "es"` so clients can read it. When a player changes language, every resource that loaded the module reloads.
- `lib.locale(key?)` loads or reloads manually. `lib.getLocales()` returns the whole dictionary. `lib.getLocaleKey()` returns the current language. `lib.getLocale(resource, key)` copies one string from another resource (through its `getLocale` export).
- `ox_lib/locales/` ships 33 languages for ox_lib's own UI strings (ar, cs, da, de, el, en, es, et, fi, fr, he, hr, hu, id, it, ja, ka, lt, nl, no, pl, pt, pt-br, ro, ru, sk, sl, sv, th, tr, zh-cn, zh-tw, al).

## 3. lib.print (shared)
```lua
lib.print.error(...) ; lib.print.warn(...) ; lib.print.info(...) ; lib.print.verbose(...) ; lib.print.debug(...)
```
- Output looks like `[resource] [LEVEL] args…`. Tables are pretty-printed as JSON (functions are shown with `tostring`).
- Level: `ox:printlevel:<resource>`, falling back to `ox:printlevel`, falling back to `info`. Levels are `error < warn < info < verbose < debug`, and a message prints when its level is ≤ the configured level.
- Changes are picked up live through `AddConvarChangeListener` (v3.30+). For client-side levels use `setr`:
```cfg
setr ox:printlevel "warn"
setr ox:printlevel:myresource "debug"
```

## 4. lib.logger (server)
```lua
lib.logger(source, event, message, ...)
-- source: player id (identifiers are added as tags, IPs excluded) or any string/number
-- event:  short event name; message: string
-- ...:    tags. Datadog: strings joined with ','; Fivemanage/Loki: 'key:value' strings or tables {key=value}
lib.logger(src, 'shop:buy', ('bought %s x%d for $%d'):format(item, count, price), 'shop:' .. shopId, { item = item })
```
Logs are buffered and sent in one HTTP batch every 500 ms. If the provider isn't configured, `lib.logger` is a **no-op**.

| Provider | Convars (use `set`, never `setr`: these are secrets) |
|---|---|
| Datadog (default `ox:logger`) | `set datadog:key "<api key>"`, `set datadog:site "datadoghq.com"` (or `datadoghq.eu`, `us5.datadoghq.com`, …) |
| Fivemanage | `set ox:logger "fivemanage"`, `set fivemanage:key "<logs token>"`, optional `set fivemanage:dataset "<dataset>"` |
| Grafana Loki | `set ox:logger "loki"`, `set loki:endpoint "<host without scheme or with https://>"`, `set loki:user "<user>"`, `set loki:password "<key>"` (`loki:key` also accepted), optional `set loki:tenant "<org id>"` |
| All | `set ox:logger:hostname "<name>"` (default `sv_projectName`, colour codes stripped) |

## 5. lib.class (shared)
```lua
local Animal = lib.class('Animal')

function Animal:constructor(name)
    self.name = name
    self.private.secret = 'hidden'      -- private: only readable inside class methods
end

function Animal:speak() return ('%s makes a sound'):format(self.name) end

local Dog = lib.class('Dog', Animal)

function Dog:constructor(name, breed)
    self:super(name)                    -- call the parent constructor (only valid inside the constructor)
    self.breed = breed
end

function Dog:speak() return ('%s barks (%s)'):format(self.name, self.private.secret) end

local rex = Dog:new('Rex', 'Husky')
print(rex:speak(), rex:instanceOf(Animal), rex:isClass(Dog))   -- ... true true
print(rex.private.secret)  -- nil outside class methods; writing to it from outside errors
```
- Use `:new(...)` to construct. `init` was removed in favour of `constructor` (v3.18).
- `private` fields are enforced by checking the calling function. Since v3.40, inherited methods can also read private fields.
- `instanceOf(class)` walks the inheritance chain. `isClass(class)` is an exact match.
- Many ox_lib modules are classes: array, map, set, lru, heap, ringbuffer, timer, dui, scaleform, selector, the entity classes, and the hook pipeline.

## 6. lib.array (shared)
```lua
local arr = lib.array:new(1, 2, 3)         -- or lib.array:from(tableOrIteratorOrString)
arr:push(4) ; arr:unshift(0) ; arr:pop() ; arr:shift()
arr:map(function(v, i) return v * 2 end) ; arr:filter(function(v) return v > 1 end)
arr:reduce(function(acc, v) return acc + v end, 0, reverse?)
arr:find(fn, last?) ; arr:findIndex(fn, last?) ; arr:indexOf(value, last?) ; arr:includes(value, fromIndex?)
arr:every(fn) ; arr:forEach(fn) ; arr:join(sep?) ; arr:slice(start?, finish?) ; arr:at(-1)
arr:fill(value, start?, endIndex?) ; arr:reverse() ; arr:toReversed() ; arr:merge(other, ...)
lib.array.isArray(tbl)                      -- array instance, array-like or empty table
-- static use on plain tables:
lib.array.reduce({ 1, 2, 3 }, function(acc, v) return acc + v end, 0)
```
Assigning a non-number key to an Array errors. Methods with a negative index (`at`, `slice`, `fill`) count from the end.

## 7. Collections (v3.38+) and DataView (v3.40)
| Class | Constructor | Methods |
|---|---|---|
| `lib.map` | `lib.map:new(initialTable?)` | `set(k, v)` (v must be non-nil), `get`, `has`, `delete`, `size`, `isEmpty`, `clear`, `entries()`, `keys()`, `values()`, `toTable()`, `toArray()`. **Insertion-ordered**; `pairs()` works; JSON and msgpack encode it as a table |
| `lib.set` | `lib.set:new(...)` | `add`, `remove`, `has`, `size`, `isEmpty`, `clear`, `each()`, `toArray()`, `union`, `intersection`, `difference`, `equals`, `isSubsetOf` |
| `lib.lru` | `lib.lru:new(capacity)` | `get` (marks as recent), `peek`, `set` (returns the evicted key/value), `has`, `delete`, `size`, `capacity`, `clear`, `each()` |
| `lib.heap` | `lib.heap:new(lessFn?)` (default min-heap `a < b`) | `push(...)`, `pop`, `peek`, `size`, `isEmpty`, `clear`, `drain()` (a sorted Array) |
| `lib.ringbuffer` | `lib.ringbuffer:new(capacity)` | `push` (returns the overwritten value), `get(i)` (1 = oldest, -1 = newest), `size`, `capacity`, `isFull`, `isEmpty`, `clear`, `each()`, `toArray()` |
| `Ox.DataView` | `local DataView = require 'Ox.DataView'; local dv = DataView:new(len)` | `get/set` + `Int8 Uint8 Int16 Uint16 Int32 Uint32 Int64 Uint64 Float32 Float64 LuaInt UluaInt LuaNum String`: `dv:setUint32(offset, value, bigEndian?)` / `dv:getUint32(offset?, bigEndian?)`; `dv.blob` holds the bytes (CfxLua `string.blob`). Mainly for native calls that take raw struct buffers. |

```lua
local recent = lib.lru:new(100)
recent:set(src, os.time())
local queue = lib.heap:new(function(a, b) return a.priority > b.priority end)   -- max-heap
queue:push({ priority = 5, job = 'a' }, { priority = 9, job = 'b' })
print(queue:pop().job) -- b
```
None of these collections has a docs page yet. The signatures above come from the v3.40.0 source.

## 8. lib.table / lib.math / lib.string (shared)
These modules **add functions to the global `table`, `math` and `string` libraries** of your resource. They only exist once the module has been loaded, either by touching `lib.table` (and so on) or with `ox_libs { 'table', 'math', 'string' }` in the manifest.
```lua
lib.table.contains(tbl, valueOrTable)   -- shallow; a table value means "contains all"
lib.table.matches(t1, t2)               -- deep equality
lib.table.deepclone(tbl)
lib.table.merge(t1, t2, addDuplicateNumbers = true)  -- mutates and returns t1; numbers are ADDED unless false
lib.table.shuffle(tbl)                  -- Fisher-Yates (v3.30)
lib.table.map(tbl, fn(value, key))      -- v3.32.5
table.freeze(tbl) ; table.isfrozen(tbl) -- read-only proxy (nested tables stay mutable)

math.round(value, places?) ; math.clamp(v, lo, hi) ; math.groupdigits(n, sep = ',')
math.tovector('1, 2, 3') ; math.toscalars('1 2 3', min?, max?, round?) ; math.torgba(...) ; math.hextorgb('#ff0000') ; math.tohex(n, upper?)
math.interp(a, b, factor) ; for v, step in math.lerp(a, b, durationMs) do ... end   -- per-frame iterator
math.normaltorotation(surfaceNormal)

string.random('1AA111')                 -- 1 digit, A upper, a lower, . alnum, ^x literal
string.random('AAA', 6)                 -- pattern padded or cut to 6 characters
string.capitalize(s) ; string.startsWith(s, p) ; string.endsWith(s, p) ; string.contains(s, v, plain = true)
string.isBlank(s) ; string.escapePattern(s) ; string.replace(s, search, repl, plain = true)   -- v3.39
```
Gotchas: `table.merge` **adds** numeric values with the same key unless `addDuplicateNumbers = false`. Use `string.random` for display codes like plates, and `lib.uuid` for identifiers. Neither uses a CSPRNG.

## 9. waitFor, intervals, timer (shared)
```lua
local ped = lib.waitFor(function()
    local p = NetToPed(netId)
    if DoesEntityExist(p) then return p end      -- return nil to keep waiting
end, 'ped did not exist in time', 5000)         -- timeout default 1000 ms; false = wait forever; THROWS on timeout
```
`SetInterval` and `ClearInterval` are globals defined by init.lua:
```lua
local id = SetInterval(function(a) print(a) end, 1000, 'tick')   -- args are passed through
SetInterval(id, 5000)       -- change the interval
ClearInterval(id)
```
Timer:
```lua
local t = lib.timer(60000, function(self) print('done') end, true)  -- third arg async=true runs it in its own thread
t:pause() ; t:play() ; t:isPaused() ; t:getTimeLeft('s')   -- 'ms'|'s'|'m'|'h', or a table with all four
t:restart(true) ; t:forceEnd(triggerOnEnd)
```
**Gotcha:** without `async = true`, `lib.timer(...)` **blocks the calling thread** until it ends.

## 10. lib.cron (server)
```lua
local task = lib.cron.new('0 */2 * * *', function(task, date)
    -- every 2 hours on the hour; `date` is os.date('*t')
end, { debug = false, maxDelay = 1 })
task:stop() ; task:run()          -- run() re-activates a stopped task
task:getNextTime() ; task:getAbsoluteNextTime() ; task:getTimeAsString(ts?)
```
- Format: `minute hour day month weekday`, with `*`, lists `1,2`, ranges `1-5`, steps `*/15`, month names (`jan`, … since v3.39 also a single name) and weekday names (`sun`…`sat`). The source maps weekday names to Lua's `os.date` numbering (sun = 1). **Use names** to avoid the 0-vs-1 Sunday ambiguity of numeric weekdays.
- Times are the **server's local time** (`os.time`).
- `maxDelay` (seconds, default 1). The annotation says "maximum allowed delay before skipping (0 to disable)", but in v3.40.0 the code **stops the task** (`isActive = false`) when the next run is more than `maxDelay` seconds overdue, and `0` makes any lateness stop it. After a long server hitch, check `task.isActive` or call `task:run()` again (observed in source).

## 11. uuid and selector (shared)
```lua
local id = lib.uuid.generate()      -- UUIDv7 string, time-ordered (v3.37); good DB primary key
lib.uuid.validate(id)               -- true only for v7 UUIDs

local loot = lib.selector:new({
    common = { { 70, 'bread' }, { 30, 'water' } },
    rare = { { 1, { item = 'goldbar', count = 1 } } },
})                                   -- or lib.selector:new({ { weight, value }, ... }) -> 'default' set
loot:getRandomWeighted('common') ; loot:getRandom('rare') ; loot:getRandomWeightedAmount('common', 3)
loot:getSet('common') ; loot:addSet(name, items) ; loot:updateSet(name, items) ; loot:removeSet(name) ; loot:getAllSets()
```
`selector` items are `{ weight, value }`. Table values are deep-cloned when they are returned. Zero-weight items are never picked (v3.33). For loot that matters to the economy, roll it on the server.

## 12. Server misc
```lua
local files, count = lib.getFilesInDirectory('data/jobs', '%.lua$')   -- relative to this resource's folder; uses io.readdir (v3.38)
lib.versionCheck('owner/repo')    -- compares fxmanifest `version` with the latest GitHub release; prints if outdated
local ok, msg = lib.checkDependency('ox_inventory', '2.40.0')          -- shared; true or false, message (printMessage=true prints instead)
GetActivePlayers()                -- server polyfill defined by init.lua (array of numeric server ids)
```

## 13. Common mistakes
- Forgetting `files { 'locales/*.json' }` (or the `locales_path` folder), so client `locale()` returns raw keys.
- Using `setr` for secrets (`datadog:key`, `fivemanage:key`, `loki:password`). `setr` replicates the convar to every client.
- Calling `table.deepclone` before `lib.table` was touched, which fails with "attempt to call a nil value". Reference `lib.table` once or add `ox_libs { 'table' }`.
- Expecting `require` to read files that aren't listed in the manifest on the client.
- Blocking a thread with a synchronous `lib.timer`, or not handling `lib.waitFor` timeouts (it throws).
- Running `lib.cron` logic on the client (it is server-only), or assuming UTC.
- Using numeric weekdays in cron expressions. Use `mon`…`sun`.

## 14. Sources
- https://github.com/overextended/ox_lib/blob/v3.40.0/imports/require/shared.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/modules/DataView/init.lua (commits b8f5a04 and 135e1b0 "support ox_lib modules v2")
- https://github.com/overextended/ox_lib/blob/v3.40.0/imports/locale/shared.lua, https://github.com/overextended/ox_lib/tree/v3.40.0/resource/locale, https://github.com/overextended/ox_lib/blob/v3.40.0/resource/settings.lua
- https://github.com/overextended/ox_lib/blob/v3.40.0/imports/print/shared.lua, https://github.com/overextended/ox_lib/tree/v3.40.0/imports/logger
- https://github.com/overextended/ox_lib/tree/v3.40.0/imports (class, array, map, set, lru, heap, ringbuffer, table, math, string, waitFor, timer, cron, uuid, selector, getFilesInDirectory)
- https://github.com/overextended/ox_lib/blob/v3.40.0/resource/version/server.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/resource/version/shared.lua, https://github.com/overextended/ox_lib/blob/v3.40.0/init.lua
- Docs: https://overextended.dev/docs/ox_lib/Logger/Server, https://overextended.dev/docs/ox_lib/Locale/Shared (and the Require, Print, Class, Array, Table, Math, String, Timer, Cron, WaitFor, Selector, Version pages; source: https://github.com/overextended/overextended.github.io/tree/main/content/docs/ox_lib)
- Release notes v3.29–v3.40: https://github.com/overextended/ox_lib/releases
