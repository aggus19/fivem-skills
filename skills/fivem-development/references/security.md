# Security: server authority, platform hardening and incident response

Baseline: FXServer Legacy 35245 / Latest 37150, OneSync forced on, ox_lib 3.40, oxmysql 2.14.3, ox_inventory 2.48, txAdmin 8.1.1 — verified 2026-10-07 against the Sources at the end of this file. Defensive content only.

## Contents
1. Threat model
2. The five server-side checks
3. Net events: secure template
4. Callbacks and exports
5. Economy and duplication (dupes)
6. Entities, state bags, request control, teleport
7. NUI
8. Admin and permission checks (ACE)
9. Platform security convars (server.cfg)
10. Rate limiting (built-in and per-resource)
11. Logging and Discord webhook hygiene
12. Secrets and credential rotation
13. Supply chain (backdoors, leaks) — summary
14. Hosting, DDoS and txAdmin hardening
15. Exploit classes → defence
16. 2026 dependency advisories
17. Review checklist
18. Sources

Related: [security-validation.md](security-validation.md) (entry-point inventory, operation contracts, replay/concurrency/failure tests), [anticheat.md](anticheat.md) (game-event filtering, detections), [audit-checklist.md](audit-checklist.md) (audit procedure).

## 1. Threat model
- **Everything on the client is attacker-controlled.** Executors can call `TriggerServerEvent` with any name and arguments, call client exports, inject into NUI, read every client/shared file, fake NUI callbacks and write client-side state bags.
- `client_scripts`, `shared_scripts`, `files` and NUI assets are **downloaded to every player**. No secrets, webhooks, admin lists or hidden prices there.
- The server is the **only** source of truth for money, items, jobs, permissions, positions that matter, cooldowns and randomness (loot rolls).
- Cfx docs: cheats can trigger events "in any context" — client→server *and* client-resource→client-resource (`TriggerEvent`).
- Escrowed resources still run client code on the client; their net events are still callable by anyone.
- Third-party code (leaks, "free premium", panels) is the main source of server compromise (section 13).

## 2. The five server-side checks
Every net event, callback or export that changes state must answer:
1. **Who?** In a Lua net event, capture `local src = source` before yielding. For callbacks/exports/commands, verify the runtime's actor/caller contract rather than assuming the global source applies. Resolve the current actor and reject missing/invalid sessions.
2. **Allowed?** Job/grade, gang, ACE permission, ownership of the target entity/vehicle/stash, active job/session state stored server-side.
3. **Where?** When location matters, validate the server-observed ped/entity, distance and routing bucket against the intended interaction. Choose tolerance for the mechanic; client-synchronized position alone does not prove legitimate activity.
4. **What?** Validate types and bounds; reject invalid privileged quantities rather than silently clamping them. Whitelist names/metadata against server config, recompute prices, and reject non-finite numbers, negatives, invalid fractions and oversized/deep payloads before expensive work.
5. **How often?** Cooldown / rate limit per player per action, plus a "busy" lock while an action is in progress.

On failure: reject without mutation and record bounded/sampled evidence. Stale UI, desync and reconnect races can produce invalid calls; a distance mismatch alone is not proof for an automatic ban. See anticheat.md §8.

## 3. Net events and mutation handlers
Use the five checks above at the entry point. For a mutation flow, read the generated shop's server handler and `assets/templates/resource-lua/server/purchase.lua`: success, definitive failure and ambiguous results are distinct. A sell operation needs the same discipline in reverse: a successful item removal followed by an unchecked money grant can lose value.

The generic shop is disabled until its installed adapters, session lifecycle and durable operation/recovery path are integrated. No short pair of framework exports is presented as an atomic economy transaction. See [design-and-validation.md](design-and-validation.md).

