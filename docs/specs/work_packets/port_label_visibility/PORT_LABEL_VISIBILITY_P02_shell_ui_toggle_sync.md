# PORT_LABEL_VISIBILITY P02: Shell UI Toggle Sync

## Objective
- Add the shared `Port Labels` toggle to both `View` and `Graphics Settings > Canvas`, keep those surfaces synchronized over the `P01` preference path, and trigger an immediate active-scene rebuild when the preference changes.

## Preconditions
- `P00` and `P01` are marked `PASS` in [PORT_LABEL_VISIBILITY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_STATUS.md).
- No later `PORT_LABEL_VISIBILITY` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Conservative Write Scope
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/port_label_visibility/P02_shell_ui_toggle_sync_WRAPUP.md`

## Required Behavior
- Add a checkable `View > Port Labels` action and place it with the other View visibility controls.
- Add the same `show_port_labels` field to the Graphics Settings Canvas page and make the dialog round-trip it through `set_values()` and `values()` without regressing the existing graphics/theme fields.
- Reuse the persistent getter/setter path from `P01`; do not add a second ad hoc preference branch for either the menu action or the dialog.
- Keep the View action, dialog control, and persisted runtime state synchronized so opening or accepting Graphics Settings cannot reset the menu toggle.
- When the preference changes, rebuild the active workspace scene payload immediately so later metric packets refresh without requiring a manual canvas mutation.
- Preserve current visible label behavior for now. This packet owns the UI/editor surfaces and the rebuild hook, not the scene metric or QML presentation change.

## Non-Goals
- No preference-schema or bridge-surface redesign beyond what `P01` already introduced.
- No standard-node minimum-width or resize-clamp changes yet. `P03` owns those.
- No tooltip-only or inline-label hide behavior yet. `P04` owns the QML rollout.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/port_label_visibility/P02_shell_ui_toggle_sync_WRAPUP.md`

## Acceptance Criteria
- `View > Port Labels` and `Graphics Settings > Canvas` both edit the same persisted `show_port_labels` preference.
- Reopening the dialog or restarting the window preserves the last saved state.
- Toggling the preference triggers the packet-owned active-scene rebuild hook immediately.
- No width-policy or QML label-presentation behavior changes are intentionally introduced in this packet.

## Handoff Notes
- Record the final action object names, dialog control names, and the scene-rebuild hook location in the wrap-up so `P03` and `P04` can rely on them directly.
- If the View action must connect through an intermediate helper for checked-state sync, keep that helper packet-local and note the narrow contract plainly.
