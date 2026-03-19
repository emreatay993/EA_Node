Implement ARCH_FOURTH_PASS_P04_execution_runtime_dto_pipeline.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P04_execution_runtime_dto_pipeline.md. Implement only P04. Stay inside the packet write scope, preserve queue-boundary payload compatibility unless the packet explicitly updates a typed adapter, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_fourth_pass/P04_execution_runtime_dto_pipeline_WRAPUP.md`, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fourth-pass/p04-execution-runtime-dto-pipeline`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker tests.test_execution_client -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fourth_pass/P04_execution_runtime_dto_pipeline_WRAPUP.md`
- Keep this packet focused on typed runtime boundaries and worker/compiler decomposition, not shell presenter or QML bridge cleanup.
