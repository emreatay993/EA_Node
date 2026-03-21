# FLOWCHART_CARDINAL_PORTS P02: Cardinal Anchor Geometry

## Objective
- Replace the flowchart row-band anchor model with exact top/right/bottom/left silhouette anchors and render four consistent visible flowchart handles across the host, edge payloads, and drop preview.

## Preconditions
- `P00` is marked `PASS` in [FLOWCHART_CARDINAL_PORTS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md).
- No later `FLOWCHART_CARDINAL_PORTS` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasDropPreview.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `ea_node_editor/ui_qml/edge_routing.py`
- targeted flowchart geometry, host, and routing tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasDropPreview.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `ea_node_editor/ui_qml/edge_routing.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/graph_track_b/scene_and_model.py`
- `docs/specs/work_packets/flowchart_cardinal_ports/P02_cardinal_anchor_geometry_WRAPUP.md`

## Required Behavior
- Add explicit side-aware flowchart anchor helpers in both Python and JS for `top`, `right`, `bottom`, and `left`.
- Use exact silhouette perimeter points for those sides rather than the existing row-band `local_y -> left/right x` model.
- Ensure `database` and `input_output` left/right anchors sit on the true visual midsides, and top/bottom anchors use the actual 0-degree / 180-degree silhouette points.
- Keep existing decision, connector, and terminator silhouette awareness while converting them to the same cardinal-side contract.
- Render four visible flowchart handles in the host and drop preview without re-enabling raw port labels.
- Update edge payload anchor generation so passive flowchart edges route from the new cardinal anchor positions.
- Update flow-edge routing tangent/normal derivation to use the selected cardinal side instead of a generic left/right `source_direction` assumption.
- Add geometry coverage that locks exact anchor behavior for `database` and `input_output`, plus top/right/bottom/left anchor checks for at least one rectangular, one slanted, one curved, and one diamond flowchart shape.
- Preserve public object discoverability and current host/drop-preview contract names relied on by tests.

## Non-Goals
- No gesture-order connection rewrite yet. `P03` owns that.
- No quick-insert or dropped-node auto-connect rewrite yet. `P04` owns that.
- No requirements/fixture/docs refresh yet. `P05` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_surfaces.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_visual_polish.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "flowchart" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_surfaces.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/flowchart_cardinal_ports/P02_cardinal_anchor_geometry_WRAPUP.md`

## Acceptance Criteria
- Flowchart anchors are computed by side (`top/right/bottom/left`) rather than by left/right row-band stacking.
- Database and input/output shapes no longer show vertically drifting side anchors.
- Host and drop-preview surfaces render four visible flowchart handles while preserving hidden label behavior.
- Flowchart edge payload anchors and routing tangents/normals follow the new cardinal geometry without breaking existing silhouette-aware routing expectations.
- The packet proves exact cardinal-anchor coverage for `database`, `input_output`, and representative rectangular/slanted/curved/diamond flowchart variants.

## Handoff Notes
- Record the exact helper names, side-vector/tangent-normal derivation rules, and any variant-specific geometry exceptions in the wrap-up so `P03` and `P04` reuse the same side/perimeter contract.
- If a side tie-break order had to be introduced for degenerate geometry, document it explicitly.
