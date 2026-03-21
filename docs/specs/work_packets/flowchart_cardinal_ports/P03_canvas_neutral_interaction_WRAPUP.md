# P03 Canvas Neutral Interaction Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/flowchart-cardinal-ports/p03-canvas-neutral-interaction`
- Commit Owner: `worker`
- Commit SHA: `7862ffc283e9c29ba32f105ad52329fba07f7f8e`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `tests/test_flow_edge_labels.py`, `tests/graph_track_b/scene_and_model.py`, `tests/test_graph_surface_input_contract.py`, `docs/specs/work_packets/flowchart_cardinal_ports/P03_canvas_neutral_interaction_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/flowchart_cardinal_ports/P03_canvas_neutral_interaction_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `tests/test_flow_edge_labels.py`, `tests/graph_track_b/scene_and_model.py`, `tests/test_graph_surface_input_contract.py`
- Neutral flowchart authoring now normalizes click, hover, and drag interactions back to the stored `neutral` port direction, carries `origin_side` on pending and wire-drag source payloads, and preserves gesture order whenever both endpoints are neutral flow ports.
- Shared canvas compatibility now routes through `GraphCanvasLogic.authoredConnection(...)`, which only bypasses fixed opposite-direction gating when both endpoints satisfy the flowchart-neutral guard (`direction="neutral"` plus a cardinal side); non-flowchart `in` / `out` behavior stays on the prior path.
- Live preview geometry now uses `origin_side` and `target_side` normals, while `EdgeLayer._portScenePoint(...)` resolves neutral flowchart anchors through `portScenePointForPort(...)` so rendered edges and preview stubs stay aligned with the selected cardinal sides.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "flowchart or connect_ports or connect_nodes" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -k "pendingConnectionPort or hoveredPort or portDrag or request_connect_ports" -q`
- PASS (Review Gate): `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch, start with an empty workspace, and use passive flowchart nodes that expose the four cardinal ports.
- Click the `right` port on one flowchart node, then click the `top` or `left` port on another flowchart node. Expected: the created edge runs from the first clicked port to the second clicked port, and the preview leaves the source from the selected side instead of forcing a fixed horizontal `out` stub.
- Repeat the same connection in reverse click order. Expected: the stored edge direction and rendered arrowhead reverse with the gesture order.
- Drag from a `top` or `left` flowchart port onto another flowchart port. Expected: the dashed preview follows the dragged source side, the hovered target port highlights as a valid drop, and dropping creates the edge without requiring opposite `in` / `out` directions.
- Drag a standard non-flowchart connection such as `exec_out -> exec_in`. Expected: fixed-direction authoring behaves exactly as before.

## Residual Risks

- `P04` still owns quick insert, dropped-node auto-connect, and edge insertion flows; this packet only rewrites direct canvas click-connect and wire-drag authoring.

## Ready for Integration

- Yes: the packet's verification commands and review gate passed in the assigned worktree, and the packet diff remains inside the allowed write scope.
