# ARCHITECTURE_REFACTOR P03: Project Session Service

## Objective
- Extract project document IO, session/autosave recovery, and project-files coordination from the oversized project-session controller so session behavior is no longer bundled into one broad host-facing class.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_files_dialog.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_files_dialog.py`
- `docs/specs/work_packets/architecture_refactor/P03_project_session_service_WRAPUP.md`

## Required Behavior
- Separate project document IO, autosave/session lifecycle, and project-files or artifact-store coordination into narrower collaborators or services.
- Move modal prompting behind explicit host or callback seams where practical so lower-level service logic stops depending on concrete dialogs.
- Preserve existing menu actions, restore/recovery flows, project-files dialog behavior, and Save/Save As wiring.
- Update inherited session/controller tests when packet-owned dependency contracts change instead of leaving stale unit-test stubs behind.

## Non-Goals
- No workspace-library narrowing beyond what `P02` already established.
- No graph, persistence, runtime, or QML bridge changes.
- No end-user behavior expansion in project-files UX.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py tests/test_project_save_as_flow.py tests/test_project_files_dialog.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P03_project_session_service_WRAPUP.md`

## Acceptance Criteria
- Project-session behavior is owned by smaller services or collaborators instead of one broad controller class.
- Existing recovery, project-file, and save-flow regression anchors stay authoritative and pass.
- The packet-owned verification command passes.

## Handoff Notes
- `P13` will own docs/traceability cleanup for any architecture rename that becomes externally relevant; do not defer known-stale test assertions to that later packet.
