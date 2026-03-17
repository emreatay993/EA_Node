Implement VERIFICATION_SPEED_P04_gui_wait_helper_cleanup.md exactly. Before editing, read VERIFICATION_SPEED_MANIFEST.md, VERIFICATION_SPEED_STATUS.md, and VERIFICATION_SPEED_P04_gui_wait_helper_cleanup.md. Implement only P04. Stay inside the packet write scope, preserve the current shell-isolation defaults unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/verification_speed/P04_gui_wait_helper_cleanup_WRAPUP.md`, update VERIFICATION_SPEED_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/verification-speed/p04-gui-wait-helper-cleanup`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellViewLibraryInspectorTests.test_qml_side_panes_share_collapsible_shell_behavior -v`
- Expected artifacts:
  - `docs/specs/work_packets/verification_speed/P04_gui_wait_helper_cleanup_WRAPUP.md`
- Keep all changes test-only.
- Do not widen into runner scripting, marker rollout, or product-code performance changes.
