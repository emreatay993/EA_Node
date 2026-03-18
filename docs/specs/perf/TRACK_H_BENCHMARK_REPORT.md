# Track H Benchmark Report

- Updated: `2026-03-18`
- Evidence Status: real `GraphCanvas.qml` offscreen regression snapshot refreshed after `P04`.
- Snapshot Command:
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_docs`
- Artifact Paths: `artifacts/graph_canvas_perf_docs/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_perf_docs/track_h_benchmark_report.json`
- Current Constraint: This checked-in snapshot was captured under `QT_QPA_PLATFORM=offscreen` with `QT_QUICK_BACKEND=software`, `QSG_RHI_BACKEND=software`, and `QQuickWindow.grabWindow()` readback. Interactive desktop/GPU validation remains required before treating the numbers as release sign-off evidence.

## Benchmark Contract

- `ea_node_editor.telemetry.performance_harness` now instantiates `ea_node_editor/ui_qml/components/GraphCanvas.qml` for pan/zoom timings and records the render path, viewport size, Qt platform, and sample counts in every report.
- The project+graph load metric still measures serializer/model/bridge setup; it does not wait for a fully rendered `GraphCanvas.qml` frame.
- Use `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` for the approved offscreen regression commands plus the still-required interactive desktop/manual follow-up.

## 2026-03-18 Offscreen Snapshot

- Generated (UTC): `2026-03-18T12:32:27.278420+00:00`
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

### Interaction Benchmark

- Kind: `graph_canvas_qml`
- Render path: `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- Driver: `ViewportBridge.centerOn + ViewportBridge.set_zoom with QQuickWindow.grabWindow()`
- Viewport: `1280` x `720`
- Theme pair: `stitch_dark` / `graph_stitch_dark`
- Real canvas path: `True`

### Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 27.851 | 27.851 | 27.851 | 27.851 | 27.851 |
| Pan interaction | 114.328 | 127.646 | 109.266 | 80.837 | 128.236 |
| Zoom interaction | 177.383 | 209.871 | 172.184 | 119.398 | 213.061 |
| Pan + zoom (combined) | 287.351 | 323.747 | 281.450 | 237.099 | 335.551 |

### Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size 120 nodes / 320 edges, so this doc-refresh snapshot is below target-scale acceptance coverage |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=`127.646 ms`, zoom p95=`209.871 ms`, combined p95=`323.747 ms` (target `<= 33 ms`) |
| REQ-PERF-003 | PASS | Project+graph load p95=`27.851 ms` (target `< 3000 ms`) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Run count: `1`

| Run | Mode | Load p95 (ms) | Pan+Zoom p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---|---|
| run_01 | offscreen | 27.851 | 323.747 | offscreen | AMD64 |

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

- Run the interactive desktop command published in `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` on a display-attached Windows session without `QT_QPA_PLATFORM=offscreen`.
- Record whether pan/zoom p95 stays above target once the offscreen/software/readback path is removed.
- Keep this checked-in report explicit about offscreen-only evidence until that desktop run is archived.

## Limitations

- Pan/zoom timings instantiate `GraphCanvas.qml` in a `QQuickWindow` and include `QQuickWindow.grabWindow()` readback overhead so frame completion is deterministic.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate `GraphCanvas.qml`.
- Offscreen runs use software Qt Quick / RHI backends, so GPU/compositor behavior differs from interactive desktop rendering.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware tier for regressions.
