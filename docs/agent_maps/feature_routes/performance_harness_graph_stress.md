# Performance Harness And Graph Stress

## Purpose
Use this for graph canvas performance, stress tests, mutation latency, scene publish time, GPU stress, and performance harness commands.

Lookup aliases: `stress_1200_nodes`, `notched port rendering`, `benchmark report fields`.

## Start Here
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/ui/perf/node_visual_quality.py`
- `scripts/capture_node_visual_quality.py`
- `ea_node_editor/ui/perf/engineering_viewer_benchmark.py`
- `scripts/profile_canvas_lag.py`
- `scripts/generate_flowchart_perf_fixture.py` (large flowchart for edge-renderer runs through `--project-path`)
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostRenderQuality.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml` edge churn counters: spatial query cache hits/misses, retained entry skips, and flow-label sync skips. Execution-flash scoped refreshes are removed with control-edge animation.
- `tests/test_track_h_perf_harness.py`
- `tests/test_node_visual_quality_tooling.py`
- `tests/test_graph_canvas_frame_coalescing.py`
- `tests/graph_surface/passive_host_boundary_suite.py`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/perf/COREX_CHANGE_LOCALITY_QA_MATRIX.md`
- `docs/specs/perf/COREX_INTERNAL_PERFORMANCE_IMPROVEMENT_QA_MATRIX.md`
- `docs/specs/perf/ENGINEERING_VIEWER_V1_NATIVE_PERF_REPORT.md`

## Current Measurement Ownership

- `node_visual_quality.py` owns the deterministic production-node visual fixture and the opt-in `--control-interactions` pointer measurements. Scalar sliders, switches, settings expansion/collapse, and actual Sticky Note resizing require committed state or geometry followed by a later `afterRendering` callback. Settings evidence additionally requires observed animation, changing geometry/progress, completion, and nonempty active-frame intervals. Target lookup and screenshot readback are outside timed control intervals; the metric excludes physical monitor presentation. The capture script records native light/dark zoom and DPR evidence through the same production QQuickWidget host, with import-root/style/renderer/fixture metadata. The benchmark host supplies the same shell-context theme bridge contract as production.

- `scripts/profile_canvas_lag.py --selection` delegates to `scripts/canvas_selection_profile.py` for production canvas mouse clicks in a composed shell with isolated preferences and an inert execution client. It measures dispatch and click-to-QML-render completion separately, verifies selection bindings before the accepted render, and records cleared inspector visual counts across collapsed, Smart Groups, Accordion, and Palette modes. The Windows/D3D11 p95 gate is `<100 ms`; `afterRendering` excludes widget composition, GPU completion, and display presentation. See [Inspector Selection Performance](../../specs/perf/INSPECTOR_SELECTION_PERFORMANCE_QA.md).
- State-side `visible_node_model_update_ms` is the sole visible-publication timing source. Harness-forced exact refresh, Qt event drain, render callback, readback, and post-readback drain are separate non-additive phases.
- Fast-pan retained-row publication is coalesced to one refresh per GUI frame while the exact viewport remains inside the current retained region. A strict-viewport escape forces an immediate refresh; stress evidence should therefore report both bounded delegate counts and visible-host continuity rather than treating offscreen timing alone as UX acceptance.
- The canonical drag control uses `12` offsets and reports first offset, steady offsets, full gesture, and end/clear separately. The legacy single-offset value is continuity-only; the selected three-node control is supplemental diagnostic evidence and never replaces formal display gates.
- Harness and `scripts/profile_canvas_lag.py` drag probes emit plain drags (`dragOffsetChanged(nodeId, dx, dy, "", False)`: no Shift lock, no Alt bypass), so with the default-on `graphics.interaction.smart_guides` preference their timings can include smart-guide work: the gesture's one snapshot at the first offset the frame scheduler flushes (or at a release commit, if no flush came first), then one engine resolve per flush. `GraphCanvasSmartGuides.qml` counts this in `profileSnapshotCount`, `profileResolveCount`, and `profileLastSnapshotMs`; keep it in mind when comparing with drag baselines recorded before smart guides. Zoomed out, a snapshot keeps at most 128 candidates (`SMART_GUIDE_CANDIDATE_LIMIT`): on the real stress fixture (offscreen, one node near the view centre) that took the first drag frame with guides on from +16.9 / +40.2 ms p50 over guides off, with GC stalls to 210 / 393 ms p95, to +6.2 / +8.4 ms at zoom 0.25 / 0.12, and the snapshot from 17.5 / 37 ms to 3.5 / 5 ms; zoom 0.5 and 1 stay at +2.3 / +1.2 ms. Steady drag frames in that run cost +5.6 ms p50 at zoom 0.12 but +0.09 ms at 0.25, where the snapshot holds the same 128 candidates, so the cap does not explain the 0.12 steady cost; its cause is unexplained and open (one offscreen run each, not verified as GC). A trimmed snapshot is also retaken during a long drag (the drop-gap rule in the [input-layers route](graph_canvas_input_layers.md)); on this fixture that is floor-bound, once per 40 screen px of travel but at most once per `retakeMinIntervalMs` (80 ms), about 5 ms p50 / 9 ms p95 each at zoom 0.12. At 60 fps a 2000-unit drag at 30 px a frame retakes once at zoom 0.12 and 3 times at 0.25 (3 and 8 times without the interval), and at 4 px a frame 5 and 12 times either way.
- The `node_insertions` scenario measures confirmed insertion dispatch, including synchronous undo capture, through the first later `QQuickWindow.afterRendering` frame where every inserted active-scope primary `graphNodeCard` is visible with non-zero bounds. It runs `ordinary_node`, `group_backdrop`, `small_custom_workflow`, and `nested_custom_workflow` profiles with `3` warmups per profile and a `40`-sample measured budget balanced round-robin across those profiles by default, reports p50/p95, excludes readback and heavy-content readiness, and applies the strict `<100 ms` p95 gate only to display-attached Windows/D3D11 runs.
- Retained reports containing `current_creation_profile` are historical evidence superseded by creation-profile removal. Preserve them, but do not treat that profile as part of the current harness contract.
- Retain wall-clock insertion evidence only from an otherwise idle machine. Concurrent test/build agents contend with Qt's GUI/render callbacks; use unrelated load, pan/zoom, and no-readback frame controls to identify a contaminated run and keep those results diagnostic rather than replacing the retained baseline.
- `tests/test_track_h_perf_harness.py` owns baseline-compatible membership-freeze feature detection, attribution sums, and selected-control report schema. The retained interpretation lives in `COREX_INTERNAL_PERFORMANCE_IMPROVEMENT_QA_MATRIX.md`.
- The same test owns the smart-guide counter guard. Both drag controls read `smartGuidesRef` before a measured gesture and after its clear, and report per-gesture snapshot, resolve, and in-session flush counts plus `profileLastSnapshotMs` as optional fields (`smart_guides_supported` is false on a build without the controller). With guides on, a gesture that flushed a frame must take exactly one snapshot and one that flushed none must take none, so a clear never spends one; with guides off, none. A snapshot trimmed to the candidate limit (the stress fixture's already is at zoom 0.5) is retaken only after at least the controller's 40 screen px re-snapshot floor of travel from the offset it was ranked at: 20 scene units at the default maximum interaction zoom 2, 80 at 0.5. A harness gesture moves a node at most 21.1 scene units in 12 offsets and takes its snapshot at the first flushed offset, at least 1/12 of the way, so it travels at most 19.4 units past it and the guard still holds. The canonical single-node gesture leaves flushing to the 16 ms scheduler timer, so it can flush zero frames, and its per-phase p50s are bimodal, since that flush can land in the control, steady-offset, or end/clear window. Compare per-sample totals, or run guides on against guides off in one tree, rather than single-phase p50s.
- On the default QQuickWidget host, `render_frame()` reads back through `widget.grab()`, which renders any pending frame inside the readback. A step that re-processes many retained edge `Shape` delegates therefore lands in `readback_grab_ms` rather than the render-callback wait. When comparing edge-renderer changes, also read the no-readback frame metrics or time frames to `afterRendering` directly, and alternate before/after runs: flowchart pan/zoom p50s moved about ±10% between identical runs on 2026-09-26.
- `graph_mutations` accepts repeatable `--mutation-scenario` filters in canonical order; omitting the option runs all seven cases. `create_edge` measures programmatic production mutation dispatch through the first rendered frame, not pointer travel, port hit-testing, or the pointer gesture used to create an edge.
- Repeated baselines use isolated child processes by default. Completed and failed run JSON files are replaced atomically in the report directory, later runs continue after a child failure, and the aggregate records completed/failed counts plus failure details. `--baseline-in-process` is a diagnostic opt-out only.
- Harness progress is one flushed bounded line per mutation scenario and baseline run. `--compare-to` prints only the fixed load, pan/zoom, steady-drag, mutation-wall-p95, and RSS scalar table; it never expands `baseline_series` or raw sample arrays.
- Feature-parity evidence includes the default-on `graphics_notched_ports` preference as `notched_ports_enabled`; a disabled notch treatment is a zero-loss failure just like hidden grid, minimap, shadows, or port labels.
- The `animated_media` scenario creates input-hidden `media.panel` fixtures with authored GIF sources, uses `--nodes` with `--edges 0`, and reads the generic `GraphNodeHost.inVisibleViewport` fact. It reports confirmed animator instances, visible/playing/idle/offscreen counts, preview states, policy violations, process CPU, and RSS. Offscreen/software runs are regression evidence; retain three-run 20- and 100-panel CPU/RSS results as release baselines rather than absolute resource gates.
- The engineering-viewer benchmark generates CAD/FE overlay geometry under
  `artifacts/`, drives the real asynchronous binder, and accepts release metrics
  only on display-attached Windows with Qt Quick `Direct3D11Rhi`. Its retained
  report covers interaction p95, full-detail restoration, warm coarse frame,
  maximum UI-thread stall, and release-on-close.
- `scripts/profile_canvas_lag.py --engineering-step <path>` runs one production CAD Import/Model Viewer flow without a second benchmark framework. Its ordered phases prove initial proxy/no warm-up; selection, hover, and single-click inactivity; proxy-viewport double-click activation; temporary wheel/box/drag/resize/wire suppression; background demotion; retained reactivation; unrelated graph mutations; and deletion. Reports separate transition, continuous, and restoration counters plus `afterRendering` frame intervals, widget identity, binder lifecycle, cached-preview, native-geometry, and overlay-sync evidence.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --help
.\venv\Scripts\python.exe scripts/profile_canvas_lag.py --selection --qt-platform windows --qsg-rhi-backend d3d11 --samples 20 --warmup 3 --output-path artifacts/canvas_lag_profiling/inspector_selection/windows_d3d11.json
.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario node_insertions --nodes 200 --edges 320 --seed 1337 --node-insertion-samples 40 --node-insertion-warmup-samples 3 --baseline-runs 1 --baseline-mode interactive --qt-platform windows --qsg-rhi-backend d3d11 --report-dir artifacts/perf_benchmarks/node_insert_typical
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario node_insertions --stress-fixture real --node-insertion-samples 40 --node-insertion-warmup-samples 3 --baseline-runs 1 --baseline-mode interactive --qt-platform windows --qsg-rhi-backend d3d11 --report-dir artifacts/perf_benchmarks/node_insert_stress
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --mutation-scenario create_edge --nodes 12 --edges 20 --load-iterations 1 --interaction-samples 1 --interaction-warmup-samples 0 --baseline-runs 1 --qt-platform offscreen --qsg-rhi-backend software --report-dir artifacts/perf_benchmarks/create_edge_smoke
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --mutation-scenario create_edge --baseline-runs 3 --compare-to artifacts/perf_benchmarks/reference/track_h_benchmark_report.json --report-dir artifacts/perf_benchmarks/current
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario animated_media --nodes 20 --edges 0 --baseline-runs 3 --qt-platform offscreen --qsg-rhi-backend software
.\venv\Scripts\python.exe scripts\generate_flowchart_perf_fixture.py
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --project-path artifacts\perf_fixtures\flowchart_edge_perf.cxproj --load-iterations 1 --interaction-samples 10 --interaction-warmup-samples 3 --interaction-zoom-min 0.3 --interaction-zoom-max 0.35 --baseline-runs 1 --qt-platform windows --qsg-rhi-backend d3d11 --baseline-mode interactive --report-dir artifacts/perf_benchmarks/flowchart_edges
.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.engineering_viewer_benchmark --report-dir artifacts/engineering_viewer_benchmark --resolution 160 --interaction-samples 20 --qt-platform windows --qsg-rhi-backend d3d11
```

## Breadcrumbs
- [Graph Canvas Rendering, Input, And Viewport](../subsystems/graph_canvas.md)
- [Packaging And Generated Assets](../subsystems/packaging_generated_assets.md)
- [Track H Benchmark Report](../../specs/perf/TRACK_H_BENCHMARK_REPORT.md)
- [Graph Canvas Perf QA Matrix](../../specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md)
- [COREX Change Locality QA Matrix](../../specs/perf/COREX_CHANGE_LOCALITY_QA_MATRIX.md)
- [COREX Internal Performance Improvement QA Matrix](../../specs/perf/COREX_INTERNAL_PERFORMANCE_IMPROVEMENT_QA_MATRIX.md)
- [Engineering Viewer Native Performance Report](../../specs/perf/ENGINEERING_VIEWER_V1_NATIVE_PERF_REPORT.md)

## Update Triggers
Update when performance harness flags, activity-property names, viewport-fact reporting, stress fixtures, graph performance packets, benchmark commands, or mutation-churn closeout proof paths change.
