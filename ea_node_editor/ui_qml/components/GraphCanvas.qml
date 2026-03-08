import QtQuick 2.15
import "graph" as GraphComponents

Item {
    id: root
    objectName: "graphCanvas"
    property var mainWindowBridge: null
    property var sceneBridge: null
    property var viewBridge: null
    property var edgePayload: []
    property var liveDragOffsets: ({})
    property var selectedEdgeIds: []
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
    property bool minimapExpanded: true
    readonly property real wireDragThreshold: 2
    readonly property real worldSize: 12000
    readonly property real worldOffset: worldSize / 2
    readonly property real minimapExpandedWidth: 238
    readonly property real minimapExpandedHeight: 162
    readonly property real minimapCollapsedWidth: 36
    readonly property real minimapCollapsedHeight: 28
    focus: true
    activeFocusOnTab: true
    clip: true

    function toggleMinimapExpanded() {
        root.minimapExpanded = !root.minimapExpanded;
    }

    function screenToSceneX(screenX) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return (viewBridge ? viewBridge.center_x : 0.0) + (screenX - root.width * 0.5) / Math.max(0.1, zoom);
    }

    function screenToSceneY(screenY) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return (viewBridge ? viewBridge.center_y : 0.0) + (screenY - root.height * 0.5) / Math.max(0.1, zoom);
    }

    function _wheelDeltaY(eventObj) {
        if (!eventObj)
            return 0.0;
        var delta = 0.0;
        if (eventObj.angleDelta && Number(eventObj.angleDelta.y) !== 0)
            delta = Number(eventObj.angleDelta.y);
        else if (eventObj.pixelDelta && Number(eventObj.pixelDelta.y) !== 0)
            delta = Number(eventObj.pixelDelta.y) * 0.5;
        if (eventObj.inverted)
            delta = -delta;
        return delta;
    }

    function applyWheelZoom(eventObj) {
        if (!viewBridge)
            return false;
        var deltaY = _wheelDeltaY(eventObj);
        if (Math.abs(deltaY) < 0.001)
            return false;

        var cursorX = Number(eventObj && eventObj.x);
        var cursorY = Number(eventObj && eventObj.y);
        var hasCursor = isFinite(cursorX) && isFinite(cursorY);
        var sceneBeforeX = 0.0;
        var sceneBeforeY = 0.0;
        if (hasCursor) {
            sceneBeforeX = screenToSceneX(cursorX);
            sceneBeforeY = screenToSceneY(cursorY);
        }

        var steps = deltaY / 120.0;
        if (Math.abs(steps) < 0.01)
            steps = deltaY > 0 ? 1.0 : -1.0;
        steps = Math.max(-1.0, Math.min(1.0, steps));
        var factor = Math.pow(1.15, steps);
        viewBridge.adjust_zoom(factor);

        if (hasCursor) {
            var sceneAfterX = screenToSceneX(cursorX);
            var sceneAfterY = screenToSceneY(cursorY);
            viewBridge.pan_by(sceneBeforeX - sceneAfterX, sceneBeforeY - sceneAfterY);
        }
        return true;
    }

    function sceneToScreenX(sceneX) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return root.width * 0.5 + (sceneX - (viewBridge ? viewBridge.center_x : 0.0)) * zoom;
    }

    function sceneToScreenY(sceneY) {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return root.height * 0.5 + (sceneY - (viewBridge ? viewBridge.center_y : 0.0)) * zoom;
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

    function _portDataType(nodeId, portKey) {
        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (!node || node.node_id !== nodeId)
                continue;
            var ports = node.ports || [];
            for (var j = 0; j < ports.length; j++) {
                var port = ports[j];
                if (port && port.key === portKey)
                    return port.data_type || "any";
            }
            return "any";
        }
        return "any";
    }

    function _arePortKindsCompatible(sourceKind, targetKind) {
        if (!sceneBridge)
            return false;
        return sceneBridge.are_port_kinds_compatible(String(sourceKind || ""), String(targetKind || ""));
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
        var sourceType = _portDataType(sourceDrag.node_id, sourceDrag.port_key);
        var candidateType = _portDataType(candidate.node_id, candidate.port_key);
        if (!_areDataTypesCompatible(sourceType, candidateType))
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

    function _nearestDropCandidateForWireDrag(screenX, screenY, sourceDrag, thresholdOverride) {
        if (!sourceDrag)
            return null;

        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
        var threshold = Number(thresholdOverride);
        if (!(threshold > 0.0))
            threshold = 14.0;
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
                var dx = screenX - sceneToScreenX(point.x);
                var dy = screenY - sceneToScreenY(point.y);
                var distance = Math.sqrt(dx * dx + dy * dy);
                if (distance > threshold || distance >= bestDistance)
                    continue;
                var candidate = {
                    "node_id": node.node_id,
                    "port_key": port.key,
                    "direction": port.direction,
                    "scene_x": point.x,
                    "scene_y": point.y,
                    "valid_drop": false
                };
                candidate.valid_drop = _isDropAllowed(sourceDrag, candidate);
                if (!candidate.valid_drop)
                    continue;
                bestDistance = distance;
                best = candidate;
            }
        }
        return best;
    }

    function _areDataTypesCompatible(sourceType, targetType) {
        if (!sceneBridge)
            return false;
        return sceneBridge.are_data_types_compatible(String(sourceType || ""), String(targetType || ""));
    }

    function _portsCompatibleForAuto(sourcePort, targetPort) {
        if (!sourcePort || !targetPort)
            return false;
        return _arePortKindsCompatible(sourcePort.kind, targetPort.kind)
            && _areDataTypesCompatible(sourcePort.data_type, targetPort.data_type);
    }

    function _libraryPorts(payload) {
        var ports = [];
        if (!payload || !payload.ports)
            return ports;
        for (var i = 0; i < payload.ports.length; i++) {
            var sourcePort = payload.ports[i];
            if (!sourcePort)
                continue;
            ports.push(
                {
                    "key": String(sourcePort.key || ""),
                    "direction": String(sourcePort.direction || ""),
                    "kind": String(sourcePort.kind || ""),
                    "data_type": String(sourcePort.data_type || ""),
                    "exposed": sourcePort.exposed !== false
                }
            );
        }
        return ports;
    }

    function _scenePortData(nodeId, portKey) {
        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (!node || node.node_id !== nodeId)
                continue;
            var ports = node.ports || [];
            for (var j = 0; j < ports.length; j++) {
                var port = ports[j];
                if (port && port.key === portKey)
                    return port;
            }
            return null;
        }
        return null;
    }

    function _scenePortPoint(node, port, inputRow, outputRow) {
        if (!node || !port)
            return {"x": 0.0, "y": 0.0};
        if (node.collapsed) {
            return {
                "x": port.direction === "in" ? node.x : (node.x + node.width),
                "y": node.y + 18.0
            };
        }
        return {
            "x": port.direction === "in"
                ? node.x + 11.5
                : node.x + node.width - 11.5,
            "y": node.y + 36.0 + 18.0 * (port.direction === "in" ? inputRow : outputRow)
        };
    }

    function _hasCompatiblePortForTarget(targetPort, nodePorts) {
        if (!targetPort || !nodePorts || !nodePorts.length)
            return false;
        if (targetPort.direction === "in" && Number(targetPort.connection_count || 0) > 0)
            return false;

        for (var i = 0; i < nodePorts.length; i++) {
            var nodePort = nodePorts[i];
            if (!nodePort || nodePort.exposed === false)
                continue;
            if (targetPort.direction === "in") {
                if (nodePort.direction !== "out")
                    continue;
                if (_portsCompatibleForAuto(nodePort, targetPort))
                    return true;
            } else {
                if (nodePort.direction !== "in")
                    continue;
                if (_portsCompatibleForAuto(targetPort, nodePort))
                    return true;
            }
        }
        return false;
    }

    function _portDropTargetAtScreen(screenX, screenY, payload) {
        var nodePorts = _libraryPorts(payload);
        if (!nodePorts.length)
            return null;

        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
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
                var dx = screenX - sceneToScreenX(point.x);
                var dy = screenY - sceneToScreenY(point.y);
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
        if (!edgeId)
            return false;
        var edge = null;
        var edges = root.edgePayload || [];
        for (var i = 0; i < edges.length; i++) {
            if (edges[i].edge_id === edgeId) {
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
            if (!hasInputCandidate && nodePort.direction === "in" && _portsCompatibleForAuto(sourcePort, nodePort))
                hasInputCandidate = true;
            if (!hasOutputCandidate && nodePort.direction === "out" && _portsCompatibleForAuto(nodePort, targetPort))
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
        var edgeId = edgeLayer.edgeAtScreen(screenX, screenY);
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
        if (!payload)
            return {"portCount": 1, "worldWidth": 210.0, "worldHeight": 50.0};
        var ports = _libraryPorts(payload);
        var inputCount = 0;
        var outputCount = 0;
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (!port || port.exposed === false)
                continue;
            if (port.direction === "in")
                inputCount += 1;
            else if (port.direction === "out")
                outputCount += 1;
        }
        var portCount = Math.max(inputCount, outputCount, 1);
        return {
            "portCount": portCount,
            "worldWidth": 210.0,
            "worldHeight": 24.0 + portCount * 18.0 + 8.0
        };
    }

    function _previewVisiblePorts(payload, direction) {
        var source = _libraryPorts(payload);
        var output = [];
        for (var i = 0; i < source.length; i++) {
            var port = source[i];
            if (!port || port.exposed === false || port.direction !== direction)
                continue;
            output.push(port);
        }
        return output;
    }

    function previewInputPorts() {
        return _previewVisiblePorts(root.dropPreviewNodePayload, "in");
    }

    function previewOutputPorts() {
        return _previewVisiblePorts(root.dropPreviewNodePayload, "out");
    }

    function previewPortColor(kind) {
        if (kind === "exec")
            return "#67D487";
        if (kind === "completed")
            return "#E4CE7D";
        if (kind === "failed")
            return "#D94F4F";
        return "#7AA8FF";
    }

    function previewNodeScreenWidth() {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return metrics.worldWidth * zoom;
    }

    function previewNodeScreenHeight() {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return metrics.worldHeight * zoom;
    }

    function previewPortLabelsVisible() {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        return zoom >= 0.95 && root.previewNodeScreenWidth() >= 155;
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

    function isPointInCanvas(screenX, screenY) {
        return Number(screenX) >= 0
            && Number(screenY) >= 0
            && Number(screenX) <= root.width
            && Number(screenY) <= root.height;
    }

    function performLibraryDrop(screenX, screenY, payload) {
        if (!payload || !mainWindowBridge || !payload.type_id) {
            clearLibraryDropPreview();
            return;
        }
        root.forceActiveFocus();
        root._closeContextMenus();
        root.clearPendingConnection();
        var target = root._computeLibraryDropTarget(screenX, screenY, payload);
        mainWindowBridge.request_drop_node_from_library(
            String(payload.type_id || ""),
            root.screenToSceneX(screenX),
            root.screenToSceneY(screenY),
            target.mode || "",
            target.node_id || "",
            target.port_key || "",
            target.edge_id || ""
        );
        root.clearEdgeSelection();
        root.clearLibraryDropPreview();
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

    function _wireDragSourceData(state) {
        if (!state)
            return null;
        return {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "source_direction": state.source_direction,
            "start_x": state.start_x,
            "start_y": state.start_y,
            "cursor_x": state.cursor_x,
            "cursor_y": state.cursor_y
        };
    }

    function wireDragSourcePort() {
        var state = root.wireDragState;
        if (!state || !state.active)
            return null;
        return {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "direction": state.source_direction
        };
    }

    function wireDragPreviewConnection() {
        var state = root.wireDragState;
        if (!state || !state.active)
            state = null;
        if (state) {
            var target = root.wireDropCandidate;
            var endX = target ? target.scene_x : state.cursor_x;
            var endY = target ? target.scene_y : state.cursor_y;
            return {
                "source_direction": state.source_direction,
                "start_x": state.start_x,
                "start_y": state.start_y,
                "target_x": endX,
                "target_y": endY,
                "valid_drop": !!target
            };
        }

        var pending = root.pendingConnectionPort;
        var hovered = root.hoveredPort;
        if (!pending || !hovered)
            return null;
        if (_samePort(pending, hovered))
            return null;
        var pendingSource = {
            "node_id": pending.node_id,
            "port_key": pending.port_key,
            "source_direction": pending.direction,
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "cursor_x": hovered.scene_x,
            "cursor_y": hovered.scene_y
        };
        var pendingCandidate = {
            "node_id": hovered.node_id,
            "port_key": hovered.port_key,
            "direction": hovered.direction,
            "scene_x": hovered.scene_x,
            "scene_y": hovered.scene_y,
            "valid_drop": _isDropAllowed(pendingSource, hovered)
        };
        return {
            "source_direction": pending.direction,
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "target_x": pendingCandidate.scene_x,
            "target_y": pendingCandidate.scene_y,
            "valid_drop": pendingCandidate.valid_drop
        };
    }

    function _updateWireDropCandidate(screenX, screenY, state) {
        var sourceDrag = _wireDragSourceData(state);
        var candidate = _nearestDropCandidateForWireDrag(screenX, screenY, sourceDrag);
        root.wireDropCandidate = candidate;
        root.hoveredPort = candidate ? candidate : null;
    }

    function _clearWireDragState() {
        if (!root.wireDragState && !root.wireDropCandidate)
            return;
        root.wireDragState = null;
        root.wireDropCandidate = null;
        root.hoveredPort = root.pendingConnectionPort ? root.pendingConnectionPort : null;
        edgeLayer.requestRedraw();
    }

    function beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) {
        root.forceActiveFocus();
        root._closeContextMenus();
        root.wireDropCandidate = null;
        root.wireDragState = {
            "node_id": nodeId,
            "port_key": portKey,
            "source_direction": direction,
            "start_x": sceneX,
            "start_y": sceneY,
            "cursor_x": sceneX,
            "cursor_y": sceneY,
            "press_screen_x": Number(screenX),
            "press_screen_y": Number(screenY),
            "active": false
        };
    }

    function updatePortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {
        var state = root.wireDragState;
        if (!state)
            return;
        if (state.node_id !== nodeId || state.port_key !== portKey || state.source_direction !== direction)
            return;
        var cursorSceneX = root.screenToSceneX(screenX);
        var cursorSceneY = root.screenToSceneY(screenY);
        var movedEnough = Boolean(dragActive)
            || Math.abs(Number(screenX) - Number(state.press_screen_x)) >= root.wireDragThreshold
            || Math.abs(Number(screenY) - Number(state.press_screen_y)) >= root.wireDragThreshold;
        var becameActive = movedEnough && !state.active;
        var next = {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "source_direction": state.source_direction,
            "start_x": state.start_x,
            "start_y": state.start_y,
            "cursor_x": cursorSceneX,
            "cursor_y": cursorSceneY,
            "press_screen_x": state.press_screen_x,
            "press_screen_y": state.press_screen_y,
            "active": state.active || movedEnough
        };
        root.wireDragState = next;
        if (!next.active)
            return;
        if (becameActive)
            root.clearPendingConnection();
        root._updateWireDropCandidate(screenX, screenY, next);
        edgeLayer.requestRedraw();
    }

    function finishPortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {
        var state = root.wireDragState;
        if (!state)
            return;
        if (state.node_id !== nodeId || state.port_key !== portKey || state.source_direction !== direction) {
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
            "cursor_x": root.screenToSceneX(screenX),
            "cursor_y": root.screenToSceneY(screenY),
            "press_screen_x": state.press_screen_x,
            "press_screen_y": state.press_screen_y,
            "active": true
        };
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
        if (candidate && candidate.valid_drop && mainWindowBridge) {
            mainWindowBridge.request_connect_ports(
                finalState.node_id,
                finalState.port_key,
                candidate.node_id,
                candidate.port_key
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
            var created = mainWindowBridge.request_connect_ports(
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
        previewEdgeId: root.dropPreviewEdgeId
        dragConnection: root.wireDragPreviewConnection()
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

    Rectangle {
        id: dragNodePreview
        visible: !!root.dropPreviewNodePayload
        z: 34
        x: root.dropPreviewScreenX
        y: root.dropPreviewScreenY
        width: root.previewNodeScreenWidth()
        height: root.previewNodeScreenHeight()
        radius: Math.max(4, 6 * (viewBridge ? viewBridge.zoom_value : 1.0))
        color: "#AA2A3340"
        border.width: 1
        border.color: "#80CFF5"
        clip: true

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: Math.max(8, 4 * (viewBridge ? viewBridge.zoom_value : 1.0))
            color: "#66A4D8"
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: Math.max(8, 4 * (viewBridge ? viewBridge.zoom_value : 1.0))
            height: Math.max(14, 24 * (viewBridge ? viewBridge.zoom_value : 1.0))
            color: "#7A2F3948"
        }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: Math.max(4, 10 * (viewBridge ? viewBridge.zoom_value : 1.0))
            anchors.right: parent.right
            anchors.rightMargin: Math.max(4, 8 * (viewBridge ? viewBridge.zoom_value : 1.0))
            anchors.top: parent.top
            anchors.topMargin: Math.max(10, 8 * (viewBridge ? viewBridge.zoom_value : 1.0))
            text: root.dropPreviewNodePayload
                ? String(root.dropPreviewNodePayload.display_name || root.dropPreviewNodePayload.type_id || "")
                : ""
            color: "#EAF3FF"
            font.bold: true
            font.pixelSize: Math.max(10, Math.min(16, 12 * (viewBridge ? viewBridge.zoom_value : 1.0)))
            elide: Text.ElideRight
        }

        Item {
            id: previewPortsLayer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: Math.max(10, 30 * (viewBridge ? viewBridge.zoom_value : 1.0))
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Math.max(2, 6 * (viewBridge ? viewBridge.zoom_value : 1.0))

            Column {
                id: previewInputColumn
                anchors.left: parent.left
                anchors.leftMargin: Math.max(4, 8 * (viewBridge ? viewBridge.zoom_value : 1.0))
                anchors.top: parent.top
                spacing: 0

                Repeater {
                    model: root.previewInputPorts()
                    delegate: Item {
                        width: Math.max(40, previewPortsLayer.width * 0.45)
                        height: Math.max(8, 18 * (viewBridge ? viewBridge.zoom_value : 1.0))

                        Rectangle {
                            anchors.left: parent.left
                            anchors.leftMargin: 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(5, Math.min(10, 8 * (viewBridge ? viewBridge.zoom_value : 1.0)))
                            height: width
                            radius: width * 0.5
                            color: "transparent"
                            border.width: 1
                            border.color: root.previewPortColor(modelData.kind)
                        }

                        Text {
                            visible: root.previewPortLabelsVisible()
                            anchors.left: parent.left
                            anchors.leftMargin: Math.max(7, 12 * (viewBridge ? viewBridge.zoom_value : 1.0))
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: String(modelData.key || "")
                            color: "#C6D1E1"
                            font.pixelSize: Math.max(7, Math.min(11, 10 * (viewBridge ? viewBridge.zoom_value : 1.0)))
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Column {
                id: previewOutputColumn
                anchors.right: parent.right
                anchors.rightMargin: Math.max(4, 8 * (viewBridge ? viewBridge.zoom_value : 1.0))
                anchors.top: parent.top
                spacing: 0

                Repeater {
                    model: root.previewOutputPorts()
                    delegate: Item {
                        width: Math.max(40, previewPortsLayer.width * 0.45)
                        height: Math.max(8, 18 * (viewBridge ? viewBridge.zoom_value : 1.0))

                        Rectangle {
                            anchors.right: parent.right
                            anchors.rightMargin: 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(5, Math.min(10, 8 * (viewBridge ? viewBridge.zoom_value : 1.0)))
                            height: width
                            radius: width * 0.5
                            color: "transparent"
                            border.width: 1
                            border.color: root.previewPortColor(modelData.kind)
                        }

                        Text {
                            visible: root.previewPortLabelsVisible()
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.rightMargin: Math.max(7, 12 * (viewBridge ? viewBridge.zoom_value : 1.0))
                            anchors.verticalCenter: parent.verticalCenter
                            text: String(modelData.key || "")
                            color: "#C6D1E1"
                            font.pixelSize: Math.max(7, Math.min(11, 10 * (viewBridge ? viewBridge.zoom_value : 1.0)))
                            horizontalAlignment: Text.AlignRight
                            elide: Text.ElideLeft
                        }
                    }
                }
            }
        }
    }

    Item {
        id: world
        width: root.worldSize
        height: root.worldSize
        transformOrigin: Item.TopLeft
        scale: viewBridge ? viewBridge.zoom_value : 1.0
        x: root.width * 0.5 - ((viewBridge ? viewBridge.center_x : 0) + root.worldOffset) * scale
        y: root.height * 0.5 - ((viewBridge ? viewBridge.center_y : 0) + root.worldOffset) * scale

        Repeater {
            model: sceneBridge ? sceneBridge.nodes_model : []
            delegate: GraphComponents.NodeCard {
                id: nodeCard
                nodeData: modelData
                worldOffset: root.worldOffset
                canvasItem: root
                hoveredPort: root.hoveredPort
                previewPort: root.dropPreviewPort
                pendingPort: root.pendingConnectionPort
                dragSourcePort: root.wireDragSourcePort()

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
                onPortDragStarted: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) {
                    root.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);
                }
                onPortDragMoved: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive) {
                    root.updatePortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive);
                }
                onPortDragFinished: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive) {
                    root.finishPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive);
                }
                onPortDragCanceled: function(_nodeId, _portKey, _direction) {
                    root.cancelWireDrag();
                }
                onPortHoverChanged: function(nodeId, portKey, direction, sceneX, sceneY, hovered) {
                    if (root.wireDragState && root.wireDragState.active)
                        return;
                    if (hovered) {
                        root.hoveredPort = {
                            "node_id": nodeId,
                            "port_key": portKey,
                            "direction": direction,
                            "scene_x": sceneX,
                            "scene_y": sceneY,
                            "valid_drop": false
                        };
                        edgeLayer.requestRedraw();
                    } else if (
                        root.hoveredPort
                        && root.hoveredPort.node_id === nodeId
                        && root.hoveredPort.port_key === portKey
                        && root.hoveredPort.direction === direction
                    ) {
                        root.hoveredPort = null;
                        edgeLayer.requestRedraw();
                    }
                }
            }
        }
    }

    Rectangle {
        id: minimapOverlay
        z: 140
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 12
        anchors.bottomMargin: 12
        width: root.minimapExpanded ? root.minimapExpandedWidth : root.minimapCollapsedWidth
        height: root.minimapExpanded ? root.minimapExpandedHeight : root.minimapCollapsedHeight
        radius: 4
        color: "#A21C2028"
        border.width: 1
        border.color: "#4B5567"
        clip: true

        Text {
            visible: root.minimapExpanded
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.top: parent.top
            anchors.topMargin: 5
            text: "MINIMAP"
            color: "#AAB4C9"
            font.pixelSize: 9
            font.bold: true
        }

        Rectangle {
            id: minimapToggle
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 4
            anchors.rightMargin: 4
            width: 22
            height: 18
            radius: 3
            color: minimapToggleMouse.pressed ? "#4A5365" : (minimapToggleMouse.containsMouse ? "#3F4857" : "#37404F")
            border.width: 1
            border.color: "#5B667A"

            Text {
                anchors.centerIn: parent
                text: root.minimapExpanded ? "-" : "+"
                color: "#E2E9F7"
                font.pixelSize: 12
                font.bold: true
            }

            MouseArea {
                id: minimapToggleMouse
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                hoverEnabled: true
                preventStealing: true
                onClicked: {
                    root.forceActiveFocus();
                    root.toggleMinimapExpanded();
                    mouse.accepted = true;
                }
            }
        }

        Item {
            id: minimapViewport
            visible: root.minimapExpanded
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: 4
            anchors.rightMargin: 4
            anchors.topMargin: 24
            anchors.bottomMargin: 4
            property real contentPadding: 7

            function _normalizeRectPayload(payload, fallbackX, fallbackY, fallbackWidth, fallbackHeight) {
                var x = Number(payload && payload.x);
                var y = Number(payload && payload.y);
                var width = Number(payload && payload.width);
                var height = Number(payload && payload.height);
                if (!isFinite(x))
                    x = Number(fallbackX);
                if (!isFinite(y))
                    y = Number(fallbackY);
                if (!(width > 0.0))
                    width = Number(fallbackWidth);
                if (!(height > 0.0))
                    height = Number(fallbackHeight);
                return {
                    "x": x,
                    "y": y,
                    "width": Math.max(1.0, width),
                    "height": Math.max(1.0, height)
                };
            }

            function sceneRect() {
                var payload = sceneBridge ? sceneBridge.workspace_scene_bounds_payload : null;
                return _normalizeRectPayload(payload, -1600.0, -900.0, 3200.0, 1800.0);
            }

            function visibleRect() {
                var scene = sceneRect();
                var payload = viewBridge ? viewBridge.visible_scene_rect_payload : null;
                return _normalizeRectPayload(payload, scene.x, scene.y, scene.width, scene.height);
            }

            function scaleValue() {
                var scene = sceneRect();
                var availableWidth = Math.max(1.0, width - contentPadding * 2.0);
                var availableHeight = Math.max(1.0, height - contentPadding * 2.0);
                return Math.min(availableWidth / scene.width, availableHeight / scene.height);
            }

            function usedWidth() {
                return sceneRect().width * scaleValue();
            }

            function usedHeight() {
                return sceneRect().height * scaleValue();
            }

            function contentOffsetX() {
                return (width - usedWidth()) * 0.5;
            }

            function contentOffsetY() {
                return (height - usedHeight()) * 0.5;
            }

            function sceneToMinimapX(sceneX) {
                var scene = sceneRect();
                return contentOffsetX() + (Number(sceneX) - scene.x) * scaleValue();
            }

            function sceneToMinimapY(sceneY) {
                var scene = sceneRect();
                return contentOffsetY() + (Number(sceneY) - scene.y) * scaleValue();
            }

            function minimapToSceneX(minimapX) {
                var scene = sceneRect();
                return scene.x + (Number(minimapX) - contentOffsetX()) / Math.max(1e-6, scaleValue());
            }

            function minimapToSceneY(minimapY) {
                var scene = sceneRect();
                return scene.y + (Number(minimapY) - contentOffsetY()) / Math.max(1e-6, scaleValue());
            }

            Rectangle {
                anchors.fill: parent
                radius: 2
                color: "#AA171A22"
                border.width: 1
                border.color: "#41495B"
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                preventStealing: true
                onPressed: {
                    root.forceActiveFocus();
                    root._closeContextMenus();
                }
                onClicked: {
                    if (!viewBridge)
                        return;
                    viewBridge.center_on_scene_point(
                        minimapViewport.minimapToSceneX(mouse.x),
                        minimapViewport.minimapToSceneY(mouse.y)
                    );
                    mouse.accepted = true;
                }
            }

            Repeater {
                model: sceneBridge ? sceneBridge.minimap_nodes_model : []
                delegate: Rectangle {
                    x: minimapViewport.sceneToMinimapX(modelData.x)
                    y: minimapViewport.sceneToMinimapY(modelData.y)
                    width: Math.max(2, modelData.width * minimapViewport.scaleValue())
                    height: Math.max(2, modelData.height * minimapViewport.scaleValue())
                    color: modelData.selected ? "#A4457FC6" : "#6C5A6273"
                    border.width: modelData.selected ? 1.2 : 1
                    border.color: modelData.selected ? "#D0EAFF" : "#909DB4"
                    radius: 1
                }
            }

            Rectangle {
                id: minimapViewportRect
                property var visibleRectPayload: minimapViewport.visibleRect()
                property real contentWidth: minimapViewport.usedWidth()
                property real contentHeight: minimapViewport.usedHeight()
                width: Math.max(10, Math.min(contentWidth, visibleRectPayload.width * minimapViewport.scaleValue()))
                height: Math.max(10, Math.min(contentHeight, visibleRectPayload.height * minimapViewport.scaleValue()))
                x: {
                    var raw = minimapViewport.sceneToMinimapX(visibleRectPayload.x);
                    var minX = minimapViewport.contentOffsetX();
                    return Math.max(minX, Math.min(raw, minX + contentWidth - width));
                }
                y: {
                    var raw = minimapViewport.sceneToMinimapY(visibleRectPayload.y);
                    var minY = minimapViewport.contentOffsetY();
                    return Math.max(minY, Math.min(raw, minY + contentHeight - height));
                }
                color: "#2A7EC7FF"
                border.width: 1
                border.color: "#E0F3FF"
                radius: 2

                MouseArea {
                    id: minimapViewportDragArea
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    hoverEnabled: true
                    cursorShape: Qt.SizeAllCursor
                    preventStealing: true
                    onPressed: {
                        root.forceActiveFocus();
                        root._closeContextMenus();
                        if (viewBridge) {
                            viewBridge.center_on_scene_point(
                                minimapViewport.minimapToSceneX(minimapViewportRect.x + mouse.x),
                                minimapViewport.minimapToSceneY(minimapViewportRect.y + mouse.y)
                            );
                        }
                        mouse.accepted = true;
                    }
                    onPositionChanged: {
                        if (!pressed || !viewBridge)
                            return;
                        viewBridge.center_on_scene_point(
                            minimapViewport.minimapToSceneX(minimapViewportRect.x + mouse.x),
                            minimapViewport.minimapToSceneY(minimapViewportRect.y + mouse.y)
                        );
                        mouse.accepted = true;
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

        onWheel: function(wheel) {
            if (root.applyWheelZoom(wheel))
                wheel.accepted = true;
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
                    mainWindowBridge.request_remove_edge(root.edgeContextEdgeId);
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
                    mainWindowBridge.request_rename_node(root.nodeContextNodeId);
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
                    mainWindowBridge.request_remove_node(root.nodeContextNodeId);
                    root.clearEdgeSelection();
                    root._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }
    }

    Keys.onDeletePressed: function(event) {
        if (mainWindowBridge)
            mainWindowBridge.request_delete_selected_graph_items(root.selectedEdgeIds);
        root.selectedEdgeIds = [];
        root.clearPendingConnection();
        root._closeContextMenus();
        event.accepted = true;
    }

    Keys.onEscapePressed: function(event) {
        var handled = false;
        if (root.cancelWireDrag())
            handled = true;
        if (root.pendingConnectionPort) {
            root.clearPendingConnection();
            handled = true;
        }
        if (root.edgeContextVisible || root.nodeContextVisible) {
            root._closeContextMenus();
            handled = true;
        }
        if (handled)
            event.accepted = true;
    }

    Connections {
        target: sceneBridge
        function onEdges_changed() {
            root.liveDragOffsets = ({});
            root._clearWireDragState();
            root._syncEdgePayload();
        }
        function onNodes_changed() {
            root.liveDragOffsets = ({});
            root._clearWireDragState();
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
        root.wireDragState = null;
        root.wireDropCandidate = null;
        root.clearLibraryDropPreview();
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
