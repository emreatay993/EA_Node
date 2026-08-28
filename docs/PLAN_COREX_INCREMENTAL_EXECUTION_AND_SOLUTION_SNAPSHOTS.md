# COREX Incremental Execution And Solution Snapshots

## Summary

This plan replaces workspace-wide rerun behavior with one execution-owned solution
state and reuse system. An execution-affecting mutation expires only the changed
node and its enabled downstream dependency closure. Current nodes retain their
settled outputs, and a prepared run invokes node implementations only for nodes
whose solution record is absent, expired, invalid, ineligible, or explicitly
forced to recompute.

The immediate user-visible acceptance case is a disconnected Model Viewer branch:
after its scene and live transport are ready, changing an unrelated toggle must not
expire, rerun, close, detach, or block that viewer. The same rule applies to every
executable node; Model Viewer is the end-to-end regression, not a special case.

The implementation is a clean current-schema cutover for an unreleased product.
There will be no compatibility adapter, legacy snapshot reader, or migration for
experimental internal metadata. Node coloring, snapshot-management UI, and the
future expired-node visual treatment are explicitly deferred. This plan delivers
the authoritative backend fact that later UI work will consume.

This plan implements the backend portions of `REQ-EXEC-017` and
`REQ-PERSIST-026`. It prepares, but does not complete, `REQ-UI-052`.

## Key Changes

### Locked terminology

- `freshness`: one of `never`, `current`, or `expired`.
- `settlement_status`: one of the existing terminal outcomes such as `completed`,
  `empty`, `failed`, or `blocked`. Settlement status is orthogonal to freshness.
- `disposition`: how a prepared execution handled a node: `reused`,
  `recomputed`, `skipped`, or `blocked`.
- `solution_key`: the deterministic SHA-256 identity of one node solution under
  one exact executable dependency and provenance state.
- `solution_record`: validated settled outputs and identity/provenance facts for
  one `solution_key`.
- `session` residency: reusable only while its owning runtime generation remains
  valid.
- `durable` residency: validated, portable, project-managed snapshot data that may
  survive process and application restarts.
- `force_recompute`: an explicit execution request that ignores reusable records;
  it is not an implicit consequence of an unrelated graph edit.

Do not use `dirty` for solution freshness. A dirty Python Script draft remains an
authoring state and must not become a scheduler synonym.

### Architecture invariants

1. `CorexRuntime` owns preparation, solution identity, reuse decisions, solution
   records, invalidation, and the public freshness projection.
2. `ExecutionPlan` is shared execution code. It must not remain worker-private or
   be independently reimplemented in the shell.
3. `ShellRunState.cached_node_output_records_by_workspace_id` remains a bounded UI
   value projection only. It never seeds execution and is not a second freshness
   authority.
4. The worker reconstructs the shared plan and validates every reuse decision
   before installing reused outputs into `NodeExecutor.node_outputs`.
5. Graph presentation facts—position, selection, title, collapse state, colors,
   exposure, and other non-executable UI state—never enter a `solution_key`.
6. A mutation expires the changed executable roots and enabled downstream nodes.
   Disabled edges and Trigger boundaries retain their existing propagation rules.
7. Stale outputs may remain available for bounded inspection, but they cannot
   satisfy a current execution dependency, current port-flow fact, or viewer live
   transport requirement unless a matching solution record is accepted.
8. Viewer invalidation is node-scoped. Workspace-wide invalidation is reserved for
   project replacement, worker/runtime generation reset, registry replacement, or
   an explicit full reset.
9. Durable solution data lives in project-managed sidecar storage, never inline in
   `.cxproj`.
10. Persistence publishes immutable blobs before manifests and prunes unreachable
    data only after the new project/manifests are committed.
11. Credentials, secrets, callbacks, native objects, worker-local handles, Trigger
    publications, and unmaterialized temporary values never enter durable records.
12. Unknown, incomplete, corrupt, or unverifiable state fails closed to
    recomputation; it never becomes a cache hit.

### Canonical state model

Move `RootExecutionError` and `SettledPortResult` from
`ea_node_editor/execution/protocol.py` to the dependency-light
`ea_node_editor/runtime_contracts/settled_results.py`; update every caller to import
the new owner directly, with no protocol re-export.

Add immutable persistence/process-neutral contracts under
`ea_node_editor/runtime_contracts/solution_records.py`:

```text
SolutionFreshness = never | current | expired
SolutionResidency = session | durable
SolutionDisposition = reused | recomputed | skipped | blocked

NodeSolutionFact
  project_id
  workspace_id
  node_id
  freshness
  revision
  retained_record_id: str | None
  retained_solution_key: str | None
  residency: SolutionResidency | None
  expiration_reason_code
  expiration_root_node_ids
  last_disposition: SolutionDisposition | None

SolutionOutputDescriptor
  port_key
  status: value | empty
  data_type_id: declared port type
  concrete_data_type_ids: tuple[str, ...]
  data_access
  item_count
  payload_kinds: tuple[inline | artifact_ref | handle_ref | blob_ref, ...]
  payload_digest
  payload_schema_version

SolutionPayloadLocator
  kind: session | durable
  reference_id
  blob_digests

SolutionRecord
  schema_version = 1
  record_id
  project_id
  workspace_id
  node_id
  solution_key
  workflow_interface_revision
  workflow_interface_digest
  node_contract_digest
  dependency_solution_keys
  input_provenance_digest
  execution_policy_digest
  implementation_digest
  execution_environment_digest
  settlement_status
  result_digest
  reuse_eligible
  output_descriptors: tuple[SolutionOutputDescriptor, ...]
  payload_locator: SolutionPayloadLocator | None
  residency
  runtime_generation
  created_at_epoch_ms

```

Add execution-only immutable preparation contracts under
`ea_node_editor/execution/prepared_execution.py`:

```text
PreparedAction = reuse | execute
RecomputeMode = reuse_valid | force_recompute

PreparedDispatchEnvelope
  project_path
  project_id
  workspace_id
  trigger
  runtime_snapshot
  execution_backend
  target_node_ids
  clicked_trigger_node_id
  trigger_capture_node_ids
  trigger_publications
  trigger_captures
  recompute_mode
  developer_mode
  catalog_fingerprint
  catalog_revisions
  plugin_bundles
  plugin_fingerprint
  runtime_registry_fingerprint
  registry_contract_fingerprint
  addon_runtime_config

PreparedNodeDecision
  node_id
  action
  reason_code
  solution_key
  dependency_solution_keys
  accepted_record_id

AcceptedOutputPayload
  node_id
  record_id
  solution_key
  settlement_status
  result_digest
  residency
  runtime_generation: int | None
  outputs: bounded map[port_key, SettledPortResult]

PreparedExecution
  preparation_id
  dispatch_envelope: PreparedDispatchEnvelope
  solution_namespace_id
  execution_affecting_workspace_revision
  runtime_snapshot_fingerprint
  execution_plan_fingerprint
  registry_contract_fingerprint
  workflow_interface_revision
  workflow_interface_digest
  execution_environment_digest
  trigger_publication_generations: tuple[(trigger_node_id, generation), ...]
  node_decisions
  accepted_output_payloads
  recompute_node_ids
  reused_node_ids

InvalidationResult
  project_id
  workspace_id
  solution_revision
  changed_root_node_ids
  expired_node_ids
  removed_node_ids
  reason_code
```

`PreparedExecution` is frozen. Single-use consumption is stored by `CorexRuntime`
against `preparation_id`; the DTO itself never mutates.

`PreparedDispatchEnvelope` is the complete frozen input needed to construct the
eventual `StartRunCommand`; dispatch reads no mutable external request, registry,
plugin, catalog, trigger, or snapshot state. T01 proves the DTO/adapters. T03 owns
preparation storage and single-use consumption; T04 owns command construction and
worker validation.

Null/optional rules are strict:

- `never`: retained record/key/residency/last disposition are all `None`;
- `current`: retained record/key/residency are required;
- `expired`: retained record/key/residency may remain together for stale inspection
  or all be `None`; partial triples are invalid;
- `PreparedNodeDecision.solution_key` is always a SHA-256 digest;
- `accepted_record_id` is required only for `reuse` and forbidden for `execute`;
- session records/payloads require a positive runtime generation;
- durable records/payloads require `runtime_generation is None`;
- `SolutionPayloadLocator` is `None` only for a reusable outputless/empty
  settlement; a value descriptor requires a matching locator entry.

Strict semantic combinations:

| Contract/state | Required | Forbidden |
| --- | --- | --- |
| `NodeSolutionFact.never` | empty expiration roots/reason | retained triple; residency; last disposition |
| `NodeSolutionFact.current` | retained record/key/residency; last disposition `reused` or `recomputed` | expiration roots/reason |
| `NodeSolutionFact.expired` | non-empty reason and root IDs | partial retained record/key/residency triple |
| `SolutionOutputDescriptor.value` | declared type/access, non-negative item count, sorted unique concrete type IDs and payload kinds (each capped at 64), SHA-256 payload digest, positive payload schema | empty concrete/kind tuples or digest |
| `SolutionOutputDescriptor.empty` | item count `0`, empty concrete type/kind tuples, schema `0`, empty digest | concrete types or payload kinds |
| session `SolutionPayloadLocator` | `kind=session`, bounded opaque session reference ID | blob digests |
| durable `SolutionPayloadLocator` | `kind=durable`, SHA-256 record/payload reference, unique SHA-256 blob digests | runtime-local ID/generation |
| reusable `SolutionRecord` | settlement status `completed` or `empty`; locator kind equals residency | `failed`/`blocked` status; descriptor/locator mismatch |
| `PreparedNodeDecision.reuse` | accepted record ID and exactly one matching `AcceptedOutputPayload` | missing/duplicate payload; failed/blocked payload |
| `PreparedNodeDecision.execute` | no accepted record or payload | accepted payload |

For a `value` record, output descriptor port keys/statuses must match the accepted
payload output map exactly. Outputless completed and wholly empty settlements may
use `payload_locator=None` and an empty accepted output map. Property-style tests
cover every valid row and reject every cross-row combination.

Mixed DataTree carriers/types are valid observation records. Reuse is allowed only
when every concrete type/carrier in the bounded descriptor is valid for the
record's residency and integrity/generation checks; otherwise the record remains
truthfully current with `reuse_eligible=false`.

`NodeSolutionFact` is the only mutable freshness projection. `SolutionRecord`
objects are immutable after publication. Expiration changes the node fact; it does
not rewrite historical records.

`SolutionRecord.settlement_status` preserves the terminal semantic needed to replay
completed, empty, and outputless settlements. `result_digest` binds the canonical
typed output payload. `payload_locator` resolves through the execution store:

- session records point to an immutable in-memory typed-output entry owned by the
  same `SolutionStore` and runtime generation;
