# Execution Snapshot, Client, Worker, And Protocol

## Purpose
Use this for runtime snapshot assembly, ordered data-edge DTOs, dependency scheduling, client/worker protocol, DataTree matching, execution artifacts, handles, and viewer execution services.

## Lookup Aliases
- `unused dynamic inputs`
- `native CURRENT resource retention`
- `runtime snapshot`
- `runtime handle lease`
- `owner-scope cleanup`
- `runtime artifact integrity`
- `memory-backed prepared scene`
- `shared memory VTK transport`
- `optimization semantic link ordering`
- `optimization design handle`

## Dynamic Inputs and Native Resources
- `ExecutionPlan.node_computation` shares the connected-input projection across `graph_changes.py`, per-node interfaces, contracts and solution keys. Complete authored ports/properties remain in runtime snapshots and workflow attestation. Schema/interface revision 5 preserves Python Script and Stream Gate computational edits.
- Process workers lease native outputs before publishing settlements. Bounded offers are claimed locally in host callbacks and settled/released asynchronously; physical worker generation and monotonic offer sequence prevent stale/replayed ownership. Failed callbacks/delivery, eviction and reset release ownership; installed CURRENT values acquire their own run leases with rollback on partial failure.
- Native-containing records support exact authenticated CURRENT reads, not general key REUSE or durable storage. Declared `never` lifetimes remain excluded. File provenance validates both connected and property paths, including changes between preparation and execution. `RuntimeArtifactService.resolve_authored_path` uses existing descriptor admission before host/worker identity hashing, so managed project files share CURRENT behavior without treating raw artifact URIs as paths. Detached-only reuse and nondeterminism behavior remain unchanged. External stdio offers are not enabled.

