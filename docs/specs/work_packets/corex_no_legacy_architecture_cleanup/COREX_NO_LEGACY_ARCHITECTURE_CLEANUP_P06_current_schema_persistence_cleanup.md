# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P06: Current Schema Persistence Cleanup

## Objective

- Tighten project, preference, session, artifact, and custom workflow persistence to current schemas only, removing old-key and loose input-shape tolerance.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only persistence/tests needed for this packet

## Preconditions

- `P05` is marked `PASS`.

## Execution Dependencies

- `P05`

## Target Subsystems

- `ea_node_editor/app_preferences.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/custom_workflows/global_store.py`
- `tests/test_app_preferences.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P06_current_schema_persistence_cleanup_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/app_preferences.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/custom_workflows/global_store.py`
- `tests/test_app_preferences.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P06_current_schema_persistence_cleanup_WRAPUP.md`

## Required Behavior

- Keep current project schema rejection for pre-current documents, but remove raw dict/list coercion that only exists to tolerate older or malformed current-shape files.
- Remove `_runtime_unresolved_workspaces` fallback in project persistence envelope parsing and related cleanup branches.
- Require `WorkspacePersistenceEnvelope` current keys: `unresolved_nodes`, `unresolved_edges`, and `authored_node_overrides`.
- Require current artifact-store metadata keys such as `relative_path`, `absolute_path`, and current staging-root mapping forms; delete `path`, `root`, and bare-string staging-root aliases.
- Require current app-preferences version only. Do not auto-upgrade v1/v2/v3 preference documents unless the current version number intentionally still is v3.
- Require current recent-session payload shapes and list-only recent project paths.
- Update persistence tests so they assert fail-fast current-schema validation rather than compatibility normalization.

## Non-Goals

- No graph-domain unresolved-overlay state removal; that belongs to `P07`.
- No runtime snapshot metadata cleanup; that belongs to `P11`.
- No docs/requirements wording updates yet.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_graphics_settings_preferences.py tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_project_session_controller_unit.py tests/test_registry_validation.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_app_preferences.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P06_current_schema_persistence_cleanup_WRAPUP.md`

## Acceptance Criteria

- Current-schema documents still round-trip deterministically.
- Pre-current or old-shape documents fail clearly instead of silently migrating through compatibility branches.
- Artifact, preference, and session stores parse only current supported shapes.

## Handoff Notes

- `P07` inherits persistence-envelope behavior and should remove graph-domain state that only existed to carry now-retired overlay payloads.
