.pragma library
.import "GraphCanvasLogic.js" as GraphCanvasLogic

function invoke(target, methodName, args, fallbackValue) {
    if (!target || typeof target[methodName] !== "function")
        return fallbackValue;
    return target[methodName].apply(target, args || []);
}

function snapToGridEnabled(canvasStateBridge) {
    return canvasStateBridge ? Boolean(canvasStateBridge.snap_to_grid_enabled) : false;
}

function snapGridSize(canvasStateBridge) {
    return GraphCanvasLogic.normalizeSnapGridSize(
        canvasStateBridge ? canvasStateBridge.snap_grid_size : 20.0
    );
}

function snapToGridValue(canvasStateBridge, value) {
    return GraphCanvasLogic.snapToGridValue(value, snapGridSize(canvasStateBridge));
}

function snappedDragDelta(sceneState, canvasStateBridge, nodeId, rawDx, rawDy) {
    return GraphCanvasLogic.snappedDragDelta(
        rawDx,
        rawDy,
        snapToGridEnabled(canvasStateBridge),
        invoke(sceneState, "sceneNodePayload", [nodeId], null),
        snapGridSize(canvasStateBridge)
    );
}

// The guide snap of a moved release, or null. Guides only resolve inside the move session that the
// drag's live offsets started (GraphCanvasSceneState._freezeLiveDragMembership); the commit never
// starts one, so a dragFinished without live offsets meets the grid alone.
function smartGuideCommit(smartGuides, nodeId, rawDx, rawDy, axisLock) {
    if (!smartGuides || !smartGuides.moveSessionFor(nodeId))
        return null;
    return smartGuides.resolveCommit(rawDx, rawDy, axisLock, false);
}

// With grid snap on and exactly one axis guided, the grid then moves the other axis. An alignment line
// on the guided axis reads every candidate's edges whatever the other axis does, so that guide stays as
// resolved. Equal spacing alone depends on the row or column the moving rect sits in, which the grid can
// change (an equal-spacing X chosen at the raw Y, say): the guided axis is resolved again from the
// guide's own value with the other axis held at its grid value (axisLock "horizontal" holds Y and lets
// only X snap), and the guide stays only if it snaps to that same value there. Otherwise, rather than
// land on a guide the drag never showed, both axes meet the grid. `guide` comes from smartGuideCommit,
// so its session is the drag's.
function gridSettledGuide(smartGuides, guide, grid) {
    if (!guide || !grid || Boolean(guide.snappedX) === Boolean(guide.snappedY))
        return guide;
    var axis = guide.snappedX ? "x" : "y";
    if (GraphCanvasLogic.guideLineOnAxis(guide.lines, axis))
        return guide;
    var settled = axis === "x"
        ? smartGuides.resolveCommit(Number(guide.dx), Number(grid.dy), "horizontal", false)
        : smartGuides.resolveCommit(Number(grid.dx), Number(guide.dy), "vertical", false);
    return GraphCanvasLogic.sameGuideSnap(guide, settled, axis) ? guide : null;
}

// Release delta of the drag anchored on `nodeId`; see GraphCanvasLogic.dragCommitDelta. An unmoved
// release (a click) never runs the guides: it keeps the grid-only commit. A Shift-locked axis stays put
// rather than meeting the grid, so a locked drag keeps its guide as resolved.
function resolveDragCommitDelta(sceneState, smartGuides, canvasStateBridge, nodeId, rawDx, rawDy, moved, axisLock, snapBypass) {
    var lock = String(axisLock || "");
    var bypass = Boolean(snapBypass);
    var guide = Boolean(moved) && !bypass ? smartGuideCommit(smartGuides, nodeId, rawDx, rawDy, lock) : null;
    var grid = bypass ? null : snappedDragDelta(sceneState, canvasStateBridge, nodeId, rawDx, rawDy);
    if (!lock.length && snapToGridEnabled(canvasStateBridge))
        guide = gridSettledGuide(smartGuides, guide, grid);
    return GraphCanvasLogic.dragCommitDelta(rawDx, rawDy, lock, bypass, guide, grid);
}

function isPointInCanvas(canvasItem, screenX, screenY) {
    return GraphCanvasLogic.pointInCanvas(
        screenX,
        screenY,
        canvasItem ? canvasItem.width : 0,
        canvasItem ? canvasItem.height : 0
    );
}

function clampMenuPosition(canvasItem, x, y, menuWidth, menuHeight) {
    return GraphCanvasLogic.clampMenuPosition(
        x,
        y,
        menuWidth,
        menuHeight,
        canvasItem ? canvasItem.width : 0,
        canvasItem ? canvasItem.height : 0,
        4
    );
}
