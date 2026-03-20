Implement ARCH_SIXTH_PASS_P02_shell_window_facade_contraction.md exactly. Before editing, read ARCH_SIXTH_PASS_MANIFEST.md, ARCH_SIXTH_PASS_STATUS.md, and ARCH_SIXTH_PASS_P02_shell_window_facade_contraction.md. Implement only P02. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, runtime semantics, and current-schema `.sfe` behavior, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the packet wrap-up, update ARCH_SIXTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-sixth-pass/p02-shell-window-facade-contraction`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -q -k "MainWindowShellTelemetryTests or MainWindowShellHostProtocolStateTests"`
- Expected artifacts:
  - `docs/specs/work_packets/arch_sixth_pass/P02_shell_window_facade_contraction_WRAPUP.md`
- Keep this packet focused on facade contraction. `P03` owns contract hardening after the shell host surface is smaller.
