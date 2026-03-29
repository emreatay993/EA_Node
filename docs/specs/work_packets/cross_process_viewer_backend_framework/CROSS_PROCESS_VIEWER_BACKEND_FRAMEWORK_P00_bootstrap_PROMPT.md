Implement CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md exactly. Before editing, read CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md, CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md, and CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/cross_process_viewer_backend_framework/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/cross-process-viewer-backend-framework/p00-bootstrap` from `main`.
- Review Gate: run the exact `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_STATUS_PASS` inline Python command from `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract_PROMPT.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization_PROMPT.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework_PROMPT.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption_PROMPT.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states_PROMPT.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout.md`
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep packet docs, future wrap-ups, and the future QA matrix trackable.
