Implement ARCH_FOURTH_PASS_P01_unknown_plugin_preservation.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P01_unknown_plugin_preservation.md. Implement only P01. Stay inside the packet write scope, preserve document shape unless the packet explicitly proves a change is unavoidable, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fourth-pass/p01-unknown-plugin-preservation`
- Review Gate: `./venv/Scripts/python.exe -m unittest tests.test_serializer -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`
- Keep this packet focused on lossless unresolved-plugin preservation, not shell/UI affordances or worker/runtime decomposition.
