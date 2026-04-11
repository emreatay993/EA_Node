import QtQuick 2.15
import QtQml 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

QtObject {
    id: root
    property Item canvasItem: null
    property var shellBridge: null
    property var sceneBridge: null
    property var edgeLayerItem: null
    property var interactionIdleTimer: null
    property int interactionIdleDelayMs: 150
    property real wireDragThreshold: 2

    property var hoveredPort: null
    property var dropPreviewPort: null
    property string dropPreviewEdgeId: ""
    property var dropPreviewNodePayload: null
    property real dropPreviewScreenX: -1
    property real dropPreviewScreenY: -1
    property var pendingConnectionPort: null
    property var wireDragState: null
    property var wireDropCandidate: null
    property bool edgeContextVisible: false
    property bool nodeContextVisible: false
    property string edgeContextEdgeId: ""
    property string nodeContextNodeId: ""
    property real contextMenuX: 0
    property real contextMenuY: 0
    property bool interactionActive: false
    readonly property bool viewportInteractionCacheActive: root.interactionActive

    function _requestEdgeRedraw() {
        if (root.edgeLayerItem && root.edgeLayerItem.requestRedraw)
            root.edgeLayerItem.requestRedraw();
    }

    function _canvasEdges() {
        return root.canvasItem ? (root.canvasItem.edgePayload || []) : [];
    }

    function _sceneNodes() {
        return root.sceneBridge ? root.sceneBridge.nodes_model : [];
    }

    function _scenePortData(nodeId, portKey) {
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedPortKey = String(portKey || "").trim();
        if (!normalizedNodeId || !normalizedPortKey)
            return null;
        var nodes = _sceneNodes();
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (!node || String(node.node_id || "").trim() !== normalizedNodeId)
                continue;
            var ports = node.ports || [];
            for (var j = 0; j < ports.length; j++) {
                var port = ports[j];
                if (port && String(port.key || "").trim() === normalizedPortKey)
                    return port;
            }
            break;
        }
        return null;
    }

    function _normalizedPortDirection(directionLike, fallbackDirection) {
        var normalized = String(directionLike || "").trim().toLowerCase();
        if (normalized === "in" || normalized === "out" || normalized === "neutral")
            return normalized;
        return String(fallbackDirection || "").trim().toLowerCase();
    }

    function _portCardinalSide(portLike, fallbackPortKey) {
        return GraphCanvasLogic.normalizedPortSide(
            portLike && portLike.side !== undefined
                ? portLike.side
                : fallbackPortKey
        );
    }

    function _authoringPortPayload(nodeId, portKey, fallbackDirection, sceneX, sceneY) {
        var portData = _scenePortData(nodeId, portKey);
        var direction = _normalizedPortDirection(
            portData ? portData.direction : fallbackDirection,
            fallbackDirection
        );
        var side = _portCardinalSide(portData, portKey);
        var payload = {
            "node_id": nodeId,
            "port_key": portKey,
            "direction": direction,
            "kind": portData ? String(portData.kind || "") : "",
            "data_type": portData ? String(portData.data_type || "") : "",
            "allow_multiple_connections": portData ? Boolean(portData.allow_multiple_connections) : false,
            "locked": portData ? Boolean(portData.locked) : false,
            "scene_x": sceneX,
            "scene_y": sceneY,
            "valid_drop": false
        };
        if (side)
            payload.side = side;
        if (GraphCanvasLogic.isNeutralFlowPort(payload))
            payload.origin_side = side;
        return payload;
    }

    function _dropTargetInput(sourceDrag, candidate) {
        return GraphCanvasLogic.dropTargetInput(sourceDrag, candidate);
    }

    function _isExactDuplicate(sourceDrag, candidate, edge) {
        return GraphCanvasLogic.isExactDuplicate(sourceDrag, candidate, edge);
    }

    function _portKind(nodeId, portKey) {
        var port = _scenePortData(nodeId, portKey);
        return port ? String(port.kind || "") : "";
    }

    function _portDataType(nodeId, portKey) {
        var port = _scenePortData(nodeId, portKey);
        return port ? String(port.data_type || "any") : "any";
    }

    function _arePortKindsCompatible(sourceKind, targetKind) {
        if (!root.sceneBridge || !root.sceneBridge.are_port_kinds_compatible)
            return false;
        return root.sceneBridge.are_port_kinds_compatible(
            String(sourceKind || ""),
            String(targetKind || "")
        );
    }

    function _areDataTypesCompatible(sourceType, targetType) {
        if (!root.sceneBridge || !root.sceneBridge.are_data_types_compatible)
            return false;
        return root.sceneBridge.are_data_types_compatible(
            String(sourceType || ""),
            String(targetType || "")
        );
    }

    function _isDropAllowed(sourceDrag, candidate) {
        if (!sourceDrag || !candidate)
            return false;
        return GraphCanvasLogic.isDropAllowedWithCompatibility(
            sourceDrag,
            candidate,
            _canvasEdges(),
            _arePortKindsCompatible(
                _portKind(sourceDrag.node_id, sourceDrag.port_key),
                _portKind(candidate.node_id, candidate.port_key)
            ),
            _areDataTypesCompatible(
                _portDataType(sourceDrag.node_id, sourceDrag.port_key),
                _portDataType(candidate.node_id, candidate.port_key)
            )
        );
    }

    function _scenePortPoint(node, port, inputRow, outputRow) {
        return GraphCanvasLogic.scenePortPoint(node, port, inputRow, outputRow);
    }

    function _nearestDropCandidateForWireDrag(screenX, screenY, sourceDrag, thresholdOverride) {
        if (!sourceDrag || !root.canvasItem)
            return null;

        var threshold = Number(thresholdOverride);
        if (!(threshold > 0.0))
            threshold = 14.0;

        var nodes = _sceneNodes();
        var best = null;
        var bestDistance = Number.POSITIVE_INFINITY;
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (!node)
                continue;
            var ports = node.ports || [];
            var inputRow = 0;
            var outputRow = 0;
            for (var j = 0; j < ports.length; j++) {
                var port = ports[j];
                if (!port)
                    continue;
                var point = _scenePortPoint(node, port, inputRow, outputRow);
                if (port.direction === "in")
                    inputRow += 1;
                else
                    outputRow += 1;
                var dx = Number(screenX) - root.canvasItem.sceneToScreenX(point.x);
                var dy = Number(screenY) - root.canvasItem.sceneToScreenY(point.y);
                var distance = Math.sqrt(dx * dx + dy * dy);
                if (distance > threshold || distance >= bestDistance)
                    continue;
                var side = _portCardinalSide(port, port.key);
                var candidate = {
                    "node_id": node.node_id,
                    "port_key": port.key,
                    "direction": _normalizedPortDirection(port.direction, ""),
                    "kind": String(port.kind || ""),
                    "data_type": String(port.data_type || ""),
                    "allow_multiple_connections": Boolean(port.allow_multiple_connections),
                    "locked": Boolean(port.locked),
                    "scene_x": point.x,
                    "scene_y": point.y,
                    "valid_drop": false
                };
                if (side)
                    candidate.side = side;
                candidate.valid_drop = _isDropAllowed(sourceDrag, candidate);
                if (!candidate.valid_drop)
                    continue;
                bestDistance = distance;
                best = candidate;
            }
        }
        return best;
    }

    function _portsCompatibleForAuto(sourcePort, targetPort) {
        return GraphCanvasLogic.portsCompatibleForAuto(
            sourcePort,
            targetPort,
            _arePortKindsCompatible(
                sourcePort ? sourcePort.kind : "",
                targetPort ? targetPort.kind : ""
            ),
            _areDataTypesCompatible(
                sourcePort ? sourcePort.data_type : "",
                targetPort ? targetPort.data_type : ""
            )
        );
    }

    function _libraryPorts(payload) {
        return GraphCanvasLogic.libraryPorts(payload);
    }

    function _hasCompatiblePortForTarget(targetPort, nodePorts) {
        if (!targetPort || !nodePorts || !nodePorts.length)
            return false;
        if (
            targetPort.direction === "in"
            && !Boolean(targetPort.allow_multiple_connections)
            && Number(targetPort.connection_count || 0) > 0
        )
            return false;

        for (var i = 0; i < nodePorts.length; i++) {
            var nodePort = nodePorts[i];
            if (!nodePort || nodePort.exposed === false)
                continue;
            if (
                GraphCanvasLogic.autoConnectCompatibleWithTarget(
                    targetPort,
                    nodePort,
                    _arePortKindsCompatible(
                        nodePort.kind || "",
                        targetPort.kind || ""
                    ),
                    _areDataTypesCompatible(
                        nodePort.data_type || "",
                        targetPort.data_type || ""
                    )
                )
            )
                return true;
        }
        return false;
    }

    function _portDropTargetAtScreen(screenX, screenY, payload) {
        if (!root.canvasItem)
            return null;

        var nodePorts = _libraryPorts(payload);
        if (!nodePorts.length)
            return null;

        var nodes = _sceneNodes();
        var threshold = 12.0;
        var best = null;
        var bestDistance = Number.POSITIVE_INFINITY;

        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (!node)
                continue;
            var ports = node.ports || [];
            var inputRow = 0;
            var outputRow = 0;
            for (var j = 0; j < ports.length; j++) {
                var port = ports[j];
                if (!port)
                    continue;
                var point = _scenePortPoint(node, port, inputRow, outputRow);
                if (port.direction === "in")
                    inputRow += 1;
                else
                    outputRow += 1;
                var dx = Number(screenX) - root.canvasItem.sceneToScreenX(point.x);
                var dy = Number(screenY) - root.canvasItem.sceneToScreenY(point.y);
                var distance = Math.sqrt(dx * dx + dy * dy);
                if (distance > threshold || distance >= bestDistance)
                    continue;
                if (!_hasCompatiblePortForTarget(port, nodePorts))
                    continue;
                bestDistance = distance;
                best = {
                    "mode": "port",
                    "node_id": node.node_id,
                    "port_key": port.key,
                    "direction": port.direction,
                    "edge_id": ""
                };
            }
        }
        return best;
    }

    function _edgeSupportsDrop(edgeId, payload) {
        var normalizedEdgeId = String(edgeId || "").trim();
        if (!normalizedEdgeId)
            return false;

        var edges = _canvasEdges();
        var edge = null;
        for (var i = 0; i < edges.length; i++) {
            if (String(edges[i].edge_id || "").trim() === normalizedEdgeId) {
                edge = edges[i];
                break;
            }
        }
        if (!edge)
            return false;

        var sourcePort = _scenePortData(edge.source_node_id, edge.source_port_key);
        var targetPort = _scenePortData(edge.target_node_id, edge.target_port_key);
        if (!sourcePort || !targetPort)
            return false;

        var nodePorts = _libraryPorts(payload);
        var hasInputCandidate = false;
        var hasOutputCandidate = false;
        for (var j = 0; j < nodePorts.length; j++) {
            var nodePort = nodePorts[j];
            if (!nodePort || nodePort.exposed === false)
                continue;
            if (
                !hasInputCandidate
                && GraphCanvasLogic.autoConnectCompatibleAsInsertedInput(
                    sourcePort,
                    nodePort,
                    _arePortKindsCompatible(
                        sourcePort.kind || "",
                        nodePort.kind || ""
                    ),
                    _areDataTypesCompatible(
                        sourcePort.data_type || "",
                        nodePort.data_type || ""
                    )
                )
            )
                hasInputCandidate = true;
            if (
                !hasOutputCandidate
                && GraphCanvasLogic.autoConnectCompatibleAsInsertedOutput(
                    nodePort,
                    targetPort,
                    _arePortKindsCompatible(
                        nodePort.kind || "",
                        targetPort.kind || ""
                    ),
                    _areDataTypesCompatible(
                        nodePort.data_type || "",
                        targetPort.data_type || ""
                    )
                )
            )
                hasOutputCandidate = true;
            if (hasInputCandidate && hasOutputCandidate)
                return true;
        }
        return false;
    }

    function _computeLibraryDropTarget(screenX, screenY, payload) {
        var portTarget = _portDropTargetAtScreen(screenX, screenY, payload);
        if (portTarget)
            return portTarget;

        var edgeId = root.edgeLayerItem && root.edgeLayerItem.edgeAtScreen
            ? root.edgeLayerItem.edgeAtScreen(screenX, screenY)
            : "";
        if (edgeId && _edgeSupportsDrop(edgeId, payload)) {
            return {
                "mode": "edge",
                "node_id": "",
                "port_key": "",
                "direction": "",
                "edge_id": edgeId
            };
        }

        return {
            "mode": "",
            "node_id": "",
            "port_key": "",
            "direction": "",
            "edge_id": ""
        };
    }

    function _previewNodeMetrics(payload) {
        return GraphCanvasLogic.previewNodeMetrics(payload);
    }

    function previewNodeMetrics() {
        return _previewNodeMetrics(root.dropPreviewNodePayload);
    }

    function _previewVisiblePorts(payload, direction) {
        return GraphCanvasLogic.previewVisiblePorts(payload, direction);
    }

    function previewInputPorts() {
        return _previewVisiblePorts(root.dropPreviewNodePayload, "in");
    }

    function previewOutputPorts() {
        return _previewVisiblePorts(root.dropPreviewNodePayload, "out");
    }

    function previewPortColor(kind) {
        return GraphCanvasLogic.previewPortColor(kind);
    }

    function previewNodeScreenWidth() {
        var zoom = root.canvasItem && root.canvasItem._canvasViewStateBridgeRef
            ? root.canvasItem._canvasViewStateBridgeRef.zoom_value
            : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return GraphCanvasLogic.previewNodeScreenExtent(metrics.default_width, zoom);
    }

    function previewNodeScreenHeight() {
        var zoom = root.canvasItem && root.canvasItem._canvasViewStateBridgeRef
            ? root.canvasItem._canvasViewStateBridgeRef.zoom_value
            : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return GraphCanvasLogic.previewNodeScreenExtent(metrics.default_height, zoom);
    }

    function previewPortLabelsVisible() {
        var zoom = root.canvasItem && root.canvasItem._canvasViewStateBridgeRef
            ? root.canvasItem._canvasViewStateBridgeRef.zoom_value
            : 1.0;
        return GraphCanvasLogic.previewPortLabelsVisible(zoom, root.previewNodeScreenWidth());
    }

    function clearLibraryDropPreview() {
        root.dropPreviewPort = null;
        root.dropPreviewEdgeId = "";
        root.dropPreviewNodePayload = null;
        root.dropPreviewScreenX = -1;
        root.dropPreviewScreenY = -1;
    }

    function updateLibraryDropPreview(screenX, screenY, payload) {
        if (!payload) {
            clearLibraryDropPreview();
            return;
        }
        root.dropPreviewNodePayload = payload;
        root.dropPreviewScreenX = Number(screenX);
        root.dropPreviewScreenY = Number(screenY);
        var target = _computeLibraryDropTarget(screenX, screenY, payload);
        root.dropPreviewPort = target.mode === "port"
            ? {
                "node_id": target.node_id,
                "port_key": target.port_key,
                "direction": target.direction
            }
            : null;
        root.dropPreviewEdgeId = target.mode === "edge" ? target.edge_id : "";
    }

    function performLibraryDrop(screenX, screenY, payload) {
        if (!payload || !root.shellBridge || !root.shellBridge.request_drop_node_from_library || !payload.type_id) {
            clearLibraryDropPreview();
            return;
        }
        if (!root.canvasItem)
            return;
        root.canvasItem.forceActiveFocus();
        root._closeContextMenus();
        root.clearPendingConnection();
        var target = _computeLibraryDropTarget(screenX, screenY, payload);
        root.shellBridge.request_drop_node_from_library(
            String(payload.type_id || ""),
            root.canvasItem.screenToSceneX(screenX),
            root.canvasItem.screenToSceneY(screenY),
            target.mode || "",
            target.node_id || "",
            target.port_key || "",
            target.edge_id || ""
        );
        root.canvasItem.clearEdgeSelection();
        root.clearLibraryDropPreview();
    }

    function _samePort(a, b) {
        if (!a || !b)
            return false;
        return a.node_id === b.node_id && a.port_key === b.port_key;
    }

    function clearPendingConnection() {
        if (!root.pendingConnectionPort)
            return;
        root.pendingConnectionPort = null;
        root.hoveredPort = null;
        _requestEdgeRedraw();
    }

    function _wireDragSourceData(state) {
        if (!state)
            return null;
        var sourcePort = _scenePortData(state.node_id, state.port_key);
        var payload = {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "source_direction": _normalizedPortDirection(
                state.source_direction,
                sourcePort ? sourcePort.direction : ""
            ),
            "kind": sourcePort ? String(sourcePort.kind || "") : "",
            "data_type": sourcePort ? String(sourcePort.data_type || "") : "",
            "allow_multiple_connections": sourcePort ? Boolean(sourcePort.allow_multiple_connections) : false,
            "locked": sourcePort ? Boolean(sourcePort.locked) : false,
            "start_x": state.start_x,
            "start_y": state.start_y,
            "cursor_x": state.cursor_x,
            "cursor_y": state.cursor_y
        };
        var side = _portCardinalSide(sourcePort, state.port_key);
        if (side)
            payload.side = side;
        if (state.origin_side !== undefined)
            payload.origin_side = GraphCanvasLogic.normalizedPortSide(state.origin_side);
        else if (GraphCanvasLogic.isNeutralFlowPort(payload))
            payload.origin_side = side;
        return payload;
    }

    function wireDragSourcePort() {
        var state = root.wireDragState;
        if (!state || !state.active)
            return null;
        var payload = {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "direction": state.source_direction
        };
        if (state.origin_side !== undefined)
            payload.origin_side = GraphCanvasLogic.normalizedPortSide(state.origin_side);
        return payload;
    }

    function wireDragPreviewConnection() {
        var state = root.wireDragState;
        if (!state || !state.active)
            state = null;
        if (state) {
            var target = root.wireDropCandidate;
            var sourcePort = _scenePortData(state.node_id, state.port_key);
            var preview = {
                "source_direction": state.source_direction,
                "source_node_id": state.node_id,
                "source_port_key": state.port_key,
                "source_kind": sourcePort ? String(sourcePort.kind || "") : "",
                "start_x": state.start_x,
                "start_y": state.start_y,
                "target_x": target ? target.scene_x : state.cursor_x,
                "target_y": target ? target.scene_y : state.cursor_y,
                "valid_drop": target ? Boolean(target.valid_drop) : false
            };
            if (state.origin_side !== undefined)
                preview.origin_side = GraphCanvasLogic.normalizedPortSide(state.origin_side);
            if (target) {
                preview.target_node_id = target.node_id;
                preview.target_port_key = target.port_key;
                preview.target_kind = String(_portKind(target.node_id, target.port_key) || "");
                if (target.side !== undefined)
                    preview.target_side = GraphCanvasLogic.normalizedPortSide(target.side);
            }
            return preview;
        }

        var pending = root.pendingConnectionPort;
        var hovered = root.hoveredPort;
        if (!pending || !hovered || _samePort(pending, hovered))
            return null;

        var pendingSource = {
            "node_id": pending.node_id,
            "port_key": pending.port_key,
            "source_direction": pending.direction,
            "kind": String(pending.kind || ""),
            "data_type": String(pending.data_type || ""),
            "allow_multiple_connections": Boolean(pending.allow_multiple_connections),
            "locked": Boolean(pending.locked),
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "cursor_x": hovered.scene_x,
            "cursor_y": hovered.scene_y
        };
        if (pending.side !== undefined)
            pendingSource.side = pending.side;
        if (pending.origin_side !== undefined)
            pendingSource.origin_side = pending.origin_side;
        var pendingCandidate = {
            "node_id": hovered.node_id,
            "port_key": hovered.port_key,
            "direction": hovered.direction,
            "allow_multiple_connections": Boolean(hovered.allow_multiple_connections),
            "scene_x": hovered.scene_x,
            "scene_y": hovered.scene_y,
            "valid_drop": _isDropAllowed(pendingSource, hovered)
        };
        if (hovered.side !== undefined)
            pendingCandidate.side = hovered.side;
        var pendingPreview = {
            "source_direction": pending.direction,
            "source_node_id": pending.node_id,
            "source_port_key": pending.port_key,
            "source_kind": String(_portKind(pending.node_id, pending.port_key) || ""),
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "target_x": pendingCandidate.scene_x,
            "target_y": pendingCandidate.scene_y,
            "valid_drop": pendingCandidate.valid_drop
        };
        pendingPreview.target_node_id = pendingCandidate.node_id;
        pendingPreview.target_port_key = pendingCandidate.port_key;
        pendingPreview.target_kind = String(_portKind(pendingCandidate.node_id, pendingCandidate.port_key) || "");
        if (pending.origin_side !== undefined)
            pendingPreview.origin_side = pending.origin_side;
        if (pendingCandidate.side !== undefined)
            pendingPreview.target_side = pendingCandidate.side;
        return pendingPreview;
    }

    function _updateWireDropCandidate(screenX, screenY, state) {
        var candidate = _nearestDropCandidateForWireDrag(
            screenX,
            screenY,
            _wireDragSourceData(state)
        );
        root.wireDropCandidate = candidate;
        root.hoveredPort = candidate ? candidate : null;
    }

    function _clearWireDragState() {
        if (!root.wireDragState && !root.wireDropCandidate)
            return;
        root.wireDragState = null;
        root.wireDropCandidate = null;
        root.hoveredPort = root.pendingConnectionPort ? root.pendingConnectionPort : null;
        _requestEdgeRedraw();
    }

    function beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) {
        if (!root.canvasItem)
            return;
        root.canvasItem.forceActiveFocus();
        root._closeContextMenus();
        root.wireDropCandidate = null;
        var source = _authoringPortPayload(nodeId, portKey, direction, sceneX, sceneY);
        if (GraphCanvasLogic.isLockedInputPort(source))
            return;
        var state = {
            "node_id": source.node_id,
            "port_key": source.port_key,
            "source_direction": source.direction,
            "start_x": source.scene_x,
            "start_y": source.scene_y,
            "cursor_x": sceneX,
            "cursor_y": sceneY,
            "press_screen_x": Number(screenX),
            "press_screen_y": Number(screenY),
            "active": false
        };
        if (source.origin_side !== undefined)
            state.origin_side = source.origin_side;
        root.wireDragState = state;
    }

    function updatePortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {
        if (!root.canvasItem)
            return;
        var state = root.wireDragState;
        if (!state)
            return;
        var normalizedDirection = _normalizedPortDirection(
            (_scenePortData(nodeId, portKey) || {}).direction,
            direction
        );
        if (state.node_id !== nodeId || state.port_key !== portKey || state.source_direction !== normalizedDirection)
            return;

        var movedEnough = Boolean(dragActive)
            || Math.abs(Number(screenX) - Number(state.press_screen_x)) >= root.wireDragThreshold
            || Math.abs(Number(screenY) - Number(state.press_screen_y)) >= root.wireDragThreshold;
        var next = {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "source_direction": state.source_direction,
            "start_x": state.start_x,
            "start_y": state.start_y,
            "cursor_x": root.canvasItem.screenToSceneX(screenX),
            "cursor_y": root.canvasItem.screenToSceneY(screenY),
            "press_screen_x": state.press_screen_x,
            "press_screen_y": state.press_screen_y,
            "active": state.active || movedEnough
        };
        if (state.origin_side !== undefined)
            next.origin_side = state.origin_side;
        var becameActive = movedEnough && !state.active;
        root.wireDragState = next;
        if (!next.active)
            return;
        if (becameActive)
            root.clearPendingConnection();
        root._updateWireDropCandidate(screenX, screenY, next);
        _requestEdgeRedraw();
    }

    function finishPortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {
        if (!root.canvasItem)
            return;
        var state = root.wireDragState;
        if (!state)
            return;
        var normalizedDirection = _normalizedPortDirection(
            (_scenePortData(nodeId, portKey) || {}).direction,
            direction
        );
        if (state.node_id !== nodeId || state.port_key !== portKey || state.source_direction !== normalizedDirection) {
            root._clearWireDragState();
            return;
        }

        var movedEnoughAtRelease = Math.abs(Number(screenX) - Number(state.press_screen_x)) >= root.wireDragThreshold
            || Math.abs(Number(screenY) - Number(state.press_screen_y)) >= root.wireDragThreshold;
        var wasActive = Boolean(state.active) || Boolean(dragActive) || movedEnoughAtRelease;
        if (!wasActive) {
            root.wireDragState = null;
            root.wireDropCandidate = null;
            return;
        }

        var finalState = {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "source_direction": state.source_direction,
            "start_x": state.start_x,
            "start_y": state.start_y,
            "cursor_x": root.canvasItem.screenToSceneX(screenX),
            "cursor_y": root.canvasItem.screenToSceneY(screenY),
            "press_screen_x": state.press_screen_x,
            "press_screen_y": state.press_screen_y,
            "active": true
        };
        if (state.origin_side !== undefined)
            finalState.origin_side = state.origin_side;
        root.wireDragState = finalState;
        root.clearPendingConnection();
        root._updateWireDropCandidate(screenX, screenY, finalState);
        if (!root.wireDropCandidate) {
            var widened = _nearestDropCandidateForWireDrag(
                Number(screenX),
                Number(screenY),
                _wireDragSourceData(finalState),
                28.0
            );
            if (widened) {
                root.wireDropCandidate = widened;
                root.hoveredPort = widened;
            }
        }

        var candidate = root.wireDropCandidate;
        if (candidate && candidate.valid_drop && root.shellBridge && root.shellBridge.request_connect_ports) {
            root.shellBridge.request_connect_ports(
                finalState.node_id,
                finalState.port_key,
                candidate.node_id,
                candidate.port_key
            );
        } else if (root.shellBridge && root.shellBridge.request_open_connection_quick_insert) {
            var overlayPoint = root.canvasItem.mapToItem(
                root.canvasItem.overlayHostItem ? root.canvasItem.overlayHostItem : root.canvasItem,
                Number(screenX),
                Number(screenY)
            );
            root.shellBridge.request_open_connection_quick_insert(
                finalState.node_id,
                finalState.port_key,
                finalState.cursor_x,
                finalState.cursor_y,
                overlayPoint.x,
                overlayPoint.y
            );
        }
        root._clearWireDragState();
    }

    function cancelWireDrag() {
        if (!root.wireDragState)
            return false;
        root._clearWireDragState();
        return true;
    }

    function handlePortClick(nodeId, portKey, direction, sceneX, sceneY) {
        if (!root.canvasItem)
            return;
        root.canvasItem.forceActiveFocus();
        root._closeContextMenus();
        var clicked = _authoringPortPayload(nodeId, portKey, direction, sceneX, sceneY);
        if (GraphCanvasLogic.isLockedInputPort(clicked))
            return;

        if (!root.pendingConnectionPort) {
            root.pendingConnectionPort = clicked;
            root.hoveredPort = clicked;
            _requestEdgeRedraw();
            return;
        }

        var pending = root.pendingConnectionPort;
        if (_samePort(pending, clicked)) {
            root.pendingConnectionPort = null;
            root.hoveredPort = null;
            _requestEdgeRedraw();
            return;
        }

        var neutralGesturePair = GraphCanvasLogic.isNeutralFlowPort(pending)
            && GraphCanvasLogic.isNeutralFlowPort(clicked);
        if (pending.direction === clicked.direction && !neutralGesturePair) {
            root.pendingConnectionPort = clicked;
            root.hoveredPort = clicked;
            _requestEdgeRedraw();
            return;
        }

        var sourceDrag = {
            "node_id": pending.node_id,
            "port_key": pending.port_key,
            "source_direction": pending.direction,
            "kind": String(pending.kind || ""),
            "data_type": String(pending.data_type || ""),
            "allow_multiple_connections": Boolean(pending.allow_multiple_connections),
            "locked": Boolean(pending.locked),
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "cursor_x": sceneX,
            "cursor_y": sceneY
        };
        if (pending.side !== undefined)
            sourceDrag.side = pending.side;
        if (pending.origin_side !== undefined)
            sourceDrag.origin_side = pending.origin_side;
        clicked.valid_drop = _isDropAllowed(sourceDrag, clicked);
        if (clicked.valid_drop && root.shellBridge && root.shellBridge.request_connect_ports) {
            var created = root.shellBridge.request_connect_ports(
                pending.node_id,
                pending.port_key,
                clicked.node_id,
                clicked.port_key
            );
            if (created) {
                root.pendingConnectionPort = null;
                root.hoveredPort = null;
                _requestEdgeRedraw();
                return;
            }
        }

        root.hoveredPort = clicked;
        _requestEdgeRedraw();
    }

    function _closeContextMenus() {
        root.edgeContextVisible = false;
        root.nodeContextVisible = false;
        root.edgeContextEdgeId = "";
        root.nodeContextNodeId = "";
    }

    function _openEdgeContext(edgeId, x, y) {
        if (!edgeId || !root.canvasItem)
            return;
        root.canvasItem.forceActiveFocus();
        var menuHeight = root.canvasItem._edgeSupportsFlowStyle(edgeId) ? 232 : 48;
        var position = root.canvasItem._clampMenuPosition(x, y, 206, menuHeight);
        root._closeContextMenus();
        root.edgeContextEdgeId = edgeId;
        root.contextMenuX = position.x;
        root.contextMenuY = position.y;
        root.edgeContextVisible = true;
    }

    function _openNodeContext(nodeId, x, y) {
        if (!nodeId || !root.canvasItem)
            return;
        root.canvasItem.forceActiveFocus();
        var menuHeight = root.canvasItem._nodeSupportsPassiveStyle(nodeId)
            ? (root.canvasItem._nodeCanEnterScope(nodeId) ? 340 : 232)
            : (root.canvasItem._nodeCanEnterScope(nodeId) ? 188 : 80);
        var position = root.canvasItem._clampMenuPosition(x, y, 206, menuHeight);
        root._closeContextMenus();
        root.nodeContextNodeId = nodeId;
        root.contextMenuX = position.x;
        root.contextMenuY = position.y;
        root.nodeContextVisible = true;
    }

    function beginViewportInteraction() {
        if (!root.interactionActive)
            root.interactionActive = true;
        if (root.interactionIdleTimer)
            root.interactionIdleTimer.stop();
    }

    function finishViewportInteractionSoon() {
        if (!root.interactionActive) {
            if (root.interactionIdleTimer)
                root.interactionIdleTimer.stop();
            return;
        }
        if (root.interactionIdleTimer)
            root.interactionIdleTimer.restart();
    }

    function noteViewportInteraction() {
        root.beginViewportInteraction();
        if (root.interactionIdleTimer)
            root.interactionIdleTimer.restart();
    }

    function endViewportInteraction() {
        if (root.interactionIdleTimer)
            root.interactionIdleTimer.stop();
        root.interactionActive = false;
    }

    function resetSceneBridgeState() {
        root.pendingConnectionPort = null;
        root.hoveredPort = null;
        root.wireDragState = null;
        root.wireDropCandidate = null;
        root.clearLibraryDropPreview();
    }

    function releaseHostReferences() {
        root.edgeLayerItem = null;
        root.canvasItem = null;
        root.shellBridge = null;
        root.sceneBridge = null;
        root.interactionIdleTimer = null;
    }
}
