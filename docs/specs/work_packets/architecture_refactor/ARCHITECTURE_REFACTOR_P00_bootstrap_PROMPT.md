Implement ARCHITECTURE_REFACTOR_P00_bootstrap.md exactly. Before editing, read ARCHITECTURE_REFACTOR_MANIFEST.md, ARCHITECTURE_REFACTOR_STATUS.md, and ARCHITECTURE_REFACTOR_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update ARCHITECTURE_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/architecture_refactor/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-refactor/p00-bootstrap`.
- Review Gate: run the exact `ARCHITECTURE_REFACTOR_P00_STATUS_PASS` inline Python command from `ARCHITECTURE_REFACTOR_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_MANIFEST.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P00_bootstrap.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P01_shell_host_composition.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P01_shell_host_composition_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P02_workspace_library_surface.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P02_workspace_library_surface_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P03_project_session_service.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P03_project_session_service_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P04_graph_boundary_adapters.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P04_graph_boundary_adapters_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P05_graph_invariant_kernel.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P05_graph_invariant_kernel_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P07_runtime_snapshot_context.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P07_runtime_snapshot_context_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P08_worker_protocol_split.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P08_worker_protocol_split_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P09_dpf_runtime_package.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P09_dpf_runtime_package_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P10_dpf_node_viewer_split.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P10_dpf_node_viewer_split_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P11_shell_qml_bridge_retirement.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P11_shell_qml_bridge_retirement_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P12_graph_canvas_scene_decomposition.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P12_graph_canvas_scene_decomposition_PROMPT.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P13_docs_release_traceability.md`
  - `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P13_docs_release_traceability_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep packet docs, future wrap-ups, and the future QA matrix trackable.
