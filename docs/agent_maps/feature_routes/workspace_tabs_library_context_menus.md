# Workspace Tabs And Library Context Menus

## Purpose
Use this for workspace tabs, view tabs, labeled tab strip visual states, library context menus, workspace bridge payloads, and library panes.

## Start Here
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellLabeledTabStrip.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `ea_node_editor/ui_qml/components/shell/NodeBrowserOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryNodeVisual.qml`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui/shell/library_projection.py`
- `ea_node_editor/ui/shell/quick_insert_projection.py`

## Design Reference
- `ShellLabeledTabStrip.qml` owns production view/workspace pill styling; production behavior stays in shell QML.
- `NodeBrowserOverlay.qml` owns the explicit three-column browser opened through `ShellLibraryBridge.request_open_node_browser(...)`, including transient category/query/direction selection, category headers with two-column node rows in the middle pane, and optional scene-anchored insertion through the existing library and canvas-drop commands.
- `ConnectionQuickInsertOverlay.qml` owns the compact result list for both connection-origin and canvas-mode Quick Insert. Ctrl+B routes through `window_actions.py` to canvas mode at the viewport center; explicit Node Browser requests remain separate.
- Connection-origin Quick Insert candidates come from the Python presenter and the active registry data-type catalog. Compatibility is target-directional and includes the target input's ordered accepted-type union so the offered nodes agree with graph mutation.
- `library_projection.py` is the sole node-library query/category owner. It derives filters, ancestor paths, category options/tree, grouped/display rows, DPF taxonomy, and custom-workflow categories from the same cached combined projected items. `LibraryPresenter` builds one category tree per filtered cache request and keeps no separate registry-category cache; `NodeRegistry` exposes no Library filter/category API.
- The presenter normalizes dragged and candidate port payloads to `PortSpec`, excludes hidden candidates, and delegates kind/type decisions to graph-owned `ports_compatible(...)`; direction and neutral-flow routing stay local, and `GraphInvariantKernel` remains the final edge gate.
- `tests/qml_quick/tst_graph_node_host.qml` owns the pure-QML `LibraryNodeVisual` flowchart aspect-ratio fit check. `tests/test_flowchart_surfaces.py` retains geometry and Python-owned canvas drop-preview integration.

## Related Help Reference
- `ea_node_editor/ui/dialogs/input_reference_dialog.py` documents user-facing workspace tab, view tab, library row, library drag/drop, and custom workflow context-menu gestures. Update it when those interactions change.

## Focused Verification
```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QUICK_CONTROLS_STYLE = "Basic"
& (Join-Path $env:QT_ROOT "bin\qmltestrunner.exe") -input tests/qml_quick/tst_graph_node_host.qml -eventdelay 0 -keydelay 0 -mousedelay 0 -o -,txt
Remove-Item Env:QT_QPA_PLATFORM, Env:QT_QUICK_CONTROLS_STYLE -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py tests/test_library_projection.py tests/test_quick_insert_projection.py tests/test_shell_library_projection_cache.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_workspace_library_controller_unit.py --ignore=venv -q
```

## Breadcrumbs
- [Workspace, Projects, Session, And Library](../subsystems/workspace_projects_session_library.md)
- [Workflow Library And Drop Connect](workflow_library_drop_connect.md)

## Update Triggers
Update when workspace tabs, view tabs, labeled tab strip visual states, library menus or hidden internal descriptors, Node Browser or canvas Quick Insert behavior, shell bridge models, library tests, or Help reference tab/library coverage change.

## 2026-07-11 Performance Ownership

- Library rows and category paths cache until the registry/workflow revision changes; inspector pin/data-type projection follows the same owner revisions. Do not add a persistent or generic presenter cache.
