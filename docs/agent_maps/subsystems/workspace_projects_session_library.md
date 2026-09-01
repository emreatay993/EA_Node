# Workspace, Projects, Session, And Library

## Purpose
Use this for workspace tabs, project session control, project files, workflow library, drop-connect, and workspace library surfaces.

## Start Here
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/workspace/`
- `ea_node_editor/graph/project_state.py` and `ea_node_editor/graph/workspace_state.py` for project/workspace data records.
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workflow_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `tests/test_workspace_library_controller_unit.py`

## Do Not Start Here
- Persistence codec internals before checking project/session services.
- QML tab UI before checking workspace models and bridges.

## Common Changes
- Keep session orchestration in shell project/session controllers.
- Route workspace tab and library UI through bridge/model surfaces.
- Route node-library filtering, category ancestors/options/tree, DPF taxonomy, and custom-workflow categories through `ui/shell/library_projection.py` and the presenter cache. Do not add registry query/category APIs or a second category cache.
- For node-owned project files, coordinate with persistence artifact routes; workspace renames also rename the readable `workspaces/<Workspace [hash]>` sidecar folder through the project artifact store.
- Workspace order and active-workspace changes participate in `ProjectData.document_epoch()` for autosave skips. Use `WorkspaceManager`/`sync_project_workspace_ownership(...)` paths so project metadata and project document revision stay aligned.
## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_workspace_library_controller_unit.py --ignore=venv -q
```

## Breadcrumbs
- [Workspace Tabs And Library Context Menus](../feature_routes/workspace_tabs_library_context_menus.md)
- [Project Session, Project Files, And Node Files](../feature_routes/project_session_files_managed_artifacts.md)
- [Workflow Library And Drop Connect](../feature_routes/workflow_library_drop_connect.md)

## Update Triggers
Update when workspace/session/library controllers, graph project/workspace data ownership, project replacement/import flows, project files, workflow library, or tab routing changes.

## 2026-07-11 Performance Ownership

- Library rows/category paths and inspector pin/data-type projections reuse existing registry/workflow revisions. Session/autosave owners consume owned non-mutating document mappings and one encoded snapshot rather than recopying them.
