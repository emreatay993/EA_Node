# TOOLTIP_MANAGER P03: Collision-Avoidance Tooltip Copy

## Objective
- Add first-wave help text for the expand-collision settings in `GraphicsSettingsDialog` and make the modal dialog honor the global tooltip policy when it is constructed.

## Preconditions
- `P00` is marked `PASS` in [TOOLTIP_MANAGER_STATUS.md](./TOOLTIP_MANAGER_STATUS.md).
- `P01` is marked `PASS` in [TOOLTIP_MANAGER_STATUS.md](./TOOLTIP_MANAGER_STATUS.md).
- No later `TOOLTIP_MANAGER` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `tests/test_graphics_settings_dialog.py`

## Conservative Write Scope
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `tests/test_graphics_settings_dialog.py`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md`
- `docs/specs/work_packets/tooltip_manager/P03_collision_avoidance_tooltip_copy_WRAPUP.md`

## Required Behavior
- Add `tooltips_enabled: bool = True` to `GraphicsSettingsDialog` construction without breaking existing call sites.
- Use `tooltips_enabled` to apply or suppress control-only informational tooltips when the modal dialog is created.
- Add concise tooltips for these expand-collision controls:
  - enabled
  - strategy
  - animate
  - scope
  - gap preset
  - reach mode
  - local radius preset
- Keep warning or validation text behavior unchanged.
- Update the shell host presenter to pass the current global tooltip policy when opening Graphics Settings.
- Extend `tests/test_graphics_settings_dialog.py` to prove tooltips are present by default, suppressed with `tooltips_enabled=False`, and do not change settings round-trip behavior.
- Name new dialog tooltip tests with `tooltip` so the review gate remains stable.

## Non-Goals
- No label-row refactor.
- No label tooltips and no section-title tooltips.
- No copy pass over unrelated graphics settings.
- No live-update behavior for an already-open modal Graphics Settings dialog.
- No menu-action, bridge, or graph-QML tooltip-surface work.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py -k tooltip --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/tooltip_manager/P03_collision_avoidance_tooltip_copy_WRAPUP.md`

## Acceptance Criteria
- The seven expand-collision controls have concise informational tooltips by default.
- `GraphicsSettingsDialog(..., tooltips_enabled=False)` suppresses those informational tooltips.
- The shell host presenter passes the current global tooltip policy when opening Graphics Settings.
- Existing settings round-trip behavior remains unchanged.
- The dialog remains modal and does not promise live updates while already open.

## Handoff Notes
- This packet consumes the `P01` policy surface but does not depend on the `P02` View action or QML adoption work.
- If the host-presenter policy path changes in P01, update the P03 dialog test and host handoff inside this packet rather than duplicating a second policy lookup.
