Implement DEAD_CODE_HYGIENE_P00_bootstrap.md exactly. Before editing, read DEAD_CODE_HYGIENE_MANIFEST.md, DEAD_CODE_HYGIENE_STATUS.md, and DEAD_CODE_HYGIENE_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve current runtime/test behavior because this packet is documentation-only, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update DEAD_CODE_HYGIENE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/dead_code_hygiene/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/dead-code-hygiene/p00-bootstrap`.
- Review Gate: run the exact `DEAD_CODE_HYGIENE_P00_STATUS_PASS` inline Python command from `DEAD_CODE_HYGIENE_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_MANIFEST.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P00_bootstrap.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup_PROMPT.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup_PROMPT.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P03_regression_locks.md`
  - `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P03_regression_locks_PROMPT.md`
- This packet is documentation-only bootstrap work.
- Add only the narrow `.gitignore` exception required for this packet directory.
- Preserve the existing dirty `graph_canvas_perf` docs/index work and do not restage or revert unrelated changes.