- durable records point to codec-validated content-addressed result blobs owned by
  the durable repository.

`PreparedNodeDecision` never embeds an unbounded payload. During preparation,
`SolutionStore.accepted_outputs(decision)` resolves the locator, verifies the
result digest, catalog contract, artifact integrity, residency, and handle/runtime
generation, then freezes the bounded typed outputs carried by the finalized
preparation's `accepted_output_payloads`. Every payload is bound to node ID, record
ID, solution key, settlement status, result digest, residency, and nullable runtime
generation. Session payloads require an exact current runtime generation; durable
payloads require `runtime_generation is None`. Queue-boundary adapters
apply the same strict DataTree/value/count/depth/byte limits as settled runtime
results; large values remain validated artifact/blob/handle references rather than
inline bytes. A missing or invalid payload becomes `execute` before
`PreparedExecution` is published, so `recompute_node_ids` is final and truthful.
Dispatch revalidation may only accept the complete immutable preparation or reject
it and require re-preparation; it never mutates an action or recompute set.

T01 establishes these queue-boundary ceilings in the shared settlement/solution
adapters; outbound payloads are reparsed under the same limits before handoff:

```text
MAX_PREPARED_NODES = 100_000
MAX_OUTPUTS_PER_NODE = 1_024
MAX_ACCEPTED_NODE_PAYLOADS_PER_PREPARATION = 100_000
MAX_ACCEPTED_PORT_RESULTS_PER_PREPARATION = 1_000_000
MAX_DATA_TREE_BRANCHES_PER_OUTPUT = 100_000
MAX_DATA_TREE_ITEMS_PER_OUTPUT = 1_000_000
MAX_ROOT_ERRORS_PER_RESULT = 64
MAX_TYPED_INLINE_BYTES = 1_048_576        # existing 1 MiB rule
MAX_REFERENCE_METADATA_BYTES = 65_536     # existing 64 KiB rule
MAX_ACCEPTED_OUTPUT_PAYLOAD_BYTES = 67_108_864  # aggregate 64 MiB
MAX_JSON_DEPTH = 32                       # existing rule
```

Count/aggregate breaches, duplicate IDs/keys, unknown fields, booleans supplied as
integers, invalid optional combinations, or oversized inline values are rejected.
During preparation, reusable nodes are considered in deterministic execution order.
If accepting another reuse would exceed the node, port-result, or aggregate-byte
budget, that node and all dependent reuse decisions become `execute` with reason
`reuse_payload_budget_exceeded` before the immutable preparation is published.
There is no command chunking in this plan.

The 64 MiB aggregate applies only to serialized `accepted_output_payloads` plus
adapter overhead. Ordinary settlement traffic retains its existing protocol
limits. A maximum-size `ImageValue` is not eligible as inline accepted output; it
must be represented by a validated artifact/blob reference. Large legitimate
values use validated artifact/blob/handle references.

### One solution store, two residencies

Add `ea_node_editor/execution/solution_store.py` as the only scheduler-facing
store. It owns session records, node facts, record selection, invalidation, and
record publication. It accepts an optional durable backend through a narrow
protocol defined in the same module.

Add `ea_node_editor/persistence/solution_repository.py` as the durable backend.
Execution never imports persistence codecs or concrete repositories. Shell
composition in `ea_node_editor/ui/shell/composition/controllers.py` binds the
repository to `CorexRuntime` only after the project-session services have validated
an opened project. Session-only use keeps working with the in-memory backend.

The runtime binding contract is explicit:

```text
CorexRuntime.bind_project_solution_store(
  project_id,
  project_path,
  repository,
  active_generation_id,
  active_generation_digest,
)
CorexRuntime.detach_project_solution_store(project_id, reason)
```

New/unsaved projects use session residency only. Project replacement detaches the
old repository under the existing replacement guard and invalidates incompatible
session records/viewers. Save As prepares a candidate repository but does not
switch the runtime binding until destination reopen validation succeeds. A failed
Save As leaves the original binding untouched.

Qt-free/headless construction uses dependency injection, not an execution-to-
persistence import inside the store/compiler/worker:

```text
CorexRuntime(
  solution_repository_factory: SolutionRepositoryFactory | None = None,
)
```

`headless_runtime.py`'s project-loading/CLI composition supplies the persistence
factory after it validates a project path. Tests may inject an in-memory or faulting
factory. `execution/solution_store.py`, `execution_plan.py`, the compiler, and the
worker never import the concrete persistence repository.

Session namespace and retention are locked:

- `solution_namespace_id = project_id` for saved projects;
- unsaved projects receive one random in-memory namespace retained for that loaded
  project lifetime; T07 persists that same value on first save;
- maximum two session records per node (current plus newest historical);
- maximum 4,096 session records per workspace;
- maximum 536,870,912 bytes (512 MiB) of canonical session payload per workspace;
- maximum 16,384 session records across the runtime;
- maximum 2,147,483,648 bytes (2 GiB) of canonical session payload across the
  runtime;
- maximum 64 outstanding preparations and 268,435,456 bytes (256 MiB) of frozen
  preparation envelopes/payloads across the runtime;
- current fact records and active preparation/run references are pinned;
- eviction is oldest unpinned non-current first, deterministic by creation sequence
  then record ID;
- if a new record cannot fit after legal eviction, do not publish it and leave the
  node `expired` with reason `session_store_capacity_exceeded`.

Before registering preparation 65 or crossing the preparation-byte ceiling, evict
the oldest unconsumed preparation by creation sequence then preparation ID and
release every record pin and Trigger reservation it owns. Dispatch of an evicted
ID fails `preparation_evicted`. Start failure, every terminal event, generation
reset, project replacement, and shutdown release the corresponding preparation/run
context, pins, and Trigger reservations. Current records and active-run references
remain non-evictable; capacity exhaustion fails closed as above.

Every settled executable node may publish an observation `SolutionRecord` so its
fact can become `current`. `solution_reuse_scope=never` records set
`reuse_eligible=false`, are never inserted into the solution-key reuse index, and
remain subject to the same retention limits. T03 adds this field to the contract
and tests; it does not broaden any T02 classification.

Each registered run stores per node the captured solution key and captured
`NodeSolutionFact.revision`. On settlement, under the store lock:

- reject stale preparation/run/backend generations completely;
- validate and canonically reparse completed/empty outputs with the active catalog;
- publish records only for valid completed/empty settlements;
- make a fact `current` only when its current node revision still equals the
  captured revision;
- keep it `expired` when that node was invalidated after preparation, even if an
  unrelated branch remained unchanged;
- preserve earlier records on failure, block, stop, or cancellation;
- same-key/same-result retains the established immutable record;
- same-key/different-result reports nondeterminism and leaves the fact expired.

Disposition-specific settlement handling is explicit:

- `reused`: validate against the registered decision, accepted payload, pinned
  record, event digest, generation, and node revision; publish no new record and
  set `last_disposition=reused` only if the capture remains current;
- `recomputed` completed/empty: use normal record/nondeterminism publication;
- `recomputed` failed, `skipped`, and `blocked`: publish no record and preserve
  prior retained data/freshness rules;
- late invalidation prevents both reused and recomputed events from restoring
  `current`.

User/event callbacks run only after releasing the store lock. Lock order is:
`CorexRuntime lifecycle RLock -> client registry-publication RLock -> brief
SolutionStore RLock`; client calls never occur while holding the store lock.

Adding durable storage changes a record's eligible residency, not the planner,
solution key, or scheduler authority. Do not build separate session and durable
cache frameworks.

#### Staged authority cutover

T03 builds and tests `SolutionStore`, preparation, invalidation, and event capture,
but does not route existing shell/manual/Auto/Trigger dispatch through them. A run
without a registered prepared/run context is ignored by the store and continues to
use the legacy shell projection. T04 makes prepared dispatch/reuse executable; T05
switches shell invalidation/freshness and removes the legacy authority. This is a
deliberate dormant-to-cutover sequence, not two production schedulers.

`CorexRuntime.start_run(...)` remains temporarily through T04 and is removed with
its shell call sites in T05. T03 must not claim the sole production freshness
authority before that cutover.

### Shared plan and preparation flow

Move `ExecutionPlan` from `ea_node_editor/execution/worker_runtime.py` to
`ea_node_editor/execution/execution_plan.py`. T01 moves current worker/runtime/tests
to the new owner and removes the old re-export. `CorexRuntime` begins consuming the
shared class in T03 when preparation is introduced; T01 does not add a speculative
planning call site.

Replace direct start-only dispatch with:

```text
prepared = CorexRuntime.prepare_execution(ExecutionRequest)
run_id = CorexRuntime.dispatch_prepared(prepared)
```

Preparation is side-effect free. It compiles the requested closure, calculates
solution keys in topological order, selects valid records, and returns exact
`recompute_node_ids`. Each prepared decision is only `reuse` or `execute`;
`skipped` and `blocked` are runtime outcomes that cannot be predicted before
recomputed upstream nodes settle. Dispatch consumes the preparation exactly once.

`CorexRuntime` owns an execution-affecting workspace revision that advances only
for executable graph/property changes, registry/runtime identity changes, and
solution resets—not cosmetic edits. Preparation captures this token. Dispatch is
performed under the same runtime/host lock and rejects a token mismatch, project or
workspace mismatch, registry/environment drift, or plan fingerprint change.

Concrete execution clients expose
`execution_generation_snapshot(selection: ExecutionBackendSelection)` and one
generation-aware event subscription. The immutable snapshot includes resolved
backend, backend generation, physical/runtime generation, stable environment
digest, and `available/reason`. `ExecutionBackendClient` preserves this metadata
when forwarding events; callbacks run after releasing every client lock.
`CorexRuntime` never inspects client private fields. A cold/dead external worker
returns unavailable and produces execute-only identity; its successful handshake
publishes the exact generation/environment used by later preparation. Idle worker
death, backend replacement, executable change, registry recycle, and shutdown
notify the runtime so all affected session records/payloads are evicted.

Preparation may read/load the project, retain a candidate registry privately,
compile the snapshot, hash declared external inputs, and register an immutable
preparation. It must not call `replace_registry()` or alter client/viewer generation
during preparation. “Side-effect free” means no node execution, registry
publication, external write/effect, fact freshness change, record publication, or
viewer invalidation; it is not a promise of zero reads or zero internal registration.

Clients add a two-step caller-ID run API:

```text
reservation = ExecutionBackendClient.reserve_run(selection, workspace_id)
started = ExecutionBackendClient.start_reserved_run(reservation, command)
ExecutionBackendClient.release_run_reservation(reservation, reason)
```

