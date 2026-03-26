# ARCHITECTURE_REFACTOR P05: Graph Invariant Kernel

## Objective
- Centralize graph normalization and invariant policy inside one shared authority so edit-time validation, fragment transforms, and runtime-facing graph rules stop re-encoding overlapping logic.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/`
- `tests/test_registry_validation.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_serializer_schema_migration.py`

## Conservative Write Scope
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/`
- `tests/test_registry_validation.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_serializer_schema_migration.py`
- `docs/specs/work_packets/architecture_refactor/P05_graph_invariant_kernel_WRAPUP.md`

## Required Behavior
- Create one invariant or normalization authority for registry resolution, exposed-port normalization, edge acceptance, and fragment normalization.
- Reuse that authority from edit-time and transform paths instead of letting policy continue to drift across multiple graph helpers.
- Pull packet-owned normalization branches out of `graph/transforms.py`, or otherwise make transform call sites delegate to the shared kernel instead of leaving policy forks embedded there.
- Update inherited regression anchors when packet-owned rule names or normalization behavior changes, rather than layering new duplicate tests on top.
- Preserve authored graph shape, unresolved-plugin preservation, and passive runtime exclusion behavior.

## Non-Goals
- No migration or codec adoption yet.
- No UI/QML bridge or canvas changes.
- No runtime worker changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_registry_validation.py tests/test_passive_runtime_wiring.py tests/test_serializer_schema_migration.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P05_graph_invariant_kernel_WRAPUP.md`

## Acceptance Criteria
- Graph invariants have one authoritative implementation path instead of overlapping policy copies.
- Existing registry and migration-facing graph tests are updated in place when needed and pass.
- The packet-owned verification command passes.

## Handoff Notes
- `P06` must adopt this kernel in persistence code rather than introducing a second persistence-only normalization fork.
