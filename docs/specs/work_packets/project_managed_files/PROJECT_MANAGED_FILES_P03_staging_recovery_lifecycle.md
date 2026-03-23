# PROJECT_MANAGED_FILES P03: Staging Recovery Lifecycle

## Objective
- Add temp staging and crash-only recovery for managed imports and stored outputs so unsaved projects, autosave, and session restore can preserve staged refs without turning staging into permanent project data.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/project_managed_files/P03_staging_recovery_lifecycle_WRAPUP.md`

## Required Behavior
- Add unsaved-project staging roots in temp storage for managed imports and `stored` outputs before the first real project save.
- Keep saved projects using staging-first writes until explicit `Save`, rather than writing directly into permanent sidecar locations during node execution or import.
- Persist enough staging metadata and root hints through session/autosave state to recover staged refs after crashes or autosave recovery.
- On clean close without save, discard staged scratch data instead of silently promoting it.
- Ensure staging replacement semantics are slot-based: regenerating the same logical output replaces the earlier staged copy rather than accumulating scratch history.
- Keep session and autosave payloads lightweight by persisting refs/metadata only, never staged payload bytes.

## Non-Goals
- No permanent sidecar promotion or prune-on-save yet. `P04` owns explicit save commits.
- No Save As copy/clone flow yet. `P05` owns that.
- No project-files summary or broken-file UX yet.
- No concrete heavy-output UI adopter yet. `P11` owns the first user-facing node contract.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_project_session_controller.py tests/test_project_session_controller_unit.py tests/test_project_artifact_store.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_project_session_controller.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/project_managed_files/P03_staging_recovery_lifecycle_WRAPUP.md`

## Acceptance Criteria
- Unsaved and saved projects can hold staged managed refs before `Save` without writing permanent project data prematurely.
- Session restore and autosave recovery can recover staged refs after crash-style interruption.
- Clean close without save discards staged scratch data.
- Session/autosave documents still store metadata and refs only, not binary payloads.

## Handoff Notes
- `P04`, `P05`, `P10`, and `P11` inherit the staging-root and logical-slot semantics from this packet.
- Record the temp-root policy, recovery hints, and clean-close cleanup triggers in the wrap-up so later packets do not duplicate lifecycle logic.
