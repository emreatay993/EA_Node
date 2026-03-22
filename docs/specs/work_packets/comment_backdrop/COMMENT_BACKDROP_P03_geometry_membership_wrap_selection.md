# COMMENT_BACKDROP P03: Geometry Membership + Wrap Selection

## Objective
- Add derived geometry-owned membership, nested backdrop ownership, and the backend wrap-selection transaction that later shell and keyboard affordances will reuse.

## Preconditions
- `P02` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/graph/comment_backdrop*.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `tests/test_comment_backdrop_membership.py`

## Conservative Write Scope
- `ea_node_editor/graph/comment_backdrop*.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `tests/test_comment_backdrop_membership.py`
- `docs/specs/work_packets/comment_backdrop/P03_geometry_membership_wrap_selection_WRAPUP.md`

## Required Behavior
- Add authoritative direct-owner computation for backdrop membership:
  - only candidates in the same scope and parent chain may be owned
  - full containment is required
  - smallest containing backdrop wins
  - nested backdrops are allowed
  - partial overlap never counts
- Keep ownership derived only. Do not persist member lists or ownership ids in project data.
- Recompute ownership on scene rebuild, on explicit refresh, and after node or backdrop geometry changes exposed by the current bridge and history paths.
- Publish packet-owned derived payload metadata needed by later packets for nesting depth, descendant lookup, and collapse/routing behavior.
- Add a backend transaction that creates a comment backdrop around an explicit node-id set using `32px` padding and a minimum size of `240x160`, but do not wire keyboard or menu affordances yet.

## Non-Goals
- No shell shortcut, menu action, or library-specific wrap-selection affordance yet. `P06` owns those user-facing entry points.
- No descendant motion yet. `P04` owns drag and resize propagation.
- No collapsed visibility or edge rerouting yet. `P05` owns those rules.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_membership.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_membership.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P03_geometry_membership_wrap_selection_WRAPUP.md`

## Acceptance Criteria
- Nested direct ownership resolves deterministically to the smallest full container in the same scope and parent chain.
- Ownership remains derived after refresh and does not add persisted member metadata to project data.
- The backend wrap-selection transaction creates a correctly padded backdrop for explicit node-id sets.
- Targeted regressions cover full containment, partial-overlap rejection, nested backdrops, and cross-scope rejection.

## Handoff Notes
- `P04` and `P05` must consume the derived owner and depth metadata from this packet rather than recomputing a second ownership model in QML.
- Record the exact transaction name and payload fields in the wrap-up so `P06` can wire shell affordances without inventing another creation path.
