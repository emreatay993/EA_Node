# ARCH_FIFTH_PASS P08: Current-Schema Persistence Boundary

## Objective
- Move persistence-only overlay state out of the live graph model and narrow load/save ownership to the current schema without preserving support for pre-current-schema `.sfe` documents.

## Preconditions
- `P07` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- current-schema persistence ownership and load/save boundaries
- unresolved-plugin/authored-override overlay state
- serializer and registry validation regressions

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_registry_validation.py`
- `tests/fixtures/persistence/*`
- `docs/specs/work_packets/arch_fifth_pass/P08_current_schema_persistence_boundary_WRAPUP.md`

## Required Behavior
- Introduce persistence-owned overlay types for unresolved plugin payloads and authored node overrides instead of storing them directly on `WorkspaceData`.
- Remove or narrow packet-owned pre-current-schema migration branches as needed so persistence logic is current-schema-owned and simpler to reason about.
- Keep current-schema `.sfe` round-trip behavior exact for users, including unresolved plugin preservation and authored override round-tripping.
- Do not introduce a schema version bump in this packet.
- Update packet-owned serializer/migration tests and fixtures so they validate the current-schema-only persistence contract explicitly.

## Non-Goals
- No runtime snapshot or worker-boundary change in this packet; `P09` owns that.
- No UI affordances for unresolved plugin content in this packet.
- No future-schema forward-compatibility plan in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P08_current_schema_persistence_boundary_WRAPUP.md`

## Acceptance Criteria
- Persistence-only unresolved payload state no longer lives on the live graph model.
- Current-schema `.sfe` documents still load/save exactly as before from the user point of view.
- Packet-owned pre-current-schema migration complexity is removed or explicitly narrowed.
- Packet verification passes in the project venv.

## Handoff Notes
- `P09` consumes the cleaner live-model boundary from this packet to build the runtime snapshot pipeline.
- If a pre-current-schema fixture or assertion is removed, record that explicitly in the wrap-up as an intentional scope change authorized by this packet set.
