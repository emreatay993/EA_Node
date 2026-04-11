Implement PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings.md exactly. Before editing, read PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md, PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md, and PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings.md. Implement only P03. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/persistent-node-elapsed-times/p03-graph-canvas-elapsed-bindings`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py -k persistent_node_elapsed_canvas --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/persistent_node_elapsed_times/P03_graph_canvas_elapsed_bindings_WRAPUP.md`
- Reuse the existing `node_execution_state_changed` plus `node_execution_revision` path; do not add a second timing-specific signal or revision counter.
- Keep the bridge property names fixed as `running_node_started_at_ms_lookup` and `node_elapsed_ms_lookup`.
- Keep `GraphNodeHost.qml` entirely out of `P03`; footer rendering belongs to `P06`.
