# COREX Graph Mutation Churn Remediation Plan

## Summary
- Goal: make small graph edits cost roughly `O(changed nodes + incident edges)`, not whole-scene or whole-workspace rebuilds.
- Corrected diagnosis: COREX already has delta publication, but common paths defeat or overweight it through backdrop/comment guards, cache-index rebuilds, payload copies, visible-model fallback, full-scope builder recomputation, history snapshots, persistence serialization, registry validation, delete scans, and plot signature churn.
- Order: measure first, land low-risk delta/cache fixes, then take gated high-risk backdrop and history work. Do not start with backdrop membership deltas or delta-history architecture.

## Key Changes
- Add counters for `rebuild_models()`, cache index rebuilds, edge-only reindexing, visible-model delta/fallback, and fallback reasons.
- Replace unconditional cache-index rebuilds with targeted node-safe and edge-connectivity-safe reindexing.
- Reduce payload copies only where ownership is proven; avoid blanket removal of boundary copies.
- Remove the visible-model `visibility_may_change` blanket fallback and rewrite tests around row-level sync.
- Re-enable backdrop fast paths in phases: first no-membership-change moves, then normal-node membership flips, with collapse/peek/backdrop geometry still full rebuild.
- Keep `scope_edges()` in edge routing/lane-offset paths; use cache-derived port counts only for targeted node payload builders.
- Treat history and autosave as correctness-sensitive: low-risk no-op/memo work first, delta history and epoch gating only after explicit audits.

## Public Interface Changes
- Extend `C:\Users\emre_\PycharmProjects\EA_Node_Editor\ea_node_editor\ui\perf\performance_harness.py` report output with fallback counters/reasons and cache/index/publish counters.
- Add internal cache APIs on `_GraphScenePayloadCache`: edge-connectivity reindexing and per-node incident/port-count helpers.
- Add optional builder inputs for targeted node payload builders: precomputed per-node port counts and minimal node views.
- Add history/document revision concepts only after auditing every captured state source; do not reuse unrelated run-state epochs.
- Add plot payload changed-field metadata so node title changes and plot `properties["title"]` changes are distinguished.

## Execution Tasks
### T00 - Measurement And Attribution
Goal: establish proof before optimization.
Preconditions: existing `graph_mutations` harness is available.
Conservative write scope: performance harness, graph-scene timing/counter plumbing, tests/docs for report shape.
Deliverables: baseline on `stress_1200_nodes.cxproj`, a backdrop-annotated fixture, and a high-edge-density fixture; p50 before/after tables plus fallback reason counts.
Verification: `tests/test_track_h_perf_harness.py`; one small offscreen smoke run; stress runs on the same machine for accepted deltas.
Non-goals: no optimization.
Packetization: P00/P01.

### T01 - Incremental Cache Index Maintenance
Goal: remove dead `rebuild_indexes()` work after same-index payload swaps.
Preconditions: T00 counters prove current rebuild frequency.
Conservative write scope: `...\ui_qml\graph_scene\state_support.py`, `...\ui_qml\graph_scene\payload_cache_sync.py`.
Deliverables: skip full index rebuild for node/minimap same-index swaps; add robust edge-only reindex that handles edge id, endpoint, and port changes.
Verification: index-map equivalence against full rebuild for position, title/payload, edge add/remove, and same-id endpoint/port mutation.
Non-goals: no payload ownership rewrite.
Packetization: P02.

### T02 - Multi-Delete Incident Edge Reuse
Goal: change multi-delete from `O(K*E)` scans to one incidence pass.
Preconditions: T00 delete scenario exists.
Conservative write scope: `...\ui_qml\graph_scene_mutation_history.py`.
Deliverables: build `incident_by_node` during the existing pre-delete edge scan and pass `incident_edge_ids` into `remove_node`.
Verification: functional multi-delete test with selected nodes, incident edges, and non-incident edges; delete benchmark p50 improvement.
Non-goals: no graph model API redesign.
Packetization: P03.

