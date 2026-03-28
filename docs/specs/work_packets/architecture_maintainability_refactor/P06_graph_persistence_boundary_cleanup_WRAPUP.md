# P06 Graph Persistence Boundary Cleanup Wrap-up

## Implementation Summary
- Packet: `P06`
- Branch Label: `codex/architecture-maintainability-refactor/p06-graph-persistence-boundary-cleanup`
- Commit Owner: `worker`
- Commit SHA: `8f201b6fa3e9f728984ca68c226ed077a32a0522`
- Changed Files: `ea_node_editor/graph/file_issue_state.py`, `ea_node_editor/graph/model.py`, `ea_node_editor/persistence/file_issues.py`, `ea_node_editor/persistence/overlay.py`, `tests/test_architecture_boundaries.py`, `tests/test_project_file_issues.py`, `tests/test_registry_validation.py`, `tests/test_workspace_manager.py`, `docs/specs/work_packets/architecture_maintainability_refactor/P06_graph_persistence_boundary_cleanup_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/architecture_maintainability_refactor/P06_graph_persistence_boundary_cleanup_WRAPUP.md`, `ea_node_editor/graph/file_issue_state.py`, `ea_node_editor/graph/model.py`, `ea_node_editor/persistence/file_issues.py`, `ea_node_editor/persistence/overlay.py`, `tests/test_architecture_boundaries.py`, `tests/test_project_file_issues.py`, `tests/test_registry_validation.py`, `tests/test_workspace_manager.py`

File-issue collection, repair-mode selection, and repair-request encoding now live in `ea_node_editor/persistence/file_issues.py`. `ea_node_editor.graph.file_issue_state` is reduced to a boundary adapter so the graph package no longer owns the project-file issue implementation while existing in-repo callers remain stable.

Workspace persistence overlays are now stored in persistence-owned side-table helpers instead of graph dataclass fields. `WorkspaceData` and `WorkspaceSnapshot` keep their existing boundary accessors and snapshot/restore behavior through `capture_persistence_state()`, `restore_persistence_state()`, and persistence overlay helpers, and snapshot equality now includes externalized overlay state so runtime history semantics stay intact.

Packet-owned regression anchors now prove the new seam directly: graph models no longer declare a `persistence_state` field, duplicated workspaces preserve independent overlay copies, snapshots restore externalized overlays, and file-issue tests use the persistence-owned authority while keeping the graph adapter available for existing UI paths.

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_project_file_issues.py tests/test_workspace_manager.py tests/test_registry_validation.py tests/test_serializer.py tests/test_serializer_schema_migration.py --ignore=venv -q` (`64 passed in 5.21s`)
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_project_file_issues.py --ignore=venv -q` (`8 passed in 3.49s`)
- PASS: `git diff --check`
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing

1. Repair a missing external file reference from the node inspector.
Prerequisites: launch a native desktop session, create or open a project, add an `io.file_read` node, and point its `path` property at a file that does not exist.
Action: select the node, confirm the inspector marks the property as a file issue, then use the repair flow to relink it to a real file.
Expected result: the repair flow returns the new path, the issue indicator clears after the property update, and the project metadata does not gain unexpected managed-artifact entries for the plain external relink.

2. Repair a missing managed media source with staged copy.
Prerequisites: open a saved project, create an `Image Panel` node whose `source_path` references a missing managed or staged asset, and keep a replacement image available on disk.
Action: trigger the property repair flow, choose the managed-copy option, and accept the replacement file.
Expected result: the node property resolves to the staged artifact reference, the staged artifact metadata updates under `artifact_store`, and the file issue clears without breaking the node.

3. Duplicate and reopen a workspace after persistence-heavy edits.
Prerequisites: in the same desktop session, create multiple workspaces and views, make a few node/property changes, then save the project to disk.
Action: duplicate a workspace, reorder or close workspaces, reopen the saved project, and switch across the restored workspaces.
Expected result: workspace order, active workspace/view selection, and node graph content reopen normally, with no visible regression from the persistence overlay moving out of the graph models.

## Residual Risks
- Out-of-scope UI and shell callers still import `ea_node_editor.graph.file_issue_state`; the logic is relocated, but that graph module remains as a packet-local boundary adapter until later packets can migrate those imports.
- The new persistence side table is covered by automated serializer, workspace, and snapshot regressions, but a native desktop smoke pass is still useful for history-heavy and file-repair workflows because the externalized overlay is exercised most deeply there.

## Ready for Integration
- Yes: graph-owned models no longer declare packet-owned persistence envelope state, file-issue logic moved into persistence-owned code, the packet verification and review gate both passed, and the updated regression anchors cover the new boundary.
