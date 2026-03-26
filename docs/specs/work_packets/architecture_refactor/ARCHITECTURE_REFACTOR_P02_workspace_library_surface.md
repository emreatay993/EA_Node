# ARCHITECTURE_REFACTOR P02: Workspace Library Surface

## Objective
- Narrow `WorkspaceLibraryController` so it stops acting as a broad capability multiplexer and instead exposes smaller editing, navigation, and library surfaces with direct dependencies.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/workspace_library_controller_unit/core_ops.py`
- `tests/workspace_library_controller_unit/custom_workflow_io.py`
- `tests/test_workspace_manager.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/workspace_library_controller_unit/`
- `tests/test_workspace_manager.py`
- `docs/specs/work_packets/architecture_refactor/P02_workspace_library_surface_WRAPUP.md`

## Required Behavior
- Replace capability-loop indirection with narrower controller or service dependencies for workspace navigation, graph editing, and custom-workflow IO.
- Keep current presenter and shell entry points working while reducing the amount of behavior that routes through one broad facade.
- Update existing controller-unit tests and helper stubs when packet-owned dependency contracts change instead of layering duplicate tests on top.
- Limit composition changes to dependency wiring needed for the narrower workspace-library surface.

## Non-Goals
- No project/session/autosave extraction yet.
- No shell bootstrap changes beyond packet-owned dependency wiring.
- No graph-domain or persistence changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/workspace_library_controller_unit/core_ops.py tests/workspace_library_controller_unit/custom_workflow_io.py tests/test_workspace_manager.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P02_workspace_library_surface_WRAPUP.md`

## Acceptance Criteria
- `WorkspaceLibraryController` stops being the default bounce point for unrelated capability wrappers.
- Narrowed workspace-library contracts are reflected in the inherited controller-unit regression anchors.
- The packet-owned verification command passes.

## Handoff Notes
- `P03` may depend on these narrower workspace/library seams when extracting project-session responsibilities.
