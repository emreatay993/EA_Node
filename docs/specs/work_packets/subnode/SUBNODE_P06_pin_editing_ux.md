# SUBNODE P06: Pin Editing UX

## Objective
- Expose subnode pin nodes in the node library and inspector so users can refine shell ports after grouping.

## Preconditions
- `P05` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/nodes/builtins/subnode.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/*`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Add `Subnode Input` and `Subnode Output` to the node library under a dedicated `Subnode` category.
- Make the inspector fields for pin label, port kind, and data type the authoritative editing surface for pin nodes.
- Refresh shell port payloads immediately when a direct child pin node changes.
- Add a clear visual affordance on subnode shells that the node can be opened.
- Keep the library/controller path modular; do not push library data shaping into QML.

## Non-Goals
- No publishing to the custom workflow library yet.
- No import/export file format work.
- No execution changes.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Users can add pin nodes from the library inside a subnode scope.
- Editing a pin node updates the parent shell port label/kind/data type without reopening the scope.
- Subnode shells remain readable and visibly enterable in the graph canvas.

## Handoff Notes
- `P08` depends on the shell port payloads and pin editing semantics from this packet when showing custom workflow previews.
- Avoid hard-coding subnode-specific inspector logic into general library search or package plumbing.
