# PROJECT_MANAGED_FILES P04: Save Promotion Prune

## Objective
- Make explicit `Save` commit the current referenced staged managed files into permanent sidecar storage, replace current versions instead of retaining history, and prune orphaned managed files no longer referenced by the saved project state.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P03`

## Target Subsystems
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `tests/serializer/round_trip_cases.py`
- `tests/test_project_artifact_store.py`
- `tests/test_shell_project_session_controller.py`

## Conservative Write Scope
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `tests/serializer/round_trip_cases.py`
- `tests/test_project_artifact_store.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/project_managed_files/P04_save_promotion_prune_WRAPUP.md`

## Required Behavior
- On explicit `Save`, promote only the currently referenced staged managed files into the permanent sibling `<project-stem>.data/` sidecar.
- Keep staged-to-permanent promotion replace-based: the current logical output or managed import replaces the previous permanent copy rather than creating version history.
- Remove permanent managed files that are no longer referenced by the saved project state.
- Ensure the first explicit save of an unsaved project can materialize the sidecar layout and commit referenced staging into it.
- Leave external absolute paths and file URLs untouched.
- Keep `.sfe`, autosave, and session documents storing refs and metadata only, not promoted payload bytes.

## Non-Goals
- No Save As flow or copy-choice dialog yet. `P05` owns that.
- No source import preference UX yet. `P06` owns browse defaults and managed-copy import behavior.
- No missing-file/project-summary UI yet.
- No execution protocol changes yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_shell_project_session_controller.py tests/serializer/round_trip_cases.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/project_managed_files/P04_save_promotion_prune_WRAPUP.md`

## Acceptance Criteria
- Explicit `Save` writes referenced staged managed files into permanent sidecar storage.
- Stale permanent managed files are pruned when they are no longer referenced by the saved project state.
- Re-saving a logical managed asset/output replaces the current permanent version rather than accumulating history.
- Existing external-path projects still save normally.

## Handoff Notes
- `P05` inherits the promotion/prune semantics when it adds Save As cloning choices.
- Record the exact prune rules and replacement semantics in the wrap-up so later packets do not accidentally preserve orphan data.
