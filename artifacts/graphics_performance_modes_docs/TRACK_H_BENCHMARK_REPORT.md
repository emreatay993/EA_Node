# Track H Benchmark Report

- Generated (UTC): `2026-03-20T19:34:47.516064+00:00`
- Command:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`

## Config

- Synthetic graph: `120` nodes / `320` edges
- Seed: `1337`
- Load iterations: `1`
- Pan/zoom samples: `10`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Node mix: `114` execution / `3` image panels / `3` PDF panels
- Generated fixtures: `3` images / `1` PDFs
- Scenario detail: Generated local PNG/PDF fixtures reused across passive media nodes inside the real GraphCanvas.qml benchmark path.

## Interaction Benchmark

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

## Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 82.356 | 82.356 | 82.356 | 82.356 | 82.356 |
| Pan interaction | 93.133 | 96.559 | 93.166 | 90.418 | 98.616 |
| Zoom interaction | 149.593 | 151.864 | 148.990 | 144.962 | 152.048 |
| Pan + zoom (combined) | 243.280 | 246.495 | 242.155 | 235.827 | 247.073 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size 120 nodes / 320 edges |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=96.559 ms, zoom p95=151.864 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=82.356 ms (target < 3000 ms) |

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

- If variance check fails, first rerun 3x on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.

- Note: Variance checks are informative when run_count >= 2. Single-run captures still provide point-in-time regression evidence.

## Limitations

- Pan/zoom timings instantiate GraphCanvas.qml in a QQuickWindow and include QQuickWindow.grabWindow() readback overhead so frame completion is deterministic.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate GraphCanvas.qml.
- Runs use Qt offscreen platform (QT_QPA_PLATFORM=offscreen), so GPU/compositor behavior differs from interactive desktop rendering.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware for regressions.
