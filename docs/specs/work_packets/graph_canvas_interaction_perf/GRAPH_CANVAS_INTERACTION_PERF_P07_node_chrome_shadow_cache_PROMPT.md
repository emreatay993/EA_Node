Implement GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache.md exactly. Before editing, read GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md, GRAPH_CANVAS_INTERACTION_PERF_STATUS.md, and GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache.md. Implement only P07. Stay inside the packet write scope, preserve locked defaults and current full-fidelity visuals unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update GRAPH_CANVAS_INTERACTION_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start P08.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Execution discipline:
- Prefer the narrowest packet-owned rerun during development and remediation; do not substitute broader repo-wide verification unless this packet explicitly requires it.
- Keep this packet on internal node chrome/shadow caching only. Do not introduce visible quality changes or broader canvas policy changes here.

Notes:
- Target branch: `codex/graph-canvas-interaction-perf/p07-node-chrome-shadow-cache`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "shadow or wheel_zoom" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_interaction_perf/P07_node_chrome_shadow_cache_WRAPUP.md`
