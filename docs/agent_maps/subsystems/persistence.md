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
- `ea_node_editor/persistence/solution_repository.py`
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
- `solution_repository.py` is the persistence-only concrete implementation of the execution-owned durable backend port. Its schema-1 sidecar is `<project-stem>.data/solutions/v1`: bind reads only the committed manifest set, lookup reads one node manifest and record, and payload resolution structurally decodes one result blob without catalog callbacks before the execution-owned durable gate checks types. Logical IDs are full tagged SHA-256 path keys; immutable no-clobber writes publish blob, record, node manifest, then manifest set. Build, validate, reachability, and active-prune protection share one aggregate-bound generation inspector.
- T07 repository methods may stage immutable records, build/validate candidate generations, enumerate validated reachability, and prune explicitly supplied safe unreachable files. They do not update project metadata, write/replace `.cxproj`, switch Save As binding, or invoke pruning from lifecycle code; those commit operations remain Save/Save As work.
- Project install/new/open resets the execution runtime and then binds the decoded `metadata.solution_store` pointer before replacing the graph model. Missing, malformed, unsupported, corrupt, or unsafe cache metadata preserves authored data and installs one session-only result; persistence never becomes a scheduler owner.

## Focused Tests
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_project_save_as_flow.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_solution_repository.py`
- `tests/test_media_panel_creation_preferences.py`
- `tests/serializer/round_trip_cases.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_solution_repository.py tests/test_serializer.py tests/test_project_artifact_store.py -q
```
