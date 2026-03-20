# GRAPHICS_PERFORMANCE_MODES P09: Perf Harness Modes + Heavy Media

## Objective
- Extend the real-canvas benchmark/report seam so it records graphics performance mode and a heavy-media scenario, giving later QA/docs work a measurable proof layer for the new architecture.

## Preconditions
- `P00` through `P08` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- `ea_node_editor/ui/perf/performance_harness.py`
- compatibility telemetry import path under `ea_node_editor/telemetry/`
- `tests/test_track_h_perf_harness.py`
- packet-owned benchmark artifact directories under `artifacts/`

## Conservative Write Scope
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- `artifacts/graphics_performance_modes_p09/**`
- `artifacts/graphics_performance_modes_p09_review/**`
- `docs/specs/work_packets/graphics_performance_modes/P09_perf_harness_modes_heavy_media_WRAPUP.md`

## Required Behavior
- Extend the benchmark CLI/report contract so runs record the selected `performance_mode`.
- Add a heavy-media scenario that exercises representative image/PDF-heavy graph content through the actual `GraphCanvas.qml` render path.
- Keep the existing reduced-size automated smoke/review footprint practical for packet verification.
- Preserve the stable telemetry import path and existing benchmark metadata unless a documented additive field is required.
- Add or update tests that lock the new mode/scenario report shape without requiring target-scale desktop runs in automation.

## Non-Goals
- No canonical requirement-doc or traceability updates yet. `P10` owns that.
- No attempt to claim final desktop sign-off in this packet.
- No new runtime optimization work outside measurement seams strictly needed for the benchmark scenario.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_p09`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_p09_review`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P09_perf_harness_modes_heavy_media_WRAPUP.md`
- `artifacts/graphics_performance_modes_p09/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graphics_performance_modes_p09/track_h_benchmark_report.json`
- `artifacts/graphics_performance_modes_p09_review/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graphics_performance_modes_p09_review/track_h_benchmark_report.json`

## Acceptance Criteria
- The benchmark/report contract records `performance_mode`.
- A heavy-media scenario runs through the actual `GraphCanvas.qml` path and produces packet-owned smoke/review artifacts.
- Harness regression tests pass with the additive mode/scenario contract.
- The packet wrap-up records the exact smoke/review commands, graph sizes, and scenario details used.

## Handoff Notes
- Keep the scenario naming and report-field naming stable; `P10` will depend on them for docs and traceability text.
- If the heavy-media scenario uses a reduced-size or synthetic fixture, state that explicitly in the wrap-up.
