# GRAPHICS_PERFORMANCE_MODES P02: Graphics Settings Mode UI

## Objective
- Add the persistent `Full Fidelity` / `Max Performance` selector to Graphics Settings in the existing Theme/Renderer area without disturbing the current settings-dialog architecture.

## Preconditions
- `P00` and `P01` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- existing graphics-settings shell/dialog plumbing
- targeted dialog and shell graphics-settings regression tests

## Conservative Write Scope
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_shell_theme.py`
- `tests/test_graphics_settings_preferences.py`
- `docs/specs/work_packets/graphics_performance_modes/P02_graphics_settings_mode_ui_WRAPUP.md`

## Required Behavior
- Add a new Performance card on the Graphics Settings Theme page beneath the existing Renderer card.
- Present the two locked mode options as `Full Fidelity` and `Max Performance` with concise explanatory copy aligned to the approved v1 defaults.
- Make the dialog round-trip the new performance-mode field through `set_values()` and `values()` without regressing the current graphics/theme fields.
- Reuse the persistent runtime mutation path from `P01`; do not add a second ad hoc persistence flow for the dialog.
- Reopening the dialog after persistence must reflect the saved mode.
- Keep the dialog structure modular and visually consistent with the current section/card styling.

## Non-Goals
- No status-strip quick toggle yet. `P03` owns that.
- No canvas-performance behavior changes yet. `P04` and `P05` own those.
- No new automatic heuristics, recommendations, or auto-switching behavior.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py --ignore=venv -k "graphics_settings" -q`
3. `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P02_graphics_settings_mode_ui_WRAPUP.md`

## Acceptance Criteria
- Graphics Settings exposes the two approved mode choices in the Theme/Renderer area.
- Accepting the dialog persists the selected mode and routes it through the existing graphics-settings application flow.
- Dialog round-trip and shell graphics-settings regressions pass without breaking current theme/renderer/minimap/shadow settings.
- No extra quick-toggle surface or automatic mode switching is introduced in this packet.

## Handoff Notes
- Record the final widget/control ids and any user-facing copy in the wrap-up so `P03` can keep the status-strip labels aligned.
- If the packet had to touch shell dialog-wiring code, keep that change narrow and note the reused setter path from `P01`.
