Implement EXECUTION_EDGE_PROGRESS_VISUALIZATION_P04_execution_edge_renderer_highlights.md exactly. Before editing, read EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md, EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md, and EXECUTION_EDGE_PROGRESS_VISUALIZATION_P04_execution_edge_renderer_highlights.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/execution-edge-progress-visualization/p04-execution-edge-renderer-highlights`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k execution_edge_progress_visualization --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/execution_edge_progress_visualization/P04_execution_edge_renderer_highlights_WRAPUP.md`
- Consume the packet-owned snapshot fields from `P03` as-is; do not invent a second renderer-only execution state path.
- Preserve the non-dimming rule for selected and previewed execution edges while allowing the flash overlay to layer on top.