Rules:
- Namespace event names for clarity. Names, obscurity and client-held tokens are not access controls; every reachable mutation must validate its operation contract.
- `RegisterNetEvent` only for events that must cross the network. Internal events: `AddEventHandler` (not network-callable).
- `RegisterNetEvent` does not block same-side calls. A client-side handler meant only for the server can check `if source ~= 65535 then return end` (server-originated events arrive with source 65535) — docs call client-side checks "not bullet proof".
- Send **intent** (`itemName`, `count`), never `price`, `reward`, `coords`, `job`.
- Never trust "start" and "finish" events separately: store the start server-side (time, location, job) and consume it on finish (`activeJobs[src] = nil` **before** granting).

## 4. Callbacks and exports
- `lib.callback.register` / framework callbacks: same five checks. Do not return other players' data (identifiers, phone numbers, IPs).
- **Server exports are callable by every resource on the server**, including a compromised one. For sensitive exports (money, bans, permissions) check the caller:
```lua
local allowed = { ['myres_admin'] = true }
exports('setPlayerMoney', function(target, amount)
    local caller = GetInvokingResource()
    if not caller or not allowed[caller] then
        Log.warn('export-denied', 0, { caller = caller or 'unknown' })
        return false
    end
    -- validate target and amount here
end)
```
- Client exports are callable by injected code: never let a client export do something the server would not allow anyway.

### HTTP handlers (`SetHttpHandler`)
`SetHttpHandler` serves `http://<server>:30120/<resource>/...` on the public game port, unauthenticated and unthrottled unless you add it (`audit.py` rule `http-handler-public`).
- Require a token from a `set` convar (never `setr`), compare in constant time; refuse to register the handler when the token is empty.
- Don't authorize on `req.address` alone (wrong behind proxies/`sv_proxyIPRanges`); if you need "local only", combine it with the token.
- Whitelist `req.path`; never build file paths, SQL or `ExecuteCommand` strings from it.
- Cap body size in `req.setDataHandler`, `pcall(json.decode, body)`, per-IP rate limit, no privileged action without auth, no identifiers/IPs/stack traces in responses.
- Dev-only bridges: gate the whole file behind a convar (`if GetConvar('myres_dev', 'false') ~= 'true' then return end`) and never ship it enabled.

## 5. Economy and duplication (dupes)
- Use framework / ox_inventory **server** APIs only; check every return value (`exports.ox_inventory:RemoveItem` returns success).
- **Verify interleaving, not only visible Wait calls.** Exports and hooks can yield internally. Check the installed contracts; serialize conflicting operations through the data owner. A pre-check such as `CanCarryItem` does not reserve capacity. Revalidate after yields, check every mutation and compensation return, and reconcile ambiguous results.
- **Locks need identity and ownership.** Key economic operations by stable character/account identity and bind them to a session generation. A late callback may only clear its own operation token. Resource-local locks cannot protect writes by other resources or processes. Do not release a lock on disconnect while the old operation is still settling.
- Multi-row DB changes in one transaction (`MySQL.transaction.await` / `MySQL.startTransaction`), never two separate awaits that can half-succeed.
- Shops: prices from server config; validate shop exists, distance, job/licence.
- Minigames/jobs: server decides outcome or validates elapsed time (reject completions faster than physically possible).
- ox_inventory hooks are **validation-only** (return `false` to cancel); do side effects in post-hook events (ox_inventory ≥ 2.47.0).
- Log every economic mutation (license, amount, reason, resource).
- **Bound before you multiply.** Lua 5.4 integer arithmetic wraps silently on overflow (no error, no clamp), so `price * qty` with a huge integer `qty` can become negative and pass a `balance < total` check. Cap every client-influenced operand first (`qty <= MAX_QTY`, `math.type(qty) == 'integer'`), then sanity-check the result (`total > 0 and total <= MAX_TX`). Modern ESX/QBCore reject non-positive amounts, but custom accounts and bridges often don't; ESX accounts with `round = true` round *after* the `> 0` check, so `0.4` charges 0 — require integers (`math.tointeger(n)`) yourself. Source: Lua 5.4 manual 3.4.1.
- **Clamping is not validation for privileged quantities.** A client may report *that* something finished, never *how much*. If a payout depends on a quantity (damage repaired, distance driven, items found), the server must have observed or recorded it. Pattern: on `start`, store `pending[src] = { startedAt = os.time(), netId = netId, before = <server-read value> }`; on `complete`, take `pending[src]` (nil -> reject), set it to `nil` immediately (single use, blocks replays), reject if the elapsed time is below the minimum, re-check distance, compute the payout from the stored record plus `ServerConfig`, and clear `pending[src]` on `playerDropped`.
- **Retry identity is not permission.** Bind a request key to actor, action and normalized payload. In-memory deduplication is bounded but does not survive restart. Use stable activity IDs for one server-authorized reward; a reused network ID or second-resolution timestamp alone is not sufficient uniqueness.
- **Ledger plus export is not atomic.** Recording PENDING, calling an inventory/framework export, then recording DONE leaves a crash window. Require owner-supported idempotency/receipts or a recovery design that can establish whether that operation applied. Unknown outcomes must not become FAILED merely because no success response arrived.
- **Retry only with evidence.** A confirmed rolled-back, DB-only transaction may be retried with bounded attempts if its whole operation is safe to repeat. Generic driver `false`, connection loss or timeout does not necessarily prove rollback. Never retry an external grant blindly. See [security-validation.md](security-validation.md) for the operation states and adversarial matrix; a zero-row UPDATE does not automatically roll back a batch transaction.

