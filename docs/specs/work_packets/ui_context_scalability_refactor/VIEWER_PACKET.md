# Viewer Packet

Baseline packet: `P06 Viewer Surface Isolation`.

Use this contract when a change affects viewer-session state, viewer projection into QML, embedded overlay hosting, viewer surface interaction contracts, or built-in viewer node behavior that feeds the isolated viewer UI path.

## Owner Files

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`

## Public Entry Points

- `ViewerSessionBridge`
- `ViewerHostService`
- `GraphViewerSurface.qml`
- The `viewerSessionBridge` and `viewerHostService` QML context properties exported by shell composition
- The built-in viewer node adapters that feed viewer-session payloads

## State Owner

- `viewer_session_service.py` owns the authoritative viewer-session model and lifecycle.
- `ViewerSessionBridge` projects that service state plus explicitly local pending UI state into QML.
- `ViewerHostService` owns native overlay binding, binder selection, and overlay synchronization.
- `GraphViewerSurface.qml` renders the proxy and live-surface contract without becoming the authority for viewer-session policy.

## Allowed Dependencies

- Viewer packet code may depend on the execution-side viewer session service, graph-scene selection context, overlay managers, widget binders, and packet-owned built-in viewer nodes or adapters.
- Viewer packet code may expose viewer projection to generic graph surfaces through the public viewer surface contract only.
- Viewer packet tests may tighten viewer bridge, host, and DPF-node regression anchors when projection fields or overlay behavior change.

## Invariants

- Generic graph-editing packets stay viewer-agnostic.
- `ViewerSessionBridge` stays a compact projection of authoritative service state plus explicitly local pending UI state.
- `GraphViewerSurface.qml` keeps the documented graph-surface interaction contract, including `embeddedInteractiveRects`, `blocksHostInteraction`, and `viewerSurfaceContract`.
- Native overlay hosting and binder management stay isolated in `ViewerHostService`.
- Documented viewer-family behavior stays preserved.

## Forbidden Shortcuts

- Do not make generic shell, graph-scene, graph-canvas, or edge packets depend on viewer-only session internals.
- Do not duplicate authoritative viewer-session state inside QML.
- Do not bypass `ViewerHostService` for overlay or widget-binder management.
- Do not move backend-specific viewer behavior into generic graph-surface packets.

## Required Tests

- `tests/test_execution_viewer_service.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_node.py`
