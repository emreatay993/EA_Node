# ARCHITECTURE_MAINTAINABILITY_REFACTOR P06: Graph Persistence Boundary Cleanup

## Objective
- Move file-issue and repair logic out of `graph` into persistence-owned or workspace-owned modules, remove `WorkspacePersistenceState` from graph-owned models, and make serializer or codec layers own persistence envelopes and mappings.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/persistence/`
- `ea_node_editor/workspace/manager.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_project_file_issues.py`
- `tests/test_workspace_manager.py`
- `tests/test_registry_validation.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/persistence/`
- `ea_node_editor/workspace/manager.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_project_file_issues.py`
- `tests/test_workspace_manager.py`
- `tests/test_registry_validation.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P06_graph_persistence_boundary_cleanup_WRAPUP.md`

## Required Behavior
- Remove file-issue, repair, or persistence-envelope ownership from graph-owned modules and relocate it to persistence-owned or workspace-owned code.
- Remove `WorkspacePersistenceState` from `WorkspaceData` and related graph-owned state holders, replacing it with explicit persistence mapping/adaptation at the serializer, codec, or workspace boundary.
- Keep current serializer, migration, artifact-resolution, and project-file-issue behavior stable while moving ownership to cleaner packages.
- Update inherited architecture-boundary, project-file-issue, workspace, and registry-validation anchors in place when the graph/persistence seam changes.

## Non-Goals
- No graph mutation authority cleanup yet; that belongs to `P07`.
- No node SDK split yet.
- No new project-file issue UX.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_project_file_issues.py tests/test_workspace_manager.py tests/test_registry_validation.py tests/test_serializer.py tests/test_serializer_schema_migration.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_project_file_issues.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P06_graph_persistence_boundary_cleanup_WRAPUP.md`

## Acceptance Criteria
- Graph-owned models stop owning persistence-envelope state.
- File-issue and repair logic are no longer graph-package responsibilities.
- The inherited architecture/persistence/workspace regression anchors pass after the boundary cleanup.

## Handoff Notes
- `P07` should assume the graph-persistence boundary is clearer and focus on singular graph mutation authority rather than revisiting persistence ownership.
