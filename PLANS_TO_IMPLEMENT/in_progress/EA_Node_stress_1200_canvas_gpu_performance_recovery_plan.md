# EA_Node Stress 1200 Canvas GPU And Interaction Performance Recovery Plan

## Summary
- Exported on `2026-05-08` as an implementation-ready plan for making `examples/stress_1200_nodes.cxproj` responsive for pan, zoom, and node drag without feature loss.
- The current evidence does not support a blind "use the GPU more" rewrite. Qt Quick can use GPU acceleration, but the slow path is likely dominated by CPU/UI-thread work before the GPU can help: QML full-list filtering, delegate churn, edge snapshot rebuilds, CPU `Canvas.Image` edge painting and texture upload, grid/minimap updates, overlay sync, and uncoalesced input events.
- The existing `GRAPH_CANVAS_PERFORMANCE` work already added frame scheduling, viewport virtualization, grid work, edge spatial indexing, subtree cache policy, zero-loss modes, and an opt-in `QQuickView` host. The newer `GRAPH_CANVAS_STRESS_1200` packet set exists, but `P02` through `P10` remain pending in the status ledger. The ledger says `P01` baseline passed, but this checkout does not contain `artifacts/graph_canvas_stress_1200_baseline/`; the first executor should reconcile or regenerate that evidence before optimizing.
- Prior published desktop-reference evidence is still far above the `REQ-PERF-002` target of `<= 33 ms` p95 pan/zoom on the real `GraphCanvas.qml` path. The plan below keeps display-attached Windows desktop proof as the acceptance gate; offscreen/software runs are regression evidence only.
- Use this plan as the Codex handoff. Implement tasks in order. Each task has a conservative write scope and expected verification. If a stale compatibility alias, stub, or test blocks the current architecture, it may be updated or removed, but only after replacing it with positive coverage for the user-visible feature.

## Key Changes
- Rebuild the stress fixture performance baseline and make the artifact set present, reproducible, and display-attached.
- Add cheap, disabled-by-default diagnostics that separate CPU model copying, QML delegate churn, edge snapshot generation, edge paint time, grid/minimap cost, overlay sync, frame scheduling, host kind, and Qt RHI backend.
- Prove the actual GPU path instead of assuming it: capture `QSG_INFO`, `QSG_RHI_BACKEND`, `QT_QUICK_BACKEND`, `QSG_RENDER_LOOP`, active graphics API, device pixel ratio, host kind, and `QQuickWidget` versus `QQuickView` behavior.
- Move node visibility out of per-frame QML full-list filtering and into a bridge-owned indexed visible model with stable identity and explicit forced-visible exceptions.
- Adopt stable visible delegate models in QML so small pans do not create or destroy large node subtrees.
- Split edge topology from visible paint snapshots. Paint and refresh visible/active edge snapshots only, and refresh only incident visible edges during node drag.
- Coalesce pan, zoom, drag, edge, grid, and overlay invalidations to frame cadence while preserving exact final positions, undo semantics, selection, context menus, tooltips, and node controls.
- Keep grid, minimap, labels, shadows, edge crossing style, overlays, embedded media, execution visualization, context menus, and full graph search/command/persistence behavior enabled in the accepted path.
- Make native/GPU renderer work conditional. Only prototype a custom scenegraph renderer if diagnostics still show grid or edge paint as the dominant bottleneck after model, delegate, edge, coalescing, and host/backend work.

## Public Interface Changes
- Benchmark CLI additions or confirmations:
  - `--stress-fixture` loads `examples/stress_1200_nodes.cxproj` and workspace `ws_perf_h`.
  - `--project-path <path>` loads an arbitrary `.cxproj` through the project serializer.
  - `--workspace-id <id>` selects a workspace for project-backed benchmark runs.
  - `--qml-host qquickwidget|qquickview_container` or equivalent environment plumbing forces the host before Qt initialization.
  - `--qsg-rhi-backend auto|d3d11|d3d12|opengl|vulkan|software` or equivalent environment plumbing forces the RHI backend before Qt initialization.
  - `--capture-qsg-info` or documented manual support captures `QSG_INFO=1` output for display-attached profiling.
- Artifact outputs:
  - `artifacts/graph_canvas_stress_1200_baseline/`
  - `artifacts/graph_canvas_stress_1200_qquickwidget/`
  - `artifacts/graph_canvas_stress_1200_qquickview/`
  - `artifacts/graph_canvas_stress_1200_final/`
