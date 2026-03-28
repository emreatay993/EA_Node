Implement ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap.md exactly. Before editing, read ARCHITECTURE_MAINTAINABILITY_REFACTOR_MANIFEST.md, ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md, and ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, delete packet-owned internal compatibility seams only when the packet explicitly owns them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/architecture_maintainability_refactor/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-maintainability-refactor/p00-bootstrap`.
- Review Gate: run the exact `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_STATUS_PASS` inline Python command from `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_MANIFEST.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P01_graph_canvas_compat_retirement.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P01_graph_canvas_compat_retirement_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P02_bridge_source_contract_hardening.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P02_bridge_source_contract_hardening_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P03_shell_host_api_retirement.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P03_shell_host_api_retirement_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P04_project_session_authority_collapse.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P04_project_session_authority_collapse_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P05_session_envelope_metadata_cleanup.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P05_session_envelope_metadata_cleanup_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P06_graph_persistence_boundary_cleanup.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P06_graph_persistence_boundary_cleanup_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P07_graph_mutation_ops_split.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P07_graph_mutation_ops_split_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P08_node_sdk_surface_cleanup.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P08_node_sdk_surface_cleanup_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P09_runtime_protocol_compat_removal.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P09_runtime_protocol_compat_removal_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P10_viewer_session_backend_split.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P10_viewer_session_backend_split_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P11_graph_canvas_scene_decomposition.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P11_graph_canvas_scene_decomposition_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P12_geometry_theme_perf_cleanup.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P12_geometry_theme_perf_cleanup_PROMPT.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P13_verification_docs_traceability_closeout.md`
  - `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_P13_verification_docs_traceability_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep packet docs, future wrap-ups, and the future QA matrix trackable.
