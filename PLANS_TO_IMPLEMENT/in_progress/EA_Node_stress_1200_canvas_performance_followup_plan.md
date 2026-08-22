# EA_Node Stress 1200 GraphCanvas Performance Follow-Up Plan

## Summary
- This plan is a follow-up to the completed `GRAPH_CANVAS_PERFORMANCE` packet set. That packet set added backend diagnostics, zero-loss mode semantics, node virtualization, edge spatial indexing, grid changes, cache policy, overlay sync, and a `QQuickView` host experiment, but the status ledger still records mostly offscreen/smaller-scene evidence and residual `REQ-PERF-002` timing risk. The immediate goal here is to make `examples/stress_1200_nodes.cxproj` responsive for pan, zoom, and drag without hiding or removing features. Treat GPU usage as one part of the diagnosis: if the UI thread is spending seconds copying model lists, rebuilding delegates, or repainting edge snapshots, the GPU will not rescue the interaction path until that CPU work is removed or coalesced.

Confirmed stress fixture facts:
- Fixture: `examples/stress_1200_nodes.cxproj`
- Active workspace: `ws_perf_h`
- Graph size: `1200` nodes / `1199` edges
- Node mix: `1198` `core.logger`, `1` `core.start`, `1` `core.end`
- Approximate scene bounds from node positions: `x=0..8580`, `y=0..4060`
- Current gap: the fixture is checked in but is not referenced by the benchmark harness, verification manifest, perf QA matrix, or tests.

Primary diagnosis from code inspection:
- `ea_node_editor/ui/perf/performance_harness.py` benchmarks synthetic graphs and heavy-media scenes, but cannot load `stress_1200_nodes.cxproj` directly.
- `ea_node_editor/ui_qml/qml_host_factory.py` defaults to `QQuickWidget`; `qquickview_container` exists but remains opt-in and lacks display-attached stress-fixture A/B evidence.
- `ea_node_editor/ui_qml/qtquick_backend.py` can select RHI backends, but backend choice is not tied to a stress-fixture pass/fail gate.
- `GraphCanvasRootLayers.qml` has viewport filtering, but it still reads `sceneStateBridge.nodes_model` and filters the full list in QML. That can copy and scan the full node list on every viewport state change.
- `GraphCanvasStateBridge` already exposes Python-side `visible_nodes_model` and `visible_backdrop_nodes_model`, but `GraphCanvasRootLayers.qml` does not use them as the primary source.
- `EdgeSnapshotCache.js` has a spatial index, but `buildVisibleEdgeSnapshots()` still loops through the full `edges` list, keeps all edge snapshots, and may run crossing metadata on broad snapshot sets.
- `GraphCanvasInputLayers.qml` and `GraphNodeHostGestureLayer.qml` dispatch pan and drag changes directly from mouse movement. Drag offsets feed `GraphCanvasSceneState.qml`, `EdgeLayer.qml`, and overlay sync, so an uncoalesced mouse stream can cause more work than one frame can display.

Model routing note:
- The planning explorer used to prepare this packet set and every explorer, remediation, review, or debug subagent used throughout execution of this plan must use `gpt-5.5` with `xhigh`. Do not route plan exploration or packet support to Spark, mini, or lower-reasoning models.

## Key Changes
- Add a fixture-backed benchmark/profiler path for `examples/stress_1200_nodes.cxproj`, with display-attached desktop runs and explicit `QQuickWidget` vs `QQuickView` plus RHI backend reporting.
- Convert node visibility from per-frame QML full-list filtering into a bridge-owned, indexed, incremental visible-node model with stable update metrics.
- Replace visible edge handling with true visible-only snapshots and incident-edge refresh during node drag, while keeping full graph data available for selection, commands, minimap, search, hit testing, and persistence.
- Coalesce pan, zoom, drag-offset, edge, overlay, and grid invalidations to a frame budget so mouse events cannot trigger multi-second redraw storms.
- Keep all optimizations zero-loss: grid, minimap, labels, shadows, edge crossing styles, overlays, context menus, tooltips, embedded viewers, execution visualization, and node controls remain available in the accepted path.
- Use GPU/backend changes only after the stress fixture shows whether the bottleneck is backend selection, `QQuickWidget` composition, UI-thread QML/JS work, Python bridge copying, edge painting, delegate churn, minimap, grid, or overlays.

