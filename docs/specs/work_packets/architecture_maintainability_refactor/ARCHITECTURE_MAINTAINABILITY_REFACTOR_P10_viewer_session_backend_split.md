# ARCHITECTURE_MAINTAINABILITY_REFACTOR P10: Viewer Session Backend Split

## Objective
- Separate generic viewer-session lifecycle and state from backend-specific DPF behavior, make the execution-side viewer session core authoritative, and reduce the QML bridge to a projection layer instead of a second state machine.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P09`

## Target Subsystems
- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/execution/dpf_runtime/`
- `ea_node_editor/execution/worker_runtime.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_materialization.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_execution_worker.py`

## Conservative Write Scope
- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/execution/dpf_runtime/`
- `ea_node_editor/execution/worker_runtime.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_materialization.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_execution_worker.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P10_viewer_session_backend_split_WRAPUP.md`

## Required Behavior
- Introduce or clarify a generic viewer-session core that owns lifecycle, identity, liveness, and invalidation behavior without embedding DPF-specific policy.
- Move DPF-specific materialization or dataset policy behind backend-specific strategy modules or services.
- Reduce `viewer_session_bridge.py` to state projection and user-intent forwarding rather than a competing packet-owned viewer state machine.
- Update inherited execution viewer, DPF runtime/materialization, viewer bridge, and worker regression anchors in place when viewer-session seams move.

## Non-Goals
- No graph-canvas scene decomposition yet; that belongs to `P11`.
- No new viewer features or backend types beyond what is needed to split ownership cleanly.
- No docs/traceability cleanup yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_viewer_session_bridge.py tests/test_execution_worker.py --ignore=venv -q`
2. `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_materialization.py tests/test_dpf_viewer_node.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_viewer_service.py tests/test_viewer_session_bridge.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P10_viewer_session_backend_split_WRAPUP.md`

## Acceptance Criteria
- Viewer-session lifecycle ownership is singular and execution-side.
- Backend-specific DPF behavior is separated from generic viewer-session state and control flow.
- The UI bridge mirrors authoritative session state instead of owning a competing workflow state machine.
- The inherited viewer and DPF regression anchors pass.

## Handoff Notes
- `P11` should assume the viewer/session boundary is cleaner and focus on graph-canvas scene decomposition without reopening viewer ownership.
