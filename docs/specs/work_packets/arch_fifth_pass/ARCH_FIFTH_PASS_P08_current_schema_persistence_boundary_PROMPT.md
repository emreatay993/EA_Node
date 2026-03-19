Implement ARCH_FIFTH_PASS_P08_current_schema_persistence_boundary.md exactly. Before editing, read ARCH_FIFTH_PASS_MANIFEST.md, ARCH_FIFTH_PASS_STATUS.md, and ARCH_FIFTH_PASS_P08_current_schema_persistence_boundary.md. Implement only P08. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, and performance, preserve current-schema `.sfe` behavior while treating pre-current-schema compatibility exactly as the packet specifies, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the packet wrap-up, update ARCH_FIFTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P08; do not start P09.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fifth-pass/p08-current-schema-persistence-boundary`
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fifth_pass/P08_current_schema_persistence_boundary_WRAPUP.md`
- Current-schema `.sfe` behavior must remain exact. This packet is allowed to drop pre-current-schema support where it simplifies the boundary.
