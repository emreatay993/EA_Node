# ARCH_THIRD_PASS P06: Execution Worker Runtime

## Objective
- Decompose `worker.py` into clearer control, scheduling, execution, and event-publication seams, and explicitly satisfy `REQ-NODE-011` so data-only dependencies are evaluated correctly rather than relying on sorted leftover execution.

## Preconditions
- `P00` through `P05` are marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- packet-owned worker/scheduler helpers under `ea_node_editor/execution/`
- limited registry bootstrap wiring if needed
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_process_run_node.py`
- `tests/test_passive_runtime_wiring.py`

## Conservative Write Scope
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- packet-owned worker/scheduler helpers under `ea_node_editor/execution/`
- limited registry bootstrap wiring if needed
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_process_run_node.py`
- `tests/test_passive_runtime_wiring.py`

## Required Behavior
- Split packet-owned worker responsibilities into clearer seams for run control, dependency scheduling, node execution, and event publication instead of keeping them interleaved in one module.
- Make evaluation of pure/data-only dependency nodes explicit so downstream requests for data outputs satisfy `REQ-NODE-011` without relying on incidental sorted leftover execution order.
- Preserve current external command/event payload shapes across `client.py` and `protocol.py` unless a packet-owned internal abstraction can keep those surfaces behaviorally identical.
- Preserve passive-runtime exclusions and existing action/exec-trigger behavior while tightening the pure-data dependency path.
- Keep any registry/bootstrap wiring changes narrow and packet-owned.

## Non-Goals
- No shell/QML/UI changes.
- No persistence/schema changes.
- No expansion of the execution protocol beyond what is required to preserve current behavior.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_process_run_node.py tests/test_passive_runtime_wiring.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_execution_worker.py tests/test_execution_client.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P06_execution_worker_runtime_WRAPUP.md`

## Acceptance Criteria
- Packet-owned execution runtime concerns are split into clearer seams than the current `worker.py` monolith.
- Worker behavior explicitly evaluates data-only dependencies needed by downstream nodes.
- Execution client/worker/process/passive-runtime regressions pass through the project venv.

## Handoff Notes
- `P07` centralizes validation and persistence rules; keep runtime changes focused on execution semantics and worker ownership, not document-shape policy.
- Record any remaining ambiguity around mixed exec/data graphs as residual risk rather than widening protocol surface without tests.
