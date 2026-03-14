# GRAPH_THEME P05: Graph Theme Settings Controls

## Objective
- Expose graph-theme mode and built-in graph-theme selection in graphics settings.

## Preconditions
- `P04` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- `graphThemeBridge` already exists and drives node/edge visuals.

## Target Subsystems
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_graph_theme_shell.py`

## Required Behavior
- Extend `GraphicsSettingsDialog` with:
  - a `Follow shell theme` checkbox
  - a `Graph theme` combo box
- Disable the graph-theme combo when `follow_shell_theme` is enabled.
- Wire dialog values through `AppPreferencesController` and `ShellWindow`.
- Surface currently available graph themes in the combo; before `P06`, that list may contain only built-ins.
- Keep the existing shell theme selection controls and behavior intact.

## Non-Goals
- No custom-theme CRUD.
- No theme-manager dialog yet.
- No token editor.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_dialog tests.test_graph_theme_shell -v`

## Acceptance Criteria
- Users can choose follow-shell versus explicit graph-theme mode.
- Explicit graph-theme selection persists and applies through the existing app-preferences/shell flow.
- No custom-theme management UI exists yet.

## Handoff Notes
- `P06` adds the custom-theme registry overlay, normalization, and CRUD helpers that expand the graph-theme choice surface.
