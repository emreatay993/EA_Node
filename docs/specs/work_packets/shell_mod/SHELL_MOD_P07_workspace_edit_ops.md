# SHELL_MOD P07: Workspace Edit Operations Extraction

## Objective
- Extract graph edit operations from `workspace_library_controller.py` into dedicated helper module(s).

## Preconditions
- `P06` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Extract methods related to:
  - selected node property/port/collapse mutations
  - connect selected, duplicate/group/ungroup
  - layout align/distribute and overlap hint flow
  - clipboard read/write/copy/cut/paste
  - undo/redo runtime history operations
  - graph interaction request wrappers (`connect/remove/rename/delete`)
- Keep `ControllerResult` contracts stable for request methods.

## Non-Goals
- No workspace/view nav extraction (already in P05).
- No import/export extraction (handled in P08).

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Controller composes extracted edit-ops helper(s).
- Edit, clipboard, and history behavior remains test-equivalent.

## Handoff Notes
- `P08` extracts controller IO flows and modularizes oversized test files.
