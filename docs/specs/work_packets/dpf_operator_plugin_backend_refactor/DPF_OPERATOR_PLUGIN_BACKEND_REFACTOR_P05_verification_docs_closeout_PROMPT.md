Implement DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P05_verification_docs_closeout.md exactly. Before editing, read DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_MANIFEST.md, DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md, and DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_P05_verification_docs_closeout.md. Implement only P05. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start P06.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P05_verification_docs_closeout_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/dpf-operator-plugin-backend-refactor/p05-verification-docs-closeout`.
- Review Gate: `.\venv\Scripts\python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P05_verification_docs_closeout_WRAPUP.md`
  - `docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md`
- Do not reopen runtime or node behavior in this packet. Keep it to QA evidence, traceability, and documented backend-contract closeout.
