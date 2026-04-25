Implement COMMENT_FLOATING_POPOVER_P03_tests_and_verification.md exactly. Before editing, read COMMENT_FLOATING_POPOVER_MANIFEST.md, COMMENT_FLOATING_POPOVER_STATUS.md, and COMMENT_FLOATING_POPOVER_P03_tests_and_verification.md. Implement only P03. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COMMENT_FLOATING_POPOVER_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start any follow-up packet.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Worker requirement:
- Use `gpt-5.5` with `xhigh` reasoning for this implementation packet.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- If the wrap-up or status update lands in a follow-up docs commit, the recorded accepted SHA may still point to the earlier substantive packet commit as long as it remains reachable from the packet branch and the wrap-up `Changed Files` list reflects the full packet-branch diff.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/comment-floating-popover/p03-tests-and-verification`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py -k "popover or peek_inside or inline_body_commit" --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/comment_floating_popover/P03_tests_and_verification_WRAPUP.md`
  - `tests/main_window_shell/comment_backdrop_workflows.py`
  - `tests/test_main_window_shell.py`
  - `tests/test_comment_backdrop_layer.py`
  - `tests/test_comment_backdrop_contracts.py`
  - `tests/test_serializer.py`
  - `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
  - `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- Keep this packet focused on final regressions and packet-scoped fixes. Do not add persistence, preferences, or behavior for non-comment nodes.
