Implement DEAD_CODE_HYGIENE_P03_regression_locks.md exactly. Before editing, read DEAD_CODE_HYGIENE_MANIFEST.md, DEAD_CODE_HYGIENE_STATUS.md, and DEAD_CODE_HYGIENE_P03_regression_locks.md. Implement only P03. Stay inside the packet write scope, preserve the intentionally retained compatibility seams while tightening only the approved regression locks, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/dead_code_hygiene/P03_regression_locks_WRAPUP.md`, update DEAD_CODE_HYGIENE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/dead-code-hygiene/p03-regression-locks`.
- Review Gate: `git diff --check -- tests/test_main_window_shell.py tests/test_dead_code_hygiene.py`
- Expected artifacts:
  - `docs/specs/work_packets/dead_code_hygiene/P03_regression_locks_WRAPUP.md`
- Prefer extending `tests/test_main_window_shell.py` for the QML boundary; add `tests/test_dead_code_hygiene.py` only if the helper-absence assertions do not fit cleanly there.
- Rerun the full `P01` and `P02` verification slices before marking the packet done.
- Record intentionally retained compatibility seams and broader out-of-scope unused-tooling findings in the wrap-up and status ledger instead of widening the cleanup.
