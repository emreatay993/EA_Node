# Graph Canvas Input Layers

## Purpose
Use this for pointer routing, canvas input layers, hit testing, node drag/resize, selection, and modal event behavior.

## Start Here
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSurfaceInteractionHost.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostHitTesting.js`
- `ea_node_editor/ui_qml/graph_canvas_command/`
- `ea_node_editor/ui_qml/graph_scene_mutation/policy.py`
- `ea_node_editor/ui_qml/graph_scene/policy_bridge.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/graph_surface/passive_host_boundary_suite.py`
- `tests/graph_surface/pointer_and_modal_suite.py`

## Related Help Reference
- `ea_node_editor/ui/dialogs/input_reference_dialog.py` documents user-facing canvas keyboard and mouse gestures. Update it when canvas selection, pan/zoom, port, node, edge, minimap, or cancellation gestures change.

## Routing Notes
- Group input overlays sit above the edge layer. Preserve explicit edge hit delegation there: use non-mutating `GraphCanvas.edgeAtScreen(...)` for hover/cursor checks and `GraphCanvas.handleEdgePressAtScreen(...)` for left/right press handling before Group drag or selection starts.
- The Group drag cursor belongs only on empty Group hit areas. Hovering an edge inside a Group should keep the edge cursor behavior, not the Group hand cursor.
- Bare Text annotation corner handles use the horizontal-resize cursor and ignore pointer Y deltas; their surface owns the content-measured height.
- `GraphNodeHostGestureLayer` owns the default node/body drag cursor. Suppress that open-hand cursor over surface-owned embedded interactive regions (`_surfaceClaimsBodyInteractionAt`) so live previews, table/folder panels, and inline controls do not look draggable while still allowing empty node body drag affordances.
- Empty-canvas left-drag marquee selection is directional: left-to-right selects only fully enclosed nodes, while right-to-left selects nodes crossed by the rectangle. Ctrl/Shift keep the same directional hit rules and add to the current selection.
- Plain Left/Right on the graph canvas is reserved for selected PDF Panel page navigation through `GraphCanvasActionRouter.navigateSelectedPdfPage(...)`; keep Alt+Left scope navigation and text-field cursor movement guarded separately.
- A real wire drag reuses the existing `wireDragState`: activation requests one fingerprinted compatible-endpoint snapshot from Python, repeated moves and release reuse it, and malformed/role/generation-mismatched snapshots fail closed. Compatible ports reuse the existing rings rather than a new overlay; final graph mutation still revalidates the drop.
- Path Pointer node drops are whole-host targets above the background OS-path catcher but do not add mouse handlers. Accept one OS or Native Explorer path, update `path` and `mode` through one bulk command/history entry, and consume multi-item or locked/read-only drops with `Qt.IgnoreAction`; dropping the same inputs on empty canvas keeps the create-node route.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/graph_surface/pointer_and_modal_suite.py tests/test_graph_surface_input_contract.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/graph_surface/passive_host_boundary_suite.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_inline.py tests/test_graph_action_contracts.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_controls.py -k "selected_pdf_page_navigation" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_controls.py -k "ctrl_drag_reassigns_selected_or_sole_edge_endpoint_without_quick_insert" --ignore=venv -q
.\venv\Scripts\python.exe -m unittest tests.test_group_backdrop_interactions.GroupBackdropInteractionTests -v
```

## Breadcrumbs
- [Graph Canvas Rendering, Input, And Viewport](../subsystems/graph_canvas.md)
- [Surface Input And Inline Controls](surface_input_and_inline_controls.md)

## Update Triggers
Update when input layers, pointer handling, fingerprinted wire-drag compatibility, node gesture routing, graph-surface input tests, or Help reference gesture coverage change.
