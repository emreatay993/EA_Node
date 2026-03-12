# GRAPHICS_SETTINGS P04: Canvas Preferences Binding

## Objective
- Bind persisted graphics preferences into the existing grid, minimap, and snap-to-grid runtime flows.

## Preconditions
- `P03` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- `ShellWindow` already exposes the graphics preference properties introduced in `P03`.

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_search_scope_state.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `tests/test_graph_track_b.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Required Behavior
- Bind `GraphCanvasBackground` grid rendering to `graphics_show_grid`.
- Bind minimap visibility to `graphics_show_minimap`.
- Initialize the minimap expanded state from `graphics_minimap_expanded`.
- Keep `toggleMinimapExpanded()` on `GraphCanvas` intact, but route expanded-state persistence back through `ShellWindow` so app preferences stay authoritative.
- Restore `snap_to_grid_enabled` from app preferences during shell startup.
- Persist snap-to-grid state when `set_snap_to_grid_enabled()` changes it, without changing the existing public method signature.
- Trigger the existing grid/minimap redraw/update paths when the bound preferences change.
- Keep the current graph canvas integration contract methods stable.

## Non-Goals
- No theme token or QML neutral-color refactor.
- No semantic node/edge/port color changes.
- No workflow settings changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Grid visibility can be toggled from preferences without breaking canvas rendering.
- Minimap visibility and expanded/collapsed state persist across window restarts.
- Snap-to-grid default/runtime behavior reflects the persisted app preference while keeping existing shell action behavior intact.

## Handoff Notes
- `P05` adds the shared theme registry, runtime stylesheet application, and the QML palette bridge used by later theme-adoption packets.
