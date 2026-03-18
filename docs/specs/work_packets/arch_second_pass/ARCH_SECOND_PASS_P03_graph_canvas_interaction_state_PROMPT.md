Implement ARCH_SECOND_PASS_P03_graph_canvas_interaction_state.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_P03_graph_canvas_interaction_state.md. Implement only P03. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_second_pass/P03_graph_canvas_interaction_state_WRAPUP.md`, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-second-pass/p03-graph-canvas-interaction-state`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellGraphCanvasHostTests -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_second_pass/P03_graph_canvas_interaction_state_WRAPUP.md`
- Keep the root GraphCanvas integration contract stable. This packet is about internal state/policy extraction, not API churn.
