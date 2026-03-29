Implement CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states.md exactly. Before editing, read CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md, CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md, and CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states.md. Implement only P05. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start P06.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/cross-process-viewer-backend-framework/p05-bridge-projection-run-required-states` from `main`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/P05_bridge_projection_run_required_states_WRAPUP.md`
  - `ea_node_editor/ui/shell/controllers/project_session_services.py`
  - `ea_node_editor/ui/shell/controllers/run_controller.py`
  - `ea_node_editor/ui_qml/viewer_session_bridge.py`
  - `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
  - `tests/test_project_session_controller_unit.py`
  - `tests/test_shell_project_session_controller.py`
  - `tests/test_shell_run_controller.py`
  - `tests/test_viewer_session_bridge.py`
  - `tests/test_viewer_surface_contract.py`
  - `tests/test_viewer_surface_host.py`
- This packet owns bridge projection and user-facing run-required states. Do not start QA-matrix or traceability closeout here.