- Optional UI after proof:
  - A graphics diagnostics/status surface may expose host kind, selected RHI backend, active graphics API, and renderer fallback status.
  - Do not change default host/backend or persist new graphics defaults until the stress fixture proves performance and parity.

## Execution Tasks

### T01 Reconcile Stress Baseline And Artifact Evidence
- Goal: Make the current `stress_1200_nodes.cxproj` baseline trustworthy and present in this checkout before any optimization work continues.
- Preconditions: Use `.\venv\Scripts\python.exe`. Read `AGENTS.md`, `docs/specs/work_packets/graph_canvas_stress_1200/GRAPH_CANVAS_STRESS_1200_MANIFEST.md`, and `docs/specs/work_packets/graph_canvas_stress_1200/GRAPH_CANVAS_STRESS_1200_STATUS.md`.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `scripts/profile_canvas_lag.py`
  - `tests/test_track_h_perf_harness.py`
  - `docs/specs/work_packets/graph_canvas_stress_1200/GRAPH_CANVAS_STRESS_1200_STATUS.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_stress_1200_baseline/**`
- Deliverables:
  - Confirm whether `P01` artifacts were intentionally omitted, ignored, or lost. Regenerate them if absent.
  - Record fixture metadata: project path, workspace id, node count, edge count, node type histogram, scene bounds, host kind, active graphics API, RHI backend, Qt platform, render loop, DPR, and readback inclusion.
  - Record current p50/p95 for load, pan, zoom, node drag, and `frame_interval_ms_without_readback`.
  - Make the report explicitly distinguish display-attached desktop timings from offscreen/software timings.
  - Keep synthetic and heavy-media scenarios intact.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_baseline`
  - Display-attached Windows run of the same benchmark with no forced offscreen platform.
- Non-goals: No renderer, model, QML, or default behavior changes.
- Packetization notes: Maps to `P01` if rerunning/reconciling baseline, otherwise use as a `P02` preflight gate before diagnostics.

### T02 Add Bottleneck Diagnostics
- Goal: Identify where seconds-long stalls actually occur before changing architecture.
- Preconditions: `T01` baseline exists and has artifacts.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasViewportController.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `ea_node_editor/ui/perf/performance_harness.py`
- Deliverables:
  - Add cheap counters/timers for visible-model query time, full-list copy time, delegate create/destroy counts, edge snapshot build time, visible edge count, candidate edge count, edge paint time, grid update/paint time, minimap update time, overlay sync time, raw input events, coalesced frame flushes, and skipped duplicate invalidations.
  - Add a `Stress 1200 Bottleneck Breakdown` table to the benchmark report.
  - Add optional `QSG_INFO=1` capture support for manual profiling; do not require it in CI.
  - Ensure diagnostics are disabled or minimal in normal application runs.
- Verification:
  - Existing Track H perf tests.
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_baseline`
  - Verify every new diagnostic field is present, numeric, and documented as zero/unknown only when the underlying QML path cannot expose it yet.
- Non-goals: No optimization yet. This task exists to prevent guessing.
- Packetization notes: Maps to `P02 Stress Diagnostics`.

