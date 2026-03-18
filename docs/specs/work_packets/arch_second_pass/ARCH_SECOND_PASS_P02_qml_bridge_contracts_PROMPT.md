Implement ARCH_SECOND_PASS_P02_qml_bridge_contracts.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_P02_qml_bridge_contracts.md. Implement only P02. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_second_pass/P02_qml_bridge_contracts_WRAPUP.md`, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-second-pass/p02-qml-bridge-contracts`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.GraphCanvasBridgeTests tests.test_main_window_shell.ShellLibraryBridgeTests tests.test_main_window_shell.ShellWorkspaceBridgeTests tests.test_main_window_shell.ShellInspectorBridgeTests -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_second_pass/P02_qml_bridge_contracts_WRAPUP.md`
- Do not widen into deep GraphCanvas state extraction or GraphNodeHost work.