## 6. Entities, state bags, request control, teleport
- **State bags:** by default players can write their own player bag and owned-entity bags. `setr sv_stateBagStrictMode true` makes the server the only writer of replicated keys (FXServer commit 2025-01-27; ox_lib ≥ 3.37 prints a startup warning when it is off; silence with `set ox:ignoreSecurityAdvisory ["stateBagStrictMode"]`, auto-silenced when qb-core is running). Even with strict mode, never read money/permissions from bags a client could influence; keep authority in server tables.
- Server-side guard for non-strict servers: `AddStateBagChangeHandler(key, nil, function(bagName, key, value, _, replicated) ... end)` — `replicated` describes replication intent, not authenticated authorship. Validate against server-owned state; the callback cannot reject the original change. Do not treat a parameter-presence check as an authorization guard.
- **Entity lockdown:** `set sv_entityLockdown relaxed` by default (blocks client script-created entities, keeps ambient population); `strict` only when every entity is created server-side (it also blocks client-created ambient population) — see [convars-and-commands.md](convars-and-commands.md) §4; per bucket `SetRoutingBucketEntityLockdownMode(bucket, 'strict')`. FXServer source also accepts `no_dummy`; docs list `full` (Enhanced only). Spawn server-side: `CreateVehicleServerSetter`, `CreatePed`, `CreateObjectNoOffset`.
- `sv_filterRequestControl` blocks `REQUEST_CONTROL_EVENT` routing: 0 off (default in source), 1 player-controlled *settled* entities, 2 any player-controlled entity, 3 = 2 + settled non-player entities, 4 no routing at all; -1 behaves like 2 with a console warning. Settle timer: `sv_filterRequestControlSettleTimer` (ms, default 30000).
- `sv_protectServerEntities true` (Legacy; replicated) blocks clients deleting server-created entities; on Enhanced lockdown replaces it.
- `sv_enableNetworkedPhoneExplosions` (default false) — keep false. `sv_enableNetworkedSounds` (default true) — set false if you see sound spam and no resource needs networked sounds.
- Validate `NetworkGetEntityFromNetworkId(netId)`: `DoesEntityExist`, `GetEntityType`, model, owner/plate matches the player's vehicle, routing bucket matches the player's.
- Teleports: server picks the destination from config; never `SetEntityCoords(GetPlayerPed(src), clientX, clientY, clientZ)`.
- Routing buckets: only the server moves players (`SetPlayerRoutingBucket`); validate bucket requests.

