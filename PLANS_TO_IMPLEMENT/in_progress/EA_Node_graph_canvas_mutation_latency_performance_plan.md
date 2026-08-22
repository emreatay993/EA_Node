# EA Node Graph Canvas Mutation Latency Performance Plan

## Summary

The prior stress-1200 performance work improved load, pan, zoom, edge rendering, and node-drag control paths, but it did not directly benchmark the small edit mutations that still feel multi-second in the app. This packet set measures real mutation latency first, then targets the over-broad rebuild and publish paths identified by exploration.

The working hypothesis is now specific: small graph writes are cheap, but many commits still trigger full graph-scene payload rebuilds, unconditional `nodes_changed` and `edges_changed` publishes, whole edge payload replacement, broad QML edge invalidation, and in some flows whole-workspace history snapshots. User-visible features must remain zero-loss, but obsolete compatibility seams, stale stub tests, and internal payload compatibility can be removed or rewritten when they block the current behavior fast path.

This plan is exported as a fresh-context work-packet set for `$subagent-work-packet-executor`:

- Packet set: `docs/specs/work_packets/graph_canvas_mutation_latency_performance`
- Execution model: one fresh top-level executor thread per wave
- Model policy: all exploration, implementation, remediation, and review support for this task uses `gpt-5.5` with `xhigh`
- Editing policy: substantive code edits belong only to the top-level executor for the active packet. Any spawned support subagents are read-only unless the user explicitly changes the packet contract.

## Findings

- The current harness reports load/setup, pan, zoom, combined pan/zoom, node-drag control, frame interval, renderer diagnostics, and pan/zoom-targeted profiling. It does not publish direct latency for rename, create edge, remove edge, delete node with incident edges, drag commit, or undo/redo.
- Rename flows converge on `GraphSceneMutationHistory._apply_title_update()` and `GraphModel.set_node_title()`, then rebuild all scene models and publish both node and edge changes. A title-only edit should not rebuild edge snapshots unless geometry or port eligibility changes.
- Create edge, remove edge, delete node, and drag commit converge through `WorkspaceMutationService` and `GraphModel`, then `_GraphSceneContext.rebuild_models()`. That rebuild regenerates partitioned node/backdrop/minimap/edge payloads and emits broad change signals.
- Live drag has incident-edge optimizations, but release/commit falls back to full model rebuild. Multi-selection drag commit likely pays this cost once per final commit path rather than preserving incident-only dirty sets through publish.
- QML node visibility uses a granular `QAbstractListModel`, but upstream scene payloads are rebuilt as whole lists. Edge payloads are closer to wholesale replacement: `edgePayload`, visible snapshots, retained edge model, and label repeaters can churn after small mutations.
- `GraphModel._remove_node_record` removes incident edges by scanning all edges, which is acceptable for small graphs but can be a measurable delete-node cost at stress scale.
- History capture may clone whole workspaces around small edits. That must be measured before changing it, because undo/redo is a user-visible zero-loss requirement.

## Key Changes

- Add mutation benchmark scenarios for:
  - rename node
  - drag node and commit
  - drag multi-selection and commit
  - create edge
  - remove edge
  - delete node with incident edges
  - undo/redo for supported mutation scenarios
- Add phase timing for:
  - command/bridge dispatch
  - history capture/apply
  - graph model mutation
  - payload rebuild or delta payload update
  - scene model publish
  - visible node model update
  - edge payload/snapshot/index update
  - QML delegate churn
  - first frame after mutation
- Introduce a mutation delta contract so scene publish can distinguish title-only node payload changes, node geometry changes, edge topology changes, node deletion with incident edges, and undo/redo replay.
- Optimize measured worst paths by replacing full rebuilds with targeted payload updates where the graph invariants allow it.
- Stabilize QML update paths so a single edit does not replace whole edge and label models unless topology genuinely requires it.
- Convert evidence into conservative acceptance thresholds only after baseline and post-fix data exist.

## Public Interface Changes

- Extend `ea_node_editor.ui.perf.performance_harness` with a mutation benchmark scenario, expected name `graph_mutations`.
- Extend JSON and Markdown report fields with mutation scenario samples, phase timings, payload sizes, dirty counts, and first-frame-after-mutation metrics.
- Extend `docs/specs/requirements/80_PERFORMANCE.md` and `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` with mutation-latency evidence requirements after the benchmark contract exists.
- No user-facing app behavior changes are expected from the measurement packets. Optimization packets may break internal legacy compatibility seams but must preserve current user-visible feature parity, current-schema persistence, undo/redo semantics, graph invariants, selection, hit testing, minimap/search command routing, and active extension contracts.

## Execution Tasks

### T01 - Mutation Benchmark Contract

Goal: Define exact mutation scenarios, fixture requirements, JSON schema fields, and Markdown report layout.

Preconditions: Use `examples/stress_1200_nodes.cxproj` plus one smaller deterministic fixture.

Affected files:

- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`

Deliverables:

- Scenario names and payload schema
- Report field contract for mutation samples and phase timings
- Unit tests for report shape

Verification:

- `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
- `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`

Non-goals: no optimization and no pass/fail thresholds.

### T02 - Mutation Phase Instrumentation

Goal: Add timing hooks around mutation boundaries without changing behavior.

Affected files:

- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_track_h_perf_harness.py`

Deliverables:

- Non-negative phase timings for model mutation, history, payload rebuild, publish, visible model update, edge payload update, and first frame after mutation
- Payload size and dirty-count metadata

Verification:

- `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- Focused graph-scene bridge timing tests added by the packet

