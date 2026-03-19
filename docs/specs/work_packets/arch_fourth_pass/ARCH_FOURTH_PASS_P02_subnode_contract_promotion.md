# ARCH_FOURTH_PASS P02: Subnode Contract Promotion

## Objective
- Move subnode semantics out of the builtin plugin layer into a lower-level contract module that graph and execution packages can depend on without importing a builtin node implementation.

## Preconditions
- `P01` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- `P00` remains `PASS`.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/nodes/builtins/subnode.py`
- graph/execution modules that currently import subnode constants or helpers
- registry/bootstrap coverage for subnode types

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/subnode.py`
- `ea_node_editor/graph/*.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/nodes/bootstrap.py`
- `tests/test_execution_worker.py`
- `tests/test_graph_track_b.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`

## Required Behavior
- Introduce a lower-level contract module for subnode constants, definitions, and transformation/runtime helpers.
- Make graph and execution packages depend on that lower-level contract instead of reaching into `nodes.builtins.subnode`.
- Keep the builtin subnode plugin implementation as a consumer of the promoted contract rather than its owner.
- Preserve authored subnode behavior, compiled-runtime behavior, and diagnostics/node-id mapping required by the existing tests and requirements.

## Non-Goals
- No new subnode features or UX flows.
- No packet-owned mutation-service boundary yet; `P03` owns that.
- No runtime DTO/worker split yet; `P04` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker tests.test_graph_track_b tests.test_registry_validation tests.test_passive_runtime_wiring -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P02_subnode_contract_promotion_WRAPUP.md`

## Acceptance Criteria
- Graph and execution layers no longer depend on builtin-plugin ownership for subnode semantics.
- Builtin subnode registration still works without changing public type ids or authored document shape.
- Packet verification passes through the project venv.

## Handoff Notes
- `P03` will build a validated mutation boundary on top of the resulting graph/runtime contracts; keep the promoted subnode seam stable for that packet.
- If a new contract module is introduced, keep it narrow and clearly below both the builtin plugin layer and UI callers.
