# P03 Standard Node Width Policy Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/port-label-visibility/p03-standard-node-width-policy`
- Commit Owner: `worker`
- Commit SHA: `6d261ace148f8af6b9c511d9f51b3f3701738d41`
- Changed Files: `ea_node_editor/ui_qml/graph_surface_metrics.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`, `tests/graph_track_b/scene_and_model.py`, `docs/specs/work_packets/port_label_visibility/P03_standard_node_width_policy_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/port_label_visibility/P03_standard_node_width_policy_WRAPUP.md`
- Width Contract Helpers: `_standard_title_full_width`, `_standard_visible_label_widths`, `_standard_port_label_min_width`, `_standard_surface_min_width_contract`
- Width Contract Fields: `standard_title_full_width`, `standard_left_label_width`, `standard_right_label_width`, `standard_port_gutter`, `standard_center_gap`, `standard_port_label_min_width`
- Center Safety Gap: `24.0`

- The standard-node metric path now reads `graphics_show_port_labels` from the scene bridge parent preference source and threads that flag through payload building, effective rendered width resolution, edge routing bounds, and resize mutation clamping.
- Expanded standard-node `min_width` now resolves to `standard_title_full_width` when labels are off and to `max(standard_title_full_width, standard_port_label_min_width)` when labels are on, without changing passive families, flowchart rules, or collapsed widths.
- The scene payload now exposes the standard width-contract fields so later QML work can consume the same left/right label widths, port gutter, and center-gap contract instead of recomputing it independently.
- Packet-local coverage now verifies the labels-on versus labels-off `min_width` delta, rendered-width clamping on re-enable without rewriting the stored custom width, resize clamping against the same computed minimum, and JSON/JS contract sync for the added metric fields.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_passive_image_nodes.py -k generated_js_surface_metric_contract_matches_authoritative_json --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: open this branch in the desktop shell and use an expanded standard node with at least one long left-side label and one long right-side label, such as `core.logger` after renaming `message` and `exec_out`.
- Action: turn `View > Port Labels` off, then refresh or reopen the active workspace if it is already visible.
- Expected: the node can contract down to its title-driven minimum width; inline label presentation is still owned by `P04`, so labels may still render even though the width policy is now title-only.
- Action: turn `View > Port Labels` back on.
- Expected: the same node widens immediately to the computed port-label-aware minimum width without rewriting the stored custom width until you explicitly resize it again.
- Action: drag-resize the same expanded standard node narrower while labels are on.
- Expected: the resize operation clamps at the same minimum width used by the rendered node and the saved custom width does not go below that shared minimum.

## Residual Risks

- Non-packet-owned callers that still invoke `node_size()` without threading the active preference, including scope-selection bounds helpers outside this packet scope, still default to labels-on width assumptions when `graphics_show_port_labels` is off.
- Standard title and label widths use deterministic text-width estimation rather than live Qt font metrics so the metric contract remains safe in non-GUI code paths; future typography changes should revisit those estimators together with the packet-owned fields above.

## Ready for Integration

- Yes: the packet-owned metric, payload, edge-routing, and resize-clamp authorities now share the same preference-aware standard-node width contract and the required verification passed.
