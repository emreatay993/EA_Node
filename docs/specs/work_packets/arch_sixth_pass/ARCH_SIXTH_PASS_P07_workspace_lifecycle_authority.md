# ARCH_SIXTH_PASS P07: Workspace Lifecycle Authority

## Objective
- Make `WorkspaceManager` the single packet-owned public authority for workspace lifecycle flows so create, duplicate, close, switch, and ordering behavior stop being split across the manager and `GraphModel`.

## Preconditions
- `P00` through `P06` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- workspace lifecycle authority
- workspace ordering and fallback policy
- shell navigation callers

## Conservative Write Scope
- `ea_node_editor/workspace/manager.py`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/ui/shell/controllers/workspace_navigation_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `tests/test_workspace_manager.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/arch_sixth_pass/P07_workspace_lifecycle_authority_WRAPUP.md`

## Required Behavior
- Move packet-owned public workspace lifecycle entrypoints behind `WorkspaceManager`.
- Demote overlapping `GraphModel` lifecycle methods to internal helpers or remove packet-owned direct callers when safe.
- Keep current workspace ordering, close fallback, and active-workspace behavior exactly.
- Preserve current shell, session-restore, and tab-strip behavior while narrowing the ownership boundary.

## Non-Goals
- No runtime snapshot or persistence overlay changes in this packet.
- No QML bridge removal or plugin/package work in this packet.
- No docs closeout work in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_manager.py tests/test_workspace_library_controller_unit.py tests/test_main_window_shell.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_workspace_manager.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P07_workspace_lifecycle_authority_WRAPUP.md`

## Acceptance Criteria
- Packet-owned workspace lifecycle callers no longer treat `GraphModel` and `WorkspaceManager` as peer public authorities.
- Workspace ordering and fallback tests pass unchanged.
- Shell workspace navigation behavior remains stable.

## Handoff Notes
- `P08` owns runtime execution boundary cleanup after workspace authority is narrowed.
- Keep the packet focused on authority consolidation, not state/history or persistence redesign.
