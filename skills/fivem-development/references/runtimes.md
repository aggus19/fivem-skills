# Scripting runtimes: CfxLua 5.4, JavaScript/TypeScript, C#

Baseline: FXServer Legacy 35245 (recommended) / citizenfx/fivem master `a74c2cc` · CfxLua = Lua **5.4.8** + LuaGLM · server JS = **Node 22** (Legacy) / Node 26 (Enhanced) · client JS = V8 12.4 · C# = Mono v1 (Legacy) / .NET 10 (Enhanced) — verified 2026-10-07.

## Contents
1. Runtime matrix
2. CfxLua extension cheat-sheet
3. Vectors, quaternions and matrices
4. Lua standard library per side
5. Scheduler: threads, Wait, promises
6. Events and `source` in the runtime
7. Exports (all runtimes)
8. Serialization: msgpack and json
9. Lua idioms and pitfalls
10. JavaScript / TypeScript
11. C#
12. Server sandbox (all runtimes)
13. Sources

## 1. Runtime matrix
| File | Runtime | Side | Notes |
|---|---|---|---|
| `*.lua` | CfxLua 5.4 (`citizen:scripting:lua`) | client + server | Lua 5.3 removed 2025-06; `lua54 'yes'` is deprecated/no-op. |
| `*.js` (server) | Node.js **22** (Legacy, `citizen-scripting-node`, `--fork-node22`) | server | Current source sends every server `.js` to Node 22; `node_version` is ignored. docs.fivem.net still says "16 default" (stale). Enhanced: Node 26. |
| `*.js` (client) | V8 12.4 (not Node) | client | No `require`, no `fs`, no DOM. FxDK uses an older V8 9.3. Enhanced: V8 14.6. |
| `*.net.dll` | Mono v1 (`CitizenFX.Core.Client/Server`) | both | `mono_rt2` pilot **expired 2026-06-30** (source refuses to load it). Enhanced uses **.NET 10**. |

All runtimes share the same event bus and exports (msgpack-serialized), so a Lua resource can call a JS export and vice versa.

## 2. CfxLua extension cheat-sheet
CfxLua = Lua 5.4.8 (`citizenfx/lua`, branch `luaglm-548`) compiled with these "power patches" (`code/vendor/lua.lua`):

| Feature (build flag) | Syntax | Equivalent / notes |
|---|---|---|
| Compound ops (`GRIT_POWER_COMPOUND`) | `n += 1` `-=` `*=` `/=` `<<=` `>>=` `&=` `\|=` `^=` | No `++`/`--`, no `//=`, no `%=`, no `..=`. |
| Safe navigation (`GRIT_POWER_SAFENAV`) | `local n = t?.a?.b` · `t?['k']` | Yields `nil` instead of erroring on a nil/undefined index. Not for method calls on nil objects. |
| `in` unpacking (`GRIT_POWER_INTABLE`) | `local x, y, z in coords` | `local x, y, z = coords.x, coords.y, coords.z` (by name). |
| Set constructor (`GRIT_POWER_TABINIT`) | `local allowed = { .police, .ems }` | `{ police = true, ems = true }`. |
| C comments (`GRIT_POWER_CCOMMENT`) | `/* block */` | |
| Compile-time hash (`GRIT_POWER_JOAAT`) | `` `adder` `` | joaat at parse time, **sign-extended** int32 (same as `GetHashKey`). Runtime: `joaat(str [, ignoreCase])`. Use `h & 0xFFFFFFFF` for unsigned. |
| `defer` (`GRIT_POWER_DEFER_OLD`) | `local _ <close> = defer(function() ... end)` | `defer` is a **function** (func2close) returning a to-be-closed object, **not** a `defer ... end` statement. |
| `each` / `__iter` (`GRIT_POWER_EACH`) | `for k, v in each(t) do` | Uses `__iter` metamethod (4 values incl. to-be-closed), else `__pairs`, else `next`. |
| `__ipairs` (`GRIT_COMPAT_IPAIRS`) | metamethod honoured again | |
| Extra table API (`GRIT_POWER_WOW`) | `table.create(narr, nrec)`, `table.wipe(t)`/`table.clear`, `table.clone(t)`, `table.type(t)` (`"empty"\|"array"\|"hash"\|"mixed"`), `table.new` | |
| Extra string API (`GRIT_POWER_WOW`) | `string.strsplit(delim, s[, n])`, `string.strtrim(s[, chars])`, `string.strjoin(delim, ...)`, `string.strconcat(...)`, `string.tostringall(...)`; `utf8.strlenutf8`, `utf8.strcmputf8i`; global `scrub(...)` | |
| Blobs (`GRIT_POWER_BLOB`) | `string.blob(n)`, `string.blob_pack`, `string.blob_unpack`, `string.isblob` | Mutable-ish byte buffers. |
| Timers (`GRIT_POWER_CHRONO`) | `os.nanotime()`, `os.microtime()`, `os.deltatime()`, `os.rdtsc()` | Only where `os` exists (server). |
| Lua 5.4 core | `local x <const> = 1`, `local f <close> = ...`, `//`, `& \| ~ << >>`, `math.tointeger`, `warn` | `LUA_COMPAT_5_3` is on. |

