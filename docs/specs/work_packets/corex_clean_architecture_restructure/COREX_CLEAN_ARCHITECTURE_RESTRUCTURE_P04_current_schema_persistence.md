# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P04: Current-Schema Persistence

## Objective

Narrow persistence around authored current-schema project documents, artifact sidecars, and lightweight session/autosave state without leaking live runtime viewer state into project files.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and persistence/test files needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P03_workspace_custom_workflows` is `PASS`.

## Execution Dependencies

- `P03_workspace_custom_workflows`

## Target Subsystems

- Project serializer and codec
- Current-schema migration/normalization
- Artifact store/resolution
- Session/autosave persistence
- Preference/settings persistence only where required by split boundaries

## Conservative Write Scope

- `ea_node_editor/persistence/**`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/execution/runtime_snapshot_assembly.py`
- `tests/test_serializer*.py`
- `tests/serializer/**`
- `tests/test_project_artifact*.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_persistence_package_imports.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P04_current_schema_persistence_WRAPUP.md`

## Required Behavior

- Keep `JsonProjectSerializer` as a thin file adapter for current-schema documents.
- Keep artifact bytes and artifact metadata separate: document stores refs and metadata, artifact store owns sidecar layout and promotion.
- Keep session/autosave state lightweight and outside project document semantics.
- Consolidate runtime/authored envelope ownership so unresolved runtime projection does not duplicate persistence responsibilities.
- Preserve current `.sfe` and `.data` behavior.

## Non-Goals

- Do not persist live viewer-session state in project documents.
- Do not reintroduce legacy schema migration paths removed by the no-legacy cleanup.
- Do not change runtime snapshot behavior beyond persistence envelope ownership needed here.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_persistence_package_imports.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_serializer_schema_migration.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P04_current_schema_persistence_WRAPUP.md`

## Acceptance Criteria

- Persistence owns document and sidecar concerns, not live viewer runtime state.
- Current-schema-only policy remains strict and tested.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If `ProjectPersistenceEnvelope` and runtime snapshot envelope ownership conflict, choose one owner and document the compatibility reasoning in the wrap-up.
