# ARCH_SECOND_PASS P07: Persistence Workspace Ownership

## Objective
- Remove persistence-to-UI dependency leaks and give workspace-order ownership a single authoritative seam without changing persisted document shape from the user’s perspective.

## Preconditions
- `P00` through `P06` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/workspace/manager.py`
- any new neutral normalizer/ownership module outside `ea_node_editor/ui/**`
- serializer/workspace regression tests

## Conservative Write Scope
- `ea_node_editor/persistence/migration.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/workspace/manager.py`
- `ea_node_editor/persistence/**`
- `ea_node_editor/workspace/**`
- `ea_node_editor/*normaliz*.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_workspace_manager.py`
- `tests/test_shell_project_session_controller.py`

## Required Behavior
- Remove packet-owned import edges from persistence code into `ea_node_editor.ui/**` by moving shared normalizers/helpers into a neutral package or by restructuring the owner seam.
- Make workspace ordering and related ownership explicitly authoritative in one layer, with other layers consuming that owner instead of re-deriving or partially owning the same rules.
- Keep `.sfe`, session, and migration behavior stable from the user’s perspective unless a narrowly justified migration-safe normalization adjustment is required.
- Preserve passive-style preset and workspace/session restore behavior.

## Non-Goals
- No shell/QML bridge refactor.
- No graph-scene mutation/subnode refactor beyond narrow fallout from neutralizing imports or ownership seams.
- No docs/traceability refresh yet; `P08` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_serializer_schema_migration tests.test_workspace_manager tests.test_shell_project_session_controller -v`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P07_persistence_workspace_ownership_WRAPUP.md`

## Acceptance Criteria
- Packet-owned persistence modules no longer import from `ea_node_editor.ui/**`.
- Workspace-order ownership is more centralized and explicit than the current baseline.
- Serializer/workspace regression coverage passes without user-visible persistence regressions.

## Handoff Notes
- `P08` refreshes traceability and QA evidence after this ownership cleanup lands.
- Call out any remaining shared-normalizer seams that still need broader package consolidation later.
