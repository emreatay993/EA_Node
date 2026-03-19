# ARCH_FOURTH_PASS P03: Graph Mutation Validation Boundary

## Objective
- Introduce a validated mutation boundary around graph authoring so invariants are enforced at write time instead of being repaired later by persistence/compiler cleanup.

## Preconditions
- `P02` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- `P01` remains `PASS`.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/graph/model.py`
- graph mutation/validation helpers
- scene/controller callers that currently perform ad hoc validation
- duplicate graph rule helpers

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/rules.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`
- `tests/test_graph_track_b.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `docs/specs/work_packets/arch_fourth_pass/P03_graph_mutation_validation_boundary_WRAPUP.md`

## Required Behavior
- Add an explicit validated mutation service or equivalent boundary that owns node/edge authoring rules used by `GraphModel` callers.
- Reduce the gap between “mutable graph state” and “registry-aware valid graph state” so invalid states are harder to create in normal authoring flows.
- Fold overlapping port-rule helpers into one canonical API path instead of keeping `graph.rules` and `graph.effective_ports` in parallel.
- Keep current public authoring behavior stable unless a test-backed invalid edge/path was previously accepted only because repair happened later.

## Non-Goals
- No runtime DTO/worker refactor yet; `P04` owns that.
- No shell presenter or QML bridge cleanup yet; `P05` and `P06` own that.
- No new node-library or inspector UX.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_workspace_library_controller_unit tests.test_graph_scene_bridge_bind_regression -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P03_graph_mutation_validation_boundary_WRAPUP.md`

## Acceptance Criteria
- Normal graph authoring paths route through one validated mutation boundary instead of relying on later cleanup layers to repair basic invariants.
- Port-rule duplication is removed or reduced to one canonical API path.
- Packet verification passes through the project venv.

## Handoff Notes
- `P04` will consume the resulting graph/runtime boundary, so keep the mutation interface explicit and typed enough for downstream compiler/runtime work.
- Avoid widening this packet into broad shell presenter refactors even if `graph_scene_mutation_history.py` touches UI-adjacent callers.
