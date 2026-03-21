# FLOWCHART_CARDINAL_PORTS P04: Flowchart Drop Connect Insert

## Objective
- Update quick insert, dropped-node auto-connect, and edge-insert flows so neutral flowchart ports behave deterministically and use nearest-facing cardinal side selection without changing non-flowchart library behavior.

## Preconditions
- `P00` is marked `PASS` in [FLOWCHART_CARDINAL_PORTS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md).
- No later `FLOWCHART_CARDINAL_PORTS` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`

## Target Subsystems
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- targeted library-inspector and drop/connect tests

## Conservative Write Scope
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `tests/test_window_library_inspector.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/main_window_shell/view_library_inspector.py`
- `docs/specs/work_packets/flowchart_cardinal_ports/P04_flowchart_drop_connect_insert_WRAPUP.md`

## Required Behavior
- Treat neutral flowchart ports as compatible flow endpoints in connection quick insert instead of filtering by opposite fixed directions.
- Keep non-flowchart library filtering and compatible-port shaping unchanged.
- When a quick insert begins from a neutral flowchart port, branch on the carried `origin_side`, keep the origin port as the source, and auto-select the inserted node’s nearest-facing exposed cardinal port as the target.
- When a node is dropped onto a neutral flowchart port, branch on the existing flowchart port side data and create the auto-connected edge from the existing origin port to the dropped node’s nearest-facing exposed cardinal port.
- When a flowchart node is inserted on an existing passive flow edge, rewire as `source -> new -> target`, select inbound/outbound cardinal ports on the inserted node by nearest-facing geometry relative to the original source and target, and prefer distinct sides when both edges attach to that node.
- Update focused tests for library-compatible port discovery, dropped-node auto-connect, and view/shell quick-insert behavior.

## Non-Goals
- No new flowchart geometry helper surface beyond what `P02` already introduced.
- No broad docs/fixture refresh yet. `P05` owns that.
- No requirement changes outside packet-local test expectations.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_window_library_inspector.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/view_library_inspector.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_window_library_inspector.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/flowchart_cardinal_ports/P04_flowchart_drop_connect_insert_WRAPUP.md`

## Acceptance Criteria
- Connection quick insert no longer depends on opposite fixed directions for neutral flowchart ports.
- Quick insert, dropped-node auto-connect, and edge insertion produce deterministic neutral flowchart wiring using nearest-facing cardinal sides and the preserved source-first flow direction.
- Non-flowchart quick insert and library compatibility remain unchanged.

## Handoff Notes
- Record the exact nearest-facing side selection rule, `origin_side` consumption path, and tie-break order in the wrap-up so `P05` can document the behavior accurately.
- If a packet-local helper was introduced for side selection, note whether it is safe for later reuse beyond the flowchart-neutral path.
