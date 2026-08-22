# EA_Node Stress 1200 GPU Canvas Performance Action Plan

## Summary
- Generated for the current `main` baseline after `d84067d8` (`Merge graph canvas stress 1200 closeout`).
- This plan supersedes the older stress-1200 follow-up plan for new implementation work. The `P01` through `P10` series improved the canvas substantially, but it did not meet the stress performance goals.
- The current evidence does not support a simple "GPU is off" diagnosis. Display-attached runs selected Direct3D 11, and `qquickview_container` is faster than `qquickwidget`, but frame cadence still fails by a wide margin. The dominant problem appears to be CPU-side QML/JS/Python work and redraw churn before the scenegraph can render smoothly.
- Latest display-attached D3D11 proof for the 1200-node stress case:
  - `qquickview_container`: pan p95 `206.475 ms`, zoom p95 `160.113 ms`, node drag p95 `537.482 ms`, frame interval p95 `500.265 ms`, load p95 `7257.051 ms`.
  - `qquickwidget`: pan p95 `271.380 ms`, zoom p95 `229.396 ms`, node drag p95 `588.314 ms`, frame interval p95 `521.347 ms`, load p95 `7682.528 ms`.
- Latest offscreen/software P10 proof: pan p95 `330.429 ms`, zoom p95 `348.836 ms`, node drag p95 `1121.054 ms`, frame interval p95 `547.234 ms`, load p95 `4363.226 ms`, canvas setup `13846.950 ms`.
- The next implementation must stop repeating completed work. Visible-node query cost is already about `0.09-0.10 ms` p95; grid/minimap/overlay timings are not the measured limit. The remaining hot areas are redraw/frame churn, edge snapshot/index behavior, CPU-backed edge Canvas rendering, synchronous viewport invalidation, delegate churn, node-drag commits, and load/canvas setup.
- Zero-loss means no accepted fix may permanently remove or hide grid, minimap, labels, shadows, edge crossing style, overlays, context menus, tooltips, drag, pan, zoom, node controls, passive media surfaces, fullscreen, search, command routing, persistence, or execution visualization. Temporary active-interaction deferral is allowed only when the settled state becomes exact automatically and quickly.

## Key Changes
- Make stress-fixture acceptance honest. The real `examples/stress_1200_nodes.cxproj` currently exists locally but is ignored by `*.cxproj`; clean worktrees can silently use the generated fallback. Acceptance must distinguish real fixture proof from generated regression proof.
- Treat graphics backend selection as a diagnostic, not the full fix. Keep the Windows display default of `qquickview_container` plus Direct3D 11 unless new evidence proves a better default.
- Replace event-loop-speed frame flushing with a real frame-budgeted scheduler. The current `GraphCanvasFrameScheduler.qml` uses `Timer { interval: 0 }`; final P10 still reports roughly `155-157` flushed frames and `158-160` edge redraw requests per interaction sample.
- Decouple pan/zoom visual feedback from synchronous Python visible-model refresh. `GraphCanvasStateBridge._invalidate_visible_scene_models()` currently refreshes immediately on every `view_state_changed`.
- Turn edge refresh into a dirty-set pipeline. `EdgeSnapshotCache.js` still scans all edges in several paths and uses JSON/string-clone dependency keys; spatial-index build metrics are suspiciously high (`~880-1332 ms` in display evidence and `972 ms` in P10 offscreen metrics).
- Add a retained/GPU-oriented edge-rendering path behind an explicit renderer abstraction. `EdgeCanvasLayer.qml` currently uses `Canvas { renderTarget: Canvas.Image }`, so normal edge drawing remains CPU-rasterized even when Qt Quick composition uses D3D11.
- Stabilize node delegates during smooth pan/zoom. `GraphCanvasWorldLayer.qml` uses a `Repeater` and clones `_hostByNodeId` maps on delegate add/remove, while P10 still reports delegate create p95 `85` and destroy p95 `48`.
- Treat load and first usable canvas time as separate performance products. Current load and canvas setup numbers are far beyond `REQ-PERF-003`.
- Remove or update obsolete compatibility/stub tests only when they protect old seams that the new measured implementation deliberately replaces. Do not delete tests that protect user-visible behavior.

## Public Interface Changes
- Add or tighten benchmark fixture modes:
  - `--stress-fixture real`: requires a committed or explicitly supplied real `stress_1200_nodes.cxproj`; fails if absent.
  - `--stress-fixture generated`: uses deterministic generated stress data and labels the report as generated.
  - Existing `--stress-fixture` may remain as a backward-compatible alias, but the report must state the selected fixture strategy clearly.
