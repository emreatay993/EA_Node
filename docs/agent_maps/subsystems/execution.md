# Execution Snapshot, Client, Worker, And Protocol

## Purpose
Use this for runtime snapshot assembly, ordered data-edge DTOs, dependency scheduling, client/worker protocol, DataTree matching, execution artifacts, handles, and viewer execution services.

## Lookup Aliases
- `runtime snapshot`
- `runtime handle lease`
- `owner-scope cleanup`
- `runtime artifact integrity`
- `memory-backed prepared scene`
- `shared memory VTK transport`
- `optimization semantic link ordering`
- `optimization design handle`

## Start Here
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/runtime_snapshot_assembly.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/managed_runtime.py`
- `ea_node_editor/execution/python_environment.py`
- `ea_node_editor/execution/stdio_worker.py`
- `ea_node_editor/execution/worker_runtime.py`
- `ea_node_editor/execution/plugin_worker_runtime.py`
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
- `tests/test_execution_protocol.py`
- `tests/test_plugin_runtime_agreement.py`
- `tests/test_plugin_worker_loading.py`
- `tests/test_execution_client.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_engineering_import_nodes.py`
- `tests/test_engineering_viewer_backend.py`
- `tests/test_execution_type_enforcement.py`
- `tests/test_viewer_viewport.py`
- `tests/test_security_contracts.py`
- `tests/test_parameter_setup_pool_links.py`

## Do Not Start Here
- `ea_node_editor/persistence/` for runtime snapshot behavior.
- `ea_node_editor/ui_qml/` until execution contract changes are understood.

## Common Changes
- `ImageValue` is the bounded immutable `COREXImage` runtime carrier: exact field types, dimensions capped at 64 MP, SHA-256, schema 1, and a 64 MiB base64 transport ceiling. PNG validation covers chunk order/length/type/CRC plus bounded incremental zlib decoding of non-interlaced IDAT data, exact IHDR-derived scanline byte counts, legal row filters, stream EOF, and no trailing stream data; Adam7 input fails closed. It uses the shared tagged runtime-value serializer and catalog validation; it is neither a handle nor a `RuntimeArtifactRef`, and `tests/test_execution_client.py` proves it through the real process queue.
- Signal Plot renders synchronously through XY's native browser-free `to_png(scale=1.0)` path and returns ImageValue bytes without allocating a managed output file.
- Keep runtime snapshot assembly in `ea_node_editor.execution`.
- Compiler/runtime edges are structured, ordered records. Only enabled data edges contribute dependencies or values; disabled edges remain authored graph state but are absent from dependency traversal and path-wise merge.
- Registry-backed compilation uses the same `NodeRegistry.data_types.compatibility(...)` decision as graph mutation and prunes incompatible, unresolved, or unresolvable-node/port data edges before runtime DTO assembly. It revalidates real-to-real edges after subnode flattening so two direct conversion legs never imply a chained synthetic conversion. Compilation without a registry can enforce structural rules only. Conversion remains worker-owned and is never performed by the graph or compiler.
- Worker evaluation follows the fixed pipeline: each enabled wire is catalog-validated or directly converted item-by-item before persisted-order fan-in; explicit property defaults are catalog-validated/coerced as untyped values; input modifiers; Item/List/Tree matching and Principal selection; sequential plugin calls; catalog validation of emitted items against the deduplicated primary-plus-accepted type union without output coercion; private atomic output aggregation; output modifiers; then DataTree publication. A scheduled node may invoke its plugin several times internally without being scheduled twice.
- The one bounded exception in default assembly is an exact built-in
  `TypedInlineValue`: the worker validates it against the candidate port types
  with `validate_carrier` and returns that same object unchanged. A wrong type,
  schema, or payload keeps the existing bounded typed-input error. Untyped
  values, Interval1D, markers, handles, artifacts, subclasses, and conversion
  behavior retain their existing paths.
- The worker resolves instance ports from normalized snapshot properties before readiness evaluation and plugin construction. The resulting topology is fixed for that runtime snapshot; plugins cannot add, remove, or rename ports during execution.
- `core.python_script` uses that same instance-resolution path in the worker: `python_script_declaration.py` revalidates the applied literal decorator source before `builtins/core.py` executes `run(ctx, ...)`. Keep timeout ownership in `execution/client.py`, user tracebacks sanitized as `<script>`, and output checks against the resolved declaration.
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
- Viewer sessions lease source/materialized handles into a collision-safe session scope, deduplicate aliases, and acquire replacement ownership before releasing the prior ref. Run cleanup preserves active viewer/cache leases; worker reset releases viewer, prepared-scene, and DPF ownership before resetting the registry.
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
- Process, external, and trusted backends pin the accepted catalog fingerprint to a generation. Post-terminal catalog changes recycle that generation, while a live viewer generation prevents unsafe replacement. Process/external retirement invalidates the accepted generation before shutdown, drops stale events, waits for retirement, and restores the prior generation only when retirement fails. Trusted events are source-tagged by `_GenerationTaggedEventSink`; uncaught trusted-worker failures advance to a successor generation, reset services, retire viewer ownership/requests, and emit successor-correlated failures. Timeout termination reacquires the transition lock and revalidates run, process/transport, physical generation, and accepted generation before killing anything.
- Viewer backend routing precedence is explicit `run_id`, then `(workspace_id, session_id)`, then workspace ownership. Only an unowned `open_viewer_session` may fall back to a unique active backend or the default process backend; update, close, materialize, and query fail closed when ownership is stale or absent. Opens are provisional and request-ordered: the newest pending request wins, a late older success cannot replace it, and a failed open removes only its own request before restoring the next pending request or baseline owner. Close/shutdown clear ownership, and completed-run ownership is capped at 64.
- Viewer traffic reuses the catalog retained by its owning run/session, and transports serialize before queue/stdin/thread handoff. Do not restore arbitrary dataclass flattening, set transport, or transport-local serializers. Viewer query `options` must round-trip unchanged, and legacy DPF source-key aliases require both the fields-container semantic type ID and backend handle kind.
- `Interval1D` is a first-class runtime value, not a generic tuple/list range. Queue/runtime adapters preserve its ordered endpoints through the tagged runtime-value serializer; node execution receives `Interval1D`. Presentation-only upstream display values are UI-owned and must not mutate the runtime fallback property or execution history.
- SSH/SFTP plugins use the normal synchronous worker callback path and publish opaque tagged Secret/Host mappings through `runtime_values.py`. Each command/script/transfer node owns one fresh Paramiko connection, registers close callbacks for cancellation, and never stores a live client in the snapshot or project.
- Tree inputs receive the complete tree without creating iterations. Item/List inputs match branches by ordinal with repeat-last behavior; Item inputs also repeat the last item, while List inputs receive the complete selected branch for each Item-driven iteration. Explicit Principal wins; fallback selection is sole non-Tree input, then greatest path depth, greatest first-index sum, and declaration order.
- Internal results distinguish pending, value(`DataTree`), empty, and failed root errors. After upstream failure resolution and before plugin construction, `NodeExecutor` calls the shared declarative readiness evaluator with normalized properties, enabled-edge override facts, and DataTree item presence. Missing prerequisites emit warning logs and a warning-bearing `status="empty"` settlement; they do not emit error logs or fail the run. An enabled incoming settlement overrides a property default even when its value is `None`, blank text, or an empty collection; disabled-only wires do not. `False` and `0` remain supplied values. Internal `NodeInputNotReadyError` remains a defensive not-ready signal, while invalid supplied values and backend failures remain real failures.
- Run targets every active node, including ready isolated nodes and outputless sinks. Run Selected carries explicit selected/group-expanded active targets and the worker pulls their enabled upstream dependencies; selected isolated active nodes run. The upstream-chain mode and selected-run output seeding are removed.
- Parameter/Response Setup-to-Pool node links add hidden execution dependencies without becoming data edges. Each run owns fresh worker-local pool state; Construct Design freezes that state into a worker-local `corex.optimization.design` handle. Legacy COREX object IDs are deterministic, and COREX `node_<id>` identifiers project within the workspace to nonzero UUIDs while literal UUID node IDs remain unchanged.
- `NodeSettledEvent` publishes typed completed/empty/failed/blocked settlements. Trigger seeds/publications use the same typed value/empty/failure model; Trigger boundaries stop normal propagation and their publications remain runtime-only.
- Runtime snapshots omit removed plot-session document state; legacy `plot_session_layout` stripping is owned by persistence.
- Avoid importing persistence serializer internals from worker/runtime code.
- Test worker, client, artifact refs, handles, and viewer protocols together for cross-process changes.
- Production artifact refs always carry a concrete semantic `data_type_id`, catalog schema, canonical lowercase backend `format`, `size_bytes`, lowercase SHA-256, and bounded producer provenance. Format tokens use alphanumeric segments separated only by `.`, `_`, or `-`. Path producers use `COREX.DataTypes.Path`; local paths and duplicate format fields stay out of carrier metadata. Raw `temp://`/`saved://` strings reject at runtime boundaries, while typed refs require catalog, active-store descriptor/target, and current content-integrity agreement before resolution.
- Workflow Settings > Environment > Python Executable is execution-owned: a non-empty project metadata value selects the external Python stdio worker for the whole workflow, while an empty value keeps the default packaged/process worker.
- Managed COREX runtime preparation is execution-owned: `managed_runtime.py` creates the app-managed venv, installs the packaged COREX wheel with `[all]`, and verifies the stdio worker import before the dialog writes the managed Python executable.
- MARS add-on preparation is also execution-owned but separate: source runs install only editable MARS with `--no-deps` into the active COREX interpreter, while frozen runs retain the app-managed venv and contained-wheel flow. Do not route Workflow Settings through this add-on selector.
- `ExternalPythonExecutionClient` passes the desktop-selected add-on Python path to its stdio worker so MARS executable resolution stays independent of the configured Workflow Python.
- Preserve node-scoped failure payloads for Python Script failures, including `BaseException` escapes, process worker death after `node_started`, and process-isolated `timeout_sec` kills, so canvas failure focus can mark the failed node.
- `StartRunCommand.developer_mode` rides the `trigger` channel into the worker (`NodeExecutor`/`ExecutionContext`); it selects full vs. sanitized Python Script tracebacks. The shell only sets it when the `COREX_DEV_MODE` capability ([ea_node_editor/developer_mode.py](../../../ea_node_editor/developer_mode.py)) is enabled and the hidden runtime toggle is active, so production runs always sanitize.
- Keep plot backend registry/static export contracts, PyVista 3D capability gating, generic series coercion, and DPF plot frame-selector normalization in `ea_node_editor.execution`; live UI surfaces and app preferences are routed through their owning UI/preferences layers.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_handle_registry_leases.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_type_enforcement.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_handle_registry.py tests/test_typed_runtime_values.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_handle_registry.py tests/test_execution_worker.py tests/test_execution_viewer_service.py tests/test_engineering_import_nodes.py tests/test_dpf_runtime_service.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_protocol.py tests/test_execution_viewer_protocol.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py tests/test_execution_client.py tests/test_execution_artifact_refs.py tests/test_execution_viewer_protocol.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py tests/test_execution_worker.py tests/test_execution_client.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_node_contracts.py tests/test_plot_headless_export.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_backend_registry.py tests/test_plot_headless_export.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_dpf_node_contracts.py tests/test_dpf_runtime_service.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_dataflow_execution_runtime.py tests/test_data_tree_contract.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_execution_type_enforcement.py tests/test_viewer_viewport.py tests/test_security_contracts_types.py --ignore=venv -q
```

## Breadcrumbs
- [Node Execution Visualization](../feature_routes/node_execution_visualization.md)
- [Run Controller And Selected Workspace State](../feature_routes/run_controller_selected_workspace_state.md)
- [Viewer Session, Native Overlay, And Fullscreen](../feature_routes/viewer_session_overlay_fullscreen.md)
- [Plotter Nodes](../feature_routes/plotter_nodes.md)
- [Ansys DPF Operator Nodes, Viewer, And Transport](../feature_routes/ansys_dpf_operator_viewer_transport.md)
- [SSH/SFTP Nodes](../feature_routes/ssh_sftp_nodes.md)

## Update Triggers
Update when runtime DTOs, catalog/plugin/runtime-registry agreement and fingerprint adapters, raw worker bootstrap, snapshot assembly, instance-port resolution, ordered data-edge or semantic-link dependency compilation, DataTree/Interval 1D/typed-default matching or serialization, declarative readiness evaluation, dependency scheduling, optimization pool/design-handle state, typed settlements or Trigger publications, Workflow Python executable routing, managed or add-on runtime preparation, node-scoped fatal failures/timeouts, handle leases/scoped disposal, Windows identity handle production, artifact integrity, prepared scenes, shared-memory viewer transports, viewer services, plot backend contracts, DPF plot frame-selection contracts, export backends, or execution tests change.

## 2026-07-11 Performance Ownership

- `execution/compiler.py` reuses one invariant kernel and validation memo per compilation pass while preserving runtime DTO/compiler output. Runtime-snapshot DTO/copy redesign remains outside this performance program.
