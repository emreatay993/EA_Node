# Track H Benchmark Report

- Generated (UTC): `2026-03-21T09:58:50.130475+00:00`
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
| project_graph_load_ms | 65.924 | 65.924 | 65.924 | 65.924 | 65.924 | 1 |
| canvas_setup_ms | 1702.514 | 1702.514 | 1702.514 | 1702.514 | 1702.514 | 1 |
| canvas_warmup_ms | 962.158 | 1041.634 | 904.854 | 701.940 | 1050.465 | 3 |
| pan_interaction_ms | 151.103 | 169.556 | 148.328 | 130.633 | 180.195 | 10 |
| zoom_interaction_ms | 146.246 | 168.789 | 148.173 | 134.236 | 176.055 | 10 |
| node_drag_control_ms | 139.055 | 363.268 | 204.693 | 135.215 | 365.689 | 10 |

## Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 65.924 | 65.924 | 65.924 | 65.924 | 65.924 |
| Pan interaction | 151.103 | 169.556 | 148.328 | 130.633 | 180.195 |
| Zoom interaction | 146.246 | 168.789 | 148.173 | 134.236 | 176.055 |
| Pan + zoom (combined) | 292.351 | 337.216 | 296.501 | 268.677 | 356.251 |
| Node-drag control | 139.055 | 363.268 | 204.693 | 135.215 | 365.689 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size 120 nodes / 320 edges |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=169.556 ms, zoom p95=168.789 ms, node-drag control p95=363.268 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=65.924 ms (target < 3000 ms) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Performance mode: `full_fidelity`
- Scenario: `heavy_media`
- Run count: `3`

| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---:|---:|---:|---|---|
| run_01 | offscreen | 80.650 | 168.296 | 160.608 | 328.689 | 386.574 | offscreen | AMD64 |
| run_02 | offscreen | 65.332 | 180.675 | 163.051 | 335.195 | 386.866 | offscreen | AMD64 |
| run_03 | offscreen | 65.924 | 169.556 | 168.789 | 337.216 | 363.268 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.1003 | 15.318 | PASS |
| pan_p95_ms | 0.20 | 8.0 | 0.0322 | 12.379 | FAIL |
| zoom_p95_ms | 0.20 | 8.0 | 0.0209 | 8.181 | FAIL |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0109 | 8.526 | FAIL |
| node_drag_control_p95_ms | 0.20 | 8.0 | 0.0292 | 23.598 | FAIL |

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
