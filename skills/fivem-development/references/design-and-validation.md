# Design decisions, failure contracts and evidence

Use for stateful features, asynchronous work, economy, lifecycle changes or optimization. Scale the analysis to the task; a cosmetic edit does not need a transaction design.

## 1. Establish the installed contract

Read the manifest and actual dependencies before choosing APIs. Record framework/inventory versions, FXServer artifact and edition, DB engine and package-manager lockfile when relevant. The dated skill baseline is a lookup aid; installed source and its matching documentation decide compatibility. An unavailable API is a research task, never permission to invent it or migrate the project's stack.

For each external call that affects correctness, verify: runtime side, arguments, return values (including nil/false), exceptions, possible yields, cancellation and restart behavior. An export can yield internally even when the caller contains no `Wait`. A boolean wrapper is only reliable if the underlying API's failure contract supports that interpretation.

## 2. Model ownership and the operation before coding

For the affected data, identify the authoritative owner, persistence owner and replicated view. One component owns a balance/inventory/entity lifecycle; a cache or state bag is not a second authority. Scope SQL to custom tables unless the framework documents direct writes as supported.

For a purchase or timed action, work through:

1. **Identity:** persistent character/account ID, connection/character generation, operation ID. `source`, net IDs and entity handles can be reused; they are not durable identity.
2. **Admission:** authenticated actor, permission/ownership, valid station/bucket, bounded types/quantities, server-owned price/recipe, rate limit.
3. **Interleaving:** where execution may yield; what can change before it resumes; which lock/reservation is shared by *all* writers. A resource-local lock does not serialize another resource.
4. **Mutation:** atomic update/transaction inside one owner where possible. Across owners, explicitly define compensation, unknown outcomes and reconciliation. Verify each return; pre-checking capacity is not reserving space.
5. **Lifecycle:** disconnect, character switch, reused source, entity migration/removal, timeout, cancellation, dependency restart and resource/server restart. A late callback may only clear its own operation token.
6. **Completion:** acknowledge only the confirmed effect. Persist a stable operation result when replay/recovery is required; bind duplicate requests to the same actor and payload. Never generate a new operation ID to retry an uncertain grant.

Useful states: `PENDING → COMMITTING → DONE`, with `CANCELLED` before commitment and `RECONCILE` for partial/unknown effects. Persist the states needed to recover after a crash. A durable `PENDING` row alone does not make inventory exports exactly-once: the inventory owner must support an idempotent operation or a reliable reconciliation path.

## 3. Choose persistence deliberately

| Data | Policy to establish |
|---|---|
| Money, transferable items, vehicle ownership | Owner's durable mutation + operation/ledger contract; confirm atomicity and crash behavior |
| Custom cosmetic/progress counters | Write-behind only with an accepted loss window, bounded queue, serialized writes and acknowledged generations |
| Derived UI/world views | Rebuild from authority; bounded cache, seed on load and resync after missed messages/restart |

The write queue in `assets/examples/versioned_store.lua` retains failed snapshots and newer mutations across yields; its memory is still lost on process crash. The transfer body in `assets/examples/transfer.lua` verifies both accounts and row counts; endpoint authorization, durable idempotency/ledger and real InnoDB tests are still required. Read database-optimization.md for integration.

The generated shop is disabled until its app-specific durable operation/recovery path is wired and its adapters are verified. `RecordRecovery` is an application contract supplied by the project, not an existing FiveM/framework API. Merely flipping `PurchasesEnabled` or adding a print callback does not complete that integration.

## 4. Match claims to tests

| Evidence label | What it establishes | What it does not establish |
|---|---|---|
| Documented | Matching official docs state the contract | Installed behavior or measured performance |
| Source-reviewed | A pinned source revision shows the mechanism | All execution paths or release rollout |
| Logic-tested | Executed assertions/fault injection in a named runtime | FXServer, framework, SQL or network integration |
| Integration-tested | Actual named stack passed recorded scenarios | Other builds, hardware or workloads |
| Measured | Reproducible before/after data with environment and workload | A universal speedup |

