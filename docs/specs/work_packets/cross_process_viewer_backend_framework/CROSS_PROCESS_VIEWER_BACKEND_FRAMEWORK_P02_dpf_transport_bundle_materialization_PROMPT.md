Implement CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization.md exactly. Before editing, read CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md, CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md, and CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/cross_process_viewer_backend_framework/P02_dpf_transport_bundle_materialization_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/cross-process-viewer-backend-framework/p02-dpf-transport-bundle-materialization` from `main`.
- Review Gate: `.\venv\Scripts\python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/P02_dpf_transport_bundle_materialization_WRAPUP.md`
  - `ea_node_editor/execution/viewer_session_service.py`
  - `ea_node_editor/execution/worker_runtime.py`
  - `ea_node_editor/execution/dpf_runtime/base.py`
  - `ea_node_editor/execution/dpf_runtime/materialization.py`
  - `ea_node_editor/execution/dpf_runtime/operations.py`
  - `ea_node_editor/execution/dpf_runtime/viewer_session_backend.py`
  - `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`
  - `tests/test_execution_viewer_service.py`
  - `tests/test_execution_worker.py`
  - `tests/test_dpf_runtime_service.py`
  - `tests/test_dpf_materialization.py`
  - `tests/test_dpf_viewer_node.py`
- This packet owns concrete DPF temp transport export, reuse, and cleanup. Do not start shell host or binder work here.
