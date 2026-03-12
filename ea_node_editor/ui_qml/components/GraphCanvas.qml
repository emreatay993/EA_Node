import QtQuick 2.15
import "graph" as GraphComponents
import "graph_canvas" as GraphCanvasComponents
import "graph_canvas/GraphCanvasLogic.js" as GraphCanvasLogic

Item {
    id: root
    objectName: "graphCanvas"
    property var mainWindowBridge: null
    property var sceneBridge: null
    property var viewBridge: null
    property var overlayHostItem: null
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
    Keys.forwardTo: [inputLayers]
    clip: true

    function toggleMinimapExpanded() {
        root.minimapExpanded = !root.minimapExpanded;
    }

    function screenToSceneX(screenX) {
        return GraphCanvasLogic.screenToSceneX(
            screenX,
            (viewBridge ? viewBridge.center_x : 0.0),
            root.width,
            (viewBridge ? viewBridge.zoom_value : 1.0)
        );
    }

    function screenToSceneY(screenY) {
        return GraphCanvasLogic.screenToSceneY(
            screenY,
            (viewBridge ? viewBridge.center_y : 0.0),
            root.height,
            (viewBridge ? viewBridge.zoom_value : 1.0)
        );
    }

    function _wheelDeltaY(eventObj) {
        return GraphCanvasLogic.wheelDeltaY(eventObj);
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
        return GraphCanvasLogic.sceneToScreenX(
            sceneX,
            (viewBridge ? viewBridge.center_x : 0.0),
            root.width,
            (viewBridge ? viewBridge.zoom_value : 1.0)
        );
    }

    function sceneToScreenY(sceneY) {
        return GraphCanvasLogic.sceneToScreenY(
            sceneY,
            (viewBridge ? viewBridge.center_y : 0.0),
            root.height,
            (viewBridge ? viewBridge.zoom_value : 1.0)
        );
    }

    function snapToGridEnabled() {
        return mainWindowBridge ? Boolean(mainWindowBridge.snap_to_grid_enabled) : false;
    }

    function snapGridSize() {
        return GraphCanvasLogic.normalizeSnapGridSize(mainWindowBridge ? mainWindowBridge.snap_grid_size : 20.0);
    }

    function snapToGridValue(value) {
        return GraphCanvasLogic.snapToGridValue(value, root.snapGridSize());
    }

    function snappedDragDelta(nodeId, rawDx, rawDy) {
        return GraphCanvasLogic.snappedDragDelta(
            rawDx,
            rawDy,
            root.snapToGridEnabled(),
            root._sceneNodePayload(nodeId),
            root.snapGridSize()
        );
    }

    function _normalizeEdgeIds(values) {
        return GraphCanvasLogic.normalizeEdgeIds(values);
    }

    function _availableEdgeIdSet() {
        return GraphCanvasLogic.availableEdgeIdSet(root.edgePayload);
    }

    function pruneSelectedEdges() {
        root.selectedEdgeIds = GraphCanvasLogic.pruneSelectedEdgeIds(root.selectedEdgeIds, _availableEdgeIdSet());
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

    function _sceneNodePayload(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return null;
        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (node && node.node_id === normalized)
                return node;
        }
        return null;
    }

    function _nodeCanEnterScope(nodeId) {
        var payload = _sceneNodePayload(nodeId);
        if (!payload)
            return false;
        if (payload.can_enter_scope !== undefined)
            return Boolean(payload.can_enter_scope);
        return String(payload.type_id || "") === "core.subnode";
    }

    function requestOpenSubnodeScope(nodeId) {
        if (!mainWindowBridge)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var opened = mainWindowBridge.request_open_subnode_scope(normalized);
        if (!opened)
            return false;
        root.clearEdgeSelection();
        root.clearPendingConnection();
        root._closeContextMenus();
        return true;
    }

    function selectedNodeIds() {
        var nodes = sceneBridge ? sceneBridge.nodes_model : [];
        var selected = [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (node && node.selected)
                selected.push(node.node_id);
        }
        return selected;
    }

    function dragNodeIdsForAnchor(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return [];
        var selected = root.selectedNodeIds();
        if (selected.length > 1 && selected.indexOf(normalized) >= 0) {
            var ordered = [normalized];
            for (var i = 0; i < selected.length; i++) {
                if (selected[i] !== normalized)
                    ordered.push(selected[i]);
            }
            return ordered;
        }
        return [normalized];
    }

    function setLiveDragOffsets(nodeIds, dx, dy) {
        var next = {};
        if (Math.abs(dx) >= 0.01 || Math.abs(dy) >= 0.01) {
            var source = nodeIds || [];
            for (var i = 0; i < source.length; i++) {
                var nodeId = String(source[i] || "").trim();
                if (!nodeId)
                    continue;
                next[nodeId] = {"dx": dx, "dy": dy};
            }
        }
        root.liveDragOffsets = next;
        edgeLayer.requestRedraw();
    }

    function clearLiveDragOffsets() {
        if (!root.liveDragOffsets || Object.keys(root.liveDragOffsets).length === 0)
            return;
        root.liveDragOffsets = ({});
        edgeLayer.requestRedraw();
    }

    function liveDragDxForNode(nodeId) {
        var entry = root.liveDragOffsets ? root.liveDragOffsets[String(nodeId || "").trim()] : null;
        var value = entry ? Number(entry.dx) : 0.0;
        return isFinite(value) ? value : 0.0;
    }

    function liveDragDyForNode(nodeId) {
        var entry = root.liveDragOffsets ? root.liveDragOffsets[String(nodeId || "").trim()] : null;
        var value = entry ? Number(entry.dy) : 0.0;
        return isFinite(value) ? value : 0.0;
    }

    function _dropTargetInput(sourceDrag, candidate) {
        return GraphCanvasLogic.dropTargetInput(sourceDrag, candidate);
    }

    function _isExactDuplicate(sourceDrag, candidate, edge) {
        return GraphCanvasLogic.isExactDuplicate(sourceDrag, candidate, edge);
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
        var sourceKind = _portKind(sourceDrag.node_id, sourceDrag.port_key);
        var candidateKind = _portKind(candidate.node_id, candidate.port_key);
        var kindsCompatible = _arePortKindsCompatible(sourceKind, candidateKind);
        var sourceType = _portDataType(sourceDrag.node_id, sourceDrag.port_key);
        var candidateType = _portDataType(candidate.node_id, candidate.port_key);
        var typesCompatible = _areDataTypesCompatible(sourceType, candidateType);
        return GraphCanvasLogic.isDropAllowedWithCompatibility(
            sourceDrag,
            candidate,
            root.edgePayload,
            kindsCompatible,
            typesCompatible
        );
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
        return GraphCanvasLogic.portsCompatibleForAuto(
            sourcePort,
            targetPort,
            _arePortKindsCompatible(sourcePort ? sourcePort.kind : "", targetPort ? targetPort.kind : ""),
            _areDataTypesCompatible(sourcePort ? sourcePort.data_type : "", targetPort ? targetPort.data_type : "")
        );
    }

    function _libraryPorts(payload) {
        return GraphCanvasLogic.libraryPorts(payload);
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
        return GraphCanvasLogic.scenePortPoint(node, port, inputRow, outputRow);
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
        return GraphCanvasLogic.previewNodeMetrics(payload);
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
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return GraphCanvasLogic.previewNodeScreenExtent(metrics.worldWidth, zoom);
    }

    function previewNodeScreenHeight() {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return GraphCanvasLogic.previewNodeScreenExtent(metrics.worldHeight, zoom);
    }

    function previewPortLabelsVisible() {
        var zoom = viewBridge ? viewBridge.zoom_value : 1.0;
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

    function isPointInCanvas(screenX, screenY) {
        return GraphCanvasLogic.pointInCanvas(screenX, screenY, root.width, root.height);
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
        } else if (mainWindowBridge) {
            var overlayPoint = root.mapToItem(
                root.overlayHostItem ? root.overlayHostItem : root,
                Number(screenX),
                Number(screenY)
            );
            mainWindowBridge.request_open_connection_quick_insert(
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
        return GraphCanvasLogic.clampMenuPosition(
            x,
            y,
            menuWidth,
            menuHeight,
            root.width,
            root.height,
            4
        );
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
        var menuHeight = _nodeCanEnterScope(nodeId) ? 144 : 72;
        var position = _clampMenuPosition(x, y, 170, menuHeight);
        _closeContextMenus();
        root.nodeContextNodeId = nodeId;
        root.contextMenuX = position.x;
        root.contextMenuY = position.y;
        root.nodeContextVisible = true;
    }

    GraphCanvasComponents.GraphCanvasBackground {
        id: backgroundLayer
        anchors.fill: parent
        viewBridge: root.viewBridge
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

    GraphCanvasComponents.GraphCanvasDropPreview {
        id: dragNodePreview
        canvasItem: root
        viewBridge: root.viewBridge
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
                liveDragDx: root.liveDragDxForNode(modelData.node_id)
                liveDragDy: root.liveDragDyForNode(modelData.node_id)

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
                onNodeOpenRequested: function(nodeId) {
                    root.requestOpenSubnodeScope(nodeId);
                }
                onDragOffsetChanged: function(nodeId, dx, dy) {
                    var snappedDelta = root.snappedDragDelta(nodeId, dx, dy);
                    root.setLiveDragOffsets(
                        root.dragNodeIdsForAnchor(nodeId),
                        snappedDelta.dx,
                        snappedDelta.dy
                    );
                }
                onDragFinished: function(nodeId, finalX, finalY, _moved) {
                    var dragNodeIds = root.dragNodeIdsForAnchor(nodeId);
                    var anchorPayload = root._sceneNodePayload(nodeId);
                    var anchorX = anchorPayload ? Number(anchorPayload.x) : Number(finalX);
                    var anchorY = anchorPayload ? Number(anchorPayload.y) : Number(finalY);
                    if (!isFinite(anchorX))
                        anchorX = Number(finalX);
                    if (!isFinite(anchorY))
                        anchorY = Number(finalY);
                    var rawDeltaX = Number(finalX) - anchorX;
                    var rawDeltaY = Number(finalY) - anchorY;
                    var snappedDelta = root.snappedDragDelta(nodeId, rawDeltaX, rawDeltaY);
                    var deltaX = Number(snappedDelta.dx);
                    var deltaY = Number(snappedDelta.dy);
                    if (!isFinite(deltaX))
                        deltaX = 0.0;
                    if (!isFinite(deltaY))
                        deltaY = 0.0;
                    var finalSnappedX = anchorX + deltaX;
                    var finalSnappedY = anchorY + deltaY;
                    var movedByCommit = Math.abs(deltaX) >= 0.01 || Math.abs(deltaY) >= 0.01;

                    root.clearLiveDragOffsets();
                    if (!sceneBridge)
                        return;
                    if (dragNodeIds.length > 1) {
                        movedByCommit = sceneBridge.move_nodes_by_delta(dragNodeIds, deltaX, deltaY);
                        if (movedByCommit)
                            root.clearEdgeSelection();
                        return;
                    }

                    sceneBridge.move_node(nodeId, finalSnappedX, finalSnappedY);
                    if (movedByCommit) {
                        root.clearEdgeSelection();
                        sceneBridge.select_node(nodeId, false);
                    }
                }
                onDragCanceled: function(_nodeId) {
                    root.clearLiveDragOffsets();
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
                onInlinePropertyCommitted: function(nodeId, key, value) {
                    root.forceActiveFocus();
                    root._closeContextMenus();
                    root.clearPendingConnection();
                    root.clearEdgeSelection();
                    if (sceneBridge)
                        sceneBridge.select_node(nodeId, false);
                    if (mainWindowBridge)
                        mainWindowBridge.set_selected_node_property(key, value);
                }
            }
        }
    }

    GraphCanvasComponents.GraphCanvasMinimapOverlay {
        id: minimapOverlay
        canvasItem: root
        sceneBridge: root.sceneBridge
        viewBridge: root.viewBridge
    }

    GraphCanvasComponents.GraphCanvasInputLayers {
        id: inputLayers
        canvasItem: root
        mainWindowBridge: root.mainWindowBridge
        sceneBridge: root.sceneBridge
        viewBridge: root.viewBridge
    }

    GraphCanvasComponents.GraphCanvasContextMenus {
        id: contextMenus
        canvasItem: root
        mainWindowBridge: root.mainWindowBridge
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
            backgroundLayer.requestGridRedraw();
            edgeLayer.requestRedraw();
        }
        function onCenter_changed() {
            backgroundLayer.requestGridRedraw();
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
