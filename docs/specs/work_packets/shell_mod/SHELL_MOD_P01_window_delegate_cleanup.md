# SHELL_MOD P01: Window Delegate Cleanup

## Objective
- Remove dynamic delegation in `ShellWindow` and replace it with explicit static delegation surfaces.

## Preconditions
- `P00` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).
- No later SHELL_MOD packet is in progress.

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`

## Required Behavior
- Remove `_DELEGATED_METHODS` and `__getattr__` from `ShellWindow`.
- Add explicit wrapper methods or explicit controller helper surfaces for every call path that previously used dynamic delegation.
- Keep all existing QML `@pyqtSlot` and `@pyqtProperty` signatures intact.
- Keep behavior equivalent for run/session/workspace flows.

## Non-Goals
- No action/menu extraction in this packet.
- No library/inspector payload extraction in this packet.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_shell_run_controller tests.test_shell_project_session_controller -v`

## Acceptance Criteria
- No dynamic delegation remains in `ShellWindow`.
- Existing tests for shell + run + project session pass unchanged in behavior.

## Handoff Notes
- `P02` will extract action/menu setup and should build on explicit call surfaces introduced here.
