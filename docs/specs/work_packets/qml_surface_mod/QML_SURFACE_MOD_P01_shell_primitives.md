# QML_SURFACE_MOD P01: Shell Primitives Extraction

## Objective
- Extract shared shell primitives and helper utilities from `MainShell.qml` into dedicated reusable modules.

## Preconditions
- `P00` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).
- No later QML_SURFACE_MOD packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/ShellButton.qml` (new)
- `ea_node_editor/ui_qml/components/shell/MainShellUtils.js` (new)
- `tests/test_main_window_shell.py`

## Required Behavior
- Extract the inline `component ShellButton` from `MainShell.qml` into `components/shell/ShellButton.qml`.
- Extract utility functions (`toEditorText`, `comboOptionValue`, `lineNumbersText`) into `components/shell/MainShellUtils.js` and route existing call sites through the helper.
- Keep shell styles, button text, control sizing, and visual states unchanged.
- Keep `MainShell.qml` behavior and binding semantics unchanged.

## Non-Goals
- No extraction of shell chrome, library pane, workspace center, inspector, or overlays.
- No GraphCanvas changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell -v`

## Acceptance Criteria
- `MainShell.qml` reuses extracted primitives/helpers without behavior differences.
- Shell regression tests pass.

## Handoff Notes
- `P02` extracts shell chrome sections and should reuse `ShellButton.qml` instead of reintroducing inline button components.
