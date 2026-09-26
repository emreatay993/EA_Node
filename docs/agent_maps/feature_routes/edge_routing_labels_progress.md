# Edge Routing, Labels, And Progress

## Purpose
Use this for edge routing, retained edge layers, active-data Item/List/Tree/Empty structure and display styling, enabled/invalid states, labels, hit testing, gap/break variants, and edge performance.

## Start Here
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_geometry/route_payload.py`
- `ea_node_editor/ui_qml/graph_scene_payload/normalize.py`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeScenegraphLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `ea_node_editor/ui_qml/components/graph/EdgePaintPolicy.js`
- `ea_node_editor/ui_qml/components/graph/EdgeArrowPaint.js`
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeRetainedLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphEdgeFloatingToolbar.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/EdgeArrowGlyph.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSharedTypography.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`
- `ea_node_editor/ui_qml/graph_canvas_command/`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/passive_style_normalization.py`
- `ea_node_editor/ui_qml/graph_geometry/route_styles.py`
- `ea_node_editor/graph/validated_mutation.py`
- `tests/qml_quick/tst_edge_paint_policy.qml`
- `tests/test_data_type_ui_projection.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`

## Focused Verification
- `GraphNodeSurfaceMetrics.js` uses projected port-row heights for standard, viewer, and media endpoints so edge rendering stays aligned with node grips at custom graph text sizes. The real-canvas regression is in `tests/graph_surface/passive_host_interaction_suite.py`.
- `active_data_wire` is true only for standard data edges incident to an `active` or `compile_only` node. Its source `data_access` renders Item solid, List round-dotted, Tree rounded-dashed, and Empty as double hairlines with hollow endpoints. Passive-only and `flow` edges keep the legacy payload and appearance.
- `graph_geometry/route_payload.py::_data_type_warning_reason` owns the stable edge-level `data_type_warning` and reason derived from graph-owned all-member forwarding compatibility and resolved endpoints. It accepts assignable, convertible, runtime-check, and the target input's ordered accepted-type union; incompatible, unresolved, or missing endpoints warn. Quick Insert recommendation tiers never alter this static legality. `graph_scene_payload/normalize.py` publishes separate availability warning/reason fields and never converts availability into a type warning. Structurally valid flow edges do not warn, and edge type reasons stay out of port text.
- Edge warning projection reuses invocation-scoped `GraphTypeResolver` facts with port descriptions. Upstream edits publish all downstream pruning and warning changes through the scene delta owner; existing Type Error rendering is unchanged. `tests/test_type_forwarding_ui.py` owns chain refresh and warning coverage.
- Ordinary execution failure never turns a data wire red. Execution/control-edge flash and the simplified control connector overlay are removed; selection, preview, labels, routing, and crossing styles remain independent effects.
- Edge Enable is checked in the edge context menu and selected-edge floating toolbar and toggles through Ctrl+E. Disabled edges retain canonical identity, order, selection, label, and hit testing. An inner subnode input/output-pin segment propagates its requested state to matching upper shell segments, and scene deltas publish every changed segment in the single undoable action.
- `visual_style.display_mode` is normalized to Default, Faint, or Hidden by graph-owned batch mutation. Faint preserves hit geometry/tooltips; Hidden leaves endpoint arcs and logical-route marquee intersection but no body click hit, then reveals the full blue route when selected. Disabled active-data wires keep their structure with a centred X; direct selection preserves it, selected-node incidence adds a blue fade, and invalid type keeps the input-centred red gradient.
- `GraphCanvasInputLayers.qml` owns held-W wire marquee and Ctrl+Left/Ctrl+Right endpoint navigation. `GraphCanvasContextMenus.qml`, `GraphCanvasOptionsMenu.qml`, and `GraphCanvasActionRouter.qml` keep single- and selected-wire display menus plus endpoint jump actions aligned with this route.
- Edge `visual_style.path_mode` can force the scene payload route to `pipe` or `bezier`; missing/empty keeps the existing auto pipe-vs-bezier routing.
- Edge label and visual-style edits publish targeted updated-edge deltas; `EdgeSnapshotCache.js` clears dirty-edge geometry, snapshots, and spatial-index entries so forced path-mode routes remain hittable for inline label editing.
- `EdgePaintPolicy.js` is the pure renderer-neutral owner for flow/standard stroke, dash, structure, display-mode, marker, drag-preview, and gradient-stop facts. Canvas and retained renderers call it directly; `EdgeMath.js` owns shared edge anchors. Retained rendering must not reference Canvas implementation methods.
- Default flow-edge label backing stays transparent; `EdgeCanvasLayer.qml` adds a label-sized break range to the existing broken-edge paint path so the edge is visually discontinuous under the label. Explicit `label_background_color` styles still draw their chosen backing color.
- Edge pan/drag/flash performance gates live in `EdgeSnapshotCache.js`, `EdgeRetainedLayer.qml`, and `EdgeFlowLabelLayer.qml`: viewport spatial queries use a single cell-range cache, dirty hit tests call `ensureSpatialIndex`, retained entries gate unchanged `contentKey`s, and flow-label model sync skips unchanged `edgeData` references.
- Selection keeps retained wire delegates alive and paints only highlighted wires through the Canvas overlay, preserving shared selection stacking. Drawing-order changes update a separate model role instead of replacing stroke data. Both renderers use pen-width dash units from `EdgePaintPolicy.js`, and retained pipe routes use one continuous path so dash phase survives corners. `tests/test_edge_snapshot_spatial_index.py` verifies rendered dash placement, unrelated pixels, and delegate/update counts across selection changes.
- `EdgeCanvasLayer.qml` exposes `canvasStateBridgeRef` from `EdgeLayer.sceneBridge`; inline edge typography and flow-label shared roles depend on that bridge projection.
- Live bezier handles: Python sizes standard forward-bezier handles for the payload chord (`route_pipe.py::edge_control_points`). While sockets are displaced from the payload by a `liveNodeGeometry` overlay (settings-group animation, resize preview) or a drag offset, `EdgeLayer._edgeGeometry` adds `EdgeMath.forwardBezierLeadDelta` so the handles fit the live chord. That keeps the wire from reshaping in place at animation start or on drop. The correction is exactly 0 at rest, so settled geometry is unchanged. Flow and backdrop-hidden (side-aware) edges and pipes stay translate-only. Keep `EdgeMath.EDGE_FORWARD_LEAD_MIN` equal to the Python constant; `tests/test_flow_edge_labels.py` guards it. Retained per-delegate drag deltas are 0 at paint time because each drag flush rebuilds incident snapshots. `tests/graph_surface/passive_host_interaction_suite.py` owns the per-frame settings-animation and drag/drop handle checks.

## Flow-Edge Arrows, Reverse, And Labels

- Flow-edge style keys (normalized by `passive_style_normalization.normalize_flow_edge_style_payload`; projected into the payload `flow_style` by `graph_geometry/route_styles.py`): `arrow_head` is the target-end arrowhead (default `filled`) and `arrow_tail` the source-end one (default `none`), both `filled|open|none`; `label_position` is the label centre as a 0..1 arc-length fraction from source to target (absent means automatic placement), and `label_orientation=follow_path` turns the label along the path (`horizontal` is the absent default). `FLOW_EDGE_LAYOUT_KEYS` (`label_position`) is per-edge placement: presets and the style clipboard strip it (`normalize_flow_edge_preset_style_payload`), and Reset/Paste Style keep the edge's own value.
- `EdgePaintPolicy.flowArrowMarkerMetrics` sizes a head from the style width (`max(minLength, 3 * stroke_width + 2)` scene units, so selection emphasis never resizes it) and sets `lineInset`: the stroke ends inside a filled head and at an open head's apex, so it never pokes past a tip. `flowArrowMarkerShape` returns renderer-neutral points; `EdgeArrowPaint.js` paints them for `EdgeCanvasLayer.qml` and the toolbar `EdgeArrowGlyph.qml`. `EdgeMath.trimGeometry` shortens pipe polylines and bezier sub-curves by arc length (with crossing/label breaks the trims become extra break ranges), and `edgeEndMarkerFrame` points each head along the chord over its own length. Flow edges always paint through the Canvas renderer; paint diagnostics report `arrowHead`/`arrowTail`, extents, and `lineTrimStart`/`lineTrimEnd`.
- Reverse Direction swaps source and target in place through `ValidatedGraphMutation.reverse_edges` (identity, label, style, enabled state survive; directed, hidden, same-node, or duplicate results reject the batch) and the scene `reverse_edges` op, one `ACTION_REVERSE_EDGE` history step that mirrors `label_position` so the label stays put. Route payloads publish `reversible` for flow edges whose ports accept both directions (neutral flowchart ports), which enables the toolbar button and the edge context-menu item.
- Labels: `EdgeFlowLabelLayer.flowLabelAnchorScene(geometry, edge, fractionOverride)` places a label at its fraction (else the longest horizontal pipe run or the midpoint) and, when following the path, carries an upright `rotation` (`EdgeMath.uprightLabelAngle`, (-90, 90]). Label text wraps at the 220/120 px maximum over up to `EdgePaintPolicy.FLOW_LABEL_MAX_LINES` lines; `EdgeCanvasLayer` measures the same wrapped box and projects it (rotation included) onto the tangent for the line gap. Snapshots rebuild the anchor when `flowLabelPlacementKey` changes.
- Dragging a label: `EdgeHitTestOverlay.qml` gives label hits priority over path picks (open-hand cursor), selects the edge on press, and after a 4 px threshold previews through `EdgeLayer.setFlowLabelDragPreview` (midpoint snap, end-marker margin); the label, its line gap, and the edge toolbar follow `labelDragAnchorScene`. Release emits `flowLabelDragFinished`, and `GraphCanvasRootLayers.qml` commits one `label_position` style edit through the action router; `holdFlowLabelDragPreviewUntilCommitted` keeps the preview until the committed fraction reaches the snapshots. Double-clicking a label opens the inline editor.

```powershell
.\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_rendering_suite.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py -k "paint_policy or active_data_wire_renderers" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_output_mode_ui.py tests/test_flow_edge_labels.py tests/test_edge_snapshot_spatial_index.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_graph_surface_input_controls.py tests/graph_track_b/scene_model_graph_scene_suite.py -k "active_data_wire or display_mode or request_rewire_edges or ctrl_drag" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_data_tree_ui.py tests/test_graph_surface_input_controls.py -k "port_and_edge_authoring or edge" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_data_type_ui_projection.py -k "type_warning or availability_annotation" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_passive_graph_surface_host.py -k "live_bezier_lead or rederives_connected_wire_handles" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_passive_style_dialogs.py tests/test_graph_canvas_host_presenter.py -n auto --ignore=venv -q
$env:QT_QPA_PLATFORM = "offscreen"; $env:QT_QUICK_CONTROLS_STYLE = "Basic"
& (Join-Path $env:QT_ROOT "bin\qmltestrunner.exe") -input tests/qml_quick/tst_edge_paint_policy.qml -eventdelay 0 -keydelay 0 -mousedelay 0 -o -,txt
Remove-Item Env:QT_QPA_PLATFORM, Env:QT_QUICK_CONTROLS_STYLE -ErrorAction SilentlyContinue
```

## Breadcrumbs
- [Graph Canvas Rendering, Input, And Viewport](../subsystems/graph_canvas.md)
- [Node Execution Visualization](node_execution_visualization.md)

## Update Triggers
Update when edge paint-policy ownership, path geometry, arrowhead kinds/sizing/line trimming, Reverse Direction, active-data structure/display/disabled/selection/error styling, type-reason/availability-warning separation, labels (placement, wrapping, orientation, dragging), inline label editing, selected-edge toolbar controls, Ctrl+E routing, wire marquee/jump actions, hit testing, or edge performance routes change.

## 2026-07-11 Performance Ownership

- Endpoint anchors come from invocation-scoped presentation facts. Stable style/label/geometry changes replace cached payloads without reindex; related lane siblings replace in place around one sorted structural insert/remove.
