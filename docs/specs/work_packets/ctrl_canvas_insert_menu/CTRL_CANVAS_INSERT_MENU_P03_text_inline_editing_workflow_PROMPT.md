Implement CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow.md exactly. Before editing, read CTRL_CANVAS_INSERT_MENU_MANIFEST.md, CTRL_CANVAS_INSERT_MENU_STATUS.md, and CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow.md. Implement only P03. Stay inside the packet write scope, preserve locked defaults and public graph/shell/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/ctrl_canvas_insert_menu/P03_text_inline_editing_workflow_WRAPUP.md`, update CTRL_CANVAS_INSERT_MENU_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ctrl-canvas-insert-menu/p03-text-inline-editing-workflow`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_inline.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/P03_text_inline_editing_workflow_WRAPUP.md`
- This packet owns auto-open inline editing, body double-click reopen, and inspector/inline sync only. Do not reopen the shell overlay contract or passive text node schema beyond the pending-surface-action hook it needs.
