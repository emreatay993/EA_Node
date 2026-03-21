# Track H Benchmark Report

- Generated (UTC): `2026-03-21T09:59:17.895770+00:00`
- Command:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`

## Config

- Synthetic graph: `120` nodes / `320` edges
- Seed: `1337`
- Load iterations: `1`
- Warmup samples: `3`
- Pan/zoom samples: `10`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Node mix: `114` execution / `3` image panels / `3` PDF panels
- Generated fixtures: `3` images / `1` PDFs
- Scenario detail: Generated local PNG/PDF fixtures reused across passive media nodes inside the real GraphCanvas.qml benchmark path.

## Interaction Benchmark

- Kind: `graph_canvas_qml`
- Render path: `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- Driver: `Single warmed GraphCanvas host using begin/note/finish viewport interaction + ViewportBridge.centerOn/set_zoom and GraphNodeHost.dragOffsetChanged with QQuickWindow.grabWindow()`
- Viewport: `1280` x `720`
- Theme pair: `stitch_dark` / `graph_stitch_dark`
- Selected performance mode: `max_performance`
- Resolved canvas mode: `max_performance`
- Scenario: `heavy_media`
- Media surface count: `6`
- Real canvas path: `True`
- Reused steady-state host: `True`

## Phase Timings (ms)

| Phase | p50 | p95 | Mean | Min | Max | Samples |
|---|---:|---:|---:|---:|---:|---:|
| project_graph_load_ms | 63.933 | 63.933 | 63.933 | 63.933 | 63.933 | 1 |
| canvas_setup_ms | 1696.502 | 1696.502 | 1696.502 | 1696.502 | 1696.502 | 1 |
| canvas_warmup_ms | 446.344 | 455.112 | 443.980 | 429.510 | 456.086 | 3 |
| pan_interaction_ms | 81.630 | 95.101 | 82.014 | 71.252 | 100.486 | 10 |
| zoom_interaction_ms | 14.655 | 15.829 | 14.617 | 13.606 | 16.115 | 10 |
| node_drag_control_ms | 30.657 | 48.651 | 36.438 | 27.821 | 48.761 | 10 |

## Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 63.933 | 63.933 | 63.933 | 63.933 | 63.933 |
| Pan interaction | 81.630 | 95.101 | 82.014 | 71.252 | 100.486 |
| Zoom interaction | 14.655 | 15.829 | 14.617 | 13.606 | 16.115 |
| Pan + zoom (combined) | 96.398 | 110.291 | 96.631 | 84.857 | 115.966 |
| Node-drag control | 30.657 | 48.651 | 36.438 | 27.821 | 48.761 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size 120 nodes / 320 edges |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=95.101 ms, zoom p95=15.829 ms, node-drag control p95=48.651 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=63.933 ms (target < 3000 ms) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Run count: `3`

| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---:|---:|---:|---|---|
| run_01 | offscreen | 74.852 | 93.075 | 16.451 | 107.118 | 56.230 | offscreen | AMD64 |
| run_02 | offscreen | 64.142 | 92.019 | 16.872 | 106.991 | 47.054 | offscreen | AMD64 |
| run_03 | offscreen | 63.933 | 95.101 | 15.829 | 110.291 | 48.651 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.0754 | 10.919 | PASS |
| pan_p95_ms | 0.20 | 8.0 | 0.0137 | 3.082 | PASS |
| zoom_p95_ms | 0.20 | 8.0 | 0.0261 | 1.042 | PASS |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0141 | 3.300 | PASS |
| node_drag_control_p95_ms | 0.20 | 8.0 | 0.0790 | 9.176 | FAIL |

### Triage

- If variance check fails, first rerun 3x on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.

- Note: Variance checks are informative when run_count >= 2. Single-run captures still provide point-in-time regression evidence.

## Limitations

- Pan/zoom and node-drag control timings reuse one warmed GraphCanvas.qml host in a QQuickWindow and include QQuickWindow.grabWindow() readback overhead so frame completion is deterministic.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate GraphCanvas.qml.
- Runs use Qt offscreen platform (QT_QPA_PLATFORM=offscreen), so GPU/compositor behavior differs from interactive desktop rendering.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware for regressions.
