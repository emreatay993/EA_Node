Implement GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling.md exactly. Before editing, read GRAPH_CANVAS_PERF_MANIFEST.md, GRAPH_CANVAS_PERF_STATUS.md, and GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling.md. Implement only P03. Stay inside the packet write scope, preserve current canvas visuals and UI/UX contracts unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graph_canvas_perf/P03_edge_label_viewport_culling_WRAPUP.md`, update GRAPH_CANVAS_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graph-canvas-perf/p03-edge-label-viewport-culling`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py -k "graph_canvas_flow_edge_labels_render_and_reduce_at_low_zoom" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_perf/P03_edge_label_viewport_culling_WRAPUP.md`
- Keep the change focused on invisible work. Do not widen into cache strategy or docs updates.
