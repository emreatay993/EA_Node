Implement ARCH_THIRD_PASS_P04_scene_mutation_contracts.md exactly. Before editing, read ARCH_THIRD_PASS_MANIFEST.md, ARCH_THIRD_PASS_STATUS.md, and ARCH_THIRD_PASS_P04_scene_mutation_contracts.md. Implement only P04. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_third_pass/P04_scene_mutation_contracts_WRAPUP.md`, update ARCH_THIRD_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-third-pass/p04-scene-mutation-contracts`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_third_pass/P04_scene_mutation_contracts_WRAPUP.md`
- Keep this packet on internal scene-service contracts. Do not widen into passive media-surface cleanup or execution-runtime refactors.
