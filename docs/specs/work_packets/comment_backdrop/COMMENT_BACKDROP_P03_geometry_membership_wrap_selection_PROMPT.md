Implement COMMENT_BACKDROP_P03_geometry_membership_wrap_selection.md exactly. Before editing, read COMMENT_BACKDROP_MANIFEST.md, COMMENT_BACKDROP_STATUS.md, and COMMENT_BACKDROP_P03_geometry_membership_wrap_selection.md. Implement only P03. Stay inside the packet write scope, preserve locked defaults and public comment-backdrop, canvas, graph-surface-input, and shell contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COMMENT_BACKDROP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/comment-backdrop/p03-geometry-membership-wrap-selection`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_membership.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/comment_backdrop/P03_geometry_membership_wrap_selection_WRAPUP.md`
- Keep ownership derived-only. Do not add persisted member ids or packet-owned shadow metadata to project files.
