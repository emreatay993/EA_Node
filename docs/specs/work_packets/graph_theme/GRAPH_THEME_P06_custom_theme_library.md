# GRAPH_THEME P06: Custom Theme Library

## Objective
- Add persisted custom graph-theme normalization, storage, and CRUD helpers without introducing the editor dialog yet.

## Preconditions
- `P05` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- Built-in graph-theme selection and `follow_shell_theme` mode already work end-to-end.

## Target Subsystems
- `ea_node_editor/ui/graph_theme/*`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `tests/test_graph_theme_preferences.py`
- `tests/test_graphics_settings_dialog.py`

## Required Behavior
- Add full custom-theme normalization and serialization.
- Merge built-in and custom themes into one graph-theme choice surface.
- Add CRUD helpers for:
  - create blank custom theme
  - duplicate an existing graph theme into custom
  - rename a custom theme
  - delete a custom theme
  - save a custom theme definition
- Generate custom-theme ids as `custom_graph_theme_<8hex>`.
- Deleting an active custom theme must leave preferences with a valid built-in fallback.
- Keep custom themes stored inline in app preferences.

## Non-Goals
- No dialog UI yet.
- No token editing widgets yet.
- No live token editing workflow yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_preferences tests.test_graphics_settings_dialog -v`

## Acceptance Criteria
- Custom graph themes round-trip through app-preferences normalization and persistence.
- Built-in and custom themes resolve through one unified graph-theme choice surface.
- Invalid or deleted custom-theme references fall back safely to a valid built-in theme.

## Handoff Notes
- `P07` adds the user-facing graph-theme manager/editor dialog shell on top of these CRUD helpers.
