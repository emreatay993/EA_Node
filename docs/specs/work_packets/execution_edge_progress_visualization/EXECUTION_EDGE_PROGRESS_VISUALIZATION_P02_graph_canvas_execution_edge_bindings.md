# EXECUTION_EDGE_PROGRESS_VISUALIZATION P02: Graph Canvas Execution Edge Bindings

## Objective
- Expose progressed execution edge lookups through the bridge-first GraphCanvas contract so later edge-layer packets can consume active-workspace-filtered authored edge ids without opening a parallel QML data path.

## Preconditions
- `P01` is marked `PASS` in [EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md](./EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md).
- No later `EXECUTION_EDGE_PROGRESS_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/bridge_support.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/bridge_support.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/execution_edge_progress_visualization/P02_graph_canvas_execution_edge_bindings_WRAPUP.md`

## Required Behavior
- Expose `progressed_execution_edge_lookup` on `GraphCanvasStateBridge`, filtered to the active workspace using the same shell-run-state authority already used for node execution lookups.
- Re-emit the existing `node_execution_state_changed` signal path so GraphCanvas consumers pick up edge-progress lookup changes without a second edge-specific signal.
- Forward the bridge property through `GraphCanvasRootBindings.qml` and `GraphCanvas.qml` as `progressedExecutionEdgeLookup`.
- Keep the existing `nodeExecutionRevision` contract authoritative for QML invalidation. Do not add a separate edge execution revision property.
- Preserve the existing `runningNodeLookup`, `completedNodeLookup`, `failedNodeLookup`, and canvas root property names unchanged.
- Add packet-owned regressions whose names include `execution_edge_progress_canvas` so the verification commands below remain stable.

## Non-Goals
- No edge-layer snapshot metadata or renderer changes yet.
- No worker/runtime event changes beyond what `P01` already established.
- No QA-matrix or requirement-doc updates yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/test_main_window_shell.py -k execution_edge_progress_canvas --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k execution_edge_progress_canvas --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/execution_edge_progress_visualization/P02_graph_canvas_execution_edge_bindings_WRAPUP.md`

## Acceptance Criteria
- `GraphCanvasStateBridge` exposes `progressed_execution_edge_lookup` filtered to the active workspace and reuses the existing node execution invalidation path.
- `GraphCanvasRootBindings.qml` and `GraphCanvas.qml` surface `progressedExecutionEdgeLookup` without adding a second revision property.
- The packet-owned `execution_edge_progress_canvas` regressions pass while the existing node execution canvas property names remain unchanged.

## Handoff Notes
- `P03` and later packets should treat `progressed_execution_edge_lookup` and `progressedExecutionEdgeLookup` as fixed packet-owned names.
- Any later packet that needs to rename or reshape this bridge/root contract must inherit and update the `tests/test_main_window_shell.py` regression anchor inside its own scope.
