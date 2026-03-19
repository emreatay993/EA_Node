# ARCH_FOURTH_PASS P01: Unknown Plugin Preservation

## Objective
- Preserve unresolved plugin-authored graph content losslessly across load, in-memory normalization, and save without making unresolved nodes executable.

## Preconditions
- `P00` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- No later `ARCH_FOURTH_PASS` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- serializer/migration regression tests

## Conservative Write Scope
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/normalization.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`

## Required Behavior
- Stop silently dropping unresolved node types during document migration and in-memory normalization.
- Introduce a lossless unresolved-node representation or equivalent opaque preservation path that keeps authored node, edge, and metadata payloads available for round-trip save.
- Preserve the current behavior that unresolved nodes are not executable until the required plugin is available.
- Keep known-node normalization, migration, and deterministic serialization behavior intact for registry-resolved content.
- Add focused regression coverage for opening and saving a project with missing plugins without destroying authored data.

## Non-Goals
- No packet-owned runtime DTO or worker decomposition yet; `P04` owns that.
- No shell/UI affordances for unresolved nodes in this packet.
- No schema version bump unless unavoidable and explicitly documented.

## Verification Commands
1. `./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_serializer_schema_migration tests.test_registry_validation -v`

## Review Gate
- `./venv/Scripts/python.exe -m unittest tests.test_serializer -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P01_unknown_plugin_preservation_WRAPUP.md`

## Acceptance Criteria
- A project containing missing-plugin nodes can load and save without deleting those unresolved nodes or their edges from the authored document.
- Known-node migration and normalization still behave deterministically for registry-resolved content.
- Packet verification passes through the project venv.

## Handoff Notes
- `P02` promotes subnode semantics below the builtin layer; do not widen this packet into subnode contract moves.
- Keep the preservation contract explicit so later runtime packets can ignore unresolved nodes intentionally rather than by destructive pruning.
