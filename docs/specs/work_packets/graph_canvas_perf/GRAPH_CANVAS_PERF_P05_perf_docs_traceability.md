# GRAPH_CANVAS_PERF P05: Perf Docs Traceability

## Objective
- Publish the updated graph-canvas performance workflow, evidence, and traceability after the runtime optimization packets land.

## Preconditions
- `P00` through `P04` are marked `PASS` in [GRAPH_CANVAS_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md).
- No later `GRAPH_CANVAS_PERF` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- benchmark evidence docs under `docs/specs/perf/`
- performance and QA requirement docs
- traceability and proof-audit coverage

## Conservative Write Scope
- `.gitignore`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `scripts/check_traceability.py`
- `tests/test_traceability_checker.py`

## Required Behavior
- Update the benchmark/report guidance so REQ-PERF evidence now points at the real `GraphCanvas.qml` pan/zoom benchmark introduced in `P01`.
- Add a focused graph-canvas FPS QA matrix that records the approved regression commands, sample sizes, environment limits, and any required desktop/manual follow-up.
- Update performance and QA requirement docs so they reference the current graph-canvas benchmark path and evidence expectations honestly.
- Update traceability and proof-audit coverage so the new graph-canvas QA matrix is represented and checked.
- If the new QA matrix lives under `docs/specs/perf/`, add the narrow `.gitignore` exception needed to track it.
- Keep the docs explicit about offscreen versus interactive desktop limits and any remaining residual risks after `P04`.

## Non-Goals
- No new runtime optimization work.
- No new user-facing settings or UX changes.
- No attempt to hide unresolved risks; record them plainly if they remain.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_docs`
3. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_perf/P05_perf_docs_traceability_WRAPUP.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`

## Acceptance Criteria
- The targeted benchmark and traceability tests pass.
- The traceability checker passes with the updated performance evidence/docs.
- `TRACK_H_BENCHMARK_REPORT.md`, the new QA matrix, and the requirement/traceability docs all point at the real graph-canvas benchmark path rather than only the pre-packet bridge-only baseline.
- Any remaining desktop-only validation requirement is documented explicitly, not implied away.

## Handoff Notes
- Record the exact benchmark command, node/edge counts, sample size, Qt platform, and machine context used for the updated evidence.
- If interactive desktop validation is still outstanding, state that clearly in both the wrap-up and the QA matrix.
