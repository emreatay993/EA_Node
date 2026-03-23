# PROJECT_MANAGED_FILES P07: File Issue Node Repair

## Objective
- Surface missing-file warnings on both owner and consumer nodes and add the lightweight node-level `Repair file...` flow, including managed/external conversion paths where needed to restore usability.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P06`

## Target Subsystems
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfacePathEditor.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`
- `tests/test_project_file_issues.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `ea_node_editor/graph/file_issue_state.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfacePathEditor.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`
- `tests/test_project_file_issues.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/project_managed_files/P07_file_issue_node_repair_WRAPUP.md`

## Required Behavior
- Opening a project with missing external files or missing managed files must stay non-blocking.
- Add file-issue detection based on resolver results so owner nodes and consumer nodes can expose broken-file state.
- Show warning indicators on both the node that owns the path/ref and nodes that currently consume the missing file.
- Add a single lightweight node-level action flow centered on `Repair file...`.
- `Repair file...` must support relinking the missing file and, where appropriate, converting between managed copy and external link without requiring a project reload.
- After repair, the warning state must clear and affected previews/consumers must become usable again.
- Keep the flow lightweight; do not add a full project-wide manager pane here.

## Non-Goals
- No compact project-files dialog yet. `P08` owns project-wide summaries.
- No Save As or import-default work here except reuse of `P05` and `P06` behavior.
- No heavy-output runtime or Process Run UI changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_file_issues.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_project_file_issues.py --ignore=venv -q`

## Expected Artifacts
- `ea_node_editor/graph/file_issue_state.py`
- `tests/test_project_file_issues.py`
- `docs/specs/work_packets/project_managed_files/P07_file_issue_node_repair_WRAPUP.md`

## Acceptance Criteria
- Projects with missing managed or external files still open normally.
- Owner nodes and consumer nodes both surface broken-file warnings.
- `Repair file...` can restore usability without reopening the project.
- Managed/external conversion flows, where offered, reuse the import semantics from `P06`.

## Handoff Notes
- `P08` inherits the issue state and repair entry points when it adds project-wide summaries.
- Record the warning-state source of truth and the exact repair action entry points in the wrap-up so later packets do not fork the issue model.
