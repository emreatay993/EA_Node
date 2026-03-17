# P03 Shell Library Search Bridge Wrap-Up

## Implementation Summary

- Implemented a focused `ShellLibraryBridge` facade in `ea_node_editor/ui_qml/shell_library_bridge.py` that forwards the existing `ShellWindow` library, custom-workflow, graph-search, connection-quick-insert, and graph-hint property/slot surface without moving business logic out of the current shell/controller layer.
- Repointed the owned QML consumers in `NodeLibraryPane.qml`, `LibraryWorkflowContextPopup.qml`, `GraphSearchOverlay.qml`, `ConnectionQuickInsertOverlay.qml`, and `GraphHintOverlay.qml` to bind to the registered `shellLibraryBridge` context object instead of reading these concerns directly from `mainWindowRef`.
- Added focused regression coverage in `tests/test_main_window_shell.py` for bridge forwarding, signal re-emission, and a source-boundary guard that asserts the migrated QML files no longer use `mainWindowRef` for the packet-owned concerns.
- Preserved the existing `ShellWindow` compatibility methods/properties for non-migrated callers outside this packet.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.ShellLibraryBridgeTests tests.test_main_window_shell.ShellLibraryBridgeQmlBoundaryTests -v`
  - Result: `3` tests passed in `0.003s`.
- FAIL then PASS: `./venv/Scripts/python.exe -m py_compile '/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_library_bridge.py' '/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/tests/test_main_window_shell.py'`
  - Result: failed with `[Errno 2] No such file or directory` because the Windows venv interpreter was invoked from `bash` with `/mnt/...` file arguments.
- PASS: `./venv/Scripts/python.exe -m py_compile ea_node_editor/ui_qml/shell_library_bridge.py tests/test_main_window_shell.py`
  - Result: completed without output.
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`
  - Result: `144` tests passed in `286.049s`.
- PASS: `git diff --check -- ea_node_editor/ui_qml/shell_library_bridge.py ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml tests/test_main_window_shell.py`
  - Result: completed without output.

## Manual Test Directives

Ready for manual testing

- Prerequisite: launch the app normally from this branch and open any project with a visible graph canvas.
- Library pane search smoke test: type a narrow query in the node library search field, confirm the grouped results update immediately, then click a library item. Expected result: the filtered list updates without errors and the clicked node is added exactly as before.
- Custom workflow context menu smoke test: ensure at least one custom workflow exists in the library, right-click it, then exercise `Rename`, `Make Global` or `Make Project-Only`, and `Delete` on a disposable workflow. Expected result: the popup actions behave exactly as before and the library updates after each action.
- Graph search smoke test: open graph search, type a query with multiple matches, use Up or Down to change the highlight, press Enter to jump, then press Escape to close. Expected result: the highlight tracks the keyboard, the selected match opens and focuses correctly, and the overlay closes cleanly.
- Connection quick insert and hint smoke test: trigger quick insert from a compatible port and from an empty canvas position, type to filter, select a result, and also try a case with no compatible results. Expected result: quick insert positioning, filtering, selection, and node creation still work, and the graph hint message still appears when no compatible insertion is available.

## Residual Risks

- The packet intentionally keeps `ShellWindow` as the underlying behavior owner, so this is a facade migration rather than a logic extraction; any pre-existing shell/controller behavior remains unchanged by design.
- The shared status ledger was not edited in this thread because the task explicitly prohibited modifying it. Integration bookkeeping for `SHELL_SCENE_BOUNDARY_STATUS.md` still needs to be handled separately if the packet process requires it.

## Ready for Integration

Yes. The owned QML consumers now route the packet-owned library/search/quick-insert/hint concerns through `ShellLibraryBridge`, the compatibility `ShellWindow` surface remains intact, and the packet verification command passed.
