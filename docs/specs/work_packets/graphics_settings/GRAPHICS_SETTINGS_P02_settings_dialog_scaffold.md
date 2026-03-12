# GRAPHICS_SETTINGS P02: Settings Dialog Scaffold

## Objective
- Extract a reusable sectioned settings-dialog shell and add `GraphicsSettingsDialog` without regressing `WorkflowSettingsDialog`.

## Preconditions
- `P01` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- `P01` has already introduced the locked default graphics settings payload.

## Target Subsystems
- `ea_node_editor/ui/dialogs/sectioned_settings_dialog.py` (new)
- `ea_node_editor/ui/dialogs/workflow_settings_dialog.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py` (new)
- `ea_node_editor/ui/dialogs/__init__.py`
- `tests/test_settings_dialog_rc2.py`
- `tests/test_graphics_settings_dialog.py` (new)

## Required Behavior
- Extract the shared left-section-list/header/page-stack/button-row chrome into `sectioned_settings_dialog.py`.
- Keep `WorkflowSettingsDialog` constructor shape and `values()` behavior stable while refactoring it onto the shared shell.
- Add `GraphicsSettingsDialog` with sections `Canvas`, `Interaction`, and `Theme`.
- `GraphicsSettingsDialog` must expose `__init__(initial_settings: dict[str, Any] | None = None, parent=None)` and `values() -> dict[str, Any]`.
- `GraphicsSettingsDialog.values()` must round-trip the normalized graphics payload shape:
  - `canvas.show_grid`
  - `canvas.show_minimap`
  - `canvas.minimap_expanded`
  - `interaction.snap_to_grid`
  - `theme.theme_id`
- Theme choices in the dialog are locked to `stitch_dark` and `stitch_light`.
- Do not wire the new dialog into `ShellWindow` in this packet.

## Non-Goals
- No Settings menu wiring.
- No app-preferences controller integration beyond consuming the normalized defaults shape.
- No QML or runtime theme changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_settings_dialog_rc2 tests.test_graphics_settings_dialog -v`

## Acceptance Criteria
- `WorkflowSettingsDialog` tests continue to pass without API regressions.
- `GraphicsSettingsDialog` defaults and value round-trip tests pass.
- Shared dialog chrome is not copy-pasted between workflow and graphics dialogs.

## Handoff Notes
- `P03` wires `GraphicsSettingsDialog` into the Settings menu and shell/controller host surfaces.
