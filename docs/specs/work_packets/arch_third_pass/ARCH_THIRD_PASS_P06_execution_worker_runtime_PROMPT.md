Implement ARCH_THIRD_PASS_P06_execution_worker_runtime.md exactly. Before editing, read ARCH_THIRD_PASS_MANIFEST.md, ARCH_THIRD_PASS_STATUS.md, and ARCH_THIRD_PASS_P06_execution_worker_runtime.md. Implement only P06. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_third_pass/P06_execution_worker_runtime_WRAPUP.md`, update ARCH_THIRD_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-third-pass/p06-execution-worker-runtime`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_execution_worker.py tests/test_execution_client.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_third_pass/P06_execution_worker_runtime_WRAPUP.md`
- Keep this packet on runtime-worker seams and `REQ-NODE-011`. Do not widen into persistence centralization or shell/QML changes.
