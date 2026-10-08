# Version baseline — verified 2026-10-07 (community-review corrections 2026-10-08)

Every value below was checked against primary sources (GitHub releases/tags/source, npm registry, docs.fivem.net, forum.cfx.re, the artifact API) on **2026-10-07**. When exact versions matter, re-check (see "How to re-verify") or ask which versions the user's server runs. Topic files carry their own "Baseline:" header with details. `assets/baseline.json` is the machine-readable copy of these versions (incl. min. safe): keep it in sync with this file.

## Contents
1. Platform (Cfx.re / Rockstar)
2. Overextended (ox) stack
3. Frameworks
4. Ecosystem resources
5. Databases
6. Tooling and npm
7. Asset tools
8. Deprecated / archived / removed — do not recommend
9. Breaking changes timeline 2024–2026 (highlights)
10. How to re-verify
11. Compare installed versions

## 1. Platform (Cfx.re / Rockstar)
| Item | Value | Source |
|---|---|---|
| FXServer (Legacy) Recommended / Latest | **35245** (since 2026-08-20) / **37150** — both bundle txAdmin 8.1.1 | https://changelogs-live.fivem.net/api/changelog/versions/win32/server · https://forum.cfx.re/t/5422124 |
| Hard cutoff | After **2026-10-15** clients cannot join servers older than 35245 | https://forum.cfx.re/t/5422124 |
| Cfx Server (GTA V Enhanced) | **build 161**, early access since **2026-07-21**; `cfx-server.exe`; no Asset Escrow yet | https://docs.fivem.net/docs/server-download/ · https://forum.cfx.re/t/5412858 |
| Artifact support policy | Recommended supported until 6 weeks after the next; Latest 2 weeks; > 3 months old not joinable from the server list | https://docs.fivem.net/docs/server-manual/end-of-support-end-of-life/ |
| Latest game build | **3889** (`mp2026_01`, The Kortz Center Heist) | https://docs.fivem.net/docs/server-manual/server-commands/ |
| txAdmin | **8.1.1** (2026-06-05) | https://github.com/citizenfx/txAdmin/releases |
| fx_version | `cerulean` | https://docs.fivem.net/docs/scripting-reference/resource-manifest/ |
| Lua | CfxLua **5.4.8** only (Lua 5.3 removed 2025-06-24; `lua54 'yes'` optional) | citizenfx/fivem source |
| Server JS | **Node 22** on Legacy (Node 16 removed 2026-02; `node_version` is ignored) · Node 26 on Enhanced | citizenfx/fivem source · https://forum.cfx.re/t/5415045 |
| C# | Legacy: Mono, CitizenFX.Core 1.0.26803 (**`mono_rt2` expired 2026-06-30**) · Enhanced: **.NET 10** | citizenfx/fivem `MonoScriptRuntime.cpp` · https://forum.cfx.re/t/5412576 |
| NUI | Legacy **CEF M103** (Chromium 103.0.5060.141), **V8 JIT disabled** (`--jitless`) from 2026-10-07 · Enhanced CEF version unpublished | citizenfx/fivem `vendor/cef` |
| OneSync | **Forced on** (commit 19fa3d5, 2026-08-16); `sv_experimental*` removed 2026-04-14 | citizenfx/fivem |
| Server threads | svMain 20 Hz (hitch > 150 ms), svNetwork 100 Hz, svSync 120 Hz | citizenfx/fivem source (performance.md) |
| Net event limits | > 50/s (burst 200) dropped; > 75/s (burst 300) or > 128 KiB/s → kick; latent default 25000 B/s | citizenfx/fivem source |
| Platform License Agreement | dated **2026-09-10**; Tebex is the exclusive monetisation partner | https://fivem.net/terms |

## 2. Overextended (ox) stack — all back under `github.com/overextended` (CommunityOx archived 2026-04-28)
| Resource | Version | Min. safe | Date | License | Notes |
|---|---|---|---|---|---|
| ox_lib | **3.40.0** | — | 2026-10-03 | LGPL-3.0 | npm `@overextended/ox_lib` 3.40.0 (no default export since 3.33.1) |
| oxmysql | **2.14.3** | **2.14.0** (SQLi fix) | 2026-10-06 | LGPL-3.0 | mysql2 3.24.5, Node 22, FXServer ≥ 12913; slow-query default 200 ms |
| ox_inventory | **2.48.0** | **2.47.6** (dupe fixes) | 2026-10-03 | GPL-3.0 | frameworks: ox, esx, qbx, nd — **no QBCore since 2.42.0** |
| ox_target | **1.18.1** | — | 2026-04-25 | MIT | `provide 'qtarget'` (not qb-target) |
| ox_core | **1.5.14** | — | 2026-05-29 | LGPL-3.0 | needs MariaDB ≥ 11.4, own DB driver, Node 22 |
| ox_doorlock | 1.22.1 | — | 2026-04-25 | GPL-3.0 | |
| ox_fuel | 1.5.4 | — | 2026-05-29 | GPL-3.0 | server trusts client price — patch it (ox-resources-misc.md) |
| ox_banking | 1.0.6 | — | — | — | requires ox_core |
Docs: https://overextended.dev/docs (coxdocs.dev redirects here).

