# P12 Viewer Session Transport Cleanup Wrap-Up

## Implementation Summary
- Packet: P12 Viewer Session Transport Cleanup
- Branch Label: codex/corex-no-legacy-architecture-cleanup/p12-viewer-session-transport-cleanup
- Commit Owner: worker
- Commit SHA: 4f2e2552393dd972d8f42dea4df9d9918fd0648b
- Changed Files: ea_node_editor/execution/dpf_runtime/viewer_session_backend.py, ea_node_editor/execution/viewer_backend_dpf.py, ea_node_editor/execution/viewer_session_service.py, ea_node_editor/ui_qml/components/GraphCanvas.qml, ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceBody.qml, ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml, ea_node_editor/ui_qml/dpf_viewer_widget_binder.py, ea_node_editor/ui_qml/viewer_host_service.py, ea_node_editor/ui_qml/viewer_session_bridge.py, tests/test_dpf_viewer_widget_binder.py, tests/test_execution_viewer_protocol.py, tests/test_execution_viewer_service.py, tests/test_graph_surface_input_controls.py, tests/test_viewer_host_service.py, tests/test_viewer_session_bridge.py, docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P12_viewer_session_transport_cleanup_WRAPUP.md
- Artifacts Produced: docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P12_viewer_session_transport_cleanup_WRAPUP.md

Replaced the compressed viewer session bridge and service facades with normal source, tightened viewer session projection to one typed model shape, and removed embedded `session_model` authority paths. Collapsed DPF viewer materialization onto the runtime transport bundle contract, removed synthetic `dpf_handle_refs` and `transport_not_ready` aliases, and forwarded typed transport release/reset operations through the DPF backend.

Updated viewer host and QML surfaces to consume typed session fields directly, replaced hidden `ea.viewer.*` widget properties with explicit binder state, and removed temporary add-on/viewer UI fallbacks including disabled restart/workflow settings affordances and the locked-node load CTA. Packet-owned tests were updated to assert the typed contract and current shell-context graph action wiring.

## Verification
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_dpf_viewer_widget_binder.py tests/test_dpf_viewer_node.py tests/test_graph_surface_input_controls.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q`
- PASS: Result was 101 passed, 4 warnings, 9 subtests passed.
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py --ignore=venv -q`
- PASS: Result was 49 passed, 32 warnings.
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing.

- Prerequisite: run from this P12 worktree with the DPF add-on and any required Ansys DPF runtime available.
- Open a workflow with a DPF viewer node, run it, and open the embedded viewer. Expected result: the viewer opens with the DPF transport bundle, no rerun-required blocker appears while the bundle is live, and open/close behavior matches the previous user-facing flow.
- Exercise play, pause, and step controls on the viewer. Expected result: playback state and step index remain stable across bridge events and host rebinding.
- Switch focus away from and back to the live viewer, including fullscreen if available. Expected result: proxy/full transitions preserve the captured camera and preview state, and the live widget rebinds without hidden widget-property state.
- Open the add-on manager with pending add-on changes. Expected result: the disabled runtime restart affordance and workflow-settings fallback button are absent.
- Open a graph containing locked missing-add-on nodes. Expected result: no locked-node load CTA is offered from the canvas status ribbon; current graph action routing still handles the explicit add-on manager context action.

## Residual Risks
The DPF live viewer path still depends on environment-specific Ansys DPF runtime availability, so automated tests validate contract behavior with controlled fixtures rather than a full external DPF server session. Broader P13 launch/import shim cleanup and P14 documentation closeout were intentionally left untouched.

## Ready for Integration
- Yes: P12 source changes, packet-owned verification, review gate, and wrap-up artifact are complete on the assigned packet branch.
