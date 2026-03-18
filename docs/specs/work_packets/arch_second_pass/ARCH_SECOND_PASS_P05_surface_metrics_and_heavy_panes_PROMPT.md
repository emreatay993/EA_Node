Implement ARCH_SECOND_PASS_P05_surface_metrics_and_heavy_panes.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_P05_surface_metrics_and_heavy_panes.md. Implement only P05. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_second_pass/P05_surface_metrics_and_heavy_panes_WRAPUP.md`, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start P06.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-second-pass/p05-surface-metrics-and-heavy-panes`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_inspector_reflection tests.test_passive_image_nodes -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_second_pass/P05_surface_metrics_and_heavy_panes_WRAPUP.md`
- Keep the packet centered on metrics ownership and heavy-pane decomposition. Do not widen into graph-scene core refactors.
