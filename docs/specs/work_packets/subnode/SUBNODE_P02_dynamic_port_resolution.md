# SUBNODE P02: Dynamic Port Resolution

## Objective
- Introduce the subnode shell/pin node types and route every port lookup through one shared effective-port resolver.

## Preconditions
- `P01` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/nodes/builtins/subnode.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_graph_track_b.py`

## Required Behavior
- Add built-in node types `core.subnode`, `core.subnode_input`, and `core.subnode_output`.
- Introduce one pure effective-port module that resolves ports for normal nodes, subnode shells, and pin nodes.
- Make `core.subnode` derive its outer ports from direct child pin nodes sorted by `(y, x, node_id)`.
- Make pin node properties authoritative for label, kind, and data type; flow kinds normalize their data type to `any`.
- Route node sizing, edge routing, compatibility checks, normalization, and default-port lookup through the shared resolver.

## Non-Goals
- No breadcrumb UI or scope navigation.
- No group/ungroup transform yet.
- No execution flattening or custom workflow library behavior.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_serializer -v`

## Acceptance Criteria
- Subnode shell ports reflect direct child pin nodes only.
- Existing non-subnode nodes keep their current port behavior.
- No duplicate port-resolution logic remains in graph interactions, routing, or normalization code paths.

## Handoff Notes
- `P03` must reuse the same resolver when the canvas becomes scope-aware.
- `P04` pin derivation must target the shell port ordering rules introduced here.
