Implement ARCH_SECOND_PASS_P07_persistence_workspace_ownership.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_P07_persistence_workspace_ownership.md. Implement only P07. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_second_pass/P07_persistence_workspace_ownership_WRAPUP.md`, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start P08.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-second-pass/p07-persistence-workspace-ownership`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_second_pass/P07_persistence_workspace_ownership_WRAPUP.md`
- Keep the packet focused on persistence/workspace ownership. Do not mix docs-refresh work into it.
