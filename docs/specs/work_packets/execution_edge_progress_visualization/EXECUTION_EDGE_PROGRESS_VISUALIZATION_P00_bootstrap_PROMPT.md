Implement EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap.md exactly. Before editing, read EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md, EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md, and EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/execution_edge_progress_visualization/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/execution-edge-progress-visualization/p00-bootstrap` from `main`.
- Review Gate: run the exact `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_STATUS_PASS` inline Python command from `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P01_run_state_edge_progress_projection.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P01_run_state_edge_progress_projection_PROMPT.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P02_graph_canvas_execution_edge_bindings.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P02_graph_canvas_execution_edge_bindings_PROMPT.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P03_execution_edge_snapshot_metadata.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P03_execution_edge_snapshot_metadata_PROMPT.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P04_execution_edge_renderer_highlights.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P04_execution_edge_renderer_highlights_PROMPT.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P05_verification_docs_traceability_closeout.md`
  - `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_P05_verification_docs_traceability_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep packet docs and future wrap-ups trackable while reusing the retained `NODE_EXECUTION_VISUALIZATION` QA matrix home.