- Add report fields:
  - `fixture_source_kind`, `fixture_source_path`, `fixture_checksum`, `fixture_path_exists`.
  - `display_attached_required`, `display_attached_observed`.
  - `qml_host_kind`, `graphics_api`, `qsg_rhi_backend`, `qt_quick_backend`, `qsg_render_loop`, `dpr`.
  - `edge_renderer_kind`, `edge_renderer_fallback_reason`, `edge_renderer_feature_parity_result`.
  - `visible_model_refresh_count`, `visible_model_deferred_count`, `viewport_bucket_change_count`.
  - `edge_spatial_index_rebuild_count`, `edge_spatial_index_dirty_update_count`, `edge_snapshot_candidate_count`.
  - `raw_input_event_count`, `scheduled_frame_count`, `duplicate_redraw_drop_count`, `over_budget_frame_count`.
  - Separate `packet_verification_result` and `performance_acceptance_result`.
- Add a developer-only graphics/perf status surface only after the benchmark fields exist. It may report host, backend, renderer kind, software fallback status, and current frame-cadence counters. Do not store these preferences in `.cxproj` project documents.
- If a native renderer is added, keep a QML Canvas fallback for offscreen/CI and unsupported systems, but do not let fallback-only evidence satisfy display performance acceptance.

## Execution Tasks

### T01 Evidence And Fixture Truth
- Goal: Establish a trustworthy current baseline and prevent silent fallback from being accepted as proof for the real stress file.
- Preconditions: Work from current `main` at or after `d84067d8`. Preserve existing untracked plans and artifacts.
- Conservative write scope:
  - `.gitignore`
  - `examples/stress_1200_nodes.cxproj` or `tests/fixtures/perf/stress_1200_nodes.cxproj`
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `scripts/profile_canvas_lag.py`
  - `tests/test_track_h_perf_harness.py`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/work_packets/graph_canvas_stress_1200/GRAPH_CANVAS_STRESS_1200_STATUS.md`
- Deliverables:
  - Decide whether to track the real `.cxproj` with a `.gitignore` negation or move a canonical copy into `tests/fixtures/perf/`.
  - Add explicit real/generated fixture modes and make real mode fail when the file is absent.
  - Report fixture checksum and source kind in both JSON and Markdown.
  - Record the current P10 metrics as the "before" baseline for this escalation.
  - Mark prior packet status as packet-pass/performance-fail, not final acceptance.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
  - Real fixture mode fails when the fixture is unavailable.
  - Real fixture mode succeeds when the canonical fixture is present.
- Non-goals: No rendering or scheduler optimization.
- Packetization notes: `P00 Evidence And Fixture Truth`. Blocks all later benchmark claims.

### T02 Display Graphics Diagnostics And Acceptance Semantics
- Goal: Prove the actual graphics path for every acceptance run and make reports impossible to misread.
- Preconditions: `T01` fixture mode is in place.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `ea_node_editor/ui_qml/qtquick_backend.py`
  - `ea_node_editor/ui_qml/qml_host_factory.py`
  - `ea_node_editor/ui/shell/window.py`
  - `scripts/profile_canvas_lag.py`
  - `scripts/verification_manifest.py`
  - `tests/test_shell_window_lifecycle.py`
  - `tests/test_track_h_perf_harness.py`
  - `tests/test_traceability_checker.py`
  - `docs/specs/requirements/80_PERFORMANCE.md`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- Deliverables:
  - Capture `QSG_INFO=1` output for display-attached acceptance runs.
  - Record Qt platform, active graphics API, RHI backend, render loop, host kind, DPR, software fallback status, and readback inclusion.
  - Keep `qquickview_container` plus D3D11 as the Windows default unless a measured packet changes it.
  - Split `packet_verification_result` from `performance_acceptance_result`.
  - Make display acceptance refuse `QT_QPA_PLATFORM=offscreen`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_shell_window_lifecycle.py tests/test_traceability_checker.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Non-goals: No canvas behavior change.
- Packetization notes: Can merge with `T01` only if the executor keeps the report contract small.

### T03 Frame-Budgeted Scheduler And Transform-First Pan/Zoom
- Goal: Make pan and zoom visually immediate by applying a cheap transform every frame and deferring expensive exact work until a frame budget, viewport bucket change, or idle settle.
- Preconditions: `T01` and `T02` provide trustworthy before metrics.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasViewportController.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/viewport_bridge.py`
  - `tests/test_graph_canvas_frame_coalescing.py`
  - `tests/test_graph_surface_input_contract.py`
  - `tests/test_graph_surface_input_inline.py`
