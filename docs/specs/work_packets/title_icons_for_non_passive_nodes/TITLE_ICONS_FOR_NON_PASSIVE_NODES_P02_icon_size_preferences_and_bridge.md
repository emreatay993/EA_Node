# TITLE_ICONS_FOR_NON_PASSIVE_NODES P02: Icon Size Preferences and Bridge

## Objective
- Add the nullable app-global `graph_node_icon_pixel_size_override` graphics typography preference and project the effective node-title icon size through the existing settings, shell, bridge, and shared QML typography path.

## Preconditions
- `P00` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- No later `TITLE_ICONS_FOR_NON_PASSIVE_NODES` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P02_icon_size_preferences_and_bridge_WRAPUP.md`

## Required Behavior
- Add `graphics.typography.graph_node_icon_pixel_size_override` with default `null`.
- Normalize the override as nullable integer:
  - `null` or missing remains `null`
  - non-null integers clamp to the inclusive `GRAPH_LABEL_PIXEL_SIZE_MIN..GRAPH_LABEL_PIXEL_SIZE_MAX` range
  - invalid values normalize to `null`
  - booleans do not count as integers
- Define the effective icon size as `graph_node_icon_pixel_size_override` when non-null, otherwise the normalized `graph_label_pixel_size`.
- Add a Graphics Settings `Theme` > `Typography` control that lets users leave icon size automatic or enable an explicit spinbox-backed override.
- Keep the control app-global and preference-backed. Do not add graph-theme-specific or per-node icon sizing.
- Thread the normalized nullable override and effective icon size through the existing app-preference controller, shell presenter/state, `ShellWindow`, context properties, graph canvas bridge, `GraphCanvasRootBindings.qml`, and `GraphSharedTypography.qml`.
- Expose a stable QML shared-typography property for P03 to consume, such as `nodeTitleIconPixelSize`, without requiring P03 to reimplement preference fallback or clamping.
- Reuse the existing graphics-preference change signal and scene refresh path. Do not introduce an icon-size-only invalidation channel.
- Add packet-owned regression tests whose names include `graph_node_icon_size` so the targeted verification commands below remain stable.

## Non-Goals
- No icon path resolution or `icon_source` payload work.
- No QML header Image rendering yet.
- No built-in asset migration.
- No new shared typography roles unrelated to node-title icon size.
- No persistence outside app preferences.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py -k graph_node_icon_size --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_main_window_shell.py tests/test_shell_run_controller.py tests/graph_track_b/qml_preference_bindings.py -k graph_node_icon_size --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k graph_node_icon_size --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P02_icon_size_preferences_and_bridge_WRAPUP.md`

## Acceptance Criteria
- Missing or invalid icon-size override values normalize to `null`.
- Explicit icon-size override values persist, clamp, and round-trip through Graphics Settings.
- When override is `null`, QML sees an effective node-title icon size matching `graph_label_pixel_size`.
- When override is non-null, QML sees the clamped override as the effective node-title icon size.
- The existing graph typography base-size behavior remains unchanged for text roles.
- Packet-owned `graph_node_icon_size` regressions pass.

## Handoff Notes
- `P03` consumes the shared QML effective icon-size property. Any rename or fallback change after this packet must inherit and update `tests/graph_track_b/qml_preference_bindings.py` and the bridge tests listed here.
- `P05` inherits this packet's preference proof when publishing final QA and traceability evidence.
