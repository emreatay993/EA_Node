# P04 Graph Scene Mutation Packet Split Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/ui-context-scalability-followup/p04-graph-scene-mutation-packet-split`
- Commit Owner: `worker`
- Commit SHA: `b3b1c5491fd4fc3c590c8991f0d7e0fb4a32caeb`
- Changed Files: `docs/specs/work_packets/ui_context_scalability_followup/P04_graph_scene_mutation_packet_split_WRAPUP.md`, `ea_node_editor/ui_qml/graph_scene_mutation/__init__.py`, `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation/clipboard_and_fragment_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation/comment_backdrop_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation/grouping_and_subnode_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation/policy.py`, `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_graph_scene_bridge_bind_regression.py`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_followup/P04_graph_scene_mutation_packet_split_WRAPUP.md`, `ea_node_editor/ui_qml/graph_scene_mutation/policy.py`, `ea_node_editor/ui_qml/graph_scene_mutation/comment_backdrop_ops.py`

- Split the graph-scene mutation monolith into focused `graph_scene_mutation` helper modules for policy, selection/scope, clipboard/fragment flows, alignment/distribution, grouping/subnode workflows, and comment backdrops while keeping `graph_scene_mutation_history.py` as the stable entry surface.
- Reduced `ea_node_editor/ui_qml/graph_scene_mutation_history.py` from 1,195 lines to 328 lines by moving operational bodies behind facade method bindings and keeping the packet-owned source assertions that lock the stable class names, helper signatures, and mutation-service factory path in place.
- Updated the graph-scene bridge bind regression to verify the new helper package, facade line budget, and method origin modules, and refreshed the packet-owned `GraphCanvas.qml` bridge assertions to the current root-bindings seam used by the repo.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py tests/test_main_window_shell.py tests/test_comment_backdrop_interactions.py tests/test_comment_backdrop_collapse.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/test_comment_backdrop_interactions.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

1. Open a workspace with ordinary nodes, subnodes, and comment backdrops, then add and remove nodes, connect ports, group and ungroup a subnode, and confirm selection, scope restrictions, and undoable mutations still behave exactly as before the split.
2. Copy a selected subgraph, paste it to a new location, duplicate it once, then wrap the result in a comment backdrop and delete the selection to confirm fragment cloning, backdrop-aware selection expansion, and delete history still round-trip through the stable scene bridge.

## Residual Risks

- The facade now relies on explicit post-class method bindings to keep the stable `GraphSceneMutationHistory` class declaration slim, so later packets that add or move mutation entrypoints need to update the facade binding list and the packet-owned seam test together.
- `tests/test_graph_scene_bridge_bind_regression.py` now reflects the current `GraphCanvas.qml` root-bindings bridge wiring; later bridge packets should preserve that seam or deliberately update both the QML bindings and the regression anchor in one change.

## Ready for Integration

- Yes: the mutation facade is under the packet budget, the required verification and review gate pass, and the final packet diff stays inside the documented P04 write scope.
