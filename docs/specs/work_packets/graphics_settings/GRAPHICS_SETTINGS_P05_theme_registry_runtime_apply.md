# GRAPHICS_SETTINGS P05: Theme Registry + Runtime Apply

## Objective
- Introduce a shared theme registry, runtime QWidget stylesheet application, and one canonical QML palette bridge sourced from the same theme tokens.

## Preconditions
- `P04` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- App preferences already persist `theme.theme_id`.

## Target Subsystems
- `ea_node_editor/ui/theme/tokens.py`
- `ea_node_editor/ui/theme/styles.py`
- `ea_node_editor/ui/theme/registry.py` (new)
- `ea_node_editor/ui/theme/__init__.py`
- `ea_node_editor/ui_qml/theme_bridge.py` (new)
- `ea_node_editor/app.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_theme_shell_rc2.py`
- `tests/test_graphics_settings_preferences.py`

## Required Behavior
- Add a shared theme registry keyed by `stitch_dark` and `stitch_light`.
- Keep the default theme id locked to `stitch_dark`.
- Generate runtime Qt stylesheet output from the active theme tokens rather than hardcoding a single stylesheet constant at import time.
- Keep `APP_STYLESHEET` available as the default-theme stylesheet so existing test/bootstrap code can keep using it.
- Add a canonical QML palette bridge sourced from the same theme tokens used for the Qt stylesheet.
- Compose the palette bridge into `ShellWindow` and expose it to QML as `themeBridge`.
- Apply the chosen theme during shell startup and when the active theme preference changes.
- Do not refactor hardcoded shell or canvas QML neutrals in this packet.

## Non-Goals
- No shell QML color-binding migration yet.
- No canvas QML color-binding migration yet.
- No editor syntax-color redesign.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_theme_shell_rc2 tests.test_graphics_settings_preferences -v`

## Acceptance Criteria
- Theme ids resolve deterministically to shared token sets.
- `ShellWindow` can apply the active theme at startup and on preference change.
- `themeBridge` exists for later QML packets without yet changing visual behavior.

## Handoff Notes
- `P06` moves shell QML surfaces onto the shared theme palette while preserving existing object names and interaction contracts.
