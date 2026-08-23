# Edge Routing, Labels, And Progress

## Purpose
Use this for edge routing, retained edge layers, Item/List/Tree structure styling, enabled/empty/invalid states, labels, hit testing, gap/break variants, and edge performance.

## Start Here
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_geometry/route_payload.py`
- `ea_node_editor/ui_qml/graph_scene_payload/normalize.py`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeScenegraphLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeRetainedLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphEdgeFloatingToolbar.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`
- `ea_node_editor/ui_qml/graph_canvas_command/`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `tests/test_data_type_ui_projection.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`

## Focused Verification
- Data-access structure comes from the source port: Item renders one stroke, List two parallel strokes, and Tree three. Empty and disabled edges remain selectable/hittable but render gray/dashed; invalid type remains red and has precedence over disabled styling.
- `graph_geometry/route_payload.py::_data_type_warning_reason` owns the stable edge-level `data_type_warning` and reason derived from the active catalog and resolved endpoints. It accepts assignable, convertible, runtime-check, and the target input's ordered accepted-type union; incompatible, unresolved, or missing endpoints warn. `graph_scene_payload/normalize.py` publishes separate availability warning/reason fields and never converts availability into a type warning. Structurally valid `flow` edges do not warn, and edge type reasons stay out of port text.
- Ordinary execution failure never turns a data wire red. Execution/control-edge flash and the simplified control connector overlay are removed; selection, preview, labels, routing, and crossing styles remain independent effects.
- Edge Enable is checked in the edge context menu and selected-edge floating toolbar and toggles through Ctrl+E. Disabled edges retain canonical identity, order, selection, label, and hit testing.
- Edge `visual_style.path_mode` can force the scene payload route to `pipe` or `bezier`; missing/empty keeps the existing auto pipe-vs-bezier routing.
- Edge label and visual-style edits publish targeted updated-edge deltas; `EdgeSnapshotCache.js` clears dirty-edge geometry, snapshots, and spatial-index entries so forced path-mode routes remain hittable for inline label editing.
- Default flow-edge label backing stays transparent; `EdgeCanvasLayer.qml` adds a label-sized break range to the existing broken-edge paint path so the edge is visually discontinuous under the label. Explicit `label_background_color` styles still draw their chosen backing color.
- Edge pan/drag/flash performance gates live in `EdgeSnapshotCache.js`, `EdgeRetainedLayer.qml`, and `EdgeFlowLabelLayer.qml`: viewport spatial queries use a single cell-range cache, dirty hit tests call `ensureSpatialIndex`, retained entries gate unchanged `contentKey`s, and flow-label model sync skips unchanged `edgeData` references.
- `EdgeCanvasLayer.qml` exposes `canvasStateBridgeRef` from `EdgeLayer.sceneBridge`; inline edge typography and flow-label shared roles depend on that bridge projection.

```powershell
.\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_rendering_suite.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_output_mode_ui.py tests/test_flow_edge_labels.py tests/test_edge_snapshot_spatial_index.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_data_tree_ui.py tests/test_graph_surface_input_controls.py -k "port_and_edge_authoring or edge" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_data_type_ui_projection.py -k "type_warning or availability_annotation" --ignore=venv -q
```

## Breadcrumbs
- [Graph Canvas Rendering, Input, And Viewport](../subsystems/graph_canvas.md)
- [Node Execution Visualization](node_execution_visualization.md)

## Update Triggers
Update when edge path geometry, structure/enabled/empty/invalid styling, type-reason/availability-warning separation, labels, inline label editing, selected-edge toolbar controls, Ctrl+E routing, hit testing, or edge performance routes change.

## 2026-07-11 Performance Ownership

- Endpoint anchors come from invocation-scoped presentation facts. Stable style/label/geometry changes replace cached payloads without reindex; related lane siblings replace in place around one sorted structural insert/remove.
