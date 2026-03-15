.pragma library

function screenToSceneX(screenX, centerX, viewportWidth, zoomValue) {
    var zoom = zoomValue;
    return centerX + (screenX - viewportWidth * 0.5) / Math.max(0.1, zoom);
}

function screenToSceneY(screenY, centerY, viewportHeight, zoomValue) {
    var zoom = zoomValue;
    return centerY + (screenY - viewportHeight * 0.5) / Math.max(0.1, zoom);
}

function wheelDeltaY(eventObj) {
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

function sceneToScreenX(sceneX, centerX, viewportWidth, zoomValue) {
    var zoom = zoomValue;
    return viewportWidth * 0.5 + (sceneX - centerX) * zoom;
}

function sceneToScreenY(sceneY, centerY, viewportHeight, zoomValue) {
    var zoom = zoomValue;
    return viewportHeight * 0.5 + (sceneY - centerY) * zoom;
}

function normalizeSnapGridSize(gridSizeValue) {
    var size = Number(gridSizeValue);
    if (!(size > 0.0))
        size = 20.0;
    return size;
}

function snapToGridValue(value, gridSizeValue) {
    var size = normalizeSnapGridSize(gridSizeValue);
    return Math.round(Number(value) / size) * size;
}

function snappedDragDelta(rawDx, rawDy, snapEnabled, anchorPayload, gridSizeValue) {
    var deltaX = Number(rawDx);
    var deltaY = Number(rawDy);
    if (!isFinite(deltaX))
        deltaX = 0.0;
    if (!isFinite(deltaY))
        deltaY = 0.0;
    if (!snapEnabled)
        return {"dx": deltaX, "dy": deltaY};
    if (!anchorPayload)
        return {"dx": deltaX, "dy": deltaY};

    var anchorX = Number(anchorPayload.x);
    var anchorY = Number(anchorPayload.y);
    if (!isFinite(anchorX))
        anchorX = 0.0;
    if (!isFinite(anchorY))
        anchorY = 0.0;

    var snappedX = snapToGridValue(anchorX + deltaX, gridSizeValue);
    var snappedY = snapToGridValue(anchorY + deltaY, gridSizeValue);
    return {
        "dx": snappedX - anchorX,
        "dy": snappedY - anchorY
    };
}

function normalizeEdgeIds(values) {
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

function availableEdgeIdSet(edges) {
    var ids = {};
    var sourceEdges = edges || [];
    for (var i = 0; i < sourceEdges.length; i++) {
        ids[sourceEdges[i].edge_id] = true;
    }
    return ids;
}

function pruneSelectedEdgeIds(selectedEdgeIds, availableIds) {
    var next = [];
    var selected = selectedEdgeIds || [];
    var idSet = availableIds || {};
    for (var i = 0; i < selected.length; i++) {
        var edgeId = selected[i];
        if (idSet[edgeId])
            next.push(edgeId);
    }
    return next;
}

function dropTargetInput(sourceDrag, candidate) {
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

function isExactDuplicate(sourceDrag, candidate, edge) {
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

function isDropAllowedWithCompatibility(sourceDrag, candidate, edges, kindsCompatible, typesCompatible) {
    if (!sourceDrag || !candidate)
        return false;
    if (candidate.node_id === sourceDrag.node_id && candidate.port_key === sourceDrag.port_key)
        return false;
    if (candidate.direction === sourceDrag.source_direction)
        return false;
    if (!kindsCompatible)
        return false;
    if (!typesCompatible)
        return false;

    var targetInput = dropTargetInput(sourceDrag, candidate);
    var targetAllowsMultiple = sourceDrag.source_direction === "out"
        ? Boolean(candidate.allow_multiple_connections)
        : Boolean(sourceDrag.allow_multiple_connections);
    var edgePayload = edges || [];
    for (var i = 0; i < edgePayload.length; i++) {
        var edge = edgePayload[i];
        var sameTargetInput = edge.target_node_id === targetInput.node_id && edge.target_port_key === targetInput.port_key;
        if (!sameTargetInput)
            continue;
        if (isExactDuplicate(sourceDrag, candidate, edge))
            continue;
        if (targetAllowsMultiple)
            continue;
        return false;
    }
    return true;
}

function portsCompatibleForAuto(sourcePort, targetPort, kindsCompatible, typesCompatible) {
    if (!sourcePort || !targetPort)
        return false;
    return kindsCompatible && typesCompatible;
}

function libraryPorts(payload) {
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

function scenePortPoint(node, port, inputRow, outputRow) {
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

function previewNodeMetrics(payload) {
    if (!payload)
        return {"portCount": 1, "worldWidth": 210.0, "worldHeight": 50.0};
    var ports = libraryPorts(payload);
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

function previewVisiblePorts(payload, direction) {
    var source = libraryPorts(payload);
    var output = [];
    for (var i = 0; i < source.length; i++) {
        var port = source[i];
        if (!port || port.exposed === false || port.direction !== direction)
            continue;
        output.push(port);
    }
    return output;
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

function previewNodeScreenExtent(worldExtent, zoomValue) {
    return worldExtent * zoomValue;
}

function previewPortLabelsVisible(zoomValue, previewNodeWidth) {
    return zoomValue >= 0.95 && previewNodeWidth >= 155;
}

function pointInCanvas(screenX, screenY, canvasWidth, canvasHeight) {
    return Number(screenX) >= 0
        && Number(screenY) >= 0
        && Number(screenX) <= canvasWidth
        && Number(screenY) <= canvasHeight;
}

function clampMenuPosition(x, y, menuWidth, menuHeight, canvasWidth, canvasHeight, padding) {
    var safePadding = Number(padding);
    if (!(safePadding >= 0.0))
        safePadding = 4.0;
    return {
        "x": Math.max(safePadding, Math.min(x, canvasWidth - menuWidth - safePadding)),
        "y": Math.max(safePadding, Math.min(y, canvasHeight - menuHeight - safePadding))
    };
}

function normalizedOffset(period, anchor) {
    var raw = anchor % period;
    if (raw < 0)
        raw += period;
    return raw;
}

function normalizeRectPayload(payload, fallbackX, fallbackY, fallbackWidth, fallbackHeight) {
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
