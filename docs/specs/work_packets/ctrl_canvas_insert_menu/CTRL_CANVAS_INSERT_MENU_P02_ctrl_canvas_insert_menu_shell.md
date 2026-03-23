# CTRL_CANVAS_INSERT_MENU P02: Ctrl Canvas Insert Menu Shell

## Objective
- Add the shell-owned Ctrl+double-click canvas insert menu, static Text/Stylus actions, and the stylus placeholder hint path while leaving plain double-click quick insert unchanged.

## Preconditions
- `P00` is marked `PASS` in [CTRL_CANVAS_INSERT_MENU_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md).
- No later `CTRL_CANVAS_INSERT_MENU` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/shell/CanvasInsertMenuOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/icons/letter-t.svg`
- `ea_node_editor/ui_qml/components/shell/icons/scribble.svg`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/test_shell_theme.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/shell/CanvasInsertMenuOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/icons/letter-t.svg`
- `ea_node_editor/ui_qml/components/shell/icons/scribble.svg`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/test_shell_theme.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P02_ctrl_canvas_insert_menu_shell_WRAPUP.md`

## Required Behavior
- Add a dedicated shell UI state object for the canvas insert menu anchor and target scene position.
- Expose that state through the existing shell-library presenter/bridge path with explicit open, close, and action-selection methods. Do not create a second overlay bridge.
- Add a graph-canvas command path such as `request_open_canvas_insert_menu(scene_x, scene_y, overlay_x, overlay_y)` and route it through the existing command bridge stack.
- Branch the empty-canvas double-click handler so `Ctrl` opens the new menu and no modifier keeps opening the existing quick insert.
- Add `CanvasInsertMenuOverlay.qml` as a sibling to the current quick-insert overlay in `MainShell.qml`.
- Use two bundled Tabler SVG assets for the `Text` and `Stylus` buttons, clamp the overlay to the viewport like quick insert, and close it on outside click, `Esc`, or after an action is chosen.
- Choosing `Text` closes the menu and creates a selected `passive.annotation.text` node at the clicked scene coordinates through the existing graph-node creation path so history and selection stay unchanged.
- Choosing `Stylus` closes the menu, creates no node, changes no preferences, and shows a graph hint such as `Stylus tool coming soon`.
- Keep graph search, connection quick insert, context menus, and existing quick insert state from fighting the new menu state.

## Non-Goals
- No inline body editor auto-open or body double-click reopen yet. `P03` owns that.
- No new app-preferences schema, persistent tool mode, or drawing behavior for stylus.
- No text-annotation contract or typography-schema expansion beyond consuming the `P01` result.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/shell_basics_and_search.py tests/test_shell_theme.py tests/test_main_window_shell.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/ctrl_canvas_insert_menu/P02_ctrl_canvas_insert_menu_shell_WRAPUP.md`

## Acceptance Criteria
- `Ctrl+Double Left Click` on empty canvas opens the new insert menu, while plain double-click still opens the existing canvas quick insert.
- The overlay clamps to the viewport, closes on outside click and `Esc`, and is owned by the shell-library state/bridge path rather than a second overlay bridge.
- Choosing `Text` creates a selected `passive.annotation.text` node at the clicked scene coordinates and closes the menu.
- Choosing `Stylus` creates no node, changes no preferences, closes the menu, and shows the coming-soon hint.

## Handoff Notes
- `P03` inherits `tests/main_window_shell/drop_connect_and_workflow_io.py` because it changes the `Text` action outcome from plain creation to creation plus inline-editor auto-open.
- Record the final bridge properties, slots, QML object names, and icon asset paths in the wrap-up so `P04` can document the shipped surface accurately.
