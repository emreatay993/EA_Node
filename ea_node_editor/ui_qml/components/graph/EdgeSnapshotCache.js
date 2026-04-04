.pragma library
.import "EdgeMath.js" as EdgeMath
.import "EdgeViewportMath.js" as EdgeViewportMath

function invalidateGeometryCache(edgeLayer) {
    edgeLayer._cachedNodeMap = null;
    edgeLayer._cachedEdgeGeometries = ({});
}

function getNodeMap(edgeLayer) {
    if (edgeLayer._cachedNodeMap !== null)
        return edgeLayer._cachedNodeMap;
    edgeLayer._cachedNodeMap = edgeLayer._nodeMap();
    return edgeLayer._cachedNodeMap;
}

function getCachedEdgeGeometry(edgeLayer, edge, nodeById) {
    var edgeId = edge.edge_id;
    var cached = edgeLayer._cachedEdgeGeometries[edgeId];
    if (cached !== undefined)
        return cached;
    var geometry = edgeLayer._edgeGeometry(edge, nodeById);
    edgeLayer._cachedEdgeGeometries[edgeId] = geometry;
    return geometry;
}

function expandedVisibleSceneBounds(edgeLayer) {
    var payload = edgeLayer.visibleSceneRectPayload;
    if ((!payload || payload.width === undefined || payload.height === undefined) && edgeLayer.viewBridge)
        payload = edgeLayer.viewBridge.visible_scene_rect_payload;
    if (!payload)
        return null;
    var x = Number(payload.x);
    var y = Number(payload.y);
    var width = Number(payload.width);
    var height = Number(payload.height);
    if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height) || width <= 0.0 || height <= 0.0)
        return null;
    var viewportTransform = EdgeViewportMath.viewportTransform(edgeLayer);
    var sceneMargin = EdgeViewportMath.screenMarginToScene(edgeLayer.viewportCullMarginPx, viewportTransform);
    return {
        "left": x - sceneMargin,
        "top": y - sceneMargin,
        "right": x + width + sceneMargin,
        "bottom": y + height + sceneMargin
    };
}

function geometrySceneBounds(edgeLayer, geometry) {
    if (!geometry)
        return null;
    if (geometry.route === "pipe")
        return edgeLayer._sceneBoundsForPoints(geometry.pipe_points || []);
    return edgeLayer._sceneBoundsForPoints([
        {"x": geometry.sx, "y": geometry.sy},
        {"x": geometry.c1x, "y": geometry.c1y},
        {"x": geometry.c2x, "y": geometry.c2y},
        {"x": geometry.tx, "y": geometry.ty}
    ]);
}

function edgeCullState(edgeLayer, edge, nodeById, viewportBounds) {
    var geometry = getCachedEdgeGeometry(edgeLayer, edge, nodeById);
    var sceneBounds = geometrySceneBounds(edgeLayer, geometry);
    var visibleBounds = viewportBounds || expandedVisibleSceneBounds(edgeLayer);
    var culled = sceneBounds && visibleBounds ? !edgeLayer._rectIntersects(sceneBounds, visibleBounds) : false;
    return {"culled": culled, "geometry": culled ? null : geometry};
}

function _isSelected(edgeLayer, edgeId) {
    return (edgeLayer.selectedEdgeIds || []).indexOf(edgeId) >= 0;
}

