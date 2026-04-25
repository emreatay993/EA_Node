Implement COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P06_current_schema_persistence_cleanup.md exactly. Before editing, read COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MANIFEST.md, COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md, and COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P06_current_schema_persistence_cleanup.md. Implement only P06. Stay inside the packet write scope, preserve current user-visible behavior and locked defaults, delete packet-owned internal compatibility seams instead of leaving fallback paths behind, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/corex-no-legacy-architecture-cleanup/p06-current-schema-persistence-cleanup`.
- Review Gate: run the `Review Gate` command from the packet spec exactly.
- Expected artifacts:
  - `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P06_current_schema_persistence_cleanup_WRAPUP.md`
