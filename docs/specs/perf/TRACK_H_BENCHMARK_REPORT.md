# Track H Benchmark Report

- Updated: `2026-03-20`
- Evidence Status: real `GraphCanvas.qml` offscreen heavy-media regression snapshot refreshed after `GRAPHICS_PERFORMANCE_MODES` `P09`.
- Snapshot Command:
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_docs`
- Artifact Paths: `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json`
- Current Constraint: This checked-in snapshot was captured under `QT_QPA_PLATFORM=offscreen` with `QT_QUICK_BACKEND=software`, `QSG_RHI_BACKEND=software`, and `QQuickWindow.grabWindow()` readback. Interactive desktop/GPU validation remains required before treating the numbers as release sign-off evidence.

## Benchmark Contract

- `ea_node_editor.telemetry.performance_harness` instantiates `ea_node_editor/ui_qml/components/GraphCanvas.qml` for pan/zoom timings and records the render path, viewport size, Qt platform, sample counts, selected `performance_mode`, resolved `resolved_graphics_performance_mode`, active `scenario`, and `media_surface_count` in every report.
- The checked-in heavy-media snapshot reuses the `P09` seam: generated local PNG/PDF fixtures plus built-in image/PDF panels still exercise the same real `GraphCanvas.qml` render path while `max_performance` is active.
- The project+graph load metric still measures serializer/model/bridge setup; it does not wait for a fully rendered `GraphCanvas.qml` frame.
- Use `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` for the approved offscreen regression command, the canonical artifact path, and the still-required interactive desktop/manual follow-up.

## 2026-03-20 Offscreen Snapshot

- Generated (UTC): `2026-03-20T19:34:47.516064+00:00`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`
- Qt Quick backend: `software`
- QSG RHI backend: `software`

### Config

- Synthetic graph: `120` nodes / `320` edges
- Seed: `1337`
- Load iterations: `1`
- Pan/zoom samples: `10`
- Baseline runs: `1`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Node mix: `114` execution / `3` image panels / `3` PDF panels
- Generated fixtures: `3` images / `1` PDFs

### Interaction Benchmark

- Kind: `graph_canvas_qml`
- Render path: `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- Driver: `ViewportBridge.centerOn + ViewportBridge.set_zoom with QQuickWindow.grabWindow()`
- Viewport: `1280` x `720`
- Theme pair: `stitch_dark` / `graph_stitch_dark`
- Selected performance mode: `max_performance`
- Resolved canvas mode: `max_performance`
- Scenario: `heavy_media`
- Media surface count: `6`
- Real canvas path: `True`

### Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 82.356 | 82.356 | 82.356 | 82.356 | 82.356 |
| Pan interaction | 93.133 | 96.559 | 93.166 | 90.418 | 98.616 |
| Zoom interaction | 149.593 | 151.864 | 148.990 | 144.962 | 152.048 |
| Pan + zoom (combined) | 243.280 | 246.495 | 242.155 | 235.827 | 247.073 |

### Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size `120` nodes / `320` edges, so this docs-refresh snapshot is below target-scale acceptance coverage |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=`96.559 ms`, zoom p95=`151.864 ms`, combined p95=`246.495 ms` (target `<= 33 ms`) |
| REQ-PERF-003 | PASS | Project+graph load p95=`82.356 ms` (target `< 3000 ms`) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Run count: `1`

| Run | Mode | Load p95 (ms) | Pan+Zoom p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---|---|
| run_01 | offscreen | 82.356 | 246.495 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.0000 | 0.000 | PASS |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0000 | 0.000 | PASS |

### Triage

- If variance check fails, first rerun `3x` on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.
- Note: variance checks are informative only when `run_count >= 2`. This single-run capture is still useful as point-in-time regression evidence.

## Desktop Follow-Up

- Prerequisites: run on a display-attached Windows desktop in this worktree, remove `QT_QPA_PLATFORM=offscreen`, and keep the canonical report directory `artifacts/graphics_performance_modes_docs`.
- Interactive command:
  `QT_QPA_PLATFORM=windows ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_docs`
- Manual spot-check: switch the app to `Max Performance` through Graphics Settings or the status strip, load a heavy-media graph, and pan/wheel-zoom for a few seconds. Expected result: image/PDF proxy surfaces appear only during the degraded interaction window, there is no stuck cache state, and the idle/full-fidelity appearance returns after interaction settles.
- Keep this checked-in report explicit about offscreen-only evidence until that desktop run replaces the canonical `artifacts/graphics_performance_modes_docs/*` snapshot.

## Limitations

- Pan/zoom timings instantiate `GraphCanvas.qml` in a `QQuickWindow` and include `QQuickWindow.grabWindow()` readback overhead so frame completion is deterministic.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate `GraphCanvas.qml`.
- Offscreen runs use software Qt Quick / RHI backends, so GPU/compositor behavior differs from interactive desktop rendering.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware tier for regressions.
