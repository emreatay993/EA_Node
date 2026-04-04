## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/architecture-residual-refactor/p06-graph-mutation-service-decoupling`
- Commit Owner: `worker`
- Commit SHA: `20d4b0a966d4a549fb153b53a23be39a40ae04b5`
- Changed Files: `docs/specs/work_packets/architecture_residual_refactor/P06_graph_mutation_service_decoupling_WRAPUP.md`, `ea_node_editor/graph/model.py`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_architecture_boundaries.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_graph_surface_input_contract.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_residual_refactor/P06_graph_mutation_service_decoupling_WRAPUP.md`, `ea_node_editor/graph/model.py`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_architecture_boundaries.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/test_graph_surface_input_contract.py`

- Added a packet-owned `WorkspaceMutationServiceFactory` seam in `ea_node_editor/graph/mutation_service.py` and changed `GraphModel` to delegate mutation-service creation through that seam instead of constructing `WorkspaceMutationService` directly.
- Routed `GraphSceneMutationHistory` through `model.mutation_service(..., boundary_adapters=self._boundary_adapters)` so graph-scene callers keep one authoritative mutation path while the scene layer still supplies the UI-owned boundary adapters for sizing and PDF-page normalization.
- Bound the shell bootstrap model to the default mutation-service factory in `ea_node_editor/ui/shell/composition.py`, preserving the composition-level authority seam for the desktop host without widening the packet beyond its allowed scope.
- Updated the inherited architecture and graph-scene regression anchors to lock the new factory path in place, and refreshed the packet-owned viewer-surface QML probe stub so the full verification suite matches the current `viewerSessionBridge.session_state(node_id)` contract.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q` (`94 passed in 64.48s (0:01:04)`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` (`19 passed in 2.76s`)
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree desktop build from `C:\w\ea_node_ed-p06-graph-mutation` with `.\venv\Scripts\python.exe main.py` in a normal display-attached Windows session.

1. Graph edit smoke
Action: create a workspace node flow, add two nodes, connect them, and change one node property from the inspector or inline editor.
Expected result: node creation, edge creation, and property updates all apply immediately with no graph mutation errors or stale selection state.

2. Grouping and fragment smoke
Action: multi-select two or more nodes, group them into a subnode, ungroup the result, then duplicate or paste the selected subgraph.
Expected result: each mutation succeeds, the resulting selection follows the new graph state, and no mutation-history regression appears during grouping, ungrouping, duplication, or paste.

Automated verification remains the primary proof for this packet because the core change is internal mutation-service ownership rather than a new user-facing workflow.

## Residual Risks

- Packet-external model construction sites still rely on `GraphModel`'s lazy default mutation-service factory unless they explicitly inject one, so future packets should keep an eye on new mutation-authority entry points outside the shell composition seam.
- The viewer-surface QML probe now depends on the current `viewerSessionBridge.session_state(node_id)` contract; if the viewer bridge projection API changes again, the packet-owned fixture in `tests/test_graph_surface_input_contract.py` will need to evolve with it.

## Ready for Integration

- Yes: `GraphModel` no longer manufactures `WorkspaceMutationService`, packet-owned graph-scene mutations resolve through the model-owned factory seam with the UI boundary adapters preserved, and both the full verification command and review gate passed on the packet branch.
