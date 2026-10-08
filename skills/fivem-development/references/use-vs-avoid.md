# USE vs AVOID — master guide

Baseline: FXServer Legacy 35245 / Latest 37150, game build 3889, CfxLua 5.4, Node 22, ox_lib 3.40, oxmysql 2.14.3, ox_inventory 2.48, ox_target 1.18, Qbox 1.24, ESX 1.15.2 — verified 2026-10-07 (versions.md has sources). One line per decision: what to avoid, what to use instead, and why. Details live in the linked reference files.

## Contents
1. Platform, manifest and runtimes
2. Lua language and threads
3. Events, callbacks, exports
4. Natives
5. Entities, OneSync, state bags
6. Database
7. Libraries and resources (deprecated → replacement)
8. Frameworks
9. UI / NUI
10. Config, convars and secrets
11. Security patterns
12. Performance patterns
13. Server operations and hosting
14. Monetisation and policy
15. Tooling
16. Common wrong advice found in community skills
17. Sources

## 1. Platform, manifest and runtimes
| AVOID | USE | Why |
|---|---|---|
| `__resource.lua`, `resource_manifest_version` | `fxmanifest.lua` + `fx_version 'cerulean'` + `game 'gta5'` | legacy format; missing `game` breaks loading |
| `fx_version 'adamant'/'bodacious'` | `'cerulean'` | old feature set |
| relying on Lua 5.3 semantics | CfxLua 5.4 (`lua54 'yes'` optional) | 5.3 removed 2025-06-24 |
| `node_version '16'` | omit, or `'22'` | Node 16 removed 2026-02 |
| unsupported/old artifacts | Recommended artifact (35245 at baseline) | builds older than the support window are not joinable |
| `sv_experimental*` flags, `onesync off` | defaults (OneSync forced on) | flags removed; OneSync always on |
| `sv_replaceExeToSwitchBuilds` | `sv_enforceGameBuild 3889` | removed |
| `xbl:` / `live:` / `ip` / `steam` as account key | `license` (`GetPlayerIdentifierByType(src, 'license')`) | xbl/live removed 2026-04; steam optional; ip changes |
| Mono-only C# assumptions on Enhanced | .NET 10 on Enhanced, Mono (CitizenFX.Core v1) on Legacy — `mono_rt2` expired 2026-06-30 | different runtimes |

## 2. Lua language and threads
| AVOID | USE | Why |
|---|---|---|
| globals | `local` everything | speed, no cross-file collisions |
| `Citizen.CreateThread/Wait/SetTimeout` | `CreateThread`, `Wait`, `SetTimeout` | shorter aliases, same function |
| `while true do` without `Wait` | dynamic sleep (`Wait(sleep)`, 500–1000 ms idle) | freezes client/server |
| `Wait(0)` outside drawing/input | event-driven code, `lib.points`/`lib.zones` | per-frame cost |
| a thread per entity/point | one thread iterating a table | scheduler overhead |
| reading `source` after a `Wait`/await | `local src = source` on line 1 | `source` changes after yields |
| `GetDistanceBetweenCoords` / manual math | `#(a - b)` on vectors | native vector ops, faster |
| `GetHashKey('x')` in hot paths | backtick `` `x` `` / `joaat` | compile-time hash |
| string `..` in loops | `table.concat` | allocations |
| periodic `collectgarbage('collect')` | let GC run; watch `collectgarbage('count')` | stop-the-world spikes |
| `load`/`loadstring` on any external data | data formats (`json.decode`) | RCE; backdoor signature |

## 3. Events, callbacks, exports
| AVOID | USE | Why |
|---|---|---|
| `RegisterServerEvent` | `RegisterNetEvent` | legacy alias |
| `RegisterNetEvent` for internal events | `AddEventHandler` | net events are callable by cheaters |
| generic names (`giveMoney`) | `resource:side:action` | brute-forced by menus; collisions |
| client sends price/amount/reward/coords | client sends intent; server computes | trust boundary |
| ping-pong "request/response" events | `lib.callback` (ox_lib) | timeouts, typed returns, less boilerplate |
| QBCore/ESX callbacks in new portable code | `lib.callback` | consistent across frameworks; QB callbacks have no rate limit/timeout |
| unrestricted sensitive server exports | `GetInvokingResource()` allow-list | any resource (incl. compromised ones) can call exports |
| `TriggerClientEvent(-1, ...)` with big/frequent payloads | targeted events, `TriggerLatentClientEvent`, state bags | bandwidth, hitches |
| `esx:getSharedObject` event | `@es_extended/imports.lua` or `exports.es_extended:getSharedObject()` | removed pattern |
| `GetCoreObject()` per call/loop | once at file scope (or direct exports / Qbox exports) | cost; QB moved to `GetShared` |
| `ExecuteCommand` with player input | direct API calls; ACE | command injection |

