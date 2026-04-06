# SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR P01: Run Flow Selected Workspace Projection

## Objective

- Expand `run_flow.py` into the shared selected-workspace run-control projection and add direct unit coverage for the pure-state seam before any controller, bridge, or QML layer consumes it.

## Preconditions

- `P00` is marked `PASS` in [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md](./SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md).
- No later `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/ui/shell/run_flow.py`
- `tests/test_run_flow.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/run_flow.py`
- `tests/test_run_flow.py`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P01_run_flow_selected_workspace_projection_WRAPUP.md`

## Required Behavior

- Replace the current narrow `run_action_state(...)` helper with a packet-owned selected-workspace projection that computes:
  - `selected_workspace_owns_active_run`
  - `can_run_active_workspace`
  - `can_pause_active_workspace`
  - `can_stop_active_workspace`
  - `pause_label`
- Keep the projection controller-agnostic so later packets can consume it from QAction, presenter, and bridge surfaces without reinterpreting the rules.
- Preserve the current `event_targets_active_run(...)` event-scoping behavior unless a pure typing or shape cleanup is required to support the shared projection cleanly.
- Add direct unit coverage for at least:
  - idle state with no active run
  - active run owned by the selected workspace
  - paused active run owned by the selected workspace
  - active run owned by a different selected workspace
  - no `Resume` label leak when the selected workspace does not own the paused run

## Non-Goals

- No `RunController`, QAction, or workspace-switch wiring in this packet.
- No presenter, bridge, or QML changes in this packet.
- No changes to backend execution-client behavior or run-event routing.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_run_flow.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_run_flow.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P01_run_flow_selected_workspace_projection_WRAPUP.md`

## Acceptance Criteria

- `run_flow.py` becomes the single packet-owned source for selected-workspace run-control availability and pause-label state.
- The new direct run-flow unit suite proves owner, non-owner, idle, and paused-owner behavior.
- Later packets can consume the projection without needing to redefine the rules.

## Handoff Notes

- `P02` consumes this projection for QAction state and workspace-switch refresh; it must not redefine the availability rules.
