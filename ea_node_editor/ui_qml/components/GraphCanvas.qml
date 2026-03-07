import QtQuick 2.15
import "graph" as GraphComponents

Item {
    id: root
    property var mainWindowBridge: null
    property var sceneBridge: null
    property var viewBridge: null
    property var edgePayload: []
    property var liveDragOffsets: ({})
    property var selectedEdgeIds: []
    property var hoveredPort: null
    property var pendingConnectionPort: null
    property bool edgeContextVisible: false
    property bool nodeContextVisible: false
    property string edgeContextEdgeId: ""
    property string nodeContextNodeId: ""
    property real contextMenuX: 0
    property real contextMenuY: 0
    readonly property real worldSize: 12000
    readonly property real worldOffset: worldSize / 2
    focus: true
    activeFocusOnTab: true
    clip: true

    function screenToSceneX(screenX) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return (viewBridge ? viewBridge.center_x : 0.0) + (screenX - root.width * 0.5) / Math.max(0.1, zoom);
    }

    function screenToSceneY(screenY) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return (viewBridge ? viewBridge.center_y : 0.0) + (screenY - root.height * 0.5) / Math.max(0.1, zoom);
    }

    function _normalizeEdgeIds(values) {
        var normalized = [];
        var seen = {};
        var sourceValues = values || [];
        for (var i = 0; i < sourceValues.length; i++) {
            var id = String(sourceValues[i] || "").trim();
            if (!id || seen[id])
                continue;
            seen[id] = true;
            normalized.push(id);
        }
        return normalized;
    }

    function _availableEdgeIdSet() {
        var ids = {};
        var edges = root.edgePayload || [];
        for (var i = 0; i < edges.length; i++) {
            ids[edges[i].edge_id] = true;
        }
        return ids;
    }

    function pruneSelectedEdges() {
        var idSet = _availableEdgeIdSet();
        var next = [];
        for (var i = 0; i < root.selectedEdgeIds.length; i++) {
            var edgeId = root.selectedEdgeIds[i];
            if (idSet[edgeId])
                next.push(edgeId);
        }
        root.selectedEdgeIds = next;
    }

    function clearEdgeSelection() {
        if (!root.selectedEdgeIds.length)
            return;
        root.selectedEdgeIds = [];
    }

    function toggleEdgeSelection(edgeId) {
        var next = _normalizeEdgeIds(root.selectedEdgeIds);
        var index = next.indexOf(edgeId);
        if (index >= 0)
            next.splice(index, 1);
        else
            next.push(edgeId);
        root.selectedEdgeIds = next;
    }

    function setExclusiveEdgeSelection(edgeId) {
        root.selectedEdgeIds = edgeId ? [edgeId] : [];
    }

    function updateLiveDragOffset(nodeId, dx, dy) {
        if (!nodeId)
            return;
        var next = {};
        var current = root.liveDragOffsets || {};
        for (var key in current)
            next[key] = current[key];

        if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01) {
            if (next[nodeId] === undefined)
                return;
            delete next[nodeId];
        } else {
            next[nodeId] = {"dx": dx, "dy": dy};
        }
        root.liveDragOffsets = next;
        edgeLayer.requestRedraw();
    }

    function clearLiveDragOffset(nodeId) {
        if (!nodeId)
            return;
        var current = root.liveDragOffsets || {};
        if (current[nodeId] === undefined)
            return;
        var next = {};
        for (var key in current) {
            if (key !== nodeId)
                next[key] = current[key];
        }
        root.liveDragOffsets = next;
        edgeLayer.requestRedraw();
    }

    function _dropTargetInput(sourceDrag, candidate) {
        if (sourceDrag.source_direction === "out") {
            return {
                "node_id": candidate.node_id,
                "port_key": candidate.port_key
            };
        }
        return {
            "node_id": sourceDrag.node_id,
            "port_key": sourceDrag.port_key
        };
    }

    function _isExactDuplicate(sourceDrag, candidate, edge) {
        if (sourceDrag.source_direction === "out") {
            return edge.source_node_id === sourceDrag.node_id
                && edge.source_port_key === sourceDrag.port_key
                && edge.target_node_id === candidate.node_id
                && edge.target_port_key === candidate.port_key;
        }
        return edge.source_node_id === candidate.node_id
            && edge.source_port_key === candidate.port_key
            && edge.target_node_id === sourceDrag.node_id
            && edge.target_port_key === sourceDrag.port_key;
    }

    function _portKind(nodeId, portKey) {
        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (!node || node.node_id !== nodeId)
                continue;
            var ports = node.ports || [];
            for (var j = 0; j < ports.length; j++) {
                var port = ports[j];
                if (port && port.key === portKey)
                    return port.kind || "";
            }
            return "";
        }
        return "";
    }

    function _arePortKindsCompatible(sourceKind, targetKind) {
        if (!sourceKind || !targetKind)
            return false;
        if (sourceKind === "exec" || targetKind === "exec")
            return sourceKind === "exec" && targetKind === "exec";
        return true;
    }

    function _isDropAllowed(sourceDrag, candidate) {
        if (!sourceDrag || !candidate)
            return false;
        if (candidate.node_id === sourceDrag.node_id && candidate.port_key === sourceDrag.port_key)
            return false;
        if (candidate.direction === sourceDrag.source_direction)
            return false;
        var sourceKind = _portKind(sourceDrag.node_id, sourceDrag.port_key);
        var candidateKind = _portKind(candidate.node_id, candidate.port_key);
        if (!_arePortKindsCompatible(sourceKind, candidateKind))
            return false;

        var targetInput = _dropTargetInput(sourceDrag, candidate);
        var edges = root.edgePayload || [];
        for (var i = 0; i < edges.length; i++) {
            var edge = edges[i];
            var sameTargetInput = edge.target_node_id === targetInput.node_id && edge.target_port_key === targetInput.port_key;
            if (!sameTargetInput)
                continue;
            if (_isExactDuplicate(sourceDrag, candidate, edge))
                continue;
            return false;
        }
        return true;
    }

    function _samePort(a, b) {
        if (!a || !b)
            return false;
        return a.node_id === b.node_id && a.port_key === b.port_key && a.direction === b.direction;
    }

    function clearPendingConnection() {
        if (!root.pendingConnectionPort)
            return;
        root.pendingConnectionPort = null;
        root.hoveredPort = null;
        edgeLayer.requestRedraw();
    }

    function handlePortClick(nodeId, portKey, direction, sceneX, sceneY) {
        root.forceActiveFocus();
        root._closeContextMenus();
        var clicked = {
            "node_id": nodeId,
            "port_key": portKey,
            "direction": direction,
            "scene_x": sceneX,
            "scene_y": sceneY,
            "valid_drop": false
        };

        if (!root.pendingConnectionPort) {
            root.pendingConnectionPort = clicked;
            root.hoveredPort = clicked;
            edgeLayer.requestRedraw();
            return;
        }

        var pending = root.pendingConnectionPort;
        if (_samePort(pending, clicked)) {
            root.pendingConnectionPort = null;
            root.hoveredPort = null;
            edgeLayer.requestRedraw();
            return;
        }

        if (pending.direction === clicked.direction) {
            root.pendingConnectionPort = clicked;
            root.hoveredPort = clicked;
            edgeLayer.requestRedraw();
            return;
        }

        var sourceDrag = {
            "node_id": pending.node_id,
            "port_key": pending.port_key,
            "source_direction": pending.direction,
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "cursor_x": sceneX,
            "cursor_y": sceneY
        };
        var candidate = clicked;
        candidate.valid_drop = _isDropAllowed(sourceDrag, candidate);
        if (candidate.valid_drop && mainWindowBridge) {
            var created = mainWindowBridge.connect_ports_from_qml(
                pending.node_id,
                pending.port_key,
                clicked.node_id,
                clicked.port_key
            );
            if (created) {
                root.pendingConnectionPort = null;
                root.hoveredPort = null;
                edgeLayer.requestRedraw();
                return;
            }
        }

        root.hoveredPort = clicked;
        edgeLayer.requestRedraw();
    }

    function _syncEdgePayload() {
        root.edgePayload = sceneBridge ? sceneBridge.edges_model : [];
        pruneSelectedEdges();
        edgeLayer.requestRedraw();
    }

    function _closeContextMenus() {
        root.edgeContextVisible = false;
        root.nodeContextVisible = false;
        root.edgeContextEdgeId = "";
        root.nodeContextNodeId = "";
    }

    function _clampMenuPosition(x, y, menuWidth, menuHeight) {
        return {
            "x": Math.max(4, Math.min(x, root.width - menuWidth - 4)),
            "y": Math.max(4, Math.min(y, root.height - menuHeight - 4))
        };
    }

    function _openEdgeContext(edgeId, x, y) {
        if (!edgeId)
            return;
        root.forceActiveFocus();
        var position = _clampMenuPosition(x, y, 170, 36);
        _closeContextMenus();
        root.edgeContextEdgeId = edgeId;
        root.contextMenuX = position.x;
        root.contextMenuY = position.y;
        root.edgeContextVisible = true;
    }

    function _openNodeContext(nodeId, x, y) {
        if (!nodeId)
            return;
        root.forceActiveFocus();
        var position = _clampMenuPosition(x, y, 170, 72);
        _closeContextMenus();
        root.nodeContextNodeId = nodeId;
        root.contextMenuX = position.x;
        root.contextMenuY = position.y;
        root.nodeContextVisible = true;
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#1D1F24" }
            GradientStop { position: 1.0; color: "#1A1C20" }
        }
    }

    Canvas {
        id: gridCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.fillStyle = "#1D1F24";
            ctx.fillRect(0, 0, width, height);

            var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
            var step = 20 * zoom;
            if (step < 10)
                step = 10;
            var major = step * 5;
            var centerX = viewBridge ? viewBridge.center_x : 0.0;
            var centerY = viewBridge ? viewBridge.center_y : 0.0;

            function normalizedOffset(period, anchor) {
                var raw = anchor % period;
                if (raw < 0)
                    raw += period;
                return raw;
            }

            var minorStartX = normalizedOffset(step, width * 0.5 - centerX * zoom);
            var minorStartY = normalizedOffset(step, height * 0.5 - centerY * zoom);
            var majorStartX = normalizedOffset(major, width * 0.5 - centerX * zoom);
            var majorStartY = normalizedOffset(major, height * 0.5 - centerY * zoom);

            ctx.lineWidth = 1;
            ctx.strokeStyle = "#2A2E37";
            for (var x = minorStartX; x <= width; x += step) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }
            for (var y = minorStartY; y <= height; y += step) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }

            ctx.strokeStyle = "#323746";
            for (x = majorStartX; x <= width; x += major) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }
            for (y = majorStartY; y <= height; y += major) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }
        }
    }

    GraphComponents.EdgeLayer {
        id: edgeLayer
        anchors.fill: parent
        z: 8
        viewBridge: root.viewBridge
        sceneBridge: root.sceneBridge
        edges: root.edgePayload
        nodes: sceneBridge ? sceneBridge.nodes_model : []
        dragOffsets: root.liveDragOffsets
        selectedEdgeIds: root.selectedEdgeIds
        inputEnabled: !(root.edgeContextVisible || root.nodeContextVisible)

        onEdgeClicked: function(edgeId, additive) {
            root.forceActiveFocus();
            root._closeContextMenus();
            root.clearPendingConnection();
            if (additive)
                root.toggleEdgeSelection(edgeId);
            else
                root.setExclusiveEdgeSelection(edgeId);
        }
        onEdgeContextRequested: function(edgeId, screenX, screenY) {
            root._openEdgeContext(edgeId, screenX, screenY);
        }
    }

    Item {
        id: world
        width: root.worldSize
        height: root.worldSize
        scale: viewBridge ? viewBridge.zoom_value : 1.0
        x: root.width * 0.5 - ((viewBridge ? viewBridge.center_x : 0) + root.worldOffset) * scale
        y: root.height * 0.5 - ((viewBridge ? viewBridge.center_y : 0) + root.worldOffset) * scale

        Repeater {
            model: sceneBridge ? sceneBridge.nodes_model : []
            delegate: GraphComponents.NodeCard {
                id: nodeCard
                nodeData: modelData
                worldOffset: root.worldOffset
                hoveredPort: root.hoveredPort
                pendingPort: root.pendingConnectionPort

                onNodeClicked: function(nodeId, additive) {
                    root.forceActiveFocus();
                    root._closeContextMenus();
                    root.clearPendingConnection();
                    if (!sceneBridge)
                        return;
                    if (!additive)
                        root.clearEdgeSelection();
                    sceneBridge.select_node(nodeId, additive);
                }
                onNodeContextRequested: function(nodeId, localX, localY) {
                    var point = nodeCard.mapToItem(root, localX, localY);
                    root._openNodeContext(nodeId, point.x, point.y);
                }
                onDragOffsetChanged: function(nodeId, dx, dy) {
                    root.updateLiveDragOffset(nodeId, dx, dy);
                }
                onDragFinished: function(nodeId, finalX, finalY, moved) {
                    root.clearLiveDragOffset(nodeId);
                    if (sceneBridge) {
                        sceneBridge.move_node(nodeId, finalX, finalY);
                        if (moved) {
                            root.clearEdgeSelection();
                            sceneBridge.select_node(nodeId, false);
                        }
                    }
                }
                onDragCanceled: function(nodeId) {
                    root.clearLiveDragOffset(nodeId);
                }
                onPortClicked: function(nodeId, portKey, direction, sceneX, sceneY) {
                    root.handlePortClick(nodeId, portKey, direction, sceneX, sceneY);
                }
                onPortHoverChanged: function(nodeId, portKey, direction, sceneX, sceneY, hovered) {
                    if (hovered) {
                        root.hoveredPort = {
                            "node_id": nodeId,
                            "port_key": portKey,
                            "direction": direction,
                            "scene_x": sceneX,
                            "scene_y": sceneY,
                            "valid_drop": false
                        };
                    } else if (
                        root.hoveredPort
                        && root.hoveredPort.node_id === nodeId
                        && root.hoveredPort.port_key === portKey
                        && root.hoveredPort.direction === direction
                    ) {
                        root.hoveredPort = null;
                    }
                }
            }
        }
    }

    MouseArea {
        id: marqueeArea
        anchors.fill: parent
        z: -9
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        property bool selecting: false
        property bool additive: false
        property real startX: 0
        property real startY: 0
        property real currentX: 0
        property real currentY: 0

        onPressed: {
            root.forceActiveFocus();
            root._closeContextMenus();
            root.clearPendingConnection();
            selecting = true;
            additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            startX = mouse.x;
            startY = mouse.y;
            currentX = mouse.x;
            currentY = mouse.y;
        }

        onPositionChanged: {
            if (!selecting)
                return;
            currentX = mouse.x;
            currentY = mouse.y;
        }

        onReleased: {
            if (!selecting)
                return;
            currentX = mouse.x;
            currentY = mouse.y;
            var dx = Math.abs(currentX - startX);
            var dy = Math.abs(currentY - startY);
            if (sceneBridge) {
                if (dx >= 4 || dy >= 4) {
                    sceneBridge.select_nodes_in_rect(
                        root.screenToSceneX(startX),
                        root.screenToSceneY(startY),
                        root.screenToSceneX(currentX),
                        root.screenToSceneY(currentY),
                        additive
                    );
                    if (!additive)
                        root.clearEdgeSelection();
                } else if (!additive) {
                    sceneBridge.clear_selection();
                    root.clearEdgeSelection();
                }
            }
            selecting = false;
        }

        onCanceled: {
            selecting = false;
        }
    }

    Rectangle {
        visible: marqueeArea.selecting
            && (Math.abs(marqueeArea.currentX - marqueeArea.startX) >= 2
                || Math.abs(marqueeArea.currentY - marqueeArea.startY) >= 2)
        z: 60
        x: Math.min(marqueeArea.startX, marqueeArea.currentX)
        y: Math.min(marqueeArea.startY, marqueeArea.currentY)
        width: Math.abs(marqueeArea.currentX - marqueeArea.startX)
        height: Math.abs(marqueeArea.currentY - marqueeArea.startY)
        color: "#3360CDFF"
        border.width: 1
        border.color: "#60CDFF"
    }

    MouseArea {
        id: panArea
        anchors.fill: parent
        z: -10
        acceptedButtons: Qt.MiddleButton
        hoverEnabled: true
        property bool panning: false
        property real lastX: 0
        property real lastY: 0

        onPressed: {
            if (!viewBridge)
                return;
            panning = true;
            lastX = mouse.x;
            lastY = mouse.y;
        }

        onPositionChanged: {
            if (!panning || !viewBridge)
                return;
            var dx = (mouse.x - lastX) / Math.max(0.1, viewBridge.zoom_value);
            var dy = (mouse.y - lastY) / Math.max(0.1, viewBridge.zoom_value);
            viewBridge.pan_by(-dx, -dy);
            lastX = mouse.x;
            lastY = mouse.y;
        }

        onReleased: {
            panning = false;
        }
    }

    WheelHandler {
        id: zoomWheel
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: {
            if (!viewBridge)
                return;
            var factor = wheel.angleDelta.y > 0 ? 1.15 : (1.0 / 1.15);
            viewBridge.adjust_zoom(factor);
            wheel.accepted = true;
        }
    }

    Rectangle {
        id: edgeContextPopup
        visible: root.edgeContextVisible
        z: 900
        x: root.contextMenuX
        y: root.contextMenuY
        width: 170
        height: 36
        radius: 4
        color: "#2B2F37"
        border.width: 1
        border.color: "#4A4E58"

        Rectangle {
            anchors.fill: parent
            color: removeEdgeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Remove Connection"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: removeEdgeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!mainWindowBridge || !root.edgeContextEdgeId)
                        return;
                    mainWindowBridge.remove_edge_from_qml(root.edgeContextEdgeId);
                    root.selectedEdgeIds = root.selectedEdgeIds.filter(function(value) {
                        return value !== root.edgeContextEdgeId;
                    });
                    root._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }
    }

    Rectangle {
        id: nodeContextPopup
        visible: root.nodeContextVisible
        z: 900
        x: root.contextMenuX
        y: root.contextMenuY
        width: 170
        height: 72
        radius: 4
        color: "#2B2F37"
        border.width: 1
        border.color: "#4A4E58"

        Rectangle {
            x: 0
            y: 0
            width: parent.width
            height: 36
            color: renameNodeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Rename Node"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: renameNodeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!mainWindowBridge || !root.nodeContextNodeId)
                        return;
                    mainWindowBridge.rename_node_from_qml(root.nodeContextNodeId);
                    root._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }

        Rectangle {
            x: 0
            y: 36
            width: parent.width
            height: 36
            color: removeNodeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Remove Node"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: removeNodeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!mainWindowBridge || !root.nodeContextNodeId)
                        return;
                    mainWindowBridge.remove_node_from_qml(root.nodeContextNodeId);
                    root.clearEdgeSelection();
                    root._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }
    }

    Keys.onDeletePressed: function(event) {
        if (mainWindowBridge)
            mainWindowBridge.delete_selected_graph_items(root.selectedEdgeIds);
        root.selectedEdgeIds = [];
        root.clearPendingConnection();
        root._closeContextMenus();
        event.accepted = true;
    }

    Connections {
        target: sceneBridge
        function onEdges_changed() {
            root.liveDragOffsets = ({});
            root._syncEdgePayload();
        }
        function onNodes_changed() {
            root.liveDragOffsets = ({});
            root._syncEdgePayload();
        }
    }

    Connections {
        target: viewBridge
        function onZoom_changed() {
            gridCanvas.requestPaint();
            edgeLayer.requestRedraw();
        }
        function onCenter_changed() {
            gridCanvas.requestPaint();
            edgeLayer.requestRedraw();
        }
    }

    onSceneBridgeChanged: {
        root.liveDragOffsets = ({});
        root.pendingConnectionPort = null;
        root.hoveredPort = null;
        root._syncEdgePayload();
    }

    onWidthChanged: {
        if (viewBridge)
            viewBridge.set_viewport_size(width, height);
    }

    onHeightChanged: {
        if (viewBridge)
            viewBridge.set_viewport_size(width, height);
    }
}