### T03 Prove Desktop GPU Host And RHI Backend
- Goal: Determine whether the user-visible desktop path is hardware accelerated and whether `QQuickWidget` composition is a bottleneck compared with `QQuickView`.
- Preconditions: `T02` diagnostics exist. Run on display-attached Windows hardware for acceptance.
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
  - Force `EA_NODE_EDITOR_QML_HOST` and `EA_NODE_EDITOR_QSG_RHI_BACKEND` before Qt initialization in benchmark/profile runs.
  - Compare at minimum:
    - `QQuickWidget` plus Qt default backend
    - `QQuickWidget` plus `d3d11`
    - `qquickview_container` plus Qt default backend
    - `qquickview_container` plus `d3d11`
    - optional Windows comparisons: `d3d12`, `opengl`, and `vulkan` if available
  - Capture QSG logs, active graphics API, renderer loop, texture atlas warnings, software fallback, and scenegraph errors.
  - Record feature parity for context menus, keyboard focus, drag, pan, zoom, minimap, status strip, floating toolbar, embedded viewer overlays, fullscreen behavior, and shell lifecycle.
  - Decide whether host/backend changes are worth pursuing before any default changes.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/test_track_h_perf_harness.py --ignore=venv -q`
  - Display-attached A/B benchmark reports in `artifacts/graph_canvas_stress_1200_qquickwidget/` and `artifacts/graph_canvas_stress_1200_qquickview/`.
- Non-goals: Do not make `QQuickView` or a specific RHI backend default until parity and performance are both proven.
- Packetization notes: Maps to `P03 Desktop Host Backend A/B`.

### T04 Build Bridge-Owned Visible Node Index
- Goal: Stop QML from scanning and copying the full node model on each pan/zoom.
- Preconditions: `T02` shows visible-model copy/filter time or delegate churn is material.
- Conservative write scope:
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `ea_node_editor/ui_qml/viewport_bridge.py`
  - `ea_node_editor/ui_qml/graph_scene_bridge.py` only if needed for stable revision signals
  - optional new helper: `ea_node_editor/ui_qml/graph_canvas_viewport_index.py`
  - `tests/test_graph_canvas_viewport_virtualization.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Add an indexed cache keyed by node id and node bounds for normal nodes and backdrop nodes.
  - Invalidate the index only for workspace changes, node list revision changes, or node geometry changes.
  - Query by expanded visible scene rect, including the existing render activation padding.
  - Preserve forced-visible exceptions: selected, failed, running, warning, hovered, context-menu target, pending wire source/target, drop candidate, live-drag nodes, and resized nodes.
  - Expose visible counts, full counts, query ms, rebuild ms, cache hit/miss, forced-visible count, and model revision.
  - Avoid returning a fresh full-list copy to QML for every viewport move.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py --ignore=venv -q`
  - Stress fixture report shows visible node counts and query timings.
- Non-goals: Do not put view-only visibility into graph-domain state or `.cxproj` persistence.
- Packetization notes: Maps to `P04 Bridge Viewport Index`.

### T05 Adopt Stable Visible Delegate Models In QML
- Goal: Make QML consume bridge-owned visible models while keeping delegate identity stable during small viewport changes.
- Preconditions: `T04` visible index exists.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `tests/test_graph_canvas_viewport_virtualization.py`
- Deliverables:
  - Replace `GraphCanvasRootLayers.qml` full-list `_filteredVisibleNodeModel(root.fullNodesModel)` as the primary rendering path.
  - Prefer a stable `QAbstractListModel` or revisioned/differential model over new `QVariantList` copies. If a list copy remains temporarily, make delegate churn metrics a failing gate for acceptance.
  - Preserve `hostForNodeId()` for visible and forced-visible nodes.
  - Keep minimap, search, command routing, hit testing, selection, persistence, and full graph operations on full graph data.
  - Preserve node controls, ports, inline inputs, passive surfaces, execution badges, context menus, tooltips, drag, resize, and selection visuals.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py --ignore=venv -q`
  - Focused graph-surface gate from `AGENTS.md` when practical.
  - Stress fixture small-pan report shows low delegate create/destroy counts.
- Non-goals: Do not redesign node visuals, port layout, or graph mutation boundaries.
- Packetization notes: Maps to `P05 Stable Visible Delegates`.

### T06 Restrict Edge Snapshots And Paint To Visible/Active Edges
- Goal: Stop full-graph edge snapshot and paint work during viewport-only changes and node drag.
- Preconditions: `T02` identifies edge snapshot/paint cost, or `T04`/`T05` exposes edges as the next bottleneck.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
  - `tests/test_edge_snapshot_spatial_index.py`
  - `tests/test_flow_edge_labels.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Keep a full edge topology map for commands, hit testing, search, context menus, execution visualization, and persistence.
  - Send only visible/active snapshots to the paint layer.
  - Include selected, previewed, hovered, wire-drag, execution-active, and incident-to-dragged-node edges even when partially offscreen.
  - On viewport-only changes, refresh only candidate and previously visible edges.
  - On node drag, refresh only incident visible/active edges plus the live wire preview.
  - Run edge crossing metadata on the visible draw set and document how offscreen crossing metadata is preserved or deferred.
  - Preserve edge labels, flow-edge styles, execution state styling, selected/preview styling, context menu hit testing, and gap-break crossing style.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_edge_snapshot_spatial_index.py tests/test_flow_edge_labels.py --ignore=venv -q`
  - Stress fixture report shows candidate edge count lower than total edge count during normal pan/zoom.
