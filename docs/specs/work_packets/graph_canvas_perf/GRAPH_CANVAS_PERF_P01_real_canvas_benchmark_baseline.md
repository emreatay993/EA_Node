# GRAPH_CANVAS_PERF P01: Real Canvas Benchmark Baseline

## Objective
- Establish a repeatable benchmark and regression seam that measures actual `GraphCanvas.qml` pan/zoom render cost, not just `GraphSceneBridge` and `ViewportBridge` event-loop timing.

## Preconditions
- `P00` is marked `PASS` in [GRAPH_CANVAS_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md).
- No later `GRAPH_CANVAS_PERF` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- private benchmark-support hooks only if strictly required for deterministic `GraphCanvas.qml` measurement

## Conservative Write Scope
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`

## Required Behavior
- Extend the performance harness so the pan/zoom metric instantiates `GraphCanvas.qml` with theme bridges and a representative synthetic graph before collecting interaction timings.
- Keep the existing load benchmark/report contract stable unless a clearly documented extension is needed for the new real-canvas metric.
- Drive benchmark samples through the real canvas pan and zoom pathways and wait for the resulting frame/event work before recording elapsed time.
- Preserve deterministic, reduced-size verification runs for automated testing so the harness remains practical in CI-sized environments.
- Add or update tests in `tests/test_track_h_perf_harness.py` to lock the new graph-canvas benchmark contract without requiring a full `1000/5000` run.
- Do not optimize product runtime behavior in this packet beyond any private, behavior-neutral measurement seam that is strictly necessary.

## Non-Goals
- No redraw coalescing yet. `P02` owns that.
- No edge/label culling yet. `P03` owns that.
- No viewport-interaction caching yet. `P04` owns that.
- No docs or traceability updates yet. `P05` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_smoke`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_review`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_perf/P01_real_canvas_benchmark_baseline_WRAPUP.md`

## Acceptance Criteria
- `tests/test_track_h_perf_harness.py` passes against the updated harness contract.
- The smoke benchmark command completes successfully and writes report output under `artifacts/graph_canvas_perf_smoke/`.
- The packet wrap-up records the exact benchmark path used for the real-canvas metric and the reduced verification graph size.
- No user-facing canvas behavior, visuals, or interaction contracts are intentionally changed in this packet.

## Handoff Notes
- Later packets must compare their small-sample smoke results against the real-canvas seam introduced here, not against the archived bridge-only baseline alone.
- If the harness has to keep both bridge-only and real-canvas timings, clearly label them so `P05` can update traceability without ambiguity.
