# PROJECT_MANAGED_FILES P08: Project Files Summary

## Objective
- Add the compact project-files dialog and project-wide staged/broken summary surfaces for open/save/save-as/recovery flows without turning the app into a full artifact manager.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P03`
- `P04`
- `P05`
- `P07`

## Target Subsystems
- `ea_node_editor/ui/dialogs/project_files_dialog.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/presenters.py`
- `tests/test_project_files_dialog.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_shell_project_session_controller.py`

## Conservative Write Scope
- `ea_node_editor/ui/dialogs/project_files_dialog.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/presenters.py`
- `tests/test_project_files_dialog.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/project_managed_files/P08_project_files_summary_WRAPUP.md`

## Required Behavior
- Add a compact project-files dialog reachable from the shell/menu action path.
- The dialog must summarize managed files, staged items, and broken-file entries using the canonical issue and artifact state from earlier packets.
- Surface staged/broken summaries in open, save, save-as, and recovery prompts where that context materially affects the user choice.
- Keep the v1 UX lightweight: use a dialog and contextual summaries, not a persistent artifact-manager pane.
- Reuse the `Repair file...` flow from `P07` where the summary surface needs to hand users toward remediation.
- Keep the dialog/readout compatible with projects that have only external files, only managed files, or no managed data at all.

## Non-Goals
- No new repair semantics beyond invoking the existing `P07` flow.
- No new import/default policy work beyond the behavior already shipped in `P06`.
- No runtime artifact payload or heavy-output node changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_files_dialog.py tests/test_project_save_as_flow.py tests/test_shell_project_session_controller.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_project_files_dialog.py --ignore=venv -q`

## Expected Artifacts
- `ea_node_editor/ui/dialogs/project_files_dialog.py`
- `tests/test_project_files_dialog.py`
- `docs/specs/work_packets/project_managed_files/P08_project_files_summary_WRAPUP.md`

## Acceptance Criteria
- A compact project-files dialog is reachable from the shell and reports managed/staged/broken state accurately.
- Save, Save As, open, and recovery flows surface staged/broken summaries where applicable.
- The new surfaces remain lightweight and do not become a full artifact-manager workspace.
- Existing projects without managed data remain usable without extra friction.

## Handoff Notes
- `P12` inherits the dialog names and summary surfaces for final docs and QA traceability.
- Record the dialog entry point and summary locations in the wrap-up so the docs packet can describe the shipped UX precisely.