- Deliverables:
  - Replace `Timer { interval: 0 }` as the default interaction flush path with a vsync-like budget, initially `16 ms` on display and test-controllable in CI.
  - Keep one pending pan, one pending zoom, one pending edge refresh, one pending grid/minimap update, and one pending overlay update per scheduled frame.
  - Apply world transform immediately for pan/zoom without forcing full visible-model or edge snapshot recompute on every pointer event.
  - Add an idle settle pass that refreshes exact visible models, edge snapshots, hit-test state, labels, crossings, minimap static state, and overlays.
  - Drop duplicate redraw reasons within a frame and report `duplicate_redraw_drop_count`.
  - Acceptance gate: reduce flushed frames per pan/zoom sample from `~155-157` to `<10` in the first pass, then tighten toward frame-count parity with actual user input duration.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_frame_coalescing.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py --ignore=venv -q`
  - Display stress benchmark proves pan/zoom p95 improves and final viewport center/zoom remain exact.
- Non-goals: No feature hiding; no selection, snap, undo, command, or persistence changes.
- Packetization notes: `P02 Frame-Budgeted Transform Path`.

### T04 Viewport Hysteresis And Stable Visible Models
- Goal: Stop small pan/zoom deltas from causing synchronous Python visible-model refresh and avoid delegate churn while smooth viewport interaction is in progress.
- Preconditions: `T03` scheduler counters exist.
- Conservative write scope:
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `ea_node_editor/ui_qml/viewport_bridge.py`
  - `ea_node_editor/ui_qml/graph_canvas_viewport_index.py`
  - `ea_node_editor/ui_qml/graph_canvas_visible_model.py`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `tests/test_graph_canvas_viewport_virtualization.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Add viewport bucket/hysteresis logic so visible models refresh only when the padded viewport crosses a meaningful boundary or the interaction settles.
  - Change `GraphCanvasStateBridge._invalidate_visible_scene_models()` so viewport-state changes can mark dirty without immediate `sync_payloads()` during high-frequency pan/zoom.
  - Keep active exceptions visible: selected, hovered, context-menu target, failed/running/warning nodes, wire endpoints, drag nodes, resized nodes, and drop candidates.
  - Stabilize `GraphCanvasWorldLayer._hostByNodeId` updates. Avoid clone-on-each-add/remove behavior if it contributes to delegate churn.
  - Preserve minimap and search on full graph data, not the visible model.
  - Acceptance gate: visible-model query p95 stays near current `~0.1 ms`, while query count and delegate create/destroy counts drop materially during pan/zoom.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py tests/graph_track_b/qml_preference_performance_suite.py --ignore=venv -q`
  - Stress report shows lower `visible_model_query_count`, `delegate_create_count`, and `delegate_destroy_count` without losing active offscreen exceptions.
- Non-goals: Do not rework graph-domain ownership or store viewport state in `.cxproj`.
- Packetization notes: `P03 Viewport Hysteresis Stable Models`.

### T05 Edge Dirty Sets, Spatial Index, And Snapshot Cache
- Goal: Eliminate repeated full-edge scans and suspicious spatial-index rebuild costs during normal pan, zoom, and drag.
- Preconditions: `T03` and `T04` have reduced frame and visible-model churn enough to expose true edge costs.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `tests/test_edge_snapshot_spatial_index.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Replace full-edge incident lookup scans with adjacency maps keyed by node id and edge id.
  - Replace stable JSON stringify dependency keys with explicit geometry/topology revision keys.
  - Ensure viewport-only pan/zoom does not rebuild the spatial index after warmup.
  - Add dirty-entry updates for dragged incident edges and topology changes.
  - Make `syncExecutionFlashState()` incremental over changed execution state instead of scanning all edges every refresh.
  - Replace `Date.now()`-only timing with a reliable timing source where available, and add rebuild count metrics so stale cumulative timings cannot masquerade as rebuild cost.
  - Acceptance gate: pan/zoom spatial-index rebuild count is `0` after warmup; edge snapshot refresh p95 drops below the frame budget or is deferred safely to idle.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_edge_snapshot_spatial_index.py tests/graph_track_b/qml_preference_performance_suite.py --ignore=venv -q`
  - Stress benchmark reports rebuild count, dirty update count, query count, candidate count, and refresh time.
- Non-goals: Do not change edge semantics, hit testing, labels, crossing gaps, execution styling, selection, or preview behavior.
- Packetization notes: `P04 Edge Dirty Set Snapshot Cache`.

### T06 Retained/GPU-Oriented Edge Renderer
- Goal: Move normal visible-edge drawing away from CPU-backed QML `Canvas.Image` while preserving all edge features and keeping a fallback path.
- Preconditions: `T05` proves edge draw/snapshot work remains on the critical path or display frame cadence still fails after scheduler and dirty-set fixes.
- Conservative write scope:
  - New renderer module under `ea_node_editor/ui_qml/components/graph/` such as `EdgeRetainedLayer.qml` or `EdgeScenegraphLayer.qml`
  - Optional native module under `ea_node_editor/ui_qml/native_rendering/` or `ea_node_editor/ui/graph_rendering/`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
  - `ea_node_editor/ui_qml/components/graph/EdgeViewportMath.js`
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `tests/test_graph_canvas_native_renderer.py`
  - `tests/test_edge_snapshot_spatial_index.py`
  - `tests/graph_track_b/qml_preference_rendering_suite.py`
- Deliverables:
  - Introduce `edge_renderer_kind=canvas|retained_qml|native_scenegraph` and report the active kind.
  - Start with a retained visible-edge renderer using Qt Quick items or Shapes only if it benchmarks better than Canvas for the visible edge set.
  - If QML retained rendering cannot meet the target, add a compiled Qt Quick scenegraph item that emits retained geometry for visible/active edges. Do not use `QQuickPaintedItem` as the final answer unless benchmarks prove it wins; it still rasterizes through CPU paint into a texture.
  - Preserve Canvas fallback for offscreen/CI and unsupported platforms.
  - Preserve edge labels, flow labels/arrows, hover/selection/preview styling, wire drag, execution flash/dimming, theme changes, context menus, hit testing, and gap-break crossing style.
  - Add renderer parity tests and A/B display benchmark artifacts.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_native_renderer.py tests/test_edge_snapshot_spatial_index.py --ignore=venv -q`
  - Display A/B benchmark with `edge_renderer_kind` recorded for Canvas and the new renderer.
  - Feature parity snapshot passes for both fallback and accepted renderer.
