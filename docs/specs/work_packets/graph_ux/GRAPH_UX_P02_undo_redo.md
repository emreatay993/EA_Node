# GRAPH_UX P02: Runtime Undo/Redo Per Workspace

## Objective
- Add runtime-only undo/redo stacks isolated per workspace so graph edits are reversible.

## Preconditions
- `P01` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- `P01` camera helpers remain the canonical way to restore/focus view state.

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/graph_interactions.py`
- a new runtime history helper under `ea_node_editor/ui/shell/` if needed
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Add per-workspace undo and redo stacks that are runtime-only and never serialized into `.sfe`.
- Clear redo history whenever a new forward mutation is committed.
- Reset all history stacks on new project, open project, and session restore from disk.
- New workspaces and duplicated workspaces start with empty history stacks.
- Record one semantic history entry for each committed action type:
  - add node
  - remove node
  - add edge
  - remove edge
  - rename node
  - collapse toggle
  - exposed-port toggle
  - property edit
  - delete-selected
  - node move
- Node drag must coalesce into a single move entry committed on drag release, not one entry per mouse move.
- Multi-object actions created through one user command must undo and redo as a single grouped operation.
- Add shell actions and shortcuts:
  - `Ctrl+Z` -> undo
  - `Ctrl+Shift+Z` -> redo
  - `Ctrl+Y` -> redo

## Non-Goals
- No persistence schema changes.
- No clipboard support.
- No command-history UI panel.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_graph_track_b tests.test_workspace_library_controller_unit tests.test_main_window_shell -v`

## Acceptance Criteria
- Each listed mutation type round-trips through undo and redo without corrupting graph state.
- Undo/redo stacks are isolated per workspace.
- Dragging a node produces one undoable move entry.
- Redo is cleared by any new forward mutation after an undo.
- Shortcuts are wired and covered by tests.

## Handoff Notes
- `P06`, `P07`, and `P08` must register grouped history actions through the same runtime history layer.
- Do not persist history state or add it to project documents.
