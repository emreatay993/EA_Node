# P01 Real Canvas Benchmark Baseline Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/graph-canvas-perf/p01-real-canvas-benchmark-baseline`
- Commit Owner: `worker`
- Commit SHA: `d2b2135a87395461a2d4563336c52c6bfc080bc7`
- Changed Files: `ea_node_editor/telemetry/performance_harness.py`, `tests/test_track_h_perf_harness.py`
- Artifacts Produced: `docs/specs/work_packets/graph_canvas_perf/P01_real_canvas_benchmark_baseline_WRAPUP.md`, `artifacts/graph_canvas_perf_smoke/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_perf_smoke/track_h_benchmark_report.json`, `artifacts/graph_canvas_perf_review/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_perf_review/track_h_benchmark_report.json`

The pan/zoom harness now instantiates `ea_node_editor/ui_qml/components/GraphCanvas.qml` inside a `QQuickWindow`, injects `ThemeBridge` plus `GraphThemeBridge`, drives `ViewportBridge.centerOn()` and `ViewportBridge.set_zoom()`, and waits for a completed frame through `QQuickWindow.grabWindow()` before recording each sample. The reduced verification seam is locked to `80` nodes / `220` edges for smoke coverage and `50` nodes / `120` edges for the review gate.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_smoke`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_review`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: use the repo root on this branch and the project venv at `./venv/Scripts/python.exe`.
- Run `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_manual`; expected result: the report directory contains both benchmark files and `TRACK_H_BENCHMARK_REPORT.md` includes an `Interaction Benchmark` section pointing at `ea_node_editor/ui_qml/components/GraphCanvas.qml`.
- Launch the app normally and pan/zoom a populated graph workspace; expected result: canvas visuals and interaction behavior match the current baseline because this packet only changes benchmark instrumentation.

## Residual Risks

- Offscreen pan/zoom samples now exercise the real canvas path, but they still include `QQuickWindow.grabWindow()` readback overhead, so absolute numbers should be compared on the same machine rather than treated as desktop GPU FPS.
- `project_graph_load_ms` remains a serializer/model/bridge timing and is intentionally not a full `GraphCanvas.qml` load metric in this packet.
- The reduced smoke and review graphs establish the regression seam, but they do not satisfy the `1000` node / `5000` edge requirement target by themselves.

## Ready for Integration

- Yes: `P01` adds the required real-canvas benchmark seam, passes the packet verification commands and review gate, and stays within the packet write scope.