- Non-goals: No full graph-scene rewrite. No native grid work unless new metrics show grid dominance.
- Packetization notes: `P05 Retained Edge Renderer`. This is the main GPU-path escalation.

### T07 Node Drag Fast Path And Targeted Commit
- Goal: Reduce node-drag p95 while keeping live selected-node motion, incident-edge feedback, undo, snap, and final model correctness.
- Preconditions: `T03` scheduler and `T05` edge dirty sets are available.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
  - `ea_node_editor/ui_qml/graph_scene/context.py`
  - `ea_node_editor/ui_qml/graph_scene/state_support.py`
  - `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
  - `tests/test_graph_canvas_frame_coalescing.py`
  - `tests/test_edge_snapshot_spatial_index.py`
  - relevant graph-scene mutation tests if touched
- Deliverables:
  - Keep the dragged selected node moving locally every frame.
  - Publish live drag offsets at frame cadence, not raw pointer-event cadence.
  - Refresh only incident visible/active edge previews during drag.
  - Defer non-incident crossing metadata, label layout, and full snapshot rebuild until idle/release.
  - Commit final graph coordinates once on release through graph-owned mutation paths.
  - Add targeted node-position payload updates if release currently forces a full scene rebuild.
  - Add metrics for local drag visual latency, incident-edge refresh time, and final commit time.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_frame_coalescing.py tests/test_edge_snapshot_spatial_index.py --ignore=venv -q`
  - Focused mutation tests for final node coordinates, multi-selection movement, snap behavior, and undo.
  - Stress benchmark shows node-drag p95 improvement without final-coordinate drift.
- Non-goals: Do not bypass graph invariants with public raw-write helpers.
- Packetization notes: `P06 Node Drag Fast Path`.

