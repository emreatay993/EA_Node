# P09 Graph Scene Payload Builder Split Wrap-Up

## Implementation Summary
- Added [`graph_scene_payload_builder.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/graph_scene_payload_builder.py) to own graph-theme resolution, PDF panel page normalization, node/minimap payload shaping, inline-property assembly, and edge payload rebuilding.
- Updated [`graph_scene_bridge.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/graph_scene_bridge.py) so `_rebuild_models()`, `_normalize_pdf_panel_pages()`, `_active_graph_theme()`, and `edge_item()` delegate to the helper while keeping the public `GraphSceneBridge` API and signal emission order stable.
- Updated [`test_graph_theme_shell.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/tests/test_graph_theme_shell.py) to run each shell-backed test in its own subprocess, matching the repo’s existing workaround for the Windows multi-`ShellWindow` Qt/QML access violation and making the packet verification command reliable.

## Verification
- `./venv/Scripts/python.exe -m py_compile ea_node_editor/ui_qml/graph_scene_bridge.py ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `./venv/Scripts/python.exe -m py_compile tests/test_graph_theme_shell.py`
- `git diff --check -- ea_node_editor/ui_qml/graph_scene_bridge.py ea_node_editor/ui_qml/graph_scene_payload_builder.py tests/test_graph_theme_shell.py`
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_shell -v`
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_visual_metadata tests.test_pdf_preview_provider -v`
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_graph_theme_shell tests.test_passive_visual_metadata tests.test_pdf_preview_provider -v`
  - Result: `24` tests passed.

## Manual Test Directives
Ready for manual testing

1. Prerequisite: launch the app from this workspace with the project venv and open a graph containing at least one `Start`, `Constant`, `Branch`, and `PDF Panel` node.
   Action: open Graphics Settings, switch the shell theme, then disable graph-theme following and pick the other graph theme explicitly.
   Expected result: shell chrome follows the shell theme, graph node accents remain category-based, and graph edge colors refresh immediately to the selected graph theme without needing to reopen the workspace.
2. Action: connect two flow-capable passive nodes, set an edge label, and apply a dashed/open-arrow edge visual style; then zoom the canvas from normal to mid zoom to low zoom.
   Expected result: the flow edge label shows as a pill at normal zoom, reduces to text at mid zoom, and hides at low zoom while the edge stroke and label colors remain correct.
3. Action: point a `PDF Panel` node at a local multi-page PDF and enter an out-of-range page number in the inspector or inline editor.
   Expected result: the node clamps to the last valid page, the preview stays available, and the stored node payload reflects the normalized page number after refresh.

## Residual Risks
- `GraphScenePayloadBuilder` still reads bridge-owned private state and writes rebuilt payload arrays back through the bridge, so later packets should continue extracting behind this seam instead of re-inlining builder logic.
- The Windows Qt/QML lifetime issue for multiple `ShellWindow()` instances in one interpreter remains a broader test-environment constraint; this packet only applied the existing subprocess-isolation pattern to the packet-owned graph-theme shell tests.

## Ready for Integration
- Ready. P09 is implemented within the packet write scope, the required regression slice is green, and the shared status ledger was intentionally left unchanged per the thread instructions.
