Implement GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline.md exactly. Before editing, read GRAPH_CANVAS_PERF_MANIFEST.md, GRAPH_CANVAS_PERF_STATUS.md, and GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline.md. Implement only P01. Stay inside the packet write scope, preserve current canvas visuals and UI/UX contracts unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graph_canvas_perf/P01_real_canvas_benchmark_baseline_WRAPUP.md`, update GRAPH_CANVAS_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graph-canvas-perf/p01-real-canvas-benchmark-baseline`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_review`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_perf/P01_real_canvas_benchmark_baseline_WRAPUP.md`
- Keep the benchmark focused on actual `GraphCanvas.qml` render work; do not stop at bridge-only timings.
- Do not widen into redraw optimization or docs updates in this packet.
