# P04 GraphNodeHost Split Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/arch-second-pass/p04-graph-node-host-split`
- Commit Owner: `worker`
- Commit SHA: `964d9b8872f641421a3d4c48e7d88b30b1aacbd9`
- Changed Files: `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHostHitTesting.js`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`, `tests/test_passive_graph_surface_host.py`, `tests/test_graph_surface_input_contract.py`
- Artifacts Produced: `docs/specs/work_packets/arch_second_pass/P04_graph_node_host_split_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHostHitTesting.js`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host tests.test_graph_surface_input_contract -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host.PassiveGraphSurfaceHostTests.test_graph_node_host_routes_body_click_open_and_context_from_below_surface_layer -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Open a graph containing standard, planning or annotation, and media nodes.
Expected result: node chrome, title/header treatment, and port positions match the pre-packet visuals while the graph remains draggable/selectable.
2. On a node with inline surface controls, click inside an inline control and then click, double-click, and right-click the adjacent node body.
Expected result: inline controls keep pointer ownership inside their embedded rects, while adjacent body interactions still select, open, and open the node context menu.
3. Put an image/media node into crop mode, then try node drag, port drag, and resize before and after leaving crop mode.
Expected result: crop mode locks host drag, resize, and port routing, and normal host interactions resume immediately after crop mode exits.

## Residual Risks

- Offscreen verification passed, but one live desktop smoke run is still useful for confirming z-order and hover feel during drag, resize, and media crop interactions under a real compositor.

## Ready for Integration

- Yes: the host split stays inside the P04 scope, preserves the existing surface-loader and input-routing contracts, and passes the packet verification plus review gate.