## 7. NUI
- NUI is a browser: `SendNUIMessage` data is visible; `RegisterNUICallback` payloads are client data — re-validate on the server.
- No `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, `{@html}` or jQuery `.html()` with player text (names, chat, phone messages, item metadata). XSS inside NUI can call your NUI callbacks and other resources' `https://<resource>/` endpoints.
- Don't load remote scripts in NUI (CDN at runtime); bundle with Vite. Image URLs from players: allow-list domains (Fivemanage etc.).
- Always release focus (`SetNuiFocus(false, false)`) on close, escape and `onResourceStop`.
- XSS impact is real even without a server bug: any NUI frame can call `window.invokeNative('quit', '')`, which force-exits the victim's game (`nui-core/src/NUICallbacks_Native.cpp`); `openUrl` asks the user first.
- NUI callbacks are `https://<resource>/<name>` requests intercepted by CEF (not a localhost port). A player can still send them by hand (CEF devtools on port 13172), so every callback is client input; `nui_callback_strict_mode 'true'` only blocks *other resources'* frames.
- Vite inlines every `VITE_*` env variable into the shipped bundle: never put keys/webhooks there (vite docs: env-and-mode). Do not ship `.map` files in `web/build`.

## 8. Admin and permission checks (ACE)
```lua
-- server.cfg:  add_ace group.admin myres.admin allow
--              add_principal identifier.license:xxxx group.admin
if not IsPlayerAceAllowed(src, 'myres.admin') then return end
```
- `RegisterCommand(name, handler, true)` restricts to ACE `command.<name>`; ox_lib: `lib.addCommand('name', { restricted = 'group.admin' }, handler)`.
- Hiding a menu on the client is UX, not security. Every admin action re-checks on the server.
- Never grant `add_ace resource.<name> command allow` (all commands) to third-party resources; grant only the specific `command.<x>` needed.
- Avoid `ExecuteCommand(('add_principal identifier.%s group.admin'):format(...))` with any client-influenced value (`audit.py` rule `ace-from-code`).
- `add_ace` / `remove_ace` / `add_principal` / `remove_principal` refuse to modify the principal that is currently executing them ("Changing ones own access is not permitted."), so a resource cannot self-grant through its own `resource.<name>` principal. Put grants in server.cfg (`code/client/citicore/se/Security.cpp`).
- `ExecuteCommand('set name value')` needs `add_ace resource.<res> command.set allow`. Prefer `SetConvar` / `SetConvarReplicated` (server natives).
- RCON compares the password with a plain (not constant-time) string compare over plaintext UDP, limited per IP to 0.2/s burst 5, and the limit resets after a successful login. Firewall the port or leave `rcon_password` unset.

## 9. Platform security convars (server.cfg)
| Convar | Recommended | Notes (source) |
|---|---|---|
| `sv_entityLockdown` | `relaxed`; `strict` only if all entities are server-created | default `inactive`; `strict` also blocks client-created ambient population |
| `sv_stateBagStrictMode` | `true` via `setr` | some old scripts break; fix them |
| `sv_filterRequestControl` | `2` after testing | default 0 in source |
| `sv_protectServerEntities` | `true` (Legacy) | replicated convar |
| `sv_enableNetworkedPhoneExplosions` | `false` (default) | |
| `sv_scriptHookAllowed` | `false` | docs: "Not recommended - makes the server vulnerable" |
| `sv_pureLevel` | `1` or `2` | 1: blocks modified client files except audio and known graphics mods; 2: blocks all |
| `sv_authMaxVariance` / `sv_authMinTrust` | defaults (5 / 1) unless you understand them | 1–5; identity-change likelihood / spoofing resistance |
| `sv_requestParanoia` | `1`–`3` if you suffer HTTP floods | blocks IPs sending `Via` (1) / `Upgrade-Insecure-Requests` (2) headers; 3 also closes the socket |
| `sv_kick_players_cnl_*` | defaults | kicks clients without a Cfx.re (CnL) connection |
| `sv_disableClientReplays` | `true` if you don't need Rockstar Editor | reduces cheat surface |
| ~~`sv_endpointPrivacy`~~ | removed 2026-07-08 | player IPs/identifiers are never exposed on HTTP endpoints now; the convar only prints a warning |
| `sv_forceIndirectListing` + `sv_listingHostOverride` | with a proxy | keeps the real IP off the server list |
| `rcon_password` | unset | use txAdmin; RCON is plaintext UDP |
| `sv_tebexSecret`, `mysql_connection_string`, `sv_licenseKey` | `set` only | never `setr`/`sets` |

