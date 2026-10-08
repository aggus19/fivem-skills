# Performance at scale: large servers, OneSync limits, network, hardware, streaming budgets

Baseline: FXServer Legacy 35245 (Recommended) / 37150 (Latest), Cfx Server (Enhanced, early access) build 161, OneSync forced on — verified 2026-10-07 against citizenfx/fivem source (master `a74c2cc`), docs.fivem.net, fivem.net and forum.cfx.re. Script-level optimisation: [performance.md](performance.md). Code recipes: [performance-cookbook.md](performance-cookbook.md).

Labels: **[source]** = read in FiveM source code; **[docs]** = official Cfx.re docs/posts; **[community]** = forum/hosting-provider advice, anecdotal; **UNVERIFIED** = could not confirm.

## Contents
1. How FXServer spends its time
2. Player slots and licensing
3. OneSync convars that affect performance
4. Entities, population and culling
5. Network and bandwidth
6. Hardware sizing
7. Linux vs Windows, artifacts
8. Streaming asset budgets
9. Standard server values
10. Restart strategy and operations
11. Practices from large servers (labelled)
12. Scaling checklist
13. Sources

## 1. How FXServer spends its time
| Thread | Timer **[source]** | Hitch warning | What runs there |
|---|---|---|---|
| svMain | 20 Hz (50 ms) | > 150 ms "server thread hitch warning" | All server scripts (Lua/JS/C#), events, resource ticks |
| svNetwork | 100 Hz (10 ms) | > 150 ms "network thread hitch warning" | ENet packet I/O |
| svSync | 120 Hz (~8 ms) | > 100 ms "sync thread hitch warning" | OneSync: entity state, scoping, culling, population |

- Scripts share **one** main thread. More cores do not make Lua faster; a single slow handler delays every player's events. Hence: **single-thread CPU speed is the main hardware factor [community, consistent with the threading model]**.
- Entity send cadence on Legacy **[source, `ServerGameState.cpp`]**: base 50 ms per entity per client; with `onesync_radiusFrequency` (default on) non-player/non-vehicle entities get 150 ms when outside the player's view frustum, 250 ms beyond 250 m, 500 ms beyond 500 m, and 50/4 = 12.5 ms closer than 35 m.
- Dev Update #3 **[docs]**: Legacy OneSync sends "30" updates/s ("40 with `sv_useAccurateSends`"); Enhanced is configurable "up to 120". Legacy entity culling "ran on the sync thread and could only process around 16 players per tick"; Enhanced spreads it across cores and claims "reducing RAM usage by up to 50%".
- Measure with txAdmin's svMain/svSync/svNetwork histograms or Prometheus `/perf/` ([performance.md §1](performance.md)).

## 2. Player slots and licensing
- `sv_maxClients` 1–2048 **[docs]**; above 48 slots needs an Element Club tier **[docs, fivem.net/server-hosting]**:

| Tier | Price | Slots |
|---|---|---|
| none | free | up to 48 |
| Argentum | $15/mo + VAT | up to 64 |
| Aurum | $25/mo + VAT | 64 OneSync / 128 "OneSync Infinity" |
| Platinum | $50/mo + VAT | 128 OneSync / **2048** "OneSync Infinity" |
(The page still distinguishes OneSync vs Infinity; since 2026-08 OneSync is forced on in big/"infinity" mode.)
- Enhanced: `sv_devMode true` limits the server to **8 slots** **[docs]**. Cfx.re ran public Enhanced stress tests on 2026-08-14 and 2026-09-04 with slot capacity "gradually increased" (forum t/5420662); **no official results were published** in that thread as of 2026-10-07 — do not quote numbers from them. Cfx.re states the goal of going "beyond the current 2,048-player cap" (Dev Update #3).

## 3. OneSync convars that affect performance
Defaults verified in `ServerGameState.cpp` / docs. Change only with measurements.

| Convar | Default | Effect |
|---|---|---|
| `onesync` | on (forced) | `legacy` mode no longer selectable on current builds |
| `onesync_population` | true | NPC/traffic population. **Read-only at runtime** — `set onesync_population false` in server.cfg before start. Per bucket: `SetRoutingBucketPopulationEnabled` |
| `onesync_distanceCulling` | true | Drop entities from sync beyond culling radius and outside view |
| `onesync_distanceCullVehicles` | false | "Can improve performance by reducing vehicle sync frequency" |
| `onesync_radiusFrequency` | true | Distance/frustum-based send cadence (§1). "Disabling may improve performance at the cost of distant entity accuracy" |
| `onesync_forceMigration` | true | "Disabling may improve performance but can leave entities without an owner" |
| `sv_useAccurateSends` (Legacy) | true | Deprecated on Enhanced → `sv_syncTickRate` |
| `sv_syncTickRate` (Enhanced) | 60 (1–120) | "Higher values can reduce latency but increase CPU usage" |
| `sv_ioThreads` (Enhanced) | 0 = cores clamped 2–4 | Network I/O threads, startup only |
| `sv_pingIntervalMilliseconds` (Enhanced) | 5000 | Keep-alive; lower = more bandwidth |
| `onesync_migrateDataTimeout` (Enhanced) | 10000 ms | Force migration after owner stops sending |
| `sv_entityLockdown` | inactive | `strict`/`relaxed` stop client-created entity spam (security + entity count) |
| `sv_filterRequestControl` | 0 | Filter `REQUEST_CONTROL_EVENT` routing |
| `sv_enableNetworkedSounds` | true | Set false to stop clients routing `NETWORK_PLAY_SOUND_EVENT` |
| `sv_netEventReassemblyMaxPendingEvents` | 100 | Per-client pending large events (memory) |
| `rateLimiter_<name>_rate/_burst` | see performance.md §8 | Client event/state bag flood limits |

**Advice**: the defaults are tuned by Cfx.re; the "secret performance convars" lists circulating on forums (`sv_maxupdaterate`, `sv_priority1`, `sv_maxPacketSize` …) were challenged by forum replies as non-existent or ineffective **[community, forum t/5260917]** — don't copy them.

## 4. Entities, population and culling
- Object ID space: **65535** network objects (`MaxObjectId = (1 << 16) - 1`, "extension of object id length from 8192") **[source + docs]**. In practice game pools on each client fill long before that: check `net_showPools 1` on a client when you see entity-creation failures.
- Default culling radius **424 units** **[source + docs]**. `SetPlayerCullingRadius` / `SetEntityDistanceCullingRadius` are **deprecated with "known, unfixable issues"** — design around scope instead (e.g. send data via events/state bags, not by forcing entities into scope).
- Population (ambient peds/traffic) is the largest entity source on busy servers. Options, cheapest first: `onesync_population false` (no NPCs, lowest sync load); keep it on but lower density in **one** client resource (`SetPedPopulationBudget`/`SetVehiclePopulationBudget` once, or density `*ThisFrame` multipliers in a single thread); disable per routing bucket for instances.
- Server-created persistent entities (garages, jobs, props) survive owner changes and accumulate: track them, despawn unused vehicles after a timeout, delete on resource stop. `SetEntityOrphanMode` controls deletion when the owner leaves.
- Routing buckets isolate instances (apartments, races): entities and population per bucket; `SetRoutingBucketEntityLockdownMode(bucket, 'strict')` for buckets that need no client entities.
- Enhanced: player join/leave scope events only when in range; player IDs are reused — never key data on server ID **[docs]**.

## 5. Network and bandwidth
- Cfx.re's hosting page asks for "decent upstream connectivity" **[docs]**; no official per-player bandwidth figure exists. Sync traffic grows with players **in scope of each other** (O(n²) in dense areas), so a 300-player server with everyone in Legion Square is far worse than 600 spread across the map.
- Biggest script-controlled costs: broadcasts to `-1`, large GlobalState, frequently changing player state bags (replicated to everyone in scope), voice. Keep event payloads < a few KB; use latent events above that.
- Join burst: every connecting client downloads all changed resources/streams from the server (or your file server/CDN if configured). Big streaming packs dominate join time **[community]**.
- Ensure `net_tcpConnLimit` (default 16 per IP) suits proxies/load balancers **[docs]**.
- DDoS/edge protection: a provider-level UDP filter is common on large servers; `sv_forceIndirectListing` + `sv_listingHostOverride` keep the real address off the server list (`sv_endpointPrivacy` was removed 2026-07-08).

## 6. Hardware sizing
Official minimum **[docs, fivem.net/server-hosting]**: "x86-64 system running Linux or Windows", "multi-core processor is preferred", "decent upstream connectivity". There is **no official sizing table**. Practical guidance:

| Players | CPU | RAM | Disk | Source |
|---|---|---|---|---|
| ≤ 64 | modern desktop-class core, high boost clock | 8–16 GB | NVMe | **[community]** |
| 64–256 | top single-thread CPU (current Ryzen 7000/9000 or Intel Core class, ≥ 5 GHz boost) | 32–64 GB | NVMe, DB on NVMe | **[community, hosting guides]** |
| 256–1024+ | same per-core speed priority; dedicated (not shared vCPU) | 64–128 GB | NVMe RAID1; DB often on a separate host | **[community]** — UNVERIFIED for 1000+ |

- Priority order: single-thread speed > dedicated cores (no noisy neighbours / CPU steal) > RAM > NVMe for MySQL/MariaDB > network.
- Avoid low-clock many-core server CPUs and oversold VPS vCPUs for the game server; they are fine for the database or web panels **[community]**.
- Put MySQL/MariaDB on fast NVMe with enough buffer pool; a slow DB shows up as svMain stalls only if you `await` in hot paths — see `database-optimization.md`.
- Load-test with your actual resource set; resource code matters more than hardware.

## 7. Linux vs Windows, artifacts
- Both are supported **[docs]**. Forum users report little real-world difference; Linux avoids licence cost **[community, t/369087, t/1041950]**. Vendor benchmarks claiming large CPU/RAM savings are unverified marketing.
- Choose the OS your team operates confidently (backups, updates, txAdmin as a service).
- Artifacts: run **Recommended** in production; test **Latest** on staging. Clients cannot join servers on builds older than the support window (cut-off 2026-10-15 for pre-35245 builds) — see [versions.md](versions.md) and [server-ops.md](server-ops.md). Performance fixes land in artifacts first; staying current is itself an optimisation.
- Enhanced (Cfx Server) is early access: lower RAM and higher sync rate are claims from Dev Update #3, not yet a reason to move production servers.

## 8. Streaming asset budgets
Server warnings when a resource starts **[source, `ResourceStreamComponent.cpp`]** — checked separately for **physical** (GPU/graphics) and **virtual** (system) memory of each RSC asset:

| Size of one asset | Console colour | Message |
|---|---|---|
| > 16 MiB | ^4 | "Asset res/file uses N MiB of physical/virtual memory." |
| > 32 MiB | ^3 (yellow) | same |
| > 48 MiB | — | adds "Oversized assets can and WILL lead to streaming issues (such as models not loading/rendering)." |
| > 64 MiB | ^1 (red) | same, highest severity |

- Treat **16 MiB per asset** as the practical ceiling; split or downscale anything above.
- Client convars **[source, `TextureStreamingLimits.cpp`]**: `str_maxVehicleTextureRes` default **1024** and `str_maxVehicleTextureResRgba` default **512** — vehicle textures above that are mip-limited on the client anyway, so 4K vehicle textures only waste download size and memory.
- Textures: 2048 px max for most assets, 1024 for vehicles/clothing; DXT1/DXT5 (BC1/BC3) compression; real mipmaps; no uncompressed A8R8G8B8 except tiny UI.
- Texture loss = client streaming/VRAM budget exhausted. Server side: fewer and smaller assets, no duplicate YTDs across resources, LODs on MLOs. Client side: in-game "Extended Texture Budget" setting **[community]**.
- Join time and memory scale with total streamed content: hundreds of add-on cars and clothing packs are the usual cause of slow joins and crashes **[community]**. Prefer fewer, curated packs; consolidate tiny resources (each resource adds manifest/metadata overhead) **UNVERIFIED magnitude**.
- Enhanced uses `stream_enhanced/`; Legacy assets must be converted with Alchemist ([gta5-enhanced.md](gta5-enhanced.md)). MLO/vehicle specifics: [mapping-streaming.md](mapping-streaming.md).

## 9. Standard server values
| Item | Good value | Reasoning |
|---|---|---|
| svMain tick p95 | < 10 ms | 50 ms budget; leaves room for spikes |
| Any hitch | none in normal play | > 150 ms = everyone lags |
| Server periodic loops | ≥ 1 s, staggered offsets | avoid all resources working on the same tick |
| Player save | every 5–15 min + on drop + on txAdmin shutdown | DB load vs data loss |
| Entity cleanup sweep | every 5–10 min | despawn abandoned vehicles/props |
| `onesync_population` | false for RP with scripted NPCs; true with lowered density otherwise | population is the largest sync load |
| `sv_entityLockdown` | `relaxed` or `strict` when all spawns are server-side | stops client entity spam |
| Enhanced `sv_syncTickRate` | 60; 90–120 only if svSync has headroom | latency vs CPU |
| Culling radius | default 424 | culling natives deprecated |
| Asset size | ≤ 16 MiB physical and virtual each | warning threshold |
| Vehicle textures | ≤ 1024 px | client mip-limits above that |
| Scheduled restarts | 1–4 per day | clears leaks, entity build-up **[community]** |

## 10. Restart strategy and operations
- txAdmin scheduled restarts with in-game warnings; listen to `txAdmin:events:scheduledRestart` / `txAdmin:events:serverShuttingDown` to flush saves ([server-ops.md](server-ops.md)).
- Don't `restart` stateful resources (framework, inventory) live in production; restart the whole server in a window.
- If memory or svMain time grows over hours, find the leak ([performance.md §10](performance.md)) instead of only restarting more often.
- Watch: txAdmin perf chart (svMain p95), FXServer memory, Prometheus `/perf/` with Grafana for history and alerts, oxmysql slow-query log.
- Stage changes: copy of the server + bots/players, profiler capture before/after, then deploy.

## 11. Practices from large servers (labelled)
- Interactions through ox_target / zones; no resource with an always-on `Wait(0)` loop **[community consensus, ox_lib design]**.
- One "population/density" resource for the whole server; NPC-heavy jobs spawn server-side on demand and despawn.
- Instances (housing, heists) in routing buckets with population disabled.
- Phone/inventory/HUD NUIs hidden when closed; HUD updates on change at ≤ 10 Hz.
- Database on its own NVMe-backed host or managed instance for 300+ players; read-heavy data cached in memory at start **[community]**.
- Voice: pma-voice/Mumble settings (grid/range) affect bandwidth; test at target population **[community]** **UNVERIFIED magnitudes**.
- Avoid escrowed resources you can't profile/fix when they show in resmon; ask the vendor for numbers.
- No reliable public case studies with measured numbers for 1000+ player FiveM servers were found; treat any "X players on Y hardware" claim as anecdotal.

## 12. Scaling checklist
- [ ] Recommended artifact; staging on Latest.
- [ ] svMain p95 < 10 ms, no hitch warnings at peak (txAdmin chart).
- [ ] Population strategy decided (convar / one density resource / buckets).
- [ ] `sv_entityLockdown` set; all gameplay entities created server-side and tracked.
- [ ] No broadcast > a few KB; GlobalState small; latent events for big data.
- [ ] No asset > 16 MiB; vehicle textures ≤ 1024; no duplicate packs.
- [ ] DB on NVMe, indexed, batched writes; slow-query log clean.
- [ ] Single-thread-fast dedicated CPU; RAM headroom; monitoring with alerts.
- [ ] Scheduled restarts with save hooks; memory flat between restarts.

## 13. Sources
- citizenfx/fivem source (master a74c2cc): `citizen-server-impl/src/GameServer.cpp` (threads, hitch thresholds, tickTime histograms), `state/ServerGameState.cpp` + `include/state/ServerGameState.h` (convar defaults, 424 culling, MaxObjectId, radius frequency), `ResourceStreamComponent.cpp` (asset size warnings), `gta-streaming-five/src/TextureStreamingLimits.cpp`, `PerfHttpHandler.cpp` — https://github.com/citizenfx/fivem
- Server commands / convars: https://docs.fivem.net/docs/server-manual/server-commands/
- OneSync: https://docs.fivem.net/docs/scripting-reference/onesync/
- Legacy vs Enhanced: https://docs.fivem.net/docs/developers/legacy-vs-enhanced/
- Dev Update #3 (sync rate, RAM, culling, metrics, Perfetto): https://forum.cfx.re/t/development-update-3-fivem-for-gtav-enhanced/5415045
- Enhanced stress test calendar: https://forum.cfx.re/t/public-stress-test-calendar-fivem-for-gtav-enhanced/5420662
- Element Club tiers, hardware statement: https://fivem.net/server-hosting
- Culling natives deprecation: https://docs.fivem.net/natives/?_0x8A2FBAD4 · https://docs.fivem.net/natives/?_0xD3A183A3
- Forum guide with disputed convars: https://forum.cfx.re/t/guide-optimizing-fivem-server-performance/5260917
- Linux vs Windows threads: https://forum.cfx.re/t/fivem-server-onesync-windows-or-linux/369087 · https://forum.cfx.re/t/windows-vs-linux/1041950
- txAdmin metrics: https://github.com/citizenfx/txAdmin (`core/modules/Metrics/svRuntime/`)
