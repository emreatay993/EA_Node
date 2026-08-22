# Project Session, Project Files, And Node Files


## Start Here
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`
- `ea_node_editor/ui/dialogs/project_files_dialog.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/artifact_resolution.py`
- `ea_node_editor/workspace/`

## Notes
- Startup session restore keeps the active project empty instead of reopening the saved `last_session.json` project path; `ProjectSessionLifecycleService.restore_session()` still keeps that path in Recent Projects and uses it only as an autosave comparison/recovery baseline.
- Project Save/Save As calls `ProjectArtifactStore.migrate_workspace_artifact_folders(...)` before promotion so legacy `nodes/<node-folder>/...` entries are rewritten under `workspaces/<Workspace [hash]>/nodes/<Node [hash]>/...` when the user saves.
- `DocumentIOService.save_project(...)` and `save_project_as(...)` call `serializer.to_persistent_document(project)` before store migration, destination copying, artifact promotion, file writing, live-property rewrites, or project-path mutation. That preflight validates typed `RuntimeArtifactRef` carriers and literal `saved://`/`temp://` properties against the existing `ProjectArtifactStore` metadata and exact `runtime_artifact` descriptor, so a bad reference leaves both the project and destination untouched.
- Workspace rename updates the readable workspace folder prefix through `WorkspaceNavigationController.rename_workspace_by_id(...)` and `ProjectArtifactStore.rename_workspace_artifact_folder(...)`; the hash suffix remains stable.
- Staged artifact resolution honors an explicit session `staging_root` before falling back to a saved project sidecar, and staged `slot` metadata is preserved when promoted to managed artifact metadata.
- Media, tabular, and web-page local HTML import paths use shell-side source import targets to convert selected files into staged `temp://` refs before save promotion rewrites them to `saved://` refs. Those transient refs are permitted before promotion, but the final persistent-document write rejects any that remain.
- After successful preflight, `commit_referenced_artifacts(...)` promotes referenced staged entries and `rewrite_project_artifact_refs(...)` converts nested temp literals and typed artifact carriers to saved strings. The promoted descriptor remains in managed metadata, and live node properties change only after the project document is written successfully.
- Clipboard-only raw media payloads use the same staged artifact store path through `ShellHostPresenter.stage_clipboard_paste_bytes(...)`; the created node stores the resulting `temp://` ref so project save promotion can rewrite it to `saved://`.
- Project review deck export must enumerate evidence from project refs and artifact-store metadata, not by raw sidecar folder scanning. `ea_node_editor/ui/project_review_deck.py` builds the reusable slide plan from referenced `saved://` / `temp://` entries, then verifies resolved paths before image/PDF evidence is embedded.
- `examples/project_review_deck_airworthiness/rotor_llp_review_showcase.cxproj` is the committed Project Review Deck showcase for ref-first managed evidence, PDF Panel persisted-page rendering, web-preview artifacts, unsupported-file warnings, and optional PowerPoint template export.
- `ProjectSessionLifecycleService.persist_session(project_doc)` honors caller-supplied runtime documents, snapshots them with `ProjectDocumentSnapshot.from_owned_document(...)`, and keeps the recent-session payload metadata-only; Save/Save As should keep using their normal persistent-document write path.
- Autosave ticks sync active view and script-editor metadata, compare the runtime-only project document epoch, and skip `serializer.to_document(...)` plus `SessionAutosaveStore.autosave_if_changed(...)` when the epoch and last fingerprint are unchanged.
- Manual Save and Save As snapshot the current `ScriptEditorModel` state immediately before persistent document conversion. Project open restores through the existing script-editor panel adapter; autosave, session, and close synchronization stay on `ProjectSessionLifecycleService._sync_session_state()`.
- Artifact-store, workflow, passive-style preset, and script-editor metadata writers should call `ProjectData.replace_metadata(...)` so the autosave epoch changes without hashing full project metadata on idle ticks.
- Project install/open/new flows reset `ViewerHostService` before `ViewerSessionBridge.project_loaded(...)` reseeds project viewer projections; this clears native overlay bindings, cached previews, and viewer view state before fixed `(workspace_id, node_id)` viewer keys are reused.


## Breadcrumbs
- [Persistence, Documents, Artifacts, And Migrations](../subsystems/persistence.md)
- [Workspace-Scoped Node Files And Data](managed_artifacts_project_data.md)


## 2026-07-11 Performance Ownership

- Empty or fully workspace-scoped stores skip artifact-owner/migration scans. Autosave consumes owned non-mutating mappings, one JSON encoding, and SHA-256 fingerprints; mixed legacy stores retain migration behavior.
