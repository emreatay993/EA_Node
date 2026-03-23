Implement CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability.md exactly. Before editing, read CTRL_CANVAS_INSERT_MENU_MANIFEST.md, CTRL_CANVAS_INSERT_MENU_STATUS.md, and CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability.md. Implement only P04. Stay inside the packet write scope, preserve locked defaults and public graph/shell/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/ctrl_canvas_insert_menu/P04_regression_docs_traceability_WRAPUP.md`, update CTRL_CANVAS_INSERT_MENU_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ctrl-canvas-insert-menu/p04-regression-docs-traceability`.
- Review Gate: `./venv/Scripts/python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/ctrl_canvas_insert_menu/P04_regression_docs_traceability_WRAPUP.md`
  - `docs/specs/requirements/20_UI_UX.md`
  - `docs/specs/requirements/30_GRAPH_MODEL.md`
  - `docs/specs/requirements/40_NODE_SDK.md`
  - `docs/specs/requirements/60_PERSISTENCE.md`
  - `docs/specs/requirements/90_QA_ACCEPTANCE.md`
  - `docs/specs/requirements/TRACEABILITY_MATRIX.md`
  - `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`
  - `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`
- This packet is the final docs and regression close-out. Keep it aligned with the actual behavior landed in `P01` through `P03`; do not invent scope that earlier packets did not ship.
