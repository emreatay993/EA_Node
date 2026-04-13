Implement TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_path_resolver_and_payload_contract.md exactly. Before editing, read TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md, TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md, and TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_path_resolver_and_payload_contract.md. Implement only P01. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

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
- Target branch: `codex/title-icons-for-non-passive-nodes/p01-path-resolver-and-payload-contract`.
- Review Gate: `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_sources.py -k title_icon --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/title_icons_for_non_passive_nodes/P01_path_resolver_and_payload_contract_WRAPUP.md`
  - `ea_node_editor/ui_qml/node_title_icon_sources.py`
  - `tests/test_node_title_icon_sources.py`
- Keep this packet Python payload/resolver only. Do not add QML rendering, settings UI, built-in asset migration, or project persistence changes.
