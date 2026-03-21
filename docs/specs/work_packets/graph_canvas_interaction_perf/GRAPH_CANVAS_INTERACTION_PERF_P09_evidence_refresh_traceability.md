# GRAPH_CANVAS_INTERACTION_PERF P09: Evidence Refresh And Exit Gate

## Objective
- Re-run the final offscreen regression evidence on the same machine, complete the Windows desktop/manual exit gate, and only then refresh the checked-in performance evidence and any required truthfulness docs.

## Preconditions
- `P08` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `scripts/check_traceability.py`

## Conservative Write Scope
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `scripts/check_traceability.py`
- `artifacts/graph_canvas_interaction_perf_p09_full_fidelity/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_full_fidelity/track_h_benchmark_report.json`
- `artifacts/graph_canvas_interaction_perf_p09_max_performance/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_max_performance/track_h_benchmark_report.json`
- `artifacts/graph_canvas_interaction_perf_p09_node_drag_control/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_node_drag_control/track_h_benchmark_report.json`
- `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json`
- `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P09_evidence_refresh_traceability_WRAPUP.md`

## Required Behavior
- Re-run the offscreen regression on the same machine in `full_fidelity`, `max_performance`, and the explicit node-drag control capture, using the final harness/report fields established earlier in the packet set.
- Complete the Windows desktop/manual exit gate on a display-attached Windows session using the same branch before claiming final packet completion.
- Record the Windows desktop/manual pass in the packet wrap-up, including an explicit manual spot-check for heavy-media pan/zoom smoothness, unchanged full-fidelity visuals, and minimap/edge-label stability.
- Refresh checked-in performance evidence only in this packet, after the offscreen reruns and Windows exit gate are complete.
- Update the QA matrix, benchmark report, and only the requirement/acceptance/traceability docs needed to keep the refreshed evidence and exit-gate status truthful.
- Keep graph size, sample size, Qt platform, selected performance mode, scenario, and whether the real `GraphCanvas.qml` path was exercised explicit in the refreshed evidence.
- Refresh packet-owned artifact outputs for the offscreen and desktop-reference reruns, plus the canonical artifact outputs under `artifacts/graphics_performance_modes_docs/`, in sync with the checked-in benchmark report.
- Keep traceability checks passing after the evidence and requirement-doc refresh.

## Non-Goals
- No new runtime optimization code in this packet unless a tiny traceability-only fix inside scope is strictly required to make the final docs truthful.
- No new user-facing settings or policy changes.
- No expansion of the packet set beyond evidence and traceability closure.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_full_fidelity`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_max_performance`
4. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_node_drag_control`
5. `QT_QPA_PLATFORM=windows ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_desktop_reference`
6. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P09_evidence_refresh_traceability_WRAPUP.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_full_fidelity/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_full_fidelity/track_h_benchmark_report.json`
- `artifacts/graph_canvas_interaction_perf_p09_max_performance/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_max_performance/track_h_benchmark_report.json`
- `artifacts/graph_canvas_interaction_perf_p09_node_drag_control/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_node_drag_control/track_h_benchmark_report.json`
- `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json`
- `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json`

## Acceptance Criteria
- Checked-in perf evidence is refreshed only in this packet and reflects final same-machine offscreen `full_fidelity`, `max_performance`, and node-drag control evidence plus the Windows desktop/manual exit-gate status.
- The packet wrap-up records the Windows desktop/manual spot-check outcome explicitly instead of inferring it from offscreen evidence alone.
- QA, performance, acceptance, and traceability docs stay aligned with the updated evidence.
- Traceability regression coverage and the traceability script both pass.
- Packet-owned offscreen and desktop-reference artifact outputs are preserved, and canonical artifact outputs under `artifacts/graphics_performance_modes_docs/` match the checked-in evidence refresh.

## Handoff Notes
- Record the final offscreen full/max/node-drag benchmark deltas, the Windows desktop/manual exit-gate result, and any remaining residual performance risk in the wrap-up.
- If any evidence still falls short of the target, document it explicitly rather than smoothing it over in the refreshed docs.
