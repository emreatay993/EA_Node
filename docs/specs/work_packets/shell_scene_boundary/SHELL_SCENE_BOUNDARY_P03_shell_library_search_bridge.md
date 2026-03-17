# SHELL_SCENE_BOUNDARY P03: Shell Library Search Bridge

## Objective
- Move node-library, custom-workflow context menu, graph-search, connection-quick-insert, and graph-hint QML consumers onto a focused shell bridge instead of reading those concerns directly from `ShellWindow`.

## Preconditions
- `P02` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Expose library filters/results, custom-workflow context actions, graph-search state/actions, connection-quick-insert state/actions, and graph-hint state through `shell_library_bridge.py` or an equivalent focused facade created in `P02`.
- Update the owned QML components to consume the dedicated bridge for those concerns instead of `mainWindowRef`.
- Keep QML object names, list models, popup behavior, and keyboard/navigation flows stable.
- Keep existing `ShellWindow` compatibility methods/properties callable for tests or non-migrated consumers outside this packet.

## Non-Goals
- No workspace/run/title/console bridge migration.
- No inspector bridge migration.
- No GraphCanvas boundary rewrite.
- No `GraphSceneBridge` internal refactor.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- The owned shell QML components no longer read library/search/quick-insert/hint concerns directly from `ShellWindow`.
- Library/search/workflow behavior remains unchanged from the user’s perspective.
- Relevant shell/controller regressions pass.

## Handoff Notes
- `P04` and `P05` migrate the remaining shell QML consumer groups in parallel.