## Public Interface Changes
- Add benchmark CLI options:
  - `--project-path <path>` to load an existing `.cxproj` through the project serializer.
  - `--workspace-id <id>` to select a workspace when the file has multiple workspaces.
  - `--qml-host qquickwidget|qquickview_container` to force the shell/canvas host for benchmark runs.
  - `--qsg-rhi-backend auto|d3d11|d3d12|opengl|vulkan|metal|software` to set the existing backend override for the benchmark process.
  - `--stress-fixture` as a convenience alias for `examples/stress_1200_nodes.cxproj` and workspace `ws_perf_h`.
- Add artifact directories for fixture proof:
  - `artifacts/graph_canvas_stress_1200_baseline/`
  - `artifacts/graph_canvas_stress_1200_qquickwidget/`
  - `artifacts/graph_canvas_stress_1200_qquickview/`
  - `artifacts/graph_canvas_stress_1200_final/`
- Optional later UI change after evidence: expose a graphics host/backend diagnostic in the graphics settings dialog or status strip. Do not change the default host/backend until a display-attached fixture benchmark proves parity and performance.

## Execution Tasks

### T01 Fixture Baseline And Bottleneck Classification
- Goal: Make `stress_1200_nodes.cxproj` a repeatable benchmark target and classify the current delay before changing render behavior.
- Preconditions: Use the project venv at `.\venv\Scripts\python.exe`. Do not rely on offscreen/software runs for final desktop conclusions.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `scripts/profile_canvas_lag.py`
  - `tests/test_track_h_perf_harness.py`
  - `scripts/verification_manifest.py`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- Deliverables:
  - Add `--project-path`, `--workspace-id`, and `--stress-fixture` loading to the harness using `JsonProjectSerializer.load()`.
  - Preserve synthetic scenarios; fixture mode is additive.
  - Report fixture metadata: project path, workspace id, node count, edge count, node type histogram, scene bounds, active graphics API, QML host kind, `QT_QPA_PLATFORM`, `QT_QUICK_BACKEND`, `QSG_RHI_BACKEND`, `QSG_RENDER_LOOP`, DPR, readback inclusion, and no-readback frame interval.
  - Capture per-sample submetrics already exposed by QML: visible node delegates, total node count, visible edge count, candidate edge count, edge snapshot refresh time, grid update/paint time, frame scheduler coalescing counters, overlay sync time, and node-drag p95.
  - Add a profile mode that runs the same fixture through `scripts/profile_canvas_lag.py`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q`
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_baseline`
  - Display-attached run on Windows with no forced offscreen platform. Record whether timings include `grabWindow()` and compare to `frame_interval_ms_without_readback`.
- Non-goals: Do not change rendering, default host, backend defaults, or canvas behavior in this task.
- Packetization notes: Convert to `P01 Stress Fixture Baseline`. This packet blocks all optimization packets because later work needs before/after evidence.

