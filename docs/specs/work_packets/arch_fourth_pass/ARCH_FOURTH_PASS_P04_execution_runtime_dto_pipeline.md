# ARCH_FOURTH_PASS P04: Execution Runtime DTO Pipeline

## Objective
- Rework execution preparation and worker runtime around typed runtime DTOs/services so compiler and worker logic stop depending on broad document-shaped mappings.

## Preconditions
- `P03` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- `P02` remains `PASS`.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/worker.py`
- packet-owned runtime DTO/service modules under `ea_node_editor/execution/`
- protocol adapters where needed

## Conservative Write Scope
- `ea_node_editor/execution/*.py`
- `ea_node_editor/graph/model.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_process_run_node.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/arch_fourth_pass/P04_execution_runtime_dto_pipeline_WRAPUP.md`

## Required Behavior
- Introduce typed runtime DTOs or equivalent explicit runtime objects between authored graph state and worker execution.
- Keep dict adapters at queue/process boundaries, but stop using raw authored-document mappings as the main internal runtime contract.
- Split worker responsibilities into clearer seams such as compile/preparation, scheduling, execution, and event publication where practical inside the packet scope.
- Preserve `REQ-EXEC-009`, current event payload compatibility, and current worker-side execution semantics unless a test-backed packet-owned improvement is explicitly documented.

## Non-Goals
- No shell/UI presenter work in this packet.
- No broad verification/docs consolidation yet; `P07` owns that.
- No new execution features outside the architectural boundary cleanup.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_client tests.test_execution_worker tests.test_process_run_node tests.test_passive_runtime_wiring -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_execution_worker tests.test_execution_client -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P04_execution_runtime_dto_pipeline_WRAPUP.md`

## Acceptance Criteria
- Compiler and worker internals depend on narrower typed runtime ownership than the authored-document mappings they started from.
- Queue-boundary command/event payload compatibility stays intact.
- Packet verification passes through the project venv.

## Handoff Notes
- `P05` and `P06` should not reopen execution internals unless a shell/UI packet explicitly needs a new stable runtime-facing contract.
- If runtime DTOs are introduced, keep naming/documentation clear enough that later docs/traceability updates can point to them directly.
