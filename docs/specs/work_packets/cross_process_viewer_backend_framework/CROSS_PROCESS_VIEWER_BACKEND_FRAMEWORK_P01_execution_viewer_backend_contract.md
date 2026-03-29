# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P01: Execution Viewer Backend Contract

## Objective

- Introduce the generic execution-side viewer backend/session contract so authoritative viewer payloads carry `backend_id`, typed transport descriptors, transport revision, explicit live-open blocker state, and camera/playback snapshots without requiring raw DPF dataset handles or renderer objects to cross the worker/UI boundary.

## Preconditions

- `P00` is complete and the packet set is registered in `.gitignore` and `docs/specs/INDEX.md`.
- The implementation base is current `main`.

## Execution Dependencies

- `P00`

## Target Subsystems

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

## Conservative Write Scope

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
- `docs/specs/work_packets/cross_process_viewer_backend_framework/P01_execution_viewer_backend_contract_WRAPUP.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`

## Required Behavior

- Add a generic execution-side viewer backend registry or contract layer that keeps backend-specific transport logic out of the base session service.
- Extend authoritative viewer commands and events so payloads carry `backend_id`, typed `transport`, `transport_revision`, explicit live-open status or blocker fields, and camera/playback snapshot data that can round-trip through the worker boundary.
- Keep `ViewerSessionService` as the single authority for lifecycle, session identity, liveness, invalidation, reopen state, and session-scoped state snapshots; do not leave packet-owned state synthesis in the shell path.
- Preserve JSON-safe protocol serialization, request correlation, and worker/client compatibility for the viewer command family.
- Update the DPF viewer adapter so the worker emits the new generic contract fields even before the shell binder exists, while preserving current node-level viewer session behavior where packet scope does not change it.
- Update inherited protocol, client, worker, viewer-session-service, and DPF viewer-node regression anchors in place instead of duplicating the same assertions in new packet-local tests.

## Non-Goals

- No session-scoped temp bundle export or cleanup implementation yet; that belongs to `P02`.
- No shell widget host or binder work yet; that belongs to `P03` and `P04`.
- No QML copy, run-required surface states, or docs/traceability updates yet.

## Verification Commands

1. Full packet verification:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_execution_client.py tests/test_execution_viewer_service.py tests/test_execution_worker.py tests/test_dpf_viewer_node.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_execution_viewer_service.py --ignore=venv -q
```

## Expected Artifacts

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

## Acceptance Criteria

- Viewer command and event payloads expose a generic backend/session contract with typed transport and blocker metadata.
- The worker-side viewer session path remains the single authority for viewer lifecycle and state snapshots.
- Viewer protocol serialization remains JSON-safe and request-correlated for the expanded payload shape.
- The DPF viewer adapter emits the new contract fields without leaking raw renderer objects across the process boundary.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P01`. Do not start `P02` in the same thread.
- `P02` inherits `tests/test_execution_viewer_service.py` and `tests/test_dpf_viewer_node.py` when it replaces placeholder transport semantics with concrete DPF temp-bundle transport behavior.
