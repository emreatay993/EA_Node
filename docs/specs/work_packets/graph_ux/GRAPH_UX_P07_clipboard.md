# GRAPH_UX P07: Graph Clipboard Workflows

## Objective
- Add copy, cut, and paste workflows for selected graph fragments.

## Preconditions
- `P06` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- `P02` history support and `P06` fragment duplication logic are available for reuse.

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- a small runtime clipboard-fragment helper under `ea_node_editor/ui/shell/` if needed
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Add shortcuts:
  - `Ctrl+C` -> copy selection
  - `Ctrl+X` -> cut selection
  - `Ctrl+V` -> paste clipboard fragment
- Clipboard payload format is an internal JSON fragment representing:
  - selected nodes
  - edges whose endpoints are both inside the selection
- Use a dedicated internal clipboard mime type and/or clipboard text payload that is fully self-contained JSON.
- Copy does not mutate graph state.
- Cut copies first, then deletes through the same semantic delete path used elsewhere so undo/redo works.
- Paste behavior:
  - pastes into the active workspace only
  - creates fresh node and edge ids
  - preserves relative offsets from the copied fragment
  - recenters the pasted fragment on the current viewport center
  - selects the pasted nodes after completion
- If the clipboard payload is missing, invalid, or from a foreign format, paste is a safe no-op.

## Non-Goals
- No interoperability with external node-editor formats.
- No persistence changes.
- No clipboard history UI.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_workspace_library_controller_unit tests.test_main_window_shell -v`

## Acceptance Criteria
- Copy and paste preserve node/edge counts for fully internal fragments.
- External edges connected to the selection are excluded from the clipboard fragment.
- Cut is undoable and redoable as a single semantic action.
- Paste into another workspace succeeds and selects the pasted nodes.
- Invalid clipboard contents do not raise or mutate graph state.

## Handoff Notes
- `P08` layout tools should operate on pasted selections without needing clipboard-specific exceptions.
- Reuse fragment serialization logic from duplicate where possible instead of maintaining two incompatible formats.
