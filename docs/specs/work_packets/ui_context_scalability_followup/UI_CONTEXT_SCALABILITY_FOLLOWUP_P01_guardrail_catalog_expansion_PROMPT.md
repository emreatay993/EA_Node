Implement UI_CONTEXT_SCALABILITY_FOLLOWUP_P01_guardrail_catalog_expansion.md exactly. Before editing, read UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md, UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md, and UI_CONTEXT_SCALABILITY_FOLLOWUP_P01_guardrail_catalog_expansion.md. Implement only P01. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/ui_context_scalability_followup/P01_guardrail_catalog_expansion_WRAPUP.md`, update UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ui-context-scalability-followup/p01-guardrail-catalog-expansion`.
- Review Gate: `.\venv\Scripts\python.exe scripts/check_context_budgets.py`
- Expected artifacts:
  - `docs/specs/work_packets/ui_context_scalability_followup/P01_guardrail_catalog_expansion_WRAPUP.md`
  - `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json`
  - `scripts/check_context_budgets.py`
  - `scripts/run_verification.py`
- Freeze the current hotspot catalog here; do not begin source or regression splits in this packet.
