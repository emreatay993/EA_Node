# P06 GraphCanvas Boundary Bridge Wrap-Up

## Implementation Summary
- Added the regression test first in `tests/test_passive_graph_surface_host.py` to prove that dragging one node from a multi-selection updates both the live drag preview and the committed positions for every selected node.
- Added `GraphCanvasBridge` coverage in `tests/test_main_window_shell.py` for forwarding `selected_node_lookup`, which is now the authoritative selection source for the shell-hosted canvas path.
- Fixed `ea_node_editor/ui_qml/components/GraphCanvas.qml` so multi-drag membership resolves from `selected_node_lookup` through `canvasBridgeRef` first, falls back to `sceneBridge.selected_node_lookup` for standalone/raw-host probes, and only uses legacy inline `node.selected` flags when no selection lookup is available.
- Extended `ea_node_editor/ui_qml/graph_canvas_bridge.py` with a `selected_node_lookup` property and selection-change signal wiring so the P06 boundary adapter continues to own canvas-facing selection reads.

## Verification
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.GraphCanvasBridgeTests.test_bridge_forwards_selected_node_lookup tests.test_passive_graph_surface_host.PassiveGraphSurfaceHostTests.test_graph_canvas_drag_moves_all_selected_nodes_together -v`
  - Result: `2` tests, `OK`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.GraphCanvasBridgeTests -v`
  - Result: `3` tests, `OK`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellGraphCanvasHostTests.test_graph_canvas_host_binds_canvas_bridge_ref_to_registered_graph_canvas_bridge -v`
  - Result: `1` test, `OK`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellGraphCanvasHostTests.test_graph_canvas_keeps_graph_node_card_discoverability_after_host_refactor -v`
  - Result: `1` test, `OK`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host.PassiveGraphSurfaceHostTests -v`
  - Result: `12` tests, `OK`
- PASS: `./venv/Scripts/python.exe -m py_compile ea_node_editor/ui_qml/graph_canvas_bridge.py tests/test_main_window_shell.py tests/test_passive_graph_surface_host.py`
  - Result: success
- PASS: `git diff --check -- ea_node_editor/ui_qml/components/GraphCanvas.qml ea_node_editor/ui_qml/graph_canvas_bridge.py tests/test_main_window_shell.py tests/test_passive_graph_surface_host.py docs/specs/work_packets/shell_scene_boundary/P06_graph_canvas_boundary_bridge_WRAPUP.md`
  - Result: no diff-check findings

## Manual Test Directives
Ready for manual testing.

- Prerequisite: launch the app normally and open a workspace where at least two nodes are visible in the same graph scope.
- Test 1: multi-select two nodes, then drag one of the selected nodes across the canvas.
  Expected result: both selected nodes move together during the live drag preview and keep the same relative spacing after release.
- Test 2: enable Snap to Grid, keep both nodes selected, and drag one of them again.
  Expected result: both selected nodes still preview together while dragging, and both commit to the same snapped delta on release.
- Test 3: clear the multi-selection, select only one node, and drag it.
  Expected result: only the dragged node moves, confirming the remediation did not widen single-node drag behavior.

## Residual Risks
- `GraphCanvas.qml` still keeps the raw `sceneBridge` and legacy inline-selection fallback for compatibility with standalone probe instantiation; later packet work should not treat that fallback as a new primary path.
- The known Windows Qt/QML lifetime instability when constructing multiple `ShellWindow` instances in one interpreter remains outside this remediation; the host-boundary shell checks were therefore verified as isolated test invocations.

## Ready for Integration
Yes. This remediation pass is integration-ready.
