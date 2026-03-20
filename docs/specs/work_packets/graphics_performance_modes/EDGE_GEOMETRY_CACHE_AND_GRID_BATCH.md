# Edge Geometry Cache + Grid Batch Optimization

- Date: `2026-03-20`
- Scope: follow-on performance optimization for canvas pan/zoom in both `full_fidelity` and `max_performance` modes.
- Builds on: `GRAPHICS_PERFORMANCE_MODES` packet set (`P00`-`P10`).

## Problem

Pan/zoom interactions become laggy with many nodes and edges. The root cause is that every `view_state_changed` signal triggers `requestViewStateRedraw()`, which fully recomputes all edge geometry and redraws the grid on every mouse-move event during pan/zoom. During viewport interaction, scene-space geometry is stable (no node positions change), yet `_nodeMap()` and `_edgeGeometry()` (including expensive `_buildLivePipePoints()` for pipe-routed edges) are recomputed from scratch on every paint frame.

Node dragging is smooth because it uses GPU texture caching (`layer.enabled`) and only updates connected edges, while pan/zoom redraws the entire edge layer and grid canvas.

## Changes

### 1. Edge Geometry Cache (`EdgeLayer.qml`)

Added a scene-space geometry cache to `EdgeLayer.qml` that avoids recomputing `_nodeMap()` and `_edgeGeometry()` during pan/zoom.

- **Cache properties:** `_cachedNodeMap` and `_cachedEdgeGeometries` hold the last-computed node map and per-edge geometry objects.
- **Cache accessor functions:** `_getNodeMap()` returns the cached node map or rebuilds it on miss. `_getCachedEdgeGeometry(edge, nodeById)` returns cached geometry per `edge_id` or computes and stores it on miss.
- **Invalidation:** `_invalidateGeometryCache()` clears both caches. It is called from `onEdgesChanged`, `onNodesChanged`, `onDragOffsetsChanged`, and `onLiveNodeGeometryChanged` -- the four signals that indicate scene-space data has changed.
- **Non-invalidating redraws:** Visual-only signals (`onSelectedEdgeIdsChanged`, `onPreviewEdgeIdChanged`, `onDragConnectionChanged`, palette changes) trigger `requestRedraw()` without invalidating the geometry cache, since they affect only stroke colors and selection highlights.
- **Pan/zoom path:** `requestViewStateRedraw()` calls `edgeLayer.requestRedraw()` but does NOT invalidate the cache. During `onPaint`, `_getNodeMap()` and `_getCachedEdgeGeometry()` return immediately from cache. The only per-frame cost is the cheap `sceneToScreenX/Y` projection and Canvas 2D draw calls.
- **`flowLabelLayer` binding:** Changed `readonly property var nodeById: root._nodeMap()` to `root._getNodeMap()` so the flow-label Repeater also benefits from the cache.
- **Hit-testing:** `edgeAtScreen()` continues to call `_edgeCullState()`, which now uses the cached geometry. This is correct because hit-testing reads fresh viewport bounds from `_expandedVisibleSceneBounds()` and scene-space geometry from the cache.

### 2. Grid Line Batching (`GraphCanvasBackground.qml`)

Restructured the grid `onPaint` handler to batch all minor grid lines into a single `beginPath/stroke` pair, and all major grid lines into another single `beginPath/stroke` pair. Previously, each individual line had its own `beginPath/moveTo/lineTo/stroke` cycle, resulting in O(n_lines) Canvas 2D state transitions. Now there are exactly 2 state transitions regardless of grid density.

## Changed Files

| File | Change |
|---|---|
| `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml` | Added geometry cache properties, accessor functions, invalidation logic, and updated `onPaint`/`_edgeCullState`/`flowLabelLayer` to use cached data |
| `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml` | Batched minor and major grid line draw calls into single paths |

## Verification

Manual testing (no automated QML rendering tests for these paths):
1. Open a graph with 50+ nodes and many edges
2. Verify pan (middle-click drag) and zoom (scroll wheel) feel responsive
3. Verify node dragging still works (edges update during drag)
4. Verify adding/removing edges renders correctly
5. Verify edge click-to-select hit-testing works
6. Verify flow label positions are correct after mutations

## Residual Risks

- The geometry cache is invalidated conservatively on any node/edge/drag data change. If a future code path mutates scene data without triggering the corresponding QML property-change signal, stale geometry could persist until the next full invalidation.
- The grid batching is a pure Canvas 2D optimization and does not change visual output.
