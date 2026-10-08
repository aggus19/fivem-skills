# Diagnose hitches, delayed actions and database latency

Use for hitch warnings, intermittent lag, slow callbacks/saves or unexplained
performance regressions. Read the affected performance/DB reference after identifying
the subsystem. Documentation/source review: 2026-10-08; no runtime benchmark implied.

## What the warning establishes

In the reviewed Legacy FXServer source, the warning reports elapsed time between
thread timer callbacks. It is not a query duration, a player's ping, or necessarily
time spent executing one Lua function. Work on the thread, scheduling delays and
host contention can all contribute. It does not identify the guilty resource.

| Message | Reviewed warning threshold | Impact to investigate |
|---|---|---|
| `server thread hitch warning` | Interval > 150 ms | Delayed script/event processing and gameplay responses |
| `network thread hitch warning` | Interval > 150 ms | Delayed network servicing |
| `sync thread hitch warning` | Interval > 100 ms | Delayed entity synchronization/scoping |

These thresholds are source-specific diagnostics, not recommended operating targets.
Check the deployed artifact and edition; do not apply a Legacy threshold to Enhanced
without matching evidence. A timer interval includes scheduling cadence and is not
interchangeable with a histogram of time executing work. Low total CPU can hide one
saturated core. A client FPS drop can occur with a healthy server and no hitch logs.

Frequent or long stalls can cause delayed actions and uneven synchronization;
effects depend on the affected thread and workload. Separate isolated startup/asset
loading stalls from recurring in-game problems. Hiding the warning changes no work.

## Capture a useful baseline

1. Save exact warning text/timestamps, artifact/edition, affected actions and actual
   concurrent players/entities. Record startup, joins, mass saves, scheduled jobs,
   backups and recent changes; align timestamps between FXServer, DB and host.
2. Capture the affected interval in the **server console**, using the documented
   commands below. Record long enough to include the symptom; frame counts do not
   imply a fixed duration across client/server or editions.

   ```text
   profiler record 500
   profiler status
   profiler saveJSON hitch-before.json
   profiler view
   ```

3. For client stutter, use client F8 `resmon 1` and a client profile. For UI issues,
   inspect NUI/CEF tasks, message volume and rendering; client resource timing alone
   does not describe all GPU, streaming or browser work.
4. Correlate server traces with per-core CPU, runnable/contending processes, memory
   pressure/page faults, storage latency and network queues. Use OS tools available
   on that host. Add DB query digests/slow logs, lock waits and connection/pool queues
   only where the evidence points to DB work.

Preserve before/after captures and configurations. Profiling and verbose SQL logging
add overhead; keep the same instrumentation when comparing and stop temporary logging
after capture. Restrict access to logs that contain query parameters or player data.

## Test competing explanations

| Observation | Evidence that distinguishes causes | Candidate change to test |
|---|---|---|
| One long script slice | Stack/line and input size in the captured stall | Bound work, reduce repeated serialization/search, chunk non-atomic processing |
| Periodic spike across resources | Timers/autosaves align; work volume and queue growth | Stagger bounded jobs, batch writes safely; retain dirty state until acknowledged |
| Slow action, healthy tick times | Separate pool wait, SQL execution, round trips, owner callback and response | Fix the measured latency component; do not diagnose a main-thread stall from delay alone |
| Fast SQL but large result processing | Rows/bytes returned, JSON work and resumed continuation slices | Select needed columns/rows, paginate, reduce result size and redundant decode/encode |
| Slow SQL / lock contention | Query plan/digest, rows examined, blocking transactions, storage latency | Index/query redesign or shorter transaction; test correctness and write cost |
| Connection queue rises | Busy pool, DB saturation and arrival/completion rate | Bound admission first; change pool only with DB headroom and a measured comparison |
| Many threads stall together | Host scheduling/CPU contention, paging, backup/storage activity | Address host contention; compare isolation or schedule under the same workload |
| Sync/network warning with light scripts | Entity density, scoping changes, replication/event bytes, thread/host metrics | Reduce unnecessary entities/broadcasts/updates while preserving required behavior |
| FPS drops only with UI/asset | Client/CEF capture, frame times, streaming/VRAM and scene | Fix rendering/message frequency or asset budget; server DB tuning is unproven |

`await` yields the calling coroutine. Query latency can cause queues and bursty
continuations, but a 300 ms async query does not prove svMain blocked for 300 ms.
Conversely, a fast query returning thousands of rows can trigger expensive script
processing. Slow SQL and hitches can share a third cause, such as storage contention.

Use controlled resource isolation in staging when traces are inconclusive. Stop
dependent systems together as needed; restarting a live framework/inventory is not
a safe profiling experiment. Synthetic load must model relevant events, entities
and data; empty connected slots alone are not a representative RP workload.

## Decide whether a change helped

Compare equivalent scenarios: idle, normal interaction, dense area, join burst,
periodic save and prolonged operation where relevant. Record versions/configuration,
hardware, data set, warm/cold cache, duration, concurrency, samples and repeat runs.
Track task latency p50/p95/p99, tick work/interval separately, hitch count/severity,
CPU/memory, network bytes, SQL timings and queue depth as appropriate. State sample
size; a p99 from very few observations is weak evidence.

Accept a change only if the target metric improves beyond observed run variation
without violating response, durability or gameplay constraints. Include correctness
checks (no lost saves, duplicates or stale authorization). If no representative run
is possible, report the causal hypothesis and **unmeasured**, with a concrete test.
There is no universal ideal ms value for every resource or DB query.

Avoid blanket fixes: `Wait(0)` to `Wait(1000)` where drawing is per-frame, increasing
connection pools without capacity, removing authorization checks, relaxing transaction
durability, deleting logs to hide a symptom, or migrating engines based only on version.

## Primary sources

- Legacy timer intervals and thresholds, pinned source reviewed 2026-10-08:
  https://github.com/citizenfx/fivem/blob/e4c0e0813cc4386928db85befff997a1f6b56abc/code/components/citizen-server-impl/src/GameServer.cpp
- Profiler command contract: https://docs.fivem.net/docs/scripting-manual/debugging/using-profiler/
- Client console tools: https://docs.fivem.net/docs/client-manual/console-commands/

The diagnostic matrix is a set of hypotheses and experiments, not measured results
for the user's server. DB-specific inspection and safe tuning: `database-optimization.md`.
