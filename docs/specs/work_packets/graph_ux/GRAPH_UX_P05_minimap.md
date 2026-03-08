# GRAPH_UX P05: Minimap Overlay

## Objective
- Add a minimap overlay that shows graph position at a glance and supports viewport navigation.

## Preconditions
- `P04` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- `P01` scene-bounds and visible-rect helpers are available for reuse.

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Add a bottom-right minimap overlay on the graph canvas.
- The minimap is expanded by default and includes a collapse toggle.
- Render node rectangles only; do not render edges.
- Show a distinct highlight for selected nodes.
- Show the current main-viewport rectangle inside the minimap.
- Clicking inside the minimap recenters the main camera on the clicked location.
- Dragging the minimap viewport rectangle pans the main canvas in real time.
- Compute minimap extents from workspace scene bounds, with a stable empty-graph fallback so the minimap never crashes.
- Keep the minimap visually lightweight so it does not interfere with existing graph interactions.

## Non-Goals
- No minimap-based selection or box-select.
- No edge rendering inside the minimap.
- No persistence of collapsed/expanded minimap state.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- The viewport rectangle updates when the main camera pans or zooms.
- Clicking the minimap recenters the main view.
- Dragging the minimap viewport rectangle pans the main view continuously.
- Selected-node highlighting is present in the minimap model/rendering path.
- Collapse/expand behavior is covered by tests and does not break the main canvas.

## Handoff Notes
- `P06` and later overlay work must preserve minimap input isolation so it does not steal unrelated canvas gestures.
- Reuse `P01` bounds helpers; do not introduce a second scene-extents implementation.