### T03 - Visible Model Row Delta
Goal: stop full viewport requery for ordinary visible-node movement.
Preconditions: T00 visible-model fallback counters exist.
Conservative write scope: `...\ui_qml\graph_canvas_state\visible_scene_service.py`, viewport virtualization tests.
Deliverables: remove only the early `visibility_may_change` fallback; keep dirty/deferred fallback; preserve fallback for offscreen-to-onscreen existing nodes unless marked added.
Verification: visible-to-visible, visible-to-offscreen, offscreen-to-offscreen no full requery; offscreen-to-onscreen existing-node fallback; added onscreen insert works.
Non-goals: no QML model architecture changes unless tests expose a real proxy regression.
Packetization: P04.

### T04 - Payload Copy Ownership Cleanup
Goal: collapse gratuitous deep copies without aliasing cached payloads into mutable consumers.
Preconditions: T01 landed.
Conservative write scope: `...\ui_qml\graph_scene\payload_cache_sync.py`, `...\ui_qml\graph_scene\context.py`, `...\ui_qml\graph_scene_payload\builder.py`.
Deliverables: shallow top-level x/y replacement; store fresh full-node builder payloads directly; use cache location maps for connection/title updates; fix full-payload minimap copy only in `build_added_node_payloads_for_ids`.
Verification: identity/alias tests proving cached dicts are swapped, cache node/backdrop/minimap payloads do not alias incorrectly, and QML/visible-model consumers do not mutate nested cache payloads.
Non-goals: no blanket removal of projection-layer copies.
Packetization: P05.

### T05 - Cache-Derived Targeted Port Counts
Goal: stop targeted node builders from scanning/sorting all scope edges.
Preconditions: T01/T04 landed.
Conservative write scope: graph-scene payload builder/partitioner/cache sync.
Deliverables: cache helper for per-node port counts from `incident_edge_ids_by_node_id`; thread optional counts through targeted node, connection, and added-node builders; replace edge cached builder’s `dict(workspace.nodes)` with endpoint slices.
Verification: count equivalence against old `scope_edges()` method for normal edges, multi-edges, locked/optional ports, hidden ports, and self-loops.
Non-goals: do not remove `scope_edges()` from full rebuilds or edge lane/routing payloads.
Packetization: P06.

### T06 - Backdrop And Comment-Peek Delta Phases
Goal: restore cheap moves on annotated canvases without stale membership bugs.
Preconditions: T01/T04/T05 landed and backdrop fixture baseline exists.
Conservative write scope: graph-scene context/cache, payload cache sync, backdrop partitioner, comment geometry.
Deliverables: WS4A no-membership-change normal-node move fast path; WS4B expanded-backdrop normal-node enter/leave/switch diff; WS4C keeps backdrop move/resize/collapse and comment-peek full rebuild.
Verification: no-change move, enter, leave, switch owner, nested backdrop, collapsed backdrop, and peek-active golden tests; p50 backdrop move proof.
Non-goals: no partial collapsed-boundary or backdrop-geometry delta until a complete spatial diff exists.
Packetization: P07/P08.

### T07 - History Snapshot Optimization
Goal: reduce full-workspace snapshot overhead without weakening undo/redo.
Preconditions: T00 proves history capture remains material after cache/payload work.
Conservative write scope: `...\graph\workspace_state.py`, `...\ui\shell\runtime_history.py`, graph-scene history orchestration.
Deliverables: Phase 1 mutation revision plus no-op skip/snapshot memo by exact revision; Phase 2 optional delta history with touched node/edge/view/extra-state manifests and periodic checkpoints.
Verification: byte-identical undo/redo for move, rename, resize, delete, paste, group/ungroup, comment wrap, port lock, exposed port, view/scope/selection changes.
Non-goals: do not rely on `RuntimeGraphHistory.grouped_action` reuse unless graph-scene context is migrated to call it.
Packetization: P09, with Phase 2 last and separately gated.

