Implement CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract.md exactly. Before editing, read CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md, CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md, and CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract.md. Implement only P01. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/cross_process_viewer_backend_framework/P01_execution_viewer_backend_contract_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/cross-process-viewer-backend-framework/p01-execution-viewer-backend-contract` from `main`.
- Review Gate: `.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_execution_viewer_service.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/P01_execution_viewer_backend_contract_WRAPUP.md`
  - `ea_node_editor/execution/protocol.py`
  - `ea_node_editor/execution/client.py`
  - `ea_node_editor/execution/worker_protocol.py`
  - `ea_node_editor/execution/worker_runner.py`
  - `ea_node_editor/execution/worker_services.py`
  - `ea_node_editor/execution/viewer_session_service.py`
  - `ea_node_editor/execution/viewer_backend*.py`
  - `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`
  - `tests/test_execution_viewer_protocol.py`
  - `tests/test_execution_client.py`
  - `tests/test_execution_viewer_service.py`
  - `tests/test_execution_worker.py`
  - `tests/test_dpf_viewer_node.py`
- This packet establishes the generic execution contract only. Do not implement DPF temp transport bundle export, shell widget host work, or QML run-required copy here.
