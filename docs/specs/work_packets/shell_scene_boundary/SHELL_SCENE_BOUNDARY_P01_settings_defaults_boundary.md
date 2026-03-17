# SHELL_SCENE_BOUNDARY P01: Settings Defaults Boundary

## Objective
- Remove the UI-layer dependency leak from `ea_node_editor/settings.py` so app-preferences and graphics defaults no longer import `DEFAULT_GRAPH_THEME_ID` from `ea_node_editor.ui.graph_theme`, while preserving existing defaults and persistence contracts.

## Preconditions
- `P00` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/settings.py`
- a new neutral shared-defaults module outside `ea_node_editor/ui/**` if needed
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/graph_theme/*` only if imports must be updated to consume the neutral constant source
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graph_theme_preferences.py`
- `tests/test_shell_project_session_controller.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/graph_theme/**`
- `ea_node_editor/*theme*defaults*.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graph_theme_preferences.py`
- `tests/test_shell_project_session_controller.py`

## Required Behavior
- Remove the import edge from `ea_node_editor/settings.py` into `ea_node_editor.ui.graph_theme`.
- Move any shared graph-theme default identifiers needed by settings/app-preferences code into a neutral module outside the UI package.
- Keep `DEFAULT_GRAPHICS_SETTINGS`, `DEFAULT_APP_PREFERENCES`, `APP_PREFERENCES_KIND`, and `APP_PREFERENCES_VERSION` behavior and serialized document shape stable.
- Keep graph-theme preference normalization behavior unchanged from the user’s perspective.
- Preserve existing app-preferences migration/version behavior.

## Non-Goals
- No QML contract changes.
- No `ShellWindow` / `GraphSceneBridge` refactors yet.
- No serializer or migration bug fixes beyond the narrow import-boundary cleanup required for this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_preferences tests.test_graph_theme_preferences tests.test_shell_project_session_controller -v`

## Acceptance Criteria
- `ea_node_editor/settings.py` no longer imports from `ea_node_editor.ui.graph_theme`.
- App-preferences and graph-theme preference tests pass unchanged.
- No schema-version or persisted-document changes are introduced.

## Handoff Notes
- `P10` reruns a broader boundary regression slice; keep this packet focused on the defaults/import boundary only.
