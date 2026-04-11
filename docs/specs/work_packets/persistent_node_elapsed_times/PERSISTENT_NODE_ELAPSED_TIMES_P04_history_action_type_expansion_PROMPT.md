Implement PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion.md exactly. Before editing, read PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md, PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md, and PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/persistent-node-elapsed-times/p04-history-action-type-expansion`.
- Review Gate: `.\venv\Scripts\python.exe -m pytest tests/graph_track_b/runtime_history.py -k persistent_node_elapsed_action_types --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/persistent_node_elapsed_times/P04_history_action_type_expansion_WRAPUP.md`
- This packet changes taxonomy only. Do not bolt on centralized elapsed-cache invalidation here; that belongs to `P05`.
- Keep execution-affecting property edits distinct from rename/title-only, node/edge style, edge-label, and port-label changes.