- Non-goals: Do not replace edge rendering with a native renderer in this task.
- Packetization notes: Maps to `P06 Visible Edge Snapshot Pipeline`.

### T07 Coalesce Pan, Zoom, Drag, Edge, Grid, And Overlay Updates
- Goal: Prevent raw mouse event frequency from becoming redraw frequency.
- Preconditions: `T02` through `T06` have enough counters to show input-event fanout.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasViewportController.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
  - `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml`
  - `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- Deliverables:
  - Add scheduler buckets for pan, zoom, drag offset publication, incident edge refresh, grid invalidation, minimap viewport update, and overlay sync.
  - Preserve immediate pointer feedback for the active node under the cursor.
  - Publish expensive global drag offsets and incident edge redraws at most once per frame.
  - Apply final node position, snap-to-grid, undo, selection, collision handling, and graph mutation exactly once on release.
  - Add metrics for raw input events, accepted visual updates, dropped duplicate redraws, and final commit latency.
- Verification:
  - Graph-surface input contract tests from `AGENTS.md`.
  - Add or update tests for drag final-position correctness and no lost final release.
  - Stress fixture drag benchmark improves without changing final node coordinates.
- Non-goals: Do not change user-visible drag semantics, selection semantics, snap-to-grid, undo history, or collision behavior.
- Packetization notes: Maps to `P07 Frame Coalesced Interaction`.

### T08 Control Grid And Minimap Cost Without Hiding Features
- Goal: Ensure grid and minimap remain visible and interactive without dominating frame time.
- Preconditions: Run after `T04` through `T07`, unless `T02` already proves grid/minimap dominates.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasGridTiled.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
  - `tests/graph_track_b/qml_preference_rendering_suite.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Measure grid item count, grid paint/update time, minimap static cache time, and minimap viewport-rect update time.
  - If tiled `Rectangle` delegates dominate at low zoom or high DPR, replace with a cheaper scenegraph-friendly path behind a parity flag. Prefer Qt Quick shader/texture or true scenegraph geometry. Do not claim `QQuickPaintedItem` is a GPU fix unless profiling proves it removes the bottleneck.
  - Cache minimap static node/edge representation separately from the moving viewport rectangle.
  - Update minimap static cache only on graph topology or node-position revision changes.
  - Keep grid style, grid visibility, minimap expansion, viewport rectangle, selection visibility, and click-to-pan behavior unchanged.
- Verification:
  - Rendering preference tests.
  - Stress fixture benchmark with grid and minimap enabled.
  - Reject fixes that pass by hiding grid or minimap in the accepted mode.
- Non-goals: Do not remove point-grid style, line-grid style, or minimap controls.
- Packetization notes: Maps to `P08 Grid Minimap Cost Control`.

### T09 Guard Overlays, Passive Surfaces, Fullscreen, And Heavy Media
- Goal: Ensure the stress fix does not regress non-stress graph features, especially if `QQuickView` or RHI defaults change.
- Preconditions: Run after `T03` if host/backend behavior may change; otherwise after `T07`.
- Conservative write scope:
  - `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
  - `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
  - `ea_node_editor/ui_qml/dpf_viewer_widget_binder.py`
  - `ea_node_editor/ui_qml/components/graph/passive/*`
  - `ea_node_editor/ui_qml/components/graph/viewer/*`
  - `tests/test_passive_graph_surface_host.py`
  - `tests/test_passive_image_nodes.py`
  - `tests/main_window_shell/passive_image_nodes.py`
  - `tests/main_window_shell/passive_pdf_nodes.py`
  - `tests/test_embedded_viewer_overlay_manager.py`
  - `tests/test_viewer_host_service.py`
  - `tests/test_viewer_session_bridge.py`
- Deliverables:
  - Run heavy-media benchmark under the same host/backend chosen for stress work.
  - Confirm passive media/viewer/tabular nodes do not force full-canvas redraws during pan/zoom.
  - Confirm overlay sync is frame-coalesced and viewport-aware.
  - Confirm fullscreen and embedded viewer mapping remain correct under both supported host paths.
  - Preserve passive-node controls, crop overlays, file explorer surfaces, PDF/image panels, tabular previews, and viewer handoff behavior.
- Verification:
  - Focused graph-surface gate from `AGENTS.md`.
  - `QT_QPA_PLATFORM=offscreen .\venv\Scripts\python.exe -m unittest tests.main_window_shell.passive_image_nodes tests.main_window_shell.passive_pdf_nodes -v`
  - Existing heavy-media performance harness command.