### T02 Renderer And UI-Thread Instrumentation
- Goal: Add enough internal timing to know whether seconds-long stalls come from bridge model copying, QML delegate churn, edge snapshot work, Canvas/Grid work, QQuickWidget composition, or GPU/RHI backend.
- Preconditions: `T01` fixture benchmark exists.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasViewportController.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui/perf/performance_harness.py`
- Deliverables:
  - Add per-frame diagnostic payloads for view-state redraw requests, edge redraw requests, overlay redraw requests, flushed frame count, coalesced request count, visible-model query time, delegate create/destroy counts, edge snapshot build time, edge paint time, grid paint/update time, and live-drag offset update count.
  - Add a single benchmark report table called `Stress 1200 Bottleneck Breakdown`.
  - Add optional `QSG_INFO=1` capture support in the profiling script for manual runs, but do not require it in CI.
  - Make diagnostics cheap when disabled. The accepted app path should not collect expensive per-node traces continuously.
- Verification:
  - Focused QML/perf tests already used by Track H, plus `tests/test_graph_canvas_viewport_virtualization.py`.
  - One fixture run confirming the new fields are present and numeric.
- Non-goals: Do not optimize yet; this task exists to prevent guessing.
- Packetization notes: Convert to `P02 Stress Diagnostics`. It can land immediately after `P01`.

### T03 Desktop GPU Host And Backend A/B Gate
- Goal: Prove whether the real desktop path is using hardware Qt Quick and whether `QQuickView` removes a meaningful composition bottleneck compared with `QQuickWidget`.
- Preconditions: `T01` and `T02` metrics are available.
- Conservative write scope:
  - `ea_node_editor/ui_qml/qtquick_backend.py`
  - `ea_node_editor/ui_qml/qml_host_factory.py`
  - `ea_node_editor/ui_qml/shell_context_bootstrap.py`
  - `ea_node_editor/ui/shell/window.py`
  - `ea_node_editor/ui/shell/host_presenter.py`
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `scripts/profile_canvas_lag.py`
  - `tests/test_shell_window_lifecycle.py`
  - `tests/test_track_h_perf_harness.py`
- Deliverables:
  - Add harness parameters that set `EA_NODE_EDITOR_QML_HOST` and `EA_NODE_EDITOR_QSG_RHI_BACKEND` before Qt initialization.
  - Run the stress fixture across at least:
    - `QQuickWidget` + Qt default backend
    - `QQuickWidget` + `d3d11`
    - `QQuickView` container + Qt default backend
    - `QQuickView` container + `d3d11`
    - Optional Windows-only comparison: `d3d12` and `opengl`
  - Capture parity facts for context menus, keyboard focus, overlay mapping, drag, pan, zoom, minimap, status strip, and embedded viewer overlay ownership.
  - Decide whether `qquickview_container` should remain experimental, become a user preference, or become default on Windows.
- Verification:
  - Unit tests for backend/host normalization.
  - Existing shell lifecycle tests.
  - Manual display-attached A/B run with the stress fixture.
- Non-goals: Do not make `QQuickView` default until the parity checklist is complete. Do not force a single RHI backend globally without evidence.
- Packetization notes: Convert to `P03 Desktop Host Backend AB`. This can run in parallel with later CPU optimization only after `P01`/`P02`, but default changes must wait for final closeout.

### T04 Bridge-Owned Viewport Model Index
- Goal: Stop copying and scanning the full node list in QML on every pan/zoom. Build a Python-side indexed visible-node model that can answer viewport queries cheaply and expose metrics.
- Preconditions: `T01` proves the stress fixture is in the harness. `T02` confirms model filtering/copying or delegate churn is material.
- Conservative write scope:
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `ea_node_editor/ui_qml/viewport_bridge.py`
  - `ea_node_editor/ui_qml/graph_scene_bridge.py` and graph-scene state support only if needed for stable source signals.
  - New helper if useful: `ea_node_editor/ui_qml/graph_canvas_viewport_index.py`
  - `tests/test_graph_canvas_viewport_virtualization.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Add an indexed cache keyed by node id and node bounds for `nodes_model` and `backdrop_nodes_model`.
  - Invalidate the index only when node geometry, workspace, or node list revisions change.
  - Query visible nodes from the expanded visible scene rect, not the raw viewport. Keep activation padding equivalent to `nodeRenderActivationPaddingPx`.
  - Preserve active exceptions: selected, failed, running, warning, hovered, context-menu target, pending wire source/target, drop candidate, live drag nodes, and resized nodes.
  - Expose `visible_nodes_model`, `visible_backdrop_nodes_model`, and diagnostics: full count, visible count, query ms, rebuild ms, cache hit/miss, and forced-visible count.
  - Avoid returning a freshly copied full `nodes_model` to QML during every viewport move.
- Verification:
  - Extend `tests/test_graph_canvas_viewport_virtualization.py` to cover active offscreen exceptions and viewport movement.
  - Fixture benchmark must show visible model query cost and visible delegate count.
- Non-goals: Do not alter graph-domain model ownership. Do not store view-only visibility in `.cxproj` persistence.
- Packetization notes: Convert to `P04 Bridge Viewport Index`. This is the first high-leverage implementation packet.

### T05 Stable Visible Delegate Model Adoption
- Goal: Make QML consume the indexed visible models without destroying/recreating large delegate sets unnecessarily during pan and zoom.
- Preconditions: `T04` visible model/index exists.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - New optional model helper under `ea_node_editor/ui_qml/`
  - `tests/test_graph_canvas_viewport_virtualization.py`
