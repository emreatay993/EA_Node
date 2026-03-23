Implement CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell.md exactly. Before editing, read CTRL_CANVAS_INSERT_MENU_MANIFEST.md, CTRL_CANVAS_INSERT_MENU_STATUS.md, and CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell.md. Implement only P02. Stay inside the packet write scope, preserve locked defaults and public graph/shell/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/ctrl_canvas_insert_menu/P02_ctrl_canvas_insert_menu_shell_WRAPUP.md`, update CTRL_CANVAS_INSERT_MENU_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ctrl-canvas-insert-menu/p02-ctrl-canvas-insert-menu-shell`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/P02_ctrl_canvas_insert_menu_shell_WRAPUP.md`
- This packet owns the shell/menu/gesture path plus the stylus placeholder only. Do not widen into inline text-editor auto-open behavior; `P03` owns that workflow.
