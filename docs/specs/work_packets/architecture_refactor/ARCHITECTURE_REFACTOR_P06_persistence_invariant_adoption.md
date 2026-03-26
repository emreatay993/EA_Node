# ARCHITECTURE_REFACTOR P06: Persistence Invariant Adoption

## Objective
- Make migration and codec paths adopt the shared graph invariant authority so load-time normalization, serializer migration, and codec reconstruction stop drifting away from graph-edit policy, while making persistence-envelope and runtime-versus-authored document-flavor boundaries explicit.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/graph/model.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/graph/`
- `tests/serializer/schema_cases.py`
- `tests/test_persistence_package_imports.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_serializer.py`
- `tests/test_registry_validation.py`

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/graph/`
- `tests/serializer/schema_cases.py`
- `tests/test_persistence_package_imports.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_serializer.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/architecture_refactor/P06_persistence_invariant_adoption_WRAPUP.md`

## Required Behavior
- Route persistence migration and codec reconstruction through the shared graph invariant kernel introduced in `P05`.
- Eliminate persistence-only policy copies when they would produce different port, edge, or node normalization than graph-edit code.
- Make runtime-versus-authored document flavor explicit at the codec boundary through named policy, type, or enum-level semantics instead of relying on implicit preservation sidecars alone.
- Wrap unresolved/authored override persistence data behind clearly named persistence-envelope helpers instead of treating it like ordinary live-domain `WorkspaceData` state.
- Update inherited serializer, schema, and import-layer tests in scope when the new shared authority or document-flavor boundary changes where assertions belong.
- Preserve `.sfe` document format and published persistence semantics.

## Non-Goals
- No new file-format features.
- No shell, runtime, or QML bridge changes.
- No release/docs cleanup yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_serializer.py tests/test_registry_validation.py tests/test_persistence_package_imports.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_persistence_package_imports.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P06_persistence_invariant_adoption_WRAPUP.md`

## Acceptance Criteria
- Migration and codec code share the same invariant authority as graph-edit paths.
- Persistence overlays and runtime-versus-authored document flavor are explicit enough that packet-owned serializer/schema regressions describe one clear contract instead of hidden sidecars.
- Serializer round-trip and migration regressions stay authoritative and pass.
- The packet-owned verification command passes.

## Handoff Notes
- `P13` may document the final boundary, but it must not discover known-stale persistence assertions left behind by this packet.