## 10. Rate limiting
**Built-in (per client, FXServer source):** `rateLimiter_netEvent_rate/burst` (default 50/200 → excess events dropped), `rateLimiter_netEventFlood_*` (75/300 → client kicked, "Reliable network event overflow"), `rateLimiter_netEventSize_*` (128 KiB/384 KiB → client kicked; values: [convars-and-commands.md](convars-and-commands.md) §7, [versions.md](versions.md) §1), and `rateLimiter_stateBag*`. These protect the server process, not your economy — still rate-limit each sensitive action.

**Per resource — token bucket per player and key:**
```lua
local buckets = {}

local function allow(src, key, rate, burst)       -- rate = tokens per second
    local now = GetGameTimer()
    local perPlayer = buckets[src]
    if not perPlayer then perPlayer = {}; buckets[src] = perPlayer end
    local b = perPlayer[key]
    if not b then b = { tokens = burst, t = now }; perPlayer[key] = b end
    if now < b.t then b.t = now end -- clock wrap/reset: do not create negative tokens
    b.tokens = math.min(burst, b.tokens + (now - b.t) / 1000 * rate)
    b.t = now
    if b.tokens < 1 then return false end
    b.tokens = b.tokens - 1
    return true
end

AddEventHandler('playerDropped', function() buckets[source] = nil end)
-- usage: if not allow(src, 'craft', 0.5, 3) then return end
```
- Use fixed server-defined action keys/rates; never allocate limiter keys from arbitrary payloads. Bound in-flight work and total queues as well as per-player frequency; clean up session state on drop. The limiter above is process-local, not a durable replay defense.
- Cap payloads: strings, collection counts, nesting depth and total work before `json.encode`/DB writes.
- Large server→client payloads: `TriggerLatentClientEvent`.

