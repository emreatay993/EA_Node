# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P02: DPF Transport Bundle Materialization

## Objective

- Implement the first concrete DPF backend so the worker exports, reuses, and cleans a session-scoped temp transport bundle plus metadata manifest for embedded viewing, while preserving current user-facing `output_mode` behavior and making rerun-required reopen state explicit when live transport is unavailable.

## Preconditions

- `P01` is complete and its viewer session contract is accepted.
- The implementation base is current `main`.

## Execution Dependencies

- `P01`

## Target Subsystems

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

## Conservative Write Scope

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
- `docs/specs/work_packets/cross_process_viewer_backend_framework/P02_dpf_transport_bundle_materialization_WRAPUP.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`

## Required Behavior

- Implement the first concrete DPF viewer backend using worker-owned, session-scoped temp transport files plus a typed manifest or metadata descriptor that the shell can consume later.
- Use the internal temp transport for live viewing even when the node is `output_mode=memory`, while preserving current stored-output behavior and user-facing `output_mode` semantics.
- Cache and reuse transport artifacts per session and transport revision instead of rematerializing them unnecessarily.
- Release session-scoped live transport on close, invalidation, rerun, worker reset, project replacement, and shutdown.
- When a session is reopened without valid live transport, publish an explicit live-open blocker or status that requires rerun rather than silently attempting to revive stale transport.
- Update inherited `tests/test_execution_viewer_service.py` and `tests/test_dpf_viewer_node.py` regression anchors in place so the new concrete transport semantics replace the earlier placeholder contract instead of coexisting with it.

## Non-Goals

- No shell widget host or binder loading yet; that belongs to `P03` and `P04`.
- No QML copy, project-load blocker messaging, or traceability updates yet.
- No generic non-DPF backend implementation beyond the contract surface already introduced in `P01`.

## Verification Commands

1. Session service and worker proof:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_worker.py tests/test_dpf_viewer_node.py --ignore=venv -q
```

2. DPF runtime materialization proof:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_materialization.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py --ignore=venv -q
```

## Expected Artifacts

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

## Acceptance Criteria

- The DPF backend emits a typed temp-bundle transport descriptor and revision through the authoritative viewer session payload.
- Live transport is reused per session when still valid and is cleaned up when the session or worker lifecycle invalidates it.
- `output_mode` semantics seen by users remain unchanged even though live viewing now uses internal temp transport files.
- Reopened sessions without valid live transport expose an explicit rerun-required blocker rather than stale live state.
- Both packet verification commands pass.
- The review gate passes.

## Handoff Notes

- Stop after `P02`. Do not start `P03` in the same thread.
- `P03` and `P04` consume `backend_id`, `transport`, `transport_revision`, and live-open blocker fields from this packet as their stable shell-side inputs.
