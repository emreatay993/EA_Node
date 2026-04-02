# ARCHITECTURE_FOLLOWUP_REFACTOR P05: Runtime Snapshot Direct Builder

## Objective

- Build runtime snapshot payloads directly from `ProjectData` and `WorkspaceData` instead of round-tripping through project serialization on the normal execution path.

## Preconditions

- `P04` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P04`

## Target Subsystems

- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/runtime_dto.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_passive_runtime_wiring.py`

## Conservative Write Scope

- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/runtime_dto.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/architecture_followup_refactor/P05_runtime_snapshot_direct_builder_WRAPUP.md`

## Required Behavior

- Replace packet-owned runtime snapshot construction through `JsonProjectSerializer` with a direct builder over domain objects.
- Preserve the external `RuntimeSnapshot` document shape, queue-safe payload behavior, and compiler expectations.
- Avoid reintroducing persistence-driven transformation churn into the normal execution path.
- Update inherited execution and runtime-wiring regression anchors in place.

## Non-Goals

- No protocol shape expansion or viewer session redesign here.
- No graph authoring command-boundary cleanup yet; that belongs to `P06`.
- No new runtime feature work beyond builder-path cleanup.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_passive_runtime_wiring.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_passive_runtime_wiring.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P05_runtime_snapshot_direct_builder_WRAPUP.md`

## Acceptance Criteria

- `build_runtime_snapshot(...)` no longer depends on project serialization for the normal execution path.
- The runtime snapshot document contract and compiler behavior remain stable.
- The inherited execution and runtime-wiring regression anchors pass.

## Handoff Notes

- `P06` inherits the cleaner direct runtime-input path when collapsing graph authoring authority.
