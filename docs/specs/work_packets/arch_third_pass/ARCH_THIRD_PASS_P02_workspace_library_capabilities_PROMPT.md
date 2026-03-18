Implement ARCH_THIRD_PASS_P02_workspace_library_capabilities.md exactly. Before editing, read ARCH_THIRD_PASS_MANIFEST.md, ARCH_THIRD_PASS_STATUS.md, and ARCH_THIRD_PASS_P02_workspace_library_capabilities.md. Implement only P02. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_third_pass/P02_workspace_library_capabilities_WRAPUP.md`, update ARCH_THIRD_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-third-pass/p02-workspace-library-capabilities`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_workspace_library_controller_unit -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_third_pass/P02_workspace_library_capabilities_WRAPUP.md`
- Keep this packet focused on capability ownership. Do not widen into bridge-first QML root cleanup or persistence-format work.
