import QtQuick 2.15
import QtQml 2.15
import "EdgeMath.js" as EdgeMath
import "EdgeSnapshotCache.js" as EdgeSnapshotCache
import "EdgeViewportMath.js" as EdgeViewportMath
import "GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics

Item {
    id: root
    readonly property var edgePalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.edge_palette
        : ({})
    readonly property var shellPalette: typeof themeBridge !== "undefined"
        ? themeBridge.palette
        : ({})
    readonly property var portKindPalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.port_kind_palette
        : ({})
    property var viewBridge: null
    property var sceneBridge: null
    property var edges: []
    property var nodes: []
    property var progressedExecutionEdgeLookup: ({})
    property int nodeExecutionRevision: 0
    property var dragOffsets: ({})
    property var liveNodeGeometry: ({})
    property var selectedEdgeIds: []
    property var visibleSceneRectPayload: ({})
    property string previewEdgeId: ""
    property var dragConnection: null
    property string edgeCrossingStyle: "none"
    property string performanceMode: "full_fidelity"
    property bool transientPerformanceActivityActive: false
    property bool viewportInteractionActive: false
    property bool transientDegradedWindowActive: false
    property bool edgeLabelSimplificationActive: false
    property bool inputEnabled: true
    property int _redrawRequestCount: 0
    property bool _viewStateRedrawDirty: false
    property real viewportCullMarginPx: 96.0
    property var _cachedNodeMap: null
    property var _cachedEdgeGeometries: ({})
    property var _visibleEdgeSnapshots: []
    property var _visibleEdgeSnapshotById: ({})
    property int _visibleEdgeSnapshotRevision: 0
    property var _executionFlashStateByEdgeId: ({})
    property bool _executionFlashTickerActive: false
    readonly property color selectedStrokeColor: edgePalette.selected_stroke || "#f0f4fb"
    readonly property color previewStrokeColor: edgePalette.preview_stroke || "#60CDFF"
    readonly property color validDragStrokeColor: edgePalette.valid_drag_stroke || "#60CDFF"
    readonly property color invalidDragStrokeColor: edgePalette.invalid_drag_stroke || "#d0d5de"
    readonly property color fallbackStrokeColor: portKindPalette.data || "#7AA8FF"
    readonly property color flowDefaultStrokeColor: shellPalette.muted_fg || invalidDragStrokeColor
    readonly property color flowDefaultLabelTextColor: shellPalette.panel_title_fg || selectedStrokeColor
    readonly property color flowDefaultLabelBackgroundColor: shellPalette.panel_bg || "#1b1d22"
    readonly property color flowDefaultLabelBorderColor: shellPalette.border || "#3a3d45"
    property real executionFlashDurationMs: 240.0
    property real flowLabelHideZoomThreshold: 0.55
    property real flowLabelSimplifyZoomThreshold: 0.85
    property real edgeCrossingGapScreenPx: 14.0
    property real edgeCrossingAnchorGuardScreenPx: 18.0
    property real edgeCrossingMergeScreenPx: 6.0
    property real edgeCrossingSampleStepScreenPx: 10.0
    signal edgeClicked(string edgeId, bool additive)
    signal edgeContextRequested(string edgeId, real screenX, real screenY)
    function requestRedraw() {
        root._viewStateRedrawDirty = false;
        EdgeSnapshotCache.refreshVisibleEdgeSnapshots(root, edgeCanvasLayer, flowLabelLayer);
        root._redrawRequestCount += 1;
        edgeCanvasLayer.requestCanvasPaint();
    }
    function markViewStateRedrawDirty() {
        root._viewStateRedrawDirty = true;
    }
    function flushViewStateRedraw() {
        if (!root._viewStateRedrawDirty)
            return false;
        requestRedraw();
        return true;
    }
    function sceneToScreenX(worldX) {
        return EdgeViewportMath.sceneXToScreen(worldX, EdgeViewportMath.viewportTransform(root));
    }
    function sceneToScreenY(worldY) {
        return EdgeViewportMath.sceneYToScreen(worldY, EdgeViewportMath.viewportTransform(root));
    }
    function _edgeAnchor(geometry, fraction) {
        return edgeCanvasLayer.edgeAnchor(geometry, fraction);
    }
    function _visibleEdgeSnapshot(edgeId) {
        return EdgeSnapshotCache.visibleEdgeSnapshot(root, edgeId);
    }
    function edgeAtScreen(screenX, screenY) {
        return EdgeSnapshotCache.edgeAtScreen(root, edgeCanvasLayer, flowLabelLayer, screenX, screenY);
    }

    function _rectIntersects(a, b) {
        if (!a || !b)
            return true;
        return a.left <= b.right
            && a.right >= b.left
            && a.top <= b.bottom
            && a.bottom >= b.top;
    }

    function _sceneBoundsForPoints(points) {
        if (!points || !points.length)
            return null;
        var minX = Number.POSITIVE_INFINITY;
        var minY = Number.POSITIVE_INFINITY;
        var maxX = Number.NEGATIVE_INFINITY;
        var maxY = Number.NEGATIVE_INFINITY;
        for (var i = 0; i < points.length; i++) {
            var point = points[i];
            if (!point)
                continue;
            var x = Number(point.x);
            var y = Number(point.y);
            if (!isFinite(x) || !isFinite(y))
                continue;
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        }
        if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY))
            return null;
        return {"left": minX, "top": minY, "right": maxX, "bottom": maxY};
    }

    function _nodeMap() {
        var byId = {};
        var sceneNodes = root.nodes || [];
        var liveGeometry = root.liveNodeGeometry || {};
        for (var i = 0; i < sceneNodes.length; i++) {
            var node = sceneNodes[i];
            if (!node || !node.node_id)
                continue;
            var overlay = liveGeometry[node.node_id];
            if (!overlay || node.collapsed) {
                byId[node.node_id] = node;
                continue;
            }
            var merged = {};
            for (var key in node) {
                if (Object.prototype.hasOwnProperty.call(node, key))
                    merged[key] = node[key];
            }
            var liveX = Number(overlay.x);
            var liveY = Number(overlay.y);
            var liveWidth = Number(overlay.width);
            var liveHeight = Number(overlay.height);
            if (isFinite(liveX))
                merged.x = liveX;
            if (isFinite(liveY))
                merged.y = liveY;
            if (isFinite(liveWidth) && liveWidth > 0.0)
                merged.width = liveWidth;
            if (isFinite(liveHeight) && liveHeight > 0.0)
                merged.height = liveHeight;
            byId[node.node_id] = merged;
        }
        return byId;
    }

    function _portScenePoint(node, portKey) {
        if (!node || !portKey)
            return null;
        var ports = node.ports || [];
        var inputRow = 0;
        var outputRow = 0;
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (!port)
                continue;
            if (String(port.key || "") === String(portKey))
                return GraphNodeSurfaceMetrics.portScenePointForPort(node, port, inputRow, outputRow);
            var direction = GraphNodeSurfaceMetrics.portLayoutDirection(port);
            if (direction === "in")
                inputRow += 1;
            else if (direction === "out")
                outputRow += 1;
        }
        return null;
    }

    function _nodeBounds(nodeId, nodeOffset, nodeById) {
        var node = nodeById[nodeId];
        if (!node)
            return null;
        var ox = nodeOffset ? nodeOffset.dx : 0.0;
        var oy = nodeOffset ? nodeOffset.dy : 0.0;
        return {
            "left": node.x + ox,
            "top": node.y + oy,
            "right": node.x + node.width + ox,
            "bottom": node.y + node.height + oy,
            "x": node.x + ox,
            "y": node.y + oy,
            "width": node.width,
            "height": node.height
        };
    }

    function _normalizedCardinalSide(side, fallback) {
        var normalized = String(side || "").trim().toLowerCase();
        if (normalized === "top" || normalized === "right" || normalized === "bottom" || normalized === "left")
            return normalized;
        return String(fallback || "").trim().toLowerCase();
    }

    function _coerceBounds(boundsPayload) {
        if (!boundsPayload)
            return null;
        var x = Number(boundsPayload.x);
        var y = Number(boundsPayload.y);
        var width = Number(boundsPayload.width);
        var height = Number(boundsPayload.height);
        if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height) || width <= 0.0 || height <= 0.0)
            return null;
        return {
            "left": x,
            "top": y,
            "right": x + width,
            "bottom": y + height,
            "x": x,
            "y": y,
            "width": width,
            "height": height
        };
    }

    function _offsetBounds(bounds, dx, dy) {
        if (!bounds)
            return null;
        var offsetX = Number(dx);
        var offsetY = Number(dy);
        if (!isFinite(offsetX))
            offsetX = 0.0;
        if (!isFinite(offsetY))
            offsetY = 0.0;
        return {
            "left": bounds.left + offsetX,
            "top": bounds.top + offsetY,
            "right": bounds.right + offsetX,
            "bottom": bounds.bottom + offsetY,
            "x": bounds.x + offsetX,
            "y": bounds.y + offsetY,
            "width": bounds.width,
            "height": bounds.height
        };
    }

    function _overlayBounds(bounds, overlay) {
        if (!bounds)
            return null;
        if (!overlay)
            return bounds;
        var x = Number(overlay.x);
        var y = Number(overlay.y);
        var width = Number(overlay.width);
        var height = Number(overlay.height);
        var nextX = isFinite(x) ? x : bounds.x;
        var nextY = isFinite(y) ? y : bounds.y;
        var nextWidth = isFinite(width) && width > 0.0 ? width : bounds.width;
        var nextHeight = isFinite(height) && height > 0.0 ? height : bounds.height;
        return {
            "left": nextX,
            "top": nextY,
            "right": nextX + nextWidth,
            "bottom": nextY + nextHeight,
            "x": nextX,
            "y": nextY,
            "width": nextWidth,
            "height": nextHeight
        };
    }

    function _edgeAnchorBounds(edge, prefix, nodeById) {
        var anchorNodeId = String(edge && edge[prefix + "_anchor_node_id"] || "");
        var nodeOffset = root.dragOffsets ? root.dragOffsets[anchorNodeId] : null;
        var nodeBounds = anchorNodeId ? root._nodeBounds(anchorNodeId, nodeOffset, nodeById) : null;
        if (nodeBounds)
            return nodeBounds;

        var bounds = root._coerceBounds(edge ? edge[prefix + "_anchor_bounds"] : null);
        if (!bounds)
            return null;
        var overlay = root.liveNodeGeometry ? root.liveNodeGeometry[anchorNodeId] : null;
        bounds = root._overlayBounds(bounds, overlay);
        if (nodeOffset)
            bounds = root._offsetBounds(bounds, nodeOffset.dx, nodeOffset.dy);
        return bounds;
    }

    function _clampToRange(value, low, high) {
        var numeric = Number(value);
        var minimum = Number(low);
        var maximum = Number(high);
        if (!isFinite(numeric))
            numeric = (minimum + maximum) * 0.5;
        if (!isFinite(minimum) || !isFinite(maximum))
            return numeric;
        if (minimum > maximum)
            return (minimum + maximum) * 0.5;
        return Math.min(maximum, Math.max(minimum, numeric));
    }

    function _perimeterPoint(bounds, side, towardPoint) {
        if (!bounds)
            return null;
        var normalizedSide = root._normalizedCardinalSide(side, "right");
        var towardX = towardPoint ? Number(towardPoint.x) : (bounds.left + bounds.right) * 0.5;
        var towardY = towardPoint ? Number(towardPoint.y) : (bounds.top + bounds.bottom) * 0.5;
        if (!isFinite(towardX))
            towardX = (bounds.left + bounds.right) * 0.5;
        if (!isFinite(towardY))
            towardY = (bounds.top + bounds.bottom) * 0.5;
        var insetX = Math.min(12.0, bounds.width * 0.5);
        var insetY = Math.min(12.0, bounds.height * 0.5);
        if (normalizedSide === "left") {
            return {"x": bounds.left, "y": root._clampToRange(towardY, bounds.top + insetY, bounds.bottom - insetY)};
        }
        if (normalizedSide === "right") {
            return {"x": bounds.right, "y": root._clampToRange(towardY, bounds.top + insetY, bounds.bottom - insetY)};
        }
        if (normalizedSide === "top") {
            return {"x": root._clampToRange(towardX, bounds.left + insetX, bounds.right - insetX), "y": bounds.top};
        }
        return {"x": root._clampToRange(towardX, bounds.left + insetX, bounds.right - insetX), "y": bounds.bottom};
    }

    function _edgeEndpointState(edge, prefix, nodeById, oppositePoint) {
        var pointX = Number(edge && edge[prefix === "source" ? "sx" : "tx"] || 0.0);
        var pointY = Number(edge && edge[prefix === "source" ? "sy" : "ty"] || 0.0);
        var anchorNodeId = String(edge && edge[prefix + "_anchor_node_id"] || edge && edge[prefix + "_node_id"] || "");
        var portKey = String(edge && edge[prefix + "_port_key"] || "");
        var fallbackSide = prefix === "source" ? "right" : "left";
        var side = root._normalizedCardinalSide(
            edge && edge[prefix + "_anchor_side"],
            root._normalizedCardinalSide(edge && edge[prefix + "_port_side"], fallbackSide)
        );
        var anchorKind = String(edge && edge[prefix + "_anchor_kind"] || "node");
        var bounds = root._edgeAnchorBounds(edge, prefix, nodeById);
        if (anchorKind === "node") {
            var anchorNode = nodeById[anchorNodeId];
            var portPoint = root._portScenePoint(anchorNode, portKey);
            if (portPoint) {
                // Drag previews keep the scene payload static, so edge anchors need the
                // transient node offset applied explicitly while the node is moving.
                var nodeOffset = root.dragOffsets ? root.dragOffsets[anchorNodeId] : null;
                var offsetX = nodeOffset ? Number(nodeOffset.dx) : 0.0;
                var offsetY = nodeOffset ? Number(nodeOffset.dy) : 0.0;
                if (!isFinite(offsetX))
                    offsetX = 0.0;
                if (!isFinite(offsetY))
                    offsetY = 0.0;
                return {
                    "point": {"x": portPoint.x + offsetX, "y": portPoint.y + offsetY},
                    "bounds": bounds,
                    "side": side
                };
            }
        }
        if (bounds) {
            return {
                "point": root._perimeterPoint(bounds, side, oppositePoint),
                "bounds": bounds,
                "side": side
            };
        }
        return {"point": {"x": pointX, "y": pointY}, "bounds": bounds, "side": side};
    }

    function _routeLength(sourceX, sourceY, sourceStubX, targetX, targetY, targetStubX, routeY) {
        return Math.abs(sourceStubX - sourceX)
            + Math.abs(routeY - sourceY)
            + Math.abs(sourceStubX - targetStubX)
            + Math.abs(targetY - routeY)
            + Math.abs(targetX - targetStubX);
    }

    function _buildLegacyPipePoints(edge, sourceBounds, targetBounds, sourceX, sourceY, targetX, targetY, nodeById) {
        if (!sourceBounds && edge && edge.source_node_id)
            sourceBounds = root._nodeBounds(edge.source_node_id, null, nodeById);
        if (!targetBounds && edge && edge.target_node_id)
            targetBounds = root._nodeBounds(edge.target_node_id, null, nodeById);
        var laneBias = edge.lane_bias || 0.0;
        var stub = Math.min(72.0, Math.max(32.0, Math.max(44.0, Math.abs(targetX - sourceX) * 0.2)));
        var sourceStubX;
        var targetStubX;
        var sourceTop;
        var sourceBottom;
        var targetTop;
        var targetBottom;

        if (sourceBounds && targetBounds) {
            sourceStubX = Math.max(sourceBounds.right, sourceX) + stub;
            targetStubX = Math.min(targetBounds.left, targetX) - stub;
            sourceTop = sourceBounds.top;
            sourceBottom = sourceBounds.bottom;
            targetTop = targetBounds.top;
            targetBottom = targetBounds.bottom;
        } else {
            sourceStubX = sourceX + stub;
            targetStubX = targetX - stub;
            sourceTop = Math.min(sourceY, targetY) - 40.0;
            sourceBottom = Math.max(sourceY, targetY) + 40.0;
            targetTop = sourceTop;
            targetBottom = sourceBottom;
        }

        if (sourceStubX <= targetStubX) {
            var midX = (sourceStubX + targetStubX) * 0.5;
            sourceStubX = midX + 22.0;
            targetStubX = midX - 22.0;
        }

        var verticalClearance = 56.0 * 0.6 + Math.abs(laneBias) * 0.8;
        var topBound = Math.min(sourceTop, targetTop);
        var bottomBound = Math.max(sourceBottom, targetBottom);
        var topRouteY = topBound - verticalClearance - Math.max(0.0, laneBias);
        var bottomRouteY = bottomBound + verticalClearance + Math.max(0.0, -laneBias);
        var candidates = [{"y": topRouteY, "priority": 1}, {"y": bottomRouteY, "priority": 1}];

        var middleLow = null;
        var middleHigh = null;
        if (sourceBottom + 10.0 <= targetTop - 10.0) {
            middleLow = sourceBottom + 10.0;
            middleHigh = targetTop - 10.0;
        } else if (targetBottom + 10.0 <= sourceTop - 10.0) {
            middleLow = targetBottom + 10.0;
            middleHigh = sourceTop - 10.0;
        }

        if (middleLow !== null && middleHigh !== null && middleLow <= middleHigh) {
            var preferredMiddle = (sourceY + targetY) * 0.5 + laneBias * 0.35;
            var middleRouteY = EdgeMath.clamp(preferredMiddle, middleLow, middleHigh);
            candidates.push({"y": middleRouteY, "priority": 0});
        }

        var best = candidates[0];
        var bestLength = _routeLength(sourceX, sourceY, sourceStubX, targetX, targetY, targetStubX, best.y);
        for (var c = 1; c < candidates.length; c++) {
            var candidate = candidates[c];
            var candidateLength = _routeLength(
                sourceX,
                sourceY,
                sourceStubX,
                targetX,
                targetY,
                targetStubX,
                candidate.y
            );
            if (candidateLength < bestLength
                || (Math.abs(candidateLength - bestLength) < 0.01 && candidate.priority < best.priority)) {
                best = candidate;
                bestLength = candidateLength;
            }
        }

        return [
            {"x": sourceX, "y": sourceY},
            {"x": sourceStubX, "y": sourceY},
            {"x": sourceStubX, "y": best.y},
            {"x": targetStubX, "y": best.y},
            {"x": targetStubX, "y": targetY},
            {"x": targetX, "y": targetY}
        ];
    }

    function _buildFlowPipePoints(sourceX, sourceY, targetX, targetY, edge, sourceBounds, targetBounds, sourceSide, targetSide) {
        return EdgeMath.flowPipeRoute(
            {"x": sourceX, "y": sourceY},
            {"x": targetX, "y": targetY},
            {
                "sourceSide": String(sourceSide || edge && edge.source_anchor_side || edge && edge.source_port_side || ""),
                "targetSide": String(targetSide || edge && edge.target_anchor_side || edge && edge.target_port_side || ""),
                "sourceBounds": sourceBounds,
                "targetBounds": targetBounds,
                "laneBias": Number(edge && edge.lane_bias || 0.0)
            }
        );
    }

    function _previewIsFlow(connection) {
        if (!connection)
            return false;
        var sourceKind = String(connection.source_kind || "").trim().toLowerCase();
        var targetKind = String(connection.target_kind || "").trim().toLowerCase();
        if (sourceKind === "flow" && (!targetKind || targetKind === "flow"))
            return true;
        return !!String(connection.origin_side || "").trim()
            || !!String(connection.target_side || "").trim();
    }

    function _previewFallbackTargetSide(sourceX, sourceY, targetX, targetY) {
        var dx = Number(targetX) - Number(sourceX);
        var dy = Number(targetY) - Number(sourceY);
        if (Math.abs(dx) >= Math.abs(dy))
            return dx >= 0.0 ? "left" : "right";
        return dy >= 0.0 ? "top" : "bottom";
    }

    function _edgeGeometry(edge, nodeById) {
        var sxWorld = edge.sx;
        var syWorld = edge.sy;
        var txWorld = edge.tx;
        var tyWorld = edge.ty;
        var c1xWorld = edge.c1x;
        var c1yWorld = edge.c1y;
        var c2xWorld = edge.c2x;
        var c2yWorld = edge.c2y;
        var sourceState = root._edgeEndpointState(edge, "source", nodeById, {"x": txWorld, "y": tyWorld});
        var targetState = root._edgeEndpointState(
            edge,
            "target",
            nodeById,
            sourceState && sourceState.point ? sourceState.point : {"x": sxWorld, "y": syWorld}
        );
        sourceState = root._edgeEndpointState(
            edge,
            "source",
            nodeById,
            targetState && targetState.point ? targetState.point : {"x": txWorld, "y": tyWorld}
        );
        if (sourceState && sourceState.point) {
            c1xWorld += sourceState.point.x - sxWorld;
            c1yWorld += sourceState.point.y - syWorld;
            sxWorld = sourceState.point.x;
            syWorld = sourceState.point.y;
        }
        if (targetState && targetState.point) {
            c2xWorld += targetState.point.x - txWorld;
            c2yWorld += targetState.point.y - tyWorld;
            txWorld = targetState.point.x;
            tyWorld = targetState.point.y;
        }

        var pipePoints = edge.pipe_points || [];
        if (edge.route === "pipe") {
            var sourceBounds = sourceState ? sourceState.bounds : null;
            var targetBounds = targetState ? targetState.bounds : null;
            var sourceSide = sourceState ? sourceState.side : root._normalizedCardinalSide(edge.source_anchor_side, edge.source_port_side);
            var targetSide = targetState ? targetState.side : root._normalizedCardinalSide(edge.target_anchor_side, edge.target_port_side);
            pipePoints = edgeCanvasLayer.edgeIsFlow(edge)
                ? _buildFlowPipePoints(
                    sxWorld,
                    syWorld,
                    txWorld,
                    tyWorld,
                    edge,
                    sourceBounds,
                    targetBounds,
                    sourceSide,
                    targetSide
                )
                : _buildLegacyPipePoints(
                    edge,
                    sourceBounds,
                    targetBounds,
                    sxWorld,
                    syWorld,
                    txWorld,
                    tyWorld,
                    nodeById
                );
            var pipeHandles = EdgeMath.pipeControlHandles(pipePoints);
            c1xWorld = pipeHandles.first.x;
            c1yWorld = pipeHandles.first.y;
            c2xWorld = pipeHandles.last.x;
            c2yWorld = pipeHandles.last.y;
        }

        return {
            "sx": sxWorld,
            "sy": syWorld,
            "tx": txWorld,
            "ty": tyWorld,
            "c1x": c1xWorld,
            "c1y": c1yWorld,
            "c2x": c2xWorld,
            "c2y": c2yWorld,
            "route": edge.route,
            "pipe_points": pipePoints
        };
    }

    function _dragGeometry(connection) {
        if (!connection)
            return null;
        var sourceX = Number(connection.start_x);
        var sourceY = Number(connection.start_y);
        var targetX = Number(connection.target_x);
        var targetY = Number(connection.target_y);
        var dominantDistance = Math.max(Math.abs(targetX - sourceX), Math.abs(targetY - sourceY));
        var handle = Math.max(42.0, Math.min(170.0, dominantDistance * 0.42));
        var sourceDirection = String(connection.source_direction || "out");
        var originSide = GraphNodeSurfaceMetrics.portCardinalSide({"side": connection.origin_side});
        var targetSide = GraphNodeSurfaceMetrics.portCardinalSide({"side": connection.target_side});
        if (root._previewIsFlow(connection)) {
            var nodeById = EdgeSnapshotCache.getNodeMap(root);
            var sourceBounds = connection.source_node_id ? root._nodeBounds(connection.source_node_id, null, nodeById) : null;
            var targetBounds = connection.target_node_id ? root._nodeBounds(connection.target_node_id, null, nodeById) : null;
            var resolvedSourceSide = EdgeMath.normalizeCardinalSide(originSide, sourceDirection === "in" ? "left" : "right");
            var resolvedTargetSide = EdgeMath.normalizeCardinalSide(
                targetSide,
                root._previewFallbackTargetSide(sourceX, sourceY, targetX, targetY)
            );
            var pipePoints = EdgeMath.flowPipeRoute(
                {"x": sourceX, "y": sourceY},
                {"x": targetX, "y": targetY},
                {
                    "sourceSide": resolvedSourceSide,
                    "targetSide": resolvedTargetSide,
                    "sourceBounds": sourceBounds,
                    "targetBounds": targetBounds,
                    "laneBias": 0.0
                }
            );
            var pipeHandles = EdgeMath.pipeControlHandles(pipePoints);
            return {
                "sx": sourceX,
                "sy": sourceY,
                "tx": targetX,
                "ty": targetY,
                "c1x": pipeHandles.first.x,
                "c1y": pipeHandles.first.y,
                "c2x": pipeHandles.last.x,
                "c2y": pipeHandles.last.y,
                "route": "pipe",
                "pipe_points": pipePoints
            };
        }
        var sourceNormal = originSide
            ? GraphNodeSurfaceMetrics.flowchartAnchorNormal(originSide)
            : (sourceDirection === "in" ? {"x": -1.0, "y": 0.0} : {"x": 1.0, "y": 0.0});
        var targetNormal = targetSide
            ? GraphNodeSurfaceMetrics.flowchartAnchorNormal(targetSide)
            : (sourceDirection === "in" ? {"x": 1.0, "y": 0.0} : {"x": -1.0, "y": 0.0});
        return {
            "sx": sourceX,
            "sy": sourceY,
            "tx": targetX,
            "ty": targetY,
            "c1x": sourceX + sourceNormal.x * handle,
            "c1y": sourceY + sourceNormal.y * handle,
            "c2x": targetX + targetNormal.x * handle,
            "c2y": targetY + targetNormal.y * handle,
            "route": "bezier",
            "pipe_points": []
        };
    }

    Timer {
        id: executionFlashTimer
        interval: 16
        repeat: true
        running: root._executionFlashTickerActive
        onTriggered: root.requestRedraw()
    }

    EdgeCanvasLayer {
        id: edgeCanvasLayer
        anchors.fill: parent
        edgeLayer: root
    }

    EdgeFlowLabelLayer {
        id: flowLabelLayer
        anchors.fill: parent
        edgeLayer: root
        canvasLayer: edgeCanvasLayer
    }

    EdgeHitTestOverlay {
        id: edgeHitTestOverlay
        anchors.fill: parent
        edgeLayer: root
        inputEnabled: root.inputEnabled
        onEdgeClicked: function(edgeId, additive) {
            root.edgeClicked(edgeId, additive);
        }
        onEdgeContextRequested: function(edgeId, screenX, screenY) {
            root.edgeContextRequested(edgeId, screenX, screenY);
        }
    }

    onEdgesChanged: { EdgeSnapshotCache.invalidateGeometryCache(root); requestRedraw(); }
    onNodesChanged: { EdgeSnapshotCache.invalidateGeometryCache(root); requestRedraw(); }
    onDragOffsetsChanged: { EdgeSnapshotCache.invalidateGeometryCache(root); requestRedraw(); }
    onLiveNodeGeometryChanged: { EdgeSnapshotCache.invalidateGeometryCache(root); requestRedraw(); }
    onSelectedEdgeIdsChanged: requestRedraw()
    onPreviewEdgeIdChanged: requestRedraw()
    onDragConnectionChanged: requestRedraw()
    onEdgePaletteChanged: requestRedraw()
    onShellPaletteChanged: requestRedraw()
    onPortKindPaletteChanged: requestRedraw()
    onNodeExecutionRevisionChanged: requestRedraw()
    onEdgeCrossingStyleChanged: requestRedraw()
    onPerformanceModeChanged: requestRedraw()
    onTransientPerformanceActivityActiveChanged: {
        if (root.transientPerformanceActivityActive)
            markViewStateRedrawDirty()
        else
            requestRedraw()
    }
    onTransientDegradedWindowActiveChanged: requestRedraw()
    onEdgeLabelSimplificationActiveChanged: requestRedraw()
}
