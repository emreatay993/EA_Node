# P07 QML Graph Canvas Core Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/corex-clean-architecture-restructure/p07-qml-graph-canvas-core`
- Commit Owner: `worker`
- Commit SHA: `0b1a42b6ae56377d2c604510c50b0019a601ee9e`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`, `tests/test_comment_backdrop_contracts.py`, `tests/test_graph_action_contracts.py`, `tests/test_passive_runtime_wiring.py`, `docs/specs/work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/corex_clean_architecture_restructure/P07_qml_graph_canvas_core_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`

Implemented a feature-root-owned graph canvas action router and wired `GraphCanvas.qml` to expose it as the semantic QML port for graph action dispatch, context-menu descriptors, keyboard shortcuts, viewer-focus clearing, and the thin content-fullscreen compatibility adapter. Graph-canvas leaves now consume the router instead of doing their own shell/viewer/fullscreen bridge lookups or raw action-id switching, while `GraphCanvasRootBindings.qml` remains the existing canvas port facade.

Context menus, node delegates, surface bridge handling, root layer edge selection, and input-layer shortcuts were moved onto router-owned semantic handlers with existing bridge fallbacks preserved. Packet-owned contract tests were updated to assert the new router ownership and to normalize current runtime DTO shape and QML probe style setup.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py --ignore=venv`
- FAIL: `.\venv\Scripts\python.exe -m pytest tests/test_comment_backdrop_contracts.py tests/test_passive_runtime_wiring.py --ignore=venv`
  - Failing test: `tests/test_comment_backdrop_contracts.py::CommentBackdropSurfaceQmlTests::test_collapsed_comment_backdrop_ignores_node_icon_source_for_title_contract`
  - Observed failure: `title icon visible: True` when a collapsed comment backdrop payload includes `icon_source`.
  - Scope note: the behavior is implemented in `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, outside the P07 conservative write scope.
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv`
- Final Verification Verdict: `FAIL`

## Manual Test Directives

Too soon for final manual testing.

- Blocker: required packet verification still has a terminal failure in the comment-backdrop title-icon contract outside the P07 write scope.
- Next condition: after the comment-backdrop title-icon contract is fixed or formally re-scoped, rerun the failed verification command and then smoke-test graph canvas selection, drag, resize, wire creation, quick insert, node and edge context menus, Delete, Alt+Left, Alt+Home, and F11 content fullscreen routing from the application launched with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`.
- Expected result after the blocker is resolved: graph-canvas interactions remain behavior-compatible while action routing continues through the feature-root router rather than leaf-level shell or viewer bridge lookups.

## Residual Risks

- Integration is blocked by the remaining comment-backdrop title-icon contract failure. The required fix appears to belong to `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, which is outside this packet scope.
- The content-fullscreen path remains intentionally thin and compatibility-oriented; deeper viewer/fullscreen policy remains P08 scope.

## Ready for Integration

- No: required verification still fails on an out-of-scope comment-backdrop title-icon contract.