```lua
-- client/main.lua
local cfg <const> = { .bank, .shop }            -- set constructor
local model = `adder`                           -- compile-time hash
local x, y, z in GetEntityCoords(cache.ped)     -- `in` unpacking works on vectors too
local label = Config.Shops?[shopId]?.label or 'Shop'
local count = 0
count += 1
/* C-style block comment */
```
Tooling: StyLua ≥ 2.1 formats CfxLua (`syntax = "CfxLua"`), Lua Language Server needs the FiveM addon, **selene has no CfxLua parser** (`?.`, `/* */`, `in` unpacking, `{ .a }` fail; see `tooling.md`).

## 3. Vectors, quaternions and matrices
First-class value types (no allocation, **immutable**, components are **float32**):
```lua
local a = vector3(1.0, 2.0, 3.0)        -- aliases: vec3; vec(...) / vector(...) choose by arity (1 arg -> number)
local b = vec(4, 5, 6)
print(type(a), type(quat(1, 0, 0, 0))) -- "vector3"  "quat"   (vector2 / vector4 too)
local d = #(a - b)                      -- # = magnitude (distance)
local s = a.xy                          -- swizzle -> vector2; a.zyx, a.xyzx...
local n = a.n                           -- dimension (3)
local key = a // 1.0                    -- floor each component; vectors can be table keys
local q = quat(90.0, vec3(0, 0, 1))     -- angle (degrees) + axis; or quat(w, x, y, z)
local rotated = q * vec3(1, 0, 0)
```
Global helpers (docs: Lua functions): `norm(v|q)`, `dot(a, b)`, `cross(a, b)` (vec3×vec3 → vec3; vec2×vec2 → number; quat variants), `inv(q)`, `slerp(a, b, t)`. Matrices: `mat3`, `mat4`, `mat(...)` (column-major, mutable). Full GLM binding: `local glm = require 'glm'` (built-in module; `glm.rotate`, `glm.perspective`, `glm.ray.intersectAABB`, ...).
- Fields: `x y z w`, `r g b a`, `1 2 3 4`; quats also `angle`, `axis`. Assigning `v.x = 1` errors — build a new vector.
- Natives accept vectors where they take `x, y, z` (auto-unpack) **unless** the resource uses `use_experimental_fxv2_oal`.
- Precision: float32 → don't use vectors to store money/IDs; `vec3(0.1, 0, 0).x ~= 0.1`.

## 4. Lua standard library per side
| Library | Client | Server | Notes |
|---|---|---|---|
| base, `table`, `string`, `math`, `coroutine`, `utf8` | yes | yes | + CfxLua extras above. `load` allowed. Prefer `LoadResourceFile` + `load` over `dofile`/`loadfile` (their path handling in the sandbox is **UNVERIFIED**). |
| `debug` | yes | yes | Partial (`LUA_SANDBOX` strips many functions); `debug.traceback`, `debug.getinfo` work. |
| `io` | **nil** | sandboxed | `io.open(path, mode)` (`@res/file` or absolute inside resource folders), `io.readdir(path)`, `io.lines`, `io.write`, `io.type`, `io.close`; `io.popen` only emulates `dir "..."` / `ls "..."`; `io.tmpfile` blocked; no `io.read`/`io.input`/`io.output`. |
| `os` | **nil** | sandboxed | `os.time/date/clock/difftime`, `os.remove/rename/createdir` (own resource only), `os.nanotime/microtime/deltatime/rdtsc/rdtscp`; `os.execute` → `nil, "Permission denied", 13`; `os.getenv('os')` → `"Windows"`/`"Linux"`, everything else `nil`; `os.setlocale` read-only. |
| `package`, `require` | `require` only | `require` only | No `package` lib. Built-in `require` knows only `'glm'` and `'lmprof'`; ox_lib replaces `require` with a resource-file loader (`require 'module.path'`, `@res.path`). |
| `msgpack`, `json` | yes | yes | lua-cmsgpack / lua-rapidjson (see §8). |
| `Citizen`, `promise`, `exports`, `GlobalState`, `LocalPlayer` (client), `Entity()`, `Player()` | yes | yes | From `scheduler.lua` / `deferred.lua`. |

