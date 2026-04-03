# ARCHITECTURE_RESIDUAL_REFACTOR P05: Runtime Snapshot Boundary Decoupling

## Objective

- Remove persistence-oriented normalization and envelope ownership from the normal execution-side runtime-snapshot path.

## Preconditions

- `P04` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P04`

## Target Subsystems

- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/*snapshot*.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_architecture_boundaries.py`

## Conservative Write Scope

- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/*snapshot*.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_architecture_boundaries.py`
- `docs/specs/work_packets/architecture_residual_refactor/P05_runtime_snapshot_boundary_decoupling_WRAPUP.md`

## Required Behavior

- Remove packet-owned persistence migration, persistence-envelope, and artifact-store normalization imports from the normal execution-side runtime-snapshot builder path.
- Introduce an execution-owned snapshot assembler or adapter seam that consumes normalized domain data without round-tripping through persistence-oriented helpers.
- Preserve runtime payload semantics, artifact refs, and run trigger contracts.
- Update inherited architecture-boundary assertions in place when the runtime-snapshot seam changes.

## Non-Goals

- No graph-domain mutation-service cycle work yet; that belongs to `P06`.
- No neutral runtime-contract extraction yet; that belongs to `P07`.
- No user-facing run workflow changes.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_passive_runtime_wiring.py tests/test_architecture_boundaries.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_architecture_boundaries.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P05_runtime_snapshot_boundary_decoupling_WRAPUP.md`

## Acceptance Criteria

- The normal execution-side runtime-snapshot path no longer depends on persistence migration or persistence-envelope helpers.
- Runtime payload and run-trigger behavior remain stable.
- The inherited execution and boundary regression anchors pass.

## Handoff Notes

- `P06` removes the graph model-to-service construction cycle against this cleaner runtime boundary.
