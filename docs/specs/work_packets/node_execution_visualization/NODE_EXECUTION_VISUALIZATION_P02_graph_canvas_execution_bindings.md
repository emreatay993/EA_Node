# NODE_EXECUTION_VISUALIZATION P02: Graph Canvas Execution Bindings

## Objective
- Thread the packet-owned execution lookup properties through `GraphCanvas.qml` so bridge-first QML callers can read running/completed execution state directly from the canvas item before node-host chrome work begins.

## Preconditions
- `P01` is marked `PASS` in [NODE_EXECUTION_VISUALIZATION_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_STATUS.md).
- No later `NODE_EXECUTION_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/node_execution_visualization/P02_graph_canvas_execution_bindings_WRAPUP.md`

## Required Behavior
- Add packet-owned readonly `GraphCanvas.qml` properties for the bridge execution state using the established bridge contract names and the same null-guard pattern already used for failure highlight properties.
- Keep the canvas surface bridge-first: source the new canvas properties from `graphCanvasStateBridgeRef` only and do not introduce new compatibility aliases or direct host fallbacks.
- Preserve existing `failedNodeLookup` / `failedNodeRevision` / `failedNodeTitle` behavior while adding the new execution properties alongside them.
- Add packet-owned regression tests in `tests/test_main_window_shell.py` whose names include `node_execution_canvas` so the targeted verification commands below remain valid.
- Lock the QML property names established here as the packet-owned canvas contract for later node-host consumers.

## Non-Goals
- No `GraphNodeHost.qml`, `GraphNodeChromeBackground.qml`, or `GraphNodeHostTheme.qml` changes yet.
- No timer label, halo, border, z-order, or render-activation logic yet.
- No Python bridge or controller changes beyond the packet-owned contract from `P01`.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k node_execution_canvas --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k node_execution_canvas_properties --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/node_execution_visualization/P02_graph_canvas_execution_bindings_WRAPUP.md`

## Acceptance Criteria
- `GraphCanvas.qml` exposes stable running/completed execution properties sourced from the packet-owned bridge contract and preserves existing failure-highlight bindings.
- The packet-owned `node_execution_canvas` regression tests prove the GraphCanvas item reflects the new execution properties through the bridge-first QML path.
- No node-host chrome or visual behavior changes land in this packet.

## Handoff Notes
- `P03` consumes the `GraphCanvas.qml` property names established here and should not rename them without inheriting `tests/test_main_window_shell.py`.
- This packet intentionally stops at canvas-level property exposure; node-host visuals, timer, and chrome priority remain owned by `P03`.
