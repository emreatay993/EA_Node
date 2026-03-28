# ARCHITECTURE_MAINTAINABILITY_REFACTOR P09: Runtime Protocol Compat Removal

## Objective
- Make `RuntimeSnapshot` the only normal execution payload, remove normal-path `project_doc` handling from client, protocol, runtime snapshot coercion, and worker code, and add request correlation where protocol errors still rely on FIFO heuristics.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/execution/worker_runtime.py`
- `ea_node_editor/execution/`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_run_controller_unit.py`
- `tests/test_shell_run_controller.py`

## Conservative Write Scope
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/execution/worker_runtime.py`
- `ea_node_editor/execution/`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_run_controller_unit.py`
- `tests/test_shell_run_controller.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P09_runtime_protocol_compat_removal_WRAPUP.md`

## Required Behavior
- Remove packet-owned normal-path `project_doc` compatibility from runtime snapshot creation, queue protocol shapes, client dispatch, and worker execution paths.
- Keep any unavoidable compatibility logic at one explicit edge adapter only when the packet can prove a hard external requirement; otherwise delete it.
- Add explicit request correlation for packet-owned protocol error handling where the current logic still relies on FIFO-per-command matching.
- Update inherited execution client, worker, handle/artifact ref, run-controller, and viewer-protocol anchors in place when runtime payload or protocol semantics change.

## Non-Goals
- No viewer-session backend split yet; that belongs to `P10`.
- No doc/traceability cleanup yet.
- No new execution features or message families beyond the correlation needed to remove FIFO ambiguity.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_execution_viewer_protocol.py tests/test_run_controller_unit.py tests/test_shell_run_controller.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_artifact_refs.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P09_runtime_protocol_compat_removal_WRAPUP.md`

## Acceptance Criteria
- `RuntimeSnapshot` is the only normal execution payload.
- Normal-path `project_doc` compatibility is removed or isolated to one explicit edge adapter with packet-owned proof.
- Protocol errors stop depending on FIFO-only correlation where packet-owned command families can overlap.
- The inherited execution and run-controller regression anchors pass.

## Handoff Notes
- `P10` should assume the execution payload and protocol seams are singular and then split viewer-session ownership on top of that cleaner runtime boundary.
