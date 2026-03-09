# SHELL_MOD P05: Workspace View and Navigation Extraction

## Objective
- Extract workspace/view navigation, framing, graph search ranking/jump, and parent reveal/focus behavior from `workspace_library_controller.py`.

## Preconditions
- `P04` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_workspace_manager.py`

## Required Behavior
- Extract methods related to:
  - workspace tab refresh and switching
  - view creation/switch and camera save/restore
  - frame/center helpers and bounds accessors
  - graph search rank/search/jump
  - failed-node focus and parent-chain reveal
- Keep controller public method names/return contracts stable.

## Non-Goals
- No node drop/auto-connect extraction.
- No edit/clipboard/history extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_workspace_manager -v`

## Acceptance Criteria
- Controller composes extracted view/nav ops while external behavior remains unchanged.
- Navigation and framing tests pass.

## Handoff Notes
- `P06` extracts drop/connect orchestration next.
