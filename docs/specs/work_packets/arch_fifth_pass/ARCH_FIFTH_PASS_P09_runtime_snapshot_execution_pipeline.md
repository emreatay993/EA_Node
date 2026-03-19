# ARCH_FIFTH_PASS P09: Runtime Snapshot Execution Pipeline

## Objective
- Replace raw `project_doc` run transport with a runtime snapshot boundary that preserves exact execution behavior, logging, and performance.

## Preconditions
- `P08` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- run-controller/client/protocol/worker command boundary
- runtime DTO / runtime snapshot ownership
- execution regression coverage

## Conservative Write Scope
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/worker.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_process_run_node.py`
- `tests/test_run_controller_unit.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/arch_fifth_pass/P09_runtime_snapshot_execution_pipeline_WRAPUP.md`

## Required Behavior
- Introduce a typed runtime snapshot boundary built from the validated live model for the active workspace.
- Replace `StartRunCommand.project_doc` with `StartRunCommand.runtime_snapshot`.
- Keep `project_path` as an explicit fallback only for non-UI callers that do not provide a runtime snapshot.
- Remove packet-owned worker/compiler dependence on broad document-shaped authoring payloads.
- Preserve exact run behavior, logs, failure reporting, worker state transitions, and current runtime performance.

## Non-Goals
- No new execution features or scheduler behavior in this packet.
- No plugin contract redesign in this packet; `P10` owns that.
- No shell/QML behavior change in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_process_run_node.py tests/test_run_controller_unit.py tests/test_passive_runtime_wiring.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P09_runtime_snapshot_execution_pipeline_WRAPUP.md`

## Acceptance Criteria
- Packet-owned run orchestration no longer transports raw `project_doc` payloads.
- Worker execution consumes the runtime snapshot boundary or the explicit path-based fallback only.
- Execution behavior and performance remain unchanged, and packet verification passes.

## Handoff Notes
- Keep any temporary compatibility adapters internal and clearly documented in the wrap-up.
- `P10` assumes the runtime boundary is no longer document-shaped.
