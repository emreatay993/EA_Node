# ARCHITECTURE_FOLLOWUP_REFACTOR P02: Shell Controller Surface Narrowing

## Objective

- Replace broad packet-owned shell controller and service host surfaces with focused controller or adapter contracts so packet-owned callers stop depending on umbrella facades.

## Preconditions

- `P01` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`
- `docs/specs/work_packets/architecture_followup_refactor/P02_shell_controller_surface_narrowing_WRAPUP.md`

## Required Behavior

- Remove packet-owned reliance on `WorkspaceLibraryController` as a broad umbrella surface where focused controller or adapter seams are sufficient.
- Narrow packet-owned project-session service dependencies so those services do not depend on a broad window-like host contract.
- Preserve current run, workspace, library, and project-session user-facing behavior while shifting packet-owned callers to smaller contracts.
- Update inherited controller and shell regression anchors in place instead of leaving stale broad-surface assertions behind.

## Non-Goals

- No graph-canvas bridge retirement yet; that belongs to `P03`.
- No graph, persistence, runtime, or viewer authority work.
- No new library, workspace, run, or project-session features.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_project_session_controller_unit.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_project_session_controller_unit.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P02_shell_controller_surface_narrowing_WRAPUP.md`

## Acceptance Criteria

- Packet-owned callers no longer depend on `WorkspaceLibraryController` as a convenience umbrella when a focused controller or adapter is available.
- Packet-owned project-session services no longer require a broad window-like host surface.
- The inherited controller and shell regression anchors pass.

## Handoff Notes

- `P03` can retire remaining QML bridge compatibility only after the packet-owned shell/controller seams are narrowed here.