## Start Here
- `ea_node_editor/execution/node_computation.py` — shared participating-port/property projection for invalidation and solution identity
- `ea_node_editor/execution/solution_resources.py` — bounded process-worker resource offers, host claims and asynchronous ownership cleanup
- `tests/test_dynamic_input_execution.py` and `tests/test_process_solution_resources.py` — dynamic-input identities and real process CAD resource/provenance lifecycle
- `ea_node_editor/execution/retained_resources.py` — shared source bindings, provenance validation and strict read scopes
- `ea_node_editor/execution/settled_output_identity.py` — computational output comparison independent of Plot run occurrence
- `tests/test_runtime_retained_sources.py` — real-process partial execution, provenance, lifecycle and durable-boundary regressions
- `ea_node_editor/execution/environment_identity.py` — read-only built-in environment memo shared by preview and reservation; external probes stay on demand
- `ea_node_editor/execution/generation_messages.py` and `ea_node_editor/execution/generation_readiness.py` — complete registry agreement command, correlated readiness and physical-generation retirement
- `tests/test_generation_readiness.py` — startup side effects, immediate Run, cancellation, failure and restart checks
- `ea_node_editor/execution/request_capture.py` — detached requests and submission-time solution-state commitments
- `ea_node_editor/execution/preparation_service.py` — execution candidate computation outside lifecycle locks
- `ea_node_editor/execution/submission_service.py` — one Qt-free executor, submission identities, ordered admission and cancellation
- `ea_node_editor/execution/compiled_snapshot_cache.py` — bounded host/worker compilation reuse by full authored snapshot and registry identity
- `tests/test_execution_submission.py` — barrier-controlled preparation, dispatch, cancellation and cache ownership checks
- `ea_node_editor/execution/prepared_dispatch.py` — sealed preparation/reservation projection, detached DTOs and explicit catalog consumption checks
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/runtime_snapshot_assembly.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/execution_plan.py`
- `ea_node_editor/execution/solution_identity.py`
- `ea_node_editor/execution/solution_store.py`
- `ea_node_editor/execution/solution_backend.py`
- `ea_node_editor/execution/project_solution.py`
- `ea_node_editor/execution/runtime_requests.py`
- `ea_node_editor/execution/project_loader.py`
- `ea_node_editor/execution/runtime.py`
- `ea_node_editor/execution/runtime_cli.py`
- `ea_node_editor/execution/prepared_execution.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/transport_fields.py`
- `ea_node_editor/execution/registry_agreement.py`
- `ea_node_editor/execution/run_messages.py`
- `ea_node_editor/execution/viewer_messages.py`
- `ea_node_editor/execution/protocol_codec.py`
- `ea_node_editor/execution/worker_protocol.py`
- `ea_node_editor/execution/client_common.py`
- `ea_node_editor/execution/client_generation.py`
- `ea_node_editor/execution/process_client.py`
- `ea_node_editor/execution/external_python_client.py`
- `ea_node_editor/execution/trusted_client.py`
- `ea_node_editor/execution/backend_client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/managed_runtime.py`
- `ea_node_editor/execution/python_environment.py`
- `ea_node_editor/execution/stdio_worker.py`
- `ea_node_editor/execution/worker_runtime.py`
- `ea_node_editor/execution/plugin_worker_runtime.py`
- `ea_node_editor/execution/signal_plot_inputs.py`
- `tests/test_scientific_worker_transport.py`
- `tests/test_signal_plot_scientific_integration.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/execution/handle_registry.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/execution/prepared_scene_runtime.py`
- `ea_node_editor/execution/viewer_backend_engineering.py`
- `tests/test_handle_registry_leases.py`
- `tests/test_execution_artifact_refs.py`
- `ea_node_editor/execution/plot_backend.py`
- `ea_node_editor/execution/plot_series_decimation.py` — bounded plot-series decimation contract (min-max envelope / stride)
- `ea_node_editor/execution/plot_backend_matplotlib.py`
- `ea_node_editor/execution/plot_backend_pyqtgraph.py`
- `ea_node_editor/execution/plot_backend_pyvista.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_plan.py`
- `tests/test_solution_identity.py`
- `tests/test_solution_store_session.py`
- `tests/test_solution_backend.py`
- `tests/test_project_solution.py`
- `tests/test_runtime_requests.py`
- `tests/test_project_loader.py`
- `tests/test_runtime.py`
- `tests/test_runtime_cli.py`
- `tests/test_solution_records.py`
- `tests/test_registry_agreement.py`
- `tests/test_run_messages.py`
- `tests/test_protocol_codec.py`
- `tests/test_plugin_runtime_agreement.py`
- `tests/test_plugin_worker_loading.py`
- `tests/test_client_common.py`
- `tests/test_process_client.py`
- `tests/test_external_python_client.py`
- `tests/test_trusted_client.py`
- `tests/test_backend_client.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_viewer_invalidation_lifecycle.py`
- `tests/test_engineering_import_nodes.py`
- `tests/test_engineering_viewer_backend.py`
- `tests/test_execution_type_enforcement.py`
- `tests/test_type_forwarding_integration.py`
- `tests/test_viewer_viewport.py`
- `tests/test_security_contracts.py`
- `tests/test_parameter_setup_pool_links.py`

## Do Not Start Here
- `ea_node_editor/persistence/` for runtime snapshot behavior.
- `ea_node_editor/ui_qml/` until execution contract changes are understood.

## Common Changes

- Built-in readiness initializes worker declarations and authoritative build/environment identities without a workflow snapshot or node execution. `CorexRuntime.warm_up_builtin_generation()` shares the preparation executor; current-generation on-demand preparation uses the same handshake. Exact locally verified trusted declarations are reused while generation bytes are still verified and implementation imports remain lazy. Worker readiness is correlated by request and physical generation; replacement, death and shutdown retire pending replies. Environment previews memoize immutable digests without publishing client state. Build identity retains all file-integrity checks, bounds reads by the admitted size, and serializes first computation across host threads.

- `CorexRuntime` captures request/registry/project/solution references, delegates candidate computation to `ExecutionPreparationService`, and registers only after revalidating captured state. `SolutionStore` gives one dispatcher a preparation claim; duplicate or altered requests cannot release its owner. Reservation, retirement and wire work run outside the lifecycle lock, followed by final guarded acceptance. `ExecutionSubmissionService` publishes correlated admission before any worker events and orders cancellation after an admitted StartRun write. Shutdown can cancel immediately and queue cleanup without waiting on preparation. The shared compiled-snapshot cache retains at most two entries and 64 MiB of encoded snapshots per host/worker; each consumer owns its mutable workspace DTO.

- `RegistryAgreement` owns validated immutable metadata for a complete registry generation. Catalog revision records validate at construction; matching fingerprints still require a frozen catalog and validated peer records. Prepared values project directly without encode/decode self-checks; constructors enforce aggregate budgets and bindings. `PreparedRunDispatch` adds reservation identity, session-generation matching and normalized viewer epochs; process/stdio send its complete wire projection, while trusted execution receives a detached DTO. Raw commands retain complete admission, with catalog mismatch distinguished before carrier decoding. `tests/test_prepared_dispatch.py` proves wire parity, detached projections, single raw catalog admission and negative consumption/generation/subclass cases.

- `graph_changes.py` owns computational before/after snapshot comparison. A raw authored-state shortcut avoids resolving unchanged invalid nodes; changed properties use `NodeRegistry.execution_properties` plus resolved contracts before skipping compilation. Compiled per-node interfaces, incoming edges, and hidden links determine roots; grouping-preserving edits stay current. Conservative fallback excludes compile-only roots and retains a successful after projection.
- `PropertySpec.affects_execution=False` excludes only declared presentation properties from both invalidation and solution keys. Full snapshots and worker attestation retain them. Solution-key schema 4 and workflow-interface revision 4 bind the new semantics, including `allow_empty_string`. `tests/test_execution_graph_changes.py` and `tests/test_execution_property_contract.py` own the contract regressions.

- `ExecutionPlan.node_solution_interface_digest` identifies one producer independently of downstream/unrelated nodes; full workflow fingerprints still attest dispatch. Result records carry `node_interface_revision`/`node_interface_digest`. Identity revision 2 prevents old global-interface cache keys matching this scope.
- Partial runs use `SolutionStore.current_outputs` and explicit `READ_CURRENT`/`PRUNE` decisions to consume only demanded detached ports. Currentness, generation, pinning, record/payload digest commitments, lifetime, and full plan validation remain execution-owned. Current reads do not republish producer facts; ordering dependencies and shared recomputation expand demand. `tests/test_runtime_current_results.py` owns the mixed Model/Table, Image/Media, empty-port, malicious-payload, volatile-lineage, and real-process regressions. `StartRunCommand.recompute_mode` carries explicit force policy to worker admission.

- `ExecutionBackendClient.retire_workspace(...)` fans acknowledged retirement out to every live concrete client before run dispatch. `WorkerServices.cleanup_run(...)` explicitly closes run-owned Mechanical resources independently of retained output leases; `reset()` closes retained inspection owners too. Request-correlated retirement errors and transport death are handled separately in `client_common.py`.
- Explicit viewer invalidation sends each concrete participant's committed epoch snapshot through `InvalidateViewerSessionsCommand`. Its request/workspace/digest/generation-bound acknowledgment is transport-only. Delivery is asynchronous under reader callbacks; run admission waits at the existing retirement boundary outside the runtime lock. Trusted, process and external-stdio workers apply idle and active-run handoffs before later commands. Direct starts carry their concrete global snapshot; prepared atomic adoption and the fresh-service baseline guard remain unchanged. `tests/test_viewer_invalidation_lifecycle.py` covers project reopen, ordering, handoff, ACK rejection and direct-run alignment.
- `runtime_dto.materialize_runtime_node(...)` serializes catalog-validated native property values before the strict graph DTO reader. Compiler and ExecutionPlan share it so decoded intervals and other semantic properties can be materialized without weakening the wire format or importing persistence.
- Authored properties use `RuntimeArtifactService.materialize_authored_properties(...)` at the three `NodeExecutor` property paths in `execution/worker_runner.py`. Only canonical registered project-import refs with valid descriptors, trusted paths, and verified bytes become typed carriers. `materialize_persisted_value`, output normalization, and raw path resolution remain strict for untyped staged refs. Real process and rejection coverage is in `tests/test_canvas_import_runtime.py` and `tests/test_execution_artifact_refs.py`.
- Scientific wire values use the runtime-contract codec; Python Script/public plugin boundaries materialize isolated native values, while trusted built-ins keep shared immutable buffers. Signal Plot normalization and rendering stay execution-owned. The existing 64 MiB encoded accepted-output budget and Python Script never-reuse policy remain unchanged; large scientific codec acceptance does not imply session reuse acceptance.
- Process workers import the nodes-owned schema-2 policy from `nodes/package_schema.py`, but `plugin_worker_runtime.py` retains worker-bound generation reads, digest rechecks, static declaration reconstruction, and registry agreement. Shared policy never substitutes for worker attestation.
- `ImageValue` is the bounded immutable `COREXImage` runtime carrier: exact field types, dimensions capped at 64 MP, SHA-256, schema 1, and a 64 MiB base64 transport ceiling. PNG validation covers chunk order/length/type/CRC plus bounded incremental zlib decoding of non-interlaced IDAT data, exact IHDR-derived scanline byte counts, legal row filters, stream EOF, and no trailing stream data; Adam7 input fails closed. It uses the shared tagged runtime-value serializer and catalog validation; it is neither a handle nor a `RuntimeArtifactRef`, and `tests/test_process_client.py` proves it through the real process queue.
- Signal Plot returns a session-only `PlotValue` containing full normalized signals, validated settings, provenance and a PNG preview rendered synchronously through XY's browser-free `to_png(scale=1.0)` path. A shared catalog conversion supplies that `ImageValue` preview to image consumers without allocating a managed output file.
- Keep runtime snapshot assembly in `ea_node_editor.execution`.
- Compiler/runtime edges are structured, ordered records. Only enabled data edges contribute dependencies or values; disabled edges remain authored graph state but are absent from dependency traversal and path-wise merge.
- Headless prepare, prepared-dispatch validation, worker validation, and solution invalidation build plans from the compiled runtime workspace while retaining the authored snapshot/envelope fingerprint. `ExecutionPlan.for_invalidation(...)` alone may recover from a private topology-cycle error by using compiled declaration order so invalidation closure and stale-record cleanup remain deterministic; ordinary preparation and worker admission still reject active cycles with the existing `ValueError` text.
- Registry-backed compilation uses the same `NodeRegistry.data_types.compatibility(...)` decision as graph mutation and prunes incompatible, unresolved, or unresolvable-node/port data edges before runtime DTO assembly. It revalidates real-to-real edges after subnode flattening so two direct conversion legs never imply a chained synthetic conversion. Compilation without a registry can enforce structural rules only. Conversion remains worker-owned and is never performed by the graph or compiler.
- Compilation additionally uses graph-owned all-member forwarding compatibility before and after boundary flattening. `ExecutionPlan` holds transient inferred source contracts separately from declared runtime ports; `worker_runner.py` still validates actual Any values, including retained Trigger outputs, before a catalog-selected direct conversion and target validation. `NodeExecutor._input_result` then applies the port's declared-type input normalizer to every wired or property-default item, so readiness, connected-source provenance capture, and node code all see canonical values (proof: `tests/test_runtime_retained_sources.py`). `solution_identity.py` includes incoming source contracts and selected per-member converter revisions so consumer reuse changes without advancing Trigger publication.
- Worker evaluation follows the fixed pipeline: each enabled wire is catalog-validated or directly converted item-by-item before persisted-order fan-in; explicit property defaults are catalog-validated/coerced as untyped values; input modifiers; Item/List/Tree matching and Principal selection; sequential plugin calls; catalog validation of emitted items against the deduplicated primary-plus-accepted type union without output coercion; private atomic output aggregation; output modifiers; then DataTree publication. A scheduled node may invoke its plugin several times internally without being scheduled twice.
- The one bounded exception in default assembly is an exact built-in
  `TypedInlineValue`: the worker validates it against the candidate port types
  with `validate_carrier` and returns that same object unchanged. A wrong type,
  schema, or payload keeps the existing bounded typed-input error. Untyped
  values, Interval1D, markers, handles, artifacts, subclasses, and conversion
  behavior retain their existing paths.
- The worker resolves instance ports from normalized snapshot properties before readiness evaluation and plugin construction. The resulting topology is fixed for that runtime snapshot; plugins cannot add, remove, or rename ports during execution.
- `code.python_script` uses that same instance-resolution path in the worker: `python_script_declaration.py` revalidates the applied literal decorator source before `builtins/core.py` executes `run(ctx, ...)`. Keep timeout ownership in `execution/process_client.py`, `execution/external_python_client.py`, and `execution/trusted_client.py`, user tracebacks sanitized as `<script>`, and output checks against the resolved declaration.
- `WorkerRunner` binds `WorkerServices` to the prepared registry's active data-type catalog before constructing execution/viewer services. Handle registration requires a known concrete handle-carrier semantic type, derives its schema version from that catalog, and treats semantic type/schema plus kind/owner/generation as immutable ref identity. Resolution authenticates that stored identity first, then independently enforces catalog assignability to the consumer's expected semantic type and equality with its expected backend kind. Handle metadata is strict, bounded JSON only; large sequences use deterministic count/sample/hash summaries while full arrays, absolute paths, secrets, and live objects stay behind the handle.
- The local Windows Authentication node uses the existing
  `ExecutionContext.register_handle(...)` path to register an opaque
  run-scoped `COREX.DataTypes.WindowsIdentity` handle with kind
  `corex.windows_identity` and exact empty metadata. Existing run cleanup,
  generation checks, stale/released/cross-run rejection, and catalog binding
  own its lifecycle. The separately emitted bounded username is display-only;
  it is not authority, handle metadata, log content, or a source-import fact.
- One handle record may carry reference-counted leases for multiple run, viewer, or cache owner scopes. `release()` drops one lease, while `release_owner_scope()` cleans the complete scope. Final explicit release surfaces disposal failure; automatic run/reset cleanup warns and continues. Disposal runs once outside registry mutation, while registration and catalog rebinding commit atomically.
- `ViewerSessionService.session_handle(...)` registers the current `public_projection()` as a worker-local `COREX.Viewer.Session` / `corex.viewer_session` value under the session owner scope. Its public ref metadata contains identity only; graph/QML code must request the authoritative projection by those IDs instead of carrying transport, data refs, paths, hierarchy, or summaries in metadata.
- Viewer sessions lease source/materialized handles into a collision-safe session scope, deduplicate aliases, and acquire replacement ownership before releasing the prior ref. Run cleanup preserves active viewer/cache leases; worker reset releases viewer and prepared-scene ownership before resetting the registry.
- Memory-backed engineering scenes keep native OCP shapes inside the worker and
  expose only validated scene metadata plus VTK XML bytes. The engineering
  backend owns bounded shared-memory segments per workspace/session/revision,
  verifies lengths and SHA-256 descriptors, preserves the file-backed asset
  fallback, and releases segments idempotently on session/workspace/reset
  cleanup. Viewer sessions lease both the prepared scene and its native source.
- Commands, events, settlements, runtime snapshots, and viewer payloads use explicit DTO adapters. Present malformed mappings, lists, strings, booleans, positions, sizes, revisions, lifecycle-state literals, and timing values reject instead of becoming empty/default values; only absent optional fields use their documented defaults, including `None` for absent custom node dimensions. Outbound runtime nodes, edges, workspaces, and snapshots re-parse the complete produced document before transport handoff. Any payload containing a semantic inline/handle/artifact carrier requires the active frozen `NodeRegistry.data_types` catalog; scalar lifecycle traffic remains catalog-free.
- Every public process, external, trusted, or backend `start_run` call supplies the current frozen catalog explicitly. `StartRunCommand` transports its fingerprint plus at most 4096 deterministically sorted `family`/`type`/`conversion` revision records, never a duplicate catalog. The fingerprint alone decides agreement; valid revision differences are diagnostic-only. Mismatch output is capped at eight candidate differences and 2048 characters, with each identity capped at 160 characters using a head/tail/digest form; it never exposes `source_label` or owner-version provenance. The worker checks agreement before snapshot decode, runtime preparation, service binding, or node execution and emits terminal `catalog_mismatch` on disagreement. A malformed raw start emits a sanitized `protocol_error` and, when it contains a safe bounded `run_id`, terminal `run_failed` plus `run_state(reason="invalid_start_run")`; an active worker rejects duplicate raw starts before registry construction or rebinding.
- Public function plugins add bounded `PluginBundleRef`/`PythonFunctionRef` DTOs, `plugin_fingerprint`, and `runtime_registry_fingerprint = sha256(data_catalog_fingerprint + ":" + plugin_fingerprint)` to `StartRunCommand`. Protocol paths must resolve to direct digest-named children of the app-approved plugin-generation root; no source bytes enter commands or project documents. `CorexRuntime.replace_registry()` retires idle client generations on combined-fingerprint changes before publishing the replacement registry.
- `NodeRegistry.contract_fingerprint()` is the complete trusted/public runtime-generation identity layered alongside (not replacing) the public-plugin formula above. `StartRunCommand` also carries a bounded add-on enabled-state projection so process, external, and trusted workers rebuild the same accepted trusted registry instead of consulting default preferences. All backends retire when the full contract changes.
- `CorexRuntime.registry_publication_guard()` and the backend/client guard block run starts and new viewer admission across final registry preflight, activation, consumer publication, persistence, and rollback. Keep admission lock ordering consistent and recheck active run/viewer state inside the guard.
- Process workers build their public registry by statically parsing command-pinned generation bytes, never by rediscovering mutable author/install roots. They hash every declared member once, compile those same cached bytes under digest-derived module names, and lazily construct `PythonFunctionAdapter` only after node readiness. The preparation cache pins exact registry/bundle agreement and removes its synthetic modules on retirement; trusted in-process execution rejects active public generations before changing client state.
- Trusted in-process execution may resolve only the independently attested `corex:builtin:functions` bundle; any external function bundle still refuses before client state changes. Process and external workers use the same verified-byte loader for both internal and external function entries, and worker registry fingerprinting imports the direct `nodes.function_bundle` owner rather than public discovery.
- Process, external, and trusted backends pin the accepted catalog fingerprint to a generation. Post-terminal catalog changes recycle that generation, while a live viewer generation prevents unsafe replacement. Process/external retirement invalidates the accepted generation before shutdown, drops stale events, waits for retirement, and restores the prior generation only when retirement fails. Trusted events are source-tagged by `_GenerationTaggedEventSink`; uncaught trusted-worker failures advance to a successor generation, reset services, retire viewer ownership/requests, and emit successor-correlated failures. Timeout termination reacquires the transition lock and revalidates run, process/transport, physical generation, and accepted generation before killing anything.
- Viewer backend routing precedence is explicit `run_id`, then `(workspace_id, session_id)`, then workspace ownership. Only an unowned `open_viewer_session` may fall back to a unique active backend or the default process backend; update, close, materialize, and query fail closed when ownership is stale or absent. Opens are provisional and request-ordered: the newest pending request wins, a late older success cannot replace it, and a failed open removes only its own request before restoring the next pending request or baseline owner. Close/shutdown clear ownership, and completed-run ownership is capped at 64.
- Viewer open/update/close/materialize/query traffic carries workspace and node invalidation epochs through protocol, concrete clients, backend routing, and the worker service. `None` advances every participant's local workspace epoch once, empty is byte-identical for every participant, and non-empty advances only each participant's named local node epochs. Worker context installation is separate from snapshot validation/adoption; only legacy empty-preparation direct runs call the service's workspace-global invalidator. A reservation retains immutable process/trusted/external snapshots plus an independent high-level projection snapshot: `StartRunCommand` and worker preflight use only the selected concrete digest, while `viewer_invalidation_committed` carries the projection digest and validated concrete responses translate to projection epochs before callbacks. Commit lock order is high-level invalidation, high-level active, then each child's state and viewer locks in process/trusted/external order; the selected pre-encoded payload uses a pinned queue/transport without reacquiring those locks or invoking callbacks. Failed delivery changes no visible state. Successful delivery creates an irreversible finalizer outside generic generation filtering; it publishes adoption before draining buffered run events and clears the gate in `finally`, including generation-drift and raising-subscriber cases. Only a state-free selected service may baseline-adopt its selected concrete workspace epoch; equal is byte-identical and context/session/node epoch/lease/buffer state rejects. Reservations are bounded to 30 seconds and never retained after terminal/reset/shutdown, and legacy empty-preparation runs remain workspace-global.
- Registry publication compares exact contract fingerprints before active run/viewer/route replaceability guards in both concrete and high-level clients. An exact match is a callback-free no-op, so same-registry prepared reruns coexist with retained live viewer routes; only a differing fingerprint enters rejection/recycle/retirement paths.
- Runtime prepared dispatch retires the workspace outside lifecycle/publication locks, then revalidates workspace revision, generation, and run/viewer reservations before activation. Explicit workspace retirement also leaves the lifecycle lock free so earlier reader callbacks cannot block the ten-second acknowledgement. A fresh process generation cannot own run sessions until its first StartRun dispatch; process replacement resets that fact. Direct backend starts retain their own retirement sweep.
- Viewer traffic reuses the catalog retained by its owning run/session, and transports serialize before queue/stdin/thread handoff. Do not restore arbitrary dataclass flattening, set transport, or transport-local serializers. Viewer query `options` must round-trip unchanged.
- `Interval1D` is a first-class runtime value, not a generic tuple/list range. Queue/runtime adapters preserve its ordered endpoints through the tagged runtime-value serializer; node execution receives `Interval1D`. Presentation-only upstream display values are UI-owned and must not mutate the runtime fallback property or execution history.
- SSH/SFTP plugins use the normal synchronous worker callback path and publish opaque tagged Secret/Host mappings through `runtime_contracts/value_codec.py`. Each command/script/transfer node owns one fresh Paramiko connection, registers close callbacks for cancellation, and never stores a live client in the snapshot or project.
- Tree inputs receive the complete tree without creating iterations. Item/List inputs match branches by ordinal with repeat-last behavior; Item inputs also repeat the last item, while List inputs receive the complete selected branch for each Item-driven iteration. Explicit Principal wins; fallback selection is sole non-Tree input, then greatest path depth, greatest first-index sum, and declaration order.
- Internal results distinguish pending, value(`DataTree`), empty, and failed root errors. After upstream failure resolution and before plugin construction, `NodeExecutor` calls the shared declarative readiness evaluator with normalized properties, enabled-edge override facts, and DataTree item presence. Missing prerequisites emit warning logs and a warning-bearing `status="empty"` settlement; they do not emit error logs or fail the run. An enabled incoming settlement overrides a property default even when its value is `None`, blank text, or an empty collection; disabled-only wires do not. `False` and `0` remain supplied values. Internal `NodeInputNotReadyError` remains a defensive not-ready signal, while invalid supplied values and backend failures remain real failures.
- Run targets every active node, including ready isolated nodes and outputless sinks. Run Selected carries explicit selected/group-expanded active targets and the worker pulls their enabled upstream dependencies; selected isolated active nodes run. The upstream-chain mode and selected-run output seeding are removed.
- Parameter/Response Setup-to-Pool node links add hidden execution dependencies without becoming data edges. Each run owns fresh worker-local pool state; Construct Design freezes that state into a worker-local `corex.optimization.design` handle. Legacy COREX object IDs are deterministic, and COREX `node_<id>` identifiers project within the workspace to nonzero UUIDs while literal UUID node IDs remain unchanged.
- `NodeSettledEvent` publishes typed completed/empty/failed/blocked settlements. Trigger seeds/publications use the same typed value/empty/failure model; Trigger boundaries stop normal propagation and their publications remain runtime-only.
- `execution_plan.py` owns the shared executable topology, target/Trigger/hidden-ordering traversal, and the deterministic versioned topology fingerprint. Worker/runtime callers import it directly; `worker_runtime.py` does not re-export it.
- `solution_identity.py` owns callback-free tagged canonical hashing, the versioned bounded file/directory provenance policy, cached COREX build identity, normalized execution-environment identity, and solution-key assembly. Raw bytes, runtime handles, unsupported values, links/reparse points, changed files, and provenance limit breaches fail closed with stable reason codes.
- `ExecutionPlan.workflow_interface_digest` binds the normalized execution-facing effective ports, defaults, exposure/compatibility, readiness, principal input, and port modifiers. `hidden_ordering_pairs` is the public read-only identity input; identity code does not read the plan's private storage.
- `prepared_execution.py` owns the frozen preparation/dispatch DTOs and strict queue-boundary adapters. Runtime snapshots, triggers, and accepted outputs are detached into canonical bytes and decoded only for dispatch; raw count/size/DataTree preflight runs before DTO materialization, durable payloads reject session-only carriers, and runtime consumption state remains outside the DTO. `StartRunCommand` has one strict empty-ID legacy form and one complete prepared form carrying namespace, workspace/runtime generation, snapshot/plan/interface/environment fingerprints, Trigger generations, decisions, and accepted payloads.
- `solution_store.py` is the one session scheduler/freshness owner for namespaces, full-plan-ordered node facts/revisions, immutable records and typed payloads, bounded preparation/run pins, Trigger generation reservations, exact downstream invalidation, revision-gated late settlements, resource leases, and deterministic eviction. Invalidation removes deleted facts, pins, records, and reuse-index entries while retaining a node-revision tombstone. During an active run, a bounded worker request may expire only current observations that were accepted by that same run within one downstream closure; running and pending capture revisions, historical records, unrelated branches/workspaces, and stale or duplicate requests remain unchanged. `handle_event()` returns an explicit settlement acceptance only when that event became/reused the retained record; late/rejected/nondeterministic/capacity/failed events return no record identity.
- `solution_backend.py` owns the strict durable backend/factory ports and result DTOs; persistence implements only those ports. `solution_store.py` lazily asks the bound backend only when no fact exists or the fact is current for that exact key, then installs record/payload/index/current fact together after validation. Expired nondeterminism facts quarantine the established key. Backend replacement or session-only fallback atomically evicts prior durable-derived facts/records/indexes/preparations while preserving independent session state. Durable publication still requires a declared `durable` maximum plus the callback-free shared gate; ordinary durable ineligibility/I/O/capacity falls back to valid session reuse. Runtime-generation reset keeps the backend, while project detach closes it without deleting content.
- `solution_identity.py` owns the one per-node identity assembler used by both runtime preparation and worker preflight. The worker rebuilds the registry/catalog/plan, requires exact decision order and key/dependency parity, reparses payloads, validates result digests, actual output ports/catalog items, artifacts, and live handles, then installs every accepted reuse once in plan order without `node_started`. Any mismatch rejects the whole run before node output installation.
- `CorexRuntime.start()` and `run()` use executable prepare-plus-dispatch; `run()` subscribes before preparation. `CorexRuntime.start_run()` and `_start_legacy()` are removed, and shell Manual/Selected/Auto/Trigger requests use the same `ExecutionRequest` preparation path.
- `CorexRuntime` enriches generation-aware settlements after store handling and before publishing its event stream. Non-run-scoped strict `solution_state_changed` events carry project/workspace, monotonic solution revision, separate expired/removed IDs, and reason for invalidation plus registry/runtime/project resets. Failed `start_reserved_run` restores captured pre-dispatch facts; a run that started and then failed/stopped remains expired.
- `ExecutionBackendClient` pins one exact result-affecting route/generation/environment snapshot per reserved run and exposes caller-ID reserve/start/release APIs. Explanatory selection reasons are excluded from identity and compatibility. Prepared dispatch order is registry publication, generation snapshot, reservation, generation adoption, store context registration, then start; synchronous events therefore use the pinned run snapshot. Concrete process/external routes notify idle generation death, and retired terminal events cannot republish an old available snapshot. Environment identity remains unavailable until the route handshake binds interpreter, package, add-on, toolchain, plugin, and registry facts.
- Session handles reuse only through a live trusted-worker lease; process/external handles and unresolved resolver refs fail closed. Supported table/array refs use source-content bindings rather than handle leases. Output bindings are scoped to consumed ports; inherited source provenance and completeness also guard detached CURRENT boundaries. Source checks run at preparation, worker admission, actual reads and settlement; expensive settlement validation occurs outside the lifecycle lock with exact lifecycle revalidation before acceptance. Runtime artifacts retain their existing descriptor/content checks and leases retain their release rules.
- Connected file provenance without an effective file hash in the captured identity disables computational reuse for that producer and its descendants, including cold-generation adoption. Valid CURRENT observations remain consumable after source-version validation. Changed or incomplete source provenance walks the required ancestry instead of reusing a detached stale boundary. Eligible detached durable results rely on complete captured source/dependency keys and omit redundant session lineage; raw source refs remain durable-ineligible.
- `settled_output_identity.py` compares exact PlotValue computational content separately from its run occurrence. A same-content recomputation can publish a new current record with fresh run provenance; changed data/settings/preview/producer still trigger nondeterminism. Full result digests, accepted payload commitments and stale XY-session guards remain unchanged.
- Durable artifact checks pass the runtime service's `ProjectArtifactStore` into the durable gate, never the catalog-validating `RuntimeArtifactService.resolve_path()` route. Session reuse retains the normal runtime-service validation path.
- `project_solution.py` owns the project-save snapshot/result/candidate/adoption/GC values and deterministic token calculation. `CorexRuntime` captures the current namespace, binding revision, active generation pointer, registry/artifact-context fingerprints, current durable-maximum session records, and removed-owner filter; one deterministic SHA-256 token binds the complete canonical snapshot. Precommit staging is backend-free. After `.cxproj` publication, `prepare_project_solution_adoption(...)` freshly opens and fully validates exactly one pending candidate; adoption is an exact no-I/O swap. Bounded GC runs only after live adoption and retains incomplete-scan context for later rescans.
- `CorexRuntime.registry_publication_guard()` owns the global lock order: lifecycle first, then client publication, then brief store locks. Prepared dispatch, viewer admission, and shell registry transactions share this order.
- Settled result DTO ownership is dependency-light under `runtime_contracts/settled_results.py`. Protocol, worker, shell, and tests import those classes from the runtime-contract owner; `execution/protocol_codec.py` retains transport adapters but does not re-export the classes.
- Runtime snapshots omit removed plot-session document state; legacy `plot_session_layout` stripping is owned by persistence.
- Avoid importing persistence serializer internals from worker/runtime code.
- Test worker, client, artifact refs, handles, and viewer protocols together for cross-process changes.
- Production artifact refs always carry a concrete semantic `data_type_id`, catalog schema, canonical lowercase backend `format`, `size_bytes`, lowercase SHA-256, and bounded producer provenance. Format tokens use alphanumeric segments separated only by `.`, `_`, or `-`. Path producers use `COREX.DataTypes.Path`; local paths and duplicate format fields stay out of carrier metadata. Raw `temp://`/`saved://` strings reject at runtime boundaries, while typed refs require catalog, active-store descriptor/target, and current content-integrity agreement before resolution.
- External Python selection is whole-workflow and execution-owned. Explicit process/trusted/auto ignores stored paths; explicit external uses its own path or falls back only to a non-empty project Workflow Override. Without explicit policy, the project override selects external Python; only shell dispatch with an empty project override may supply app preference `python_runtime.default_executable`. Both stored paths blank selects the built-in process worker, with no PATH discovery.
- `workflow_python_path_from_snapshot(...)` performs text-only project extraction. `ExecutionBackendClient.start_run(...)` validates the final non-empty external path exactly once through `resolve_python_environment(...)`; bounded malformed/missing/directory/non-executable paths fail before a new worker starts. The app default never enters project metadata, runtime snapshots, graph/node records, or protocol fields.
- `ExternalPythonExecutionClient` reuses a live same-path worker without import re-probe, restart, or generation advance. New, dead, and switched workers run the bounded stdio-worker import preflight before run reservation; live viewers guard switching. Cold/switched `Popen` failure releases the reservation, accepts no new physical/catalog generation, emits a bounded error, and permits next-run recovery; a switched failure need not restore an already retired worker. Registry/catalog/plugin/protocol agreement remains post-launch.
- Managed COREX runtime preparation is execution-owned: `managed_runtime.py` creates the app-managed venv, installs the packaged COREX wheel with `[all]`, and verifies both `import corex` and the stdio worker import before the dialog writes the managed Python executable.
- MARS add-on preparation is also execution-owned but separate: source runs install only editable MARS with `--no-deps` into the active COREX interpreter, while frozen runs retain the app-managed venv and contained-wheel flow. Do not route Workflow Settings through this add-on selector.
- `ExternalPythonExecutionClient` passes the desktop-selected add-on Python path to its stdio worker so MARS executable resolution stays independent of the configured Workflow Python.
- Preserve node-scoped failure payloads for Python Script failures, including `BaseException` escapes, process worker death after `node_started`, and process-isolated `timeout_sec` kills, so canvas failure focus can mark the failed node.
- `StartRunCommand.developer_mode` rides the `trigger` channel into the worker (`NodeExecutor`/`ExecutionContext`); it selects full vs. sanitized Python Script tracebacks. The shell only sets it when the `COREX_DEV_MODE` capability ([ea_node_editor/developer_mode.py](../../../ea_node_editor/developer_mode.py)) is enabled and the hidden runtime toggle is active, so production runs always sanitize.
- Keep plot backend registry/static export contracts, PyVista 3D capability gating, and generic series coercion in `ea_node_editor.execution`; live UI surfaces and app preferences are routed through their owning UI/preferences layers.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_handle_registry_leases.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest -n 0 tests/test_viewer_invalidation_lifecycle.py -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_type_enforcement.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_handle_registry.py tests/test_typed_runtime_values.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_handle_registry.py tests/test_execution_worker.py tests/test_execution_viewer_service.py tests/test_engineering_import_nodes.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_registry_agreement.py tests/test_run_messages.py tests/test_protocol_codec.py tests/test_execution_viewer_protocol.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py tests/test_client_common.py tests/test_process_client.py tests/test_external_python_client.py tests/test_trusted_client.py tests/test_backend_client.py tests/test_execution_artifact_refs.py tests/test_execution_viewer_protocol.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py tests/test_execution_worker.py tests/test_backend_client.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_external_python_client.py tests/test_backend_client.py -k "workflow_python or external_python or external_executable or application_default_python" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k "application_default_python" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_node_contracts.py tests/test_plot_headless_export.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_backend_registry.py tests/test_plot_headless_export.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_dataflow_execution_runtime.py tests/test_data_tree_contract.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_solution_identity.py tests/test_execution_plan.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_runtime_requests.py tests/test_project_loader.py tests/test_runtime.py tests/test_runtime_cli.py tests/test_solution_backend.py tests/test_project_solution.py tests/test_solution_store_session.py tests/test_execution_plan.py tests/test_solution_identity.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_runtime.py tests/test_solution_backend.py tests/test_project_solution.py tests/test_solution_store_session.py -k "durable or solution_repository or project_solution" -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_type_enforcement.py tests/test_viewer_viewport.py tests/test_security_contracts_types.py --ignore=venv -q
```

## Breadcrumbs
- [Node Execution Visualization](../feature_routes/node_execution_visualization.md)
- [Run Controller And Selected Workspace State](../feature_routes/run_controller_selected_workspace_state.md)
- [Viewer Session, Native Overlay, And Fullscreen](../feature_routes/viewer_session_overlay_fullscreen.md)
- [Plotter Nodes](../feature_routes/plotter_nodes.md)
- [SSH/SFTP Nodes](../feature_routes/ssh_sftp_nodes.md)

## Update Triggers
Update when runtime DTOs, prepared-execution contracts, shared plan topology/fingerprints, catalog/plugin/runtime-registry agreement and fingerprint adapters, raw worker bootstrap, snapshot assembly, instance-port resolution, ordered data-edge or semantic-link dependency compilation, DataTree/Interval 1D/typed-default matching or serialization, declarative readiness evaluation, dependency scheduling, optimization pool/design-handle state, typed settlements or Trigger publications, Workflow/app-default Python routing or external-worker lifecycle, managed or add-on runtime preparation, workspace retirement fan-out, node-scoped fatal failures/timeouts, handle leases/scoped disposal, Windows identity handle production, artifact integrity, prepared scenes, shared-memory viewer transports, viewer services, plot backend contracts, export backends, or execution tests change.

## 2026-07-11 Performance Ownership

- `execution/compiler.py` reuses one invariant kernel and validation memo per compilation pass while preserving runtime DTO/compiler output. Runtime-snapshot DTO/copy redesign remains outside this performance program.
- `execution/compiled_snapshot_cache.py` owns bounded compiled-snapshot reuse by the full authored payload and registry identity. The canonical dispatch fingerprint is computed lazily from the validated encoded snapshot and shared by the entry's consumers; invalidation does not compute an unused dispatch commitment.
