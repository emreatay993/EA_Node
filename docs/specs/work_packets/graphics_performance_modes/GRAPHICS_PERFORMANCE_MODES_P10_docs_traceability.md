# GRAPHICS_PERFORMANCE_MODES P10: Docs + Traceability

## Objective
- Update the canonical requirements, benchmark guidance, QA matrix, and traceability/proof-audit coverage so the new graphics performance modes and heavy-node render-quality contract are documented honestly.

## Preconditions
- `P00` through `P09` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P09`

## Target Subsystems
- canonical requirement docs under `docs/specs/requirements/`
- benchmark/QA docs under `docs/specs/perf/`
- proof-audit/traceability coverage under `scripts/` and `tests/`
- packet-owned benchmark artifact directory under `artifacts/`

## Conservative Write Scope
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `scripts/check_traceability.py`
- `tests/test_traceability_checker.py`
- `artifacts/graphics_performance_modes_docs/**`
- `docs/specs/work_packets/graphics_performance_modes/P10_docs_traceability_WRAPUP.md`

## Required Behavior
- Update the canonical requirements so app-wide graphics mode support, the persistent status-strip quick toggle, the render-quality Node SDK contract, and the mode-aware heavy-media benchmark/report obligations are allocated explicitly.
- Update `TRACK_H_BENCHMARK_REPORT.md` and `GRAPH_CANVAS_PERF_QA_MATRIX.md` so they describe the new `performance_mode` and heavy-media evidence seams honestly.
- Update proof-audit/traceability coverage so the new docs/requirements remain enforced by the checker.
- Keep the docs explicit about remaining interactive desktop/manual follow-up if it still exists after `P09`.
- Use the benchmark/report seam from `P09`; do not invent a second canonical performance-report path.

## Non-Goals
- No new runtime implementation work.
- No attempt to hide unresolved desktop-validation gaps.
- No new work-packet planning beyond documenting this packet set’s delivered capability.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_docs`
3. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P10_docs_traceability_WRAPUP.md`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md`
- `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json`

## Acceptance Criteria
- Traceability/proof-audit tests pass.
- The traceability checker passes with the updated requirement and perf-doc surfaces.
- Canonical docs reference the mode-aware heavy-media benchmark/report path introduced in `P09`.
- Any remaining desktop/manual validation requirement is stated plainly in both the checked-in docs and the packet wrap-up.

## Handoff Notes
- Record the exact requirement IDs or acceptance rows that were updated so later audits can diff them quickly.
- If the checker needed new tokens or rows, document that explicitly in the wrap-up.