- Deliverables:
  - Replace QML-side `_filteredVisibleNodeModel(root.fullNodesModel)` as the primary path with bridge-provided visible models.
  - Prefer a stable `QAbstractListModel` or differential update helper over a new `QVariantList` copy for every viewport change. If a list is retained initially, include explicit delegate churn metrics and follow up with a stable model before accepting the packet.
  - Keep `hostForNodeId()` behavior for visible nodes and return `null` for offscreen nodes unless the node is actively forced visible.
  - Keep minimap on full graph data. Do not feed the viewport-filtered model to minimap.
  - Preserve full graph search, selection, command routing, context menus, drag, resize, and connection creation.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py -q`
  - Focused graph surface gate from `AGENTS.md` when practical.
  - Stress fixture run must report low delegate churn during small pans.
- Non-goals: Do not redesign node visuals or port layout.
- Packetization notes: Convert to `P05 Stable Visible Delegates`. Depends on `P04`.

### T06 Visible-Only Edge Snapshots And Incident Drag Refresh
- Goal: Stop treating every edge as a paint/snapshot candidate during viewport-only changes and node drag.
- Preconditions: `T02` identifies edge snapshot/paint cost, or `T04`/`T05` reveal edge work as the next bottleneck.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
  - `tests/test_edge_snapshot_spatial_index.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Keep a full `edgeById`/topology map for commands and hit-test support, but pass only visible/active edge snapshots to the paint layer.
  - Query the spatial index for visible candidates, selected/previewed edges, wire-drag preview, and incident edges for live-drag nodes.
  - On viewport-only refresh, update candidate and previous-visible edges only.
  - On drag, refresh only incident visible/active edges instead of invalidating all edge geometry.
  - Ensure `applyCrossingMetadata()` runs on the visible draw set, with a documented policy for offscreen crossing metadata reuse.
  - Preserve edge labels, flow-edge styles, execution visualization, selected/preview styling, context menu hit testing, and gap-break crossing style.
- Verification:
  - Extend `tests/test_edge_snapshot_spatial_index.py` for visible-only snapshots, selected offscreen exceptions, and incident-edge refresh.
  - Stress fixture benchmark must show candidate edge count much lower than total edge count during normal pan.
- Non-goals: Do not replace edge rendering with a native renderer in this task.
- Packetization notes: Convert to `P06 Visible Edge Snapshot Pipeline`.

### T07 Frame-Coalesced Pan, Zoom, And Drag State
- Goal: Prevent mouse event frequency from becoming redraw frequency. UI should accept every input event but flush expensive canvas updates at most once per frame.
- Preconditions: `T02` and `T06` metrics identify redraw storms or drag-offset churn.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
  - `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml`
  - `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- Deliverables:
  - Add pending pan/zoom/drag buckets to the frame scheduler.
  - Keep immediate local visual feedback for the node under the pointer, but coalesce global live-drag offset publication and incident-edge redraws.
  - During panning, aggregate mouse deltas and apply one `pan_by` per scheduled frame.
  - During drag, publish live drag offsets once per scheduled frame and commit final model movement on release exactly as before.
  - Keep toolbar, edge preview, overlay geometry, and hit testing aligned with the coalesced state.
  - Add counters for raw input events vs flushed visual updates.
- Verification:
  - Existing graph-surface input tests.
  - Add focused tests for drag commit correctness and no lost final position.
  - Stress fixture drag benchmark must improve without changing final node coordinates.
- Non-goals: Do not change selection semantics, snap-to-grid behavior, collision avoidance, or undo history.
- Packetization notes: Convert to `P07 Frame Coalesced Interaction`.

### T08 Minimap And Grid Zero-Loss Cost Control
- Goal: Ensure full-feature minimap and grid do not dominate pan/zoom after node and edge work is fixed.
- Preconditions: Run after `T04` through `T07`, unless `T02` already proves grid/minimap is dominant.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasGridTiled.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
  - `tests/graph_track_b/qml_preference_rendering_suite.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Measure grid item count, grid update time, and minimap update time in fixture reports.
  - If `GraphCanvasGridTiled.qml` creates too many `Rectangle` delegates at low zoom/high DPR, replace it with a shader/tiled texture or native scenegraph-backed tile behind a parity-checked flag.
  - Cache minimap static node dots/edges separately from the moving viewport rectangle. Update the static cache only when graph topology or node positions change.
  - Keep grid style, minimap expansion, viewport rectangle, selection visibility, and click-to-pan behavior unchanged.
- Verification:
  - Rendering preference tests.
  - Fixture benchmark comparing grid/minimap enabled vs measured component time. Do not accept a fix that passes by hiding either feature.
- Non-goals: Do not remove point-grid style or minimap features.
- Packetization notes: Convert to `P08 Grid Minimap Cost Control`.

