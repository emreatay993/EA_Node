# ARCHITECTURE_RESIDUAL_REFACTOR P01: Shell Host Surface Retirement

## Objective

- Finish reducing `ShellWindow` to lifecycle, Qt ownership, and focused event-wiring duties so packet-owned orchestration commands live on controllers, presenters, and bridge objects instead of a broad host facade.

## Preconditions

- `P00` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_project_session_controller_unit.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`
- `docs/specs/work_packets/architecture_residual_refactor/P01_shell_host_surface_retirement_WRAPUP.md`

## Required Behavior

- Remove remaining packet-owned pass-through shell commands and properties from `ShellWindow` when focused controller, presenter, or bridge ownership already exists.
- Keep composition as the authoritative place that wires host-facing protocols and focused bridge exports into controllers and presenters.
- Narrow packet-owned controller and presenter dependencies to focused host or adapter protocols instead of concrete `ShellWindow` access.
- Update inherited shell bootstrap and controller regression anchors in place when packet-owned host seams change.

## Non-Goals

- No shell teardown or fresh-process isolation work yet; that belongs to `P02`.
- No graph-scene bridge or viewer-session decomposition yet.
- No execution-side runtime or graph-domain decoupling yet.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_project_session_controller_unit.py tests/test_workspace_library_controller_unit.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py tests/test_main_window_shell.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_project_session_controller_unit.py tests/test_workspace_library_controller_unit.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P01_shell_host_surface_retirement_WRAPUP.md`

## Acceptance Criteria

- `ShellWindow` is no longer the packet-owned application-command hub.
- Packet-owned controllers and presenters depend on focused protocols or bridge seams instead of broad `ShellWindow` access.
- The inherited shell bootstrap and controller regression anchors pass.

## Handoff Notes

- `P02` hardens shell teardown and repeated in-process lifecycle behavior against the slimmer host surface from this packet.
