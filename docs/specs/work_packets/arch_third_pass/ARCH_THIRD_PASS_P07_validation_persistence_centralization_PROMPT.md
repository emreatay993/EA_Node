Implement ARCH_THIRD_PASS_P07_validation_persistence_centralization.md exactly. Before editing, read ARCH_THIRD_PASS_MANIFEST.md, ARCH_THIRD_PASS_STATUS.md, and ARCH_THIRD_PASS_P07_validation_persistence_centralization.md. Implement only P07. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_third_pass/P07_validation_persistence_centralization_WRAPUP.md`, update ARCH_THIRD_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start P08.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-third-pass/p07-validation-persistence-centralization`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_registry_validation.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_third_pass/P07_validation_persistence_centralization_WRAPUP.md`
- Keep this packet on validation/normalization centralization. Do not introduce schema-version changes or new unknown-plugin behavior.
