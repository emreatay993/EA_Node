# Tooltip Manager and Collision-Avoidance Help

## Summary
- Add a shell-wide tooltip policy that persists in `graphics.shell.show_tooltips`, appears as `View > Show Tooltips`, disables informational tooltips across the current app surfaces, and keeps warning/inactive-state explanations visible.
- Use that policy for the first rollout by adding informational tooltips to the collision-avoidance controls in Graphics Settings.

## Key Changes
- Preferences and runtime state:
  add `graphics.shell.show_tooltips` with default `true`, normalize/persist it with the existing app-preferences pipeline, mirror it into shell UI state, and expose it as `graphics_show_tooltips` from the shell/QML bridge.
- Tooltip manager:
  add a small shared `TooltipManager` owned by the shell window that centralizes `info` vs `warning` visibility rules; the global toggle controls informational tooltips only.
- View menu and existing tooltip sites:
  add a checkable `Show Tooltips` action next to `Port Labels`, sync it from resolved preferences, and gate the currently discovered tooltip surfaces in shell QML, graph QML, recent-project actions, and the existing graph-theme editor button tooltip.
- Collision-avoidance help:
  add concise control-only tooltips for the seven expand-collision controls in `GraphicsSettingsDialog`, using the current tooltip-enabled state when the modal dialog is created.

## Public Interface Changes
- New persistent preference: `graphics.shell.show_tooltips: bool` with default `true`.
- New shell/QML property: `graphics_show_tooltips` on `ShellWindow` and `GraphCanvasStateBridge`.
- New View menu action: `Show Tooltips` (checkable, persisted).
- Internal dialog constructor addition: `GraphicsSettingsDialog(..., tooltips_enabled: bool = True)`.

## Execution Tasks

### T01 Tooltip Preference and Manager Contract
- Goal: add the persisted tooltip policy and a thin shell-owned manager that defines informational vs warning tooltip behavior.
- Preconditions: `none`
- Conservative write scope: `ea_node_editor/settings.py`, `ea_node_editor/app_preferences.py`, shell presenter/UI-state files, shell window state helpers, and one new tooltip-manager module.
- Deliverables: default schema key, normalization/load/store support, `graphics_show_tooltips` shell property, `set_graphics_show_tooltips` slot, action-sync helper, and a `TooltipManager` with `info_tooltips_enabled` plus warning passthrough.
- Verification: extend `tests/test_graphics_settings_preferences.py` for defaulting, invalid payload normalization, persistence, and host application of `graphics.shell.show_tooltips`.
- Non-goals: no per-surface or per-feature tooltip settings.
- Packetization notes: direct `P01`; later tasks consume this contract without reopening the schema.

### T02 View Menu and Current Tooltip Adoption
- Goal: make `View > Show Tooltips` live and apply it to every current informational tooltip surface already in the repo.
- Preconditions: `T01`
- Conservative write scope: `ea_node_editor/ui/shell/window_actions.py`, `ea_node_editor/ui/shell/window_state/run_and_style_state.py`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, and the currently discovered tooltip-bearing QML/widget files only.
- Deliverables: checkable View action near `Port Labels`; recent-project hover text respects the flag; informational QML tooltips bind to `graphics_show_tooltips`; inactive-port warning tooltips in `GraphNodePortsLayer.qml` remain visible even when informational tooltips are off.
- Verification: add focused shell/QML regression for action state, preference writes, bridge projection, informational port-label tooltip gating, and preserved inactive-port warning tooltip behavior.
- Non-goals: no audit of non-tooltip hover UI or plain text hints that do not use Qt/QML tooltip APIs.
- Packetization notes: direct `P02`; keep adoption limited to the currently discovered tooltip files.

### T03 Collision-Avoidance Settings Tooltips
- Goal: add first-wave help text for expand-collision settings, using the global tooltip policy.
- Preconditions: `T01`
- Conservative write scope: `ea_node_editor/ui/dialogs/graphics_settings_dialog.py` and `ea_node_editor/ui/shell/host_presenter.py`.
- Deliverables: control-only tooltips for enabled, strategy, animate, scope, gap preset, reach mode, and local radius preset; dialog host passes `tooltips_enabled` from the current tooltip policy; no label-row refactor.
- Verification: extend `tests/test_graphics_settings_dialog.py` to assert the new tooltips exist by default, disappear with `tooltips_enabled=False`, and do not change settings round-trip behavior.
- Non-goals: no label tooltips, no section-title tooltips, no copy pass over unrelated graphics settings.
- Packetization notes: can merge with `T01` if implemented as one small change, but keep the dialog copy surface isolated if packetized later.

## Work Packet Conversion Map
1. `P00 Bootstrap`: tracking/docs only if packetized.
2. `P01 Tooltip Preference and Manager Contract`: derived from `T01`.
3. `P02 View Menu and Tooltip Surface Adoption`: derived from `T02`.
4. `P03 Collision-Avoidance Tooltip Copy`: derived from `T03`.

## Test Plan
- Extend `tests/test_graphics_settings_preferences.py` for `graphics.shell.show_tooltips`.
- Extend `tests/test_graphics_settings_dialog.py` for collision-avoidance control tooltips on/off.
- Add or extend a focused main-window shell test for the new `Show Tooltips` action and persisted checked state.
- Extend `tests/graph_track_b/qml_preference_bindings.py` with `graphics_show_tooltips` projection and graph-tooltip gating coverage.
- Manual smoke: turn tooltips off, confirm shell/button/minimap/port-label help disappears, confirm inactive-port reason still shows, restart and confirm persistence, then open Graphics Settings and verify collision-avoidance controls follow the saved state.

## Assumptions
- “Keep warnings” means informational/help tooltips are hidden when off, but warning/inactive-state explanations remain visible.
- Existing and new users default to `graphics.shell.show_tooltips = true` if the key is missing.
- The v1 adoption set is the currently discovered tooltip files only: `window_actions.py`, `graph_theme_editor_dialog.py`, `GraphNodePortsLayer.qml`, `GraphSurfaceButton.qml`, `GraphCanvasMinimapOverlay.qml`, `InspectorButton.qml`, `InspectorColorField.qml`, `ShellButton.qml`, `ShellCollapsibleSidePane.qml`, and `ShellCreateButton.qml`.
- Graphics Settings remains modal, so v1 applies tooltip state at dialog construction time rather than live-updating an already-open dialog.
