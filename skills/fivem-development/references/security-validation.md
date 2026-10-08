# Validate entry points, privileged operations and failure behavior

Use when creating or auditing events, callbacks, exports, commands or functions
that access protected data or mutate gameplay state. Combine with `security.md`
and the ownership/failure model in `design-and-validation.md`. Reviewed 2026-10-08.

## Map entry points to effects

For each relevant operation, record:

`entry point -> authenticated actor -> authorization -> bounded intent -> owner -> effect -> persistence/result`

Follow indirect helper calls, bridge exports, hooks and delayed jobs. Searching
for `AddMoney` alone misses direct SQL, inventory metadata, `SetMoney`, account
overwrites and alternative entry points into the same function.

| Boundary | Identity and authorization | Common bypass to investigate |
|---|---|---|
| Client-to-server net event | Capture engine-provided `source` before yielding; resolve current character | Actor/target/price/job passed in the payload |
| Framework / library callback | Verify the installed callback's source argument contract | Assuming a callback is private because it returns a value |
| Server-local event / export | Verify intended resource caller, validate arguments, enforce owner contract | Trusted wrapper forwards untrusted input into a privileged helper |
| Command | Server-side permissions; explicit console/source-0 behavior | Client menu visibility or command suggestions used as authorization |
| NUI callback / client export | Client presentation only; real action reaches validated server endpoint | Browser data or client checks authorize a payout |
| State-bag change | Compare with authoritative server-owned state | Treating replication intent, bag ownership or client-written job as privilege |
| HTTP endpoint | Authenticate caller, authorize operation, cap body/work, protect credentials in transport | Public handler indirectly invokes admin/economy functions |
| Timer / lifecycle / hook | Capture stable identity and operation context; recheck current state | Late callback acts on reused player source, entity ID or character session |

`AddEventHandler` does not itself network-register an event. Check whether the same
event is network-enabled elsewhere in its resource. Server exports are not directly
network endpoints, but server resources can invoke them. A caller allow-list narrows
accidental access; it cannot isolate the economy from arbitrary malicious server code.
Random event names, client-held tokens, obfuscation and an anticheat are not substitutes
for server authorization. A local function is not secure merely because it is `local`.

## Define an operation contract before writing a payout

- **Actor and subject:** resolve the caller's current character from trusted runtime
  context. A target player/account/vehicle/stash is a separate subject requiring
  ownership or permission checks. A persistent character ID is not a session token.
- **Eligibility:** use server-owned job/grade, mission state, permissions, item
  definitions, prices and reward limits. Validate entity existence/type/business ID
  and routing bucket when applicable. Server-observed positions still incorporate
  client sync; proximity alone does not prove a legitimate completed activity.
- **Input:** reject invalid types, non-finite numbers, fractions where integer counts
  are required, negative/zero amounts, excessive counts and overflow before arithmetic.
  Bound strings, collections, depth and payload work. Whitelist metadata keys and
  identifiers; SQL placeholders bind values, not arbitrary table/column names.
- **Capacity:** cheap rejection and per-session/action rate limiting precede expensive
  queries. Bound total in-flight work, queues and limiter storage; a lock is not a
  rate limiter. Fixed server-defined action names prevent unbounded limiter keys.
- **Concurrency:** serialize conflicting writes through the actual data owner; claim
  uniqueness in storage when several resources/processes participate. A resource-local
  `busy` flag cannot protect another writer. Verify which calls yield internally.
- **Persistence:** decide when success can be acknowledged. Memory-only deduplication
  does not survive resource/server restart. Check every mutation's documented result;
  `nil`, exception, timeout and definitive rejection may mean different things.
- **Recovery:** after a yield, validate session/generation before further effects.
  Keep settling operations attributable after disconnect; release only the current
  operation's lock. Recovery must work after restart, not just during a callback.

## Idempotency without a false atomicity claim

A client request ID can identify a retry; it does not authorize an action. Bind it
to actor, operation type and normalized payload. Reusing the key for different data
must fail. A server-created activity ID must identify one persisted activity instance;
`netId + current second` alone is not reliably unique across reuse/restarts.

