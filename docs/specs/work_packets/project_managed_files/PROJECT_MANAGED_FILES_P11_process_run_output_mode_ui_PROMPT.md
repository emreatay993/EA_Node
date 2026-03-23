Implement PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui.md exactly. Before editing, read PROJECT_MANAGED_FILES_MANIFEST.md, PROJECT_MANAGED_FILES_STATUS.md, and PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui.md. Implement only P11. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PROJECT_MANAGED_FILES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P11; do not start P12.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/project-managed-files/p11-process-run-output-mode-ui`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_graph_output_mode_ui.py --ignore=venv -q`
- Expected artifacts:
  - `tests/test_graph_output_mode_ui.py`
  - `docs/specs/work_packets/project_managed_files/P11_process_run_output_mode_ui_WRAPUP.md`
- Keep this packet on the first concrete heavy-output adopter only. Do not generalize the quick-toggle surface beyond Process Run in this packet.
