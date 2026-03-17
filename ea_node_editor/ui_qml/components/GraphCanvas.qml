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
    readonly property var canvasBridgeRef: (typeof graphCanvasBridge !== "undefined" && graphCanvasBridge) ? graphCanvasBridge : null
    property var overlayHostItem: null
    property var edgePayload: []
    property var liveDragOffsets: ({})
    property var liveResizeDimensions: ({})
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
    property bool interactionActive: false
    property bool minimapExpanded: root.canvasBridgeRef ? Boolean(root.canvasBridgeRef.graphics_minimap_expanded) : (mainWindowBridge ? Boolean(mainWindowBridge.graphics_minimap_expanded) : true)
    readonly property bool showGrid: root.canvasBridgeRef ? Boolean(root.canvasBridgeRef.graphics_show_grid) : (mainWindowBridge ? Boolean(mainWindowBridge.graphics_show_grid) : true)
    readonly property bool minimapVisible: root.canvasBridgeRef ? Boolean(root.canvasBridgeRef.graphics_show_minimap) : (mainWindowBridge ? Boolean(mainWindowBridge.graphics_show_minimap) : true)
    readonly property bool nodeShadowEnabled: root.canvasBridgeRef ? Boolean(root.canvasBridgeRef.graphics_node_shadow) : (mainWindowBridge ? Boolean(mainWindowBridge.graphics_node_shadow) : true)
    readonly property int shadowStrength: root.canvasBridgeRef ? root.canvasBridgeRef.graphics_shadow_strength : (mainWindowBridge ? mainWindowBridge.graphics_shadow_strength : 70)
    readonly property int shadowSoftness: root.canvasBridgeRef ? root.canvasBridgeRef.graphics_shadow_softness : (mainWindowBridge ? mainWindowBridge.graphics_shadow_softness : 50)
    readonly property int shadowOffset: root.canvasBridgeRef ? root.canvasBridgeRef.graphics_shadow_offset : (mainWindowBridge ? mainWindowBridge.graphics_shadow_offset : 4)
    readonly property bool highQualityRendering: !root.interactionActive
    readonly property int interactionIdleDelayMs: 150
    readonly property real wireDragThreshold: 2
    readonly property real worldSize: 12000
    readonly property real worldOffset: worldSize / 2
    readonly property real minimapExpandedWidth: 238
    readonly property real minimapExpandedHeight: 162
    readonly property real minimapCollapsedWidth: 28
    readonly property real minimapCollapsedHeight: 28
    focus: true
    activeFocusOnTab: true
    Keys.forwardTo: [inputLayers]
    clip: true

    function toggleMinimapExpanded() {
        var nextExpanded = !root.minimapExpanded;
        var bridge = root.canvasBridgeRef || mainWindowBridge;
        if (bridge && bridge.set_graphics_minimap_expanded) {
            bridge.set_graphics_minimap_expanded(nextExpanded);
            return;
        }
        root.minimapExpanded = nextExpanded;
    }

    function beginViewportInteraction() {
        if (!root.interactionActive)
            root.interactionActive = true;
        interactionIdleTimer.stop();
    }

    function finishViewportInteractionSoon() {
        if (!root.interactionActive) {
            interactionIdleTimer.stop();
            return;
        }
        interactionIdleTimer.restart();
    }

    function noteViewportInteraction() {
        root.beginViewportInteraction();
        interactionIdleTimer.restart();
    }

    function screenToSceneX(screenX) {
        var view = root.canvasBridgeRef || viewBridge;
        return GraphCanvasLogic.screenToSceneX(
            screenX,
            (view ? view.center_x : 0.0),
            root.width,
            (view ? view.zoom_value : 1.0)
        );
    }

    function screenToSceneY(screenY) {
        var view = root.canvasBridgeRef || viewBridge;
        return GraphCanvasLogic.screenToSceneY(
            screenY,
            (view ? view.center_y : 0.0),
            root.height,
            (view ? view.zoom_value : 1.0)
        );
    }

    function _wheelDeltaY(eventObj) {
        return GraphCanvasLogic.wheelDeltaY(eventObj);
    }

    function applyWheelZoom(eventObj) {
        var view = root.canvasBridgeRef || viewBridge;
        if (!view)
            return false;
        var deltaY = _wheelDeltaY(eventObj);
        if (Math.abs(deltaY) < 0.001)
            return false;
        root.noteViewportInteraction();

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
        if (view.adjust_zoom)
            view.adjust_zoom(factor);
        else if (viewBridge && viewBridge.adjust_zoom)
            viewBridge.adjust_zoom(factor);

        if (hasCursor) {
            var sceneAfterX = screenToSceneX(cursorX);
            var sceneAfterY = screenToSceneY(cursorY);
            if (view.pan_by)
                view.pan_by(sceneBeforeX - sceneAfterX, sceneBeforeY - sceneAfterY);
            else if (viewBridge && viewBridge.pan_by)
                viewBridge.pan_by(sceneBeforeX - sceneAfterX, sceneBeforeY - sceneAfterY);
        }
        return true;
    }

    Timer {
        id: interactionIdleTimer
        interval: root.interactionIdleDelayMs
        repeat: false
        onTriggered: root.interactionActive = false
    }

    function sceneToScreenX(sceneX) {
        var view = root.canvasBridgeRef || viewBridge;
        return GraphCanvasLogic.sceneToScreenX(
            sceneX,
            (view ? view.center_x : 0.0),
            root.width,
            (view ? view.zoom_value : 1.0)
        );
    }

    function sceneToScreenY(sceneY) {
        var view = root.canvasBridgeRef || viewBridge;
        return GraphCanvasLogic.sceneToScreenY(
            sceneY,
            (view ? view.center_y : 0.0),
            root.height,
            (view ? view.zoom_value : 1.0)
        );
    }

    function snapToGridEnabled() {
        return root.canvasBridgeRef ? Boolean(root.canvasBridgeRef.snap_to_grid_enabled) : (mainWindowBridge ? Boolean(mainWindowBridge.snap_to_grid_enabled) : false);
    }

    function snapGridSize() {
        return GraphCanvasLogic.normalizeSnapGridSize(root.canvasBridgeRef ? root.canvasBridgeRef.snap_grid_size : (mainWindowBridge ? mainWindowBridge.snap_grid_size : 20.0));
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
        var nodes = root.canvasBridgeRef ? root.canvasBridgeRef.nodes_model : (sceneBridge ? sceneBridge.nodes_model : []);
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (node && node.node_id === normalized)
                return node;
        }
        return null;
    }

    function _sceneEdgePayload(edgeId) {
        var normalized = String(edgeId || "").trim();
        if (!normalized)
            return null;
        var edges = root.edgePayload || [];
        for (var i = 0; i < edges.length; i++) {
            var edge = edges[i];
            if (edge && edge.edge_id === normalized)
                return edge;
        }
        return null;
    }

    function _nodeSupportsPassiveStyle(nodeId) {
        var payload = _sceneNodePayload(nodeId);
        if (!payload)
            return false;
        return String(payload.runtime_behavior || "").toLowerCase() === "passive";
    }

    function _edgeSupportsFlowStyle(edgeId) {
        var payload = _sceneEdgePayload(edgeId);
        if (!payload)
            return false;
        return String(payload.edge_family || "").toLowerCase() === "flow";
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
        var bridge = root.canvasBridgeRef || mainWindowBridge;
        if (!bridge || !bridge.request_open_subnode_scope)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var opened = bridge.request_open_subnode_scope(normalized);
        if (!opened)
            return false;
        root.clearEdgeSelection();
        root.clearPendingConnection();
        root._closeContextMenus();
        return true;
    }

    function prepareNodeSurfaceControlInteraction(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        root._closeContextMenus();
        root.cancelWireDrag();
        root.clearPendingConnection();
        root.clearEdgeSelection();
        var bridge = root.canvasBridgeRef || sceneBridge;
        if (bridge && bridge.select_node)
            bridge.select_node(normalized, false);
        return true;
    }

    function commitNodeSurfaceProperty(nodeId, key, value) {
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedKey = String(key || "").trim();
        if (!normalizedNodeId || !normalizedKey)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        var bridge = root.canvasBridgeRef || sceneBridge;
        if (!bridge || !bridge.set_node_property)
            return false;
        bridge.set_node_property(normalizedNodeId, normalizedKey, value);
        return true;
    }

    function browseNodePropertyPath(nodeId, key, currentPath) {
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedKey = String(key || "").trim();
        var bridge = root.canvasBridgeRef || mainWindowBridge;
        if (!normalizedNodeId || !normalizedKey || !bridge || !bridge.browse_node_property_path)
            return "";
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        return String(bridge.browse_node_property_path(
            normalizedNodeId,
            normalizedKey,
            String(currentPath || "")
        ) || "");
    }

    function selectedNodeIds() {
        var nodes = root.canvasBridgeRef ? root.canvasBridgeRef.nodes_model : (sceneBridge ? sceneBridge.nodes_model : []);
        var selectedLookup = null;
        if (root.canvasBridgeRef && typeof root.canvasBridgeRef.selected_node_lookup !== "undefined")
            selectedLookup = root.canvasBridgeRef.selected_node_lookup || ({});
        else if (sceneBridge && typeof sceneBridge.selected_node_lookup !== "undefined")
            selectedLookup = sceneBridge.selected_node_lookup || ({});
        var selected = [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            var nodeId = node ? String(node.node_id || "").trim() : "";
            if (!nodeId)
                continue;
            if (selectedLookup !== null) {
                if (Boolean(selectedLookup[nodeId]))
                    selected.push(nodeId);
                continue;
            }
            if (node.selected)
                selected.push(nodeId);
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

    function setLiveResizeDimensions(nodeId, width, height, active) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return;
        var next = {};
        var source = root.liveResizeDimensions || {};
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key))
                next[key] = source[key];
        }
        if (active) {
            next[normalized] = {
                "width": Math.max(1.0, Number(width)),
                "height": Math.max(1.0, Number(height))
            };
        } else {
            delete next[normalized];
        }
        root.liveResizeDimensions = next;
        edgeLayer.requestRedraw();
    }

    function clearLiveResizeDimensions() {
        if (!root.liveResizeDimensions || Object.keys(root.liveResizeDimensions).length === 0)
            return;
        root.liveResizeDimensions = ({});
        edgeLayer.requestRedraw();
    }

    function _dropTargetInput(sourceDrag, candidate) {
        return GraphCanvasLogic.dropTargetInput(sourceDrag, candidate);
    }

    function _isExactDuplicate(sourceDrag, candidate, edge) {
        return GraphCanvasLogic.isExactDuplicate(sourceDrag, candidate, edge);
    }

    function _portKind(nodeId, portKey) {
        var node = _sceneNodePayload(nodeId);
        if (!node)
            return "";
        var ports = node.ports || [];
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (port && port.key === portKey)
                return port.kind || "";
        }
        return "";
    }

    function _portDataType(nodeId, portKey) {
        var node = _sceneNodePayload(nodeId);
        if (!node)
            return "any";
        var ports = node.ports || [];
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (port && port.key === portKey)
                return port.data_type || "any";
        }
        return "any";
    }

    function _arePortKindsCompatible(sourceKind, targetKind) {
        var bridge = root.canvasBridgeRef || sceneBridge;
        if (!bridge || !bridge.are_port_kinds_compatible)
            return false;
        return bridge.are_port_kinds_compatible(String(sourceKind || ""), String(targetKind || ""));
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

        var nodes = root.canvasBridgeRef ? root.canvasBridgeRef.nodes_model : (sceneBridge ? sceneBridge.nodes_model : []);
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
                    "allow_multiple_connections": Boolean(port.allow_multiple_connections),
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
        var bridge = root.canvasBridgeRef || sceneBridge;
        if (!bridge || !bridge.are_data_types_compatible)
            return false;
        return bridge.are_data_types_compatible(String(sourceType || ""), String(targetType || ""));
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
        var node = _sceneNodePayload(nodeId);
        if (!node)
            return null;
        var ports = node.ports || [];
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (port && port.key === portKey)
                return port;
        }
        return null;
    }

    function _scenePortPoint(node, port, inputRow, outputRow) {
        return GraphCanvasLogic.scenePortPoint(node, port, inputRow, outputRow);
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

        var nodes = root.canvasBridgeRef ? root.canvasBridgeRef.nodes_model : (sceneBridge ? sceneBridge.nodes_model : []);
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
        var view = root.canvasBridgeRef || viewBridge;
        var zoom = view ? view.zoom_value : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return GraphCanvasLogic.previewNodeScreenExtent(metrics.default_width, zoom);
    }

    function previewNodeScreenHeight() {
        var view = root.canvasBridgeRef || viewBridge;
        var zoom = view ? view.zoom_value : 1.0;
        var metrics = _previewNodeMetrics(root.dropPreviewNodePayload);
        return GraphCanvasLogic.previewNodeScreenExtent(metrics.default_height, zoom);
    }

    function previewPortLabelsVisible() {
        var view = root.canvasBridgeRef || viewBridge;
        var zoom = view ? view.zoom_value : 1.0;
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
        var bridge = root.canvasBridgeRef || mainWindowBridge;
        if (!payload || !bridge || !bridge.request_drop_node_from_library || !payload.type_id) {
            clearLibraryDropPreview();
            return;
        }
        root.forceActiveFocus();
        root._closeContextMenus();
        root.clearPendingConnection();
        var target = root._computeLibraryDropTarget(screenX, screenY, payload);
        bridge.request_drop_node_from_library(
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
        var sourcePort = _scenePortData(state.node_id, state.port_key);
        return {
            "node_id": state.node_id,
            "port_key": state.port_key,
            "source_direction": state.source_direction,
            "allow_multiple_connections": sourcePort ? Boolean(sourcePort.allow_multiple_connections) : false,
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
            "allow_multiple_connections": Boolean(pending.allow_multiple_connections),
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "cursor_x": hovered.scene_x,
            "cursor_y": hovered.scene_y
        };
        var pendingCandidate = {
            "node_id": hovered.node_id,
            "port_key": hovered.port_key,
            "direction": hovered.direction,
            "allow_multiple_connections": Boolean(hovered.allow_multiple_connections),
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
        var bridge = root.canvasBridgeRef || mainWindowBridge;
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
        if (candidate && candidate.valid_drop && bridge && bridge.request_connect_ports) {
            bridge.request_connect_ports(
                finalState.node_id,
                finalState.port_key,
                candidate.node_id,
                candidate.port_key
            );
        } else if (bridge && bridge.request_open_connection_quick_insert) {
            var overlayPoint = root.mapToItem(
                root.overlayHostItem ? root.overlayHostItem : root,
                Number(screenX),
                Number(screenY)
            );
            bridge.request_open_connection_quick_insert(
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
        var bridge = root.canvasBridgeRef || mainWindowBridge;
        root.forceActiveFocus();
        root._closeContextMenus();
        var clickedPort = _scenePortData(nodeId, portKey);
        var clicked = {
            "node_id": nodeId,
            "port_key": portKey,
            "direction": direction,
            "allow_multiple_connections": clickedPort ? Boolean(clickedPort.allow_multiple_connections) : false,
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
            "allow_multiple_connections": Boolean(pending.allow_multiple_connections),
            "start_x": pending.scene_x,
            "start_y": pending.scene_y,
            "cursor_x": sceneX,
            "cursor_y": sceneY
        };
        var candidate = clicked;
        candidate.valid_drop = _isDropAllowed(sourceDrag, candidate);
        if (candidate.valid_drop && bridge && bridge.request_connect_ports) {
            var created = bridge.request_connect_ports(
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
        root.edgePayload = root.canvasBridgeRef ? root.canvasBridgeRef.edges_model : (sceneBridge ? sceneBridge.edges_model : []);
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
        var menuHeight = _edgeSupportsFlowStyle(edgeId) ? 232 : 48;
        var position = _clampMenuPosition(x, y, 206, menuHeight);
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
        var menuHeight = _nodeSupportsPassiveStyle(nodeId)
            ? (_nodeCanEnterScope(nodeId) ? 340 : 232)
            : (_nodeCanEnterScope(nodeId) ? 188 : 80);
        var position = _clampMenuPosition(x, y, 206, menuHeight);
        _closeContextMenus();
        root.nodeContextNodeId = nodeId;
        root.contextMenuX = position.x;
        root.contextMenuY = position.y;
        root.nodeContextVisible = true;
    }

    GraphCanvasComponents.GraphCanvasBackground {
        id: backgroundLayer
        objectName: "graphCanvasBackground"
        anchors.fill: parent
        viewBridge: root.viewBridge
        showGrid: root.showGrid
    }

    GraphComponents.EdgeLayer {
        id: edgeLayer
        objectName: "graphCanvasEdgeLayer"
        anchors.fill: parent
        viewBridge: root.viewBridge
        sceneBridge: root.sceneBridge
        edges: root.edgePayload
        nodes: root.canvasBridgeRef ? root.canvasBridgeRef.nodes_model : (sceneBridge ? sceneBridge.nodes_model : [])
        dragOffsets: root.liveDragOffsets
        liveNodeSizes: root.liveResizeDimensions
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
        objectName: "graphCanvasDropPreview"
        canvasItem: root
        viewBridge: root.viewBridge
    }

    Item {
        id: world
        objectName: "graphCanvasWorld"
        width: root.worldSize
        height: root.worldSize
        transformOrigin: Item.TopLeft
        scale: root.canvasBridgeRef ? root.canvasBridgeRef.zoom_value : (viewBridge ? viewBridge.zoom_value : 1.0)
        x: root.width * 0.5 - ((root.canvasBridgeRef ? root.canvasBridgeRef.center_x : (viewBridge ? viewBridge.center_x : 0)) + root.worldOffset) * scale
        y: root.height * 0.5 - ((root.canvasBridgeRef ? root.canvasBridgeRef.center_y : (viewBridge ? viewBridge.center_y : 0)) + root.worldOffset) * scale

        Repeater {
            model: root.canvasBridgeRef ? root.canvasBridgeRef.nodes_model : (sceneBridge ? sceneBridge.nodes_model : [])
            delegate: GraphComponents.GraphNodeHost {
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
                showShadow: root.nodeShadowEnabled
                shadowStrength: root.shadowStrength
                shadowSoftness: root.shadowSoftness
                shadowOffset: root.shadowOffset
                zoom: root.canvasBridgeRef ? root.canvasBridgeRef.zoom_value : (viewBridge ? viewBridge.zoom_value : 1.0)
                renderQualitySimplified: root.interactionActive

                onNodeClicked: function(nodeId, additive) {
                    var bridge = root.canvasBridgeRef || sceneBridge;
                    root.forceActiveFocus();
                    root._closeContextMenus();
                    root.clearPendingConnection();
                    if (!bridge || !bridge.select_node)
                        return;
                    if (!additive)
                        root.clearEdgeSelection();
                    bridge.select_node(nodeId, additive);
                }
                onNodeContextRequested: function(nodeId, localX, localY) {
                    var point = nodeCard.mapToItem(root, localX, localY);
                    root._openNodeContext(nodeId, point.x, point.y);
                }
                onNodeOpenRequested: function(nodeId) {
                    root.requestOpenSubnodeScope(nodeId);
                }
                onDragOffsetChanged: function(nodeId, dx, dy) {
                    root.setLiveDragOffsets(
                        root.dragNodeIdsForAnchor(nodeId),
                        Number(dx),
                        Number(dy)
                    );
                }
                onDragFinished: function(nodeId, finalX, finalY, _moved) {
                    var bridge = root.canvasBridgeRef || sceneBridge;
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
                    if (!bridge)
                        return;
                    if (dragNodeIds.length > 1) {
                        movedByCommit = bridge.move_nodes_by_delta ? bridge.move_nodes_by_delta(dragNodeIds, deltaX, deltaY) : false;
                        if (movedByCommit)
                            root.clearEdgeSelection();
                        return;
                    }

                    if (bridge.move_node)
                        bridge.move_node(nodeId, finalSnappedX, finalSnappedY);
                    if (movedByCommit && bridge.select_node) {
                        root.clearEdgeSelection();
                        bridge.select_node(nodeId, false);
                    }
                }
                onDragCanceled: function(_nodeId) {
                    root.clearLiveDragOffsets();
                }
                onResizePreviewChanged: function(nodeId, newWidth, newHeight, active) {
                    root.setLiveResizeDimensions(nodeId, newWidth, newHeight, active);
                }
                onResizeFinished: function(nodeId, newWidth, newHeight) {
                    var bridge = root.canvasBridgeRef || sceneBridge;
                    root.setLiveResizeDimensions(nodeId, newWidth, newHeight, false);
                    if (!bridge || !bridge.resize_node)
                        return;
                    bridge.resize_node(nodeId, newWidth, newHeight);
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
                        var hoveredPortData = root._scenePortData(nodeId, portKey);
                        root.hoveredPort = {
                            "node_id": nodeId,
                            "port_key": portKey,
                            "direction": direction,
                            "allow_multiple_connections": hoveredPortData ? Boolean(hoveredPortData.allow_multiple_connections) : false,
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
                onSurfaceControlInteractionStarted: function(nodeId) {
                    root.prepareNodeSurfaceControlInteraction(nodeId);
                }
                onInlinePropertyCommitted: function(nodeId, key, value) {
                    if (root.commitNodeSurfaceProperty(nodeId, key, value))
                        root.forceActiveFocus();
                }
            }
        }
    }

    GraphCanvasComponents.GraphCanvasMinimapOverlay {
        id: minimapOverlay
        objectName: "graphCanvasMinimapOverlay"
        canvasItem: root
        sceneBridge: root.sceneBridge
        viewBridge: root.viewBridge
    }

    GraphCanvasComponents.GraphCanvasInputLayers {
        id: inputLayers
        objectName: "graphCanvasInputLayers"
        canvasItem: root
        mainWindowBridge: root.mainWindowBridge
        sceneBridge: root.sceneBridge
        viewBridge: root.viewBridge
    }

    GraphCanvasComponents.GraphCanvasContextMenus {
        id: contextMenus
        objectName: "graphCanvasContextMenus"
        canvasItem: root
        mainWindowBridge: root.mainWindowBridge
    }

    Connections {
        target: root.canvasBridgeRef ? root.canvasBridgeRef : sceneBridge
        ignoreUnknownSignals: true
        function _handleSceneMutation() {
            root.liveDragOffsets = ({});
            root.liveResizeDimensions = ({});
            root._clearWireDragState();
            root._syncEdgePayload();
        }
        function onScene_edges_changed() {
            _handleSceneMutation();
        }
        function onScene_nodes_changed() {
            _handleSceneMutation();
        }
        function onEdges_changed() {
            _handleSceneMutation();
        }
        function onNodes_changed() {
            _handleSceneMutation();
        }
    }

    Connections {
        target: root.canvasBridgeRef ? root.canvasBridgeRef : viewBridge
        ignoreUnknownSignals: true
        function _handleViewStateChanged() {
            backgroundLayer.requestGridRedraw();
            edgeLayer.requestRedraw();
        }
        function onView_state_changed() {
            _handleViewStateChanged();
        }
        function onZoom_changed() {
            _handleViewStateChanged();
        }
        function onCenter_changed() {
            _handleViewStateChanged();
        }
    }

    onSceneBridgeChanged: {
        root.liveDragOffsets = ({});
        root.liveResizeDimensions = ({});
        root.pendingConnectionPort = null;
        root.hoveredPort = null;
        root.wireDragState = null;
        root.wireDropCandidate = null;
        root.clearLibraryDropPreview();
        root._syncEdgePayload();
    }

    onWidthChanged: {
        var view = root.canvasBridgeRef || viewBridge;
        if (view && view.set_viewport_size)
            view.set_viewport_size(width, height);
    }

    onHeightChanged: {
        var view = root.canvasBridgeRef || viewBridge;
        if (view && view.set_viewport_size)
            view.set_viewport_size(width, height);
    }
}