### T09 Overlay And Passive Surface Guardrails
- Goal: Ensure the stress fix does not regress heavy media, embedded viewers, fullscreen content, or overlay mapping, especially if `QQuickView` becomes default.
- Preconditions: `T03` if `QQuickView` is considered; otherwise can run after `T07`.
- Conservative write scope:
  - `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
  - `ea_node_editor/ui_qml/dpf_viewer_widget_binder.py`
  - `ea_node_editor/ui_qml/components/graph/passive/*`
  - `tests/graph_surface/media_and_scope_suite.py`
  - `tests/graph_surface/passive_host_boundary_suite.py`
  - `tests/test_passive_graph_surface_host.py`
  - `tests/test_passive_image_nodes.py`
- Deliverables:
  - Add a heavy-media fixture rerun using the same host/backend selected by the stress plan.
  - Verify overlay sync is frame-coalesced and viewport-culling aware.
  - Confirm passive media/viewer nodes do not force full-canvas redraws during pan/zoom.
  - Confirm fullscreen/embedded viewer mapping remains correct under `QQuickWidget` and `QQuickView` if both remain supported.
- Verification:
  - Focused graph-surface gate from `AGENTS.md`.
  - Existing heavy-media performance harness command.
- Non-goals: Do not optimize stress_1200 by ignoring media paths; this is a guardrail packet.
- Packetization notes: Convert to `P09 Overlay Guardrails`.

### T10 Default Policy, Acceptance Thresholds, And Closeout
- Goal: Choose the accepted host/backend/default behavior and publish repeatable proof that the stress fixture is fixed without feature loss.
- Preconditions: Optimization tasks have before/after artifacts.
- Conservative write scope:
  - `ea_node_editor/settings.py`
  - `ea_node_editor/app_preferences.py`
  - `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
  - `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
  - `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `scripts/verification_manifest.py`
  - `docs/specs/requirements/80_PERFORMANCE.md` only if acceptance thresholds change.
- Deliverables:
  - Decide whether the default app path remains `QQuickWidget`, switches to `QQuickView`, or offers an explicit graphics preference.
  - Decide whether to recommend a Windows RHI backend such as `d3d11` or leave Qt default.
  - Publish final fixture report under `artifacts/graph_canvas_stress_1200_final/`.
  - Add a final zero-loss feature parity checklist covering grid, minimap, labels, shadows, edge crossing style, overlays, context menus, tooltips, drag, pan, zoom, node controls, and execution visualization.
  - Update perf docs and verification manifest so `stress_1200_nodes.cxproj` remains a regression gate.
- Verification:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
  - Focused graph-surface gate from `AGENTS.md`.
  - Stress fixture final desktop benchmark.
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Non-goals: Do not start a native renderer rewrite unless final diagnostics still show grid/edge rendering as the measured dominant bottleneck after all earlier tasks.
- Packetization notes: Convert to `P10 Stress Closeout And Defaults`.

### T11 Conditional Native Renderer Prototype
- Goal: Only if the final measured bottleneck remains grid or edge paint after `T04` through `T10`, prototype a native Qt Quick renderer for the dominant path.
- Preconditions: Final fixture diagnostics show QML/Canvas edge or grid paint remains the top bottleneck after model, delegate, edge snapshot, coalescing, and host/backend work.
- Conservative write scope:
  - New native/QML bridge module under `ea_node_editor/ui_qml/` or `ea_node_editor/ui/graph_rendering/`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasGridTiled.qml`
  - `tests/test_graph_canvas_native_renderer.py`
- Deliverables:
  - Implement an opt-in renderer for the measured dominant path only.
  - Keep feature parity before considering default adoption.
  - Preserve QML fallback for test/offscreen environments if the native path cannot run there.
- Verification:
  - Native renderer unit tests.
  - Stress fixture A/B report showing native path wins and preserves parity.
- Non-goals: Do not build a full custom scene replacement. Do not move graph-domain ownership into UI rendering code.
- Packetization notes: Convert to `P11 Conditional Native Renderer` only if evidence requires it. Otherwise record `NOT NEEDED`.

## Work Packet Conversion Map
1. `P00 Bootstrap`: publish packet manifest, status ledger, prompts, and optional spec-index registration for this follow-up track.
2. `P01 Stress Fixture Baseline`: derived from `T01`.
3. `P02 Stress Diagnostics`: derived from `T02`.
4. `P03 Desktop Host Backend AB`: derived from `T03`.
5. `P04 Bridge Viewport Index`: derived from `T04`.
6. `P05 Stable Visible Delegates`: derived from `T05`.
7. `P06 Visible Edge Snapshot Pipeline`: derived from `T06`.
8. `P07 Frame Coalesced Interaction`: derived from `T07`.
9. `P08 Grid Minimap Cost Control`: derived from `T08`.
10. `P09 Overlay Guardrails`: derived from `T09`.
11. `P10 Stress Closeout And Defaults`: derived from `T10`.
12. `P11 Conditional Native Renderer`: derived from `T11` only if measured bottlenecks remain.

Suggested branch labels if packetized:
- `codex/graph-canvas-stress-1200/p00-bootstrap`
- `codex/graph-canvas-stress-1200/p01-stress-fixture-baseline`
- `codex/graph-canvas-stress-1200/p02-stress-diagnostics`
- `codex/graph-canvas-stress-1200/p03-desktop-host-backend-ab`
- `codex/graph-canvas-stress-1200/p04-bridge-viewport-index`
- `codex/graph-canvas-stress-1200/p05-stable-visible-delegates`
- `codex/graph-canvas-stress-1200/p06-visible-edge-snapshot-pipeline`
- `codex/graph-canvas-stress-1200/p07-frame-coalesced-interaction`
- `codex/graph-canvas-stress-1200/p08-grid-minimap-cost-control`
- `codex/graph-canvas-stress-1200/p09-overlay-guardrails`
- `codex/graph-canvas-stress-1200/p10-stress-closeout-defaults`
- `codex/graph-canvas-stress-1200/p11-conditional-native-renderer`

## Test Plan
- Normal fast regression:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
- Focused graph-surface gate for QML/input/passive-node changes:
  - `$env:QT_QPA_PLATFORM = "offscreen"`
  - `.\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`
  - `Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue`
- Viewport virtualization:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py -q`
- Edge spatial/snapshot pipeline:
  - `.\venv\Scripts\python.exe -m pytest tests/test_edge_snapshot_spatial_index.py tests/graph_track_b/qml_preference_performance_suite.py -q`
- Harness/report contract:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q`
- Stress fixture benchmark, display-attached desktop:
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_final`
- `QQuickView` A/B example:
  - `$env:EA_NODE_EDITOR_QML_HOST = "qquickview_container"`
  - `$env:EA_NODE_EDITOR_QSG_RHI_BACKEND = "d3d11"`
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_qquickview`
  - `Remove-Item Env:EA_NODE_EDITOR_QML_HOST -ErrorAction SilentlyContinue`
  - `Remove-Item Env:EA_NODE_EDITOR_QSG_RHI_BACKEND -ErrorAction SilentlyContinue`
- Docs/proof checks after perf docs or verification manifest changes:
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`

Acceptance targets for this follow-up:
- `stress_1200_nodes.cxproj` pan, zoom, and single-node drag must not take seconds on a display-attached Windows desktop run.
- The final report must include both readback-inclusive interaction timing and no-readback frame interval timing.
- Visible delegate count during normal viewport operations should be close to the viewport candidate set, not the full `1200` nodes.
- Edge candidate count during normal viewport operations should be close to the visible/active candidate set, not the full `1199` edges.
- No accepted optimization may pass by hiding grid, minimap, labels, shadows, overlays, edge crossing style, context menus, tooltips, embedded viewers, execution visualization, or node controls.

## Assumptions
- The repo remains Windows-first and the project venv remains the primary interpreter.
- `stress_1200_nodes.cxproj` is a real user-relevant fixture and should become a regression gate.
- The app is pre-release, so internal compatibility shims can be removed when doing so simplifies the current architecture and tests.
- Offscreen/software runs are useful for deterministic regression checks but are not sufficient to prove desktop GPU performance.
- Low GPU utilization during pan/drag does not by itself prove that Qt Quick is not using the GPU; it may mean the UI thread is CPU-bound before the scenegraph has enough work to keep the GPU busy.
- `QQuickWidget` can still use accelerated Qt Quick rendering, but it adds an offscreen composition path and disables the threaded render loop, so it must be A/B tested against `QQuickView` for this canvas.
- Node, edge, minimap, search, selection, command routing, and persistence must continue to operate on full graph data even when visual delegates and painted edge snapshots are viewport-filtered.
- App-wide graphics preferences stay outside `.cxproj` project persistence unless an existing spec explicitly requires otherwise.