Under the runtime lifecycle lock and client registry-publication lock, dispatch
first publishes/revalidates the candidate registry. It then takes the route-specific
post-publication generation snapshot and reserves the caller-owned run ID against
that exact generation. For a cold route, reservation performs/binds the handshake
generation atomically before any workflow event callback. Dispatch then atomically
consumes the preparation and registers the complete run capture in `SolutionStore`
before calling `start_reserved_run`. Synchronous settlement/terminal events
therefore always find context. Failed start releases the reservation/context/pins
and preserves prior facts/records. Tests cover registry-changing and cold
synchronous-settlement/terminal starts.

If complete reusable identity cannot be built, the node receives an execute-only
SHA-256 key over a version tag, namespace/workspace/node, preparation ID, workspace
solution revision, and deterministic failure reason. It is never inserted into the
reuse index.

Trigger generations are committed publication facts. Preparation uses the current
committed generation for ordinary Trigger dependencies and reserves `current + 1`
only for the clicked Trigger. The reservation is stored in the preparation/run
context; it commits only on a validated `trigger_published` event. Failure, stop,
cancellation, or stale generation discards the reservation without advancing the
counter.

`dispatch_prepared()` extends `StartRunCommand` with the typed prepared decisions.
The worker reconstructs `ExecutionPlan`, recalculates the decision inputs, and
rejects the command if its scheduled nodes or fingerprints disagree. Accepted
reused outputs are installed before dependent nodes run.

The worker emits no `node_started` event for reused nodes. The worker determines
the final `SolutionDisposition`: accepted reuse becomes `reused`; a successfully
executed node becomes `recomputed`; and runtime dependency outcomes may become
`skipped` or `blocked`. It emits one normal `node_settled` event with these
additive fields:

```text
disposition
decision_reason
solution_key
record_id
residency
```

The event remains the one settlement stream used by shell projections, port-flow
state, previews, run counts, diagnostics, and future freshness UI.

### Solution identity

Add `ea_node_editor/execution/solution_identity.py`. Use canonical tagged JSON
encoded as UTF-8 and SHA-256. The encoder must preserve type distinctions,
ordered DataTree paths/items, IEEE-754 special-value policy, `None`, bytes through
validated blob refs only, and deterministic map/set ordering. It must never call
user `repr`, iteration hooks, callbacks, filesystem access, or network access.

Each node `solution_key` binds:

- stable logical solution-namespace/workspace/node identity. The solution namespace
  is stored in current-schema project metadata and is preserved by Save As;
- a validated normalized workflow-interface revision and digest covering the
  execution-facing portion of `REQ-NODE-036`;
- node type ID and normalized execution contract digest;
- resolved effective input/output ports, access modes, readiness rules, and
  execution-relevant per-port modifiers;
- authored execution properties after defaults/normalization;
- enabled compiled incoming edges, endpoints, port keys, conversions, and
  `input_order`;
- execution-relevant hidden ordering/dependency links;
- ordered upstream `solution_key` values or explicit Trigger publication
  generation;
- managed/runtime artifact semantic type, schema, format, byte size, SHA-256,
  producer facts, logical/project-relative identity, and current integrity. Do not
  hash destination-root-specific store descriptors;
- plain file content SHA-256 plus the node's normalized path policy;
- directory content through a deterministic relative-path/content tree hash, or
  `session`/`never` eligibility when the node has no directory provenance codec;
- node implementation digest;
- only the data-type/conversion revisions the node actually uses;
- a stable `execution_environment_digest` covering backend, isolation mode,
  interpreter build, relevant packages/add-ons/toolchains, and result-affecting
  execution policy.

Exclude run ID, timestamps, UI state, selection, view state, trigger labels,
console settings, explanatory reason text, project absolute path, destination
artifact root, and ephemeral runtime-generation counters. Runtime generation is
validated separately for session records and live handles; it is never part of a
durable key.

The workflow-interface digest is a prerequisite, not optional wording. T02 defines
its normalized execution-facing representation and revision owner. Records without
a valid interface digest are ineligible for durable residency, and
`REQ-EXEC-017`/`REQ-PERSIST-026` remain partial until the interface acceptance tests
pass.

External provenance hashing is bounded by a versioned `ProvenanceHashPolicy`
included in the execution policy digest:

```text
follow_symlinks_or_reparse_points = false
max_single_file_bytes = 68_719_476_736        # 64 GiB
max_directory_total_bytes = 68_719_476_736   # 64 GiB
max_directory_entries = 100_000
max_directory_depth = 32
```

Hashing streams in bounded chunks, observes cancellation between chunks/entries,
and compares file identity/size/mtime before and after reading. A reparse point,
limit breach, cancellation, permission failure, or change during hashing yields a
deterministic non-reusable reason and an `execute` action without publishing a
solution record. Directory reuse is allowed only for nodes whose accepted
classification names this exact policy; otherwise directory inputs remain `never`.

`execution/solution_identity.py` owns one shared per-node solution-key assembler.
Both runtime preparation and worker validation call it with the namespace,
workspace revision, preparation ID, Trigger generations, environment digest,
plan/dependency keys, catalog, provenance, and execution policy. Do not duplicate
the runtime's identity assembly in worker code.

### Reuse eligibility

Extend the node execution contract with one explicit internal field:

```text
solution_reuse_scope = never | session | durable
```

Default is `never`. Every executable built-in, add-on function, trusted helper,
and public function declaration must be classified deliberately.

- `never`: external side effects, untracked environment/network state, hidden
  mutable worker state, nondeterminism, or incomplete provenance.
- `session`: deterministic within one runtime generation, including live handles
  or temporary resources that cannot be serialized safely.
- `durable`: deterministic and fully described by portable identity/provenance,
  with every output supported by a durable codec.

All public/untrusted declarations are locked to `never` for this plan. Bundle
digests and declared I/O do not prove absence of hidden environment, network,
time, randomness, or side effects. Public opt-in requires a separate accepted
trust/provenance contract and is not introduced here.

Implementation identity must be content based. Module and qualified names alone
are insufficient. Built-ins bind the packaged source/build digest; public
functions bind their existing bundle/function source digest; add-ons bind package
and implementation digests.

File/directory provenance is declared, never inferred from property names. Add an
internal `SolutionProvenanceInputSpec(property_key, kind=file|directory,
policy_revision)` tuple on `NodeTypeSpec`, but keep public/static declaration
syntax unchanged. A registry-owned typed table in
`ea_node_editor/nodes/solution_provenance.py` overlays only the accepted shipped
session readers (`engineering.cad_import`, `engineering.fe_import`, `io.file_read`,
`io.image_import`, `io.excel_read`, and `tabular.input`) during trusted registry
construction. Public/package rows never receive the overlay. Missing or mismatched
declarations make identity execute-only.

#### Locked initial classification rules

T02 must produce the exact registry-row inventory at
`docs/specs/perf/COREX_SOLUTION_REUSE_CLASSIFICATION.md` before changing any node
metadata. The implementation sub-agent may apply only an inventory accepted by the
orchestrator/reviewer. These family rules are locked:

| Executable family | Initial maximum | Required evidence |
| --- | --- | --- |
| Pure scalar/List/Tree transforms with catalog codecs | `durable` | deterministic implementation digest, normalized properties/ports, durable output codecs |
| Pure geometry/mesh/FE transforms returning portable managed artifacts | `durable` | content-addressed artifact outputs, toolchain digest, deterministic codec |
| File/directory import readers | `session` until proven durable | content/tree hash, path policy, importer/toolchain digest; no timestamp-only identity |
| CAD Import in the primary acceptance chain | `session` initially | source content hash, importer digest, session-valid prepared-scene output |
| Model Viewer and nodes producing live/native/runtime handles | `session` | matching runtime generation and handle/transport validation |
| Pure plotting/image rendering with stable artifact output | `durable` only after codec audit | input keys, renderer/package digest, content-addressed output |
| Trigger/sample-and-hold | `never` for durable; existing session semantics remain explicit | publication generation is not snapshot persistence |
| File/process/email/SSH/export/write/remote/service side effects | `never` | none; execution is the effect |
| Time/random/network/environment-dependent compute without captured provenance | `never` | may be reclassified only after explicit deterministic provenance contract |
| Public/untrusted function declarations | `never` | locked for this plan; no opt-in surface |
| Hidden mutable worker-state/optimization pairs | `never` or one coupled `session` decision | state snapshot codec and coupled invalidation proof required |
| Passive/display-only nodes | not executable | excluded from solution records |
| Unknown/unclassified executable node | `never` | fail closed |

The inventory must enumerate every current executable registry row with: type ID,
owner family, proposed scope, side-effect classification, implementation digest
source, input provenance, output codec, handle/artifact facts, reason, and proving
test. No row may inherit a broader scope merely from its category label.

T02's locked shipped baseline is 936 rows: 898 executable and 38 excluded
(35 passive, 3 compile-only). The conservative initial totals are:

- `durable`: 29 explicitly proven pure/portable rows;
- `session`: 27 file-reader, viewer, runtime-handle/ref, or currently non-durable
  codec rows;
- `never`: 842 rows, including every one of the 805 DPF rows until trusted-factory
  content/toolchain identity is complete;
- excluded: 38 non-executable rows.

Runtime-discovered public plugins remain outside the tracked row inventory and are
forced to `never`; never publish their private IDs or paths. The classification
artifact is the exact row authority and must preserve these totals unless a
reviewer reopens T02 with concrete identity/codec evidence. A non-durable input
carrier caps a row at `session` even when every output has a durable codec.

### Invalidation and Auto/manual behavior

Move executable invalidation authority out of mutable shell cache fields:

```text
CorexRuntime.invalidate_solution(
  project_id,
  workspace_id,
  runtime_snapshot,
  changed_root_node_ids,
  reason_code,
) -> InvalidationResult
```

The shared plan calculates the affected enabled downstream closure with current
Trigger boundaries. The result includes exact expired node IDs and a monotonic
workspace solution revision. `RunController` projects this result but does not
recalculate another closure.

`ExecutionPlan.affected_downstream_closure(root_node_ids)` is the only closure
owner. It validates/deduplicates roots, includes roots, traverses enabled compiled
data edges plus validated hidden-ordering pairs, includes a Trigger reached from
upstream but stops beyond it, does not traverse from a Trigger root, returns
deterministic plan/declaration order, and reports the contributing root IDs for
each affected node.

- Auto requests the affected target closure and the planner reuses any still-valid
  upstream records.
- Manual Run may continue to request all active nodes, but only `recompute`
  decisions invoke node implementations.
- Run Selected requests selected targets; current upstream dependencies are reused
  and expired/missing upstream dependencies are recomputed.
- A future Run Expired UI action may pass the exposed expired IDs. This plan
  provides the backend API but no new action or visual control.
- `force_recompute` explicitly ignores valid records within the requested closure.
- A mutation during an active run expires the affected captured keys. Late
  settlements remain historical records for their captured keys and cannot make
  the current node fact current.

