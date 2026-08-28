# Workspace-Scoped Node Files And Data

## Purpose
Use this for workspace-scoped node project files, saved/temporary artifact refs, runtime artifact integrity, transactional staged cleanup, artifact cache metadata, and project data repair.

## Start Here
- `ea_node_editor/persistence/artifact_refs.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/artifact_resolution.py`
- `ea_node_editor/persistence/solution_repository.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/file_issues.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui/dialogs/project_files_dialog.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_artifact_resolution.py`

## Notes
- The OS sidecar layout is `<project>.data/workspaces/<Workspace [hash]>/nodes/<Node [hash]>/{in,out,tmp}/...`; the workspace hash is stable from `workspace_id`, while the readable prefix follows workspace renames.
- `ProjectArtifactStore.migrate_workspace_artifact_folders(...)` accepts legacy `nodes/<node-folder>/...` metadata and moves only registered artifact payloads into the workspace-scoped layout on Save/Save As; unknown extra files in legacy folders are left alone.
- Raw clipboard media imports are node-first staged artifacts: shell code writes bytes under the node temp input path, registers MIME/size/hash metadata, stores a `temp://` ref on the media or web node, and relies on the normal save path to promote referenced artifacts to `saved://`.
- Project review deck evidence discovery is ref-first: include only referenced managed/staged artifact entries, resolve paths through `ProjectArtifactStore`/`ProjectArtifactResolver`, and treat stale sidecar files or unsupported extensions as warnings instead of slides.
- Artifact-store metadata writes should flow through `ProjectData.replace_metadata(...)` via project session services, shell presenters, or bridge fallback helpers so no-change autosave can rely on the project document epoch instead of serializing the whole document.
- Runtime artifact resolution validates catalog identity, active-store descriptor/target ownership, and current file or directory integrity under the trusted store root.
- `ProjectArtifactStore.inspect_durable_artifact(...)` is the callback-free durable inspection route: it accepts only an exact managed runtime ref, compares the owned entry and descriptor fields directly, then runs bounded no-follow content integrity. It never invokes catalog validators or methods on the value.
- Durable solution output may retain a managed `RuntimeArtifactRef` only when the shared runtime-value gate reuses that same trusted resolution/content-integrity path. Staged refs, raw `saved://`/`temp://` strings, private paths, handles, and invalid descriptor/content bindings remain session-only and write no durable result bytes.
- Durable solution files share the project-owned sidecar root under `solutions/v1` but do not enter artifact-store metadata or its pre-project-commit prune. The solution repository owns immutable generations/reachability; project transaction coordination remains separate.
- A typed persisted artifact property accepts either a `RuntimeArtifactRef` carrier or a literal `saved://`/`temp://` string only when the owned managed/staged store entry has the exact `runtime_artifact` descriptor and its concrete type is catalog-compatible with the property's `persistence_data_type_id`. `to_persistent_document()` performs this metadata-only preflight before Save/Save As mutation. Staged refs are valid only until promotion; `commit_referenced_artifacts(...)` plus `rewrite_project_artifact_refs(...)` converts nested temp literals and carriers to saved strings while retaining the descriptor in managed metadata.
- Staged replacement and `discard_staged_entries(...)` / `discard_staged_paths(...)` prevalidate the whole batch before mutation or deletion. Reject absolute hints, traversal, symlink/reparse/special targets, managed paths, and tracked overlaps; safe file/directory/missing targets preserve the unsaved staging root.
- Cleanup remains best effort after prevalidation: a locked file can leave untracked residue, and a same-user post-`lstat` path-swap window remains. Closing that window requires Windows handle-relative deletion rather than path-based removal.
## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_project_artifact_store.py tests/test_solution_repository.py -q
```

## Breadcrumbs
- [Persistence, Documents, Artifacts, And Migrations](../subsystems/persistence.md)
- [Project Session, Project Files, And Node Files](project_session_files_managed_artifacts.md)

## Update Triggers
Update when artifact refs/integrity, typed persisted-artifact descriptor ownership, staged replacement/discard safety, node-owned files, project files dialog, project review deck evidence discovery, temporary artifacts, or artifact tests change.

## 2026-07-11 Performance Ownership

- `ProjectArtifactStore` early exits only when the store is empty or completely workspace-scoped. Any mixed legacy ownership continues through the existing lookup and migration path.
