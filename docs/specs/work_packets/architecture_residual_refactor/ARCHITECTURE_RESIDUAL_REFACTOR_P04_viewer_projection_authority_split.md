# ARCHITECTURE_RESIDUAL_REFACTOR P04: Viewer Projection Authority Split

## Objective

- Make viewer-session authority singular and keep packet-owned bridge and host layers on projection and widget-hosting duties instead of a competing viewer workflow state machine.

## Preconditions

- `P03` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/ui_qml/viewer_widget_binder.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_widget_binder.py`

## Conservative Write Scope

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/ui_qml/viewer_widget_binder.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `docs/specs/work_packets/architecture_residual_refactor/P04_viewer_projection_authority_split_WRAPUP.md`

## Required Behavior

- Extract one packet-owned viewer-session authority seam so execution-side code owns liveness, blocker, transport revision, and projection inputs.
- Keep `ViewerSessionBridge` and `ViewerHostService` on projection, transport to QML, and widget-hosting responsibilities only.
- Preserve REQ-ARCH-016 and existing `backend_id`, `transport`, `transport_revision`, and live-open contract semantics.
- Update inherited viewer regression anchors in place instead of leaving parallel old and new assertions behind.

## Non-Goals

- No neutral runtime-contract extraction yet; that belongs to `P07`.
- No graph-domain mutation-factory work yet.
- No new viewer feature behavior.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_viewer_surface_host.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P04_viewer_projection_authority_split_WRAPUP.md`

## Acceptance Criteria

- Viewer-session state has one packet-owned authority.
- Bridge and host layers no longer own a competing workflow state machine.
- The inherited viewer-service, bridge, and host regression anchors pass.

## Handoff Notes

- `P05` decouples runtime-snapshot assembly after this packet stabilizes the viewer authority boundary.
