# PORT_LABEL_VISIBILITY P04: QML Label Presentation Rollout

## Objective
- Consume the new preference and width-policy contract in the QML host path so expanded standard nodes keep inline-editable labels when enabled, switch to tooltip-only labels when disabled, and preserve a no-overlap label layout near the minimum width.

## Preconditions
- `P00` through `P03` are marked `PASS` in [PORT_LABEL_VISIBILITY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_STATUS.md).
- No later `PORT_LABEL_VISIBILITY` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/port_label_visibility/P04_qml_label_presentation_rollout_WRAPUP.md`

## Required Behavior
- Pass the new `graphics_show_port_labels` flag into the graph canvas host path through the packet-owned bridge references.
- Keep expanded standard-node port labels visible and inline-editable only when the preference is on.
- When the preference is off for expanded standard non-passive nodes, hide the inline label text and show the effective port label only as a hover tooltip on the port hit target.
- Reserve left and right label columns plus a center gutter for expanded standard nodes so visible labels do not visually squash into each other near the packet-owned minimum width.
- Do not show tooltip-only labels for surfaces that already hide labels for family-specific reasons.
- Keep passive families, flowchart neutral-handle rules, collapsed nodes, and stored `port_labels` data unchanged.
- Consume the width-policy contract from `P03`; do not add a second QML-side width authority.

## Non-Goals
- No preference-schema, menu, dialog, or bridge-surface changes in this packet.
- No further scene-metric or mutation-clamp redesign beyond consuming the `P03` contract.
- No passive-family label-visibility redesign.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/port_label_visibility/P04_qml_label_presentation_rollout_WRAPUP.md`

## Acceptance Criteria
- Long expanded-standard-node labels stay fully visible at minimum width when the preference is on.
- Opposite-side standard-node labels do not overlap near the packet-owned minimum width.
- When the preference is off, expanded standard nodes hide inline label text and show tooltip-only labels on hover, while passive and family-specific label rules remain unchanged.
- The packet passes the QML preference-binding and graph-host regression suites without reopening the preference or scene-metric ownership boundaries.

## Handoff Notes
- Record the final tooltip trigger surface and any host property names used to gate standard-node-only behavior so future QML work reuses the same distinction.
- The overall targeted verification matrix requested in the source plan is the union of `P01` through `P04` verification commands; note any residual mismatch plainly if the packet had to narrow the tooltip gesture or layout behavior to preserve stability.
