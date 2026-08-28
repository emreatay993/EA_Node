# Persistence, Documents, Artifacts, And Migrations

## Purpose
Use this for `.cxproj` documents, serializers, migrations, workspace-scoped project files, artifact stores, and session persistence.

## Start Here
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/artifact_refs.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/artifact_resolution.py`
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`

## Boundaries
- Keep document conversion and legacy-envelope handling in persistence.
- Keep runtime snapshot and worker code independent of persistence internals.
- Route workspace-scoped `in`/`out`/`tmp` files through the artifact store and resolution helpers.
- Persistent `ImageValue` properties externalize to content-addressed PNG sidecars only at save time.
- Save and Save As use the generic staged/managed artifact paths; no product-specific importer owns a special promotion path.
- Keep protected properties encrypted and reject unresolved add-ons before final writes.
- Persist Python Script source and authored decorator settings as ordinary node
  properties; resolve the declaration from source instead of storing a second manifest.
- Persist `media.panel` authored properties and exact per-instance Source exposure through the normal node document path. The removed pre-cutover media identities are unknown types with no alias or migration; current project/fragment/history paths preserve serialized exposure without consulting app preferences.
- Project install/new/open calls the attached execution runtime's project-session reset after existing shell runtime-state cleanup and before replacing the graph model. T03 clears session-only solutions here; durable repository binding remains deferred and persistence does not become a second scheduler owner.

## Focused Tests
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_media_panel_creation_preferences.py`
- `tests/serializer/round_trip_cases.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_project_save_as_flow.py tests/test_project_artifact_store.py -q
```
