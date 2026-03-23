# PROJECT_MANAGED_FILES P01: Artifact Store Foundation

## Objective
- Add the project-managed artifact/store foundation: additive `metadata.artifact_store` persistence, sibling sidecar path helpers, stable managed-file refs, and one central resolver/service contract without changing save/session/UI behavior yet.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/artifact_refs.py`
- `ea_node_editor/persistence/artifact_resolution.py`
- `tests/serializer/round_trip_cases.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_artifact_resolution.py`

## Conservative Write Scope
- `ea_node_editor/settings.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/artifact_refs.py`
- `ea_node_editor/persistence/artifact_resolution.py`
- `tests/serializer/round_trip_cases.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_artifact_resolution.py`
- `docs/specs/work_packets/project_managed_files/P01_artifact_store_foundation_WRAPUP.md`

## Required Behavior
- Introduce a central artifact service and helper types that define the canonical project-managed layout under sibling `<project-stem>.data/` roots, including `assets/`, `artifacts/`, and hidden staging helpers.
- Add additive persistence metadata under `metadata.artifact_store` while keeping schema version `4`; do not introduce a schema-version bump.
- Normalize and round-trip the new metadata through migration and codec paths without duplicating payload bytes into `.sfe`.
- Add stable managed-file reference DTOs and string refs for stored project-managed paths while preserving raw absolute paths and file URLs for external files.
- Add one path/artifact resolver contract that can later resolve external paths, managed refs, and staged refs to absolute local paths at consumer boundaries.
- Keep source-file node properties string-based and backward compatible with existing documents.
- Land narrow persistence/resolution tests that prove the metadata round-trip, sidecar path derivation, resolver behavior, and non-duplication baseline.

## Non-Goals
- No media preview, PDF, or graph-surface adoption yet. `P02` owns consumer routing.
- No staging recovery, autosave, or clean-close scratch handling yet. `P03` owns that lifecycle.
- No save-time promotion, pruning, Save As, or project-copy behavior yet.
- No heavy-output runtime protocol changes yet. `P09` owns execution artifact refs.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py tests/serializer/round_trip_cases.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py --ignore=venv -q`

## Expected Artifacts
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/persistence/artifact_refs.py`
- `ea_node_editor/persistence/artifact_resolution.py`
- `tests/test_project_artifact_store.py`
- `tests/test_project_artifact_resolution.py`
- `docs/specs/work_packets/project_managed_files/P01_artifact_store_foundation_WRAPUP.md`

## Acceptance Criteria
- `.sfe` documents can round-trip additive `metadata.artifact_store` content without changing schema version.
- The new artifact service can derive project sidecar roots and represent managed refs without embedding file bytes into persisted documents.
- A central resolver contract exists for external, managed, and staged refs, even if later packets are still the only adopters.
- Existing external raw-path documents remain loadable and behavior-compatible.

## Handoff Notes
- `P02`, `P03`, `P04`, `P06`, `P09`, `P10`, and `P11` all build on the types and helpers introduced here.
- Record the canonical ref shape, metadata keys, and sidecar directory layout in the wrap-up so later packets reuse the same contract.
