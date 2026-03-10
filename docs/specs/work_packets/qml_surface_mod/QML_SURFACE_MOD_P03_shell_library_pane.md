# QML_SURFACE_MOD P03: Shell Library Pane Extraction

## Objective
- Extract node library pane behavior and workflow context popup/backdrop from `MainShell.qml` into dedicated shell components.

## Preconditions
- `P02` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml` (new)
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Extract node library search/list/delegate/collapsed-category state logic into `NodeLibraryPane.qml`.
- Extract custom-workflow context popup/backdrop behavior into `LibraryWorkflowContextPopup.qml`.
- Preserve drag/drop preview/drop behavior routed through `graphCanvas` helper methods.
- Keep `libraryPane` discoverable for tests (`objectName: "libraryPane"`) and preserve reset signal handling (`libraryPaneResetRequested`).
- Preserve custom workflow scope toggle/delete invocation semantics.

## Non-Goals
- No center-pane extraction.
- No inspector or overlay extraction.
- No GraphCanvas internals extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Library-pane behavior remains equivalent, including search, category collapse defaults, drag/drop, and custom workflow context menu actions.
- Shell and workspace-library-controller tests pass.

## Handoff Notes
- `P04` extracts workspace center composition around `GraphCanvas` and console/workspace tabs.
