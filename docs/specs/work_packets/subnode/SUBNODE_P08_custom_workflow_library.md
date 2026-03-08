# SUBNODE P08: Custom Workflow Library

## Objective
- Add a project-local custom workflow library source backed by snapshot definitions in project metadata.

## Preconditions
- `P07` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/custom_workflows/*`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Add a `Custom Workflows` library source stored in project metadata rather than the node registry.
- Allow publishing/updating from a selected subnode shell or the currently open subnode scope.
- Save a snapshot definition containing workflow metadata, cached shell port previews, and the subtree payload needed to recreate the subnode.
- Dropping a custom workflow into the canvas must create an independent copied subtree with fresh ids and no live link back to the saved definition.
- Merge the library source into existing library/filter/search UX without registering fake executable node types.

## Non-Goals
- No file import/export yet.
- No linked or synchronized instances.
- No changes to the Python plugin package system.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Published custom workflows appear in the library and can be placed repeatedly as snapshots.
- Updating a saved custom workflow affects future placements only.
- Drag/drop preview and auto-connect use cached shell-port preview data without bypassing the normal graph transform path.

## Handoff Notes
- `P09` must reuse the same metadata codec and snapshot schema when adding `.eawf` import/export.
- Keep node registry and custom workflow library concerns separate.
