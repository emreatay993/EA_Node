# Graph Canvas Packet

Baseline packet: `P04 Graph Canvas Root Packetization`.

Use this contract when a change affects the `GraphCanvas.qml` root contract, canvas root bindings, root-local helper forwarding, input layers, or canvas-local composition seams that sit between focused bridges and graph delegates.

## Owner Files

- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootApi.js`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`

## Public Entry Points

- `GraphCanvas.qml`
- `toggleMinimapExpanded()`
- `clearLibraryDropPreview()`
- `updateLibraryDropPreview()`
- `isPointInCanvas()`
- `performLibraryDrop()`

## State Owner

- `GraphCanvas.qml` owns composition and the stable root contract only.
- `GraphCanvasRootBindings.qml` resolves root-level bindings from focused bridges.
- `GraphCanvasSceneLifecycle`, `GraphCanvasViewportController`, `GraphCanvasInteractionState`, and `GraphCanvasSceneState` own ephemeral canvas-local interaction and redraw state behind the root contract.
- Graph-scene, shell, and view bridges remain the authoritative external state owners.

## Allowed Dependencies

- Graph-canvas packet code may depend on `graphCanvasStateBridge`, `graphCanvasCommandBridge`, `graphCanvasViewBridge`, graph-scene payloads, and focused canvas helper components.
- Graph-canvas packet code may coordinate with node-surface helpers, but shell-owned overlays stay outside the canvas root.
- Canvas packet code may call through `GraphCanvasRootApi.js` to focused helper objects instead of duplicating forwarding logic in the root.

## Invariants

- `GraphCanvas.qml` remains composition-first and exposes only the documented stable public root methods.
- Root-local property binding clusters stay in `GraphCanvasRootBindings.qml`.
- Non-public layer composition stays in `GraphCanvasRootLayers.qml`.
- Root-local forwarding helpers stay in `GraphCanvasRootApi.js`.
- Shell-owned overlays remain shell-owned rather than becoming canvas-local widgets.

## Forbidden Shortcuts

- Do not reopen `GraphCanvas.qml` as a general workflow bucket.
- Do not bypass focused bridges with new raw host globals or compatibility-only context properties.
- Do not move shell-owned overlays or search surfaces into the canvas packet.
- Do not duplicate input, context-menu, or drag-preview logic between the root and helper layers when a focused helper already owns the seam.

## Required Tests

- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`
