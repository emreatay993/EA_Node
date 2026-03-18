Implement DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup.md exactly. Before editing, read DEAD_CODE_HYGIENE_MANIFEST.md, DEAD_CODE_HYGIENE_STATUS.md, and DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup.md. Implement only P01. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly removes an approved unread local plumbing seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/dead_code_hygiene/P01_qml_shell_plumbing_cleanup_WRAPUP.md`, update DEAD_CODE_HYGIENE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/dead-code-hygiene/p01-qml-shell-plumbing-cleanup`.
- Review Gate: `git diff --check -- ea_node_editor/ui_qml/MainShell.qml ea_node_editor/ui_qml/components/shell tests/test_main_window_shell.py`
- Expected artifacts:
  - `docs/specs/work_packets/dead_code_hygiene/P01_qml_shell_plumbing_cleanup_WRAPUP.md`
- Remove only the approved unread property plumbing and its exact call-site assignments.
- Keep `sceneBridgeRef`, `viewBridgeRef`, all global context-property names, and focused bridge object names stable.
- `overlayHostItem` is conditional: remove it only if you confirm there is no remaining runtime read after caller plumbing deletion; otherwise retain it and record the exact surviving read locations in the wrap-up and status ledger.
