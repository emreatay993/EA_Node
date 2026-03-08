# SUBNODE P01: Hierarchy Persistence

## Objective
- Add schema `3` persistence for subnode hierarchy state without changing runtime/UI behavior yet.

## Preconditions
- `P00` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/settings.py`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/hierarchy.py`
- `ea_node_editor/custom_workflows/*`
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `tests/test_serializer.py`
- `tests/test_serializer_v2_migration_rc2.py`

## Required Behavior
- Bump `SCHEMA_VERSION` from `2` to `3`.
- Extend `ViewState` with persistent `scope_path: list[str]`.
- Add normalized project metadata storage for `custom_workflows`.
- Add a pure graph hierarchy helper module for scope normalization/traversal queries; do not wire it into QML behavior yet.
- Keep project loading compatible with schema `2` documents by migrating them to schema `3`.
- Default missing `scope_path` values to `[]` and missing `custom_workflows` metadata to `[]`.
- Ensure serializer round-trip preserves `scope_path`, workspace order, and normalized custom workflow metadata.

## Non-Goals
- No subnode shell or pin node types.
- No graph-area breadcrumb UI or navigation commands.
- No group/ungroup behavior.
- No execution compiler or custom workflow library UI.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_serializer_v2_migration_rc2 -v`

## Acceptance Criteria
- Existing schema `2` projects load successfully as schema `3`.
- `ViewState.scope_path` round-trips through save/load.
- `metadata.custom_workflows` is normalized deterministically during migration and serialization.
- No graph canvas, shell, or execution behavior changes are introduced in this packet.

## Handoff Notes
- `P02` must introduce the subnode node types and one shared effective-port resolver while reusing the persistence structures from this packet.
- Keep hierarchy and custom-workflow helpers stable so later packets can call them rather than reimplementing the same normalization logic.