## 3. Frameworks
| Framework | Version | Min. safe | Date | Repo / docs | Notes |
|---|---|---|---|---|---|
| Qbox `qbx_core` | **1.24.0** | — | 2026-08-22 | https://github.com/Qbox-project/qbx_core · https://docs.qbox.re | needs ox_lib ≥ 3.20, ox_inventory ≥ 2.42.1, OneSync Infinity, build ≥ 10731, MariaDB ≥ 10.9; `/optin` enforced for admin cmds |
| ESX Legacy `es_extended` | **1.15.2** | — | 2026-09-06 | https://github.com/esx-framework/esx_core · https://docs.esx-framework.org/en | esx_lib required (1.14+), build ≥ 10188; `removeAccountMoney` can go negative; `addInventoryItem` ignores weight |
| QBCore `qb-core` | manifest 1.3.0 (code 2026-06-17) | — | — | https://github.com/qbcore-fivem/qb-core · https://qbcore.org/docs | **2026-05 refactor** (no `QBConfig`/`QBShared` globals, `GetShared`, `OnPlayerUpdated`) |
| ND_Core | 2.3.2 (main to 2026-03) | — | 2025-02-22 | https://github.com/ND-Framework/ND_Core · https://ndcore.dev | low activity |
| vRP | — | — | last push 2025-05 | https://github.com/vRP-framework/vRP | unmaintained; Creative/vRPEX off-GitHub |

QBCore resources: qb-inventory 2.2.3, qb-target 5.5.0, qb-menu 1.5.0, qb-input 1.2.0, qb-banking 2.0.0, PolyZone 2.6.2.

## 4. Ecosystem resources
| Resource | Version | Notes |
|---|---|---|
| pma-voice | 7.0.1 (tag v7.0.2-rc3) | releases page stale |
| screencapture (itschip) | 0.17.2 (2026-09-24) | replaces screenshot-basic (`provide`) |
| Fivemanage SDK (`fmsdk`) | 3.2.0 (2026-08-06) | Node 22 |
| npwd | 3.16.0 (2025-03-27) | maintenance mode |
| illenium-appearance | 5.7.0 (no commits since 2024-12) | Qbox recipe default |
| bob74_ipl | 2.7.1 (2026-10-04) | adds Enhanced streaming files, Kortz Center |
| Renewed-Weathersync | 1.1.8 | |
| ps-dispatch / ps-mdt | 3.0.0 / 3.1.4 | ps-housing/ps-hud/ps-inventory/ps-ui archived 2026 |
| vMenu Enhanced / EasyAdmin | 1.0.6 (3.8.67) / 7.53 | |
Full list and use/avoid per category: [ecosystem-resources.md](ecosystem-resources.md), [qbox-ecosystem.md](qbox-ecosystem.md), [esx-ecosystem.md](esx-ecosystem.md).

## 5. Databases — vendor recheck 2026-10-08
| Engine | Maintained LTS patches observed | Support distinction |
|---|---|---|
| MariaDB Community | 12.3.3, 11.8.9, 11.4.13, 10.11.19 | Community EOL: 12.3 on 2029-06-12; **11.8 on 2028-06-04**; 11.4 on 2029-05-29; 10.11 on 2028-02-16. 10.6 Community ended 2026-07-06. |
| MySQL | 8.4.12, 9.7.3 | LTS policy and package availability must be checked for the selected deployment/support channel. |

