# FLOWCHART_CARDINAL_PORTS P03: Canvas Neutral Interaction

## Objective
- Make GraphCanvas click/drag authoring between neutral flowchart ports honor gesture order and use side-based live preview without regressing non-flowchart wiring behavior.

## Preconditions
- `P00` is marked `PASS` in [FLOWCHART_CARDINAL_PORTS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md).
- No later `FLOWCHART_CARDINAL_PORTS` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- targeted canvas/edge/flowchart interaction tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `tests/test_flow_edge_labels.py`
- `tests/graph_track_b/scene_and_model.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/flowchart_cardinal_ports/P03_canvas_neutral_interaction_WRAPUP.md`

## Required Behavior
- When both endpoints are neutral flowchart ports, preserve caller order during direct connection authoring (`request_connect_ports`, click-connect, and drag-connect):
  - first clicked/dragged port becomes the edge source
  - second selected/hovered port becomes the edge target
- Carry `origin_side` through the pending-port / drag interaction payload whenever a neutral flowchart port starts the gesture, and consume the flowchart port `side` field for hover-preview and drop-candidate logic.
- Update pending-port connect, hover preview, and wire-drag drop-candidate logic so neutral flowchart ports no longer depend on opposite fixed directions.
- Keep invalid self-connections and same-port no-op cases rejected.
- Update live wire preview geometry and arrow orientation so preview shaping uses the origin side vector instead of assuming an `out`/`in` horizontal sign.
- Preserve existing fixed-direction behavior for non-flowchart nodes and other port kinds.
- Add or update focused regressions that prove reversing the same two neutral flowchart ports reverses the stored arrow direction.

## Non-Goals
- No library-inspector compatibility rewrite yet. `P04` owns that.
- No dropped-node auto-connect or edge-insert rewrite yet. `P04` owns those flows.
- No requirement/fixture/docs refresh yet. `P05` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "flowchart or connect_ports or connect_nodes" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -k "pendingConnectionPort or hoveredPort or portDrag or request_connect_ports" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/flowchart_cardinal_ports/P03_canvas_neutral_interaction_WRAPUP.md`

## Acceptance Criteria
- Direct connect and wire-drag connect between neutral flowchart ports store source/target by gesture order.
- Neutral flowchart drag payloads expose `origin_side`, and preview/drop-candidate logic branches on side data instead of fixed port direction.
- Live preview and final edge rendering follow the origin side and resulting edge direction correctly.
- Non-flowchart canvas authoring remains unchanged.

## Handoff Notes
- Record any new interaction payload fields or helper names, especially `origin_side`, in the wrap-up so `P04` reuses the same neutral-port gesture context.
- If the packet needed a compatibility branch inside shared GraphCanvas helpers, document the exact condition that limits it to flowchart neutral ports.
