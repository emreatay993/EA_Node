Implement ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption.md exactly. Before editing, read ARCHITECTURE_REFACTOR_MANIFEST.md, ARCHITECTURE_REFACTOR_STATUS.md, and ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption.md. Implement only P06. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ARCHITECTURE_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-refactor/p06-persistence-invariant-adoption`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_persistence_package_imports.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/architecture_refactor/P06_persistence_invariant_adoption_WRAPUP.md`
- Keep `.sfe` format and published persistence semantics stable while making persistence adopt the shared invariant authority and making persistence-envelope versus document-flavor contracts explicit.
