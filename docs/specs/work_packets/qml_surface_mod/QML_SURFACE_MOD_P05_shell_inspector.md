# QML_SURFACE_MOD P05: Shell Inspector Extraction

## Objective
- Extract the right-side inspector panel and editors from `MainShell.qml` into a dedicated component while preserving node edit behavior.

## Preconditions
- `P04` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_inspector_reflection.py`

## Required Behavior
- Extract inspector panel structure and selected-node editors into `InspectorPane.qml`.
- Preserve support for bool/enum/string editors, subnode pin data type editor, exposed-port toggles, and collapse/publish actions.
- Preserve all `mainWindow` property and slot binding semantics for selected-node edits.
- Keep existing selected-node and selected-port payload consumption unchanged.

## Non-Goals
- No graph-search/script-editor/hint overlay extraction.
- No GraphCanvas refactor in this packet.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_inspector_reflection -v`

## Acceptance Criteria
- Inspector component extraction is behavior-equivalent for node and port editing flows.
- Shell, workspace-library-controller, and inspector reflection tests pass.

## Handoff Notes
- `P06` extracts remaining overlays (graph search, script editor, graph hint) from `MainShell.qml`.
