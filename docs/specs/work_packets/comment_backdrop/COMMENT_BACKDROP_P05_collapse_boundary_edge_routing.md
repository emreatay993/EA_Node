# COMMENT_BACKDROP P05: Collapse + Boundary Edge Routing

## Objective
- Hide descendant content when a backdrop collapses and reroute boundary edges to the collapsed backdrop perimeter without corrupting the underlying graph document.

## Preconditions
- `P04` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_comment_backdrop_collapse.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_comment_backdrop_collapse.py`
- `docs/specs/work_packets/comment_backdrop/P05_collapse_boundary_edge_routing_WRAPUP.md`

## Required Behavior
- Collapsing a backdrop must hide descendant nodes and descendant backdrops from the active scene payload while preserving their stored graph-model state.
- Fully internal edges whose visible endpoints both resolve inside the same collapsed backdrop must be suppressed while that backdrop stays collapsed.
- Boundary edges that cross a collapsed backdrop boundary must reroute hidden endpoints to the collapsed backdrop perimeter.
- Nested collapsed backdrops must resolve proxy endpoints deterministically to the nearest visible collapsed ancestor, and if both hidden endpoints collapse into the same visible backdrop the edge must stay suppressed.
- Expanding a backdrop must restore descendants and edge routing without rewriting stored node positions, direct-owner rules, or edge payload identities.

## Non-Goals
- No shell shortcut or inline editing changes yet. `P06` owns those user-facing affordances.
- No clipboard, delete, or load semantics yet. `P07` owns those lifecycle rules.
- No requirements or traceability updates yet. `P08` owns docs closeout.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_collapse.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_collapse.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P05_collapse_boundary_edge_routing_WRAPUP.md`

## Acceptance Criteria
- Collapsed backdrops hide descendant content without mutating the authored graph document.
- Fully internal edges disappear while crossing edges reroute to the collapsed backdrop perimeter.
- Nested collapse chains choose the correct visible proxy ancestor for routed endpoints.
- Expanding a backdrop restores visible descendants and edge geometry without ownership drift.

## Handoff Notes
- `P07` may assume the collapsed descendant set and boundary-edge classification are already available or easy to reuse.
- Record the routed-endpoint payload contract in the wrap-up so later packets do not invent a second hidden-endpoint representation.
