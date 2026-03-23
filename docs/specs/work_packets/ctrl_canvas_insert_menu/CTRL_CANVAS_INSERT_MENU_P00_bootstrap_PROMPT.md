Implement CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md exactly. Before editing, read CTRL_CANVAS_INSERT_MENU_MANIFEST.md, CTRL_CANVAS_INSERT_MENU_STATUS.md, and CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve locked defaults and public graph/shell/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update CTRL_CANVAS_INSERT_MENU_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/ctrl_canvas_insert_menu/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ctrl-canvas-insert-menu/p00-bootstrap`.
- Review Gate: run the exact `CTRL_CANVAS_INSERT_MENU_P00_STATUS_PASS` inline Python command from `CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_MANIFEST.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography_PROMPT.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell_PROMPT.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow_PROMPT.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability.md`
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist update needed to keep the packet docs trackable.
