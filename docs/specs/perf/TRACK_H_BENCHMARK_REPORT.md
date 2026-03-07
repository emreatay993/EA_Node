# Track H Benchmark Report

- Generated (UTC): `2026-03-07T22:04:53.697667+00:00`
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
| Project + graph load | 45.691 | 52.112 | 46.794 | 42.619 | 53.343 |
| Pan interaction | 0.003 | 0.004 | 0.003 | 0.002 | 0.028 |
| Zoom interaction | 0.002 | 0.003 | 0.003 | 0.002 | 0.103 |
| Pan + zoom (combined) | 0.005 | 0.006 | 0.006 | 0.005 | 0.107 |

## Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | PASS | Generated graph size 1000 nodes / 5000 edges |
| REQ-PERF-002 | PASS | Pan p95=0.004 ms, Zoom p95=0.003 ms (frame p95 target <= 33 ms) |
| REQ-PERF-003 | PASS | Project+graph load p95=52.112 ms (target < 3000 ms) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Run count: `1`

| Run | Mode | Load p95 (ms) | Pan+Zoom p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---|---|
| run_01 | offscreen | 52.112 | 0.006 | offscreen | AMD64 |

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
