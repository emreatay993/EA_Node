Implement COMMENT_BACKDROP_P08_docs_traceability_closeout.md exactly. Before editing, read COMMENT_BACKDROP_MANIFEST.md, COMMENT_BACKDROP_STATUS.md, and COMMENT_BACKDROP_P08_docs_traceability_closeout.md. Implement only P08. Stay inside the packet write scope, preserve locked defaults and public comment-backdrop, canvas, graph-surface-input, and shell contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COMMENT_BACKDROP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P08; do not start P09.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/comment-backdrop/p08-docs-traceability-closeout`
- Review Gate: `./venv/Scripts/python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/comment_backdrop/P08_docs_traceability_closeout_WRAPUP.md`
- Keep this packet docs-only. If a traceability check exposes a real code gap, document it and stop rather than sneaking runtime code into the closeout packet.
