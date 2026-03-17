# P02 QML Context Bootstrap Wrap-Up

## Implementation Summary

- Extracted QML shell bootstrap wiring out of [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui/shell/window.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui/shell/window.py) into [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_context_bootstrap.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_context_bootstrap.py). The helper now owns `QQuickWidget` resize setup, image-provider registration, legacy context-property registration, new facade context-property registration, `MainShell.qml` source load, and render-frame hookup.
- Added narrow bootstrap-only facade skeletons for later packets:
  - [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_library_bridge.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_library_bridge.py)
  - [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_workspace_bridge.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_workspace_bridge.py)
  - [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_inspector_bridge.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/shell_inspector_bridge.py)
  - [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/graph_canvas_bridge.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui_qml/graph_canvas_bridge.py)
- `ShellWindow` now instantiates and retains the four new facades before QML load, while keeping all locked legacy context-property names intact.
- Remediated the packet gate regressions caused by stale selection readers after `GraphSceneBridge` moved selection state out of `nodes_model`:
  - [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/ea_node_editor/ui/shell/controllers/workspace_edit_ops.py) now derives overlap bounds from `scene.selected_node_lookup` plus `nodes_model` geometry instead of expecting `node_payload["selected"]`.
  - [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/tests/main_window_shell/edit_clipboard_history.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/tests/main_window_shell/edit_clipboard_history.py) now asserts selected clipboard/duplicate results against `scene.selected_node_lookup`, matching the P02 scene-boundary contract.
- Added regression coverage in [`/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/tests/test_main_window_shell.py`](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/tests/test_main_window_shell.py) for legacy context preservation plus new facade registration. No shared status-ledger edits were made, per thread constraint.

## Verification

- `./venv/Scripts/python.exe -c "import PyQt6,sys; print(sys.executable)"`  
  PASS. Confirmed the project-local interpreter at `C:\Users\emre_\PycharmProjects\EA_Node_Editor\venv\Scripts\python.exe`.
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.edit_clipboard_history.MainWindowShellEditClipboardHistoryTests.test_qml_request_duplicate_selected_nodes_duplicates_internal_edges_and_selects_result tests.main_window_shell.edit_clipboard_history.MainWindowShellEditClipboardHistoryTests.test_qml_request_copy_and_paste_selected_nodes_preserves_internal_edges_and_recenters_fragment tests.main_window_shell.edit_clipboard_history.MainWindowShellEditClipboardHistoryTests.test_qml_request_paste_selected_nodes_into_other_workspace_selects_pasted_nodes tests.main_window_shell.shell_basics_and_search.MainWindowShellBasicsAndSearchTests.test_align_overlap_posts_tidy_hint -v`  
  PASS. `4` tests ran in about `9.9s`; the three clipboard regressions and the align-overlap hint regression all passed after the selection-reader fix.
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression -v`  
  PASS. `122` tests ran in `273.669s`.
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellContextBootstrapTests tests.test_graph_scene_bridge_bind_regression -v`  
  PASS. `3` tests ran in `0.997s`.
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.shell_basics_and_search.MainWindowShellBasicsAndSearchTests.test_qml_shell_and_bridges_are_present -v`  
  PASS. `1` test ran in `0.998s`.

## Manual Test Directives

Ready for manual testing

- Prerequisite: launch the app from this branch with the normal shell entrypoint in an environment where Qt can create a window.
- Smoke test 1: start the shell and confirm the main window loads without a `UI Load Error` dialog. Expected result: the `MainShell.qml` surface renders, the graph canvas is visible, and the shell still opens with the existing library/inspector/workspace layout.
- Smoke test 2: exercise one trivial shell interaction after startup, such as selecting a node or opening the library pane. Expected result: no startup-time binding errors appear, and the app behaves the same as before the bootstrap extraction.
- Smoke test 3: close and relaunch once. Expected result: startup remains stable on the second launch, which helps confirm the extracted bootstrap still wires image providers, context properties, and frame hooks consistently.

## Residual Risks

- The new facade classes are intentionally skeletal. They are safe bootstrap anchors for `P03` through `P06`, but they do not yet carry migrated consumer logic.
- Selection now correctly lives outside `nodes_model`; future shell work should continue reading selection from `GraphSceneBridge.selected_node_lookup` or selection-specific APIs rather than reintroducing payload flags.

## Ready for Integration

Yes. The required packet verification command is now green, and the P02 bootstrap seam plus the previously failing shell regressions pass together on this branch.