For one DB-owned account system, an operation's unique claim, conditional debit,
credit and final result can share a single transaction on one connection. Check
affected rows; zero-row business failure is not necessarily a SQL error. Verify
engine/driver behavior with real integration tests, including lost acknowledgments.

For separate inventory/framework owners, inserting a ledger row and then calling
`AddItem` does **not** make the grant atomic. An interruption between effect and
result recording leaves an unknown outcome. Require an owner-supported idempotent
operation or an evidence-backed reconciliation/compensation design. A current
balance or count alone may not identify whether this particular operation applied.

Useful persistent states are `PENDING`, `APPLIED`, `REJECTED` and `UNKNOWN`, with
operation identity, actor, payload binding and owner receipt/version when available.
Only a confirmed non-application can be rejected safely; an unknown effect must
not be silently retried or refunded. Document how recovery resolves each state.
These are application design states, not an invented framework API.

## Adversarial acceptance matrix

Run against isolated fixtures or a staging server owned/authorized for testing.
Adapt cases to the requested operation; do not send exploit traffic to third parties.

| Case | Expected observable result |
|---|---|
| Legitimate action | Exactly the intended effect, accurate response and durable result |
| Forged price/reward/job/actor/target | Rejected or ignored as designed; unauthorized balance/item delta is zero |
| Negative, zero, fractional, NaN/infinite, huge number | Rejected before mutation/DB work; no arithmetic wraparound |
| Oversized/deep payload or arbitrary metadata | Bounded rejection; no unbounded allocation, log or query work |
| Missing/deleted/wrong-owner entity or wrong bucket | No effect on another player's object or account |
| Remote completion, missing start, replayed activity | No reward without server-established eligibility |
| Duplicate request and same key/different payload | Original result reused or request rejected; no second effect |
| Two simultaneous requests; two actors accessing one stash | Inventory/money invariants hold under actual interleaving |
| Disconnect/reconnect or character switch during await | No grant to the new session; old operation remains recoverable |
| Inventory full; debit/grant/refund returns false | Outcome follows the verified adapter contract; no unchecked compensation |
| Exception/timeout after owner may have applied effect | Unknown recorded; no blind retry or success acknowledgment |
| Restart between claim, effect and result | Recovery resolves using durable evidence; no duplicate grant |
| DB rollback/deadlock/lock timeout/lost commit response | Correct classification; retry only if rollback and operation safety are established |
| Sustained spam and disconnect churn | Bounded handlers, queues, limiter memory and sampled denial logs |
| Alternate export/callback/command reaches same helper | Same protected invariants; wrapper cannot bypass owner checks |

Economic checks must assert invariants, not only a response string: conservation
for transfers, authorized issuance for rewards, non-negative bounded balances,
single ownership, and no double consumption. Inject a failure at each effect boundary.
Runtime-less adapter tests validate logic; they do not prove actual framework,
inventory, transport or DB semantics.

## Report coverage and evidence

For each finding record file:line, reachable entry point, actor privileges, effect,
reproduction or reasoning, severity, fix and regression test. Mark paths as reviewed,
logic-tested, integration-tested or unavailable. `audit.py` is a heuristic triage
tool, not a control-flow proof or complete exploit detector. No findings is not a
security certification. Escrow/opaque paths remain an explicit coverage limitation.

## Primary sources

- Cfx.re event contexts and server checks: https://docs.fivem.net/docs/developers/server-security/
- Cfx.re state-bag policy and handler semantics: https://docs.fivem.net/docs/scripting-manual/networking/state-bags/
- Lua numeric behavior: https://www.lua.org/manual/5.4/manual.html#3.4.1
- Driver transaction contract: https://github.com/overextended/oxmysql/blob/fa4f3d3fb75751dafccad42ede5d22a1e2f810aa/src/database/startTransaction.ts

The operation contract and test matrix are engineering recommendations derived
from these boundaries; they are not a claim that Cfx.re guarantees transactional
behavior across independently owned frameworks and inventories.