Client wall-clock: `GetCloudTimeAsInt()` (UTC seconds) or `GetLocalTime`; server: `os.time()`. Timers both sides: `GetGameTimer()` (ms).

## 5. Scheduler: threads, Wait, promises
| Function | Meaning |
|---|---|
| `CreateThread(fn)` / `Citizen.CreateThread` | New coroutine, starts next tick. |
| `Citizen.CreateThreadNow(fn, name?)` | Runs immediately until its first yield (event handlers use this). |
| `Wait(ms)` / `Citizen.Wait` | Yield current coroutine; `Wait(0)` = next frame. |
| `SetTimeout(ms, fn)` → id, `ClearTimeout(id)` | One-shot timer. |
| `promise.new()`, `p:resolve(v)`, `p:reject(e)`, `p:next(ok, err)`, `promise.all(list)`, `promise.first(list)`, `promise.map(list, fn)` | Deferred lib (global `promise`). |
| `Citizen.Await(p)` | Yield until `p` settles; rethrows on reject. Must be inside a coroutine. |
| `PerformHttpRequestAwait(url, method?, data?, headers?, options?)` | Server, build ≥ 9515. |
| `Citizen.Trace(str)`, `print(...)` | Console output. |

Rules:
- File scope runs in a coroutine-less context: `Wait`/`Citizen.Await` at top level errors ("Current execution context is not in the scheduler"). Wrap in `CreateThread`.
- Event, command, NUI-callback and export-handler bodies already run inside a coroutine (`CreateThreadNow`), so `Wait`, `MySQL.*.await`, `lib.callback.await` work there.
- One script error kills only that coroutine; a `while true do` loop without `Wait` freezes the whole resource (and the client).
```lua
-- server/main.lua
local function fetchJson(url)
    local p = promise.new()
    PerformHttpRequest(url, function(status, body)
        if status == 200 then p:resolve(json.decode(body)) else p:reject(('HTTP %s'):format(status)) end
    end, 'GET')
    return Citizen.Await(p)
end

CreateThread(function()
    local ok, data = pcall(fetchJson, 'https://example.com/data.json')
    if ok then print(data.version) end
end)
```

