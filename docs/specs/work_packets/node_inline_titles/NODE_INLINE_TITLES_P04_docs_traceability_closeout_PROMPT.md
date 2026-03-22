Implement NODE_INLINE_TITLES_P04_docs_traceability_closeout.md exactly. Before editing, read NODE_INLINE_TITLES_MANIFEST.md, NODE_INLINE_TITLES_STATUS.md, and NODE_INLINE_TITLES_P04_docs_traceability_closeout.md. Implement only P04. Stay inside the packet write scope, preserve locked defaults and public graph-title/scope-entry contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update NODE_INLINE_TITLES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Execution discipline:
- Prefer the narrowest packet-owned rerun during development and remediation; do not substitute broader repo-wide verification unless this packet explicitly requires it.
- Keep this packet docs-only except for traceability-checker changes required to validate the new documentation mapping.

Notes:
- Target branch: `codex/node-inline-titles/p04-docs-traceability-closeout`
- Review Gate: `./venv/Scripts/python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/node_inline_titles/P04_docs_traceability_closeout_WRAPUP.md`
