# Edge Rendering Packet

Baseline packet: `P05 Edge Renderer Packet Split`.

Use this contract when a change affects edge paint paths, flow-label projection, viewport culling, snapshot reuse, hit testing, or the packet-owned Python helpers that shape edge geometry for QML rendering.

## Owner Files

- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeViewportMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`

## Public Entry Points

- `EdgeLayer.qml`
- `edgeClicked`
- `edgeContextRequested`
- The geometry and cache helpers imported by `EdgeLayer.qml`
- `edge_routing.py` and `graph_surface_metrics.py` as the packet-owned Python geometry inputs consumed before QML paint

## State Owner

- `EdgeLayer.qml` owns the root property contract, redraw coordination, and signal glue.
- `EdgeCanvasLayer.qml` owns the canvas paint path.
- `EdgeFlowLabelLayer.qml` owns flow-label projection and label-layer rendering.
- `EdgeHitTestOverlay.qml` owns pointer hit testing.
- `EdgeSnapshotCache.js` owns visible-edge snapshot and geometry-cache state reused by paint and hit testing.

## Allowed Dependencies

- Edge packet code may depend on graph-theme and shell palettes, viewport transforms, node-surface metrics, scene payloads, and focused edge helper modules.
- Edge packet code may depend on `edge_routing.py` and `graph_surface_metrics.py` for packet-owned geometry calculations.
- Generic edge rendering may react to viewer-agnostic scene data only; viewer-specific state stays in the viewer packet.

## Invariants

- `EdgeLayer.qml` remains a composition surface plus root property contract and signal glue.
- Paint, labels, cache, and hit testing stay split across focused helpers.
- Selected, previewed, drag-preview, flow-label simplification, and edge-crossing semantics stay preserved.
- Paint and hit testing share the same packet-owned snapshot and geometry sources.

## Forbidden Shortcuts

- Do not move paint, label, cache, or hit-test logic back into `EdgeLayer.qml`.
- Do not let hit testing compute geometry from a different source than the paint path.
- Do not introduce viewer-specific behavior into generic edge helpers.
- Do not bypass packet-owned cache invalidation when edge or node geometry changes.

## Required Tests

- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graph_track_b.py`
