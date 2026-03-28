# ARCHITECTURE_MAINTAINABILITY_REFACTOR P05: Session Envelope Metadata Cleanup

## Objective
- Stop storing a full `project_doc` in recent-session payloads, keep full-document recovery in autosave only, replace typeless `project.metadata` integration-bus usage with typed substructures, and keep session-state ownership explicit.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`

## Conservative Write Scope
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P05_session_envelope_metadata_cleanup_WRAPUP.md`

## Required Behavior
- Remove full `project_doc` duplication from recent-session payloads and keep full-document recovery responsibility inside autosave only.
- Replace typeless packet-owned metadata buses with typed or clearly namespaced substructures so session-state ownership is explicit and discoverable.
- Preserve current recovery, recent-project, save-as, and staged-artifact semantics while changing where session data is stored and how it is shaped.
- Update inherited session-store and serializer/migration regression anchors in place when the recent-session or metadata contract changes.

## Non-Goals
- No graph-model persistence relocation yet; that belongs to `P06`.
- No graph mutation-path cleanup yet.
- No new recent-project or recovery UX.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py tests/test_project_save_as_flow.py tests/test_serializer.py tests/test_serializer_schema_migration.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_serializer_schema_migration.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P05_session_envelope_metadata_cleanup_WRAPUP.md`

## Acceptance Criteria
- Recent-session payloads no longer embed a full `project_doc`.
- Autosave remains the only full-document recovery authority.
- Packet-owned metadata structures become explicit enough that the inherited session and serializer regression anchors pass without typeless integration-bus fallbacks.

## Handoff Notes
- `P06` should assume session payload ownership is now explicit and move graph-persistence coupling out of graph core on top of that cleaner persistence boundary.
