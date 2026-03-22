Implement PORT_LABEL_VISIBILITY_P03_standard_node_width_policy.md exactly. Before editing, read PORT_LABEL_VISIBILITY_MANIFEST.md, PORT_LABEL_VISIBILITY_STATUS.md, and PORT_LABEL_VISIBILITY_P03_standard_node_width_policy.md. Implement only P03. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node-surface contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PORT_LABEL_VISIBILITY_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/port-label-visibility/p03-standard-node-width-policy`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/port_label_visibility/P03_standard_node_width_policy_WRAPUP.md`
- Keep this packet in the scene metric and mutation layer. Do not start the QML tooltip or inline-visibility rollout here.
