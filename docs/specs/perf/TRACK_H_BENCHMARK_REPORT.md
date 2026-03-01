# Track H Benchmark Report

- Generated (UTC): `2026-03-01T19:59:00.747782+00:00`
- Command:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`

## Config

- Synthetic graph: `1000` nodes / `5000` edges
- Seed: `1337`
- Load iterations: `5`
- Pan/zoom samples: `200`

## Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 295.678 | 318.950 | 294.760 | 261.880 | 322.050 |
| Pan interaction | 10.502 | 13.605 | 10.356 | 5.933 | 16.428 |
| Zoom interaction | 15.396 | 17.845 | 15.684 | 13.657 | 29.010 |
| Pan + zoom (combined) | 25.960 | 30.205 | 26.040 | 20.854 | 41.619 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | PASS | Generated graph size 1000 nodes / 5000 edges |
| REQ-PERF-002 | PASS | Pan p95=13.605 ms, Zoom p95=17.845 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=318.950 ms (target < 3000 ms) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Run count: `1`

| Run | Mode | Load p95 (ms) | Pan+Zoom p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---|---|
| run_01 | offscreen | 318.950 | 30.205 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.0000 | 0.000 | PASS |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0000 | 0.000 | PASS |

### Triage

- If variance check fails, first rerun 3x on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.

- Note: Variance checks are informative when run_count >= 2. Single-run captures still provide point-in-time regression evidence.

## Limitations

- Measurements are from a Python-level harness and include event-loop processing overhead.
- Runs use Qt offscreen platform (QT_QPA_PLATFORM=offscreen), so GPU/compositor behavior differs from interactive desktop rendering.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware for regressions.
