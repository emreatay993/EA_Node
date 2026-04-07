Implement EXECUTION_EDGE_PROGRESS_VISUALIZATION_P02_graph_canvas_execution_edge_bindings.md exactly. Before editing, read EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md, EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md, and EXECUTION_EDGE_PROGRESS_VISUALIZATION_P02_graph_canvas_execution_edge_bindings.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/execution-edge-progress-visualization/p02-graph-canvas-execution-edge-bindings`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k execution_edge_progress_canvas --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/execution_edge_progress_visualization/P02_graph_canvas_execution_edge_bindings_WRAPUP.md`
- Keep `progressed_execution_edge_lookup`, `progressedExecutionEdgeLookup`, and `nodeExecutionRevision` stable; later packets will consume those exact names.
- Do not add edge-layer snapshot metadata, draw logic, or docs closeout work in this packet.
