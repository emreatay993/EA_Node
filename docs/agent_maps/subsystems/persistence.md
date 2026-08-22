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

## Focused Tests
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`

## Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_project_save_as_flow.py tests/test_project_artifact_store.py -q
```
