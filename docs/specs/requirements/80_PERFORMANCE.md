# Performance Requirements

## Targets
- `REQ-PERF-001`: Target scale is `1000` nodes / `5000` edges per scene. Published benchmark evidence shall record the exact synthetic graph size used for each run.
- `REQ-PERF-002`: Pan/zoom p95 frame time target is `<= 33 ms` on reference hardware when measured through the actual `ea_node_editor/ui_qml/components/GraphCanvas.qml` render path.
- `REQ-PERF-003`: Project load target is `< 3s` for a target-scale graph. Published load timings shall state whether they measure serializer/model/bridge setup only or a fully rendered frame.

## Rendering Strategy
- `REQ-PERF-004`: Viewport interaction work shall stay on the `ViewportBridge` / `GraphCanvas.qml` path and avoid duplicate pan/zoom invalidation scheduling.
- `REQ-PERF-005`: Edge, label, and background work shall stay viewport-aware and avoid full-scene processing when offscreen content cannot contribute to the visible frame.
- `REQ-PERF-006`: Node/edge presentation shall avoid hot-path allocations where practical and may use interaction-only cache reuse only if the steady-state idle appearance returns automatically after viewport input settles.

## Concurrency
- `REQ-PERF-007`: Heavy execution/analysis work shall run outside the UI thread.

## Evidence Workflow
- `AC-REQ-PERF-002-01`: `ea_node_editor.telemetry.performance_harness` plus `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` shall publish pan/zoom p50/p95 metrics, Qt platform, viewport size, sample counts, and whether the actual `GraphCanvas.qml` render path was exercised.
- `AC-REQ-PERF-002-02`: `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` shall record the approved offscreen regression command and the remaining interactive desktop/manual follow-up required before claiming desktop sign-off.
- `AC-REQ-PERF-003-01`: `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` shall publish the current load-timing snapshot from the same benchmark workflow and point at the generated artifact path used for the recorded evidence.