### T08 - Registry Prune Memoization
Goal: remove repeated validation setup during structural edits.
Preconditions: T00 or microbench wraps prune paths.
Conservative write scope: `...\graph\validated_mutation.py`, `...\graph\invariant_kernel.py`, registry validation tests.
Deliverables: memoized workspace-node view, effective-port/find-port lookup, and workspace-edge tuple per validation pass; consider incident-edge scoping only after seeding capacity/dedup state from unaffected edges.
Verification: reparent, port-hide, subnode pin, single-input capacity, duplicate connections, mutually exclusive inputs.
Non-goals: do not implement the stale “pass resolved_nodes” item; that already exists.
Packetization: P10.

### T09 - Autosave And Persistence Churn
Goal: stop no-change autosave from serializing/fingerprinting whole documents.
Preconditions: audit all `to_document()` inputs.
Conservative write scope: session lifecycle service, session store, serializer, project codec, project/session tests.
Deliverables: Stage A honor `persist_session(project_doc)`, avoid redundant snapshot deepcopy for owned docs, and return original payload from artifact-ref rewrite when replacements are empty; Stage B document epoch covering graph, view, metadata, artifact store, script editor, and session/UI state.
Verification: autosave remains fresh after graph, view, metadata, artifact, and script-editor changes; no-change ticks skip document build.
Non-goals: do not reuse run-state epochs.
Packetization: P11.

### T10 - Plot Signature Reuse
Goal: avoid plot signature/stat/cache churn on non-render-affecting edits.
Preconditions: T04 copy ownership is clear.
Conservative write scope: plot payload kind, plot auto-preview service, cache sync.
Deliverables: pass changed-field sets; distinguish `node.title` from plot `properties["title"]`; reuse old `plot_surface` only when signature inputs and source descriptor are unchanged.
Verification: node-title-only rename reuses, plot-property title recomputes, source edge/source file stat changes recompute, no-change reuse stays stable.
Non-goals: preserve current cheap signature plus async render-cache architecture.
Packetization: P12.

## Work Packet Conversion Map
- P00/P01: measurement contract, counters, fixtures, baseline.
- P02-P06: low-risk cache, delete, viewport, copy, and targeted builder fixes.
- P07/P08: gated backdrop delta phases.
- P09: history Phase 1, with Phase 2 as a separate final packet only if benchmarks justify it.
- P10-P12: registry, autosave, and plot cleanup.
- Final closeout: update performance docs, agent maps if ownership/routing changed, traceability, benchmark proof, and residual-risk notes.

## Test Plan
- Focused tests: `tests/test_track_h_perf_harness.py`, `tests/test_graph_canvas_viewport_virtualization.py`, `tests/test_group_backdrop_membership.py`, `tests/test_group_backdrop_contracts.py`, `tests/test_registry_validation.py`, `tests/test_plot_auto_preview_service.py`, `tests/test_plot_node_contracts.py`, session/autosave tests, and graph Track B via its documented runner.
- Closeout commands: `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast --summarize-output`, `.\venv\Scripts\python.exe .\scripts\check_traceability.py`, `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`.
- Benchmark acceptance: compare p50 before/after on the same machine and fixture; p95 may remain a guardrail when existing harness thresholds require it, but merge proof for this plan is p50 plus correctness tests.

## Assumptions
- COREX is unreleased, so internal compatibility shims can be removed, but user-visible behavior, current `.cxproj` persistence, undo/redo, selection/scope, and graph invariants must remain zero-loss.
- Graphify/maps remain the navigation authority before implementation; after code or architecture changes, update affected agent maps and rebuild/update Graphify outputs as repo policy requires.
- High-risk work is gated: no WS4B/WS4C relaxation or delta-history Phase 2 merges without both benchmark improvement and correctness proof.