Primary evidence: [MariaDB maintenance](https://mariadb.org/about/#maintenance-policy),
[maintenance releases](https://mariadb.org/mariadb-server-12-3-11-8-11-4-and-10-11-q3-2026-maintenance-releases-and-goodbye-10-6/),
[MySQL 8.4](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/),
[MySQL 9.7](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/) and
[MySQL policy](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html).

For a new compatible ox deployment, evaluate a maintained MariaDB LTS; preserve
supported MySQL when the project is compatible. Qbox baseline migrations contain
MariaDB-specific syntax. MariaDB 12.3 changes snapshot-isolation defaults, so a major
upgrade needs transaction/driver/migration tests. No version is a hitch-free guarantee.
Re-verify when asked for a current recommendation; use the compatibility and tuning
procedure in [database-optimization.md](database-optimization.md).

## 6. Tooling and npm (registry, 2026-10-07)
| Package / tool | Version |
|---|---|
| @citizenfx/client · @citizenfx/server | 2.0.35805-1 |
| @nativewrappers/fivem · /server | 0.0.174 (`@nativewrappers/client` deprecated) |
| react / react-dom · vite · @vitejs/plugin-react · typescript | 19.3.0 · 8.3.3 · 6.1.2 · 7.0.2 |
| svelte · vue · tailwindcss | 5.57.2 · 3.5.43 · 4.3.3 (**v4 needs Chrome 111+ → use Tailwind 3.4.19 on Legacy CEF 103**) |
| NUI boilerplate | project-error/fivem-react-boilerplate-lua v4.1.0 (2026-08-02) |
| Lua Language Server addon | https://github.com/overextended/fivem-lls-addon (clone it; the `cfxlua-vscode` extension is discontinued) |
| StyLua | 2.5.2 (`syntax = "CfxLua"`) |

## 7. Asset tools
Sollumz **2.9.0** (2026-08-04, Blender ≥ 4.0) · CodeWalker (Discord dev builds; Gen9 converter in source since 2025-04) · **Alchemist** (Legacy → Enhanced conversion, Windows 11) · grzyClothTool 1.3.0 (2026-07-14).

## 8. Deprecated / archived / removed — do not recommend
- `CommunityOx/*` and `@communityox/*` (archived), `coxdocs.dev`.
- `mysql-async`, `ghmattimysql`, `MySQL.Async/Sync`.
- `screenshot-basic` (unmaintained; use screencapture).
- `qbcore-framework/*` org URLs (now `qbcore-fivem`), `QBConfig`/`QBShared` globals, `QBCore:Player:SetPlayerData`-only listeners.
- ox_inventory with QBCore; ox_inventory < 2.47.6.
- `qbx_smallresources` (deprecated), `qbx_apartments`/`qbx_houses` (→ `qbx_properties`), `qbx_radio`, `qbx_weathersync` (archived), ps-housing/ps-hud/ps-inventory/ps-ui (archived).
- `@nativewrappers/client`, `overextended.cfxlua-vscode` extension.
- `__resource.lua`, `fx_version 'adamant'/'bodacious'`, Lua 5.3, Node 16 / `node_version '16'`, `mono_rt2`.
- `sv_replaceExeToSwitchBuilds`, `sv_experimental*`, `onesync` convars (internal), `sv_endpointPrivacy`, `sv_exposePlayerIdentifiersInHttpEndpoint` (removed 2026-07-08), `xbl:`/`live:` identifiers (removed 2026-04-27), `*.users.cfx.re` proxy (retired 2026-03-31).
Master list with replacements: [use-vs-avoid.md](use-vs-avoid.md).

## 9. Breaking changes timeline 2024–2026 (highlights)
| Date | Change |
|---|---|
| 2024-08 | ox_inventory 2.42.0 drops QBCore bridge |
| 2024-11 | ESX 1.11: build ≥ 10188, SecureNetEvent (client), spawnmanager optional |
| 2025-02 | oxmysql 2.13: Node 22, FXServer ≥ 12913 |
| 2025-06-24 | Lua 5.3 removed |
| 2026-02 | Node 16 removed |
| 2026-04 | ox repos back to overextended; oxmysql 2.14 (SQLi fix); `sv_experimental*` removed; QBCore `OnPlayerUpdated`; `xbl/live` identifiers removed |
| 2026-05 | QBCore core refactor; ox_inventory 2.46/2.47 (dupe fixes, validation-only hooks + post-hooks); ox_lib 3.35 npm exports change |
| 2026-06-30 | `mono_rt2` expired |
| 2026-07 | ESX 1.14 (esx_lib); GTA V Enhanced early access (07-21) |
| 2026-08 | OneSync forced; FXServer 35245 recommended; Qbox 1.24 |
| 2026-09 | ESX 1.15.x; PLA revision 09-10 |
| 2026-10 | CEF V8 JIT disabled; ox_inventory 2.48 (vehicle inventories by netid); cutoff 10-15 |

## 10. How to re-verify
```bash
curl -s https://changelogs-live.fivem.net/api/changelog/versions/win32/server   # artifacts
gh release list -R overextended/ox_lib -L 3                                     # any GitHub repo
curl -s https://registry.npmjs.org/<pkg>/latest                                 # npm
python scripts/natives.py update                                                # native DB
python scripts/build_natives_catalog.py --refresh                               # regenerate assets/natives
```

## 11. Compare installed versions
1. Read the installed `version` from the resource's `fxmanifest.lua` (else `package.json` or the git tag) and cite `file:line`.
2. Compare semver against **Min. safe** and the baseline (§2–§4, `assets/baseline.json`).
3. Classify: `< min-safe` (**high** if an advisory exists, e.g. [security.md](security.md) §16) · `< baseline` (low) · `= baseline` · `unknown` (no version found; a fork may carry a stale manifest — say so).
4. Never call a resource "up to date" without a `file:line` citation.

`python scripts/project.py <server> --versions` does this automatically.

## Sources
Each row above cites its primary source inline; topic files list full sources.
