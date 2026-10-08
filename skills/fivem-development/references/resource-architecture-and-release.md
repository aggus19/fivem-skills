# Resource architecture, packaging and release

Baseline: GitHub Actions versions (softprops/action-gh-release v3.0.3, actions/checkout v7.0.1, actions/upload-artifact v7.0.2) and FiveM docs — verified 2026-10-08.

## Contents
1. Architecture rules (public contract, dependencies, lifecycle)
2. Pre-release gate
3. Packaging
4. Tag-triggered release workflow
5. Release notes and upgrade safety
6. Known runtime gotchas worth testing before release
7. Sources

## 1. Architecture rules
- One resource = one folder; the folder name is the runtime name used by `dependency`, `exports[...]`, `GetResourceState`. Keep `fxmanifest.lua` declarative (see `fxmanifest.md`).
- Same-resource calls: plain Lua functions/modules (`require`). Use `exports` for the intentional cross-resource API and `RegisterNetEvent` only for what the other side of the network must call. Validate export arguments as strictly as net events (an export reachable by another resource must not skip the checks of the matching server event).
- Order is declared, not guessed: `dependency`/`dependencies` (with `/onesync`, `/gameBuild:` constraints) for required resources; `GetResourceState(name) == 'started'` before optional integrations; never use a `Wait()` race instead.
- Keep optional framework/inventory code behind one adapter file (`framework-bridge.md`); the core logic stays framework-free.
- Server-only config (prices, rewards, secrets, webhooks) never goes in `shared_scripts`/client files.
- Lifecycle: every thread, entity, blip, zone, DUI, key mapping and NUI focus created by the resource has a teardown in `onResourceStop`; initialization is idempotent so `restart <res>` and late joiners do not duplicate state. Entity rules: `onesync-entities.md`.
- Boot-time self-check in `onResourceStart` (`res == GetCurrentResourceName()`): validate `Config` ranges/enums and required convars, `error()` with an actionable message, and skip optional features when their dependency is absent.
- Observability: gate debug output behind a convar (`GetConvarInt('myres:debug', 0) == 1`, or ox_lib `lib.print.debug` with `set ox:printlevel:<resource> debug`), never log per frame, redact tokens/webhooks, include resource/action/source in messages, and rate-limit repeated failure logs. See `debugging.md`.
- Localization: see `ox-lib-utilities.md` section 2 (en fallback is built in); keep player-facing strings out of logic.

## 2. Pre-release gate
Run from the repo root of the resource (paths relative to this skill):
1. `python scripts/natives.py check --strict <res>` · `python scripts/manifest.py <res>` · `python scripts/audit.py <res>`.
2. Lint/format (`tooling.md` section 2-3, CfxLua syntax), NUI `npm ci && npm run build`, then confirm every built file is matched by `files {}`.
3. Two-client test (ownership, scope, state bags), join/leave mid-action, `restart <res>` while in use, death/cancel during timed actions, a player without the required job/permission (must be denied server-side), NUI open/close ten times (focus always released).
4. Clean-server start: copy the packaged archive into an empty `resources/` and `ensure` it; zero `SCRIPT ERROR` after an idle soak.

## 3. Packaging
- Archive contains one top-level folder named exactly like the resource, with only runtime files: manifest, scripts, built NUI output, locales, `sql/` migrations, license, README, CHANGELOG.
- Exclude `.git*`, `.env`, `node_modules`, source maps, test fixtures, editor files, local logs, credentials.
- Linux paths are case-sensitive: manifest globs and NUI asset paths must match the exact case.
- Do not strip third-party license notices.

## 4. Tag-triggered release workflow
```yaml
name: release
on:
  push:
    tags: ['v*']
permissions:
  contents: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build NUI (only if web/package.json exists)
        run: |
          if [ -f web/package.json ]; then (cd web && npm ci && npm run build); fi
      - name: Package
        run: |
          RES="${GITHUB_REPOSITORY#*/}"
          mkdir -p "dist/$RES"
          cp -r fxmanifest.lua config.lua client server shared locales sql "dist/$RES"/ 2>/dev/null || true
          [ -d web/dist ] && mkdir -p "dist/$RES/web" && cp -r web/dist "dist/$RES/web/"
          (cd dist && zip -r "../$RES.zip" "$RES" && cd .. && sha256sum "$RES.zip" > "$RES.zip.sha256")
      - uses: softprops/action-gh-release@v3
        with:
          files: |
            *.zip
            *.zip.sha256
```
Adjust the copied paths to the real layout. Run the section 2 gate in an earlier job (`needs:`) so a failing audit blocks the release. Pin actions to a current major (see `assets/configs/github-workflow.yml`); `NTBBloodbath/selene-action` has had no release since 2021 and does not know CfxLua syntax, so prefer the selene/StyLua binaries as in `tooling.md`.

## 5. Release notes and upgrade safety
- Semver impact: a changed export/event/callback signature, config key or DB schema is breaking (major, or minor for 0.x); document the change and a migration default.
- Ship migrations as idempotent SQL (`CREATE TABLE IF NOT EXISTS`, guarded `ALTER`), state the order and a backup requirement, and never call a data-losing migration reversible.
- Test a clean install and an upgrade from the previous release on a copy of the database (`database-oxmysql.md`).
- README: prerequisites and supported framework/artifact matrix (only versions you tested), `ensure` order, config reference, public exports/events with direction/payload/authority notes, NUI build steps, troubleshooting.

## 6. Known runtime gotchas worth testing before release
- `GetEntityModel` may be `0` inside server `entityCreating` (do not reject on 0): `onesync-entities.md`.
- `AddBlipForArea` ignores `SetBlipAsShortRange` (citizenfx/fivem#3973): remove/create by distance.
- DUI: create on demand, wait for `IsDuiAvailable`, destroy on stop/far (`nui.md` section 11). `SetDuiUrl(dui, 'about:blank')` before `DestroyDui` is a community suggestion, not documented (UNVERIFIED).

## 7. Sources
- https://docs.fivem.net/docs/scripting-reference/resource-manifest/resource-manifest/ (`dependency`/`dependencies`, runtime constraints, `files`)
- https://docs.fivem.net/docs/scripting-reference/events/list/onResourceStart/ · https://docs.fivem.net/docs/scripting-reference/events/list/onResourceStop/
- https://github.com/softprops/action-gh-release/releases (v3.0.3, 2026-08-30) · https://github.com/actions/checkout/releases (v7.0.1) · https://github.com/actions/upload-artifact/releases (v7.0.2) · https://github.com/NTBBloodbath/selene-action/releases (v1.0.0, 2021-06-24)
- https://github.com/citizenfx/fivem/issues/2924 · /4053 · /3973
- https://github.com/overextended/ox_lib (`imports/locale/shared.lua`, `lib.print`)
