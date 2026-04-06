# SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR P02: QAction Refresh And Workspace Switch Sync

## Objective

- Make the three QActions consume the shared selected-workspace projection and refresh QAction state immediately when workspace selection changes.

## Preconditions

- `P01` is marked `PASS` in [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md](./SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md).
- No later `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR` packet is in progress.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_run_controller_unit.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_run_controller_unit.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P02_qaction_refresh_and_workspace_switch_sync_WRAPUP.md`

## Required Behavior

- Consume the packet-owned selected-workspace run-control projection from `run_flow.py`; do not duplicate the availability logic in controller, QAction, or QML code.
- Make `RunController.update_run_actions()` drive `action_run`, `action_pause`, and `action_stop` from that shared projection.
- Add `action_run` and `run_controls_changed` to `_RunControllerHostProtocol`.
- Stop leaving `action_stop` always enabled.
- Preserve the existing pause or resume QAction icon and label behavior, but source it from the shared projection.
- Emit `run_controls_changed` after QAction state recomputes so later presenter and bridge packets have a packet-owned notification seam to consume.
- Refresh run controls from `WorkspaceViewNavOps.switch_workspace()` so tab switches update QAction state immediately without waiting for another execution event.
- Update regression anchors so the packet proves:
  - idle state keeps `Run` enabled and `Pause` or `Stop` disabled
  - selected workspace owning the active run disables `Run` and enables `Pause` or `Stop`
  - paused selected-workspace ownership keeps `Pause` enabled with the `Resume` label
  - a non-owning selected workspace sees `Run` enabled and `Pause` or `Stop` disabled
  - workspace switches refresh QAction state immediately
  - the shortcut smoke no longer assumes `Stop` is always enabled

## Non-Goals

- No presenter or bridge properties in this packet.
- No QML `enabled:` bindings, button `objectName`s, or disabled styling in this packet.
- No backend execution, worker, or run-guard logic changes.
- No new pure-state projection semantics in this packet beyond consuming the `P01` seam.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py tests/test_workspace_library_controller_unit.py::WorkspaceViewNavOpsMutationServiceTests tests/main_window_shell/shell_basics_and_search.py::MainWindowShellBasicsAndSearchTests::test_command_actions_and_workspace_shortcuts_are_wired --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py tests/test_workspace_library_controller_unit.py::WorkspaceViewNavOpsMutationServiceTests --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P02_qaction_refresh_and_workspace_switch_sync_WRAPUP.md`

## Acceptance Criteria

- The `P01` selected-workspace projection in `run_flow.py` remains the single packet-owned source for QAction availability and pause-label state.
- `RunController` updates `action_run`, `action_pause`, and `action_stop` from that projection and emits `run_controls_changed` after recompute.
- Workspace selection changes refresh QAction state immediately through the shared workspace-navigation path.
- The packet-owned controller, workspace-navigation, and shortcut-smoke regression anchors pass.

## Handoff Notes

- `P03` may consume the `run_controls_changed` seam and selected-workspace projection, but it must not duplicate the projection logic.
