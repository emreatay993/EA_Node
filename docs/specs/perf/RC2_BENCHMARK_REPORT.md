# RC2 Benchmark Report

- Source command: `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Source files:
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/track_h_benchmark_report.json`
- Generated UTC: `2026-03-01T19:10:05.533069+00:00`

## Metrics

| Metric | p50 (ms) | p95 (ms) | Mean (ms) |
|---|---:|---:|---:|
| Project + graph load | 295.201 | 345.132 | 303.838 |
| Pan interaction | 10.652 | 14.101 | 10.644 |
| Zoom interaction | 15.835 | 17.649 | 15.993 |
| Pan + zoom combined | 26.730 | 30.222 | 26.637 |

## Gate Check

| Requirement | Target | Actual | Status |
|---|---|---|---|
| REQ-PERF-001 | 1000 nodes / 5000 edges | 1000 / 5000 | PASS |
| REQ-PERF-002 | p95 <= 33 ms | 30.222 ms | PASS |
| REQ-PERF-003 | load p95 < 3000 ms | 345.132 ms | PASS |

## Notes

- Measurements are from offscreen Qt and are suitable for regression checks in this environment.
- Desktop/GPU interactive baselines should still be gathered for final pilot validation.