- Non-goals: Do not make `stress_1200` fast by ignoring media and overlay paths.
- Packetization notes: Maps to `P09 Overlay Guardrails`.

### T10 Retire Stale Compatibility Seams Only With Replacement Coverage
- Goal: Remove obsolete internal aliases, stub behavior, or tests that preserve the old architecture and block the current high-performance canvas path.
- Preconditions: A later task identifies a specific stale seam as a blocker.
- Conservative write scope:
  - `tests/test_graph_canvas_native_renderer.py`
  - `tests/test_track_h_perf_harness.py`
  - `tests/graph_surface_pointer_regression.py`
  - `tests/graph_surface/environment.py`
  - `tests/test_shell_window_lifecycle.py`
  - `tests/test_embedded_viewer_overlay_manager.py`
  - `tests/test_viewer_host_service.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
  - `tests/graph_track_b/qml_preference_rendering_suite.py`
  - affected implementation file named by the owning task
- Deliverables:
  - For each removed seam, state the old behavior, why it is obsolete, which current feature replaces it, and which positive test now covers the current behavior.
  - Remove legacy telemetry aliases only if current benchmark entry points are updated.
  - Update negative/native-renderer guard tests if a real native renderer is introduced.
  - Update pointer-regression or shell-host tests only when the new input/host behavior has positive parity tests.
  - Keep user-visible feature parity. Do not delete a failing test just to pass CI.
- Verification:
  - Narrow test set for the changed seam.
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast` before closeout if test contracts changed broadly.
- Non-goals: No unrelated cleanup. No compatibility removal that changes persisted `.cxproj` behavior or user-facing workflows without a matching migration and test.
- Packetization notes: This task may be folded into the owning packet, or split as a remediation packet if the cleanup crosses multiple test families.

### T11 Choose Defaults, Regression Gates, And Closeout Proof
- Goal: Publish the accepted performant path and make `stress_1200_nodes.cxproj` a permanent regression gate.
- Preconditions: `T03` through `T09` complete with before/after artifacts.
- Conservative write scope:
  - `ea_node_editor/settings.py`
  - `ea_node_editor/app_preferences.py`
  - `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
  - `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
  - `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
  - `scripts/verification_manifest.py`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/requirements/80_PERFORMANCE.md` only if acceptance thresholds change
  - `artifacts/graph_canvas_stress_1200_final/**`
- Deliverables:
  - Decide whether default host remains `QQuickWidget`, changes to `qquickview_container`, or becomes a graphics preference.
  - Decide whether Windows should prefer a specific RHI backend such as `d3d11`, or keep Qt default.
  - Publish final display-attached stress fixture proof.
  - Add a zero-loss parity checklist covering grid, minimap, labels, shadows, edge crossing style, overlays, context menus, tooltips, drag, pan, zoom, node controls, passive surfaces, fullscreen, and execution visualization.
  - Update docs and verification manifest so future performance changes cannot ignore `stress_1200_nodes.cxproj`.
- Verification:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
  - Focused graph-surface gate from `AGENTS.md`
  - Final display-attached stress fixture benchmark in `artifacts/graph_canvas_stress_1200_final/`
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Non-goals: Do not claim release success from offscreen-only evidence.
- Packetization notes: Maps to `P10 Stress Closeout Defaults`.

