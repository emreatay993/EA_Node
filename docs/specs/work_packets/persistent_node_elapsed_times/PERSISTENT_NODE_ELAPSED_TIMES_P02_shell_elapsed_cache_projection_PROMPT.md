Implement PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection.md exactly. Before editing, read PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md, PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md, and PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/persistent-node-elapsed-times/p02-shell-elapsed-cache-projection`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/persistent_node_elapsed_times/P02_shell_elapsed_cache_projection_WRAPUP.md`
- Keep cached elapsed data separate from `running_node_ids`, `completed_node_ids`, and execution-edge progress state.
- Preserve shell fallback timing when `started_at_epoch_ms` or `elapsed_ms` is absent.
- `run_started` must clear transient live state without clearing cached elapsed values for an unchanged workspace.
- Clear cached elapsed timing data on project/session replacement paths such as `_install_project()`; later packets should not need to bolt that behavior on after the fact.
