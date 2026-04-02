# ARCHITECTURE_FOLLOWUP_REFACTOR P07: Viewer Session Single Authority

## Objective

- Make execution-side viewer session state the sole packet-owned authority and limit bridge, host-service, and QML surface layers to projection, intent forwarding, and widget hosting.

## Preconditions

- `P06` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P06`

## Target Subsystems

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/execution/viewer_backend.py`
- `ea_node_editor/execution/viewer_backend_dpf.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_execution_worker.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_widget_binder.py`

## Conservative Write Scope

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/execution/viewer_backend.py`
- `ea_node_editor/execution/viewer_backend_dpf.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_execution_worker.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `docs/specs/work_packets/architecture_followup_refactor/P07_viewer_session_single_authority_WRAPUP.md`

## Required Behavior

- Keep `ViewerSessionService` as the sole packet-owned authority for viewer session lifecycle, blocker state, transport revision, and live/proxy projection inputs.
- Reduce packet-owned bridge and host-service logic to projection, widget-host coordination, and intent forwarding only.
- Update `GraphViewerSurface.qml` to consume one normalized packet-owned session model instead of recomputing state from multiple payload fragments.
- Update inherited viewer bridge, viewer host, execution viewer, and viewer-surface regression anchors in place rather than leaving stale assertions behind.

## Non-Goals

- No new backend types or viewer features beyond authority cleanup.
- No new project-persistence semantics beyond what existing viewer requirements already allow.
- No final docs or traceability closeout yet; that belongs to `P08`.

## Verification Commands

1. Execution-side viewer proof:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_execution_worker.py tests/test_viewer_session_bridge.py --ignore=venv -q
```

2. Host and surface proof:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_host_service.py tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P07_viewer_session_single_authority_WRAPUP.md`

## Acceptance Criteria

- Packet-owned viewer session state has one authoritative path.
- Packet-owned bridge and host-service layers do not own a competing blocker or liveness state machine.
- `GraphViewerSurface.qml` consumes one normalized packet-owned session model.
- The inherited execution-viewer, bridge, host, and surface regression anchors pass.

## Handoff Notes

- `P08` closes out docs, QA evidence, and traceability for the final architecture state shipped through this packet.
