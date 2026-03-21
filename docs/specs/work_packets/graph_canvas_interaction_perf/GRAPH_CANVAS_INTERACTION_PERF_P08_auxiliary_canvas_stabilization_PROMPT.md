Implement GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization.md exactly. Before editing, read GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md, GRAPH_CANVAS_INTERACTION_PERF_STATUS.md, and GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization.md. Implement only P08. Stay inside the packet write scope, preserve locked defaults and current full-fidelity visuals unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update GRAPH_CANVAS_INTERACTION_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P08; do not start P09.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Execution discipline:
- Prefer the narrowest packet-owned rerun during development and remediation; do not substitute broader repo-wide verification unless this packet explicitly requires it.
- Keep this packet on auxiliary canvas hot paths only, including the requirement that repeated center changes move only the minimap viewport rect and do not rebuild minimap node geometry. Do not refresh checked-in perf docs or traceability here.

Notes:
- Target branch: `codex/graph-canvas-interaction-perf/p08-auxiliary-canvas-stabilization`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "minimap" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_interaction_perf/P08_auxiliary_canvas_stabilization_WRAPUP.md`