Remove shell-owned scheduling mutations of `fresh_run_node_ids_by_workspace_id`
and per-record `stale` flags after all consumers use `NodeSolutionFact`. The shell
may retain settled output values for bounded display, keyed by record/solution ID,
without owning freshness.

### Viewer and live-resource scoping

Replace blanket viewer invalidation in both processes:

- `RunController._invalidate_viewer_sessions_for_rerun(...)` receives the prepared
  `recompute_node_ids` and projects run-required only for viewer nodes in that set.
- `ViewerSessionBridge.project_workspace_run_required(...)` and
  `invalidate_workspace_sessions(...)` accept an optional exact `node_ids`
  filter. `None` retains full-reset behavior.
- `ViewerSessionService.prepare_workspace_context(...)` and
  `invalidate_workspace(...)` accept the same filter.
- `worker_runner.py` passes only recomputed viewer IDs; it must stop using
  unconditional `invalidate_existing=True` for partial/reuse-valid runs.

Filtering alone is insufficient for in-flight requests. The bridge, execution
client, and worker viewer service maintain a monotonic per-workspace/per-node viewer
invalidation epoch. Every open/update/materialize/query request captures the epoch;
every response carries it. Scoped invalidation increments only affected nodes,
retires their pending requests, and rejects any later response from an older epoch.
True global resets advance the workspace epoch and retire all pending requests.

Reused viewer records remain session-only while they contain live handles. Worker
reset, runtime/registry generation replacement, project replacement, backend
change, or handle-generation mismatch invalidates them globally and fails closed.

Primary acceptance scenario:

1. Branch A completes `CAD Import -> Model Viewer`.
2. Model Viewer is open/ready and has a live transport.
3. Disconnected branch B changes an unrelated toggle.
4. Invalidation returns only B and its enabled downstream closure.
5. Auto dispatch contains no recompute decision for branch A.
6. No viewer run-required projection or worker transport release occurs for A.
7. Viewer remains `phase == "open"`, `live_open_status == "ready"`, and has no
   rerun blocker before, during, and after B settles.
8. A deliberately delayed old open/materialize response cannot restore a viewer
   after a same-node invalidation epoch advances.

### Durable repository and artifact lifecycle

Use this current-schema sidecar layout:

```text
<project-stem>.data/solutions/v1/
  generations/<generation-id>/manifest-set.json
  generations/<generation-id>/nodes/<workspace-key>/<node-key>.json
  records/sha256/<first-two>/<record-digest>.json
  blobs/sha256/<first-two>/<sha256>
```

`workspace-key` and `node-key` are SHA-256 path keys derived from logical IDs; the
logical IDs remain inside validated manifests. Do not place untrusted IDs directly
into paths.

Generation directories, node manifests, records, and blobs are immutable after
publication. Each durable output uses the existing data-type catalog codec and a
bounded descriptor; never use pickle or assembly-qualified runtime-object
serialization.

Each immutable node manifest maps `solution_key` to `record_digest`; each record
binds both values plus `result_digest`. A corrupt record digest/path never owns the
solution key permanently: a valid recomputation may publish a new content-addressed
record, and the next immutable generation points to it. Corrupt/unreachable records
remain garbage until safe pruning.

The `.cxproj` document is the sole commit point. Current-schema project metadata
contains only:

```text
solution_store
  schema_version = 1
  solution_namespace_id
  active_generation_id
  active_manifest_set_digest
```

The manifest-set digest covers every node-manifest path/digest in the generation.
Opening a project validates the generation and digest before binding it. A complete
but unreferenced generation is unreachable garbage, not a partially committed
project state.

Durable commit order:

1. Preflight graph document, solution records, artifacts, destination, free space,
   codecs, and every referenced digest.
2. Stage immutable result blobs and any promoted managed artifacts.
3. Stage immutable solution records.
4. Write and fsync one immutable candidate generation and its manifest-set digest.
5. Stage `.cxproj` with the candidate generation pointer.
6. Atomically replace `.cxproj`; this one replacement commits the generation.
7. Reopen and validate the committed pointer/generation before reporting success.
8. Mark every referenced solution/artifact payload reachable from the committed
   document/generation.
9. Prune unreferenced generations/payloads only after reopen succeeds, retaining
   the previous generation until then.

A failed save before the `.cxproj` replacement leaves the previous document,
generation, records, and reachable artifacts intact. A crash after replacement
finds a fully written candidate generation. Unreachable staged generations/blobs
may remain for later garbage collection; a mixed manifest generation is never the
active commit.

Save As preserves `solution_namespace_id`, logical workspace/node IDs, portable
artifact identity, and solution keys. It copies only validated reachable
records/blobs/artifacts into a new immutable destination generation, then atomically
replaces the destination `.cxproj` pointer. Destination-root-specific store
descriptors are rewritten outside the key. An existing destination's old `.cxproj`
and active generation remain authoritative until the replacement. Runtime
repository binding switches only after destination reopen succeeds; otherwise the
source binding and destination's previous commit remain intact. Live handles,
temporary refs, credentials, secret values, private absolute paths, and session
Trigger state are excluded.

Forced recomputation under an existing `solution_key` calculates the canonical
`result_digest` before publication. An identical digest retains the existing
immutable record (updating only mutable node fact/history projections). A different
digest is a nondeterminism conflict: report it, quarantine no new current record,
and never overwrite the established record.

There is no migration. Schema values other than `1` fail closed with a clear
current-schema error and require regeneration.

### Relationship to explicit value internalization

Solution snapshots remain a derived performance cache. They do not sever graph
dependencies and do not become authored node properties.

Explicit value internalization/data-container behavior is a separate future
feature. If implemented later, input ports—not the solution store—should own the
authored captured-value reference, wire attachment should clear that authored
capture, and undo/redo should cover the graph mutation. This plan does not add
container nodes or internalization commands.

## Public Interface Changes

### Headless runtime

- Add `CorexRuntime.prepare_execution(request) -> PreparedExecution`.
- Add `CorexRuntime.dispatch_prepared(prepared) -> str`.
- Add `CorexRuntime.invalidate_solution(...) -> InvalidationResult`.
- Keep `CorexRuntime.start(request: ExecutionRequest) -> str` as the only
  convenience entrypoint; it is exactly prepare followed by dispatch.
- Remove `CorexRuntime.start_run(project_path, workspace_id, ...)` and update every
  call site to construct `ExecutionRequest`; do not keep an alias. This removal
  occurs in T05 after T04 makes prepared dispatch executable.
- Add `bind_project_solution_store(...)` and
  `detach_project_solution_store(project_id, reason)` with the lifecycle semantics
  defined above.
- Extend `ExecutionRequest` with `recompute_mode: RecomputeMode = "reuse_valid"`.
- Add read-only solution-state queries:
  - `solution_facts(project_id, workspace_id) -> tuple[NodeSolutionFact, ...]`;
    unknown project/workspace returns an empty tuple;
  - `expired_node_ids(project_id, workspace_id) -> tuple[str, ...]`; unknown
    project/workspace returns an empty tuple, sorted by execution-plan order;
  - `solution_record(record_id) -> SolutionRecord | None`; unknown ID returns
    `None`.
- `InvalidationResult` has the exact fields listed in Canonical state model; an
  unknown project/workspace or malformed root raises `ValueError` before mutation.
- Add runtime-local strict `solution_state_changed` events after locks are released:
  `{project_id, workspace_id, solution_revision, expired_node_ids,
  removed_node_ids, reason_code}`. Adapters bound counts/types and reject unknown or
  malformed fields. This notifies shell/QML of registry/generation/project resets
  without creating another settlement stream.
- Add `ExecutionBackendClient.execution_generation_snapshot()` and a
  generation-aware subscription used by `CorexRuntime`; forwarded events retain
  backend/generation/environment metadata.

### Worker protocol

- Extend `StartRunCommand` with immutable `reuse|execute` prepared decisions,
  `accepted_output_payloads`, and these non-duplicated preparation facts:
  `preparation_id`, `solution_namespace_id`, execution-affecting workspace revision,
  dispatch runtime generation, runtime-snapshot/plan/workflow-interface/environment
  digests, Trigger publication generations, node decisions, and accepted payloads.
- Empty `preparation_id` is the explicit legacy shell form and requires every
  prepared-only field to be empty/default. Non-empty ID requires the complete
  prepared field set. Session payload generation equals the command generation;
  durable payloads have no runtime generation.
- Extend `NodeSettledEvent` with disposition, reason, solution key, record ID, and
  residency.
- Settlement combinations are strict:
  - `reused`: completed/empty with record ID and residency;
  - `recomputed`: completed/empty/failed without record ID/residency;
  - `skipped`: empty without record ID/residency;
  - `blocked`: blocked without record ID/residency;
  - legacy: empty solution key, reason `legacy_direct_run`, no record/residency.
- Do not add a second settlement event family.

### Node execution contracts

- Add `solution_reuse_scope` to the internal node execution specification.
- Add internal `SolutionProvenanceInputSpec` declarations for accepted file and
  directory readers.
- Add a content-based `implementation_digest` contract.
- Reject missing/invalid declarations at registry validation for nodes opting into
  `session` or `durable` reuse.
- Add `SolutionRecord.reuse_eligible`; `never` rows publish observation records
  with `false` but never enter the reuse index.

### Viewer invalidation

- Add optional exact `node_ids` filters to bridge/service workspace invalidators.
- `None` means a true workspace-wide reset; an empty set means invalidate none.
- Add viewer invalidation epoch fields to viewer commands/events and pending-request
  registries; older-epoch responses are ignored.

### Future UI transport, without styling

- Add `ExecutionStateProps.node_solution_freshness_lookup`.
- Add `GraphCanvasExecutionFacts.nodeSolutionFreshnessLookup`.
- Values are `current` or `expired`; a missing node ID means `never`.
- Do not add node colors, badges, stripes, tooltips, animations, or actions.

### Removed internal contracts

- Remove shell scheduling authority from `fresh_run_node_ids_by_workspace_id`.
- Remove mutable per-output-record `stale`/`stale_reason` as the freshness source.
- Remove blanket viewer invalidation on every rerun.
- Remove worker-private `ExecutionPlan` ownership.
- Remove duplicate direct-run call paths that bypass `CorexRuntime` preparation.

## Execution Tasks

### T01 Define solution contracts and move the shared execution plan

- Goal: Establish one dependency-light solution contract and one shared
  `ExecutionPlan` used by preparation and worker validation.
- Preconditions: Current `main`; approved plan; implementation sub-agent has read
  the execution subsystem and requirements `REQ-EXEC-015`/`017`.