Non-goals: no behavior change and no threshold enforcement.

### T03 - Real Mutation Harness And Baseline

Goal: Run mutation scenarios against the real GraphCanvas/QML path and produce baseline evidence.

Affected files:

- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- `artifacts/graph_canvas_mutation_latency_baseline/**`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`

Deliverables:

- `--scenario graph_mutations`
- JSON and Markdown mutation latency baseline report
- Fixture metadata and checksum
- Small fixture smoke test

Verification:

- `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- One offscreen small fixture benchmark
- Real stress-1200 baseline only when explicitly requested by the executor/user because it can be slow and display-sensitive

Non-goals: no optimization.

### T04 - Rename And History Fast Path

Goal: Optimize title-only rename and undo/redo replay after measurements identify the cost split.

Affected files:

- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/graph/model.py`
- focused rename/history tests under `tests/**`

Deliverables:

- Title-only rename publishes a targeted node payload change
- No edge payload/snapshot publish for title-only changes unless measured dependencies prove it is required
- History/undo remains zero-loss, with any full-workspace snapshot compatibility seam rewritten or removed only if current undo/redo behavior remains covered

Verification:

- Focused rename, undo/redo, graph-scene bridge, and mutation benchmark tests
- Before/after mutation benchmark for rename

Non-goals: edge topology optimization.

### T05 - Edge Mutation Delta Publish

Goal: Optimize create edge, remove edge, and delete node with incident edges by dirtying only affected nodes/edges and by avoiding unnecessary full payload replacement.

Affected files:

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- focused graph invariant and edge tests under `tests/**`

Deliverables:

- Edge create/remove publish edge-topology deltas plus affected endpoint node payload updates
- Node delete uses incident-edge knowledge instead of broad downstream rebuild where possible
- Existing graph invariants, hit testing, minimap/search, and persistence remain zero-loss

Verification:

- Focused graph invariant tests
- Edge snapshot/spatial index tests
- Mutation benchmark before/after for create edge, remove edge, and delete node

Non-goals: drag commit optimization.

### T06 - Drag Commit And Multi-Selection Commit Fast Path

Goal: Preserve live-drag incident-only behavior through final commit for single and multi-selection drag.

Affected files:

- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `tests/test_graph_canvas_frame_coalescing.py`
- `tests/test_edge_snapshot_spatial_index.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`

Deliverables:

- Drag release commits graph coordinates once while publishing targeted node geometry and incident-edge dirties
- Multi-selection drag commit avoids full visible model rebuild
- Snap, undo, selection, and final coordinates remain covered

Verification:

- Existing graph-surface drag guardrails
- Mutation benchmark before/after for drag commit and multi-selection drag commit

Non-goals: rename and edge-topology optimization.

### T07 - QML Edge And Delegate Stabilization

Goal: Reduce delegate churn and delayed first frame after mutations.

Affected files:

- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneLifecycle.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `ea_node_editor/ui_qml/components/graph/EdgeRetainedLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/graph_canvas_visible_model.py`
- focused QML/graph-surface tests under `tests/**`

Deliverables:

- Stable edge/delegate identity for targeted mutations
- Avoid full retained-edge and flow-label model replacement for single-edge or incident-edge updates where feasible
- First-frame-after-mutation metrics improve without losing visual fidelity after idle

Verification:

- Graph-surface passive host tests
- Edge renderer and snapshot tests
- Mutation benchmark before/after

Non-goals: graph-domain mutation semantics.

### T08 - Closeout, Thresholds, And Proof

Goal: Convert evidence into maintainable acceptance criteria and publish final proof.

Affected files:

- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `artifacts/graph_canvas_mutation_latency_final/**`

Deliverables:

- Baseline vs final mutation latency table
- Conservative thresholds derived from measured data
- Residual risk list
- Docs explaining which mutations are covered

Verification:

- `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
- Focused graph-surface guardrails
- `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
- `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`

Non-goals: new optimization work after final thresholds are set.

## Work Packet Conversion Map

- P00 Bootstrap: publish packet docs, prompts, status ledger, source plan, and index registration.
- P01 Contract: mutation benchmark contract and documentation anchors.
- P02 Instrumentation: phase timing hooks.
- P03 Harness Baseline: real GraphCanvas mutation harness and baseline artifacts.
- P04 Rename Fast Path: targeted title-only publish and history/undo treatment.
- P05 Edge Mutation Delta: create/remove/delete incident-edge dirty publish.
- P06 Drag Commit Fast Path: single and multi-selection final commit optimization.
- P07 QML Stabilization: edge/delegate update churn reduction.
- P08 Closeout: thresholds, final proof, docs, residual risks.

## Test Plan

- Unit tests for timing schema and report generation.
- Small deterministic fixture tests for each mutation scenario.
- Real stress-1200 fixture benchmark for evidence.
- Focused graph invariant tests after graph-domain optimization.
- Focused graph-surface, QML, edge snapshot, and passive host guardrails after QML update changes.
- No `xdist` requirement for mutation benchmark proof unless a packet only runs unit tests and provides a serial fallback.

## Assumptions

- The current multi-second delay is not primarily edge paint alone.
- The likely causes are over-broad scene rebuild, edge publish churn, history snapshot cost, and QML delegate/model replacement.
- The first priority is direct measurement, because pan/zoom and prior node-drag metrics are insufficient for mutation performance decisions.
- Internal compatibility may be broken aggressively because Corex is pre-release, but current user-visible behavior remains zero-loss.
