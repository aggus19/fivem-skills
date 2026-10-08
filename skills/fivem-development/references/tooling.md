# Tooling: editor, linting, formatting, TypeScript, bundling, CI, debugging

Baseline (npm / GitHub releases, verified 2026-10-07): Lua Language Server 3.19.1 · fivem-lls-addon (overextended, main 2026-07) · selene 0.32.0 · StyLua 2.5.2 · TypeScript 7.0.2 · esbuild 0.28.2 · rolldown 1.2.13 · tsup 8.5.1 (unmaintained) / tsdown 0.23.0 · @citizenfx/client|server 2.0.35805-1 · @nativewrappers/fivem 0.0.174 · @overextended/ox_lib 3.40.0 · @types/node 26.6.4.

## Contents
1. Lua Language Server + FiveM addon
2. Formatting with StyLua (CfxLua syntax)
3. Linting with selene
4. TypeScript resources (tsconfig per side)
5. Bundling recipes (esbuild, rolldown, tsup/tsdown)
6. NUI tooling
7. CI (GitHub Actions)
8. Debugging and profiling tools
9. Skill scripts
10. Sources

## 1. Lua Language Server + FiveM addon
- Editor: VS Code with **`sumneko.lua`** (LuaLS 3.19.1), or Zed/Neovim with lua-language-server.
- Types/natives/CfxLua syntax: **https://github.com/overextended/fivem-lls-addon** (MIT). Its `config.json` sets `Lua 5.4`, `nonstandardSymbol` (`/**/`, `` ` ``, `+=` ... `^=`), ignores `web`/`node_modules`; its `plugin.lua` hides `?.`/`?[` safe-navigation errors and FXAP (escrowed) files.
- The VS Code extension **`overextended.cfxlua-vscode` is discontinued** (README: use fivem-lls-addon instead); `communityox.cfxlua-vscode-cox` is archived. The LuaLS Addon Manager entry "FiveM" points to a different fork (`tf-framework/fivem-lls-addon`), not overextended.
- Setup:
```sh
mkdir -p ~/lua-addons && cd ~/lua-addons
git clone https://github.com/overextended/fivem-lls-addon.git
```
Then `.luarc.json` in the workspace (template: `assets/configs/.luarc.json`; edit the paths):
```json
{
  "$schema": "https://raw.githubusercontent.com/LuaLS/vscode-lua/master/setting/schema.json",
  "workspace.checkThirdParty": "Ask",
  "workspace.userThirdParty": ["C:/dev/lua-addons"],
  "workspace.library": ["C:/dev/fxserver/server-data/resources/[ox]/ox_lib"]
}
```
`userThirdParty` = folder **containing** `fivem-lls-addon`; when LuaLS detects `fxmanifest.lua` it asks to apply the CfxLua addon ("Ask"). `workspace.library` gives completion for ox_lib (`lib.*`) and frameworks if their source is on disk. Commit a `.luarc.default.json` and gitignore personal paths.

## 2. Formatting with StyLua (CfxLua syntax)
- https://github.com/JohnnyMorganz/StyLua — v2.5.2. Release binaries include the `cfxlua` feature; **`syntax = "CfxLua"`** (added in 2.1.0) parses compound ops, `?.`, backtick hashes, `in` unpacking, set constructors and `/* */`.
- Config `assets/configs/.stylua.toml` (4 spaces, 120 cols, `AutoPreferSingle`, `syntax = "CfxLua"`). Run `stylua .` / check `stylua --check .`.
- `cargo install stylua --features cfxlua` if building from source.

## 3. Linting with selene
- https://github.com/Kampfkarren/selene — v0.32.0. Parser features: Lua 5.2–5.4, LuaJIT, Roblox/Luau — **no CfxLua**. `?.`, `/* */`, `in` unpacking and `{ .a }` set syntax fail to parse; backtick hashes parse as Luau interpolated strings and compound ops as Luau compound assignment (works by accident, behaviour **UNVERIFIED** per version). Exclude files that use CfxLua-only syntax or avoid it in linted code.
- This skill ships `assets/configs/selene.toml` + `assets/configs/cfx.yml` (std `cfx` based on `lua54`, runtime globals). Natives are thousands of globals → `undefined_variable = "allow"`; verify natives with `python scripts/natives.py check --strict` instead.
- Run `selene .` in the resource directory.

## 4. TypeScript resources (tsconfig per side)
- TypeScript **7.0** (`typescript@7`, native Go compiler; `tsc` CLI unchanged). If a tool/plugin breaks on 7, pin `typescript@~6.0` (the React boilerplate still uses `~6.0.3`).
- Client and server typings declare different natives with the same names → **separate tsconfig per side**:
```jsonc
// tsconfig.server.json
{
  "compilerOptions": {
    "target": "ES2023", "module": "ESNext", "moduleResolution": "bundler",
    "strict": true, "noEmit": true, "skipLibCheck": true, "isolatedModules": true,
    "types": ["@citizenfx/server", "@types/node"]
  },
  "include": ["src/server", "src/shared"]
}
// tsconfig.client.json: same, but "types": ["@citizenfx/client"], "lib": ["ES2023"] (no DOM), include src/client + src/shared
```
- Packages: `npm i -D typescript @citizenfx/client @citizenfx/server @types/node esbuild`; optional `@nativewrappers/fivem` (client) / `@nativewrappers/server`, `@overextended/ox_lib` (needs ox_lib started; import from `@overextended/ox_lib/client|server|shared`).
- Script templates: `overextended/fivem-typescript-boilerplate` (pushed 2026-05).

