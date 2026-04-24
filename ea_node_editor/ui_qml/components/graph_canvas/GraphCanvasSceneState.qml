import QtQml 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

QtObject {
    id: root
    property var canvasItem: null
    property var edgeLayerItem: null
    property var selectedEdgeIds: []
    property var liveDragOffsets: ({})
    property var liveNodeGeometry: ({})

    function _requestEdgeRedraw() {
        if (root.edgeLayerItem && root.edgeLayerItem.requestRedraw)
            root.edgeLayerItem.requestRedraw();
    }

    function normalizeEdgeIds(values) {
        return GraphCanvasLogic.normalizeEdgeIds(values);
    }

    function availableEdgeIdSet() {
        return GraphCanvasLogic.availableEdgeIdSet(root.canvasItem ? root.canvasItem.edgePayload : []);
    }

    function pruneSelectedEdges() {
        root.selectedEdgeIds = GraphCanvasLogic.pruneSelectedEdgeIds(root.selectedEdgeIds, root.availableEdgeIdSet());
    }

    function clearEdgeSelection() {
        if (!root.selectedEdgeIds.length)
            return;
        root.selectedEdgeIds = [];
    }

    function toggleEdgeSelection(edgeId) {
        var next = root.normalizeEdgeIds(root.selectedEdgeIds);
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

    function sceneBackdropNodesModel() {
        var stateBridge = root.canvasItem ? root.canvasItem.sceneStateBridge : null;
        if (stateBridge && stateBridge.backdrop_nodes_model !== undefined)
            return stateBridge.backdrop_nodes_model || [];
        return [];
    }

    function sceneAllNodesModel() {
        var nodes = root.canvasItem && root.canvasItem.sceneStateBridge
            ? root.canvasItem.sceneStateBridge.nodes_model
            : [];
        var backdrops = root.sceneBackdropNodesModel();
        if (!backdrops.length)
            return nodes;
        return nodes.concat(backdrops);
    }

    function sceneNodePayload(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return null;
        var nodes = root.sceneAllNodesModel();
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (node && node.node_id === normalized)
                return node;
        }
        return null;
    }

    function sceneEdgePayload(edgeId) {
        var normalized = String(edgeId || "").trim();
        if (!normalized)
            return null;
        var edges = root.canvasItem ? (root.canvasItem.edgePayload || []) : [];
        for (var i = 0; i < edges.length; i++) {
            var edge = edges[i];
            if (edge && edge.edge_id === normalized)
                return edge;
        }
        return null;
    }

    function nodeSupportsPassiveStyle(nodeId) {
        var payload = root.sceneNodePayload(nodeId);
        if (!payload)
            return false;
        return String(payload.runtime_behavior || "").toLowerCase() === "passive";
    }

    function edgeSupportsFlowStyle(edgeId) {
        var payload = root.sceneEdgePayload(edgeId);
        if (!payload)
            return false;
        return String(payload.edge_family || "").toLowerCase() === "flow";
    }

    function nodeCanEnterScope(nodeId) {
        var payload = root.sceneNodePayload(nodeId);
        if (!payload)
            return false;
        if (payload.can_enter_scope !== undefined)
            return Boolean(payload.can_enter_scope);
        return String(payload.type_id || "") === "core.subnode";
    }

    function selectedNodeIds() {
        var bridge = root.canvasItem ? root.canvasItem.sceneStateBridge : null;
        var nodes = root.sceneAllNodesModel();
        var selectedLookup = null;
        if (bridge && typeof bridge.selected_node_lookup !== "undefined")
            selectedLookup = bridge.selected_node_lookup || ({});
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

    function _appendUniqueDragNodeId(nodeIds, seenNodeIds, nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized || Boolean(seenNodeIds[normalized]))
            return;
        seenNodeIds[normalized] = true;
        nodeIds.push(normalized);
    }

    function _payloadNodeIdList(payload, key) {
        if (!payload || payload[key] === undefined || payload[key] === null)
            return [];
        if (payload[key].length === undefined)
            return [payload[key]];
        return payload[key];
    }

    function isCommentBackdropPayload(payload) {
        return !!payload && String(payload.surface_family || "").trim() === "comment_backdrop";
    }

    function _nodeVisiblePorts(payload) {
        if (!payload)
            return [];
        var ports = payload.ports || [];
        var visiblePorts = [];
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (port && port.exposed !== false)
                visiblePorts.push(port);
        }
        return visiblePorts;
    }

    function nodeCanAffectEdgeGeometry(nodeId) {
        var payload = root.sceneNodePayload(nodeId);
        if (!payload)
            return true;
        if (root.isCommentBackdropPayload(payload))
            return false;
        return root._nodeVisiblePorts(payload).length > 0;
    }

    function _appendBackdropDragDescendants(nodeIds, seenNodeIds, backdropNodeId) {
        var payload = root.sceneNodePayload(backdropNodeId);
        if (!root.isCommentBackdropPayload(payload))
            return;

        var memberNodeIds = root._payloadNodeIdList(payload, "member_node_ids");
        for (var i = 0; i < memberNodeIds.length; i++)
            root._appendUniqueDragNodeId(nodeIds, seenNodeIds, memberNodeIds[i]);

        var memberBackdropIds = root._payloadNodeIdList(payload, "member_backdrop_ids");
        for (var j = 0; j < memberBackdropIds.length; j++)
            root._appendUniqueDragNodeId(nodeIds, seenNodeIds, memberBackdropIds[j]);
        for (var k = 0; k < memberBackdropIds.length; k++)
            root._appendBackdropDragDescendants(nodeIds, seenNodeIds, memberBackdropIds[k]);
    }

    function _appendBackdropAwareDragNodeIds(nodeIds, seenNodeIds, nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return;
        root._appendUniqueDragNodeId(nodeIds, seenNodeIds, normalized);
        root._appendBackdropDragDescendants(nodeIds, seenNodeIds, normalized);
    }

    function dragNodeIdsForAnchor(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return [];
        var selected = root.selectedNodeIds();
        var baseNodeIds = [];
        if (selected.length > 1 && selected.indexOf(normalized) >= 0) {
            baseNodeIds.push(normalized);
            for (var i = 0; i < selected.length; i++) {
                if (selected[i] !== normalized)
                    baseNodeIds.push(selected[i]);
            }
        } else {
            baseNodeIds.push(normalized);
        }

        var ordered = [];
        var seenNodeIds = {};
        for (var index = 0; index < baseNodeIds.length; index++)
            root._appendBackdropAwareDragNodeIds(ordered, seenNodeIds, baseNodeIds[index]);
        return ordered;
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
        root._requestEdgeRedraw();
    }

    function clearLiveDragOffsets() {
        if (!root.liveDragOffsets || Object.keys(root.liveDragOffsets).length === 0)
            return;
        root.liveDragOffsets = ({});
        root._requestEdgeRedraw();
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

    function setLiveNodeGeometry(nodeId, x, y, width, height, active) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return;
        var redrawEdges = root.nodeCanAffectEdgeGeometry(normalized);
        var next = {};
        var source = root.liveNodeGeometry || {};
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key))
                next[key] = source[key];
        }
        if (active) {
            next[normalized] = {
                "x": Number(x),
                "y": Number(y),
                "width": Math.max(1.0, Number(width)),
                "height": Math.max(1.0, Number(height))
            };
        } else {
            delete next[normalized];
        }
        root.liveNodeGeometry = next;
        if (redrawEdges)
            root._requestEdgeRedraw();
    }

    function clearLiveNodeGeometry() {
        if (!root.liveNodeGeometry || Object.keys(root.liveNodeGeometry).length === 0)
            return;
        root.liveNodeGeometry = ({});
        root._requestEdgeRedraw();
    }

    function syncEdgePayload() {
        if (!root.canvasItem)
            return;
        root.canvasItem.edgePayload = root.canvasItem.sceneStateBridge
            ? root.canvasItem.sceneStateBridge.edges_model
            : [];
        root.pruneSelectedEdges();
        root._requestEdgeRedraw();
    }
}
