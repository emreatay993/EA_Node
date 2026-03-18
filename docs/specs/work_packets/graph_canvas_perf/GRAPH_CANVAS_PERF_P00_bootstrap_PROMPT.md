Implement GRAPH_CANVAS_PERF_P00_bootstrap.md exactly. Before editing, read GRAPH_CANVAS_PERF_MANIFEST.md, GRAPH_CANVAS_PERF_STATUS.md, and GRAPH_CANVAS_PERF_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve current canvas visuals and UI/UX contracts unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update GRAPH_CANVAS_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/graph_canvas_perf/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graph-canvas-perf/p00-bootstrap`.
- Review Gate: run the exact `GRAPH_CANVAS_PERF_P00_STATUS_PASS` inline Python command from `GRAPH_CANVAS_PERF_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_MANIFEST.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P00_bootstrap.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P05_perf_docs_traceability.md`
  - `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P05_perf_docs_traceability_PROMPT.md`
- This packet is documentation-only bootstrap work.
- Add only the narrow `.gitignore` exception required for this packet directory.