### T12 Conditional Native Scenegraph Renderer Prototype
- Goal: Only if final diagnostics still show grid or edge paint as the dominant bottleneck, prototype a true scenegraph/GPU renderer for that measured path.
- Preconditions: `T04` through `T11` are complete, and the remaining bottleneck is proven to be edge or grid paint rather than model copying, delegate churn, input fanout, or host/backend fallback.
- Conservative write scope:
  - new module under `ea_node_editor/ui_qml/native_rendering/` or `ea_node_editor/ui/graph_rendering/`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasGridTiled.qml`
  - `tests/test_graph_canvas_native_renderer.py`
- Deliverables:
  - Prototype one measured renderer path only: edge mesh or grid mesh, not a full custom canvas rewrite.
  - Prefer true Qt Quick scenegraph geometry or a compiled Qt Quick plugin if PyQt cannot expose the required `QSGGeometryNode` path safely.
  - Keep QML fallback for offscreen/test environments.
  - Prove parity for styling, selection, edge labels, crossing gaps, execution state, zoom scaling, hit testing, and theme changes before default adoption.
- Verification:
  - Native renderer focused tests.
  - Stress fixture A/B report showing the native path wins and preserves parity.
- Non-goals: No full graph-scene replacement. No graph-domain ownership inside renderer code. No native renderer unless evidence demands it.
- Packetization notes: Conditional post-closeout packet. If not needed, record `NOT NEEDED` with diagnostic evidence.

## Work Packet Conversion Map
1. `P00 Bootstrap`: already exists for the stress packet set; keep it as the docs/manifest root unless a new packet set is intentionally created.
2. `P01 Baseline Reconciliation`: from `T01` if artifacts are absent or stale; otherwise mark as preflight complete.
3. `P02 Stress Diagnostics`: from `T02`.
4. `P03 Desktop GPU Host Backend A/B`: from `T03`.
5. `P04 Bridge Viewport Index`: from `T04`.
6. `P05 Stable Visible Delegates`: from `T05`.
7. `P06 Visible Edge Snapshot Pipeline`: from `T06`.
8. `P07 Frame Coalesced Interaction`: from `T07`.
9. `P08 Grid Minimap Cost Control`: from `T08`.
10. `P09 Overlay Guardrails`: from `T09`.
11. `P09R Compatibility Seam Cleanup`: from `T10` only if cleanup is too broad to fold into the owning packet.
12. `P10 Stress Closeout Defaults`: from `T11`.
13. `P11 Conditional Native Renderer`: from `T12` only if diagnostics justify it.

## Test Plan
- Use the project venv first for every Python, PyQt6, Qt, pytest, or QML command: `.\venv\Scripts\python.exe`.
- Core packet regression:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py tests/test_edge_snapshot_spatial_index.py tests/test_flow_edge_labels.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/test_embedded_viewer_overlay_manager.py tests/test_viewer_host_service.py tests/test_viewer_session_bridge.py --ignore=venv -q`
- Focused graph-surface gate from `AGENTS.md` when graph input, passive nodes, overlays, or QML surface behavior changes:
  - `$env:QT_QPA_PLATFORM = "offscreen"`
  - `.\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`
  - `Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue`
- Stress fixture benchmarks:
  - Offscreen deterministic regression run for repeatability.
  - Display-attached Windows run for acceptance.
  - `QQuickWidget` versus `qquickview_container` A/B run.
  - RHI backend A/B run with at least default and `d3d11` on Windows.
- Closeout:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Acceptance targets:
  - `REQ-PERF-002` remains `<= 33 ms` p95 pan/zoom on the actual `GraphCanvas.qml` render path.
  - `REQ-PERF-003` remains `< 3 s` project load.
  - Node drag should have an explicit published p95 target before closeout. Use `<= 50 ms` p95 as the proposed stress goal unless product owners choose a different threshold.
  - Feature parity must be documented as PASS, not inferred from timing success.

## Assumptions
- The stress fixture is `examples/stress_1200_nodes.cxproj`, workspace `ws_perf_h`, with approximately `1200` nodes and `1199` edges.
- This product is unreleased enough that internal compatibility seams, stale aliases, and obsolete stub tests can be removed when they block current architecture and are replaced by positive current-feature coverage.
- App graphics preferences are app-wide and must not be stored in `.cxproj` project documents unless an existing spec requires it.
- The graph domain remains independent of UI/QML rendering details. Viewport visibility, renderer caches, and host/backend choices stay in UI/bridge layers.
- Full graph data remains authoritative for minimap, search, command routing, selection, persistence, context menus, hit testing, execution visualization, and graph mutation.
- Offscreen/software Qt runs are useful for deterministic CI regression but cannot prove GPU or desktop compositor performance.
- `QQuickWidget` may incur composition overhead because it renders Qt Quick into an offscreen surface before widget composition. `QQuickView` may improve GPU/compositor behavior, but it must pass shell and overlay parity before becoming default.
- QML `Canvas.Image` edge rendering can still be CPU raster plus texture upload. If edge paint remains dominant, the next GPU step should be true scenegraph geometry, not simply moving CPU painting into a different wrapper.
- Do not begin native renderer work until diagnostics prove it is the remaining dominant bottleneck after indexed visibility, stable delegates, visible-only edges, frame coalescing, and host/backend A/B are complete.
