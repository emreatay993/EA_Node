# SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR P04: QML Toolbar Workspace Run States

## Objective

- Bind the shell toolbar run buttons to the new bridge properties, add stable button object names, and make disabled controls look disabled while preserving the existing single-run warning behavior.

## Preconditions

- `P03` is marked `PASS` in [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md](./SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md).
- No later `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR` packet is in progress.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellButton.qml`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_shell_run_controller.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellButton.qml`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_shell_run_controller.py`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P04_qml_toolbar_workspace_run_states_WRAPUP.md`

## Required Behavior

- Bind the Run, Pause, and Stop buttons in `ShellRunToolbar.qml` to:
  - `shellWorkspaceBridge.active_workspace_can_run`
  - `shellWorkspaceBridge.active_workspace_can_pause`
  - `shellWorkspaceBridge.active_workspace_can_stop`
- Keep the toolbar on `shellWorkspaceBridge`; do not reintroduce direct `mainWindowRef` or `ShellWindow` run-control ownership.
- Add stable QML `objectName`s:
  - `shellRunToolbarRunButton`
  - `shellRunToolbarPauseButton`
  - `shellRunToolbarStopButton`
- Update `ShellButton.qml` so disabled controls visibly read as disabled by dimming icon or text color and muting hover or pressed treatment while disabled.
- Add or update runtime shell assertions so the packet proves:
  - start a run in workspace A, switch to workspace B, and the toolbar `enabled` states flip immediately
  - switch back to workspace A and the owning-workspace toolbar states restore immediately
  - triggering `Run` from workspace B while workspace A owns the active run still surfaces the existing single-run warning
- Update the workspace bridge QML boundary suite to assert the new property references and button object names without broadening to unrelated failing `GraphCanvasQmlBoundaryTests`.

## Non-Goals

- No new presenter or bridge properties in this packet.
- No dedicated QML pause-label or icon property in this packet.
- No changes to backend execution or single-run guard logic.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py::ShellWorkspaceBridgeQmlBoundaryTests --ignore=venv -q
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m unittest tests.test_shell_run_controller
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py::ShellWorkspaceBridgeQmlBoundaryTests --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P04_qml_toolbar_workspace_run_states_WRAPUP.md`

## Acceptance Criteria

- The toolbar buttons use the bridge properties for enablement and expose stable object names.
- Disabled shell buttons are visually muted instead of merely non-clickable.
- The packet-owned QML boundary and shell integration regressions pass while preserving the existing single-run warning path.

## Handoff Notes

- This is the final implementation packet in the set.
