# Track H Benchmark Report

- Generated (UTC): `2026-03-21T08:45:38.255600+00:00`
- Command:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `windows`

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
| project_graph_load_ms | 146.767 | 146.767 | 146.767 | 146.767 | 146.767 | 1 |
| canvas_setup_ms | 2871.894 | 2871.894 | 2871.894 | 2871.894 | 2871.894 | 1 |
| canvas_warmup_ms | 868.972 | 1286.211 | 1009.813 | 827.896 | 1332.571 | 3 |
| pan_interaction_ms | 176.901 | 191.553 | 174.775 | 158.124 | 198.449 | 10 |
| zoom_interaction_ms | 171.866 | 276.627 | 189.663 | 156.546 | 349.500 | 10 |
| node_drag_control_ms | 167.467 | 413.152 | 262.723 | 161.184 | 413.400 | 10 |

## Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 146.767 | 146.767 | 146.767 | 146.767 | 146.767 |
| Pan interaction | 176.901 | 191.553 | 174.775 | 158.124 | 198.449 |
| Zoom interaction | 171.866 | 276.627 | 189.663 | 156.546 | 349.500 |
| Pan + zoom (combined) | 350.344 | 467.096 | 364.439 | 319.303 | 547.948 |
| Node-drag control | 167.467 | 413.152 | 262.723 | 161.184 | 413.400 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size 120 nodes / 320 edges |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=191.553 ms, zoom p95=276.627 ms, node-drag control p95=413.152 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=146.767 ms (target < 3000 ms) |

## Baseline Series

- Mode: `interactive`
- Tag: `desktop_reference`
- Performance mode: `full_fidelity`
- Scenario: `heavy_media`
- Run count: `3`

| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---:|---:|---:|---|---|
| run_01 | interactive | 94.886 | 193.745 | 190.784 | 383.914 | 418.899 | windows | AMD64 |
| run_02 | interactive | 205.614 | 192.332 | 190.031 | 382.363 | 426.157 | windows | AMD64 |
| run_03 | interactive | 146.767 | 191.553 | 276.627 | 467.096 | 413.152 | windows | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.3034 | 110.728 | FAIL |
| pan_p95_ms | 0.20 | 8.0 | 0.0047 | 2.192 | PASS |
| zoom_p95_ms | 0.20 | 8.0 | 0.1855 | 86.596 | FAIL |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0963 | 84.734 | FAIL |
| node_drag_control_p95_ms | 0.20 | 8.0 | 0.0127 | 13.005 | FAIL |

### Triage

- If variance check fails, first rerun 3x on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.

- Note: Variance checks are informative when run_count >= 2. Single-run captures still provide point-in-time regression evidence.

## Limitations

- Pan/zoom and node-drag control timings reuse one warmed GraphCanvas.qml host in a QQuickWindow and include QQuickWindow.grabWindow() readback overhead so frame completion is deterministic.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate GraphCanvas.qml.
- This desktop-reference capture used `Qt platform: windows`; timings still include `QQuickWindow.grabWindow()` readback overhead, so treat it as same-machine desktop evidence rather than release sign-off.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware for regressions.
