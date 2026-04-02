# ARCHITECTURE_FOLLOWUP_REFACTOR P04: Graph Persistence Sidecar Removal

## Objective

- Remove the remaining persistence-overlay sidecar ownership from graph-owned models and snapshots so graph domain state no longer imports persistence overlay machinery directly.

## Preconditions

- `P03` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/persistence/file_issues.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/migration.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_project_file_issues.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_workspace_manager.py`

## Conservative Write Scope

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/persistence/file_issues.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/migration.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_project_file_issues.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_workspace_manager.py`
- `docs/specs/work_packets/architecture_followup_refactor/P04_graph_persistence_sidecar_removal_WRAPUP.md`

## Required Behavior

- Remove packet-owned `graph.model` imports and ownership of persistence-overlay state.
- Keep persistence envelope, unresolved-document, and file-repair state in persistence-owned structures or adapters at persistence boundaries.
- Preserve current serializer, migration, and project-file-issue behavior while moving ownership out of graph-owned classes.
- Update inherited architecture-boundary, serializer, and workspace regression anchors in place.

## Non-Goals

- No runtime snapshot builder cleanup yet; that belongs to `P05`.
- No graph authoring command-boundary cleanup yet; that belongs to `P06`.
- No user-facing persistence feature expansion.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_project_file_issues.py tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_workspace_manager.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_serializer_schema_migration.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P04_graph_persistence_sidecar_removal_WRAPUP.md`

## Acceptance Criteria

- Packet-owned graph models and snapshots no longer import or own persistence overlay state directly.
- Serializer and migration behavior remain stable after the ownership move.
- The inherited architecture-boundary and serializer regression anchors pass.

## Handoff Notes

- `P05` builds the direct runtime snapshot builder on top of this cleaner graph or persistence boundary.