- Conservative write scope:
  - `ea_node_editor/runtime_contracts/settled_results.py` (new)
  - `ea_node_editor/runtime_contracts/solution_records.py` (new)
  - `ea_node_editor/runtime_contracts/__init__.py`
  - `ea_node_editor/execution/prepared_execution.py` (new)
  - `ea_node_editor/execution/execution_plan.py` (new)
  - `ea_node_editor/execution/protocol.py`
  - `ea_node_editor/execution/worker_runtime.py`
  - `ea_node_editor/execution/worker_runner.py`
  - exact settlement import consumers identified by the accepted T01 explorer
  - `tests/test_solution_records.py` (new)
  - `tests/test_execution_plan.py` (new)
  - `tests/test_execution_worker.py`
  - `tests/test_execution_protocol.py`
  - `tests/test_architecture_boundaries.py`
  - `docs/agent_maps/subsystems/execution.md`
  - `docs/agent_maps/subsystems/supporting_runtime_assets.md`
  - regenerated `docs/agent_route_index.md`, `docs/agent_route_index.json`, and
    `docs/source_test_file_index.md`
- Deliverables:
  - enums/DTOs listed in Canonical state model;
  - shared settlement ownership moved without a compatibility re-export;
  - structural ownership proof confirms the settlement classes are defined only in
    `runtime_contracts/settled_results.py`, are unavailable from
    `execution.protocol`, and no live source/test imports them from the old owner;
  - strict `to_payload`/`from_payload` adapters with the approved
    count/depth/byte/null/type limits;
  - `ExecutionPlan` moved without behavior drift;
  - deterministic versioned canonical-JSON plan fingerprint over workspace ID,
    effective targets/Trigger mode, scheduled IDs/order, execution-relevant ports,
    enabled edge endpoints/input order, and validated hidden-ordering pairs;
  - fingerprint excludes titles, coordinates, collapse/style/labels,
    selection/view state, and disabled edges;
  - current Trigger, disabled-edge, hidden-ordering, dynamic-port, and target
    behavior preserved.
- Verification:
  - `./venv/Scripts/python.exe -m pytest tests/test_solution_records.py tests/test_execution_plan.py -q`
  - `./venv/Scripts/python.exe -m pytest tests/test_execution_protocol.py -q`
  - `./venv/Scripts/python.exe -m pytest tests/test_dataflow_execution_runtime.py -q`
  - `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py::GraphArchitectureBoundaryTests::test_runtime_contracts_do_not_import_execution_implementation -q`
  - focused import-smoke coverage for `ui/support/port_flow_state.py`,
    `ui_qml/graph_canvas_state/execution_state_props.py`, shell run state/controller,
    and protocol/client/worker consumers after the ownership move;
  - existing worker-runtime target/ordering selectors;
  - generate source/test and agent-route indexes, then run
    `./venv/Scripts/python.exe ./scripts/check_agent_maps.py`;
  - `git diff --check`.
- Non-goals: reuse decisions, persistence, viewer changes, QML facts.
- Packetization notes: `P01`; mandatory foundation. One pre-implementation explorer,
  one implementation sub-agent, and one separate reviewer are required.

### T02 Implement canonical solution identity and reuse eligibility

- Goal: Compute fail-closed `solution_key` values and classify every executable
  node's maximum reuse residency.
- Preconditions: T01 accepted.
- Conservative write scope:
  - `ea_node_editor/execution/solution_identity.py` (new)
  - `ea_node_editor/execution/execution_plan.py`
  - `ea_node_editor/nodes/registry.py`
  - `ea_node_editor/nodes/node_specs.py`
  - `ea_node_editor/nodes/decorators.py`
  - `ea_node_editor/nodes/plugin_declaration.py`
  - `ea_node_editor/nodes/builtins/icon_catalog.py`
  - `ea_node_editor/nodes/builtin_functions/core_value.py`
  - `ea_node_editor/nodes/builtin_functions/data_control.py`
  - `ea_node_editor/nodes/builtin_functions/engineering_fem.py`
  - `ea_node_editor/nodes/builtin_functions/engineering_geometry.py`
  - `ea_node_editor/nodes/builtin_functions/engineering_imports.py`
  - `ea_node_editor/nodes/builtin_functions/engineering_viewer.py`
  - `ea_node_editor/nodes/builtin_functions/integrations_file_io.py`
  - `ea_node_editor/nodes/builtin_functions/integrations_spreadsheet.py`
  - `ea_node_editor/nodes/builtin_functions/plot_signal.py`
  - `ea_node_editor/nodes/builtin_functions/reporting.py`
  - `ea_node_editor/nodes/builtin_functions/rich_values.py`
  - `ea_node_editor/nodes/builtin_functions/spatial.py`
  - `ea_node_editor/nodes/builtin_functions/unit_math.py`
  - `ea_node_editor/nodes/builtin_functions/viewer_viewport.py`
  - `ea_node_editor/addons/tabular_data/function_nodes.py`
  - `ea_node_editor/common/payload_tools.py` only if existing canonical helpers are
    insufficient and can remain dependency-light
  - `docs/specs/perf/COREX_SOLUTION_REUSE_CLASSIFICATION.md` (new)
  - `.gitignore` exact negation for
    `docs/specs/perf/COREX_SOLUTION_REUSE_CLASSIFICATION.md` only
  - `tests/non_dpf_catalog_fixture.py`
  - `tests/test_solution_identity.py` (new)
  - `tests/test_registry_validation.py`
  - `tests/test_decorator_sdk.py`
  - `tests/test_plugin_declaration.py`
  - `tests/test_builtin_function_infrastructure.py`
  - `tests/test_corex_contract_catalog.py`
  - relevant built-in/integration/tabular migration tests
  - `docs/agent_maps/subsystems/nodes_registry_builtins.md`
  - `docs/agent_maps/subsystems/execution.md`
  - regenerated route/source indexes
- Deliverables:
  - callback-free canonical tagged encoder;
  - executable node projection excluding UI-only fields;
  - normalized execution-facing workflow-interface revision/digest required by
    durable identity;
  - public/untrusted rows hard-locked to `never`;
  - trusted factories hard-locked to `never` in T02 until content/toolchain
    identity is available;
  - one cached COREX build digest and one normalized execution-environment digest;
  - read-only `ExecutionPlan.hidden_ordering_pairs` accessor for identity without a
    private-field dependency;
  - upstream/artifact/file/toolchain/backend/implementation identity;
  - `solution_reuse_scope` and content-based implementation digest validation;
  - explicit fail-closed reason codes for ineligible nodes;
  - accepted classification inventory for every executable registry row, including
    the CAD Import/Model Viewer chain.
- Verification:
  - same executable inputs produce the same key across process restarts;
  - UI-only edits do not change a key;
  - execution property, edge enable/order, port modifier, file content, artifact
    digest, implementation, catalog revision, backend, or toolchain changes do;
  - hostile values invoke no callbacks/I/O;
  - `./venv/Scripts/python.exe -m pytest tests/test_solution_identity.py tests/test_registry_validation.py tests/test_decorator_sdk.py -q`.
- Non-goals: storing outputs, running reused results, durable files.
- Packetization notes: `P02`; split the node-classification inventory into a
  read-only classification-drafter/reviewer gate before metadata implementation,
  exactly as recorded in the ledger. No metadata edit starts before
  `CLASSIFICATION_ACCEPTED`.

### T03 Add the execution-owned session solution store

- Goal: Add the execution-owned session solution store, preparation, invalidation,
  and generation-safe settlement capture as a dormant production path; sole shell
  freshness/scheduling authority switches only in T05.
- Preconditions: T01-T02 accepted.
- Conservative write scope:
  - `ea_node_editor/execution/solution_store.py` (new)
  - `ea_node_editor/execution/headless_runtime.py`
  - `ea_node_editor/execution/client.py`
  - `ea_node_editor/execution/execution_plan.py`
  - `ea_node_editor/execution/solution_identity.py`
  - `ea_node_editor/runtime_contracts/solution_records.py`
  - `ea_node_editor/nodes/node_specs.py`
  - `ea_node_editor/nodes/registry.py`
  - `ea_node_editor/nodes/bootstrap.py` only if trusted-overlay installation cannot
    remain inside registry construction
  - `ea_node_editor/nodes/solution_provenance.py` (new)
  - `ea_node_editor/ui/shell/composition/controllers.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`
  - `tests/test_solution_store_session.py` (new)
  - `tests/test_headless_runtime.py` (new)
  - `tests/test_solution_records.py`
  - `tests/test_execution_client.py`
  - `tests/test_execution_plan.py`
  - `tests/test_solution_identity.py`
  - `tests/test_plugin_runtime_agreement.py`
  - `tests/test_registry_replacement.py`
  - `docs/agent_maps/subsystems/execution.md`
  - `tests/test_registry_validation.py`
  - `tests/test_architecture_boundaries.py`
  - `tests/test_project_session_controller_unit.py`
  - `tests/test_shell_project_session_controller.py`
  - focused reader tests identified by the accepted T03 exploration
  - `docs/agent_maps/subsystems/execution.md`
  - `docs/agent_maps/subsystems/startup_and_bootstrap.md`
  - `docs/agent_maps/subsystems/supporting_runtime_assets.md`
  - `docs/agent_maps/subsystems/nodes_registry_builtins.md`
  - `docs/agent_maps/subsystems/persistence.md`
  - `docs/agent_maps/subsystems/ui_shell.md`
  - `docs/agent_maps/subsystems/addons.md`
  - `docs/agent_maps/feature_routes/project_session_files_managed_artifacts.md`
  - `docs/agent_maps/feature_routes/neutral_cad_fe_engineering_viewer.md`
  - `docs/agent_maps/feature_routes/core_integrations_file_process_email_spreadsheet.md`
  - `docs/agent_maps/feature_routes/tabular_data_addon_preview.md`
  - regenerated route/source indexes
- Deliverables:
  - in-memory record backend;
  - immutable in-memory typed-output payload lookup with result digests;
  - `reuse_eligible` observation records for `never` rows without reuse indexing;
  - node facts and monotonic workspace solution revision;
  - saved-project namespace equals `project_id`; stable in-memory namespace for
    unsaved projects;
  - deterministic per-workspace/runtime/preparation retention ceilings, eviction,
    and pin/reservation cleanup on every terminal/reset/replacement/shutdown path;
  - route-specific generation-aware client snapshot/event API and environment
    identity, including cold unavailable behavior;
  - caller-ID run reservation and atomic preparation-consume/run-context registration
    before client start;
  - registry-owned trusted file/directory provenance overlay for accepted session
    readers;
  - bounded heterogeneous concrete output type/carrier descriptors;
  - shared `ExecutionPlan.affected_downstream_closure()` with contributing roots;
  - record publication only after validated terminal settlement;
  - affected-closure invalidation through shared `ExecutionPlan`;
  - execution-affecting workspace revision captured by preparation/dispatch;
  - late-settlement protection by captured solution key/revision;
  - execute-only keys for identity failures;
  - Trigger publication generation reservation/commit/discard;
  - runtime-generation eviction for handle-bearing/session-only records;
  - `prepare_execution()` and single-use `dispatch_prepared()` API;
  - T03 dispatch supports all-`execute` preparations only and rejects any `reuse`
    action with `prepared_reuse_not_supported_until_t04`;
  - existing `start()`/`start_run()` and shell dispatch remain unchanged until
    T04/T05;
  - project replacement/new/open clears the previous session store without adding
    durable binding.
