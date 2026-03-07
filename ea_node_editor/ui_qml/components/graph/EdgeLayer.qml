import QtQuick 2.15
import "EdgeMath.js" as EdgeMath

Item {
    id: root
    property var viewBridge: null
    property var sceneBridge: null
    property var edges: []
    property var nodes: []
    property var dragOffsets: ({})
    property var selectedEdgeIds: []
    property string previewEdgeId: ""
    property bool inputEnabled: true

    signal edgeClicked(string edgeId, bool additive)
    signal edgeContextRequested(string edgeId, real screenX, real screenY)

    function requestRedraw() {
        edgeCanvas.requestPaint();
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

    function _nodeMap() {
        var byId = {};
        var sceneNodes = root.nodes || [];
        for (var i = 0; i < sceneNodes.length; i++) {
            byId[sceneNodes[i].node_id] = sceneNodes[i];
        }
        return byId;
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

    function _isSelected(edgeId) {
        return (root.selectedEdgeIds || []).indexOf(edgeId) >= 0;
    }

    function _edgeDistanceAtScreen(edge, screenX, screenY, nodeById) {
        var geometry = _edgeGeometry(edge, nodeById);
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
        var bestId = "";
        var bestDistance = Number.POSITIVE_INFINITY;
        var threshold = 8.0;
        for (var i = edgesList.length - 1; i >= 0; i--) {
            var edge = edgesList[i];
            var distance = _edgeDistanceAtScreen(edge, screenX, screenY, nodeById);
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
            var nodeById = root._nodeMap();

            for (var i = 0; i < edgesList.length; i++) {
                var edge = edgesList[i];
                var geometry = root._edgeGeometry(edge, nodeById);
                var selected = root._isSelected(edge.edge_id);
                var previewed = root.previewEdgeId && root.previewEdgeId === edge.edge_id;

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
                ctx.strokeStyle = selected
                    ? "#A7D8FF"
                    : (previewed ? "#FFD173" : (edge.color || "#7AA8FF"));
                ctx.lineWidth = Math.max(1.0, (selected ? 3.0 : (previewed ? 2.8 : 2.0)) * zoom);
                ctx.stroke();
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

    onEdgesChanged: requestRedraw()
    onNodesChanged: requestRedraw()
    onDragOffsetsChanged: requestRedraw()
    onSelectedEdgeIdsChanged: requestRedraw()
    onPreviewEdgeIdChanged: requestRedraw()

    Connections {
        target: root.viewBridge
        function onZoom_changed() {
            root.requestRedraw();
        }
        function onCenter_changed() {
            root.requestRedraw();
        }
    }
}
