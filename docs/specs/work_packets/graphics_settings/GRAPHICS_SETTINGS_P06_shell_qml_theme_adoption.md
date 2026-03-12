# GRAPHICS_SETTINGS P06: Shell QML Theme Adoption

## Objective
- Move shell QML surfaces off hardcoded neutral colors and onto the shared theme palette.

## Preconditions
- `P05` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- `themeBridge` is already available to QML from `ShellWindow`.

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/ShellButton.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `tests/test_main_window_shell.py`
- `tests/test_theme_shell_rc2.py`

## Required Behavior
- Replace hardcoded shell neutral/background/border/text colors with `themeBridge` palette bindings.
- Preserve existing object names, ids, context-property names, and interaction routing contracts.
- Keep layout, sizing, and composition structure intact; this packet is a palette migration, not a shell re-layout.
- Keep status/toolbar/search/overlay behavior unchanged except for theme-driven colors.
- Leave the code editor syntax/highlight palette unchanged in this packet unless a neutral container color must match the active theme.

## Non-Goals
- No graph canvas neutral-color migration.
- No semantic node/edge/port color changes.
- No new settings UI or controller behavior.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_theme_shell_rc2 -v`

## Acceptance Criteria
- Shell QML surfaces react to the active theme without breaking current shell behavior.
- Existing shell tests still locate the same objects and contracts.
- Theme switching between `stitch_dark` and `stitch_light` does not require any new QML context properties beyond `themeBridge`.

## Handoff Notes
- `P07` applies the same palette migration to graph-canvas-facing QML surfaces while preserving semantic graph colors.
