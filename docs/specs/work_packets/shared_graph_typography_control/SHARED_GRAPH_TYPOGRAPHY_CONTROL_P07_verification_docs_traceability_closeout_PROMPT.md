Implement SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout.md exactly. Before editing, read SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md, SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md, and SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout.md. Implement only P07. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start any later packet.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- If the wrap-up or status update lands in a follow-up docs commit, the recorded accepted SHA may still point to the earlier substantive packet commit as long as it remains reachable from the packet branch and the wrap-up `Changed Files` list reflects the full packet-branch diff.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/shared-graph-typography-control/p07-verification-docs-traceability-closeout`.
- Review Gate: `.\venv\Scripts\python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/INDEX.md`
  - `docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md`
  - `docs/specs/requirements/20_UI_UX.md`
  - `docs/specs/requirements/80_PERFORMANCE.md`
  - `docs/specs/requirements/90_QA_ACCEPTANCE.md`
  - `docs/specs/requirements/TRACEABILITY_MATRIX.md`
  - `tests/test_traceability_checker.py`
  - `docs/specs/work_packets/shared_graph_typography_control/P07_verification_docs_traceability_closeout_WRAPUP.md`
- Keep the closeout aligned with the locked defaults and the retained `PERSISTENT_NODE_ELAPSED_TIMES` precedent for elapsed-footer typography. Do not reopen worker timing, cache invalidation, or graph-theme schema scope here.
