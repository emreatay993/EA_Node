# Track H Benchmark Report

- Updated: `2026-03-21`
- Evidence Status: same-machine real `GraphCanvas.qml` heavy-media evidence refreshed after `GRAPH_CANVAS_INTERACTION_PERF` `P09`; the checked-in canonical snapshot remains the offscreen `max_performance` capture, while the Windows desktop/manual exit gate is recorded separately in the packet-owned desktop-reference artifact.
- Snapshot Command:
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_max_performance`
- Artifact Paths: `artifacts/graph_canvas_interaction_perf_p09_max_performance/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_interaction_perf_p09_max_performance/track_h_benchmark_report.json`, `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json`
- Windows Desktop Exit Gate: `PASS` on `2026-03-21`; desktop-reference artifacts: `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json`

## Benchmark Contract

- `ea_node_editor.telemetry.performance_harness` instantiates `ea_node_editor/ui_qml/components/GraphCanvas.qml` for pan/zoom timings and records the render path, viewport size, Qt platform, sample counts, selected `performance_mode`, resolved `resolved_graphics_performance_mode`, active `scenario`, and `media_surface_count` in every report.
- The checked-in canonical heavy-media snapshot reuses the final `P09` seam: generated local PNG/PDF fixtures plus built-in image/PDF panels still exercise the same real `GraphCanvas.qml` render path while `max_performance` is active, and the canonical `artifacts/graphics_performance_modes_docs/*` files are refreshed from that same-machine packet-owned rerun.
- The final packet-owned evidence set also preserves same-machine offscreen `full_fidelity`, explicit node-drag control, and Windows desktop-reference captures under `artifacts/graph_canvas_interaction_perf_p09_*`.
- The project+graph load metric still measures serializer/model/bridge setup; it does not wait for a fully rendered `GraphCanvas.qml` frame.
- Use `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` for the approved rerun commands, the canonical artifact path, and the recorded desktop/manual exit-gate status.

## 2026-03-21 Offscreen Snapshot

- Generated (UTC): `2026-03-21T08:21:32.521494+00:00`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`
- Qt Quick backend: `software`
- QSG RHI backend: `software`

### Config

- Synthetic graph: `120` nodes / `320` edges
- Seed: `1337`
- Load iterations: `1`
- Warmup samples: `3`
- Pan/zoom samples: `10`
- Baseline runs: `3`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Node mix: `114` execution / `3` image panels / `3` PDF panels
- Generated fixtures: `3` images / `1` PDFs

### Interaction Benchmark

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

### Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 67.842 | 67.842 | 67.842 | 67.842 | 67.842 |
| Pan interaction | 80.335 | 97.890 | 81.644 | 70.279 | 103.589 |
| Zoom interaction | 14.530 | 16.657 | 14.771 | 13.503 | 16.728 |
| Pan + zoom (combined) | 94.454 | 112.350 | 96.414 | 84.430 | 118.474 |
| Node-drag control | 30.960 | 48.352 | 36.818 | 28.899 | 48.524 |

### Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size `120` nodes / `320` edges, so this docs-refresh snapshot is below target-scale acceptance coverage |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=`97.890 ms`, zoom p95=`16.657 ms`, node-drag control p95=`48.352 ms` (target `<= 33 ms`) |
| REQ-PERF-003 | PASS | Project+graph load p95=`67.842 ms` (target `< 3000 ms`) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Performance mode: `max_performance`
- Scenario: `heavy_media`
- Run count: `3`

| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---:|---:|---:|---|---|
| run_01 | offscreen | 76.941 | 97.164 | 15.557 | 111.300 | 47.783 | offscreen | AMD64 |
| run_02 | offscreen | 64.792 | 96.687 | 16.063 | 111.519 | 46.515 | offscreen | AMD64 |
| run_03 | offscreen | 67.842 | 97.890 | 16.657 | 112.350 | 48.352 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.0739 | 12.148 | PASS |
| pan_p95_ms | 0.20 | 8.0 | 0.0051 | 1.203 | PASS |
| zoom_p95_ms | 0.20 | 8.0 | 0.0279 | 1.100 | PASS |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0040 | 1.049 | PASS |
| node_drag_control_p95_ms | 0.20 | 8.0 | 0.0161 | 1.837 | PASS |

### Triage

- If variance check fails, first rerun `3x` on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.

## Windows Desktop Exit Gate

- Status: `PASS`
- Desktop command:
  `./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --performance-mode full_fidelity --scenario heavy_media --qt-platform windows --report-dir artifacts/graph_canvas_interaction_perf_p09_desktop_reference`
- Desktop reference facts:
  - Generated (UTC): `2026-03-21T08:45:38.255600+00:00`
  - Qt platform: `windows`
  - Selected performance mode: `full_fidelity`
  - Pan p95=`191.553 ms`, zoom p95=`276.627 ms`, node-drag control p95=`413.152 ms`
  - Manual checklist accepted in-thread to proceed after the desktop run; the packet wrap-up records the accepted smoothness, visual-fidelity, and minimap/edge-label outcomes explicitly.

## Limitations

- Pan/zoom timings instantiate `GraphCanvas.qml` in a `QQuickWindow` and include `QQuickWindow.grabWindow()` readback overhead so frame completion is deterministic.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate `GraphCanvas.qml`.
- The checked-in canonical snapshot still uses the Qt offscreen/software path for determinism, while the packet-owned desktop-reference artifact records the completed Windows exit gate separately.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware tier for regressions.
