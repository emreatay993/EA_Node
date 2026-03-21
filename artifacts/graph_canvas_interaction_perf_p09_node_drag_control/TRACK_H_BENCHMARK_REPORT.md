# Track H Benchmark Report

- Generated (UTC): `2026-03-21T10:00:05.401739+00:00`
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
- Performance mode: `full_fidelity`
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
- Selected performance mode: `full_fidelity`
- Resolved canvas mode: `full_fidelity`
- Scenario: `heavy_media`
- Media surface count: `6`
- Real canvas path: `True`
- Reused steady-state host: `True`

## Phase Timings (ms)

| Phase | p50 | p95 | Mean | Min | Max | Samples |
|---|---:|---:|---:|---:|---:|---:|
| project_graph_load_ms | 63.957 | 63.957 | 63.957 | 63.957 | 63.957 | 1 |
| canvas_setup_ms | 1672.182 | 1672.182 | 1672.182 | 1672.182 | 1672.182 | 1 |
| canvas_warmup_ms | 952.426 | 1059.848 | 908.175 | 700.314 | 1071.783 | 3 |
| pan_interaction_ms | 147.883 | 162.502 | 146.602 | 129.738 | 168.824 | 10 |
| zoom_interaction_ms | 145.301 | 163.622 | 145.598 | 128.833 | 167.398 | 10 |
| node_drag_control_ms | 355.733 | 363.032 | 291.185 | 135.003 | 364.368 | 10 |

## Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 63.957 | 63.957 | 63.957 | 63.957 | 63.957 |
| Pan interaction | 147.883 | 162.502 | 146.602 | 129.738 | 168.824 |
| Zoom interaction | 145.301 | 163.622 | 145.598 | 128.833 | 167.398 |
| Pan + zoom (combined) | 289.189 | 326.003 | 292.200 | 262.873 | 336.222 |
| Node-drag control | 355.733 | 363.032 | 291.185 | 135.003 | 364.368 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size 120 nodes / 320 edges |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=162.502 ms, zoom p95=163.622 ms, node-drag control p95=363.032 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=63.957 ms (target < 3000 ms) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Performance mode: `full_fidelity`
- Scenario: `heavy_media`
- Run count: `3`

| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---:|---:|---:|---|---|
| run_01 | offscreen | 72.289 | 167.234 | 159.790 | 326.692 | 378.647 | offscreen | AMD64 |
| run_02 | offscreen | 56.422 | 168.784 | 234.658 | 395.108 | 383.687 | offscreen | AMD64 |
| run_03 | offscreen | 63.957 | 162.502 | 163.622 | 326.003 | 363.032 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.1009 | 15.866 | PASS |
| pan_p95_ms | 0.20 | 8.0 | 0.0161 | 6.282 | PASS |
| zoom_p95_ms | 0.20 | 8.0 | 0.1851 | 74.869 | FAIL |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0928 | 69.105 | FAIL |
| node_drag_control_p95_ms | 0.20 | 8.0 | 0.0234 | 20.654 | FAIL |

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
