// Purpose: Own the smart-guide session of one node drag or resize: snapshot the candidates (again after a zoom, a pan, a scene change or, at most once per retake interval, a move that a trimmed snapshot's left-out candidates could reach), snap through GraphCanvasSmartGuideEngine.js and publish the guide lines and gap markers the overlay draws.
// Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
// Tests: tests/test_graph_canvas_smart_guides.py
import QtQml 2.15
import "GraphCanvasSmartGuideEngine.js" as SmartGuideEngine

// One session at a time. A move session starts when the live drag freezes its membership and ends
// with clearLiveDragOffset(); the resize handle starts and ends its own session. The candidate
// snapshot is taken on the first resolve that is not bypassed (as a rule the gesture's only Python
// call) and is rebuilt only when the zoom or view centre changed since, when the scene changed under
// the session (invalidateSnapshot), or when the gesture has moved far enough from where a trimmed
// snapshot was ranked that a candidate it left out could matter and retakeMinIntervalMs has passed
// since the session's last snapshot. Every rect and offset is in scene units.
QtObject {
    id: root
    objectName: "graphCanvasSmartGuides"

    property var canvasItem: null
    property var canvasStateBridge: null
    property var viewBridge: null
    property bool enabled: true
    property real thresholdPx: 6.0
    // The snapshot covers the exact viewport plus this margin, so a node just off screen can still
    // guide an edge dragged to the viewport border.
    property real snapshotMarginPx: 32.0
    // A snapshot the bridge trimmed to its candidate cap was ranked around the gesture's offset when it
    // was taken, and names the smallest gap along x and along y from the moving union there to a
    // candidate it left out (dropGapX, dropGapY). Equal spacing along x only reads the candidates that
    // overlap the moving rect along y, and along y those that overlap it along x, so none left out can
    // join them before the union has moved that far along the other axis; a snap moves the settled rect
    // up to one threshold further, so that much less. Past it the snapshot is retaken, but never before
    // the gesture has travelled resnapshotFloorPx screen pixels from where it was ranked: a dense layout
    // that leaves candidates out beside the moving rect retakes at most once per that much travel.
    property real resnapshotFloorPx: 40.0
    // Nor before this many milliseconds have passed since the session's last snapshot (_nowMs()). A
    // slow, precise drag takes longer than that to cover the floor, so it keeps every retake; a fast
    // one retakes at most about 12 times a second rather than every frame or two, each retake being a
    // slot call and an index build of several milliseconds. The session's first snapshot, a zoom or
    // view-centre change and invalidateSnapshot() never wait.
    property int retakeMinIntervalMs: 80
    // Published guides, scene coordinates: lines [{axis, value, start, end}] and gap markers
    // [{axis, start, end, cross, crossStart, crossEnd, size}] (see GraphCanvasSmartGuideEngine.js).
    property var lines: []
    property var gaps: []
    // Bumped once per publish that changed lines or gaps, after both are set, so the overlay builds its
    // pieces once per publish rather than once per array.
    property int guideRevision: 0
    // True while a move or resize session runs.
    readonly property bool active: root._mode.length > 0
    property int profileSnapshotCount: 0
    property int profileResolveCount: 0
    property real profileLastSnapshotMs: 0.0

    // Cached view state, so a drag frame reads no Python property.
    readonly property real _viewZoom: {
        var zoom = root.viewBridge ? Number(root.viewBridge.zoom_value) : 1.0;
        return isFinite(zoom) && zoom > 0.0001 ? zoom : 1.0;
    }
    readonly property real _viewCenterX: root.viewBridge ? Number(root.viewBridge.center_x) || 0.0 : 0.0
    readonly property real _viewCenterY: root.viewBridge ? Number(root.viewBridge.center_y) || 0.0 : 0.0
    property string _mode: ""
    property var _nodeIds: []
    property var _index: null
    property var _base: null
    property bool _snapshotReady: false
    property real _snapshotZoom: 0.0
    property real _snapshotCenterX: 0.0
    property real _snapshotCenterY: 0.0
    // Whether the bridge trimmed the snapshot, the offset it was ranked around, and its drop gaps (scene
    // units).
    property bool _snapshotTrimmed: false
    property real _snapshotOffsetX: 0.0
    property real _snapshotOffsetY: 0.0
    property real _dropGapX: 0.0
    property real _dropGapY: 0.0
    // When the current snapshot was taken (_nowMs()), and whether the last live frame resolved on it
    // although the drop-gap rule wanted it retaken, because the retake interval had not passed yet.
    property real _snapshotTakenMs: 0.0
    property bool _retakeHeld: false
    property var _resizeSpec: null

    function _finite(value, fallback) {
        var number = Number(value);
        return isFinite(number) ? number : fallback;
    }

    // Scene-unit snap distance at the current zoom.
    function threshold() {
        return Math.max(0.0, Number(root.thresholdPx) || 0.0) / root._viewZoom;
    }

    function _normalizedNodeIds(values) {
        var normalized = [];
        var seen = {};
        var source = values || [];
        for (var i = 0; i < source.length; ++i) {
            var nodeId = String(source[i] || "").trim();
            if (!nodeId.length || seen[nodeId])
                continue;
            seen[nodeId] = true;
            normalized.push(nodeId);
        }
        return normalized;
    }

    function _dropSnapshot() {
        root._index = null;
        root._snapshotReady = false;
        root._snapshotTrimmed = false;
    }

    function _begin(mode, nodeIds) {
        var normalized = root._normalizedNodeIds(nodeIds);
        root._mode = normalized.length ? mode : "";
        root._nodeIds = normalized;
        root._dropSnapshot();
        root._base = null;
        root._resizeSpec = null;
        root._publish([], []);
    }

    function _end() {
        root._mode = "";
        root._nodeIds = [];
        root._dropSnapshot();
        root._base = null;
        root._resizeSpec = null;
        root._publish([], []);
    }

    // The scene changed under the running session: the next resolve takes a new snapshot, and the guides
    // drawn from the old one go now. The session keeps running, and so does the moving union of the old
    // snapshot, so a resize still ranks the new one around its moving corner.
    function invalidateSnapshot() {
        if (!root._mode.length)
            return;
        root._dropSnapshot();
        root._publish([], []);
    }

    // Cheap: the snapshot waits for the first resolve that is not bypassed.
    function beginMove(nodeIds) {
        root._begin("move", nodeIds);
    }

    function endMove() {
        if (root._mode === "move")
            root._end();
    }

    // Whether the running move session belongs to the drag anchored on `nodeId`.
    function moveSessionFor(nodeId) {
        return root._mode === "move"
            && root._nodeIds.length > 0
            && root._nodeIds[0] === String(nodeId || "").trim();
    }

    function beginResize(nodeId) {
        root._begin("resize", [nodeId]);
    }

    function endResize() {
        if (root._mode === "resize")
            root._end();
    }

    function _sameEntries(current, next, keys) {
        if (!current || current.length !== next.length)
            return false;
        for (var i = 0; i < next.length; ++i) {
            for (var k = 0; k < keys.length; ++k) {
                if (current[i][keys[k]] !== next[i][keys[k]])
                    return false;
            }
        }
        return true;
    }

    // The overlay places horizontal-gap markers from crossStart, so a changed span republishes even when
    // its middle (cross) stays put.
    function _publish(lines, gaps) {
        var nextLines = lines || [];
        var nextGaps = gaps || [];
        var changed = false;
        if (!root._sameEntries(root.lines, nextLines, ["axis", "value", "start", "end"])) {
            root.lines = nextLines;
            changed = true;
        }
        if (!root._sameEntries(root.gaps, nextGaps, ["axis", "start", "end", "cross", "crossStart", "crossEnd", "size"])) {
            root.gaps = nextGaps;
            changed = true;
        }
        if (changed)
            root.guideRevision += 1;
    }

    // The visible scene rect {x, y, width, height}, or null when it is not a finite rect with a size.
    function _visibleRect() {
        var visible = root.canvasItem ? root.canvasItem.visibleSceneRectPayload : null;
        if (!visible)
            return null;
        var x = Number(visible.x);
        var y = Number(visible.y);
        var width = Number(visible.width);
        var height = Number(visible.height);
        if (!(isFinite(x) && isFinite(y) && width > 0.0 && height > 0.0))
            return null;
        return {"x": x, "y": y, "width": width, "height": height};
    }

    function _queryRect(visible) {
        if (!visible)
            return ({});
        var margin = Math.max(0.0, Number(root.snapshotMarginPx) || 0.0) / root._viewZoom;
        return {
            "x": visible.x - margin,
            "y": visible.y - margin,
            "width": visible.width + margin * 2.0,
            "height": visible.height + margin * 2.0
        };
    }

    // Scene units a gesture travels from where a trimmed snapshot was ranked before it may be retaken.
    function _resnapshotFloor() {
        return Math.max(0.0, Number(root.resnapshotFloorPx) || 0.0) / root._viewZoom;
    }

    // A drop gap of the snapshot; one that is missing or not a finite non-negative number is 0, so any
    // move past the floor retakes.
    function _dropGap(snapshot, key) {
        var gap = snapshot ? Number(snapshot[key]) : NaN;
        return isFinite(gap) && gap > 0.0 ? gap : 0.0;
    }

    function _viewChangedSinceSnapshot() {
        return root._snapshotZoom !== root._viewZoom
            || root._snapshotCenterX !== root._viewCenterX
            || root._snapshotCenterY !== root._viewCenterY;
    }

    // The retake interval's clock, in milliseconds.
    function _nowMs() {
        return Date.now();
    }

    // Whether retakeMinIntervalMs has passed since the current snapshot was taken. A clock that went back
    // (a system time change) counts as passed, so it cannot hold retakes back for as long as it jumped.
    function _retakeIntervalPassed() {
        var elapsed = root._nowMs() - root._snapshotTakenMs;
        return !(elapsed >= 0.0) || elapsed >= Math.max(0.0, Number(root.retakeMinIntervalMs) || 0.0);
    }

    // The drop-gap rule: whether the gesture at (offsetX, offsetY) has moved past the floor from where a
    // trimmed snapshot was ranked and far enough along x or y that a candidate left out could overlap the
    // settled moving rect along that axis.
    function _leftOutCandidateInReach(offsetX, offsetY) {
        if (!root._snapshotTrimmed)
            return false;
        var dx = Math.abs(offsetX - root._snapshotOffsetX);
        var dy = Math.abs(offsetY - root._snapshotOffsetY);
        var floor = root._resnapshotFloor();
        if (dx * dx + dy * dy < floor * floor)
            return false;
        var slack = root.threshold();
        return dx + slack >= root._dropGapX || dy + slack >= root._dropGapY;
    }

    // Whether the gesture at (offsetX, offsetY) needs a new snapshot: there is none, the view changed, or
    // the drop-gap rule says so and the retake interval has passed. A live frame notes a retake the
    // interval held back, and a release after it keeps that snapshot, so the node lands where the frame
    // showed it rather than on a guide only a later snapshot has.
    function _snapshotStale(offsetX, offsetY, release) {
        if (!root._snapshotReady || root._viewChangedSinceSnapshot())
            return true;
        var due = root._leftOutCandidateInReach(offsetX, offsetY);
        if (release)
            return due && !root._retakeHeld && root._retakeIntervalPassed();
        var stale = due && root._retakeIntervalPassed();
        root._retakeHeld = due && !stale;
        return stale;
    }

    // Takes a snapshot ranked around the moving rects moved by (offsetX, offsetY), unless the current one
    // still serves; false without candidates. `release` marks the release's resolve (resolveCommit).
    function _ensureSnapshot(offsetX, offsetY, release) {
        var rankX = root._finite(offsetX, 0.0);
        var rankY = root._finite(offsetY, 0.0);
        if (root._snapshotStale(rankX, rankY, Boolean(release))) {
            root._snapshotTakenMs = root._nowMs();
            root._retakeHeld = false;
            var started = Date.now();
            var bridge = root.canvasStateBridge;
            var visible = root._visibleRect();
            var snapshot = bridge && typeof bridge.smart_guide_snapshot === "function"
                ? bridge.smart_guide_snapshot(root._nodeIds, root._queryRect(visible), {
                    "offset_x": rankX,
                    "offset_y": rankY
                })
                : null;
            var moving = snapshot && snapshot.moving ? snapshot.moving : [];
            var candidates = snapshot && snapshot.candidates ? snapshot.candidates : [];
            root._index = SmartGuideEngine.buildIndex(candidates);
            root._base = SmartGuideEngine.unionRect(moving);
            root._snapshotReady = true;
            root._snapshotZoom = root._viewZoom;
            root._snapshotCenterX = root._viewCenterX;
            root._snapshotCenterY = root._viewCenterY;
            root._snapshotTrimmed = Boolean(snapshot && snapshot.trimmed);
            root._snapshotOffsetX = rankX;
            root._snapshotOffsetY = rankY;
            root._dropGapX = root._dropGap(snapshot, "dropGapX");
            root._dropGapY = root._dropGap(snapshot, "dropGapY");
            root.profileSnapshotCount += 1;
            root.profileLastSnapshotMs = Date.now() - started;
        }
        return root._index !== null && root._index.count > 0;
    }

    function _rawMove(rawDx, rawDy) {
        return {
            "dx": root._finite(rawDx, 0.0),
            "dy": root._finite(rawDy, 0.0),
            "snappedX": false,
            "snappedY": false,
            "lines": [],
            "gaps": []
        };
    }

    function _guidedMove(rawDx, rawDy, axisLock, release) {
        if (!root._ensureSnapshot(rawDx, rawDy, release) || root._base === null)
            return root._rawMove(rawDx, rawDy);
        root.profileResolveCount += 1;
        return SmartGuideEngine.resolveMove(root._index, root._base, rawDx, rawDy, {
            "threshold": root.threshold(),
            "axisLock": String(axisLock || ""),
            "spacing": true
        });
    }

    // Live drag frame: the snapped offset of the moving union, and its guides published for the overlay.
    // Disabled, bypassed (Alt) or outside a move session it returns the raw offset and clears the guides.
    function resolveMove(rawDx, rawDy, axisLock, snapBypass) {
        if (!root.enabled || Boolean(snapBypass) || root._mode !== "move") {
            root._publish([], []);
            return root._rawMove(rawDx, rawDy);
        }
        var result = root._guidedMove(rawDx, rawDy, axisLock, false);
        root._publish(result.lines, result.gaps);
        return result;
    }

    // Release: the same snap as resolveMove without touching the published guides, on the snapshot the
    // last frame kept if the retake interval held its retake back.
    function resolveCommit(rawDx, rawDy, axisLock, snapBypass) {
        if (!root.enabled || Boolean(snapBypass) || root._mode !== "move")
            return root._rawMove(rawDx, rawDy);
        return root._guidedMove(rawDx, rawDy, axisLock, true);
    }

    // How far the moving corner of a resize is from where the node's stored rect puts it: the offset a
    // resize snapshot is ranked around, so a trimmed snapshot follows an edge dragged far out. Zero before
    // the session's first snapshot, which gives the stored rect; a snapshot the scene change dropped
    // (invalidateSnapshot) leaves its moving union behind, so the next one is ranked at the corner too.
    function _resizeOffset(rect, spec) {
        var base = root._base;
        if (!base)
            return {"x": 0.0, "y": 0.0};
        var x = spec.movingLeft ? Number(rect.left) - base.left : Number(rect.right) - base.right;
        var y = spec.horizontalOnly
            ? 0.0
            : (spec.movingTop ? Number(rect.top) - base.top : Number(rect.bottom) - base.bottom);
        return {"x": root._finite(x, 0.0), "y": root._finite(y, 0.0)};
    }

    // Resize frame: `rect` {left, top, right, bottom} after the handle's own clamp and aspect lock;
    // spec {movingLeft, movingTop, horizontalOnly, aspectRatio, minWidth, minHeight}. Returns
    // {rect, snappedX, snappedY, lines} and publishes the lines.
    function resolveResize(rect, spec, snapBypass) {
        var raw = {"rect": rect, "snappedX": false, "snappedY": false, "lines": []};
        root._resizeSpec = null;
        var source = spec || {};
        var ready = root.enabled && !Boolean(snapBypass) && root._mode === "resize" && Boolean(rect);
        if (ready) {
            var offset = root._resizeOffset(rect, source);
            ready = root._ensureSnapshot(offset.x, offset.y, false);
        }
        if (!ready) {
            root._publish([], []);
            return raw;
        }
        var settings = {
            "movingLeft": Boolean(source.movingLeft),
            "movingTop": Boolean(source.movingTop),
            "horizontalOnly": Boolean(source.horizontalOnly),
            "aspectRatio": root._finite(source.aspectRatio, 0.0),
            "minWidth": root._finite(source.minWidth, 0.0),
            "minHeight": root._finite(source.minHeight, 0.0),
            "threshold": root.threshold()
        };
        root.profileResolveCount += 1;
        var result = SmartGuideEngine.resolveResize(root._index, rect, settings);
        root._resizeSpec = settings;
        root._publish(result.lines, []);
        return result;
    }

    // Drops the lines whose moving edge a later clamp moved off the guide, so the overlay only shows
    // what `finalRect` satisfies.
    function confirmResize(finalRect) {
        var spec = root._resizeSpec;
        if (root._mode !== "resize" || !spec || !finalRect || !root.lines.length)
            return;
        var tolerance = Math.min(SmartGuideEngine.LINE_TOLERANCE, spec.threshold);
        var xEdge = Number(spec.movingLeft ? finalRect.left : finalRect.right);
        var yEdge = Number(spec.movingTop ? finalRect.top : finalRect.bottom);
        var kept = [];
        for (var i = 0; i < root.lines.length; ++i) {
            var line = root.lines[i];
            var edge = line.axis === "x" ? xEdge : yEdge;
            if (Math.abs(Number(line.value) - edge) <= tolerance)
                kept.push(line);
        }
        if (kept.length !== root.lines.length)
            root._publish(kept, []);
    }
}
