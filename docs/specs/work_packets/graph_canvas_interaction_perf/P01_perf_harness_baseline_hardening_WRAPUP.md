# P01 Perf Harness Baseline Hardening Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/graph-canvas-interaction-perf/p01-perf-harness-baseline-hardening`
- Commit Owner: `worker`
- Commit SHA: `aa125fae8dd2e65cdad2c90c58132c48a0fbdc1c`
- Changed Files: `ea_node_editor/ui/perf/performance_harness.py`, `tests/test_track_h_perf_harness.py`, `docs/specs/work_packets/graph_canvas_interaction_perf/P01_perf_harness_baseline_hardening_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graph_canvas_interaction_perf/P01_perf_harness_baseline_hardening_WRAPUP.md`, `artifacts/graph_canvas_interaction_perf_p01/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_interaction_perf_p01/track_h_benchmark_report.json`

The harness now reuses one warmed real `GraphCanvas.qml` host for steady-state interaction sampling, records explicit `project_graph_load_ms` / `canvas_setup_ms` / `canvas_warmup_ms` phase slices, and adds a `node_drag_control_ms` metric beside the existing pan, zoom, and combined pan+zoom summaries. Baseline reports stay backward-compatible by preserving `pan_zoom_p95_ms` while adding separate `pan_p95_ms`, `zoom_p95_ms`, and `node_drag_control_p95_ms` series plus the explicit real-canvas reuse evidence in the interaction benchmark payload.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 6 --baseline-runs 1 --performance-mode full_fidelity --scenario synthetic_exec --report-dir artifacts/graph_canvas_interaction_perf_p01`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: stay on `codex/graph-canvas-interaction-perf/p01-perf-harness-baseline-hardening` in this packet worktree and use `./venv/Scripts/python.exe`.
- Run `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 6 --baseline-runs 1 --performance-mode full_fidelity --scenario synthetic_exec --report-dir artifacts/graph_canvas_interaction_perf_p01_manual`; expected result: the report directory contains both benchmark files, the markdown report includes `Phase Timings (ms)` with `canvas_setup_ms`, `canvas_warmup_ms`, `pan_interaction_ms`, `zoom_interaction_ms`, and `node_drag_control_ms`, and the interaction benchmark section still names `ea_node_editor/ui_qml/components/GraphCanvas.qml`.
- Inspect `artifacts/graph_canvas_interaction_perf_p01_manual/track_h_benchmark_report.json`; expected result: `interaction_benchmark.steady_state_canvas_host_reused` is `true`, `interaction_benchmark.warmup_samples` matches the configured warmup count, and `baseline_series.metric_series` contains separate `pan_p95_ms` and `zoom_p95_ms` arrays while preserving `pan_zoom_p95_ms`.

## Residual Risks

- Offscreen timings still include `QQuickWindow.grabWindow()` readback overhead and software Qt Quick backends, so the new phase slices are regression evidence for same-machine comparisons rather than desktop release-signoff numbers.
- `canvas_setup_ms` is intentionally large because it captures first host creation plus initial real-canvas readiness; later packets should compare it separately from steady-state pan/zoom samples instead of folding it into interaction conclusions.
- The node-drag control seam measures the live drag-preview path with cancellation rather than a committed move, which is appropriate for a smoothness control baseline but not a full node-mutation benchmark.

## Ready for Integration

- Yes: `P01` stays inside the packet write scope, preserves the existing combined compatibility metrics, and passes the required verification plus review-gate commands.
