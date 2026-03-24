# P05 Save As Copy Flow Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/project-managed-files/p05-save-as-copy-flow`
- Commit Owner: `worker`
- Commit SHA: `40d3acf5eb9bd2bfb7ad3ec2ce538e14a9ed6238`
- Changed Files: `ea_node_editor/ui/dialogs/project_save_as_dialog.py`, `ea_node_editor/ui/shell/controllers/project_session_controller.py`, `ea_node_editor/ui/shell/presenters.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/window_actions.py`, `tests/test_project_save_as_flow.py`, `tests/test_shell_project_session_controller.py`, `docs/specs/work_packets/project_managed_files/P05_save_as_copy_flow_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/project_managed_files/P05_save_as_copy_flow_WRAPUP.md`, `ea_node_editor/ui/dialogs/project_save_as_dialog.py`, `ea_node_editor/ui/shell/controllers/project_session_controller.py`, `ea_node_editor/ui/shell/presenters.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/window_actions.py`, `tests/test_project_save_as_flow.py`, `tests/test_shell_project_session_controller.py`
- Save As Choices: `Create a self-contained copy and copy referenced managed files` or `Save the project file only`; both choices leave external file links external.
- Default Selection: `Create a self-contained copy and copy referenced managed files`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_save_as_flow.py tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_project_save_as_flow.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing

- Prerequisite: open a project with at least one managed `artifact://...` file reference; add a staged `artifact-stage://...` reference as well if you want to confirm the no-staging rule.
- Default Save As copy: choose `File > Save Project As...`, leave the default self-contained copy option selected, and save to a new `.sfe` path. Expected result: the active project switches to the new path, referenced managed files are copied into the new sibling `.data/` sidecar, external links stay external, and no `.staging` payloads are copied.
- Project file only option: choose `File > Save Project As...`, switch to `Save the project file only`, and save to a different new path. Expected result: the `.sfe` is written, the active project path switches, and no managed sidecar data is copied into the destination.
- Plain project smoke: run `Save Project As...` on a project without managed data. Expected result: save completes without errors and the new project path becomes active.

## Residual Risks

- When a project still contains staged `artifact-stage://...` references, the default Save As copy intentionally excludes staged payloads and staged metadata, so those refs become unresolved in the new project until later packets add broader warning and repair UX.

## Ready for Integration

- Yes: the packet adds the Save As shell flow, always prompts for managed-data handling, defaults to a self-contained managed copy, and passed the required verification commands.
