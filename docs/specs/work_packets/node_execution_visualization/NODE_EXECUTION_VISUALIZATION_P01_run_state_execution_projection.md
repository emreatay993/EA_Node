# NODE_EXECUTION_VISUALIZATION P01: Run State Execution Projection

## Objective
- Add run-scoped running/completed node execution state to the shell/controller path and expose bridge-level execution lookup properties that later QML packets can consume without changing worker protocol or persistence semantics.

## Preconditions
- `P00` is marked `PASS` in [NODE_EXECUTION_VISUALIZATION_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_STATUS.md).
- No later `NODE_EXECUTION_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `tests/test_run_controller_unit.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `tests/test_run_controller_unit.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/node_execution_visualization/P01_run_state_execution_projection_WRAPUP.md`

## Required Behavior
- Extend `ShellRunState` with packet-owned running/completed node sets, workspace IDs, and a revision counter suitable for QML highlight invalidation.
- Add `node_execution_state_changed` plus packet-owned mutation helpers on `ShellWindow` for marking nodes running, marking nodes completed, and clearing execution visualization state.
- Update `RunController.handle_execution_event()` so `node_started` marks running state, `node_completed` moves nodes to completed state, `run_started` clears stale execution state, `run_completed` and `run_stopped` clear execution state, and fatal worker-reset failures clear execution state while non-fatal `run_failed` intentionally preserve the last execution context.
- Expose `running_node_lookup`, `completed_node_lookup`, and `node_execution_revision` on `GraphCanvasStateBridge`, and re-emit a packet-owned bridge signal when shell execution state changes or the scene workspace changes.
- Keep workspace filtering authoritative in the bridge so only the active workspace returns execution highlight lookups.
- Do not add Python-side timestamp bridging; the elapsed timer remains a later QML-local concern in this packet set.
- Add packet-owned regression tests whose names include `node_execution_bridge` so the targeted verification commands below remain valid.

## Non-Goals
- No `GraphCanvas.qml` or node-host QML changes yet.
- No running/completed colors, halo geometry, timer labels, or chrome border logic yet.
- No worker protocol, runtime snapshot, or persistence schema changes.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py tests/main_window_shell/bridge_contracts.py -k node_execution_bridge --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k node_execution_bridge --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/node_execution_visualization/P01_run_state_execution_projection_WRAPUP.md`

## Acceptance Criteria
- `ShellRunState`, `ShellWindow`, and `RunController` track and clear running/completed node execution state according to the locked defaults.
- `GraphCanvasStateBridge` exposes stable `running_node_lookup`, `completed_node_lookup`, and `node_execution_revision` contracts filtered to the active workspace.
- The packet-owned `node_execution_bridge` regression tests pass with no worker protocol or persistence changes.

## Handoff Notes
- `P02` consumes the bridge contract established here and should treat `running_node_lookup`, `completed_node_lookup`, and `node_execution_revision` as fixed packet-owned names.
- Any later packet that needs to rename or reshape these bridge properties must inherit and update the `tests/main_window_shell/bridge_contracts.py` regression anchor inside its own scope.
