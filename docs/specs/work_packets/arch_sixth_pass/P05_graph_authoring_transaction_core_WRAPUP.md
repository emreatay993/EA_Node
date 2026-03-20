# P05 Graph Authoring Transaction Core Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/arch-sixth-pass/p05-graph-authoring-transaction-core`
- Commit Owner: `worker`
- Commit SHA: `cb84127a0722424b60bc4f61be7177f0b744edeb`
- Changed Files: `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/transforms.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `docs/specs/work_packets/arch_sixth_pass/P05_graph_authoring_transaction_core_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/arch_sixth_pass/P05_graph_authoring_transaction_core_WRAPUP.md`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/transforms.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_graph_scene_bridge_bind_regression.py`

- Added graph-owned authoring transaction methods on `WorkspaceMutationService` for fragment insertion, grouping, and ungrouping.
- Kept the existing transform entrypoints behavior-compatible by turning them into wrappers over the new mutation-service transaction surface.
- Reduced `GraphSceneMutationHistory` to orchestration for history grouping, selection updates, and model rebuilds while delegating graph rewrites to the graph-owned transaction boundary.
- Added bridge regression coverage that verifies scene grouping, fragment rewrites, and ungrouping route through `WorkspaceMutationService`.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer.py -q -k grouped_subnode_parenting`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_graph_scene_bridge_bind_regression.py tests/test_workspace_library_controller_unit.py tests/test_passive_visual_metadata.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

Prerequisite: launch the desktop app on this branch and open any workspace with a visible graph canvas.

1. Group two sibling nodes that have inbound and outbound external connections.
Action: Select both nodes and trigger the existing Group command.
Expected result: one subnode shell is created, boundary pins appear in stable order, external wiring is preserved, and one undo step removes the whole grouping.

2. Ungroup the resulting subnode shell.
Action: Select the shell and trigger the existing Ungroup command.
Expected result: the child nodes return to their original parent scope, outer connections are restored, and undo/redo each operate as single history steps.

3. Duplicate and paste a connected two-node selection with visible styling or labels.
Action: Duplicate the selection, then copy/paste the same fragment into empty canvas space.
Expected result: only internal edges are duplicated, visual metadata stays intact, the new nodes become selected, and each duplicate/paste action records as one history entry.

## Residual Risks

- Interactive desktop smoke coverage was not run, so live canvas checks are still useful for selection feel, viewport focus timing, and any Qt-only edge cases around grouped undo/redo.
- Compatibility wrappers remain in `ea_node_editor/graph/transforms.py` for packet-external callers; later packets can decide whether any remaining direct callers should be migrated off those wrappers.

## Ready for Integration

- Yes: graph-scene complex rewrites now route through a graph-owned mutation-service transaction core, and the required packet verification passed.
