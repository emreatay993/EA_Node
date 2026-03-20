# P09 Perf Harness Modes + Heavy Media Wrap-Up

## Implementation Summary

- Packet: `P09`
- Branch Label: `codex/graphics-performance-modes/p09-perf-harness-modes-heavy-media`
- Commit Owner: `worker`
- Commit SHA: `7daba42fa2ac3d0ff96af5106a1eb1817a4c8c15`
- Changed Files: `ea_node_editor/ui/perf/performance_harness.py`, `tests/test_track_h_perf_harness.py`, `artifacts/graphics_performance_modes_p09/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graphics_performance_modes_p09/track_h_benchmark_report.json`, `artifacts/graphics_performance_modes_p09_review/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graphics_performance_modes_p09_review/track_h_benchmark_report.json`, `docs/specs/work_packets/graphics_performance_modes/P09_perf_harness_modes_heavy_media_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graphics_performance_modes/P09_perf_harness_modes_heavy_media_WRAPUP.md`, `artifacts/graphics_performance_modes_p09/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graphics_performance_modes_p09/track_h_benchmark_report.json`, `artifacts/graphics_performance_modes_p09_review/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graphics_performance_modes_p09_review/track_h_benchmark_report.json`
- Report Contract: `ea_node_editor/ui/perf/performance_harness.py` now records additive `performance_mode`, `scenario`, `scenario_details`, `resolved_graphics_performance_mode`, and `media_surface_count` fields while keeping the existing telemetry entrypoint stable.
- Heavy-Media Scenario: the harness now generates reusable local PNG/PDF fixtures, builds a mixed image/PDF-heavy scene that still runs through the real `GraphCanvas.qml` path, and emits packet-owned smoke/review reports under the required artifact directories.
- Automation Footprint: the heavy-media smoke and review commands intentionally use reduced-size graphs with a 3-image / 3-PDF media mix so the offscreen packet verification path remains runnable while still exercising the media surface render path.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_p09` -> `load_p95=63.549 ms`, `pan_zoom_p95=218.576 ms`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_p09_review` -> `load_p95=57.737 ms`, `pan_zoom_p95=139.051 ms`
- Final Verification Verdict: PASS

## Manual Test Directives

- `$manual-test-directives` was unavailable in this session, so concise packet-specific steps are recorded directly here.
- Ready for manual testing.
- From an interactive desktop session in this worktree, rerun `./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_p09_desktop`.
- Confirm the generated JSON or markdown report records `config.performance_mode=max_performance`, `config.scenario=heavy_media`, `interaction_benchmark.resolved_graphics_performance_mode=max_performance`, and `interaction_benchmark.media_surface_count=6`.
- Compare the desktop run against the packet-owned offscreen artifacts before treating the timings as sign-off evidence.

## Residual Risks

- The packet smoke and review artifacts intentionally use reduced-size heavy-media graphs, so `REQ-PERF-001` remains false in those captures and they are not final scale-signoff evidence.
- The offscreen heavy-media timings still fail `REQ-PERF-002` (`pan/zoom` frame target `<= 33 ms`) in both packet artifacts.
- Heavy-media interaction sampling recycles the `GraphCanvas` host per sample to keep the offscreen path stable; those timings are conservative relative to a continuously-open desktop session.

## Ready for Integration

- Yes: packet scope is implemented, the required verification and review commands passed, and the additive report contract plus packet-owned artifacts are ready for downstream `P10` docs and traceability work.
