# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P11: Runtime Snapshot Only Protocol

## Objective

- Make `RuntimeSnapshot` the mandatory normal execution payload and delete project-path rebuild, old trigger-shape tolerance, and permissive snapshot ingestion.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only execution/runtime tests needed for this packet

## Preconditions

- `P10` is marked `PASS`.

## Execution Dependencies

- `P10`

## Target Subsystems

- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/runtime_snapshot_assembly.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/worker_runtime.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/execution/worker_protocol.py`
- `ea_node_editor/execution/dpf_runtime/viewer_session_backend.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_run_controller_unit.py`
- `tests/test_shell_run_controller.py`
- `tests/test_architecture_boundaries.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P11_runtime_snapshot_only_protocol_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/runtime_snapshot_assembly.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/worker_runtime.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/worker_runner.py`
- `ea_node_editor/execution/worker_protocol.py`
- `ea_node_editor/execution/dpf_runtime/viewer_session_backend.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_run_controller_unit.py`
- `tests/test_shell_run_controller.py`
- `tests/test_architecture_boundaries.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P11_runtime_snapshot_only_protocol_WRAPUP.md`

## Required Behavior

- Require `runtime_snapshot` at run startup and fail fast if absent.
- Remove `project_doc` trigger sanitization and legacy rejection branches after callers no longer send it.
- Remove `project_path`-based worker rebuild as a normal startup path. Keep `project_path` only as artifact-resolution context if still needed and clearly named as such.
- Remove permissive snapshot/workspace ingestion that derives missing `workspace_order` or accepts flat workspace payloads when canonical DTO fields are required.
- Remove unused compatibility parameters such as `serializer` on runtime snapshot builders.
- Normalize DPF runtime viewer source keys before execution so viewer session backend no longer accepts old aliases such as `fields`, `field_data`, `result`, `model`, or `mesh` unless they are canonical current keys.

## Non-Goals

- No interactive pause/resume/stop removal unless the packet proves one-shot execution is the current product contract. If run control remains current behavior, keep it.
- No viewer UI transport rewrite; that belongs to `P12`.
- No docs closeout.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_execution_viewer_protocol.py tests/test_run_controller_unit.py tests/test_shell_run_controller.py tests/test_architecture_boundaries.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P11_runtime_snapshot_only_protocol_WRAPUP.md`

## Acceptance Criteria

- Runtime startup requires a canonical `RuntimeSnapshot`.
- Worker no longer rebuilds a run from project files as an ordinary fallback.
- Execution tests assert current payload shape rather than legacy sanitization.

## Handoff Notes

- `P12` can assume viewer events and backend sessions are fed by snapshot-only execution payloads.
