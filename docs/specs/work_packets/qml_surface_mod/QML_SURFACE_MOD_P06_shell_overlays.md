# QML_SURFACE_MOD P06: Shell Overlays Extraction

## Objective
- Extract graph-search, script-editor, and graph-hint overlays from `MainShell.qml` into composition components and reduce `MainShell.qml` to orchestration layout.

## Preconditions
- `P05` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml` (new)
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml` (new)
- `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml` (new)
- `tests/test_main_window_shell.py`
- `tests/test_script_editor_dock_rc2.py`
- `tests/test_theme_shell_rc2.py`

## Required Behavior
- Extract graph search overlay, script editor overlay, and graph hint overlay into dedicated shell components.
- Preserve keyboard/focus behavior for graph search and script editor interactions.
- Preserve script editor bridge behavior (`visible`, `dirty`, apply/revert, cursor metrics, syntax highlighter attach).
- Keep `graphHintOverlay` discoverable for tests (`objectName: "graphHintOverlay"`) with unchanged visibility behavior.
- Keep `MainShell.qml` as composition host for extracted shell sections.

## Non-Goals
- No GraphCanvas internals extraction.
- No Python controller/bridge refactor.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_script_editor_dock_rc2 tests.test_theme_shell_rc2 -v`

## Acceptance Criteria
- Overlay behavior remains unchanged under automated coverage.
- Main shell remains fully loadable and functional with extracted overlay components.

## Handoff Notes
- `P07` begins GraphCanvas-focused modularization and should not revisit MainShell extraction scope except minimal integration wiring.
