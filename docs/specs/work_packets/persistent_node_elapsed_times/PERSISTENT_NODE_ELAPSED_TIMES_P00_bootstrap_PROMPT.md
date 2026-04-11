Implement PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md exactly. Before editing, read PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md, PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md, and PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/persistent_node_elapsed_times/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/persistent-node-elapsed-times/p00-bootstrap` from `main`.
- Review Gate: run the exact `PERSISTENT_NODE_ELAPSED_TIMES_P00_STATUS_PASS` inline Python command from `PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P01_worker_timing_protocol_projection.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P01_worker_timing_protocol_projection_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P05_timing_cache_invalidation_hooks.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P05_timing_cache_invalidation_hooks_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P06_node_footer_persistent_elapsed_rendering.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P06_node_footer_persistent_elapsed_rendering_PROMPT.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P07_verification_docs_traceability_closeout.md`
  - `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_P07_verification_docs_traceability_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work. Do not edit runtime, shell, bridge, QML, or requirement files in `P00`.
