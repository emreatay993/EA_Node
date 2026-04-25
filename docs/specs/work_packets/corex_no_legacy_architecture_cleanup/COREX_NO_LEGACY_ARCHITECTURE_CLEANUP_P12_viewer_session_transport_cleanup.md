# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P12: Viewer Session Transport Cleanup

## Objective

- Replace viewer session projection aliases, compressed bridge facade code, and widget-property handshakes with typed session and transport contracts.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only viewer/add-on/QML files needed for this packet

## Preconditions

- `P11` is marked `PASS`.

## Execution Dependencies

- `P11`

## Target Subsystems

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/execution/viewer_backend_dpf.py`
- `ea_node_editor/execution/dpf_runtime/viewer_session_backend.py`
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/dpf_viewer_widget_binder.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceBody.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P12_viewer_session_transport_cleanup_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/execution/viewer_backend_dpf.py`
- `ea_node_editor/execution/dpf_runtime/viewer_session_backend.py`
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/dpf_viewer_widget_binder.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceBody.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P12_viewer_session_transport_cleanup_WRAPUP.md`

## Required Behavior

- Replace compressed `exec(zlib.decompress(...))` bridge facade code in `viewer_session_bridge.py` with normal source that can be reviewed and maintained.
- Require one viewer session model shape; remove embedded `session_model`, top-level summary/options fallbacks, `legacy_data_refs`, frame-index aliases, and proxy/full live demotion branches unless still current with explicit typed fields.
- Collapse DPF viewer backend projection into one typed backend/session contract instead of a two-step wrapper that synthesizes blocked bundles and `transport_not_ready` aliases.
- Update `viewer_host_service` to consume typed bridge/session objects instead of discovering bridges through `getattr` and reconstructing snapshots from partial dicts.
- Replace `ea.viewer.*` hidden widget properties in `dpf_viewer_widget_binder.py` with explicit typed adapter state where feasible.
- Remove temporary viewer/add-on UI fallbacks such as locked-node load CTA variants, disabled restart runtime affordances, and workflow-settings fallbacks when they only preserve transitional behavior.
- Preserve current viewer open/close/play/pause/user-facing behavior where it is a current feature.

## Non-Goals

- No plugin descriptor cleanup; P10 owns that.
- No launch/import shim cleanup; P13 owns that.
- No uncommitted user overlay-manager changes should be reverted; work with them if present.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_dpf_viewer_widget_binder.py tests/test_dpf_viewer_node.py tests/test_graph_surface_input_controls.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P12_viewer_session_transport_cleanup_WRAPUP.md`

## Acceptance Criteria

- Viewer session state has one typed current projection.
- Viewer bridge and host service are readable normal source and do not rely on compatibility dict probing.
- Widget binder and QML surface actions use explicit session/transport command objects or the narrowest current equivalent.

## Handoff Notes

- `P13` may remove import shims around viewer modules only after this packet leaves clear canonical import paths.