## 5. Bundling recipes
Output one file per side and reference it from the manifest:
```lua
client_script 'dist/client.js'
server_script 'dist/server.js'
```
Targets: server = Node 22 on Legacy (`node22`, CommonJS, `require` of Node built-ins allowed); client = V8 12.4, **not Node** (`es2023`, IIFE, no Node built-ins). Ship `dist/`; servers don't run npm (Node packages used at runtime must be bundled or present in the resource's `node_modules`).

**esbuild 0.28** (`build.mjs`, run `node build.mjs` / `node build.mjs --watch`):
```js
import { context, build } from 'esbuild';

const watch = process.argv.includes('--watch');
const configs = [
  { entryPoints: ['src/server/index.ts'], outfile: 'dist/server.js', platform: 'node', target: 'node22', format: 'cjs' },
  { entryPoints: ['src/client/index.ts'], outfile: 'dist/client.js', platform: 'browser', target: 'es2023', format: 'iife' },
].map((c) => ({ ...c, bundle: true, logLevel: 'info', legalComments: 'none' }));

if (watch) {
  for (const c of configs) await (await context(c)).watch();
} else {
  await Promise.all(configs.map((c) => build(c)));
}
```
**rolldown 1.2** (`rolldown.config.mjs`, run `npx rolldown -c` / `-w`):
```js
import { defineConfig } from 'rolldown';

export default defineConfig([
  {
    input: 'src/server/index.ts',
    platform: 'node',
    transform: { target: 'node22' },
    output: { file: 'dist/server.js', format: 'cjs' },
  },
  {
    input: 'src/client/index.ts',
    platform: 'browser',
    transform: { target: 'es2023' },
    output: { file: 'dist/client.js', format: 'iife' },
  },
]);
```
**tsup 8.5** works (`tsup src/server/index.ts --format cjs --target node22 --platform node -d dist`) but its README says it is **no longer actively maintained** → for new projects use **tsdown 0.23** (rolldown-based, needs Node ≥ 22.18) or plain esbuild/rolldown.

## 6. NUI tooling
- Vite 8.3 + `@vitejs/plugin-react` 6.1 (React 19.3) / `@vitejs/plugin-vue` 6.0 (Vue 3.5) / `@sveltejs/vite-plugin-svelte` 7.3 (Svelte 5.57). Node `^20.19 || >=22.12`.
- Always `base: './'`, `build.target`/`cssTarget: 'chrome103'` (see `nui.md` §2 for the API table). Tailwind: v3.4.19 for Legacy CEF 103.
- Lint/format web code with ESLint 10 + Prettier 3.9 or Biome 2.5.

## 7. CI (GitHub Actions)
`assets/configs/github-workflow.yml` (actions/checkout@v7, setup-python@v7, setup-node@v7, JohnnyMorganz/stylua-action@v5):
1. `scripts/manifest.py` on every resource.
2. `scripts/audit.py --min high` (fails on high/critical).
3. `scripts/natives.py check --strict` (downloads the native DB on the runner).
4. `stylua --check` (CfxLua syntax via `.stylua.toml`).
5. NUI: `npm ci && npm run build` for resources with `web/package.json` (Node 22).
selene is optional in CI because of CfxLua syntax (install the binary from its releases if you use it).

## 8. Debugging and profiling tools
| Tool | Where | Use |
|---|---|---|
| F8 console | client | Script errors (`SCRIPT ERROR: @res/file.lua:12`), `print` output. First error wins. |
| Server console / txAdmin live console | server | Server errors, `ensure`/`restart`, `refresh`. |
| `resmon` (`resmon 1`) | client | Per-resource CPU ms / memory; idle target 0.00–0.02 ms. |
| `profiler record 500` → `profiler view` / `profiler saveJSON file.json`; `profiler status` | client F8 and server console | Frame-level script timing; open in Chrome. |
| `nui_devtools` / http://localhost:13172 | client | Chromium devtools for NUI/DUI (dev mode). |
| `strict` natives check | skill | `python scripts/natives.py check <res> --strict`. |
| `lib.print.*` (ox_lib) / `ox:printlevel` convar | both | Leveled logging. |
| `block_net_game_event`, `rateLimiter_*` convars | server | See `events-and-callbacks.md`. |
More: `debugging.md` (error catalogue) and `performance.md`.

## 9. Skill scripts (Python 3.8+, standard library only)
| Script | Purpose |
|---|---|
| `scripts/natives.py` | `update`, `search`, `show`, `check` natives (official DB, offline cache) |
| `scripts/manifest.py` | validate `fxmanifest.lua` vs files on disk |
| `scripts/audit.py` | heuristic security/performance/compat audit |
| `scripts/scaffold.py` | create a resource from templates (bridge, optional NUI) |

## 10. Sources
- https://github.com/overextended/fivem-lls-addon (README, `config.json`, `plugin.lua`) · https://github.com/overextended/cfxlua-vscode (discontinued notice) · https://github.com/LuaLS/lua-language-server/releases · https://github.com/LuaLS/LLS-Addons (`addons/fivem`)
- https://github.com/JohnnyMorganz/StyLua (README syntax table, `Cargo.toml` features, release workflow, CHANGELOG 2.1.0) · https://github.com/Kampfkarren/selene (CHANGELOG 0.32.0, `selene-lib/Cargo.toml` features)
- https://www.npmjs.com/package/esbuild · https://www.npmjs.com/package/rolldown · https://www.npmjs.com/package/tsup · https://www.npmjs.com/package/tsdown · https://www.npmjs.com/package/typescript · https://www.npmjs.com/package/@citizenfx/server
- https://docs.fivem.net/docs/scripting-manual/runtimes/javascript/ · https://docs.fivem.net/docs/scripting-manual/debugging/using-profiler/ · https://forum.cfx.re/t/809058
- https://github.com/actions/checkout/releases · https://github.com/JohnnyMorganz/stylua-action