## 11. Logging and Discord webhook hygiene
- Log from the **server** only: who (license via `GetPlayerIdentifierByType(src, 'license')`), what, values, resource, result. Prefer a log service (Fivemanage `fmsdk`, Loki/Grafana, your DB) for volume; Discord is for alerts.
- Webhook URL in a server convar (`set myres_webhook "..."`, read with `GetConvar`), never in client/shared files (`audit.py` rule `webhook-exposed`), never in Git.
- **Batch and throttle** (Discord rate-limits per webhook; one message holds up to 10 embeds); always send `allowed_mentions = { parse = {} }` so player-controlled text cannot ping `@everyone`; truncate player names/messages.
```lua
local webhook = GetConvar('myres_webhook', '')
local queue = {}
local droppedAlerts = 0

function Log.alert(title, description)
    if webhook == '' then return end
    if #queue >= 512 then droppedAlerts = droppedAlerts + 1; return end
    queue[#queue + 1] = { title = title:sub(1, 256), description = description:sub(1, 2000) }
end

CreateThread(function()
    while true do
        Wait(5000)
        if webhook ~= '' and #queue > 0 then
            local embeds = {}
            for i = 1, math.min(10, #queue) do embeds[i] = table.remove(queue, 1) end
            PerformHttpRequest(webhook, function(status)
                if status >= 400 then print(('[myres] webhook failed: %s'):format(status)) end
            end, 'POST', json.encode({ embeds = embeds, allowed_mentions = { parse = {} } }),
                { ['Content-Type'] = 'application/json' })
        end
    end
end)
```
- The example alert queue is bounded, best-effort and memory-only; expose its dropped-alert counter to monitoring. Keep required economic recovery/audit records in durable storage, separately from notifications.
- Screenshots: `screenshot-basic`'s client `requestScreenshotUpload(url, field, cb)` uploads **from the player's client**, exposing the URL/API key to every player. Capture with the server-side `requestClientScreenshot` (or screencapture) and upload from the server; gate captures by ACE + rate limit.
- Discord-role whitelists/permissions: resolve roles server-side from the `discord:` identifier, cache with a TTL, and **fail closed** on API errors/429 (`if not ok then return false end`). A bot token ever set with `setr` or committed to Git is compromised: regenerate it, don't just move it.
- One webhook per channel/purpose; delete and recreate a webhook if it ever leaked (anyone with the URL can post).
- **Where to log:** after the permission check and after the mutation succeeded (`AddMoney`/`AddItem` returned true, DB write returned). Log denied attempts separately (`warn`, `denied = true`, failed permission). Client-only actions the server can't verify: route through a server event with an ACE check and mark `clientReported = true`. Economy-wide audit: one `AddEventHandler('QBCore:Server:OnMoneyChange', function(src, moneyType, amount, action, reason) ... end)` covers every Qbox/QBCore AddMoney/RemoveMoney/SetMoney (qbx_core `server/player.lua`; qb-core `server/player.lua`). To log a resource you can't edit, a server-local `TriggerEvent` is observable with `AddEventHandler`; a client→server net event needs `RegisterNetEvent` in the logger too (per-resource safe-for-net) and its payload is client-controlled; `lib.callback.register`/`lib.addCommand`/exports are not observable — patch after success with a namespaced audit event (`TriggerEvent('mylogs:server:<res>:<action>', src, data)`).
- Don't log full IPs/HWIDs/tokens unless needed; restrict log channel access (privacy, PLA §4 makes the Server Admin responsible for personal-data compliance).

## 12. Secrets and credential rotation
- `set` = server-only; `setr` = replicated to clients; `sets` = public server info. Secrets only with `set` (or a `server_only` file / environment variable).
- Rotate on any suspicion (backdoor found, staff leaves, leaked dump):

| Secret | How |
|---|---|
| `sv_licenseKey` | regenerate in the Cfx.re Portal, update server.cfg |
| DB user/password | new user with least privilege (no `GRANT`, no `FILE`), update `mysql_connection_string` |
| txAdmin | remove unknown accounts in Admin Manager (check `txData/admins.json`), reset passwords, revoke `all_permissions` |
| Discord webhooks / bot tokens | delete & recreate / reset token |
| `sv_tebexSecret` | regenerate in Tebex panel |
| Fivemanage / other API keys | regenerate in their dashboard |
| SSH / RDP / SFTP / panel | new keys/passwords from a clean device; enable 2FA where offered |
| `rcon_password` | remove it |

## 13. Supply chain — summary
- Install resources only from original authors (GitHub releases, Cfx Portal/Tebex purchase). Leaks and "free premium" packs are the main carrier of Cipher/Blum-family backdoors.
- Before installing: `python scripts/audit.py <resource>` and the full [audit-checklist.md](audit-checklist.md) §2 (signatures, IOCs, remediation).
- Keep `resources/` and `server.cfg` in Git: injected `server_scripts`, new `.js` droppers and edited txAdmin files show up as diffs.
- Never call obfuscated or escrowed code "safe".