### T08 Load And First Usable Canvas Setup
- Goal: Reduce project load and canvas setup time for `stress_1200_nodes.cxproj` without weakening persistence compatibility or graph invariants.
- Preconditions: Can run independently after `T01`, but final acceptance should include interaction fixes too.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `ea_node_editor/persistence/project_codec.py`
  - `ea_node_editor/persistence/serializer.py`
  - `ea_node_editor/ui_qml/graph_scene/state_support.py`
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `ea_node_editor/ui_qml/graph_canvas_visible_model.py`
  - `ea_node_editor/ui_qml/graph_canvas_viewport_index.py`
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/nodes/` only if registry loading is proven hot
  - `tests/test_track_h_perf_harness.py`
  - persistence tests if serializer/codecs are touched
- Deliverables:
  - Break `project_graph_load_ms` into serializer parse, migration, registry lookup, project conversion, scene bridge population, visible-index build, edge-index build, and first model attach.
  - Break `canvas_setup_ms` into QML load, root binding, node model attach, edge model attach, initial visible model, initial edge snapshot, grid/minimap setup, and first rendered frame.
  - Batch initial model reset signals during project load.
  - Lazy-build non-visible node surface payloads.
  - Build edge spatial index once during initial setup and reuse it for first interaction.
  - Acceptance gate: real fixture load p95 below `3000 ms`; first usable canvas time tracked and materially improved even if not formalized yet.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
  - Relevant persistence tests if touched.
  - Stress fixture load benchmark with at least `3` runs.
- Non-goals: Do not change `.cxproj` schema unless a migration is explicitly required.
- Packetization notes: `P07 Load And First Usable Canvas`.

### T09 Zero-Loss Interaction Policy And Test Cleanup
- Goal: Encode the new performance behavior as zero-loss interaction policy and remove tests that only protect obsolete implementation seams.
- Preconditions: `T03` through `T07` have changed the runtime behavior.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
  - `ea_node_editor/settings.py`
  - `ea_node_editor/app_preferences.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
  - `tests/graph_track_b/qml_preference_rendering_suite.py`
  - `tests/test_graph_canvas_bridge_boundary.py`
  - `tests/test_graph_canvas_native_renderer.py`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- Deliverables:
  - Replace misleading "simplification" semantics with explicit categories:
    - `steady_state_exact`
    - `active_interaction_deferred_exactness`
    - `fallback_renderer`
  - Keep full fidelity as the settled state.
  - During active interaction, allow cached/frozen exact visuals only when they remain visibly equivalent and settle automatically.
  - Delete or rewrite compatibility/stub tests that assert the old Canvas-only or interval-0 scheduler seam.
  - Add tests that assert user-facing parity instead: final labels, crossing gaps, minimap, shadows, context menus, hit testing, execution visualization, passive surfaces, and final coordinates.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_performance_suite.py tests/graph_track_b/qml_preference_rendering_suite.py tests/test_graph_canvas_bridge_boundary.py --ignore=venv -q`
  - Feature parity snapshot remains `PASS` in the final stress report.
- Non-goals: Do not use max-performance feature hiding as the accepted path for this user problem.
- Packetization notes: `P08 Zero-Loss Policy Cleanup`.

### T10 Display-Attached Final Proof And Closeout
- Goal: Publish repeatable evidence that the real 1200-node fixture is responsive on the accepted display path without feature loss.
- Preconditions: Implementation tasks have before/after artifacts and passing focused tests.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `scripts/profile_canvas_lag.py`
  - `scripts/verification_manifest.py`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/requirements/80_PERFORMANCE.md`
  - `docs/specs/work_packets/graph_canvas_stress_1200/GRAPH_CANVAS_STRESS_1200_STATUS.md`
  - `artifacts/graph_canvas_stress_1200_display_final/**`
- Deliverables:
  - Run the final Windows display-attached benchmark on the real fixture with `qquickview_container`, Direct3D 11, and the accepted edge renderer.
  - Capture `QSG_INFO=1`, active graphics API, renderer kind, host kind, DPR, software fallback status, and feature parity.
  - Include both readback-inclusive timings and `frame_interval_ms_without_readback`.
  - Keep offscreen/generated runs as regression evidence only.
  - Update status/docs so `REQ-PERF-002` and `REQ-PERF-003` are either accepted with evidence or still explicitly failed.
- Verification:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
  - `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v; Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue`
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
  - Display command:
    `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --qml-host qquickview_container --qsg-rhi-backend d3d11 --qt-platform windows --baseline-mode interactive --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_display_final`
- Non-goals: Do not claim acceptance from offscreen/software or generated fallback data.
- Packetization notes: `P09 Display Final Proof Closeout`.

