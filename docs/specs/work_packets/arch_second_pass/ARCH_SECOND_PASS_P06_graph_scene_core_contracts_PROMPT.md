Implement ARCH_SECOND_PASS_P06_graph_scene_core_contracts.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_P06_graph_scene_core_contracts.md. Implement only P06. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_second_pass/P06_graph_scene_core_contracts_WRAPUP.md`, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-second-pass/p06-graph-scene-core-contracts`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_second_pass/P06_graph_scene_core_contracts_WRAPUP.md`
- Keep the packet centered on graph-scene/core/subnode contracts. Do not widen into persistence or docs refresh work.
