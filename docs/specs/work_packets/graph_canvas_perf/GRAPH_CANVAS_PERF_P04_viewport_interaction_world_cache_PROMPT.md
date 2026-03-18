Implement GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache.md exactly. Before editing, read GRAPH_CANVAS_PERF_MANIFEST.md, GRAPH_CANVAS_PERF_STATUS.md, and GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache.md. Implement only P04. Stay inside the packet write scope, preserve current canvas visuals and UI/UX contracts unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graph_canvas_perf/P04_viewport_interaction_world_cache_WRAPUP.md`, update GRAPH_CANVAS_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graph-canvas-perf/p04-viewport-interaction-world-cache`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k "graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_perf/P04_viewport_interaction_world_cache_WRAPUP.md`
- Keep the cache strategy viewport-only. Do not widen into docs work or new user-facing settings.