function buildVisibleEdgeSnapshots(edgeLayer, canvasLayer, labelLayer, revision) {
    var snapshots = [];
    var snapshotById = {};
    var edgesList = edgeLayer.edges || [];
    var nodeById = getNodeMap(edgeLayer);
    var viewportBounds = expandedVisibleSceneBounds(edgeLayer);
    var viewportTransform = EdgeViewportMath.viewportTransform(edgeLayer);

    for (var i = 0; i < edgesList.length; i++) {
        var edge = edgesList[i];
        if (!edge || !edge.edge_id)
            continue;
        var edgeId = String(edge.edge_id);
        var cullState = edgeCullState(edgeLayer, edge, nodeById, viewportBounds);
        var geometry = cullState && !cullState.culled ? cullState.geometry : null;
        var labelMode = labelLayer.flowLabelMode(edge);
        var snapshot = {
            "revision": revision,
            "edgeId": edgeId,
            "edgeData": edge,
            "culled": cullState ? Boolean(cullState.culled) : false,
            "geometry": geometry,
            "selected": _isSelected(edgeLayer, edgeId),
            "previewed": Boolean(edgeLayer.previewEdgeId && edgeLayer.previewEdgeId === edgeId),
            "flowEdge": canvasLayer.edgeIsFlow(edge),
            "labelText": labelLayer.edgeLabelText(edge),
            "labelMode": labelMode,
            "drawOrderIndex": i,
            "crossingBreaks": [],
            "crossingSamplePoints": [],
            "labelAnchorScene": labelMode !== "hidden" && geometry
                ? labelLayer.flowLabelAnchorScene(geometry)
                : null
        };
        snapshots.push(snapshot);
        snapshotById[edgeId] = snapshot;
    }

    snapshots = canvasLayer.applyCrossingMetadata(snapshots, viewportTransform);
    return {"snapshots": snapshots, "snapshotById": snapshotById};
}

function refreshVisibleEdgeSnapshots(edgeLayer, canvasLayer, labelLayer) {
    var nextRevision = edgeLayer._visibleEdgeSnapshotRevision + 1;
    var model = buildVisibleEdgeSnapshots(edgeLayer, canvasLayer, labelLayer, nextRevision);
    edgeLayer._visibleEdgeSnapshots = model.snapshots;
    edgeLayer._visibleEdgeSnapshotById = model.snapshotById;
    edgeLayer._visibleEdgeSnapshotRevision = nextRevision;
}

function visibleEdgeSnapshot(edgeLayer, edgeId) {
    var normalized = String(edgeId || "");
    if (!normalized)
        return null;
    return edgeLayer._visibleEdgeSnapshotById[normalized] || null;
}

function _edgeDistanceAtScreen(geometry, screenX, screenY, viewportTransform) {
    if (!geometry)
        return Number.POSITIVE_INFINITY;
    var sceneX = EdgeViewportMath.screenToSceneX(screenX, viewportTransform);
    var sceneY = EdgeViewportMath.screenToSceneY(screenY, viewportTransform);
    if (geometry.route === "pipe")
        return EdgeMath.distancePolyline(sceneX, sceneY, geometry.pipe_points || []);
    return EdgeMath.distanceBezier(
        sceneX,
        sceneY,
        geometry.sx,
        geometry.sy,
        geometry.c1x,
        geometry.c1y,
        geometry.c2x,
        geometry.c2y,
        geometry.tx,
        geometry.ty,
        28
    );
}

function edgeAtScreen(edgeLayer, canvasLayer, labelLayer, screenX, screenY) {
    var snapshots = edgeLayer._visibleEdgeSnapshots || [];
    if (!snapshots.length && (edgeLayer.edges || []).length) {
        refreshVisibleEdgeSnapshots(edgeLayer, canvasLayer, labelLayer);
        snapshots = edgeLayer._visibleEdgeSnapshots || [];
    }
    if (!snapshots.length)
        return "";
    var viewportTransform = EdgeViewportMath.viewportTransform(edgeLayer);
    var threshold = EdgeViewportMath.screenLengthToScene(8.0, viewportTransform);
    var bestId = "";
    var bestDistance = Number.POSITIVE_INFINITY;
    for (var i = snapshots.length - 1; i >= 0; i--) {
        var snapshot = snapshots[i];
        if (!snapshot || snapshot.culled || !snapshot.geometry)
            continue;
        var distance = _edgeDistanceAtScreen(snapshot.geometry, screenX, screenY, viewportTransform);
        if (distance < bestDistance && distance <= threshold) {
            bestDistance = distance;
            bestId = snapshot.edgeId;
        }
    }
    return bestId;
}
