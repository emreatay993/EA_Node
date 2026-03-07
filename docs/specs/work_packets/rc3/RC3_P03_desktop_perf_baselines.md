# RC3 P03: Desktop Performance Baselines

## Objective
- Extend performance evidence beyond offscreen runs with repeatable interactive desktop baseline collection and variance thresholds.

## Non-Objectives
- No feature-level UI redesign.
- No weakening of existing RC2 regression benchmark gates.

## Inputs
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/perf/RC2_BENCHMARK_REPORT.md`
- `docs/specs/perf/PILOT_BACKLOG.md`

## Allowed Files
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
- `docs/specs/perf/track_h_benchmark_report.json`
- `docs/specs/perf/rc3/*`

## Do Not Touch
- `ea_node_editor/nodes/**`
- `ea_node_editor/persistence/**`

## Verification
1. `venv\Scripts\python -m unittest tests.test_track_h_perf_harness -v`
2. `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`

## Output Artifacts
- `docs/specs/perf/rc3/desktop_perf_baselines.md`
- `docs/specs/perf/rc3/desktop_perf_runs.json`

## Merge Gate (Requirement IDs)
- `REQ-PERF-001`
- `REQ-PERF-002`
- `REQ-PERF-003`
- `AC-REQ-PERF-002-02`
