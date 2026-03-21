Implement GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap.md exactly. Before editing, read GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md, GRAPH_CANVAS_INTERACTION_PERF_STATUS.md, and GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve locked defaults and current full-fidelity visuals unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update GRAPH_CANVAS_INTERACTION_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graph-canvas-interaction-perf/p00-bootstrap`.
- Review Gate: run the exact `GRAPH_CANVAS_INTERACTION_PERF_P00_STATUS_PASS` inline Python command from `GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P01_perf_harness_baseline_hardening.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P01_perf_harness_baseline_hardening_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P02_atomic_viewport_state_updates.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P02_atomic_viewport_state_updates_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P03_view_state_redraw_flush.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P03_view_state_redraw_flush_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P04_scene_space_edge_paint_path.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P04_scene_space_edge_paint_path_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P05_visible_edge_snapshot_label_model.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P05_visible_edge_snapshot_label_model_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P06_viewport_aware_node_activation.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P06_viewport_aware_node_activation_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization_PROMPT.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability.md`
  - `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability_PROMPT.md`
- This packet is documentation-only. Do not change runtime code, tests, scripts, or checked-in perf evidence docs here.
