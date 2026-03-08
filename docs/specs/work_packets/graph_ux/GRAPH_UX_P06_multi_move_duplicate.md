# GRAPH_UX P06: Multi-Selection Move and Duplicate

## Objective
- Support moving selected nodes as a group and duplicating a selected subgraph inside the active workspace.

## Preconditions
- `P05` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- `P02` shared history support is available for grouped move and duplicate commands.

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/NodeCard.qml`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- When multiple nodes are selected, dragging any selected node moves the full selection while preserving relative offsets.
- Dragging an unselected node keeps the current single-node drag behavior.
- Group movement commits one grouped history entry on drag release.
- Add `Ctrl+D` duplicate for the active selection.
- Duplicate behavior:
  - duplicates selected nodes into the same workspace
  - duplicates only edges whose source and target are both selected
  - offsets the duplicated fragment by `(40, 40)` world units
  - assigns fresh node and edge ids
  - leaves titles unchanged unless existing runtime logic already normalizes them
  - selects the duplicated nodes after the command completes
- If there is no node selection, duplicate is a safe no-op.

## Non-Goals
- No clipboard integration.
- No cross-workspace duplication.
- No auto-layout after duplication.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Group drag preserves relative offsets across all moved nodes.
- Group drag produces one undoable move action.
- `Ctrl+D` duplicates only internal edges and selects the duplicates.
- Duplicate is a safe no-op with empty selection.
- Undo/redo covers both grouped move and duplicate behavior.

## Handoff Notes
- `P07` clipboard copy/cut/paste should reuse the same fragment-building logic as duplicate where practical.
- Keep grouped-move logic compatible with the existing node drag affordance and context menus.
