Implement ARCH_FOURTH_PASS_P06_bridge_first_qml_contract_cleanup.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P06_bridge_first_qml_contract_cleanup.md. Implement only P06. Stay inside the packet write scope, preserve public QML object names and stable bridge contracts unless the packet explicitly introduces a verified replacement path, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fourth-pass/p06-bridge-first-qml-contract-cleanup`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`
- Keep this packet focused on packet-owned QML contracts and cross-package helper direction, not verification manifest work.