## 14. Hosting, DDoS and txAdmin hardening
- **Network:** host with upstream DDoS mitigation that understands FiveM UDP/TCP 30120; expose only 30120 (UDP+TCP). Keep MySQL (3306) bound to `127.0.0.1`/private network. txAdmin (TCP 40120, `TXHOST_TXA_PORT`) behind a firewall allow-list, VPN or TLS reverse proxy — not open to the world.
- **IP hiding:** proxy/CDN setup with `sv_forceIndirectListing true`, `sv_listingHostOverride`, `sv_endpoints`, `sv_proxyIPRanges` (docs "Proxy setup"). Hiding the IP after it is already known is of limited value; change IP if needed.
- **OS:** run FXServer as a dedicated non-admin user (never Administrator/root), no browsers or personal accounts on the game host, egress allow-list (DB, Cfx, Discord, Fivemanage, Tebex), automatic OS updates, offsite DB backups with restore tests.
- **Artifacts:** stay on Recommended (35245 at baseline); clients cannot join builds older than the support window (versions.md).
- **txAdmin:** least-privilege permissions (`players.kick` vs `all_permissions`, `console.write`, `server.cfg.editor`, `commands.resources` are high-risk); remove ex-staff immediately; review `admins.json` for unknown accounts; keep `TXHOST_API_TOKEN` undefined (endpoint disabled) unless needed; reinstall txAdmin from an official release after any compromise (backdoors patch `monitor/resource/*.lua`).
- **Cfx.re / Discord accounts** of owners and staff: unique passwords and 2FA (forum/Portal 2FA availability: **UNVERIFIED** for every account type).

## 15. Exploit classes → defence
| Class | Typical cause | Defence |
|---|---|---|
| Event spoofing | net event trusts args/`source` assumptions | five checks (§2), intent-only events |
| Money / item injection | client sends price/amount/reward | server-side prices, whitelists |
| Dupes | grant-before-verify across a yield, yields without locks, disconnect mid-swap, drops/stashes race | take/verify first, per-player lock, transactions, idempotency ledger, keep ox_inventory updated (§16) |
| Callback data leak | callback returns other players' data | return only caller's own data |
| NUI injection / XSS | `innerHTML` with player text | escape, framework rendering |
| State bag abuse | trusting client-written bags | `sv_stateBagStrictMode`, server tables |
| Entity spawn spam / blacklisted models | client-created networked entities | `sv_entityLockdown` (`relaxed`; `strict` if all spawns are server-side), `entityCreating` filter (anticheat.md) |
| Explosion / ptfx / projectile spam | game events routed unchecked | cancel/whitelist `explosionEvent`, `ptFxEvent`, `startProjectileEvent` |
| Remote weapon give/remove, task clearing | `giveWeaponEvent`, `removeWeaponEvent`, `clearPedTasksEvent` on other players | cancel from clients (anticheat.md) |
| Damage manipulation | modified damage values | `weaponDamageEvent` checks, server-side health logic |
| Control theft of others' vehicles | request-control events | `sv_filterRequestControl` |
| SQL injection | concatenated / template SQL | placeholders; oxmysql ≥ 2.14.0 |
| Backdoor / RCE | leaked resources, panels | audit, provenance, Git diffs, egress filter |
| txAdmin takeover | weak/shared passwords, open 40120, tampered monitor files | §14, reinstall after compromise |

## 16. 2026 dependency advisories
| Package | Version | Issue | Action |
|---|---|---|---|
| oxmysql | 2.14.0 (2026-04-25) | mysql2 update resolves "an sql injection exploit due to another dependency (sqlstring)" | use ≥ 2.14.0 (baseline 2.14.3); still never build SQL strings |
| ox_inventory | 2.46.0 (2026-05-03) | dupe: incorrect data passed to newly created drops; adds `LogExploit` | update |
| ox_inventory | 2.46.1 | correction to swapItems exploit check | update |
| ox_inventory | 2.47.0 (2026-05-14) | inventory-state modification during actions; stash `instance` field (secure only with strict state bags); post-hook events | update; move side effects out of hooks |
| ox_inventory | 2.47.6 (2026-06-06) | dupe exposed by 2.47.3 swapItems delay; disconnect mid-swap; crafting locks | update (baseline 2.48.0) |
| ox_lib | 3.37.0 / 3.37.1 (2026-06) | startup **security advisory** when `sv_stateBagStrictMode` is off; opt-out convar `ox:ignoreSecurityAdvisory` | enable strict mode rather than silencing |

