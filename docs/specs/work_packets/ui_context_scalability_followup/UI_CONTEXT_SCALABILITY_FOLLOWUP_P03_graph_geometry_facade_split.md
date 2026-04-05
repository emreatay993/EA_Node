# UI_CONTEXT_SCALABILITY_FOLLOWUP P03: Graph Geometry Facade Split

## Objective

- Split graph surface metrics and edge routing into focused geometry modules behind stable facade files so ordinary graph-editing changes stop paying the full geometry-context cost.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_geometry/*.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_viewer_surface_contract.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_geometry/*.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_viewer_surface_contract.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P03_graph_geometry_facade_split_WRAPUP.md`

## Required Behavior

- Create a focused `ea_node_editor/ui_qml/graph_geometry/` package with these modules:
  - `surface_contract.py`
  - `standard_metrics.py`
  - `flowchart_metrics.py`
  - `panel_metrics.py`
  - `viewer_metrics.py`
  - `anchors.py`
  - `route_endpoints.py`
  - `route_pipe.py`
  - `route_styles.py`
  - `route_payload.py`
- Keep `graph_surface_metrics.py` as the stable facade entry surface for callers that already import it.
- Keep `edge_routing.py` as the stable facade entry surface for callers that already import it.
- End the packet with `graph_surface_metrics.py` at or below `350` lines and `edge_routing.py` at or below `400` lines.
- Preserve current edge-label, flowchart-anchor, viewer-surface, and Track-B contracts.
- Update inherited regression anchors in place when packet-owned helper locations or import surfaces move.

## Non-Goals

- No graph-scene mutation split yet.
- No edge-rendering QML split; that happened in the earlier packet set.
- No regression-suite packetization yet beyond updating inherited anchors this packet invalidates.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_flowchart_visual_polish.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py tests/test_graph_track_b.py tests/graph_track_b/qml_preference_bindings.py tests/test_viewer_surface_contract.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_graph_track_b.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P03_graph_geometry_facade_split_WRAPUP.md`
- `ea_node_editor/ui_qml/graph_geometry/route_payload.py`
- `ea_node_editor/ui_qml/graph_geometry/anchors.py`

## Acceptance Criteria

- The geometry helpers live in focused modules behind stable facade files.
- `graph_surface_metrics.py` is at or below `350` lines.
- `edge_routing.py` is at or below `400` lines.
- The packet-owned geometry regression anchors pass.

## Handoff Notes

- `P04` may consume the slimmer geometry facades when it splits graph-scene mutation history.