## 6. Events and `source` in the runtime
- `source` is a **global** set while a handler runs and restored afterwards; after any `Wait`/await it may point to another event. Capture it first: `local src = source`.
- Net events are rejected ("was not safe for net") unless registered with `RegisterNetEvent` (Lua/JS) / `[EventHandler]` (C#, all are net-safe).
- Server: for net events `source` = player server id (number); for server-internal events (`playerDropped`, `playerJoining`) it is also the player id.
- Full event API and built-in event list: `events-and-callbacks.md`.

## 7. Exports (all runtimes)
```lua
-- provider resource 'myres' (server or client; exports are per side)
exports('getStock', function(shopId) return Stock[shopId] end)
-- consumer
local stock = exports.myres:getStock('shop_1')          -- colon call: first arg (self) is dropped
local s2 = exports['my-res']:getStock('shop_1')          -- bracket syntax for names with '-'
```
Internals (scheduler.lua / main.js): `exports(name, fn)` registers handler for local event `__cfx_export_<resource>_<name>`; the consumer resolves it once via `TriggerEvent` and caches the function reference; manifest `export` / `server_export` entries export globals of the same name. Consequences:
- Synchronous call, but arguments/returns are **msgpack-copied** (tables are copies, functions become refs). Don't pass huge tables per frame.
- Errors: "No such export X in resource Y" if the resource is stopped/not started yet or the name is wrong. Guard with `GetResourceState('myres') == 'started'` or `dependency 'myres'`.
- The cache lives in the consumer and is cleared when the provider stops (`onClientResourceStop`/`onServerResourceStop`, Lua and JS), so refs refresh after a restart. Errors inside an export are rethrown in the caller as "An error occurred while calling export ...".
- Inside an export, `GetInvokingResource()` returns the caller's name: use it to allow-list callers of privileged exports.
- JS alias: `exports.txAdmin` resolves to `monitor`.

## 8. Serialization: msgpack and json
- Events, exports, state bags and function refs use **MessagePack**. Lua config set by `scheduler.lua`: integers packed `unsigned` where possible, arrays `without_hole` (a sparse array becomes a map with integer keys), empty table → empty **array**.
- Lua vectors/quats are msgpack **extension types** — they survive Lua ↔ Lua (and C#) events. JS has no unpacker for them: send `{ x, y, z }` tables across Lua ↔ JS. (**UNVERIFIED**: exact JS-side shape of a received Lua vector.)
- Functions are sent as function references (callable across resources); entity/Player objects in JS have their own ext (41/42).
- `json` = lua-rapidjson: `json.encode(value[, opts])`, `json.decode(str)`, `json.null`. Defaults set by runtime: `empty_table_as_array = true` (`{}` → `[]`), `with_hole = true` (sparse arrays get `null`). Pretty print: `json.encode(t, { indent = true })` (option name present in source; formatting details **UNVERIFIED**).
- NaN/inf are not valid JSON; integer-valued floats may round-trip as integers.

## 9. Lua idioms and pitfalls
- `local` everything; globals are shared by all files of the same side of the resource.
- `#t` is undefined for sparse tables/maps; keep a counter or use `table.type`.
- `tonumber()` all external numbers; reject `n ~= n` (NaN), `math.huge`, non-integers where IDs are expected (`math.type(n) == 'integer'`).
- `('%d'):format(1.5)` errors; `1 == 1.0` is true but `math.type` differs.
- String building in loops: collect parts in a table and `table.concat`.
- Avoid closures/tables created every frame in `Wait(0)` loops (GC churn shows in `resmon`).
- `Citizen.*` prefixes are optional (`CreateThread`, `Wait`, `SetTimeout` are aliases).

## 10. JavaScript / TypeScript
JS globals (from `citizen/scripting/v8/main.js`, `timer.js`):

| Global | Side | Meaning |
|---|---|---|
| `on(name, cb)` / `addEventListener` | both | Local + internal events (not network-safe). |
| `onNet(name, cb)` / `addNetEventListener` | both | Network-safe handler. `RegisterNetEvent` also exists. |
| `emit(name, ...args)` | both | Local event (`TriggerEvent`). |
| `emitNet(name, ...args)` (client) / `emitNet(name, target, ...args)` (server) | both | Network event; target `-1` = everyone. `TriggerClientEvent`/`TriggerServerEvent`/`TriggerLatent*` aliases exist. |
| `removeEventListener(name, cb)`, `addRawEventListener(name, cb)` | both | Raw = receives undecoded msgpack payload. |
| `setTick(fn)` → id, `clearTick(id)` | both | Per-frame callback (can be `async`). |
| `setTimeout/setInterval/setImmediate` + `clear*`, `requestAnimationFrame` | both | Overridden to run on the game thread. |
| `exports(name, fn)`, `exports.res.fn(...)` | both | No colon/`self` in JS. |
| `source` (`global.source`) | both | Set during handler; `const src = source;` first. |
| `getPlayers()`, `getPlayerIdentifiers(p)`, `getPlayerTokens(p)` | server | String ids. |
| `GlobalState`, `Entity(handle).state`, `Player(src).state`, `LocalPlayer` (client), `NewStateBag` | both | State bags. |
| `SendNUIMessage(obj)`, `RegisterNuiCallback(name, (data, cb) => {})` | client | NUI. |
| `Citizen.invokeNative`, `Citizen.pointerValue*`, `Citizen.resultAs*` | both | Raw native calls. |
| `msgpack_pack/unpack`, `printError`, `console` | both | |

```ts
// src/server/main.ts  (bundled to dist/server.js, platform node)
onNet('myres:server:hello', (msg: unknown) => {
  const src = source;                                   // capture immediately
  if (typeof msg !== 'string' || msg.length > 64) return;
  emitNet('myres:client:hello', src, `hi ${GetPlayerName(String(src))}`);
});
exports('ping', () => 'pong');

// src/client/main.ts
const tick = setTick(async () => {
  // per frame; prefer setInterval for low-frequency logic
});
on('onResourceStop', (res: string) => { if (res === GetCurrentResourceName()) clearTick(tick); });
```
- Node thread affinity (server): callbacks from Node APIs (fs, sockets, timers of npm libs) run on the libuv thread; call natives only after `setImmediate(() => ...)`.
- `child_process`/`worker_threads` need `add_unsafe_child_process_permission` / `add_unsafe_worker_permission` in `server.cfg`.
- Natives use numbers/strings; vectors come back as `[x, y, z]` arrays; hashes via `GetHashKey`.
- Typings: `@citizenfx/client` / `@citizenfx/server` **2.0.35805-1** (declare `source`, `exports: CitizenExports`, natives). Extend export typings with `declare global { interface CitizenExports { myres: { getStock(id: string): number } } }`.
- Wrappers: `@nativewrappers/fivem` / `@nativewrappers/server` 0.0.174 (`@nativewrappers/client` deprecated). ox_lib for JS: `@overextended/ox_lib` 3.40.0 (`/client`, `/server`, `/shared`).
- Bundling recipes (esbuild 0.28, rolldown 1.2, tsup 8.5): `tooling.md` §5.

## 11. C#
- Legacy: Mono runtime, NuGet **`CitizenFX.Core.Client`** / **`CitizenFX.Core.Server`** `1.0.26803` (2026-03-11). Output file must end in `.net.dll` and be listed in `client_script`/`server_script`. Template: `dotnet new install CitizenFX.Templates` → `dotnet new cfx-resource`.
- Old "v2" runtime (`mono_rt2 'Prerelease expiring ...'`): expired **2026-06-30**; current builds print "mono_rt2 is no longer supported" and skip the file. Remove the directive.
- Enhanced (Cfx Server): Mono replaced by **.NET 10** (needs .NET 10 SDK); Cfx.re says details will follow — API compatibility specifics **UNVERIFIED**.
- v1 API: inherit `BaseScript`; attributes `[EventHandler("name")]`, `[Tick]`, `[Command("name")]`, `[FromSource] Player player`; dictionaries `EventHandlers["name"] += new Action<...>(...)`, `Exports.Add("name", fn)` / `Exports["res"].fn(...)`; `await Delay(ms)`; `TriggerServerEvent`, `TriggerClientEvent(player, ...)`, `Players`, `API.*` natives.
```csharp
// Server: MyRes.Server.net.dll
using System;
using CitizenFX.Core;
using static CitizenFX.Core.Native.API;

public class Main : BaseScript
{
    [EventHandler("myres:server:hello")]
    private void OnHello([FromSource] Player player, string msg)
    {
        if (msg == null || msg.Length > 64) return;
        player.TriggerEvent("myres:client:hello", $"hi {player.Name}");
    }

    // Supported signatures: (), (string[] args), (Player p) and (Player p, string[] args) - Player only on the server
    [Command("ping", Restricted = true)]
    private void Ping(Player player, string[] args) => Debug.WriteLine($"pong from {player.Name}");
}
```
- `clr_disable_task_scheduler` is implied by `fx_version 'bodacious'`+: after `await` of non-Citizen tasks, `await Delay(0)` to get back to the main thread before calling natives.
- Use C# only when the team already knows it; ox_lib and frameworks are Lua-first.

## 12. Server sandbox (all runtimes)
- File I/O (Lua `io`, `SaveResourceFile`, Node `fs` where hooked): write only inside the **same** resource; other resources, server root and paths outside resource folders are blocked (`EACCES`/13); `..` traversal and symlinks rejected. Grant with `add_filesystem_permission resA write resB`.
- `os.execute` always denied; `io.popen` only emulated `dir`/`ls`.
- Convars: once `add_convar_permission res read convar` is set for a convar, only listed resources can read it.
- Node: `add_unsafe_worker_permission res`, `add_unsafe_child_process_permission res`.
- Docs: https://docs.fivem.net/docs/developers/sandbox/

## 13. Sources
- https://docs.fivem.net/docs/scripting-manual/runtimes/lua/ · https://docs.fivem.net/docs/scripting-manual/runtimes/javascript/ · https://docs.fivem.net/docs/scripting-manual/runtimes/csharp/
- https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/norm/ (and `dot`, `cross`, `inv`, `slerp`, `quat`, `vector`, `PerformHttpRequestAwait` pages)
- https://docs.fivem.net/docs/developers/sandbox/ · https://docs.fivem.net/docs/developers/legacy-vs-enhanced/ · https://docs.fivem.net/docs/developers/script-runtimes/
- https://github.com/citizenfx/fivem — `code/vendor/lua.lua` (power-patch flags), `code/components/citizen-scripting-lua/src/{LuaScriptRuntime,LuaIO,LuaOS}.cpp`, `data/shared/citizen/scripting/lua/{scheduler,deferred}.lua`, `data/shared/citizen/scripting/v8/{main,timer}.js`, `code/components/citizen-scripting-node/src/NodeScriptRuntime.cpp`, `code/components/citizen-scripting-v8/src/V8ScriptRuntime.cpp`, `code/components/citizen-scripting-mono-v2/src/MonoScriptRuntime.cpp`
- https://github.com/citizenfx/lua/tree/luaglm-548 (README power patches, `lbaselib.c`, `ltablib.c`, `lstrlib.c`) · https://github.com/citizenfx/lua-rapidjson (grit) · https://github.com/citizenfx/lua-cmsgpack (grit)
- https://www.npmjs.com/package/@citizenfx/server · https://www.nuget.org/packages/CitizenFX.Core.Server
