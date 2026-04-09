Implement SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption.md exactly. Before editing, read SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md, SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md, and SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- If the wrap-up or status update lands in a follow-up docs commit, the recorded accepted SHA may still point to the earlier substantive packet commit as long as it remains reachable from the packet branch and the wrap-up `Changed Files` list reflects the full packet-branch diff.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/shared-graph-typography-control/p04-standard-node-chrome-typography-adoption`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_host_chrome --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/shared_graph_typography_control/P04_standard_node_chrome_typography_adoption_WRAPUP.md`
- Preserve the retained passive-authoritative font paths and the `PERSISTENT_NODE_ELAPSED_TIMES` footer semantics. This packet changes typography sources, not execution-timing behavior.
