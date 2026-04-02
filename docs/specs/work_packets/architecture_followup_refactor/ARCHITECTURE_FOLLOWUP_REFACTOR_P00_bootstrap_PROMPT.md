Implement ARCHITECTURE_FOLLOWUP_REFACTOR_P00_bootstrap.md exactly. Before editing, read ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md, ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md, and ARCHITECTURE_FOLLOWUP_REFACTOR_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done, create or update the packet docs exactly as required, update ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, and stop after P00; do not start P01.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-followup-refactor/p00-bootstrap`.
- Review Gate: `@'... ARCHITECTURE_FOLLOWUP_REFACTOR_P00_STATUS_PASS ...'@ | .\venv\Scripts\python.exe -`
- Expected artifacts include the review baseline doc, spec-index update, manifest, status ledger, and packet specs or prompts for `P00` through `P08`.
- Stop after the bootstrap packet; do not implement any later packet here.
