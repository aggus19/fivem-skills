# ox_lib — JS/TS package `@overextended/ox_lib`

Baseline: ox_lib v3.40.0 — verified 2026-10-07 (npm `@overextended/ox_lib` 3.40.0)

Part of the ox_lib reference. Entry point and index: [ox-lib.md](ox-lib.md).

## Contents
1. Install and entry points
2. Breaking changes in the package (2026)
3. What is exported where
4. Callbacks, commands, cache
5. Zones (experimental)
6. Locales
7. Gotchas observed in the v3.40.0 source
8. Sources

---

## 1. Install and entry points
```bash
npm install @overextended/ox_lib     # or bun add / pnpm add
```
The **ox_lib resource must still be installed and started**. Most wrappers just call `exports.ox_lib.*`. The package is ESM only (`"type": "module"`), built with tsdown. Its dependencies are `@overextended/core` (^0.2.5, for vectors, grid and geometry), `fast-printf` and `csstype`. It no longer depends on `@nativewrappers/*` (dropped in v3.35).

| Import path | Resolves to | Use from |
|---|---|---|
| `@overextended/ox_lib` | `dist/common/index.js` | shared code (client or server) |
| `@overextended/ox_lib/<module>` | `dist/common/<module>/index.js`, e.g. `/hooks`, `/zones`, `/locale`, `/uuid`, `/cache` | shared |
| `@overextended/ox_lib/client` | `dist/client/index.js` (re-exports common) | client scripts |
| `@overextended/ox_lib/client/<module>` | e.g. `/client/interface`, `/client/callback`, `/client/streaming` | client |
| `@overextended/ox_lib/server` | `dist/server/index.js` (re-exports common) | server scripts |
| `@overextended/ox_lib/server/<module>` | e.g. `/server/addCommand`, `/server/acl` | server |

```ts
// client.ts
import { lib, notify, inputDialog, triggerServerCallback, cache, onCache } from '@overextended/ox_lib/client';

onCache('vehicle', (vehicle, old) => { if (vehicle) notify({ title: 'In vehicle', type: 'inform' }); });

const input = await inputDialog('Amount', [{ type: 'number', label: 'Amount', min: 1, required: true }]);
const stock = await triggerServerCallback<number>('myres:getStock', null, 'shop_1');
lib.notify({ description: `Stock: ${stock}` });   // the namespace export `lib` holds every export
```

## 2. Breaking changes in the package (2026)
| Version | Change | What to do |
|---|---|---|
| **v3.33.1** (2026-05-14) | Module paths reorganised (`shared/` → `common/`, `client/resource/*` → `client/*`). The **default export was removed**. | Replace `import lib from '@overextended/ox_lib/client'` with `import { lib } from '…/client'` or named imports. Replace imports from `…/shared` with the package root `@overextended/ox_lib`. Note that the docs site and README still show `import lib from …`, which is stale. |
| v3.33.0 | Added the `zones` module (experimental) | Section 5 |
| v3.34.0 | Added a `StateBag` class (no longer exported in v3.40.0; its state methods live on `GameEntity`), game entity classes (`Ped`, `Player`, `Prop`, `Vehicle`, `createPed/createObject/createVehicle`) and hooks (`HookPipeline`, `registerHook`) | |
| **v3.35.0** (2026-05-24) | Dropped `@nativewrappers/*`, compiled with tsdown, adjusted barrel exports | Remove any reliance on types that used to be re-exported from nativewrappers. Install `@nativewrappers/fivem` yourself if you need it. |
| v3.36.0 | `addCommand` param field renamed `paramType` → **`type`** (the old `argType` key is still mapped) | Use `type` |
| v3.39.0 | zones: more parity with Lua; a `remove()` method added | |

## 3. What is exported where
**common** (`@overextended/ox_lib`): `cache`, `onCache`, `GameEntity`, `Ped`, `Player`, `Prop`, `Vehicle`, `getNearbyVehicles`, `HookPipeline`, `registerHook`, `locale`, `getLocales`, `getLocale`, `initLocale` (deprecated), `createLocales`, `checkDependency`, `Zone`, `uuid`, `context`, `sleep`, `waitFor`, `getRandomInt`, `getRandomChar`, `getRandomAlphanumeric`, `getRandomString`, and the types `VehicleProperties` and `FlattenObjectKeys`.

**client** (everything in common, plus):
- Interface: `notify`, `defaultNotify`, `showTextUI`, `hideTextUI`, `isTextUIOpen`, `progressBar`, `progressCircle`, `progressActive`, `cancelProgress`, `skillCheck`, `skillCheckActive`, `cancelSkillCheck`, `registerContext`, `showContext`, `hideContext`, `getOpenContextMenu`, `registerMenu`, `showMenu`, `hideMenu`, `getOpenMenu`, `setMenuOptions`, `inputDialog`, `closeInputDialog`, `alertDialog`, `closeAlertDialog`, `addRadialItem`, `removeRadialItem`, `registerRadial`, `showRadialMenu`, `hideRadial`, `disableRadial`, `getCurrentRadialId`, `setClipboard`.
- Other: `addKeybind`, `getKeybind`, `getAllKeybinds`, `triggerServerCallback`, `onServerCallback`, `Dui`, `Point`, `requestModel`, `requestAnimDict`, `requestAnimSet`, `requestNamedPtfxAsset`, `requestScaleformMovie`, `requestStreamedTextureDict`, `requestWeaponAsset`, `getVehicleProperties`, `setVehicleProperties`, and client `createPed/createObject/createVehicle`.

**server** (everything in common, plus): `addAce`, `removeAce`, `addPrincipal`, `removePrincipal`, `addCommand`, `triggerClientCallback`, `onClientCallback`, `getServerLocale`, `versionCheck`, `setVehicleProperties`, and server `createPed/createObject/createVehicle(model, type, x, y, z, heading)`.