Record command/scenario, versions, result and limitations with the change. Mark unexecuted tests explicitly. Do not describe a scaffold as production-ready solely because static scripts pass.

`natives.py` lexically checks Lua names and runtime sides from literal manifests (filename fallback for runtime-loaded modules). It does not prove argument types, conditional branches, JS/TS/C# natives or export contracts. Unknown side is reported. `manifest.py` checks a static literal subset; computed manifests need separate review/runtime metadata. `audit.py` reports candidates, includes shipped build code, and leaves dependencies in node_modules outside its default scope. `--min` only filters display, not failure status. None certifies absence of vulnerabilities.

## 5. Failure cases that should drive tests

- Economy: zero/negative/fractional/NaN/overflow quantity, missing receiver, insufficient funds, failed credit, inventory full, failed refund, exception after a possible mutation, duplicate intent.
- Scheduling: two requests interleaved at each await, two writes to the same key, old callback after a new operation, character switch/source reuse, cancel racing completion.
- Persistence: failed write, overlapping flush, mutation during flush, unload during failure, backpressure, restart with pending operations, commit acknowledgement lost.
- NUI: open before listeners, reload while open, close/stop after a callback failure, aborted fetch, invalid response and repeated messages.
- World: spawn timeout, stream out, owner migration/drop, deleted/reused net ID, repeated cleanup and resource restart with existing entities.

Use unit/fault tests for deterministic invariants and a real FXServer with at least two clients for synchronization/lifecycle acceptance. Simulated players or mocked SQL do not reproduce OneSync behavior or database locks.

## 6. Performance experiment contract

State the bottleneck and expected mechanism before editing. Preserve correctness, gameplay responsiveness and the accepted persistence policy.

- Fix artifact/build, dependency commits, CPU/GPU/RAM, OS, DB version/config, player/entity/point counts, scene, resolution/FPS cap and resource list.
- Compare baseline/candidate after warm-up with repeated runs of equal duration; alternate run order when practical. Keep raw profiler captures/query plans and note variability. Report regressions too.
- Client: script CPU and frame-time distribution/spikes, allocations/memory, native frequency, total effect including shared libraries. Repeat at relevant FPS caps: per-frame work scales with frames.
- Server: svMain/svSync/svNetwork timing, event/request volume, payload bytes, serialization cost, pending work and memory. Distinguish coroutine wait latency from CPU execution.
- NUI: message rate/size, render/JS/compositor activity, hidden vs visible behavior, fetch latency/failures. A hidden React tree does not destroy its CEF instance.
- Database: throughput, p50/p95/p99 latency, rows examined/affected, query plans, lock waits, pool queueing and data-loss/recovery behavior. Fewer queries alone is not proof of a better system.

Include idle, normal interaction, dense activity and failure/restart scenarios. Explain when the alternative loses (latency, memory, correctness or CPU). `0.00 ms` is a displayed/rounded reading, not zero total cost. Hardware-independent numerical targets are guidelines, not acceptance evidence.

## 7. Sources and verification boundary

- Cfx events/security: https://docs.fivem.net/docs/developers/server-security/
- Manifest semantics: https://docs.fivem.net/docs/scripting-reference/resource-manifest/
- Coroutine scheduling: https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/Citizen.Wait/
- Profiling: https://docs.fivem.net/docs/scripting-manual/debugging/using-profiler/
- Transaction implementation reviewed 2026-10-08: https://github.com/overextended/oxmysql/blob/fa4f3d3fb75751dafccad42ede5d22a1e2f810aa/src/database/startTransaction.ts (boolean result does not classify errors).
- Lua logic tests in this repository use `lupa.lua54`; they do not run CfxLua extensions or FXServer. Test-only dependency: https://github.com/scoder/lupa

These are design/validation criteria, not new benchmark measurements or a re-verification of the entire version baseline.