- Verification:
  - current/expired/never transitions;
  - disconnected branches retain current records;
  - changed/downstream closure expires exactly once;
  - Trigger/disabled-edge/hidden-ordering closure and contributing-root matrix;
  - failure/cancel leaves prior record expired and intact;
  - stale late completion cannot restore current;
  - unrelated-branch invalidation does not reject a valid settlement;
  - prepared execution rejects reuse after graph/registry/runtime revision drift;
  - prepare alone does not publish/replace registry generation or alter viewer
    ownership;
  - synchronous settlement/terminal during start sees registered context; failed
    start releases reservation/context/pins;
  - generation replacement evicts all session records/payloads and expires facts;
  - per-workspace and runtime-global record/byte/preparation capacity and eviction;
  - namespace, observation-record, mixed carrier/type descriptor, execute-only key,
    Trigger reservation, and project-replacement tests;
  - `./venv/Scripts/python.exe -m pytest tests/test_solution_store_session.py tests/test_headless_runtime.py tests/test_execution_plan.py tests/test_solution_identity.py -q`;
  - `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_plugin_runtime_agreement.py tests/test_registry_replacement.py -q`;
  - `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_solution_records.py -q`;
  - `./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py -q`;
  - focused engineering/file/spreadsheet/tabular reader suites named by the T03
    explorer.
- Non-goals: worker reuse/output injection, shell/Auto freshness cutover, removal of
  `start_run`, viewer invalidation, durable repository.
- Packetization notes: `P03`; do not merge with T04 because store invariants must be
  reviewed before process-boundary reuse.

### T04 Validate and execute prepared reuse decisions in the worker

- Goal: Prevent unchanged eligible nodes from invoking their implementation while
  preserving the existing settlement stream.
- Preconditions: T01-T03 accepted.
- Conservative write scope:
  - `ea_node_editor/execution/protocol.py`
  - `ea_node_editor/execution/client.py`
  - `ea_node_editor/execution/headless_runtime.py`
  - `ea_node_editor/execution/prepared_execution.py`
  - `ea_node_editor/execution/solution_identity.py`
  - `ea_node_editor/execution/solution_store.py`
  - `ea_node_editor/execution/worker_runner.py`
  - `ea_node_editor/execution/worker_runtime.py`
  - `tests/test_execution_protocol.py`
  - `tests/test_execution_client.py`
  - `tests/test_headless_runtime.py`
  - `tests/test_solution_records.py`
  - `tests/test_solution_identity.py`
  - `tests/test_solution_store_session.py`
  - `tests/test_plugin_runtime_agreement.py`
  - `tests/test_registry_replacement.py`
  - `tests/test_execution_worker.py`
  - `tests/test_dataflow_execution_runtime.py`
  - `docs/agent_maps/subsystems/execution.md`
- Deliverables:
  - prepared decisions encoded on `StartRunCommand`;
  - strictly bounded accepted-output payloads round-trip through protocol adapters
    with node/record/key/status/digest binding;
  - worker reconstruction and plan/solution-key validation;
  - exact scheduled-node/order decision parity and shared per-node key/dependency
    reconstruction;
  - session/durable payload lookup resolves settlement status and typed outputs;
  - reused outputs installed into `NodeExecutor` in `worker_runner.py` before
    dependent execution;
  - reused nodes emit `node_settled` without `node_started`;
  - reused nodes install outputs/add `executed` exactly once in plan order, with
    cancellation polling and preserved ordered fan-in;
  - recomputed settlements publish new immutable records through `CorexRuntime`;
  - force-recompute path;
  - `CorexRuntime.start(ExecutionRequest)` becomes exactly prepare plus executable
    prepared dispatch; legacy `start_run` remains only for shell until T05;
  - `CorexRuntime.run(ExecutionRequest)` subscribes then uses the same
    prepare/dispatch path;
  - `CorexRuntime.start_run(...)` calls a renamed legacy `_start_legacy(...)` path;
    shell/RunController remain untouched in T04;
  - failed/blocked/corrupt/generation-incompatible records rejected.
- Verification:
  - second unchanged Run invokes zero node implementations for reusable nodes;
  - Run Selected reuses current upstream nodes and runs only expired/missing nodes;
  - a diamond graph reuses shared upstream once and preserves input order;
  - outputless completed/empty eligible nodes may reuse;
  - failed/blocked results never reuse;
  - handle generation and artifact integrity fail closed;
  - worker validates every prepared fingerprint, decision/key/dependency tuple,
    payload binding/digest, actual output port/catalog item, artifact, and trusted
    live handle before installing any reused output;
  - any mismatch rejects the whole run, never downgrades reuse to execute;
  - malformed, oversized, mismatched-node/record/key/status/digest/residency/runtime-
    generation accepted-output payloads are rejected before worker output
    installation;
  - protocol dict round-trip preserves valid reused EMPTY/value results and refs;
  - reused settlement events preserve residency; durable payloads reject a runtime
    generation and session payloads reject a missing/stale generation;
  - identical forced recomputation retains the established same-key record;
  - divergent forced recomputation reports nondeterminism and does not overwrite;
  - `./venv/Scripts/python.exe -m pytest tests/test_solution_records.py tests/test_solution_identity.py tests/test_solution_store_session.py tests/test_headless_runtime.py -q`;
  - `./venv/Scripts/python.exe -m pytest tests/test_execution_protocol.py tests/test_execution_client.py tests/test_execution_worker.py tests/test_dataflow_execution_runtime.py -q`;
  - `./venv/Scripts/python.exe -m pytest tests/test_plugin_runtime_agreement.py tests/test_registry_replacement.py -q`;
  - `./venv/Scripts/python.exe ./scripts/check_agent_maps.py`;
  - explicit proof that `CorexRuntime.start()` uses executable prepared dispatch,
    while legacy `start_run()` remains shell-only until T05;
  - exact headless proof that `CorexRuntime.run()` subscribes before preparation,
    dispatches the prepared command, captures terminal events, and cannot bypass
    reuse.
- Non-goals: shell/QML behavior, viewer invalidation, durable persistence.
- Packetization notes: `P04`; implementation and reviewer sub-agents must be
  different because this is the trust boundary.

### T05 Cut graph invalidation and Auto/manual scheduling over to CorexRuntime

- Goal: Remove shell cache as freshness/scheduling authority and expose generic
  node freshness for future UI.
- Preconditions: T03-T04 accepted.
- Conservative write scope:
  - `ea_node_editor/execution/headless_runtime.py`
  - `ea_node_editor/execution/solution_store.py`
  - `ea_node_editor/execution/prepared_execution.py`
  - `ea_node_editor/ui/shell/runtime_history.py`
  - `ea_node_editor/ui/shell/controllers/run_controller.py`
  - `ea_node_editor/ui/shell/state.py`
  - `ea_node_editor/ui/shell/controllers/mutation_ui_effects.py`
  - `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
  - `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
  - `ea_node_editor/ui/graph_interactions.py`
  - `ea_node_editor/ui_qml/graph_scene/context.py`
  - `ea_node_editor/ui/support/solution_output_cache.py` (new)
  - `ea_node_editor/ui/support/port_flow_state.py`
  - `ea_node_editor/ui/media_panel_source.py`
  - `ea_node_editor/ui_qml/graph_canvas_state/execution_state_props.py`
  - `ea_node_editor/ui_qml/graph_canvas_state/protocols.py`
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasExecutionFacts.qml`
  - `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
  - `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
  - `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
  - `ea_node_editor/ui/project_review_deck.py`
  - `ea_node_editor/ui/shell/presenters/project_review_deck_presenter.py`
  - `tests/test_run_controller_unit.py`
  - `tests/test_shell_run_controller.py`
  - `tests/test_port_flow_state.py`
  - `tests/test_media_panel_source_resolution.py`
  - `tests/test_data_type_ui_projection.py`
  - `tests/test_graph_scene_presentation_facts.py`
  - `tests/test_dpf_ui_summary.py`
  - `tests/test_content_fullscreen_bridge.py`
  - `tests/test_project_review_deck.py`
  - `tests/test_port_availability.py`
  - `tests/main_window_shell/bridge_support.py`
  - `tests/main_window_shell/view_library_inspector.py`
  - `tests/main_window_shell/bridge_qml_boundaries.py`
  - `tests/main_window_shell/mutation_ui_effects.py`
  - `tests/graph_track_b/qml_preference_rendering_suite.py`
  - `tests/test_headless_runtime.py`
  - `tests/test_execution_client.py`
  - `tests/test_plugin_runtime_agreement.py`
  - `tests/test_registry_replacement.py`
  - `tests/test_solution_store_session.py`
  - `tests/test_solution_records.py`
  - `docs/agent_maps/feature_routes/run_controller_selected_workspace_state.md`
  - `docs/agent_maps/feature_routes/node_execution_visualization.md`
  - `docs/agent_maps/feature_routes/clipboard_undo_redo_mutation_history.md`
  - `docs/agent_maps/feature_routes/media_image_video_pdf_refocus.md`
  - `docs/agent_maps/feature_routes/persistent_node_elapsed_times.md`
  - `docs/agent_maps/feature_routes/port_availability_and_default_values.md`
  - `docs/agent_maps/feature_routes/qml_bridge_wiring.md`
  - `docs/agent_maps/feature_routes/port_availability_and_default_values.md`
  - `docs/agent_maps/feature_routes/graph_scene_payload_and_projection.md`
  - `docs/agent_maps/feature_routes/project_session_files_managed_artifacts.md`
  - `docs/agent_maps/feature_routes/tabular_data_addon_preview.md`
  - `docs/agent_maps/subsystems/execution.md`
  - `docs/agent_maps/subsystems/ui_shell.md`
  - `docs/agent_maps/subsystems/graph_canvas.md`
  - `docs/agent_maps/subsystems/qml_shell_and_bridges.md`
  - `docs/agent_maps/testing/qml_and_graph_surface_tests.md`
  - regenerated QML/source/route indexes
