Implement COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_bootstrap.md exactly. Before editing, read COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MANIFEST.md, COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md, and COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve current user-visible behavior and locked defaults, create or repair only the packet bootstrap artifacts, update COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md so P00 is PASS and later packets are PENDING, and stop after P00; do not start P01.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Bootstrap closeout requirements:
- Confirm the manifest, status ledger, all packet specs, and all packet prompts exist.
- Confirm the manifest has `Execution Waves`.
- Confirm `docs/specs/INDEX.md` registers the manifest and status ledger.
- Do not create an implementation wrap-up for P00 unless the executor explicitly requests one.
- Stop after bootstrap.

Notes:
- Target branch: `codex/corex-no-legacy-architecture-cleanup/p00-bootstrap`.
- Review Gate: `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_STATUS_PASS`
- Expected artifacts:
  - `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MANIFEST.md`
  - `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md`