## Work Packet Conversion Map
1. `P00 Evidence And Fixture Truth`: `T01`.
2. `P01 Display Diagnostics And Acceptance Semantics`: `T02`.
3. `P02 Frame-Budgeted Transform Path`: `T03`.
4. `P03 Viewport Hysteresis Stable Models`: `T04`.
5. `P04 Edge Dirty Set Snapshot Cache`: `T05`.
6. `P05 Retained Edge Renderer`: `T06`.
7. `P06 Node Drag Fast Path`: `T07`.
8. `P07 Load And First Usable Canvas`: `T08`.
9. `P08 Zero-Loss Policy Cleanup`: `T09`.
10. `P09 Display Final Proof Closeout`: `T10`.

Suggested branch labels:
- `codex/graph-canvas-stress-1200/p00-evidence-fixture-truth`
- `codex/graph-canvas-stress-1200/p01-display-diagnostics`
- `codex/graph-canvas-stress-1200/p02-frame-budget-transform`
- `codex/graph-canvas-stress-1200/p03-viewport-hysteresis`
- `codex/graph-canvas-stress-1200/p04-edge-dirty-cache`
- `codex/graph-canvas-stress-1200/p05-retained-edge-renderer`
- `codex/graph-canvas-stress-1200/p06-node-drag-fast-path`
- `codex/graph-canvas-stress-1200/p07-load-first-canvas`
- `codex/graph-canvas-stress-1200/p08-zero-loss-policy`
- `codex/graph-canvas-stress-1200/p09-display-final-proof`

## Test Plan
- Use the project venv first:
  - `.\venv\Scripts\python.exe`
- Focused harness/report tests:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py --ignore=venv -q`
- Scheduler, viewport, and edge tests:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_frame_coalescing.py tests/test_graph_canvas_viewport_virtualization.py tests/test_edge_snapshot_spatial_index.py --ignore=venv -q`
- Native/retained renderer tests:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_native_renderer.py --ignore=venv -q`
- Graph-surface and passive-node guardrail:
  - `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v; Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue`
- Normal regression:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
- Docs/proof checks after docs, specs, traceability, or verification manifest changes:
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Benchmark progression:
  - Regression-only generated/offscreen run:
    `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture generated --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_generated_regression`
  - Required display acceptance run:
    `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --qml-host qquickview_container --qsg-rhi-backend d3d11 --qt-platform windows --baseline-mode interactive --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_display_final`

Acceptance targets:
- `REQ-PERF-002`: pan and zoom p95 `<=33 ms` on the real `GraphCanvas.qml` path, display-attached.
- Temporary node-drag escalation gate: node-drag p95 `<=50 ms` until a formal requirement exists.
- `REQ-PERF-003`: project+graph load p95 `<3000 ms`.
- Frame interval without readback: p95 `<=33 ms` for display-attached acceptance.
- Spatial-index rebuild count: `0` for steady pan/zoom after warmup.
- Flushed frame count: first reduction gate `<10` per pan/zoom sample, then tighten based on actual sample duration.
- Feature parity snapshot: `PASS` for grid, minimap, labels, shadows, edge crossing style, overlays, context menus, tooltips, drag, pan, zoom, node controls, passive media, fullscreen, search, command routing, persistence, and execution visualization.

## Assumptions
- The current repo baseline is `main` at or after `d84067d8`.
- The user-visible problem is the real `stress_1200_nodes.cxproj` scenario, not just the generated fallback.
- Display-attached Windows proof is required before claiming GPU/canvas performance acceptance.
- Low GPU utilization during pan/drag is expected if the UI thread is saturated by QML/JS/Python work before rendering.
- `QQuickView` plus Direct3D 11 is currently the preferred Windows default, but it is not sufficient by itself.
- QML `Canvas.Image` edge drawing is a likely CPU bottleneck and should not be the final accepted edge path if frame cadence remains above target.
- Python `QQuickPaintedItem` is not assumed to be a GPU fix; it still tends to paint through CPU rasterization into a texture.
- Offscreen/software and generated-fixture runs remain useful for regression but are not sufficient for final acceptance.
- The app is pre-release enough that obsolete internal seams and stub tests may be removed when replacements preserve user-facing behavior.
- Graph-domain invariants remain owned by `ea_node_editor.graph`; performance fixes must use existing mutation boundaries or private model writers where appropriate.
