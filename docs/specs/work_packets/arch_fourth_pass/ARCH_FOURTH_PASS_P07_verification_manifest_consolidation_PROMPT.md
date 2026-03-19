Implement ARCH_FOURTH_PASS_P07_verification_manifest_consolidation.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P07_verification_manifest_consolidation.md. Implement only P07. Stay inside the packet write scope, preserve developer-facing verification entry points unless the packet explicitly adds a compatibility layer, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_fourth_pass/P07_verification_manifest_consolidation_WRAPUP.md`, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start P08.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fourth-pass/p07-verification-manifest-consolidation`
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fourth_pass/P07_verification_manifest_consolidation_WRAPUP.md`
- Keep this packet focused on canonical verification facts and packet-owned traceability logic, not broader architecture doc closeout.
