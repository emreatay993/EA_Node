# ARCH_THIRD_PASS P07: Validation And Persistence Centralization

## Objective
- Centralize graph validation and normalization rules now split across `model.py`, `graph/normalization.py`, `migration.py`, and `compiler.py`, while preserving current persisted document shape and current unknown-plugin behavior unless a packet-owned, lossless internal abstraction can keep behavior stable.

## Preconditions
- `P00` through `P06` are marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/nodes/registry.py`
- packet-owned validation helpers
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_registry_validation.py`
- `tests/test_graph_track_b.py`
- `tests/test_passive_runtime_wiring.py`

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/nodes/registry.py`
- packet-owned validation helpers
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_registry_validation.py`
- `tests/test_graph_track_b.py`
- `tests/test_passive_runtime_wiring.py`

## Required Behavior
- Introduce a clearer authoritative validation/normalization seam so graph model, compiler, and persistence layers stop carrying divergent packet-owned rule fragments.
- Preserve current persisted document shape and current unknown-plugin behavior unless a lossless internal abstraction can keep behavior stable without changing authored documents.
- Keep migration, codec, serializer, registry, and compiler interactions aligned around the centralized rule set instead of duplicating edge/node validation logic.
- Preserve passive-runtime exclusions, registry multiplicity rules, and current migration/serializer behavior from the user perspective.
- Prefer new focused helpers or services over adding more cross-layer validation logic into existing monolithic modules.

## Non-Goals
- No schema version bumps or intended `.sfe` document-shape changes.
- No new unknown-plugin UX behavior.
- No new runtime-worker feature work beyond consuming the centralized validation contract.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py tests/test_graph_track_b.py tests/test_passive_runtime_wiring.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_serializer_schema_migration.py tests/test_registry_validation.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P07_validation_persistence_centralization_WRAPUP.md`

## Acceptance Criteria
- Packet-owned validation and normalization rules have a clear authoritative seam instead of being redefined across model/compiler/persistence layers.
- Persisted document shape and unknown-plugin behavior remain stable.
- Serializer, migration, registry-validation, graph-track, and passive-runtime regressions pass.

## Handoff Notes
- `P08` is closure-only. Keep this packet focused on internal rule centralization and do not sweep in documentation-only cleanup except what is required to keep tests green.
- If a rule cannot be centralized without behavioral risk, preserve current behavior and record the residual risk explicitly.
