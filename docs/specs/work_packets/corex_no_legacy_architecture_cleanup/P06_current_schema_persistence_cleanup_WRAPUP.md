## Implementation Summary
- Packet: COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P06 Current Schema Persistence Cleanup
- Branch Label: codex/corex-no-legacy-architecture-cleanup/p06-current-schema-persistence-cleanup
- Commit Owner: worker
- Commit SHA: f966d97d6c474606cd344df7912efec8d44d54da
- Changed Files: ea_node_editor/app_preferences.py; ea_node_editor/persistence/artifact_store.py; ea_node_editor/persistence/migration.py; ea_node_editor/persistence/overlay.py; ea_node_editor/persistence/project_codec.py; ea_node_editor/persistence/session_store.py; tests/test_app_preferences.py; tests/test_graphics_settings_preferences.py; tests/test_project_artifact_store.py; tests/test_project_session_controller_unit.py; tests/test_registry_validation.py; tests/test_serializer_schema_migration.py; docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P06_current_schema_persistence_cleanup_WRAPUP.md
- Artifacts Produced: docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P06_current_schema_persistence_cleanup_WRAPUP.md

- App preferences now accept only the current preferences version and no longer auto-upgrade v1/v2 documents.
- Project persistence now rejects legacy runtime envelope metadata and old workspace envelope alias keys instead of silently normalizing them.
- Artifact-store metadata now requires current `relative_path`, `absolute_path`, and staging-root object forms, rejecting `path`, `root`, and bare-string staging roots.
- Recent-session parsing now requires current object payloads and list-only `recent_project_paths`.
- Tests were updated to cover current-schema round trips, fail-fast legacy-shape rejection, and the accepted workspace navigation authority in session-controller unit stubs.

## Verification
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_graphics_settings_preferences.py tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_project_session_controller_unit.py tests/test_registry_validation.py --ignore=venv -q` -> 143 passed, 16 subtests passed, 32 warnings.
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_project_artifact_store.py tests/test_app_preferences.py --ignore=venv -q` -> 37 passed, 2 subtests passed, 20 warnings.
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing
- Prerequisite: run the application from this packet branch with the project-local virtual environment.
- Open and save a current-schema `.sfe` project that contains normal graph content. Expected result: the project opens, saves, and reloads without changes to visible graph behavior.
- If available, open a current-schema project with temporarily unavailable add-on nodes. Expected result: unresolved nodes remain preserved through save/load using the current `_persistence_envelope` shape.
- Change a graphics preference, restart the app, and confirm the preference persists. Expected result: current v3 preference documents load normally.

## Residual Risks
- Existing Ansys DPF operator rename deprecation warnings appeared during verification and are unrelated to this packet.
- Manual UI coverage remains useful for real saved-project and preferences smoke testing because this packet primarily tightens internal persistence parsing.
- P07 still owns graph-domain unresolved-overlay state removal; P06 only removes legacy/current-shape tolerance in persistence parsing.

## Ready for Integration
- Yes: P06 is ready for integration after passing the full packet verification command and the required review gate.
