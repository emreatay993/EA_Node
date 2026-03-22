# PORT_LABEL_VISIBILITY P03: Standard Node Width Policy

## Objective
- Replace the static expanded-standard-node `120px` minimum-width floor with a preference-aware title/port layout contract that the scene payload, effective rendered width, and resize mutation clamping all share.

## Preconditions
- `P00` through `P02` are marked `PASS` in [PORT_LABEL_VISIBILITY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_STATUS.md).
- No later `PORT_LABEL_VISIBILITY` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `tests/graph_track_b/scene_and_model.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `tests/graph_track_b/scene_and_model.py`
- `docs/specs/work_packets/port_label_visibility/P03_standard_node_width_policy_WRAPUP.md`

## Required Behavior
- Extend the standard-node surface metric calculation to accept the current port-label-visibility flag from the shell-owned preference path.
- Compute expanded standard-node `min_width` from the shared title/port layout contract instead of the current static `120.0` floor.
- When `show_port_labels` is on for an expanded standard non-passive node, include:
  - full title width
  - widest visible left label width
  - widest visible right label width
  - both port/dot gutters
  - a fixed center safety gap so opposite-side labels cannot overlap
- When `show_port_labels` is off for an expanded standard non-passive node, clamp only to full title width plus the normal standard-node chrome margins.
- Clamp effective rendered width to `max(custom/default width, computed min_width)` so re-enabling labels expands narrow standard nodes immediately without rewriting stored custom widths in project data.
- Use that same computed minimum in resize mutation clamping so drag-resize and saved custom widths follow the same rule.
- Keep passive families, flowchart neutral-handle rules, collapsed widths, and stored `port_labels` data unchanged.
- If the QML host needs extra standard-node layout fields to honor this contract, expose those fields through the metric payload here rather than recomputing width policy in QML.

## Non-Goals
- No preference-schema, menu, or dialog changes in this packet.
- No tooltip-only or inline-label visibility changes in QML yet. `P04` owns that presentation behavior.
- No passive-family or collapsed-node width-policy rewrite.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/port_label_visibility/P03_standard_node_width_policy_WRAPUP.md`

## Acceptance Criteria
- Expanded standard-node `min_width` is measurably larger with labels on than with labels off.
- Effective rendered width clamps to the computed minimum when labels are re-enabled without rewriting stored custom widths.
- Resize mutation clamping uses the same computed minimum as the scene payload.
- Passive families, flowchart neutral-handle behavior, and collapsed-node width rules remain unchanged.

## Handoff Notes
- Record the exact metric fields and helper names that define the width contract so `P04` can consume them directly rather than reconstructing label-column math in QML.
- If the packet had to choose a fixed center safety gap value, note that constant explicitly in the wrap-up so future metric work keeps the same overlap contract.