## 4. Natives
| AVOID | USE | Why |
|---|---|---|
| inventing native names/params | `python scripts/natives.py show/search` | hallucinated natives fail silently |
| `GetPlayerPed(-1)` | `PlayerPedId()` / `cache.ped` | clearer, cached |
| client `CreateVehicle` for persistent/owned vehicles | `CreateVehicleServerSetter` (server) | entity lockdown; ownership; persistence |
| `NetworkRegisterEntityAsNetworked` hacks | server-side creation | unreliable |
| `SetEntityAsMissionEntity` + `DeleteVehicle` dance | `DeleteEntity` with control / server-side delete | simpler, reliable |
| `GetPlayerIdentifiers` loop to find license | `GetPlayerIdentifierByType(src, 'license')` | direct |
| `Citizen.InvokeNative(0x...)` when a wrapper exists | the named wrapper | readability, typed |
| DrawText3D helpers every frame | ox_lib textUI / ox_target | per-frame cost |
| `DisableControlAction` loops for whole UIs | `SetNuiFocus` (+ `SetNuiFocusKeepInput` carefully) only while open | per-frame cost, stuck input |
| Task natives on peds you don't own | run on the owner client (or server-side ped tasks where available) | tasks only run on the owner |

## 5. Entities, OneSync, state bags
| AVOID | USE | Why |
|---|---|---|
| `sv_entityLockdown inactive` (default) | `strict` (or `relaxed` while migrating) | blocks client spawn exploits |
| client-writable replicated state for authority | `setr sv_stateBagStrictMode true`; server tables for money/permissions | clients could write bags |
| nested state bag edits `state.x.y = v` | flat keys `state['x:y'] = v` | nested edits don't replicate |
| polling entity state | `AddStateBagChangeHandler` | event-driven |
| trusting netIds from clients | `NetworkGetEntityFromNetworkId` + `DoesEntityExist` + type/owner/bucket checks | spoofed ids |
| syncing positions via events | built-in entity sync | redundant traffic |
| orphaned server entities | `SetEntityOrphanMode` deliberately; delete on resource stop | leaks |
| `sv_protectServerEntities` on Enhanced | `sv_entityLockdown` | replaced on Enhanced |

## 6. Database
| AVOID | USE | Why |
|---|---|---|
| `mysql-async`, `ghmattimysql`, `MySQL.Async.*`, `MySQL.Sync.*` | oxmysql (`@oxmysql/lib/MySQL.lua`; `MySQL.query.await`, `MySQL.single.await`, `MySQL.scalar.await`, `MySQL.insert.await`, `MySQL.update.await`) | deprecated/unmaintained |
| oxmysql < 2.14.0 | ≥ 2.14.0 (baseline 2.14.3) | sqlstring SQL-injection fix |
| string-built SQL (`..`, `string.format`, JS template literals) | `?` / `@named` placeholders | SQL injection |
| several dependent awaits that can half-succeed | `MySQL.transaction.await` / `MySQL.startTransaction` | consistency, dupes |
| queries per tick / per player per second | cache in memory, batch writes, periodic saves | DB load, hitches |
| `SELECT *` in hot paths | explicit columns + indexes | bandwidth, plans |
| DB root user, port 3306 public | least-privilege user, bind to localhost/private net | blast radius |
| `MySQL.prepare` for one-off statements | `prepare` for hot repeated statements only | prepared-statement cache |

## 7. Libraries and resources (deprecated → replacement)
| AVOID | USE | Why |
|---|---|---|
| `CommunityOx/*` forks, `@communityox/*`, coxdocs.dev | `overextended/*`, overextended.dev | forks archived 2026-04-28 |
| `screenshot-basic` | `screencapture` (provides screenshot-basic) | unmaintained since 2023 |
| `@nativewrappers/client` | `@nativewrappers/fivem` / `@nativewrappers/server` | renamed |
| `qbcore-framework/*` URLs | `qbcore-fivem/*` | org moved |
| esx_menu_default / esx_menu_dialog / qb-menu / qb-input / NativeUI / RageUI in new code | ox_lib context/menu/input/alert | maintained, consistent, secure input handling |
| qb-target / bt-target / qtarget | ox_target | maintained; provides `qtarget` only (not `qb-target`) |
| PolyZone | `lib.zones` / `lib.points` | maintained, cheaper |
| progressbar / mythic_progbar / mythic_notify | `lib.progressBar` / `lib.progressCircle`, `lib.notify` | maintained |
| ps-housing (archived 2026-02) | maintained housing (framework-specific) | no updates |
| ox_inventory < 2.47.6 | ≥ 2.47.6 (baseline 2.48.0) | dupe fixes 2.46.0–2.47.6 |
| leaked / "free premium" resources, panels | author releases, Cfx Portal / Tebex purchases | Cipher/Blum backdoors |
| obfuscated "anticheats"/"admin panels" with HTTP | audited open source or reputable vendors; server-side checks (anticheat.md) | supply-chain RCE |

