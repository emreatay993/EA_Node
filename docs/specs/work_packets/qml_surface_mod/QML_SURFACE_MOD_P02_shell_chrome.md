# QML_SURFACE_MOD P02: Shell Chrome Extraction

## Objective
- Extract shell chrome sections from `MainShell.qml` into focused composition components while preserving behavior.

## Preconditions
- `P01` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml` (new)
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml` (new)
- `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml` (new)
- `tests/test_main_window_shell.py`
- `tests/test_theme_shell_rc2.py`

## Required Behavior
- Extract top title bar, run toolbar, and bottom status strip into dedicated components.
- Keep existing action wiring (`run`, `pause`, `stop`, `settings`, script toggle) unchanged.
- Preserve text labels, ordering, layout heights, and styling values.
- Keep bridge/property usage unchanged (`mainWindow`, `viewBridge`, status bridges, `scriptEditorBridge`).

## Non-Goals
- No library-pane extraction.
- No inspector extraction.
- No overlay extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_theme_shell_rc2 -v`

## Acceptance Criteria
- Chrome composition is modularized with no behavior/visual regressions in automated coverage.
- Theme and shell tests pass.

## Handoff Notes
- `P03` extracts the left library pane and workflow context popup/backdrop.
