# SHELL_MOD P06: Workspace Drop and Auto-Connect Extraction

## Objective
- Extract node insertion, custom-workflow snapshot placement, and drop auto-connect flows from `workspace_library_controller.py`.

## Preconditions
- `P05` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Extract methods related to:
  - `insert_library_node` + custom workflow snapshot insertion
  - fragment retarget/normalization helper flow
  - auto-connect dropped node to target port/edge
  - request drop orchestration with grouped history
- Preserve grouped history semantics and existing candidate prompt behavior.

## Non-Goals
- No import/export extraction.
- No edit/clipboard/history extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Drop/connect logic resides in helper module(s) and controller remains orchestration facade.
- Existing drop/autoconnect tests pass.

## Handoff Notes
- `P07` extracts edit operations next.
