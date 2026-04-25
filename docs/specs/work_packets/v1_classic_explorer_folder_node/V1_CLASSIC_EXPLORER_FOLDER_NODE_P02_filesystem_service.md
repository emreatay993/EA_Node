# V1_CLASSIC_EXPLORER_FOLDER_NODE P02: Filesystem Service

## Objective
- Add a UI-independent filesystem service for real-directory browsing, metadata listing, sorting/filtering, path normalization, and confirmed file mutations used by the V1 Classic Explorer node.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only source/test files needed for the filesystem service

## Preconditions
- `P00` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/ui/folder_explorer/__init__.py`
- `ea_node_editor/ui/folder_explorer/filesystem_service.py`
- `tests/test_folder_explorer_filesystem_service.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_files_dialog.py`

## Conservative Write Scope
- `ea_node_editor/ui/folder_explorer/__init__.py`
- `ea_node_editor/ui/folder_explorer/filesystem_service.py`
- `tests/test_folder_explorer_filesystem_service.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_files_dialog.py`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P02_filesystem_service_WRAPUP.md`

## Source Public Entry Points
- `FolderExplorerFilesystemService` under `ea_node_editor.ui.folder_explorer`.
- Immutable listing/entry DTOs for folder contents.
- Mutation methods for new folder, rename, delete, copy, cut, paste, and copy-path formatting.

## Regression Public Entry Points
- Temporary-directory tests for listing, sorting, filtering, and mutations.
- Existing project-file mutation confirmation tests remain unchanged and continue to pass.

## State Owner
- The service owns short-lived filesystem operation state only.
- Persistent node state and QML navigation state are out of scope.

## Allowed Dependencies
- Python standard library: `pathlib`, `os`, `shutil`, `stat`, `datetime`, and typing/dataclasses.
- Existing project test helpers and temporary-directory fixtures.

## Required Behavior
- Add `FolderExplorerFilesystemService` and immutable DTOs for directory entries and listings under `ea_node_editor.ui.folder_explorer`.
- Support directory listing, path normalization, parent/breadcrumb helpers, sorting, and case-insensitive filtering.
- Support confirmed new-folder, rename, delete, copy, cut, paste, and copy-path operations.
- Fail expected filesystem errors as structured service errors that bridge callers can present without crashing.

## Required Invariants
- Listing returns stable entries with name, absolute path, kind (`file` or `folder`), modified timestamp, extension/type label, and display size.
- Sorting supports at least `name`, `type`, `size`, and `modified`, with folders grouped before files for name sorting.
- Search/filtering is case-insensitive and never mutates filesystem state.
- Mutating methods require an explicit confirmation argument; unconfirmed calls fail without side effects.
- Paste collision policy is fail-fast for V1: do not silently overwrite existing files or folders.
- Delete is real deletion after confirmation and is limited to the selected path; tests must cover temp directories only.
- Service code does not call shell commands for file mutations.

## Non-Goals
- No QML UI or graph bridge routing.
- No app-global preferences or project persistence.
- No recycle-bin integration or shell-specific command execution.

## Forbidden Shortcuts
- Do not call Windows shell commands or `subprocess` for mutations.
- Do not add QML or graph bridge code in this packet.
- Do not store service state in project documents or app preferences.
- Do not reuse `ProjectArtifactStore` for arbitrary real-filesystem browsing; keep managed-project-file behavior separate.

## Required Tests
- Add temp-directory listing tests for folders/files, size/type/modified metadata, sorting, and search filtering.
- Add mutation tests proving confirmation is required and confirmed operations mutate only the intended temp paths.
- Add copy/cut/paste collision tests that prove existing targets are not overwritten.
- Run existing project-file tests to ensure the new service does not regress managed-file workflows.

## Verification Anchor Handoff
- Later bridge or QML packets that change service method names, DTO field names, or collision semantics must inherit and update `tests/test_folder_explorer_filesystem_service.py`.
- Later packets may add UI coverage without duplicating the pure temp-directory service assertions.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_folder_explorer_filesystem_service.py tests/test_project_artifact_store.py tests/test_project_files_dialog.py --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_folder_explorer_filesystem_service.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P02_filesystem_service_WRAPUP.md`

## Acceptance Criteria
- The service can list a real directory and returns deterministic Explorer-style metadata.
- Confirmed mutations work in temp-directory tests; unconfirmed mutations have no side effects.
- Copy/cut/paste never silently overwrites existing targets.
- Managed project-file tests still pass.

## Handoff Notes
- `P03` owns bridge confirmation prompts and command routing to this service.
- If the service public method names change after this packet, later packets must inherit and update `tests/test_folder_explorer_filesystem_service.py`.
