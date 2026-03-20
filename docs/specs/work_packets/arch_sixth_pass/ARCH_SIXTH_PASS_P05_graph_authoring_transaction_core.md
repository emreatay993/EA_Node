# ARCH_SIXTH_PASS P05: Graph Authoring Transaction Core

## Objective
- Move complex graph rewrites such as fragment insert, group, and ungroup onto a graph-owned authoring transaction core so the hardest mutations stop bypassing the primary validated mutation boundary.

## Preconditions
- `P00` through `P04` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- graph transform and fragment rewrite flows
- mutation service boundary
- scene mutation orchestration

## Conservative Write Scope
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `tests/test_graph_track_b.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_workspace_library_controller_unit.py`
- `docs/specs/work_packets/arch_sixth_pass/P05_graph_authoring_transaction_core_WRAPUP.md`

## Required Behavior
- Introduce or complete a graph-owned transaction layer for complex graph rewrite operations.
- Move packet-owned fragment insert, group, and ungroup flows off direct `*_raw` mutation helper use where an authoritative transaction boundary can own the rewrite safely.
- Reduce graph-domain work inside `GraphSceneMutationHistory` so it becomes orchestration over a graph-owned transaction surface.
- Preserve current graph authoring behavior, undo grouping, and fragment/custom-workflow behavior exactly.

## Non-Goals
- No persistence overlay redesign in this packet.
- No shell verification or docs-only work in this packet.
- No plugin/package boundary changes in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_graph_scene_bridge_bind_regression.py tests/test_workspace_library_controller_unit.py tests/test_passive_visual_metadata.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P05_graph_authoring_transaction_core_WRAPUP.md`

## Acceptance Criteria
- Packet-owned complex graph rewrites no longer rely on raw mutation helpers as the public authoring surface.
- `GraphSceneMutationHistory` owns less graph-domain rewrite logic than the current baseline.
- Graph authoring regressions pass with no behavior or undo-history changes.

## Handoff Notes
- `P06` owns workspace state, history, and clipboard boundary cleanup after the transaction core is authoritative.
- Preserve current fragment/custom-workflow semantics exactly while moving the ownership boundary.
