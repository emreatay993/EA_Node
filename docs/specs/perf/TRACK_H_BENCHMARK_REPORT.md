# Track H Benchmark Report

- Updated: `2026-03-18`
- Evidence Status: Historical offscreen harness baseline restored from repo
  history after the checked-in report disappeared from the current proof layer.
- Snapshot Date (UTC): `2026-03-01T19:10:05.533069+00:00`
- Snapshot Command:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Current Constraint: P08 did not rerun the performance harness. Treat the
  numbers below as the last preserved benchmark snapshot, not as fresh release
  or pilot sign-off evidence.

## Current Guidance

- `ea_node_editor.telemetry.performance_harness` and
  `tests/test_track_h_perf_harness.py` still define the benchmark/report
  contract in source.
- Rerun the harness on the target desktop before making new performance claims.
- Offscreen numbers will differ from interactive desktop GPU/compositor timing.

## Archived 2026-03-01 Snapshot

- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`

### Config

- Synthetic graph: `1000` nodes / `5000` edges
- Seed: `1337`
- Load iterations: `5`
- Pan/zoom samples: `200`

### Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 295.201 | 345.132 | 303.838 | 277.964 | 355.577 |
| Pan interaction | 10.652 | 14.101 | 10.644 | 5.717 | 16.087 |
| Zoom interaction | 15.835 | 17.649 | 15.993 | 14.226 | 27.585 |
| Pan + zoom (combined) | 26.730 | 30.222 | 26.637 | 20.985 | 41.575 |

### Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | PASS | Generated graph size 1000 nodes / 5000 edges |
| REQ-PERF-002 | PASS | Pan p95=14.101 ms, Zoom p95=17.649 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=345.132 ms (target < 3000 ms) |

## Limitations

- Measurements are from a Python-level harness and include event-loop
  processing overhead.
- Runs use Qt offscreen platform (`QT_QPA_PLATFORM=offscreen`), so GPU and
  compositor behavior differs from interactive desktop rendering.
- Absolute timings are machine- and load-dependent; compare trends on the same
  hardware for regressions.
