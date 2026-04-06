# SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR P03: Presenter Bridge Run Control Projection

## Objective

- Project the selected-workspace run-control state through the current presenter and bridge stack with a dedicated run-controls signal and bridge contract coverage, while keeping the bridge as a projection surface rather than a second interpreter of run semantics.

## Preconditions

- `P02` is marked `PASS` in [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md](./SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md).
- No later `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR` packet is in progress.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui/shell/presenters/contracts.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_contracts_workspace_and_console.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/presenters/contracts.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_contracts_workspace_and_console.py`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P03_presenter_bridge_run_control_projection_WRAPUP.md`

## Required Behavior

- Add `run_controls_changed` to `_ShellWorkspacePresenterHostProtocol`, `ShellWorkspacePresenter`, `_ShellWorkspaceSource`, and `ShellWorkspaceBridge`.
- Add `run_state` to `_ShellWorkspacePresenterHostProtocol` so the presenter can compute the selected-workspace projection without reaching into controller internals or QAction surfaces.
- Have `ShellWorkspacePresenter` consume the shared `run_flow.py` projection and expose:
  - `active_workspace_can_run`
  - `active_workspace_can_pause`
  - `active_workspace_can_stop`
- Have `ShellWorkspaceBridge` re-emit `run_controls_changed` and expose the same properties with `notify=run_controls_changed`.
- Update workspace-source stubs and bridge contract coverage so the packet proves the new signal and properties through both injected and wrapped presenter paths.
- Keep the bridge projection additive only; do not add QML `enabled:` bindings, object names, or disabled-style work in this packet.

## Non-Goals

- No QAction recompute logic in this packet; that stays in `P02`.
- No direct derivation from `QAction` state inside the bridge.
- No QML toolbar or `ShellButton.qml` changes in this packet.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_workspace_and_console.py::ShellWorkspaceBridgeTests --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_workspace_and_console.py::ShellWorkspaceBridgeTests --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P03_presenter_bridge_run_control_projection_WRAPUP.md`

## Acceptance Criteria

- The presenter and bridge expose packet-owned selected-workspace run-control properties and a dedicated `run_controls_changed` signal.
- The bridge remains a projection of presenter or host state instead of a second independent interpreter of run-control semantics.
- The packet-owned bridge support and contract suites pass.

## Handoff Notes

- `P04` binds QML to the new bridge properties and adds runtime toolbar assertions; it must not route around the bridge.
