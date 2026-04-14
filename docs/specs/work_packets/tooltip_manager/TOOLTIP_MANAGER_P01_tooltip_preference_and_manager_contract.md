# TOOLTIP_MANAGER P01: Tooltip Preference and Manager Contract

## Objective
- Add the persisted tooltip policy and the thin shell-owned manager contract that defines informational tooltip visibility while preserving warning/inactive tooltip behavior.

## Preconditions
- `P00` is marked `PASS` in [TOOLTIP_MANAGER_STATUS.md](./TOOLTIP_MANAGER_STATUS.md).
- No later `TOOLTIP_MANAGER` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/tooltip_manager.py`
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graphics_settings_preferences.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/tooltip_manager.py`
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graphics_settings_preferences.py`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md`
- `docs/specs/work_packets/tooltip_manager/P01_tooltip_preference_and_manager_contract_WRAPUP.md`

## Required Behavior
- Add `graphics.shell.show_tooltips: bool` to the app graphics-preferences schema with default `true`.
- Normalize missing and invalid payloads to `true`.
- Persist and reload `graphics.shell.show_tooltips` through the existing app-preferences pipeline.
- Mirror the resolved preference into shell UI state.
- Expose a `graphics_show_tooltips` property from `ShellWindow` for QML consumers.
- Add a `set_graphics_show_tooltips` slot or equivalent shell entry point that updates runtime state through the same preference path later used by the View action.
- Add a small shell-owned `TooltipManager` that exposes `info_tooltips_enabled` and keeps warning tooltip visibility independent of the global informational-tooltip toggle.
- Add a focused action-sync helper surface if the shell already centralizes view-action state there, but do not create the actual `View > Show Tooltips` action in this packet.
- Extend `tests/test_graphics_settings_preferences.py` for defaulting, invalid payload normalization, persistence, and host application of `graphics.shell.show_tooltips`.
- Name new tooltip-policy regression tests with `tooltip` so the review gate remains stable.

## Non-Goals
- No `View > Show Tooltips` menu action in this packet.
- No QML tooltip-surface adoption in this packet.
- No collision-avoidance help-copy changes in this packet.
- No per-surface or per-feature tooltip settings.
- No project-file persistence or `.sfe` schema migration.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k tooltip --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/tooltip_manager/P01_tooltip_preference_and_manager_contract_WRAPUP.md`
- `ea_node_editor/ui/shell/tooltip_manager.py`
- `tests/test_graphics_settings_preferences.py`

## Acceptance Criteria
- Existing and new users resolve `graphics.shell.show_tooltips` to `true` when the key is missing.
- Invalid `graphics.shell.show_tooltips` payloads normalize to `true` without corrupting the rest of graphics settings.
- Saving, loading, and applying app preferences preserves explicit `true` and `false` values.
- `ShellWindow.graphics_show_tooltips` reflects the resolved runtime preference.
- `TooltipManager.info_tooltips_enabled` follows the global preference while warning/inactive tooltip behavior remains available to later consumers.

## Handoff Notes
- `P02` consumes `graphics_show_tooltips` for menu synchronization and QML tooltip-surface gating. If P01 changes that property name, path, or setter contract, P02 must inherit and update the P01-owned preference regression in `tests/test_graphics_settings_preferences.py`.
- `P03` consumes the current tooltip policy when constructing `GraphicsSettingsDialog`. If P01 changes how the host reads the policy, P03 must update its dialog tests and host handoff accordingly.
