import QtQuick 2.15
import "EdgeMath.js" as EdgeMath
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
    property var dragOffsets: ({})
    property var liveNodeGeometry: ({})
    property var selectedEdgeIds: []
    property var visibleSceneRectPayload: ({})
    property string previewEdgeId: ""
    property var dragConnection: null
    property string performanceMode: "full_fidelity"
    property bool transientPerformanceActivityActive: false
    property bool transientDegradedWindowActive: false
    property bool edgeLabelSimplificationActive: false
    property bool inputEnabled: true
    property int _redrawRequestCount: 0
    property real viewportCullMarginPx: 96.0
    property var _cachedNodeMap: null
    property var _cachedEdgeGeometries: ({})
    readonly property color selectedStrokeColor: edgePalette.selected_stroke || "#f0f4fb"
    readonly property color previewStrokeColor: edgePalette.preview_stroke || "#60CDFF"
    readonly property color validDragStrokeColor: edgePalette.valid_drag_stroke || "#60CDFF"
    readonly property color invalidDragStrokeColor: edgePalette.invalid_drag_stroke || "#d0d5de"
    readonly property color fallbackStrokeColor: portKindPalette.data || "#7AA8FF"
    readonly property color flowDefaultStrokeColor: shellPalette.muted_fg || invalidDragStrokeColor
    readonly property color flowDefaultLabelTextColor: shellPalette.panel_title_fg || selectedStrokeColor
    readonly property color flowDefaultLabelBackgroundColor: shellPalette.panel_bg || "#1b1d22"
    readonly property color flowDefaultLabelBorderColor: shellPalette.border || "#3a3d45"
    property real flowLabelHideZoomThreshold: 0.55
    property real flowLabelSimplifyZoomThreshold: 0.85

    signal edgeClicked(string edgeId, bool additive)
    signal edgeContextRequested(string edgeId, real screenX, real screenY)

    function requestRedraw() {
        root._redrawRequestCount += 1;
        edgeCanvas.requestPaint();
    }

    function _invalidateGeometryCache() {
        root._cachedNodeMap = null;
        root._cachedEdgeGeometries = ({});
    }

    function _getNodeMap() {
        if (root._cachedNodeMap !== null)
            return root._cachedNodeMap;
        root._cachedNodeMap = root._nodeMap();
        return root._cachedNodeMap;
    }

    function _getCachedEdgeGeometry(edge, nodeById) {
        var edgeId = edge.edge_id;
        var cached = root._cachedEdgeGeometries[edgeId];
        if (cached !== undefined)
            return cached;
        var geometry = root._edgeGeometry(edge, nodeById);
        root._cachedEdgeGeometries[edgeId] = geometry;
        return geometry;
    }

    function sceneToScreenX(worldX) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        var centerX = viewBridge ? viewBridge.center_x : 0.0;
        return root.width * 0.5 + (worldX - centerX) * zoom;
    }

    function sceneToScreenY(worldY) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        var centerY = viewBridge ? viewBridge.center_y : 0.0;
        return root.height * 0.5 + (worldY - centerY) * zoom;
    }

    function _zoomValue() {
        var zoom = viewBridge ? Number(viewBridge.zoom_value) : 1.0;
        if (!isFinite(zoom) || zoom <= 0.0001)
            return 1.0;
        return zoom;
    }

    function _screenMarginToScene(screenMarginPx) {
        return Math.max(0.0, Number(screenMarginPx || 0.0)) / root._zoomValue();
    }

    function _expandedVisibleSceneBounds() {
        var payload = root.visibleSceneRectPayload;
        if ((!payload || payload.width === undefined || payload.height === undefined) && root.viewBridge)
            payload = root.viewBridge.visible_scene_rect_payload;
        if (!payload)
            return null;
        var x = Number(payload.x);
        var y = Number(payload.y);
        var width = Number(payload.width);
        var height = Number(payload.height);
        if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height) || width <= 0.0 || height <= 0.0)
            return null;
        var sceneMargin = root._screenMarginToScene(root.viewportCullMarginPx);
        return {
            "left": x - sceneMargin,
            "top": y - sceneMargin,
            "right": x + width + sceneMargin,
            "bottom": y + height + sceneMargin
        };
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
        return {
            "left": minX,
            "top": minY,
            "right": maxX,
            "bottom": maxY
        };
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
            var direction = String(port.direction || "");
            var rowIndex = direction === "in" ? inputRow : outputRow;
            if (String(port.key || "") === String(portKey))
                return GraphNodeSurfaceMetrics.portScenePoint(node, direction, rowIndex);
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
            "bottom": node.y + node.height + oy
        };
    }

    function _routeLength(sourceX, sourceY, sourceStubX, targetX, targetY, targetStubX, routeY) {
        return Math.abs(sourceStubX - sourceX)
            + Math.abs(routeY - sourceY)
            + Math.abs(sourceStubX - targetStubX)
            + Math.abs(targetY - routeY)
            + Math.abs(targetX - targetStubX);
    }

    function _buildLivePipePoints(edge, sourceOffset, targetOffset, sourceX, sourceY, targetX, targetY, nodeById) {
        var sourceBounds = _nodeBounds(edge.source_node_id, sourceOffset, nodeById);
        var targetBounds = _nodeBounds(edge.target_node_id, targetOffset, nodeById);
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

    function _edgeGeometry(edge, nodeById) {
        var sxWorld = edge.sx;
        var syWorld = edge.sy;
        var txWorld = edge.tx;
        var tyWorld = edge.ty;
        var c1xWorld = edge.c1x;
        var c1yWorld = edge.c1y;
        var c2xWorld = edge.c2x;
        var c2yWorld = edge.c2y;
        var sourceNode = nodeById[edge.source_node_id];
        var targetNode = nodeById[edge.target_node_id];
        var sourcePoint = _portScenePoint(sourceNode, edge.source_port_key);
        var targetPoint = _portScenePoint(targetNode, edge.target_port_key);

        if (sourcePoint) {
            c1xWorld += sourcePoint.x - sxWorld;
            c1yWorld += sourcePoint.y - syWorld;
            sxWorld = sourcePoint.x;
            syWorld = sourcePoint.y;
        }
        if (targetPoint) {
            c2xWorld += targetPoint.x - txWorld;
            c2yWorld += targetPoint.y - tyWorld;
            txWorld = targetPoint.x;
            tyWorld = targetPoint.y;
        }

        var sourceOffset = root.dragOffsets ? root.dragOffsets[edge.source_node_id] : null;
        if (sourceOffset) {
            sxWorld += sourceOffset.dx;
            syWorld += sourceOffset.dy;
            c1xWorld += sourceOffset.dx;
            c1yWorld += sourceOffset.dy;
        }
        var targetOffset = root.dragOffsets ? root.dragOffsets[edge.target_node_id] : null;
        if (targetOffset) {
            txWorld += targetOffset.dx;
            tyWorld += targetOffset.dy;
            c2xWorld += targetOffset.dx;
            c2yWorld += targetOffset.dy;
        }

        var pipePoints = edge.pipe_points || [];
        if (edge.route === "pipe") {
            pipePoints = _buildLivePipePoints(
                edge,
                sourceOffset,
                targetOffset,
                sxWorld,
                syWorld,
                txWorld,
                tyWorld,
                nodeById
            );
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

    function _geometrySceneBounds(geometry) {
        if (!geometry)
            return null;
        if (geometry.route === "pipe")
            return root._sceneBoundsForPoints(geometry.pipe_points || []);
        return root._sceneBoundsForPoints([
            {"x": geometry.sx, "y": geometry.sy},
            {"x": geometry.c1x, "y": geometry.c1y},
            {"x": geometry.c2x, "y": geometry.c2y},
            {"x": geometry.tx, "y": geometry.ty}
        ]);
    }

    function _edgeCullState(edge, nodeById, viewportBounds) {
        var geometry = root._getCachedEdgeGeometry(edge, nodeById);
        var sceneBounds = root._geometrySceneBounds(geometry);
        var visibleBounds = viewportBounds || root._expandedVisibleSceneBounds();
        var culled = sceneBounds && visibleBounds ? !root._rectIntersects(sceneBounds, visibleBounds) : false;
        return {
            "culled": culled,
            "geometry": culled ? null : geometry
        };
    }

    function _dragGeometry(connection) {
        if (!connection)
            return null;
        var sourceX = Number(connection.start_x);
        var sourceY = Number(connection.start_y);
        var targetX = Number(connection.target_x);
        var targetY = Number(connection.target_y);
        var horizontalDistance = Math.abs(targetX - sourceX);
        var handle = Math.max(42.0, Math.min(170.0, horizontalDistance * 0.42));
        var sourceDirection = String(connection.source_direction || "out");
        var sourceSign = sourceDirection === "in" ? -1.0 : 1.0;
        var targetSign = sourceDirection === "in" ? 1.0 : -1.0;
        return {
            "sx": sourceX,
            "sy": sourceY,
            "tx": targetX,
            "ty": targetY,
            "c1x": sourceX + sourceSign * handle,
            "c1y": sourceY,
            "c2x": targetX + targetSign * handle,
            "c2y": targetY
        };
    }

    function _edgeIsFlow(edge) {
        if (!edge)
            return false;
        if (String(edge.edge_family || "") === "flow")
            return true;
        return String(edge.source_port_kind || "") === "flow"
            && String(edge.target_port_kind || "") === "flow";
    }

    function _flowStyle(edge) {
        if (!edge)
            return ({});
        if (edge.flow_style)
            return edge.flow_style;
        return edge.visual_style || ({});
    }

    function _styleString(value) {
        return String(value || "").trim();
    }

    function _stylePositiveNumber(value, fallback) {
        var numeric = Number(value);
        if (!isFinite(numeric) || numeric <= 0.0)
            return fallback;
        return numeric;
    }

    function _flowStrokePattern(edge) {
        var style = _flowStyle(edge);
        var pattern = _styleString(style.stroke_pattern || style.stroke).toLowerCase();
        if (pattern === "dashed" || pattern === "dotted")
            return pattern;
        return "solid";
    }

    function _flowArrowHead(edge) {
        var style = _flowStyle(edge);
        var arrowHead = _styleString(style.arrow_head).toLowerCase();
        if (!arrowHead) {
            var arrow = style.arrow;
            if (arrow)
                arrowHead = _styleString(arrow.kind).toLowerCase();
        }
        if (arrowHead === "open" || arrowHead === "none")
            return arrowHead;
        return "filled";
    }

    function _flowStrokeColor(edge, selected, previewed) {
        if (selected)
            return root.selectedStrokeColor;
        if (previewed)
            return root.previewStrokeColor;
        var style = _flowStyle(edge);
        return _styleString(style.stroke_color || style.color) || root.flowDefaultStrokeColor;
    }

    function _flowStrokeWidth(edge, selected, previewed, zoom) {
        var baseWidth = _stylePositiveNumber(_flowStyle(edge).stroke_width, 2.0);
        if (selected)
            baseWidth = Math.max(baseWidth, 3.0);
        else if (previewed)
            baseWidth = Math.max(baseWidth, 2.8);
        return Math.max(1.0, baseWidth * zoom);
    }

    function _flowDashPattern(edge, zoom) {
        var unit = Math.max(1.0, zoom);
        var pattern = _flowStrokePattern(edge);
        if (pattern === "dashed")
            return [Math.max(3.0, 8.0 * unit), Math.max(2.0, 5.0 * unit)];
        if (pattern === "dotted")
            return [Math.max(1.0, 1.0 * unit), Math.max(2.0, 4.0 * unit)];
        return [];
    }

    function _edgeAnchor(geometry, fraction) {
        if (!geometry)
            return null;
        if (geometry.route === "pipe")
            return EdgeMath.pointTangentAlongPolyline(geometry.pipe_points || [], fraction);
        return EdgeMath.pointTangentAlongBezier(
            geometry.sx,
            geometry.sy,
            geometry.c1x,
            geometry.c1y,
            geometry.c2x,
            geometry.c2y,
            geometry.tx,
            geometry.ty,
            fraction,
            40
        );
    }

    function _edgeLabelText(edge) {
        return String(edge && edge.label ? edge.label : "").trim();
    }

    function _flowLabelMode(edge) {
        if (!root._edgeIsFlow(edge) || !root._edgeLabelText(edge))
            return "hidden";
        if (root.edgeLabelSimplificationActive)
            return "hidden";
        var zoom = root.viewBridge ? root.viewBridge.zoom_value : 1.0;
        if (zoom < root.flowLabelHideZoomThreshold)
            return "hidden";
        if (zoom < root.flowLabelSimplifyZoomThreshold)
            return "text";
        return "pill";
    }

    function _flowLabelTextColor(edge) {
        return _styleString(_flowStyle(edge).label_text_color) || root.flowDefaultLabelTextColor;
    }

    function _flowLabelBackgroundColor(edge) {
        return _styleString(_flowStyle(edge).label_background_color) || root.flowDefaultLabelBackgroundColor;
    }

    function _flowLabelBorderColor(edge, selected, previewed) {
        if (selected || previewed)
            return root._flowStrokeColor(edge, selected, previewed);
        return root.flowDefaultLabelBorderColor;
    }

    function _flowLabelAnchor(geometry) {
        var anchor = null;
        if (geometry && geometry.route === "pipe") {
            var pipePoints = geometry.pipe_points || [];
            var longestHorizontal = null;
            for (var i = 1; i < pipePoints.length; i++) {
                var start = pipePoints[i - 1];
                var end = pipePoints[i];
                var dx = end.x - start.x;
                var dy = end.y - start.y;
                if (Math.abs(dy) > 0.01)
                    continue;
                var length = Math.abs(dx);
                if (!longestHorizontal || length > longestHorizontal.length) {
                    longestHorizontal = {
                        "x": (start.x + end.x) * 0.5,
                        "y": start.y,
                        "dx": dx >= 0.0 ? 1.0 : -1.0,
                        "dy": 0.0,
                        "angle": dx >= 0.0 ? 0.0 : 180.0,
                        "length": length
                    };
                }
            }
            anchor = longestHorizontal || root._edgeAnchor(geometry, 0.5);
        } else {
            anchor = root._edgeAnchor(geometry, 0.5);
        }
        if (!anchor)
            return null;
        var normalX = -anchor.dy;
        var normalY = anchor.dx;
        if (normalY > 0.0) {
            normalX = -normalX;
            normalY = -normalY;
        }
        return {
            "screen_x": root.sceneToScreenX(anchor.x) + normalX * 18.0,
            "screen_y": root.sceneToScreenY(anchor.y) + normalY * 18.0,
            "angle": anchor.angle
        };
    }

    function _drawFlowArrowHead(ctx, geometry, edge, strokeColor, zoom) {
        var arrowHead = root._flowArrowHead(edge);
        if (arrowHead === "none")
            return;
        var anchor = root._edgeAnchor(geometry, 1.0);
        if (!anchor)
            return;
        var tipX = root.sceneToScreenX(anchor.x);
        var tipY = root.sceneToScreenY(anchor.y);
        var size = Math.max(6.0, 8.0 * zoom);
        var wing = Math.max(3.0, 4.5 * zoom);
        var baseX = tipX - anchor.dx * size;
        var baseY = tipY - anchor.dy * size;
        var normalX = -anchor.dy;
        var normalY = anchor.dx;
        var leftX = baseX + normalX * wing;
        var leftY = baseY + normalY * wing;
        var rightX = baseX - normalX * wing;
        var rightY = baseY - normalY * wing;

        ctx.save();
        ctx.setLineDash([]);
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.strokeStyle = strokeColor;
        ctx.fillStyle = strokeColor;
        ctx.lineWidth = Math.max(1.0, 1.4 * zoom);
        ctx.beginPath();
        ctx.moveTo(leftX, leftY);
        ctx.lineTo(tipX, tipY);
        ctx.lineTo(rightX, rightY);
        if (arrowHead === "filled") {
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        } else {
            ctx.stroke();
        }
        ctx.restore();
    }

    function _isSelected(edgeId) {
        return (root.selectedEdgeIds || []).indexOf(edgeId) >= 0;
    }

    function _edgeDistanceAtScreen(geometry, screenX, screenY) {
        if (!geometry)
            return Number.POSITIVE_INFINITY;
        if (geometry.route === "pipe") {
            var screenPoints = [];
            var pipePoints = geometry.pipe_points || [];
            for (var i = 0; i < pipePoints.length; i++) {
                screenPoints.push(
                    {
                        "x": root.sceneToScreenX(pipePoints[i].x),
                        "y": root.sceneToScreenY(pipePoints[i].y)
                    }
                );
            }
            return EdgeMath.distancePolyline(screenX, screenY, screenPoints);
        }

        return EdgeMath.distanceBezier(
            screenX,
            screenY,
            root.sceneToScreenX(geometry.sx),
            root.sceneToScreenY(geometry.sy),
            root.sceneToScreenX(geometry.c1x),
            root.sceneToScreenY(geometry.c1y),
            root.sceneToScreenX(geometry.c2x),
            root.sceneToScreenY(geometry.c2y),
            root.sceneToScreenX(geometry.tx),
            root.sceneToScreenY(geometry.ty),
            28
        );
    }

    function edgeAtScreen(screenX, screenY) {
        var edgesList = root.edges || [];
        if (!edgesList.length)
            return "";
        var nodeById = _nodeMap();
        var viewportBounds = root._expandedVisibleSceneBounds();
        var bestId = "";
        var bestDistance = Number.POSITIVE_INFINITY;
        var threshold = 8.0;
        for (var i = edgesList.length - 1; i >= 0; i--) {
            var edge = edgesList[i];
            var cullState = root._edgeCullState(edge, nodeById, viewportBounds);
            if (cullState.culled || !cullState.geometry)
                continue;
            var distance = _edgeDistanceAtScreen(cullState.geometry, screenX, screenY);
            if (distance < bestDistance && distance <= threshold) {
                bestDistance = distance;
                bestId = edge.edge_id;
            }
        }
        return bestId;
    }

    Canvas {
        id: edgeCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var zoom = root.viewBridge ? root.viewBridge.zoom_value : 1.0;
            var edgesList = root.edges || [];
            var nodeById = root._getNodeMap();
            var viewportBounds = root._expandedVisibleSceneBounds();

            for (var i = 0; i < edgesList.length; i++) {
                var edge = edgesList[i];
                var cullState = root._edgeCullState(edge, nodeById, viewportBounds);
                if (cullState.culled || !cullState.geometry)
                    continue;
                var geometry = cullState.geometry;
                var selected = root._isSelected(edge.edge_id);
                var previewed = root.previewEdgeId && root.previewEdgeId === edge.edge_id;
                var flowEdge = root._edgeIsFlow(edge);
                ctx.save();
                ctx.beginPath();
                if (geometry.route === "pipe") {
                    var pipePoints = geometry.pipe_points || [];
                    for (var j = 0; j < pipePoints.length; j++) {
                        var point = pipePoints[j];
                        var px = root.sceneToScreenX(point.x);
                        var py = root.sceneToScreenY(point.y);
                        if (j === 0)
                            ctx.moveTo(px, py);
                        else
                            ctx.lineTo(px, py);
                    }
                    ctx.lineJoin = "round";
                    ctx.lineCap = "round";
                } else {
                    ctx.moveTo(root.sceneToScreenX(geometry.sx), root.sceneToScreenY(geometry.sy));
                    ctx.bezierCurveTo(
                        root.sceneToScreenX(geometry.c1x),
                        root.sceneToScreenY(geometry.c1y),
                        root.sceneToScreenX(geometry.c2x),
                        root.sceneToScreenY(geometry.c2y),
                        root.sceneToScreenX(geometry.tx),
                        root.sceneToScreenY(geometry.ty)
                    );
                }

                if (flowEdge) {
                    var flowStrokeColor = root._flowStrokeColor(edge, selected, previewed);
                    ctx.strokeStyle = flowStrokeColor;
                    ctx.lineWidth = root._flowStrokeWidth(edge, selected, previewed, zoom);
                    ctx.setLineDash(root._flowDashPattern(edge, zoom));
                    ctx.stroke();
                    root._drawFlowArrowHead(ctx, geometry, edge, flowStrokeColor, zoom);
                } else {
                    ctx.strokeStyle = selected
                        ? root.selectedStrokeColor
                        : (previewed ? root.previewStrokeColor : (edge.color || root.fallbackStrokeColor));
                    ctx.lineWidth = Math.max(1.0, (selected ? 3.0 : (previewed ? 2.8 : 2.0)) * zoom);
                    ctx.stroke();
                }
                ctx.restore();
            }

            var liveDrag = root.dragConnection;
            if (liveDrag) {
                var dragGeometry = root._dragGeometry(liveDrag);
                if (dragGeometry) {
                    ctx.save();
                    ctx.beginPath();
                    ctx.moveTo(root.sceneToScreenX(dragGeometry.sx), root.sceneToScreenY(dragGeometry.sy));
                    ctx.bezierCurveTo(
                        root.sceneToScreenX(dragGeometry.c1x),
                        root.sceneToScreenY(dragGeometry.c1y),
                        root.sceneToScreenX(dragGeometry.c2x),
                        root.sceneToScreenY(dragGeometry.c2y),
                        root.sceneToScreenX(dragGeometry.tx),
                        root.sceneToScreenY(dragGeometry.ty)
                    );
                    ctx.strokeStyle = liveDrag.valid_drop ? root.validDragStrokeColor : root.invalidDragStrokeColor;
                    ctx.lineWidth = Math.max(1.0, (liveDrag.valid_drop ? 2.7 : 2.0) * zoom);
                    ctx.setLineDash([Math.max(2.0, 6.0 * zoom), Math.max(1.0, 4.0 * zoom)]);
                    ctx.lineCap = "round";
                    ctx.stroke();
                    ctx.restore();
                }
            }

        }
    }

    Item {
        id: flowLabelLayer
        anchors.fill: parent
        readonly property var nodeById: root._getNodeMap()
        readonly property var viewportBounds: root._expandedVisibleSceneBounds()

        Repeater {
            model: root.edges || []

            delegate: Item {
                objectName: "graphEdgeFlowLabelItem"
                property var edgeData: modelData
                property string labelText: root._edgeLabelText(edgeData)
                property string labelMode: root._flowLabelMode(edgeData)
                property bool labelRequested: labelMode !== "hidden"
                property var cullState: labelRequested
                    ? root._edgeCullState(edgeData, flowLabelLayer.nodeById, flowLabelLayer.viewportBounds)
                    : null
                property bool culledByViewport: labelRequested && cullState ? Boolean(cullState.culled) : false
                property bool pillVisible: labelMode === "pill"
                property real anchorScreenX: labelAnchor ? labelAnchor.screen_x : 0.0
                property real anchorScreenY: labelAnchor ? labelAnchor.screen_y : 0.0
                property var geometry: labelRequested && !culledByViewport && cullState ? cullState.geometry : null
                property var labelAnchor: geometry ? root._flowLabelAnchor(geometry) : null
                property bool hitTestMatches: visible
                property bool selectedEdge: root._isSelected(String(edgeData && edgeData.edge_id || ""))
                property bool previewedEdge: root.previewEdgeId && root.previewEdgeId === String(edgeData && edgeData.edge_id || "")
                property real horizontalPadding: pillVisible ? 9.0 : 1.0
                property real verticalPadding: pillVisible ? 5.0 : 0.0
                property real maximumTextWidth: pillVisible ? 180.0 : 110.0
                visible: labelRequested && !culledByViewport && labelAnchor !== null
                width: labelTextItem.width + horizontalPadding * 2.0
                height: labelTextItem.height + verticalPadding * 2.0
                x: anchorScreenX - width * 0.5
                y: anchorScreenY - height * 0.5

                Rectangle {
                    objectName: "graphEdgeFlowLabelPill"
                    anchors.fill: parent
                    radius: height * 0.5
                    visible: parent.pillVisible
                    color: root._flowLabelBackgroundColor(parent.edgeData)
                    border.width: 1
                    border.color: root._flowLabelBorderColor(
                        parent.edgeData,
                        parent.selectedEdge,
                        parent.previewedEdge
                    )
                }

                Text {
                    id: labelTextItem
                    objectName: "graphEdgeFlowLabelText"
                    anchors.centerIn: parent
                    width: Math.min(parent.maximumTextWidth, implicitWidth)
                    text: parent.labelText
                    color: root._flowLabelTextColor(parent.edgeData)
                    font.pixelSize: parent.pillVisible ? 12 : 11
                    font.weight: parent.pillVisible ? Font.DemiBold : Font.Medium
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    MouseArea {
        id: edgeHitArea
        anchors.fill: parent
        enabled: root.inputEnabled
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        propagateComposedEvents: true

        onPressed: {
            var edgeId = root.edgeAtScreen(mouse.x, mouse.y);
            if (!edgeId) {
                mouse.accepted = false;
                return;
            }
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            if (mouse.button === Qt.LeftButton) {
                root.edgeClicked(edgeId, additive);
            } else if (mouse.button === Qt.RightButton) {
                root.edgeContextRequested(edgeId, mouse.x, mouse.y);
            }
            mouse.accepted = true;
        }
    }

    onEdgesChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onNodesChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onDragOffsetsChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onLiveNodeGeometryChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onSelectedEdgeIdsChanged: requestRedraw()
    onPreviewEdgeIdChanged: requestRedraw()
    onDragConnectionChanged: requestRedraw()
    onEdgePaletteChanged: requestRedraw()
    onShellPaletteChanged: requestRedraw()
    onPortKindPaletteChanged: requestRedraw()

}
