Implement ARCH_FIFTH_PASS_P05_bridge_first_qml_migration.md exactly. Before editing, read ARCH_FIFTH_PASS_MANIFEST.md, ARCH_FIFTH_PASS_STATUS.md, and ARCH_FIFTH_PASS_P05_bridge_first_qml_migration.md. Implement only P05. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, and performance, preserve current-schema `.sfe` behavior while treating pre-current-schema compatibility exactly as the packet specifies, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the packet wrap-up, update ARCH_FIFTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start P06.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fifth-pass/p05-bridge-first-qml-migration`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -q -k "GraphCanvasBridgeTests or MainWindowShellContextBootstrapTests"`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fifth_pass/P05_bridge_first_qml_migration_WRAPUP.md`
- Preserve exact shell/canvas behavior and performance. This packet removes compatibility globals only after all packet-owned QML consumers are migrated.
