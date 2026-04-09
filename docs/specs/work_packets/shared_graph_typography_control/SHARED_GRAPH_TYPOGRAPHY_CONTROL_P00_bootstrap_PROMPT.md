Implement SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md exactly. Before editing, read SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md, SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md, and SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/shared_graph_typography_control/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- If the wrap-up or status update lands in a follow-up docs commit, the recorded accepted SHA may still point to the earlier substantive packet commit as long as it remains reachable from the packet branch and the wrap-up `Changed Files` list reflects the full packet-branch diff.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/shared-graph-typography-control/p00-bootstrap` from `main`.
- Review Gate: run the exact `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_STATUS_PASS` inline Python command from `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_preferences_typography_schema_normalization.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_preferences_typography_schema_normalization_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_shell_typography_projection.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_shell_typography_projection_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_canvas_typography_contract_and_metrics.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_canvas_typography_contract_and_metrics_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_inline_and_edge_typography_adoption.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_inline_and_edge_typography_adoption_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_graphics_settings_typography_control.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_graphics_settings_typography_control_PROMPT.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout.md`
  - `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work. Do not edit runtime, shell, bridge, QML, perf, or requirement files in `P00`.
