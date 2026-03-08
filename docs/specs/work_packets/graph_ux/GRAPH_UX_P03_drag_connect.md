# GRAPH_UX P03: Drag-to-Connect Ports

## Objective
- Make drag-to-connect the primary port wiring interaction while keeping click-to-click connect as a fallback.

## Preconditions
- `P02` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- Undo/redo exists so successful edge creation can be recorded through the shared history path.

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/NodeCard.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_track_b.py`

## Required Behavior
- Left-press on a port starts a potential wire drag.
- Moving beyond the existing small drag threshold converts the gesture into a live connection drag.
- While dragging, show a preview wire from the source port to the current pointer location.
- Highlight only compatible drop targets using the existing port-kind and data-type compatibility rules.
- Releasing over a compatible target creates the edge through the existing connection request path.
- Releasing on empty space, on an incompatible target, or pressing `Esc` cancels the wire drag without mutating graph state.
- A simple click without entering drag mode must preserve the current click-to-click connection fallback.
- Keep right-click context menus and normal node dragging behavior unchanged.

## Non-Goals
- No reroute nodes.
- No edge waypoint editing.
- No changes to compatibility rules themselves.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Drag connect succeeds for compatible ports in either source/target selection order.
- Incompatible targets are visibly rejected and do not create edges.
- Duplicate-edge prevention still works.
- Canceling a wire drag fully clears preview/highlight state.
- Click-to-click connection still works when the user clicks ports without dragging.

## Handoff Notes
- `P04` and `P05` should not break the new wire-drag state machine when adding overlays.
- Reuse the existing compatibility helpers instead of adding a second validation path.
