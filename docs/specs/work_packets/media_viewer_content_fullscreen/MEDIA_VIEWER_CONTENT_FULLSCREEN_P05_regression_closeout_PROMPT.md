Implement MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md exactly. Before editing, read MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md, MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md, and MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md. Implement only P05. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start any later packet.

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
- Target branch: `codex/media-viewer-content-fullscreen/p05-regression-closeout`.
- Review Gate: `.\venv\Scripts\python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/media_viewer_content_fullscreen/P05_regression_closeout_WRAPUP.md`
  - `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md`
- Keep this packet to integrated regression coverage, requirement/traceability updates, QA evidence, and manual smoke directives. Do not add new runtime behavior that belongs in earlier packets.
