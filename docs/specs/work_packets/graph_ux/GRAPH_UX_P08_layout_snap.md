# GRAPH_UX P08: Layout Tools and Snap-to-Grid

## Objective
- Add selection layout tools and optional snap-to-grid behavior for graph editing.

## Preconditions
- `P07` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- `P02` history support exists for grouped move operations.

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Add layout actions for the current selection:
  - Align Left
  - Align Right
  - Align Top
  - Align Bottom
  - Distribute Horizontally
  - Distribute Vertically
- Layout actions operate on selected nodes only and are safe no-ops for fewer than `2` selected nodes.
- Alignment semantics:
  - left/right use node bounding-box left/right edges
  - top/bottom use node bounding-box top/bottom edges
- Distribution semantics:
  - sort nodes by current axis position
  - keep the outermost two nodes fixed
  - evenly distribute the gaps between node bounding boxes along the chosen axis
- Add a runtime `Snap to Grid` toggle, default `off`.
- Grid size is `20` world units.
- When snap is enabled, live drag previews and final committed positions snap to grid.
- When snap is enabled, layout action results also snap before commit.
- All layout commands and snap-adjusted moves must create grouped undoable history entries.

## Non-Goals
- No automatic graph-wide layout.
- No persistent grid/snap preferences.
- No comment/frame annotations.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Each layout action moves the selected nodes according to the defined alignment/distribution semantics.
- Actions are safe no-ops for zero or one selected node.
- Snap-to-grid affects live drag and final committed positions when enabled and leaves behavior unchanged when disabled.
- Undo/redo covers layout actions and snap-adjusted moves.
- The snap toggle defaults to off for new app sessions.

## Handoff Notes
- This packet closes the current Graph UX roadmap. Later follow-on work such as comments/frames, reroute nodes, or run-state overlays should start a new packet set instead of extending this one ad hoc.