**Not in JS** (Lua only): `lib.zones` sphere/box/poly constructors (JS has its own `Zone` API), `lib.points` helpers beyond `Point`, `lib.callback.await` (JS returns Promises instead), `lib.logger`, `lib.cron`, `lib.class`, `lib.array`, the collections, `lib.timer`, `lib.raycast`, `lib.marker`, `lib.scaleform`, `lib.getClosest*` (only `getNearbyVehicles` is wrapped), `lib.triggerClientEvent`, `lib.require`, and `Ox.DataView`.

## 4. Callbacks, commands, cache
```ts
// server.ts
import { onClientCallback, triggerClientCallback, addCommand } from '@overextended/ox_lib/server';

onClientCallback('myres:getStock', (playerId, shopId: string) => {
  if (typeof shopId !== 'string') return null;
  return Shops[shopId]?.stock ?? 0;
});

const answer = await triggerClientCallback<boolean>('myres:confirm', playerId, 'Pay $500?');

addCommand<{ target: number; amount: number }>(
  'givecash',
  async (source, args) => { /* validate args.amount, then act */ },   // the handler MUST be async (it calls .catch)
  { help: 'Give cash', restricted: 'group.admin',
    params: [ { name: 'target', type: 'playerId' }, { name: 'amount', type: 'number' } ] },
);
```
- **The argument order differs from Lua.** JS is `addCommand(name, handler, properties)`, while Lua is `lib.addCommand(name, properties, handler)`.
- Client `triggerServerCallback(name, delay | null, ...args)` returns a `Promise`, or `undefined` when rate-limited by `delay`. It rejects on timeout (`ox:callbackTimeout`, default 300000 ms) and when the callback doesn't exist.
- Errors thrown inside `onServerCallback`/`onClientCallback` handlers are logged, and the caller receives `undefined`.
- `cache` is a Proxy with the same keys as Lua (`ped`, `vehicle`, `seat`, `weapon`, `playerId`, `serverId`, `resource`, `game`). `onCache(key, (value, oldValue) => {})` works the same way.

## 5. Zones (experimental)
Importing the module prints "The ox_lib zones module is experimental and may change in future versions." The shapes come from `@overextended/core/geometry` (0.2.x):
```ts
import { Zone } from '@overextended/ox_lib/zones';
import { Vector2, Vector3 } from '@overextended/core/vector';

const sphere = Zone.Sphere(new Vector3(441.0, -982.0, 30.7), 2.0);                 // (coords, radius)
const box = Zone.Cuboid(new Vector3(0, 0, 70), 4, 6, 3, 45);                      // (origin, width, depth, height, heading?)
const prism = Zone.Prism([new Vector2(10, 10), new Vector2(20, 10), new Vector2(20, 25)], 4, 28);  // (vertices, height, z)

box.onEnter = () => console.log('enter');
box.onExit = () => console.log('exit');
box.inside = () => {};          // every frame while inside
box.shouldDraw = true;          // debug drawing
box.contains(new Vector3(0, 0, 70));
box.remove();                   // or Zone.delete(box.id)
Zone.getAll(); Zone.getCurrent(); Zone.getNearby(point?); Zone.has(id);
```
- Polling runs every 300 ms on the client. One `setTick` runs **every frame for as long as the module is imported**, iterating over nearby and inside zones, so don't import it into resources that don't need zones.
- On the server there is no polling. Use `contains`.
- `@overextended/core` 0.3.x exists, but the package range `^0.2.5` keeps 0.2.x. Constructor signatures were checked against 0.2.5 typings.

## 6. Locales
```ts
import { locale, createLocales } from '@overextended/ox_lib';
// locales are loaded on import (package sideEffects); same JSON layout and fallback rules as Lua
const t = createLocales<typeof import('../locales/en.json')>();  // typed keys (v3.35)
t('shop.bought', 2, 'bread');
```

## 7. Gotchas observed in the v3.40.0 source
- `server/acl` **`removeAce` calls `exports.ox_lib.addAce`** (a copy-paste bug), so it adds the ACE instead of removing it. Call `exports.ox_lib.removeAce(principal, ace, allow)` directly (observed in `package/server/acl/index.ts`).
- `getServerLocale()` calls `exports.ox_lib.getServerLocale`, but the Lua resource doesn't define that export in v3.40.0. Use `exports.ox_lib.getLocaleKey()` or `GetConvar('ox:locale', 'en')` (**UNVERIFIED** at runtime).
- `uuid.generate()` in JS builds the timestamp bytes with 32-bit `>>` shifts on a 48-bit millisecond value, so the time prefix is not a correct UUIDv7 timestamp, and lexical order may not follow creation time. `validate()` still accepts the result. Generate IDs in Lua (or the database) when ordering matters (observed in source, **UNVERIFIED** at runtime).
- Promise-returning UI functions (`progressBar`, `inputDialog`, `alertDialog`, `skillCheck`) must be awaited inside an `async` function.

## 8. Sources
- https://github.com/overextended/ox_lib/tree/v3.40.0/package (package.json, README.md, tsdown.config.ts, client/, server/, common/)
- https://registry.npmjs.org/@overextended/ox_lib/latest (3.40.0)
- https://unpkg.com/@overextended/core@0.2.5/dist/geometry.d.ts and https://registry.npmjs.org/@overextended/core
- Commits: 4f23f6c "refactor(package): adjust module paths and exports" (v3.33.1), 2c110f0 "adjust barrel exports" (v3.35.0)
- Release notes: https://github.com/overextended/ox_lib/releases
- Docs: https://overextended.dev/docs/ox_lib (JS tabs; still shows the old default import)
