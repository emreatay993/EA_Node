# ARCHITECTURE_MAINTAINABILITY_REFACTOR P04: Project Session Authority Collapse

## Objective
- Make one active authority for save, save-as, open, recover, autosave, and project-files flows and remove duplicate controller-side implementations instead of retaining facade-plus-service duplication.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_files_dialog.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_files_dialog.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P04_project_session_authority_collapse_WRAPUP.md`

## Required Behavior
- Choose one active implementation path for project/session open, save, save-as, recover, autosave, and project-files flows.
- Delete duplicate controller-side implementations after packet-owned callers are routed through the chosen authority.
- Keep `ProjectSessionController` as a thin facade that orchestrates one authoritative project/session service path.
- Update the inherited project-session, save-as, and project-files regression anchors in place when authority boundaries move.

## Non-Goals
- No session-envelope payload cleanup yet; that belongs to `P05`.
- No graph or persistence-boundary relocation yet.
- No new save/recovery UX.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py tests/test_project_save_as_flow.py tests/test_project_files_dialog.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P04_project_session_authority_collapse_WRAPUP.md`

## Acceptance Criteria
- One authoritative project/session implementation path owns save, save-as, open, recover, autosave, and project-files behavior.
- Duplicate controller-side implementations are removed rather than left behind as fallback paths.
- The inherited session/save/project-files regression anchors pass.

## Handoff Notes
- `P05` should clean up session payload ownership and metadata structure on top of this single authority instead of trying to resolve both problems at once.
