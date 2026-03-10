# QML_SURFACE_MOD P04: Shell Workspace Center Extraction

## Objective
- Extract the workspace center composition from `MainShell.qml`, including workspace/view/scope chrome, GraphCanvas host region, workspace tabs, and console section.

## Preconditions
- `P03` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_manager.py`

## Required Behavior
- Extract workspace/view/scope header, `GraphCanvas` host wiring, workspace tab strip, and console tabs into `WorkspaceCenterPane.qml`.
- Preserve all current `mainWindow` request bindings for views/workspaces/scope breadcrumbs.
- Keep `GraphCanvas` usage and behavior unchanged, including object name contract (`graphCanvas`).
- Preserve console tab switching and clear behavior.

## Non-Goals
- No inspector extraction.
- No graph-search/script/hint overlay extraction.
- No GraphCanvas helper/component extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_manager -v`

## Acceptance Criteria
- Center-pane composition is extracted with equivalent workspace/view/scope and console behavior.
- Shell and workspace-manager tests pass.

## Handoff Notes
- `P05` extracts the inspector pane and editor delegates.