## 8. Frameworks
| AVOID | USE | Why |
|---|---|---|
| mixing frameworks in one resource | bridge pattern (framework-bridge.md) | maintainability |
| Qbox `Player.Functions.*` | qbx_core exports (with `reason` for money) | deprecated since 1.22.0 |
| Qbox/QB permission API (`AddPermission`, `HasPermission`) | ACE (`IsPlayerAceAllowed`) | deprecated |
| `qbx_core/shared/items.lua` | `ox_inventory/data/items.lua` | deprecated (empty) |
| caching ESX `xPlayer` or writing its fields | re-fetch per handler; use methods | snapshot copies |
| trusting `ESX.PlayerData` / QB PlayerData on the server | server-side player objects | client data |
| reachable `QBCore:Server:SpawnVehicle` / `CreateVehicle` on public servers | permission wrapper; server-side spawn helpers | arbitrary spawns |
| `QBCore.Functions.HasItem` (server) | `exports['qb-inventory']:HasItem` / ox_inventory | deprecated |

## 9. UI / NUI
| AVOID | USE | Why |
|---|---|---|
| `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, `{@html}`, jQuery `.html()` with player text | framework text rendering / `textContent` | XSS inside the client |
| runtime CDN scripts in NUI | bundled assets (Vite, `chrome103` target) | offline, supply chain, CSP |
| `ui_page 'http://localhost:5173'` in production | built `dist/` | dev-only |
| `SendNUIMessage` per frame | on change, throttled 4–10 Hz | CEF cost |
| always-visible heavy UI | hide root when closed; no infinite animations/backdrop-filter | GPU/CPU every frame |
| forgetting `SetNuiFocus(false, false)` | release on close/escape/`onResourceStop` | stuck cursor |
| trusting `RegisterNUICallback` data | re-validate on the server | client data |
| heavy JS (JIT disabled in CEF from 2026-10) | small bundles, memoisation | slower V8 |
| expecting escrow to protect NUI | treat NUI as public | escrow does not support NUI |

## 10. Config, convars and secrets
| AVOID | USE | Why |
|---|---|---|
| one shared `config.lua` with prices/limits/webhooks | `config/shared.lua` (public) + `config/server.lua` (`server_scripts` only) | shared files are downloaded |
| `setr`/`sets` for secrets | `set` (server-only) / environment variables | replicated or public |
| webhooks/API keys in code or Git | `GetConvar('myres_webhook', '')` | leaks |
| `rcon_password` | txAdmin; leave RCON unset | plaintext UDP |
| `sv_scriptHookAllowed true` | `false` | mod-menu vector |
| `sv_pureLevel 0` on public servers | `1` or `2` | blocks modified client files |
| `server.cfg` with secrets in public repos | split `secrets.cfg` (`exec`), git-ignored | leaks |

## 11. Security patterns
| AVOID | USE | Why |
|---|---|---|
| client-side permission checks only | server ACE/framework checks | UX ≠ security |
| grant across a yield before verifying/taking | no yield between check and mutations, else take/verify first + refund on failure; per-player lock | dupes |
| unbounded arguments | type checks, clamps, NaN/inf rejection, length caps | crashes, exploits |
| no rate limit on sensitive actions | token bucket per player/action | spam, dupes |
| banning on single noisy signal | score + evidence + review; auto-ban only honeypots/impossible values | false bans |
| client-side anticheat as authority | server-side game-event filters (`explosionEvent`, `ptFxEvent`, `giveWeaponEvent`, `entityCreating`, …) | client checks are bypassed |
| Discord webhook calls from the client | server-side, batched, `allowed_mentions = { parse = {} }` | URL leaks, ping abuse |
| running FXServer as Administrator/root | dedicated low-privilege user, egress allow-list | backdoor blast radius |
| txAdmin `all_permissions` for every staff member | least-privilege permissions | account compromise impact |

## 12. Performance patterns
| AVOID | USE | Why |
|---|---|---|
| distance loops for markers/interactions | ox_target, `lib.points`, `lib.zones` | measure total interaction-library work; preserve necessary per-frame behavior |
| `GetGamePool` scans every frame | throttled scans, `lib.getClosest*` | O(n) per frame |
| per-frame table/closure allocation | reuse with `table.wipe`, preallocate `table.create` | GC spikes |
| heavy sync work on svMain (50 ms tick) | async, chunked, staggered ≥ 1000 ms jobs | server hitches |
| `json.encode` of big tables frequently | diff and send changes | O(size) |
| handlers re-registered repeatedly | register once; remove handlers on cleanup | leaks |

## 13. Server operations and hosting
| AVOID | USE | Why |
|---|---|---|
| txAdmin port 40120 open to the world | firewall allow-list / VPN / TLS reverse proxy | panel brute force |
| editing txAdmin files / copying from `master` | official artifact releases | tampering, mismatches |
| real server IP on the list behind a proxy | `sv_forceIndirectListing`, `sv_listingHostOverride`, `sv_endpoints` | DDoS targeting |
| `sv_endpointPrivacy` / `sv_exposePlayerIdentifiersInHttpEndpoint` in server.cfg | delete them (removed 2026-07-08; IPs are never exposed on HTTP endpoints) | convars now only warn at boot |
| `sv_enableDevtools` | nothing (convar does not exist; feature request citizenfx/fivem#2667). Enhanced: `sv_devMode false` | community guides recommend it; it's a no-op |
| no backups / untested restores | scheduled offsite DB backups + restore tests | dupes/infections need rollback |
| `resources/` without version control | Git (detect injected files) | backdoor detection |

## 14. Monetisation and policy
| AVOID | USE | Why |
|---|---|---|
| PayPal/Patreon/crypto/other stores for perks | Tebex only | Cfx docs: other providers prohibited (PLA) |
| real-money gambling, cash-out, loot boxes/gacha (real or in-game currency), currency sales, crypto/NFTs | cosmetic/custom content, queue/VIP perks via Tebex | PLA §3.1 |
| Rockstar logos/IP in server name; no disclaimer | own branding + "NOT APPROVED, SPONSORED, OR ENDORSED BY ROCKSTAR GAMES" + contact email | PLA §2.3 |
| commercial music streams | licence-free/royalty-free audio | PLA §2.4 |
| decompiling/decrypting purchased or escrowed resources | ask the author; use `escrow_ignore` files | PLA §6.4; escrow |
| feeding Marketplace content to AI training | — | PLA §6.4(4) |

## 15. Tooling
| AVOID | USE | Why |
|---|---|---|
| plain editor with no FiveM typings | VS Code + CfxLua extension / fivem-lls-addon, `@citizenfx/*` typings | catches native/API mistakes |
| shipping unreviewed changes | `natives.py check --strict`, `manifest.py`, `audit.py` in CI (`--json`) | regressions, exploits |

## 16. Common wrong advice found in community skills
Claims verified wrong against primary sources (2026-10-07). Use as red flags when reviewing generated or third-party guidance.
| Claim seen in community skills | Reality |
|---|---|
| `dependency '/res'` marks an optional dependency | A leading `/` is a constraint (`/server:<build>`, `/onesync`, `/gameBuild:<n>`, `/policy:`); there are no optional dependencies — check `GetResourceState` at runtime instead |
| Pass vectors as `{x,y,z}` tables over events | Lua↔Lua events keep `vector3/4`/`quat` (msgpack ext); only Lua↔JS needs tables |
| `.await` (oxmysql/lib.callback) deadlocks in an event handler | Net/event handlers already run in a coroutine; `.await` is fine there |
| `SetRoutingBucketPopulationEnabled` is off by default | Population is on in every bucket by default (`noPopulation = false`); disable it explicitly for instances |
| `GetEntityCoords` is client-only | A server version exists (OneSync, 1 argument) |
| `nui_devtools true` in server.cfg | It is a client console command / http://localhost:13172 |
| Leading-underscore natives are called as `_Name` | Codegen strips it: `_GET_X` → `GetX`; only `_<digit>` parts keep the underscore (`GetGroundZFor_3dCoord`) |
| `resmon` in the server console | Client command; the server uses `profiler record/save/view` |
| `QBX:Client:OnPlayerLoaded` events | Qbox fires `QBCore:Client:OnPlayerLoaded` and `qbx_core:client:*` events |
| `Player(PlayerId()).state` on the client | `Player()` expects a **server ID**; use `LocalPlayer.state` |
## 17. Sources
- Version and deprecation sources: [versions.md](versions.md)
- Secure your events: https://docs.fivem.net/docs/developers/server-security/
- Server commands / convars: https://docs.fivem.net/docs/server-manual/server-commands/ · https://docs.fivem.net/docs/scripting-reference/convars/
- OneSync / state bags: https://docs.fivem.net/docs/scripting-reference/onesync/ · https://docs.fivem.net/docs/scripting-manual/networking/state-bags/
- oxmysql 2.14.0: https://github.com/overextended/oxmysql/releases/tag/v2.14.0 · ox_inventory releases: https://github.com/overextended/ox_inventory/releases
- PLA (2026-09-10): https://static.cfx.re/platform-license-agreement-10-sept-2026.pdf · Tebex: https://docs.fivem.net/docs/server-manual/setting-up-a-tebex-store/ · Asset Escrow: https://docs.fivem.net/docs/server-manual/asset-escrow/
- Proxy setup: https://docs.fivem.net/docs/server-manual/proxy-setup/
