Implement PROJECT_MANAGED_FILES_P03_staging_recovery_lifecycle.md exactly. Before editing, read PROJECT_MANAGED_FILES_MANIFEST.md, PROJECT_MANAGED_FILES_STATUS.md, and PROJECT_MANAGED_FILES_P03_staging_recovery_lifecycle.md. Implement only P03. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PROJECT_MANAGED_FILES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/project-managed-files/p03-staging-recovery-lifecycle`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_project_session_controller.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/project_managed_files/P03_staging_recovery_lifecycle_WRAPUP.md`
- Keep this packet focused on staging roots, autosave/session recovery, and clean-close discard behavior. Do not add save promotion, Save As, or node-level issue UI here.
