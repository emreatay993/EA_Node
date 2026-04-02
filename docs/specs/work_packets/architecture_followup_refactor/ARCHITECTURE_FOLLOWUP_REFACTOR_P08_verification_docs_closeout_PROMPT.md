Implement ARCHITECTURE_FOLLOWUP_REFACTOR_P08_verification_docs_closeout.md exactly. Before editing, read ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md, ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md, and ARCHITECTURE_FOLLOWUP_REFACTOR_P08_verification_docs_closeout.md. Implement only P08. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P08.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/architecture_followup_refactor/P08_verification_docs_closeout_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-followup-refactor/p08-verification-docs-closeout`.
- Review Gate: `.\venv\Scripts\python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/architecture_followup_refactor/P08_verification_docs_closeout_WRAPUP.md`
  - `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md`
- This packet closes the set. Do not start any new packet or follow-on refactor plan here.
