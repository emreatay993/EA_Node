# Performance Requirements

## Targets
- `REQ-PERF-001`: Target scale is `1000` nodes / `5000` edges per scene. Published benchmark evidence shall record the exact synthetic graph size used for each run.
- `REQ-PERF-002`: Pan/zoom p95 frame time target is `<= 33 ms` on reference hardware when measured through the actual `ea_node_editor/ui_qml/components/GraphCanvas.qml` render path.
- `REQ-PERF-003`: Project load target is `< 3s` for a target-scale graph. Published load timings shall state whether they measure serializer/model/bridge setup only or a fully rendered frame.

## Rendering Strategy
- `REQ-PERF-004`: Viewport interaction work shall stay on the `ViewportBridge` / `GraphCanvas.qml` path and avoid duplicate pan/zoom invalidation scheduling.
- `REQ-PERF-005`: Edge, label, and background work shall stay viewport-aware and avoid full-scene processing when offscreen content cannot contribute to the visible frame.
- `REQ-PERF-006`: Node/edge presentation shall support an app-global `full_fidelity` / `max_performance` policy: `full_fidelity` may take invisible structural optimizations only, while `max_performance` may use temporary whole-canvas simplification, cache reuse, or proxy-surface strategies during active pan/zoom and structural mutation bursts only if the steady-state idle appearance returns automatically after viewport input settles.

## Concurrency
- `REQ-PERF-007`: Heavy execution/analysis work shall run outside the UI thread.
- `REQ-PERF-008`: the PyDPF viewer closeout shall keep large-model and packaged-viewer performance risk explicit in `docs/specs/perf/PYDPF_VIEWER_V1_QA_MATRIX.md`, including repo-local `.rst` / `.rth` smoke fixtures, Windows packaged-build checks, and any manual large-model validation that remains outside the fast lane.
- `REQ-PERF-009`: When `graphics.canvas.edge_crossing_style` resolves to `gap_break`, crossing decoration shall stay render-only, compute gap sizing in screen space, keep previewed and selected edges above ordinary edges with remaining ties resolved by visible-edge order, and suppress decoration whenever the canvas is in `max_performance` or a transient degraded-rendering window.

## Evidence Workflow
- `AC-REQ-PERF-002-01`: `ea_node_editor.telemetry.performance_harness` plus `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` shall publish pan/zoom p50/p95 metrics, Qt platform, viewport size, sample counts, selected `performance_mode`, resolved `resolved_graphics_performance_mode`, active `scenario`, `media_surface_count`, and whether the actual `GraphCanvas.qml` render path was exercised.
- `AC-REQ-PERF-002-02`: `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` shall record the approved same-machine offscreen regression command with `--baseline-runs 3 --performance-mode max_performance --scenario heavy_media`, the canonical artifact path `artifacts/graphics_performance_modes_docs`, and the current desktop/manual exit-gate status for the packet-owned Windows `desktop_reference` evidence.
- `AC-REQ-PERF-003-01`: `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` shall publish the current load-timing snapshot from the same 3-run mode-aware heavy-media benchmark workflow and point at the canonical artifact path `artifacts/graphics_performance_modes_docs` refreshed from the packet-local max-performance rerun used for the recorded evidence.
- `AC-REQ-PERF-008-01`: `docs/specs/perf/PYDPF_VIEWER_V1_QA_MATRIX.md` records the approved PyDPF viewer reruns, repo-local smoke fixtures, Windows packaged-build and manual checks, and remaining large-model/manual risks without claiming broader automated coverage than the packet set actually ships.
- `AC-REQ-PERF-009-01`: `tests/graph_track_b/qml_preference_bindings.py`, `tests/test_flow_edge_labels.py`, and `docs/specs/perf/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md` record deterministic ordering, render-only gap handling, pipe/bezier crossing coverage, and suppression of crossing decoration during `max_performance` or degraded-rendering windows without changing original hit geometry.
