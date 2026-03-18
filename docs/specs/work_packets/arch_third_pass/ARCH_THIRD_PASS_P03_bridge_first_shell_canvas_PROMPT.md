Implement ARCH_THIRD_PASS_P03_bridge_first_shell_canvas.md exactly. Before editing, read ARCH_THIRD_PASS_MANIFEST.md, ARCH_THIRD_PASS_STATUS.md, and ARCH_THIRD_PASS_P03_bridge_first_shell_canvas.md. Implement only P03. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_third_pass/P03_bridge_first_shell_canvas_WRAPUP.md`, update ARCH_THIRD_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-third-pass/p03-bridge-first-shell-canvas`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_third_pass/P03_bridge_first_shell_canvas_WRAPUP.md`
- Keep this packet on bridge-first root QML migration. Do not widen into `GraphSceneBridge` internals or passive media cleanup.
