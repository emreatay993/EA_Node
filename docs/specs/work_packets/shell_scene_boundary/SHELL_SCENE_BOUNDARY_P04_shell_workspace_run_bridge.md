# SHELL_SCENE_BOUNDARY P04: Shell Workspace Run Bridge

## Objective
- Move workspace/run/title/console shell QML consumers onto a focused workspace bridge so those components stop depending directly on `ShellWindow`, `workspaceTabsBridge`, and `consoleBridge` for owned concerns.

## Preconditions
- `P02` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_workspace_manager.py`
- `tests/test_script_editor_dock.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_workspace_manager.py`
- `tests/test_script_editor_dock.py`

## Required Behavior
- Expose project title, scope breadcrumb data/actions, view/workspace tab state/actions, run controls, script-editor visibility toggles, and console readouts through `shell_workspace_bridge.py` or an equivalent focused facade created in `P02`.
- Update the owned QML components to consume the dedicated bridge for those concerns instead of direct `mainWindowRef`, `workspaceTabsBridgeRef`, and `consoleBridgeRef` usage.
- Preserve workspace tab/object discoverability, run-button behavior, console clear behavior, and script-editor dock flows.
- Keep `GraphCanvas.qml` wiring unchanged in this packet.

## Non-Goals
- No library/search/quick-insert/hint migration.
- No inspector migration.
- No GraphCanvas bridge rewrite.
- No `GraphSceneBridge` internal refactor.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_shell_run_controller tests.test_workspace_manager tests.test_script_editor_dock -v`

## Acceptance Criteria
- The owned shell QML components no longer depend directly on raw shell/workspace/console bridge objects for their owned concerns.
- Workspace/run/title/console behavior remains stable.
- Relevant shell/runtime regressions pass.

## Handoff Notes
- `P06` depends on this packet only for the broader shell-boundary pattern; it does not reopen these components unless a regression requires it.
