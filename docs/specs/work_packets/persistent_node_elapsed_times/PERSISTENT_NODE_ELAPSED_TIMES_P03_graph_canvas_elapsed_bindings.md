# PERSISTENT_NODE_ELAPSED_TIMES P03: Graph Canvas Elapsed Bindings

## Objective
- Expose active-workspace timing lookups through the bridge-first GraphCanvas contract so later renderer work can consume stable started-at and cached-elapsed properties without reaching back into shell internals.

## Preconditions
- `P02` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P03_graph_canvas_elapsed_bindings_WRAPUP.md`

## Required Behavior
- Add `running_node_started_at_ms_lookup` and `node_elapsed_ms_lookup` properties to `GraphCanvasStateBridge`, filtered to the active workspace in the same way as the existing packet-owned execution lookups.
- Thread `running_node_started_at_ms_lookup` and `node_elapsed_ms_lookup` through `GraphCanvasRootBindings.qml` and `GraphCanvas.qml` as stable renderer-facing property names.
- Reuse the existing `node_execution_state_changed` plus `node_execution_revision` path for timing lookup changes instead of adding a second packet-owned timing signal or revision channel.
- Keep active-workspace filtering authoritative in the bridge so switching scenes/workspaces hides foreign timing data rather than mutating or clearing it.
- Add packet-owned regression tests whose names include `persistent_node_elapsed_canvas` so the targeted verification commands below remain stable.

## Non-Goals
- No QML footer rendering or styling changes yet.
- No history action-type split or edit invalidation behavior yet.
- No requirement, QA-matrix, or traceability refresh yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/test_main_window_shell.py -k persistent_node_elapsed_canvas --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py -k persistent_node_elapsed_canvas --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py -k persistent_node_elapsed_canvas --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P03_graph_canvas_elapsed_bindings_WRAPUP.md`

## Acceptance Criteria
- `GraphCanvasStateBridge`, `GraphCanvasRootBindings.qml`, and `GraphCanvas.qml` expose the fixed timing lookup names `running_node_started_at_ms_lookup` and `node_elapsed_ms_lookup`.
- Active-workspace filtering and the shared `node_execution_revision` path still govern the new timing lookups.
- The packet-owned `persistent_node_elapsed_canvas` bridge/canvas regressions pass.

## Handoff Notes
- `P06` must treat `running_node_started_at_ms_lookup` and `node_elapsed_ms_lookup` as fixed renderer-facing contracts.
- Any later packet that renames or reshapes those properties must inherit and update `tests/main_window_shell/bridge_support.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, and `tests/test_main_window_shell.py`.
