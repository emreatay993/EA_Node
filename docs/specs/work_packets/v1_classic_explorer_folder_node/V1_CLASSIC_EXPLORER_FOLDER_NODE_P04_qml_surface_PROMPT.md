Implement V1_CLASSIC_EXPLORER_FOLDER_NODE_P04_qml_surface.md exactly. Before editing, read V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md, V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md, and V1_CLASSIC_EXPLORER_FOLDER_NODE_P04_qml_surface.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

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
- Target branch: `codex/v1-classic-explorer-folder-node/p04-qml-surface`
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k folder_explorer --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md`
- Match the V1 Classic Explorer controls and route all filesystem work through P03 bridge actions.
