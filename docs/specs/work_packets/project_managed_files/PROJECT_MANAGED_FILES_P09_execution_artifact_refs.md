# PROJECT_MANAGED_FILES P09: Execution Artifact Refs

## Objective
- Add the queue-safe runtime artifact-ref protocol so heavy outputs in `stored` mode travel through execution as structured refs instead of raw payload blobs, while small outputs remain inline.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P03`

## Target Subsystems
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/nodes/types.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`

## Conservative Write Scope
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/nodes/types.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`
- `docs/specs/work_packets/project_managed_files/P09_execution_artifact_refs_WRAPUP.md`

## Required Behavior
- Add a structured runtime artifact-ref DTO/protocol shape for stored outputs and downstream inputs.
- Keep small outputs inline exactly as today; only packet-owned stored outputs should emit artifact refs instead of raw payload blobs.
- Make worker/client queue transport, event payloads, and runtime snapshot handling compatible with typed artifact refs.
- Add runtime resolution hooks so downstream nodes can consume stored artifact refs through the central artifact service without bypassing the packet-owned protocol.
- Keep backward compatibility for current inline-only runs and legacy payload readers.
- Add packet-owned execution tests that prove large stored outputs stay out of inline queue payloads while downstream consumers can still resolve the produced refs.

## Non-Goals
- No concrete node adoption yet. `P10` and `P11` own the first producers.
- No project-files dialog, save flow, or source-import UX changes.
- No automatic storage promotion based on output size.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_execution_worker.py tests/test_execution_client.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_execution_artifact_refs.py --ignore=venv -q`

## Expected Artifacts
- `tests/test_execution_artifact_refs.py`
- `docs/specs/work_packets/project_managed_files/P09_execution_artifact_refs_WRAPUP.md`

## Acceptance Criteria
- Execution can transport stored outputs as typed artifact refs rather than raw payload blobs.
- Small inline outputs remain behavior-compatible.
- Downstream runtime consumers can resolve stored refs through packet-owned helpers.
- Existing worker/client flows keep working for non-stored runs.

## Handoff Notes
- `P10` and `P11` must reuse the exact artifact-ref DTO and queue contract from this packet.
- Record the final event/trigger/runtime snapshot payload shape in the wrap-up so later packets do not fork the execution contract.
