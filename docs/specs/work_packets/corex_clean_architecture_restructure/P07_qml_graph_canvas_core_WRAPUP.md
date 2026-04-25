# P07 QML Graph Canvas Core Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/corex-clean-architecture-restructure/p07-qml-graph-canvas-core`
- Commit Owner: `executor`
- Commit SHA: `9887d87bb2b6762db71fe6e7ec2215f2db5af848`
- Changed Files: `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P07_qml_graph_canvas_core.md`, `docs/specs/work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`, `tests/test_comment_backdrop_contracts.py`, `tests/test_graph_action_contracts.py`, `tests/test_passive_runtime_wiring.py`
- Artifacts Produced: `docs/specs/work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`

Implemented a feature-root-owned graph canvas action router and wired `GraphCanvas.qml` to expose it as the semantic QML port for graph action dispatch, context-menu descriptors, keyboard shortcuts, viewer-focus clearing, and the thin content-fullscreen compatibility adapter. Graph-canvas leaves now consume the router instead of doing their own shell/viewer/fullscreen bridge lookups or raw action-id switching, while `GraphCanvasRootBindings.qml` remains the existing canvas port facade.

Context menus, node delegates, surface bridge handling, root layer edge selection, and input-layer shortcuts were moved onto router-owned semantic handlers with existing bridge fallbacks preserved. Packet-owned contract tests were updated to assert the new router ownership and to normalize current runtime DTO shape and QML probe style setup.

User-authorized remediation extended P07 scope to `GraphNodeHeaderLayer.qml` and gates generic title icons off for comment-backdrop headers, preserving the dedicated collapsed comment glyph while preventing injected `icon_source` values from surfacing as `graphNodeTitleIcon`.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py --ignore=venv`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_comment_backdrop_contracts.py tests/test_passive_runtime_wiring.py --ignore=venv`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Launch the app with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`.
2. Smoke-test graph canvas selection, drag, resize, wire creation, quick insert, node and edge context menus, Delete, Alt+Left, Alt+Home, and F11 content fullscreen routing.
3. Create or load a collapsed comment backdrop with an injected node `icon_source`; expected result: the generic `graphNodeTitleIcon` remains hidden and the dedicated collapsed comment glyph remains available.

## Residual Risks

No blocking residual risks. The content-fullscreen path remains intentionally thin and compatibility-oriented; deeper viewer/fullscreen policy remains P08 scope. Verification continues to report existing Ansys DPF deprecation warnings and occasional non-fatal Windows pytest temp cleanup `PermissionError` after successful exit.

## Ready for Integration

- Yes: P07 graph-canvas routing is integration-ready and the user-authorized comment-backdrop title-icon contract remediation now lets all required verification commands pass.
