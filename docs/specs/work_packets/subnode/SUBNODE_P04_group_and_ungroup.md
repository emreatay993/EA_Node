# SUBNODE P04: Group And Ungroup

## Objective
- Add the graph transform that groups visible same-scope selections into a new subnode and reverses that transform.

## Preconditions
- `P03` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/hierarchy.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Add `Ctrl+G` to group a multi-selection when every selected visible root shares the same direct parent scope.
- Create a new `core.subnode` shell at the selection bounds origin and move the selected visible roots under it without changing their local coordinates.
- Derive input/output pin nodes from boundary-crossing edges and rewire outer edges through the shell ports and inner pin nodes.
- Add `Ctrl+Shift+G` to ungroup the selected subnode shell, restore the prior wiring shape, and remove the shell plus its direct pin nodes.
- Record grouping and ungrouping as one undoable history entry each.

## Non-Goals
- No clipboard/duplicate/search hierarchy retrofits yet.
- No pin inspector editing beyond what `P02` already exposes internally.
- No execution flattening or custom workflow publishing.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Grouping is rejected across mixed scopes.
- Boundary pins are derived deterministically and shell rewiring is valid.
- Ungroup restores nodes to the original parent scope and removes the generated shell/pin nodes cleanly.

## Handoff Notes
- `P05` must reuse the subtree fragment and transform helpers from this packet rather than reimplementing copy/duplicate logic.
- Keep pin naming deterministic because `P08` will cache shell-port previews from these definitions.
