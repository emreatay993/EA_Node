# TOOLTIP_MANAGER P02: View Menu and Tooltip Surface Adoption

## Objective
- Add the live `View > Show Tooltips` action and apply the global informational-tooltip policy to the currently discovered tooltip surfaces in shell widgets, graph QML, recent-project actions, and the graph-theme editor button.

## Preconditions
- `P00` is marked `PASS` in [TOOLTIP_MANAGER_STATUS.md](./TOOLTIP_MANAGER_STATUS.md).
- `P01` is marked `PASS` in [TOOLTIP_MANAGER_STATUS.md](./TOOLTIP_MANAGER_STATUS.md).
- No later `TOOLTIP_MANAGER` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceButton.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorButton.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorColorField.qml`
- `ea_node_editor/ui_qml/components/shell/ShellButton.qml`
- `ea_node_editor/ui_qml/components/shell/ShellCollapsibleSidePane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellCreateButton.qml`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfaceButton.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorButton.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorColorField.qml`
- `ea_node_editor/ui_qml/components/shell/ShellButton.qml`
- `ea_node_editor/ui_qml/components/shell/ShellCollapsibleSidePane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellCreateButton.qml`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md`
- `docs/specs/work_packets/tooltip_manager/P02_view_menu_and_tooltip_surface_adoption_WRAPUP.md`

## Required Behavior
- Add a checkable `Show Tooltips` action under the `View` menu near the existing `Port Labels` action.
- Initialize the action from the resolved `graphics.shell.show_tooltips` preference exposed by P01.
- Toggling the action updates the authoritative shell preference path and persists through the existing app-preferences pipeline.
- Keep the action checked state synchronized when preferences are applied or refreshed through the shell.
- Project `graphics_show_tooltips` through the graph canvas bridge/root binding if graph QML needs that bridge to consume the shell policy.
- Gate the current informational tooltip surfaces in:
  - recent-project actions in `window_actions.py`
  - graph-theme editor button tooltip
  - `GraphSurfaceButton.qml`
  - `GraphCanvasMinimapOverlay.qml`
  - `InspectorButton.qml`
  - `InspectorColorField.qml`
  - `ShellButton.qml`
  - `ShellCollapsibleSidePane.qml`
  - `ShellCreateButton.qml`
  - informational port-label or graph-surface help in `GraphNodePortsLayer.qml`
- Preserve inactive-port warning explanations in `GraphNodePortsLayer.qml` even when informational tooltips are disabled.
- Add focused regressions for action state, preference writes, bridge projection, informational tooltip gating, and preserved warning tooltip behavior.

## Non-Goals
- No new preference schema work beyond consuming the `P01` contract.
- No collision-avoidance Graphics Settings help-copy changes.
- No audit of non-tooltip hover UI or plain text hints that do not use Qt/QML tooltip APIs.
- No per-surface or per-feature tooltip settings.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/bridge_support.py tests/test_graph_theme_editor_dialog.py --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/graph_track_b/qml_preference_rendering_suite.py --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py -k tooltip --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/tooltip_manager/P02_view_menu_and_tooltip_surface_adoption_WRAPUP.md`

## Acceptance Criteria
- `View > Show Tooltips` appears as a checkable action near `Port Labels`.
- Toggling the action writes and persists `graphics.shell.show_tooltips`.
- Shell/QML and graph/QML informational tooltip surfaces hide when the policy is `false` and show when it is `true`.
- Recent-project and graph-theme editor button tooltips follow the policy.
- Inactive-port warning tooltips remain visible when informational tooltips are disabled.
- Packet-owned tests prove both the Python action path and QML binding path.

## Handoff Notes
- This packet consumes the `P01` `graphics_show_tooltips` contract. If the bridge projection requires renaming or reshaping that contract, inherit and update the relevant `P01` regression anchor instead of leaving stale assertions.
- `P03` may run in parallel after `P01` because it owns the modal Graphics Settings copy path, not the shell menu or QML-surface adoption files.