- Deliverables:
  - rename the history execution classifier/hook away from persistent-elapsed
    terminology, with no compatibility alias;
  - one before/after/registry-aware classifier: cosmetic/passive-only changes do
    not advance execution revision; currently present active roots invalidate;
    removed-only executable changes advance with an empty root tuple; changed edge
    old/new targets are considered;
  - invalidation synchronizes store facts against current full-plan node IDs:
    deleted facts, current pins, and reuse indexes are removed; a session tombstone
    revision remains so undo/re-add cannot accept an old settlement;
    `InvalidationResult.removed_node_ids` drives presentation-cache cleanup;
  - remove `_AUTO_RUN_ACTION_TYPES` and duplicate Auto closure helpers;
  - history hook calls `CorexRuntime.invalidate_solution()` with normalized roots;
  - Auto uses returned affected targets;
  - Manual, Selected, Auto, and Trigger build one `ExecutionRequest` and dispatch
    through prepare/dispatch; remove `CorexRuntime.start_run()` and `_start_legacy()`;
  - Manual targets all active nodes, Selected explicit targets, Auto exact expired
    targets, Trigger retains clicked/capture fields;
  - active-run edits union pending expired targets and schedule one terminal rerun;
    Manual-to-Auto toolbar transition still requests full active-workflow evaluation;
  - pending outcome table:
    - successful `run_completed` drains exactly one unioned Auto target set when
      Auto remains enabled and the workspace is still active;
    - `run_failed`, `run_stopped`, cancellation, fatal/infrastructure/protocol
      failure clear pending targets and never auto-retry;
    - workspace switch/project replacement and Auto-to-Manual/Pause clear pending
      targets for that workspace;
    - Manual, Selected, and Trigger requests during an active run retain the
      existing reject/warn behavior and are not queued;
    - explicit Run/Run Selected that consumes Apply suppresses its duplicate Auto
      invalidation/rerun;
  - `node_solution_freshness_lookup` projects current/expired; absence means never;
  - runtime-local solution-state events notify RunController/QML after registry,
    generation, project, and explicit resets;
  - `SolutionStore.handle_event()` returns an explicit acceptance result with
    accepted record ID, solution key, result digest, and disposition only when that
    exact event became/reused the retained record; rejected/late/nondeterministic/
    capacity/failed events receive no record ID and can never stamp old retained IDs
    onto new outputs;
  - every accepted cached shell event is stamped from that acceptance result with
    record ID, solution key, disposition, typed outputs, and timestamp;
  - lock/event flow is exactly:
    `generation callback -> CorexRuntime store handling/enrichment ->
    ExecutionEventStream -> ShellWindow.execution_event ->
    RunController.handle_execution_event -> commit_node_execution_state_change ->
    node_execution_state_changed -> GraphCanvasStateBridge
    node_execution_state_changed/port_flow_state_changed -> ExecutionStateProps/QML`;
    enriched `node_settled` publishes only after store fact/record update;
    `solution_state_changed` is non-run-scoped;
  - shared retained-record selector chooses only the event matching
    `NodeSolutionFact.retained_record_id`; expired retained records remain
    inspectable/stale, expired-without-record and never expose no cached value;
  - port flow, DPF, property presentation, Panel, Media, fullscreen, graph commands,
    graph presenter, and Project Review Deck use that selector;
  - exact node-level availability clearing uses invalidation results and prepared
    recompute IDs; late/rejected settlements cannot republish availability;
  - remove mutation-time workspace-wide availability clears from
    `graph_interactions.py` and `workspace_edit_ops.py`; keep workspace clears only
    for true project/workspace replacement;
  - old mutable shell freshness fields/flags and duplicate closure logic removed;
  - keep `fresh_run_node_lookup` only as a derived current-only compatibility fact
    for unchanged visuals, not mutable authority;
  - add generic `GraphCanvasExecutionFacts.nodeSolutionFreshnessLookup` transport
    only; no styling consumer;
  - UI cache bound: maximum two records per node, 4,096 records and 512 MiB
    canonical payload per workspace; retained fact record pinned, oldest unpinned
    evicted deterministically; oversized/unfit payload becomes metadata-only and
    unavailable to previews rather than misrepresented;
  - runtime-global UI cache bound: maximum 16,384 records and 2 GiB canonical
    payload across workspaces; evict oldest unpinned cross-workspace entry by
    observed sequence, workspace ID, node ID, record ID; active retained records are
    pinned and capacity failure degrades the new entry to metadata-only;
  - preserve monotonic session-only run counts in a separate counter instead of
    deriving them from bounded cache length;
  - failed `start_reserved_run` restores pre-dispatch facts; a run that actually
    started and later failed/stopped/cancelled remains expired;
  - `solution_state_changed` payload includes project ID, workspace ID, monotonic
    solution revision, separate expired and removed node IDs, and reason;
    RunController rejects a mismatched project or non-increasing revision;
  - authoring dirty state remains separate.
- Verification:
  - cosmetic edits do not expire solutions;
  - property/node/edge changes expire exact roots/downstream with disabled-edge and
    Trigger boundaries;
  - deleted isolated executable advances revision without invalid roots;
  - active-run edits coalesce one pending Auto rerun;
  - late/rejected/nondeterministic/capacity settlements cannot become current,
    republish availability, or replace retained previews;
  - expired retained output stays inspectable but produces no flowing grip/Panel/
    media renderer; current retained output does;
  - registry/runtime resets notify freshness projection immediately;
  - failed start restores prior current fact; started-run failure remains expired;
  - `CorexRuntime.start_run` and `_start_legacy` are absent;
  - cache count/byte/record eviction and monotonic run-count tests;
  - no node styling changes appear;
  - `./venv/Scripts/python.exe -m pytest tests/test_run_controller_unit.py tests/test_shell_run_controller.py tests/test_port_flow_state.py tests/test_port_availability.py tests/test_media_panel_source_resolution.py tests/test_data_type_ui_projection.py tests/test_graph_scene_presentation_facts.py tests/test_dpf_ui_summary.py tests/test_content_fullscreen_bridge.py tests/test_project_review_deck.py tests/main_window_shell/bridge_support.py tests/main_window_shell/view_library_inspector.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/mutation_ui_effects.py tests/graph_track_b/qml_preference_rendering_suite.py -q`;
  - `./venv/Scripts/python.exe -m pytest tests/test_solution_store_session.py tests/test_headless_runtime.py tests/test_execution_client.py tests/test_plugin_runtime_agreement.py tests/test_registry_replacement.py -q`;
  - `./venv/Scripts/python.exe ./scripts/generate_source_test_file_index.py`;
  - `./venv/Scripts/python.exe ./scripts/generate_qml_navigation_index.py`;
  - `./venv/Scripts/python.exe ./scripts/generate_agent_route_index.py`;
  - `./venv/Scripts/python.exe ./scripts/check_agent_maps.py`;
  - `git diff --check`.
- Non-goals: expired-node coloring, Run Expired action, inspector, persistence;
  `_invalidate_viewer_sessions_for_rerun` filtering, viewer bridge/service/host,
  transport release, and invalidation epochs remain T06. T05 preserves existing
  blanket viewer preflight/run-required behavior while adapting dispatch only.
- Packetization notes: `P05`; QML change is transport-only and stays in the same
  packet because it consumes the new single authority.

### T06 Scope viewer and live-resource invalidation to recomputed nodes

- Goal: Keep unaffected Model Viewer sessions/transports ready during unrelated
  partial runs.
- Preconditions: T03-T05 accepted; exact prepared recompute set available.
- Conservative write scope:
  - `ea_node_editor/ui/shell/controllers/run_controller.py`
  - `ea_node_editor/ui_qml/viewer_session_bridge.py`
  - `ea_node_editor/execution/protocol.py`
  - `ea_node_editor/execution/client.py`
  - `ea_node_editor/execution/viewer_session_service.py`
  - `ea_node_editor/execution/worker_runner.py`
  - `tests/test_shell_run_controller.py`
  - `tests/test_viewer_session_bridge.py`
  - `tests/test_execution_viewer_service.py`
  - `tests/test_viewer_host_service.py`
- Deliverables:
  - exact node filters on UI/worker viewer invalidators;
  - partial run invalidates only recomputed viewers;
  - per-node viewer invalidation epochs retire affected pending requests and reject
    older responses;
  - reuse preserves session handles and transport;
  - true reset/project/registry/runtime/backend replacement remains global;
  - no Model Viewer-specific branch in generic scheduling.
- Verification:
  - primary eight-step acceptance scenario in Viewer and live-resource scoping;
  - two viewers in one workspace, recompute one, retain one;
  - empty filter invalidates none; `None` invalidates all;
  - same-branch upstream change expires/recomputes viewer and requires a new live
    transport;
  - worker reset invalidates all session-only handles;
  - delayed pre-invalidation open/update/materialize/query responses cannot restore
    ready state;
  - `./venv/Scripts/python.exe -m pytest tests/test_shell_run_controller.py tests/test_viewer_session_bridge.py tests/test_execution_viewer_service.py tests/test_viewer_host_service.py -q`.
- Non-goals: viewer QML styling or a persistent live native handle.
- Packetization notes: `P06`; primary UX acceptance packet.

### T07 Implement the durable solution repository and codecs

- Goal: Persist eligible solution records/results atomically in project-managed
  sidecar storage using the same store/record model as session reuse.
- Preconditions: T01-T04 accepted; durable eligibility and implementation identity
  gates from T02 complete.
- Conservative write scope:
  - `ea_node_editor/persistence/solution_repository.py` (new)
  - `ea_node_editor/execution/headless_runtime.py`
  - `ea_node_editor/ui/shell/composition/controllers.py`
  - `ea_node_editor/ui/shell/controllers/project_session_controller.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/session_lifecycle_service.py`
  - `ea_node_editor/persistence/artifact_store.py`
  - `ea_node_editor/runtime_contracts/runtime_values.py`
  - `tests/test_solution_repository.py` (new)
  - `tests/test_project_artifact_store.py`
  - `tests/test_architecture_boundaries.py`
- Deliverables:
  - exact `solutions/v1` layout;
  - schema-1 strict manifest/record/blob codecs;
  - immutable generation/manifest-set publication and `.cxproj` pointer contract;
  - lazy per-node record/blob load;
  - validated project open/new/replacement bind/detach lifecycle;
  - current integrity verification and recompute fallback;
  - reachability mark/prune API shared with artifact ownership;
  - live/protected/nonportable result exclusion;
  - nondeterminism conflict reporting for divergent results under one key.
- Verification:
  - restart reuse for JSON-safe typed values and supported artifact outputs;
  - corrupt/missing/hash-mismatched/path-escaping/reparse/unknown-schema records
    fail closed;
  - no pickle, callbacks, credentials, handles, absolute private paths, or temp
    refs in durable files;
  - atomic failure retains prior valid record;
  - project replacement detaches old repository and unsaved projects remain
    session-only;
  - lazy load touches only requested node data;
  - `./venv/Scripts/python.exe -m pytest tests/test_solution_repository.py tests/test_project_artifact_store.py tests/test_architecture_boundaries.py -q`.
