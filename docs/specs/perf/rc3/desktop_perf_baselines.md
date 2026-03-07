# RC3 Desktop Performance Baselines

- Packet: RC3-P03
- Date: 2026-03-01
- Source benchmark JSON: docs/specs/perf/track_h_benchmark_report.json
- Benchmark command: venv\\Scripts\\python -m ea_node_editor.telemetry.performance_harness

## Current Evidence Snapshot

- Mode: offscreen
- Tag: local
- Run count: 1
- Latest load p95: 318.950 ms
- Latest pan+zoom p95: 30.205 ms
- Machine: EA / AMD64 / Intel64 Family 6 Model 154 Stepping 3, GenuineIntel

## Variance Threshold Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.0000 | 0.000 | PASS |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0000 | 0.000 | PASS |

- Variance gates are provisional because only one run is available in this environment.

## Interactive Desktop Collection Procedure

1. Run desktop baseline collection on each pilot hardware tier:
   - venv\\Scripts\\python -m ea_node_editor.telemetry.performance_harness --baseline-mode interactive --baseline-runs 3 --baseline-tag <hardware_tier> --qt-platform windows
2. Record generated JSON and markdown outputs for each tier.
3. Compare load_p95_ms and pan_zoom_p95_ms variance against thresholds in this document.

## Failure Triage Criteria

1. If threshold fails, rerun 3x on the same machine with background load minimized.
2. If variance still fails, split baselines by hardware tier and keep separate reference envelopes.
3. Escalate as regression only when failures persist across two consecutive captures in the same tier.

## Output Artifact

- docs/specs/perf/rc3/desktop_perf_runs.json
