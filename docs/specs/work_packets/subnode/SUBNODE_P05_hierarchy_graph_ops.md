# SUBNODE P05: Hierarchy Graph Ops

## Objective
- Retrofit the rest of the graph-area operations so they respect scope boundaries and subtree semantics.

## Preconditions
- `P04` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/hierarchy.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Make selection, delete, duplicate, clipboard, drag-move, drag-connect, layout, minimap, framing, search jump, and failure focus scope-aware.
- Treat a selected subnode shell as a subtree root for duplicate/copy/cut operations.
- Reuse one subtree fragment builder/inserter for duplicate, clipboard, and later custom workflow publishing.
- Make search/failure focus open the required ancestor scopes instead of relying on legacy parent-chain reveal assumptions.
- Keep scope filtering out of QML business logic; graph and controller layers should expose the needed scoped payloads.

## Non-Goals
- No new pin inspector affordances beyond packet `P06`.
- No execution compiler behavior.
- No publish/import/export UI yet.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Copy/duplicate of a subnode shell preserves its full descendant subtree and only the internal edges valid for that subtree fragment.
- Search and failure focus navigate into nested scopes correctly.
- Layout/minimap/framing operations only act on the currently visible scope.

## Handoff Notes
- `P08` must reuse the subtree fragment helper from this packet when saving and placing custom workflow snapshots.
- Do not duplicate fragment cloning logic in the controller layer.