- Non-goals: remote/global cache, cross-project deduplication, migration.
- Packetization notes: `P07`; execution timing and worktree use defer entirely to
  the current orchestration baseline in the ledger.

### T08 Integrate Save, Save As, reopen, and garbage collection

- Goal: Make project lifecycle operations transactionally preserve reachable
  durable solutions and artifacts.
- Preconditions: T07 accepted.
- Conservative write scope:
  - `ea_node_editor/ui/shell/controllers/project_session_controller.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/session_lifecycle_service.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/project_files_service.py`
  - `ea_node_editor/execution/headless_runtime.py`
  - `ea_node_editor/persistence/solution_repository.py`
  - `ea_node_editor/persistence/artifact_store.py`
  - `tests/test_project_save_as_flow.py`
  - `tests/test_project_artifact_store.py`
  - `tests/test_serializer.py`
  - `tests/test_solution_repository.py`
- Deliverables:
  - immutable-generation preflight/stage, one `.cxproj` commit point, reopen, and
    prune ordering;
  - destination descriptor rewrite and portable copy;
  - reopen verification before Save As success;
  - unreachable staged-blob recovery/GC;
  - schema-1 rejection with regeneration guidance;
  - no legacy reader or migration path.
  - Save As candidate repository binding switches only after destination reopen;
    failure restores neither metadata nor binding because the old commit remains
    authoritative.
- Verification:
  - Save and reopen reuses durable eligible nodes;
  - Save As reopens independently after source project removal from the test scope;
  - injected failures at each stage preserve prior document/manifests/artifacts;
  - clear/prune removes only unreachable content;
  - temp artifact promotion and solution manifest publication are atomic together;
  - `./venv/Scripts/python.exe -m pytest tests/test_project_save_as_flow.py tests/test_project_artifact_store.py tests/test_serializer.py tests/test_solution_repository.py -q`.
- Non-goals: compatibility migration, cloud synchronization.
- Packetization notes: `P08`; implementation sub-agent must reread T07 accepted
  contracts and the ledger before editing.

### T09 Closeout, independent review, documentation, and acceptance

- Goal: Prove the clean cutover, remove obsolete paths, and register only accepted
  requirement evidence.
- Preconditions: T01-T08 accepted; any pre-existing `docs/specs/INDEX.md` owner
  diff has been reconciled or separately authorized and the ledger dirty baseline
  has been updated before T09 starts.
- Conservative write scope:
  - obsolete cache/invalidation code and exact call sites
  - `docs/agent_maps/subsystems/execution.md`
  - `docs/agent_maps/subsystems/persistence.md`
  - `docs/agent_maps/subsystems/nodes_registry_builtins.md`
  - `docs/agent_maps/subsystems/supporting_runtime_assets.md`
  - `docs/agent_maps/subsystems/ui_shell.md`
  - `docs/agent_maps/subsystems/qml_shell_and_bridges.md`
  - `docs/agent_maps/subsystems/viewer_surfaces.md`
  - `docs/agent_maps/feature_routes/run_controller_selected_workspace_state.md`
  - `docs/agent_maps/feature_routes/node_execution_visualization.md`
  - `docs/agent_maps/feature_routes/viewer_session_overlay_fullscreen.md`
  - `docs/agent_maps/feature_routes/project_session_files_managed_artifacts.md`
  - `docs/agent_maps/feature_routes/managed_artifacts_project_data.md`
  - `docs/agent_maps/feature_routes/serialization_migration_legacy_rejection.md`
  - `docs/agent_maps/COVERAGE.md`
  - `docs/agent_route_index.md`, `docs/agent_route_index.json`,
    `docs/source_test_file_index.md`, and `docs/qml_navigation_index.json`
  - `docs/specs/requirements/20_UI_UX.md`,
    `docs/specs/requirements/50_EXECUTION_ENGINE.md`,
    `docs/specs/requirements/60_PERSISTENCE.md`,
    `docs/specs/requirements/TRACEABILITY_MATRIX.md`, and `docs/specs/INDEX.md`
  - retained QA evidence if requested by the implementation packet
- Deliverables:
  - zero duplicate scheduler/freshness authorities;
  - zero blanket partial-run viewer invalidators;
  - updated exact maps/indexes listed in the write scope;
  - `REQ-EXEC-017`/`REQ-PERSIST-026` status updated only to the level proven;
  - `REQ-UI-052` remains planned because coloring/actions/inspector are deferred;
  - independent architecture, security/data-integrity, and UX-acceptance reviews.
- Verification:
  - rerun only focused suites invalidated by T09 cleanup itself;
  - `./venv/Scripts/python.exe ./scripts/check_traceability.py`;
  - `./venv/Scripts/python.exe ./scripts/check_markdown_links.py`;
  - `./venv/Scripts/python.exe ./scripts/generate_source_test_file_index.py`;
  - `./venv/Scripts/python.exe ./scripts/generate_qml_navigation_index.py`;
  - `./venv/Scripts/python.exe ./scripts/generate_agent_route_index.py`;
  - then
    `./venv/Scripts/python.exe ./scripts/check_agent_maps.py`;
  - `./venv/Scripts/python.exe ./scripts/run_verification.py --mode fast --summarize-output` because the cutover crosses execution, persistence, shell, and viewer boundaries;
  - final display-attached manual acceptance of the disconnected Model Viewer
    scenario if the environment is stable; focused automated proof remains required
    regardless of manual availability.
- Non-goals: UI coloring, new snapshot controls, unrelated cleanup.
- Packetization notes: `P09`; reviewers must be separate from all implementation
  owners. Any reviewer finding reopens the owning task, not a new catch-all patch.

## Work Packet Conversion Map

1. `P00 Bootstrap`: create external packet manifests/prompts only after plan
   approval; copy task IDs and ledger gates verbatim; no production edits.
2. `P01 Solution Contracts And Shared Plan`: T01.
3. `P02 Canonical Identity And Eligibility`: T02.
4. `P03 Session Solution Store`: T03.
5. `P04 Worker Reuse Cutover`: T04.
6. `P05 Shell Invalidation And Freshness Projection`: T05.
7. `P06 Scoped Viewer Invalidation`: T06.
8. `P07 Durable Solution Repository`: T07.
9. `P08 Save And Save-As Transactions`: T08.
10. `P09 Closeout And Independent Acceptance`: T09.

Assignment, resume, evidence, worktree, implementation, and review gates are owned
only by `docs/PLANS/COREX_INCREMENTAL_EXECUTION_TASK_LEDGER.md`.

## Test Plan

### Required semantic matrix

- never-run node -> `never`.
- valid settlement -> `current`.
- execution-affecting node/property/edge change -> exact root/downstream
  `expired`.
- cosmetic graph edit -> no freshness change.
- disabled edge and Trigger boundary -> no propagation past boundary.
- mutation during run -> late old-key settlement cannot restore current.
- second identical Run -> reused dispositions, zero implementation calls.
- Run Selected -> reuse current upstream, recompute expired/missing upstream, do
  not run siblings.
- Auto -> only affected target closure requested; current upstream reused.
- force recompute -> valid record ignored intentionally.
- force recompute with identical outputs -> established record retained; divergent
  outputs -> nondeterminism conflict without overwrite.
- empty/outputless eligible settlement -> reusable.
- failed/blocked/cancelled/infrastructure-lost settlement -> not reusable.
- file/artifact/implementation/toolchain/backend/catalog change -> key miss and
  recompute.
- UI-only change -> key remains stable.
- stale output remains bounded/inspectable but cannot become current flow.
- worker/runtime/registry generation replacement -> session handles expire.
- durable restart -> supported records lazily restore.
- durable restart uses stable environment/interface identity, never ephemeral
  runtime-generation counters.
- corrupt or unsupported durable state -> recompute with deterministic reason.
- Save/Save As failure -> previous committed project and artifact set remain valid.
- Save As preserves logical solution identity while rewriting destination storage
  descriptors outside solution keys.
- crash before/after `.cxproj` pointer replacement resolves to one complete
  generation, never a mixed manifest set.

### Primary UX regression

Automate the disconnected Model Viewer acceptance scenario from Key Changes. The
test must assert all of the following, not merely absence of a QML label:

- unrelated branch is the only recompute target;
- viewer node freshness remains `current`;
- viewer node receives no `node_started` event;
- viewer bridge receives no run-required projection;
- worker viewer service releases no transport/owner scope for that node;
- session stays open/ready with the same transport revision;
- last cached preview/live presentation remains available throughout.
- delayed old-epoch viewer responses are discarded and cannot revive invalidated
  state.

### Data integrity and security matrix

- canonical encoder rejects hostile/custom values without callbacks;
- manifests are size/depth/count bounded;
- all logical IDs are validated and path-keyed;
- path escape, symlink/reparse, hash mismatch, truncation, and unknown schema fail
  closed;
- secret/protected/runtime-handle/native/callback/private-path values cannot become
  durable;
- immutable record conflict reports nondeterminism;
- cleanup never deletes content reachable from the previous or newly committed
  manifest set.

### Broad acceptance boundary

Run focused suites during each task. After T09 only, run the repo fast verifier
once with summarized output. Escalate to full verification only if implementation
changes shell-wide composition/startup or the user explicitly requests release
confidence.

## Assumptions

- COREX remains unreleased; internal APIs and experimental metadata may break.
- Existing architecture boundaries may be changed when the replacement ownership
  is cleaner and more intuitive; update all callers, boundary tests, and agent maps
  in the same accepted task instead of adding adapters.
- No migration or compatibility reader is required.
- The existing `.cxproj` current schema remains the project document; durable
  results live in its `.data` sidecar.
- Session reuse is delivered before durability because live handles and the primary
  Model Viewer acceptance depend on runtime-generation-local state.
- Durable eligibility remains fail closed until normalized execution identity,
  implementation digest, provenance, and output codecs are complete.
- Trigger publication/sample-and-hold remains session-only and is not a durable
  solution dependency unless a later requirement defines it.
- Nodes with side effects or untracked external state default to `never` reuse.
- Worker queues/stdin are treated as private OS-owned parent/child channels. T04
  validates structure, identity, catalog, resources, and generation; authenticated
  command envelopes/MACs are a separate security scope.
- Node coloring, expired stripes, snapshot settings UI, inspector, clear/recompute
  actions, and provenance explanations are later UI work under `REQ-UI-052`.
- Explicit value internalization/data-container nodes are a separate authored-data
  feature and are not part of solution snapshot caching.
- Orchestration mechanics are governed exclusively by
  `docs/PLANS/COREX_INCREMENTAL_EXECUTION_TASK_LEDGER.md`.
