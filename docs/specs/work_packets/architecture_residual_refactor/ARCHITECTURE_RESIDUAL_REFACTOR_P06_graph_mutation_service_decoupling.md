# ARCHITECTURE_RESIDUAL_REFACTOR P06: Graph Mutation Service Decoupling

## Objective

- Remove graph-domain service construction knowledge from `GraphModel` and inject packet-owned mutation authority from composition-level seams instead.

## Preconditions

- `P05` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P05`

## Target Subsystems

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/architecture_residual_refactor/P06_graph_mutation_service_decoupling_WRAPUP.md`

## Required Behavior

- Remove packet-owned `GraphModel` factory creation of `WorkspaceMutationService`.
- Inject packet-owned mutation authority through composition, bridge wiring, or a dedicated factory seam instead of graph-domain construction knowledge.
- Preserve one authoritative graph mutation path for packet-owned callers.
- Update inherited architecture-boundary and graph-scene regression anchors in place when this seam changes.

## Non-Goals

- No neutral runtime-contract extraction yet; that belongs to `P07`.
- No fresh graph feature work.
- No viewer-session behavior changes beyond packet-owned mutation wiring fallout.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P06_graph_mutation_service_decoupling_WRAPUP.md`

## Acceptance Criteria

- `GraphModel` no longer manufactures `WorkspaceMutationService`.
- Packet-owned graph mutation consumers obtain their mutation authority through composition-level seams.
- The inherited boundary and graph-scene regression anchors pass.

## Handoff Notes

- `P07` extracts shared runtime contracts against this cleaned-up graph-domain boundary.
