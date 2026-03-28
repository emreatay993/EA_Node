# ARCHITECTURE_MAINTAINABILITY_REFACTOR P07: Graph Mutation Ops Split

## Objective
- Make one mutation service the sole graph write authority, route invariant enforcement through one kernel, and split the current transform bucket into focused modules for layout, fragment, grouping, and subnode operations.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/`
- `tests/test_architecture_boundaries.py`
- `tests/test_registry_validation.py`
- `tests/test_workspace_manager.py`
- `tests/test_passive_runtime_wiring.py`

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/`
- `tests/test_architecture_boundaries.py`
- `tests/test_registry_validation.py`
- `tests/test_workspace_manager.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P07_graph_mutation_ops_split_WRAPUP.md`

## Required Behavior
- Collapse packet-owned graph write paths behind one authoritative mutation service boundary.
- Make one invariant kernel the only normal place where graph normalization and mutation validation are enforced.
- Split `graph/transforms.py` into focused operations modules so layout, fragment, grouping, and subnode behavior stop sharing one broad utility bucket.
- Update inherited architecture, registry-validation, workspace, and runtime-wiring regression anchors in place when graph mutation APIs move.

## Non-Goals
- No persistence-envelope relocation; that belongs to `P06`.
- No node SDK module split yet.
- No UI/QML scene decomposition yet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_workspace_manager.py tests/test_passive_runtime_wiring.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_registry_validation.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P07_graph_mutation_ops_split_WRAPUP.md`

## Acceptance Criteria
- Packet-owned graph writes flow through one mutation authority and one invariant kernel.
- The transform bucket is decomposed into narrower focused modules or helpers.
- The inherited graph/runtime regression anchors pass without leaving direct ad hoc graph writes behind as tolerated fallback paths.

## Handoff Notes
- `P08` should treat the graph model and mutation layer as cleaner dependencies and focus on the high-fan-in node SDK surface next.
