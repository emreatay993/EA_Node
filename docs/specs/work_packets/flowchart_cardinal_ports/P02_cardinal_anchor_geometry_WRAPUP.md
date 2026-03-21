# P02 Cardinal Anchor Geometry Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/flowchart-cardinal-ports/p02-cardinal-anchor-geometry`
- Commit Owner: `worker`
- Commit SHA: `45801ba2293db2db3a88470d8449ce99688ed3b9`
- Changed Files: `ea_node_editor/ui_qml/graph_surface_metrics.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`, `ea_node_editor/ui_qml/edge_routing.py`, `tests/test_flowchart_surfaces.py`, `tests/test_flowchart_visual_polish.py`, `tests/graph_track_b/scene_and_model.py`, `docs/specs/work_packets/flowchart_cardinal_ports/P02_cardinal_anchor_geometry_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/flowchart_cardinal_ports/P02_cardinal_anchor_geometry_WRAPUP.md`

Replaced the legacy flowchart row-band anchor path with explicit cardinal helpers in both Python and QML/JS. `flowchart_port_side()`, `flowchart_anchor_local_point()`, `flowchart_anchor_normal()`, and `flowchart_anchor_tangent()` in [graph_surface_metrics.py](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_worktrees/flowchart_cardinal_ports_p02_cardinal_anchor_geometry/ea_node_editor/ui_qml/graph_surface_metrics.py) now resolve stored `top/right/bottom/left` flowchart ports to exact silhouette perimeter points, including true midside anchors for `database` and slanted midsides for `input_output`. The JS mirror in [GraphNodeSurfaceMetrics.js](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_worktrees/flowchart_cardinal_ports_p02_cardinal_anchor_geometry/ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js) adds the same side-aware geometry plus `portCardinalSide()`, `portLayoutDirection()`, and `visiblePortsForDirection()` so QML keeps a stable `in`/`out` layout bridge while rendering four neutral flowchart handles.

Flowchart host and preview rendering now discover neutral ports through side-based layout grouping instead of raw `port.direction` filtering. [GraphNodeHost.qml](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_worktrees/flowchart_cardinal_ports_p02_cardinal_anchor_geometry/ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml) and [GraphCanvasLogic.js](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_worktrees/flowchart_cardinal_ports_p02_cardinal_anchor_geometry/ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js) both treat `top/left` as temporary layout inputs and `right/bottom` as temporary layout outputs, which keeps the existing host/drop-preview contracts alive until `P03` rewrites neutral interaction payloads. Edge payload construction in [edge_routing.py](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor_worktrees/flowchart_cardinal_ports_p02_cardinal_anchor_geometry/ea_node_editor/ui_qml/edge_routing.py) now publishes `source_port_side` / `target_port_side` and derives control points plus pipe stubs from side normals/tangents instead of assuming horizontal `in`/`out` leads.

Side-vector rules for later packets are now fixed as: `top -> normal (0, -1), tangent (1, 0)`; `right -> normal (1, 0), tangent (0, 1)`; `bottom -> normal (0, 1), tangent (1, 0)`; `left -> normal (-1, 0), tangent (0, 1)`. Vertical-to-vertical pipe routes transpose the existing horizontal pipe solver, while mixed-side routes use an orthogonal stub from each anchor normal and a single midpoint bend axis. No extra side tie-break order was needed beyond the stable layout ordering `top,left` for temporary inputs and `right,bottom` for temporary outputs.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_surfaces.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_visual_polish.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "flowchart" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_surfaces.py --ignore=venv -q` (review gate)
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: stay on `codex/flowchart-cardinal-ports/p02-cardinal-anchor-geometry` and launch the app with the packet worktree venv so the QML helpers and routing payloads come from this branch.
- Action: add `Process`, `Decision`, `Database`, and `Input/Output` passive flowchart nodes to a scene.
- Expected result: each node renders four visible flow handles at `top`, `right`, `bottom`, and `left`, and raw port labels remain hidden on the host surface.
- Action: place two `Process` nodes vertically and connect the upper node’s `bottom` handle to the lower node’s `top` handle using the existing direct port drag/click flow.
- Expected result: the edge exits from the upper node’s bottom silhouette point, enters the lower node’s top silhouette point, and uses a vertical pipe stub rather than a left/right row-band offset.
- Action: place two `Process` nodes left-to-right and connect the left node’s `right` handle to the right node’s `left` handle.
- Expected result: the edge leaves and enters from the true horizontal midsides and keeps a bezier route with horizontally oriented control leads.
- Action: add a `Database` node and an `Input/Output` node, then zoom in and inspect the left/right handles.
- Expected result: `Database` handles sit on the cylinder’s true midsides, and `Input/Output` handles sit on the slanted side midsides instead of drifting vertically.

## Residual Risks

- `P03` still owns the real neutral gesture-order rewrite. Current QML interaction state continues to bridge neutral flowchart ports through temporary layout directions (`top/left -> in`, `right/bottom -> out`) so existing host drag/click contracts keep working.
- Shared scene payloads still do not publish a dedicated `side` field to QML. This packet infers the cardinal side from the stored flowchart port key, which is stable for the locked built-in catalog but should be replaced by explicit side payload data if later packets broaden the contract.

## Ready for Integration

- Yes: the packet-owned geometry and routing changes are committed, all required verification commands plus the review gate pass with `./venv/Scripts/python.exe`, and the wrap-up records the substantive packet SHA for reuse by later flowchart packets.
