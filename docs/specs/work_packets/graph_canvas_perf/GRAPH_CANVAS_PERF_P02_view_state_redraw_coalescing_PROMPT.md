Implement GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing.md exactly. Before editing, read GRAPH_CANVAS_PERF_MANIFEST.md, GRAPH_CANVAS_PERF_STATUS.md, and GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing.md. Implement only P02. Stay inside the packet write scope, preserve current canvas visuals and UI/UX contracts unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graph_canvas_perf/P02_view_state_redraw_coalescing_WRAPUP.md`, update GRAPH_CANVAS_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graph-canvas-perf/p02-view-state-redraw-coalescing`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p02_review`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_perf/P02_view_state_redraw_coalescing_WRAPUP.md`
- Treat redraw ownership as the point of this packet. Do not widen into viewport culling, interaction caching, or docs work.
