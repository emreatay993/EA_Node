# GRAPHICS_SETTINGS P01: App Preferences Foundation

## Objective
- Add versioned app-preferences defaults and controller/store scaffolding for graphics settings.

## Preconditions
- `P00` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- No later GRAPHICS_SETTINGS packet is in progress.

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py` (new)
- `ea_node_editor/ui/shell/controllers/__init__.py`
- `tests/test_graphics_settings_preferences.py` (new)

## Required Behavior
- Add `DEFAULT_GRAPHICS_SETTINGS` to `ea_node_editor/settings.py`.
- Add `app_preferences_path()` returning `user_data_dir() / "app_preferences.json"`.
- Implement an app-preferences document shape with `kind`, `version`, and `graphics`.
- Normalize missing or invalid app-preferences files to the locked defaults from the manifest.
- Implement `AppPreferencesController` as the single app-wide load/read/update/persist surface for graphics preferences.
- Use existing atomic JSON write helpers rather than inventing a second persistence pattern.
- Keep app preferences separate from `.sfe` project serialization and separate from `last_session.json`.
- Do not wire menus, dialogs, or QML theme application in this packet.

## Non-Goals
- No Settings menu changes.
- No dialog extraction or new dialog UI.
- No QML or QWidget theme refactor.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_graphics_settings_preferences -v`

## Acceptance Criteria
- Graphics preferences load with sane defaults when the file is missing or invalid.
- Persisted round-trip preserves the normalized graphics payload and document metadata.
- No `.sfe` serializer or session-store paths are modified.

## Handoff Notes
- `P02` builds the shared settings dialog shell and `GraphicsSettingsDialog` on top of this foundation.
