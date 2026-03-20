Implement GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media.md. Implement only P09. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P09_perf_harness_modes_heavy_media_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P09; do not start P10.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p09-perf-harness-modes-heavy-media`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_p09_review`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P09_perf_harness_modes_heavy_media_WRAPUP.md`
  - `artifacts/graphics_performance_modes_p09/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graphics_performance_modes_p09/track_h_benchmark_report.json`
  - `artifacts/graphics_performance_modes_p09_review/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graphics_performance_modes_p09_review/track_h_benchmark_report.json`
- Keep this packet on harness/report code and packet-owned benchmark artifacts only. Do not edit canonical docs or traceability here.
