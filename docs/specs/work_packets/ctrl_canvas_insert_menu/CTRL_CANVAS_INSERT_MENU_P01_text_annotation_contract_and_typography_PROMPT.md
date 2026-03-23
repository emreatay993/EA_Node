Implement CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography.md exactly. Before editing, read CTRL_CANVAS_INSERT_MENU_MANIFEST.md, CTRL_CANVAS_INSERT_MENU_STATUS.md, and CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography.md. Implement only P01. Stay inside the packet write scope, preserve locked defaults and public graph/shell/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/ctrl_canvas_insert_menu/P01_text_annotation_contract_and_typography_WRAPUP.md`, update CTRL_CANVAS_INSERT_MENU_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ctrl-canvas-insert-menu/p01-text-annotation-contract-and-typography`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_planning_annotation_catalog.py tests/test_passive_style_dialogs.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/P01_text_annotation_contract_and_typography_WRAPUP.md`
- This packet owns the text annotation contract, typography style schema, and minimal render surface only. Do not widen into Ctrl+double-click shell overlay work or inline auto-open editing.
