# PROJECT_MANAGED_FILES P05: Save As Copy Flow

## Objective
- Add `Save As` plus the explicit managed-data copy-choice flow so users can create a new project path with a self-contained project copy by default, without carrying staging scratch into the destination.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P03`
- `P04`

## Target Subsystems
- `ea_node_editor/ui/dialogs/project_save_as_dialog.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/presenters.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`

## Conservative Write Scope
- `ea_node_editor/ui/dialogs/project_save_as_dialog.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/presenters.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/project_managed_files/P05_save_as_copy_flow_WRAPUP.md`

## Required Behavior
- Add a `Save As` path through the current shell/menu flow.
- `Save As` must always ask the user how managed project data should be handled.
- The default selection must create a self-contained copy of the project plus the currently referenced managed files in a new sibling `.data/` sidecar.
- Exclude staging and scratch data from the default copy behavior.
- Keep unresolved external files and external-link refs as external unless the chosen `Save As` path explicitly asks to internalize them.
- After successful `Save As`, update the active project/session path and recent-project state to the new location.
- Add narrow tests that prove the dialog default, managed-data copy behavior, and no-staging-by-default rule.

## Non-Goals
- No app preference for default import mode yet. `P06` owns that.
- No node-level missing-file repair flow yet. `P07` owns that.
- No compact project-files dialog yet. `P08` owns the general summary surface.
- No runtime artifact-ref protocol changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_save_as_flow.py tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_project_save_as_flow.py --ignore=venv -q`

## Expected Artifacts
- `ea_node_editor/ui/dialogs/project_save_as_dialog.py`
- `tests/test_project_save_as_flow.py`
- `docs/specs/work_packets/project_managed_files/P05_save_as_copy_flow_WRAPUP.md`

## Acceptance Criteria
- `Save As` exists in the shell flow and always prompts for managed-data handling.
- The default selection creates a self-contained project copy with currently referenced managed files and no staging scratch.
- Successful `Save As` switches the active project/session path to the new location.
- Existing plain projects without managed data still work through `Save As` without regression.

## Handoff Notes
- `P08` inherits the dialog and summary surfaces from this packet when it adds project-wide staged/broken counts.
- Record the user-visible `Save As` choices and default selection in the wrap-up so later packets stay aligned with the approved UX.
