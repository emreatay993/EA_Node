# P05 Collapse + Boundary Edge Routing Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/comment-backdrop/p05-collapse-boundary-edge-routing`
- Commit Owner: `worker`
- Commit SHA: `a92032370b5a8ce3df8c715b38c6775eefabf089`
- Changed Files: `docs/specs/work_packets/comment_backdrop/P05_collapse_boundary_edge_routing_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_comment_backdrop_collapse.py`
- Artifacts Produced: `docs/specs/work_packets/comment_backdrop/P05_collapse_boundary_edge_routing_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_comment_backdrop_collapse.py`

Collapsed boundary edges now carry routed-endpoint metadata without mutating the authored edge identity: `source_node_id` and `target_node_id` remain the stored graph endpoints, while `*_anchor_kind`, `*_anchor_node_id`, `*_hidden_by_backdrop_id`, `*_anchor_side`, and `*_anchor_bounds` describe the visible endpoint actually rendered when collapse proxies an endpoint to a visible collapsed backdrop.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_collapse.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing

- Prerequisite: open a graph with one comment backdrop that contains nodes and a nested comment backdrop, plus at least one node outside the outer backdrop.
- Action: collapse the outer backdrop. Expected result: descendant nodes and nested backdrops disappear, fully internal edges disappear, and crossing edges reroute to the collapsed backdrop perimeter.
- Action: collapse a nested backdrop first, then collapse its ancestor. Expected result: crossing edges proxy to the inner collapsed backdrop while it is visible, then re-proxy to the outer collapsed backdrop once the ancestor collapses; edges whose hidden endpoints now resolve to the same visible collapsed backdrop disappear.
- Action: expand the collapsed backdrop chain. Expected result: descendants return at their authored positions and the original edge endpoints/routes restore without duplicate or rewritten edges.

## Residual Risks

- Packet verification covered the payload builder and canvas redraw path in the dedicated collapse test file, but broader shell workflows that inspect edge payloads indirectly were not rerun in this packet.

## Ready for Integration

- Yes: collapse filtering, boundary-edge proxy routing, nested collapsed-ancestor resolution, and the packet verification command all passed on the assigned branch.
