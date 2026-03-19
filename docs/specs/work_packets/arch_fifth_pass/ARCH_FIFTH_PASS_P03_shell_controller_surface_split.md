# ARCH_FIFTH_PASS P03: Shell Controller Surface Split

## Objective
- Break the current `WorkspaceLibraryController` orchestration bucket into focused controllers while preserving its observable behavior and keeping existing call sites stable through a compatibility facade.

## Preconditions
- `P02` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- shell controller boundaries for workflow publishing, navigation, graph edit, and package/file IO
- `WorkspaceLibraryController` compatibility facade
- workspace-library regression tests

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workflow_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_navigation_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_graph_edit_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_package_io_controller.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/workspace_library_controller_unit/**`
- `tests/test_window_library_inspector.py`
- `tests/test_node_package_io_ops.py`
- `docs/specs/work_packets/arch_fifth_pass/P03_shell_controller_surface_split_WRAPUP.md`

## Required Behavior
- Split `WorkspaceLibraryController` responsibilities into four focused public controllers:
  - workflow/library publishing
  - workspace/view navigation
  - graph edit commands
  - package/file import-export
- Keep `WorkspaceLibraryController` as a compatibility facade in this packet so current `ShellWindow` and bridge callers do not need packet-external rewrites yet.
- Preserve the exact behavior of graph search, quick insert, workflow publishing, package IO, and failure focus flows.
- Keep packet-owned controller protocols explicit and narrow; do not reintroduce broad host reach-through where a smaller protocol suffices.

## Non-Goals
- No QML bridge migration in this packet.
- No `ShellWindow` public QML surface contraction beyond what is required to delegate to the new focused controllers.
- No mutation-boundary or persistence/runtime changes in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_window_library_inspector.py tests/test_node_package_io_ops.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P03_shell_controller_surface_split_WRAPUP.md`

## Acceptance Criteria
- The focused controllers exist and own the packet-scoped responsibilities listed above.
- `WorkspaceLibraryController` is reduced to a compatibility/delegation surface rather than a large orchestration bucket.
- Packet-owned workspace/library/package behaviors remain exactly unchanged from the existing UI/test perspective.
- Packet verification passes in the project venv under offscreen Qt.

## Handoff Notes
- `P04` introduces new bridge contracts. Keep current bridge callers functioning through the compatibility facade in this packet.
- Do not start deleting old controller entrypoints until the bridge/QML migration packets own the call-site updates.
