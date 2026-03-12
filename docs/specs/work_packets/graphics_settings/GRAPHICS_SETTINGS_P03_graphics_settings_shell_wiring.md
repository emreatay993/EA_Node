# GRAPHICS_SETTINGS P03: Graphics Settings Shell Wiring

## Objective
- Add the new shell menu/action/API surfaces for graphics settings and compose app-preferences handling into `ShellWindow`.

## Preconditions
- `P02` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- `GraphicsSettingsDialog` and `AppPreferencesController` already exist.

## Target Subsystems
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/dialogs/__init__.py`
- `tests/test_theme_shell_rc2.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/test_graphics_settings_preferences.py`

## Required Behavior
- Add `Graphics Settings` as a new sibling entry under `&Settings` after `Workflow Settings`.
- Add `window.action_graphics_settings` with no keyboard shortcut in this packet.
- Add `ShellWindow.show_graphics_settings_dialog()` as the public shell API for the new modal.
- Compose `AppPreferencesController` into `ShellWindow` before `_build_qml_shell()` so preference-backed properties are available during QML load.
- Add a dedicated notify signal for graphics preferences and expose these QML-readable properties:
  - `graphics_show_grid`
  - `graphics_show_minimap`
  - `graphics_minimap_expanded`
  - `active_theme_id`
- Keep the existing `snap_to_grid_enabled` public property stable; do not rename or remove it.
- Persist accepted `GraphicsSettingsDialog` values through `AppPreferencesController`.
- Do not start the shell/canvas QML color refactors in this packet.

## Non-Goals
- No QML neutral-color replacement.
- No canvas redraw/persistence binding changes beyond the host/controller plumbing needed for later packets.
- No project metadata or serializer changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_theme_shell_rc2 tests.test_main_window_shell tests.test_graphics_settings_preferences -v`

## Acceptance Criteria
- The Settings menu exposes both `Workflow Settings` and `Graphics Settings`.
- `ShellWindow` exposes the new graphics-settings API/property surfaces without breaking existing shell contracts.
- Accepting the graphics dialog persists app preferences through the controller.

## Handoff Notes
- `P04` binds persisted graphics preferences into grid/minimap/snap runtime behavior and QML flows.
