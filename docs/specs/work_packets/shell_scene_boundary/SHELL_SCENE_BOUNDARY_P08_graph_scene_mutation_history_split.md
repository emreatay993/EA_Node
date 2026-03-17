# SHELL_SCENE_BOUNDARY P08: GraphScene Mutation History Split

## Objective
- Extract node/edge mutation, layout, fragment/clipboard, and history-grouping behavior from `GraphSceneBridge` into dedicated edit-operation helpers while keeping the public bridge contract stable.

## Preconditions
- `P07` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py` (new)
- `tests/test_graph_track_b.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_property_editors.py`
- `tests/test_passive_image_nodes.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `tests/test_graph_track_b.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_property_editors.py`
- `tests/test_passive_image_nodes.py`

## Required Behavior
- Extract node/edge creation/removal, property/style mutation, move/resize/layout helpers, group/ungroup flows, fragment duplication/paste flows, and history snapshot/grouping behavior into `graph_scene_mutation_history.py` or equivalent helpers.
- Preserve current undo/history semantics and public `GraphSceneBridge` mutation slot names.
- Preserve explicit `nodeId` graph-surface commit/browse behavior introduced by `GRAPH_SURFACE_INPUT`.
- Keep mutation behavior stable for passive-property, graph-track, and image-surface workflows.

## Non-Goals
- No scope/selection extraction work beyond minimal integration with `P07`.
- No payload/theme/minimap/media normalization extraction yet.
- No `ShellWindow` or QML boundary rewrites.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_graph_surface_input_inline tests.test_passive_property_editors tests.test_passive_image_nodes -v`

## Acceptance Criteria
- `GraphSceneBridge` no longer owns all mutation/history logic inline.
- Undo/layout/fragment/property regressions pass.
- Public mutation slot names and behavior stay stable.

## Handoff Notes
- `P09` extracts payload-building and media/theme normalization next; do not reopen those concerns here.