## 17. Review checklist
- [ ] Every server `RegisterNetEvent`/callback captures `source` and validates identity, permission, distance, arguments and rate.
- [ ] No price, amount, reward, coordinates or item name trusted from the client without a server whitelist.
- [ ] Yield/return contracts verified, conflicting operations serialized by their owner, session tokens rechecked, every mutation/compensation result handled, durable operation recovery where needed.
- [ ] Sensitive server exports check `GetInvokingResource()`.
- [ ] Placeholders only in SQL (Lua and JS).
- [ ] No secrets/webhooks in client/shared files or `setr`/`sets`.
- [ ] No `load`/`loadstring`/`eval`/`new Function`/`os.execute`/`io.popen`/`child_process`; no obfuscated code.
- [ ] Admin actions gated by ACE/framework permissions on the server.
- [ ] Entities spawned server-side; `sv_entityLockdown relaxed` (or `strict` if no client-created ambient population is needed), `sv_stateBagStrictMode true` tested.
- [ ] Game-event filters in place (anticheat.md).
- [ ] NUI escapes player text; focus released.
- [ ] Logs + alerts server-side; webhook batched with `allowed_mentions`.
- [ ] txAdmin least privilege; ports firewalled; FXServer non-admin user.
- [ ] `scripts/audit.py` run; every high/critical resolved or justified.

## 18. Sources
- Secure your events: https://docs.fivem.net/docs/developers/server-security/
- Server events (entityCreating, ptFxEvent, weaponDamageEvent, startProjectileEvent fields): https://docs.fivem.net/docs/scripting-reference/events/server-events/
- OneSync / entity lockdown modes: https://docs.fivem.net/docs/scripting-reference/onesync/
- State bags: https://docs.fivem.net/docs/scripting-manual/networking/state-bags/
- Convars (set/setr/sets): https://docs.fivem.net/docs/scripting-reference/convars/
- Server commands (sv_pureLevel, sv_entityLockdown, sv_filterRequestControl, sv_requestParanoia ...): https://docs.fivem.net/docs/server-manual/server-commands/
- Proxy setup: https://docs.fivem.net/docs/server-manual/proxy-setup/
- FXServer source (convars, rate limiters, game events): https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/state/ServerGameState.cpp · https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/src/packethandlers/ServerEventPacketHandler.cpp · https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/include/OneSyncVars.h
- State bag strict mode commit: https://github.com/citizenfx/fivem/commit/49943778302c52a1ca79ef3e18f9788ada788fbf
- ox_lib releases (3.37 advisory): https://github.com/overextended/ox_lib/releases
- ox_inventory releases (2.46–2.47.6): https://github.com/overextended/ox_inventory/releases
- oxmysql 2.14.0: https://github.com/overextended/oxmysql/releases/tag/v2.14.0
- txAdmin permissions / env config: https://github.com/citizenfx/txAdmin/blob/master/docs/permissions.md · https://github.com/citizenfx/txAdmin/blob/master/docs/env-config.md
- ox_inventory shop order (check, add, then remove with no yield): https://github.com/overextended/ox_inventory/blob/main/modules/shops/server.lua
- oxmysql rollback only on SQL error: https://github.com/overextended/oxmysql/blob/main/src/database/rawTransaction.ts · INSERT IGNORE semantics: https://mariadb.com/kb/en/insert-ignore/
- ACE self-modification guard: https://github.com/citizenfx/fivem/blob/master/code/client/citicore/se/Security.cpp · RCON: https://github.com/citizenfx/fivem/blob/master/code/components/citizen-server-impl/include/outofbandhandlers/RconOutOfBand.h
- NUI `quit` native: https://github.com/citizenfx/fivem/blob/master/code/components/nui-core/src/NUICallbacks_Native.cpp
- Blum Panel advisory (Cfx forum, 2026-07-21): https://forum.cfx.re/t/warning-blum-panel-blum-panel-me-warden-panel-me-is-a-malicious-backdoor-remote-code-loader-hidden-in-resources/5415839
