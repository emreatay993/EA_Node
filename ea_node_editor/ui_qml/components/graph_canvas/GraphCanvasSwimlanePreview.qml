import QtQml 2.15

// Live swimlane previews for canvas gestures (the rules live in
// ea_node_editor/ui_qml/graph_scene_mutation/swimlane_ops.py, so a preview is what the commit lands):
// - a lane or pool resize draws its whole pool (the other lanes and what they hold) while the handle is held;
// - a lane dragged in its pool is a reorder: it moves along the stack only, and the lanes it passes make room;
// - any other drag over lanes lights up the lane (or pool) it would drop into and grows the lanes it would grow.
// Previews are written into the canvas's shared liveNodeGeometry map (hosts and edges follow it) in one assignment,
// never for a node of the live drag set; they end with the gesture or at the next scene mutation.
QtObject {
    id: root
    property var sceneState: null
    property var canvasItem: null
    // Lane (or pool) id -> true while a drag would drop into it.
    property var dropTargetLookup: ({})
    property string laneDragLaneId: ""
    property int laneDragIndex: -1
    property int laneDragCurrent: -1
    property int profilePreviewCallCount: 0
    property string _moveSession: ""
    property bool _dropPreviewActive: false
    property var _dropMovingBounds: null
    property var _dropContainerRects: []
    property string _resizeNodeId: ""
    property string _resizeSession: ""
    property var _ownedIds: ({})
    property string _lastPreviewKey: ""
    property int _sessionCounter: 0

    function _bridge() {
        return root.canvasItem ? root.canvasItem.sceneCommandBridge : null;
    }

    function _payload(nodeId) {
        return root.sceneState && nodeId ? root.sceneState.sceneNodePayload(String(nodeId)) : null;
    }

    function _variant(payload) {
        return payload ? String(payload.surface_variant || "") : "";
    }

    function _isSwimlanePayload(payload) {
        var variant = root._variant(payload);
        return variant === "swimlane_pool" || variant === "swimlane_lane";
    }

    function isSwimlaneNode(nodeId) {
        return root._isSwimlanePayload(root._payload(nodeId));
    }

    function _newSession(prefix) {
        root._sessionCounter += 1;
        return prefix + ":" + root._sessionCounter;
    }

    function _rectOf(payload) {
        return {
            "x": Number(payload.x),
            "y": Number(payload.y),
            "width": Number(payload.width),
            "height": Number(payload.height)
        };
    }

    // --- moves --------------------------------------------------------------------------------------------------

    // When a drag freezes its moving set: returns the set to move instead (a lane reorder moves just the lane and
    // what it holds), or null to keep it.
    function beginMove(anchorNodeId, nodeIds) {
        root.endMove();
        if (!root._bridge())
            return null;
        var anchor = root._payload(anchorNodeId);
        if (root._variant(anchor) === "swimlane_lane" && !anchor.collapsed) {
            var owner = root._payload(String(anchor.owner_backdrop_id || ""));
            if (root._variant(owner) === "swimlane_pool" && !owner.collapsed) {
                var laneIds = [];
                root.sceneState._appendBackdropAwareDragNodeIds(laneIds, ({}), String(anchorNodeId));
                root.laneDragLaneId = String(anchorNodeId);
                root._moveSession = root._newSession("lane");
                return laneIds;
            }
        }
        root._beginDropPreview(nodeIds || []);
        return null;
    }

    function _beginDropPreview(nodeIds) {
        var moving = {};
        var bounds = null;
        for (var i = 0; i < nodeIds.length; i++) {
            var payload = root._payload(nodeIds[i]);
            if (!payload)
                continue;
            moving[String(nodeIds[i])] = true;
            var rect = root._rectOf(payload);
            if (!bounds) {
                bounds = {"left": rect.x, "top": rect.y, "right": rect.x + rect.width, "bottom": rect.y + rect.height};
                continue;
            }
            bounds.left = Math.min(bounds.left, rect.x);
            bounds.top = Math.min(bounds.top, rect.y);
            bounds.right = Math.max(bounds.right, rect.x + rect.width);
            bounds.bottom = Math.max(bounds.bottom, rect.y + rect.height);
        }
        var containers = [];
        var backdrops = root.sceneState ? root.sceneState.sceneBackdropNodesModel() : [];
        for (var j = 0; j < backdrops.length; j++) {
            var backdrop = backdrops[j];
            if (!root._isSwimlanePayload(backdrop) || moving[String(backdrop.node_id || "")] || backdrop.collapsed)
                continue;
            containers.push(root._rectOf(backdrop));
        }
        if (!bounds || !containers.length)
            return;
        root._dropMovingBounds = bounds;
        root._dropContainerRects = containers;
        root._dropPreviewActive = true;
        root._moveSession = root._newSession("drop");
    }

    function _dropOverlapsLanes(dx, dy) {
        var bounds = root._dropMovingBounds;
        if (!bounds)
            return false;
        var left = bounds.left + dx;
        var top = bounds.top + dy;
        var right = bounds.right + dx;
        var bottom = bounds.bottom + dy;
        for (var i = 0; i < root._dropContainerRects.length; i++) {
            var rect = root._dropContainerRects[i];
            if (left <= rect.x + rect.width && right >= rect.x && top <= rect.y + rect.height && bottom >= rect.y)
                return true;
        }
        return false;
    }

    function laneReorderActive() {
        return root.laneDragLaneId.length > 0;
    }

    // Once per flushed frame. A lane reorder returns its offset kept on the pool's stack axis; any other move keeps
    // the offset it was given and refreshes the drop preview.
    function resolveMove(dx, dy, nodeIds) {
        var bridge = root._bridge();
        if (root.laneReorderActive()) {
            var lanePreview = root._lanePreview(dx, dy);
            if (!lanePreview)
                return {"dx": 0.0, "dy": 0.0};
            root.laneDragIndex = Number(lanePreview.index);
            root.laneDragCurrent = Number(lanePreview.current);
            root._applyPreview(lanePreview, "lane:" + root.laneDragIndex, null);
            return {"dx": Number(lanePreview.offset[0]), "dy": Number(lanePreview.offset[1])};
        }
        if (!root._dropPreviewActive || !bridge || !bridge.swimlane_drop_preview)
            return {"dx": dx, "dy": dy};
        if (!root._dropOverlapsLanes(dx, dy)) {
            root._clearPreview();
            return {"dx": dx, "dy": dy};
        }
        root.profilePreviewCallCount += 1;
        var preview = bridge.swimlane_drop_preview(nodeIds || [], dx, dy, root._moveSession);
        root._applyPreview(preview, "", preview ? preview.targets : null);
        return {"dx": dx, "dy": dy};
    }

    function _lanePreview(dx, dy) {
        var bridge = root._bridge();
        if (!bridge || !bridge.swimlane_lane_drag_preview)
            return null;
        root.profilePreviewCallCount += 1;
        var preview = bridge.swimlane_lane_drag_preview(root.laneDragLaneId, dx, dy, root._moveSession);
        return preview && preview.offset ? preview : null;
    }

    // The reorder a lane drag that ends on ``anchorNodeId`` at raw offset (dx, dy) commits: {laneId, index, current},
    // or null when that drag was not a lane reorder.
    function laneReorderCommit(anchorNodeId, dx, dy) {
        if (!root.laneReorderActive() || root.laneDragLaneId !== String(anchorNodeId || ""))
            return null;
        var preview = root._lanePreview(Number(dx), Number(dy));
        return {
            "laneId": root.laneDragLaneId,
            "index": preview ? Number(preview.index) : root.laneDragIndex,
            "current": preview ? Number(preview.current) : root.laneDragCurrent
        };
    }

    function endMove() {
        root.laneDragLaneId = "";
        root.laneDragIndex = -1;
        root.laneDragCurrent = -1;
        root._dropPreviewActive = false;
        root._dropMovingBounds = null;
        root._dropContainerRects = [];
        root._moveSession = "";
        root._clearPreview();
    }

    // --- resizes ------------------------------------------------------------------------------------------------

    // Previews a lane or pool resize; false for any other node (the caller previews that node alone).
    function previewResize(nodeId, x, y, width, height, active) {
        var normalized = String(nodeId || "");
        if (!root.isSwimlaneNode(normalized))
            return false;
        if (!active) {
            // The commit (a scene mutation) clears the live map; this covers a release that changed nothing.
            root._resizeNodeId = "";
            root._resizeSession = "";
            Qt.callLater(root._clearPreview);
            return true;
        }
        var bridge = root._bridge();
        if (!bridge || !bridge.swimlane_resize_preview)
            return false;
        if (root._resizeNodeId !== normalized) {
            root._resizeNodeId = normalized;
            root._resizeSession = root._newSession("resize");
        }
        root.profilePreviewCallCount += 1;
        var preview = bridge.swimlane_resize_preview(normalized, x, y, width, height, root._resizeSession);
        if (!preview || !preview.frames || !preview.frames[normalized])
            return false;
        root._applyPreview(preview, "", null);
        return true;
    }

    // --- the shared live map ------------------------------------------------------------------------------------

    function _applyPreview(preview, key, targets) {
        var frames = preview && preview.frames ? preview.frames : ({});
        var positions = preview && preview.positions ? preview.positions : ({});
        root._setDropTargets(targets);
        var previewKey = key.length ? key : JSON.stringify([frames, positions]);
        if (previewKey === root._lastPreviewKey || !root.sceneState)
            return;
        root._lastPreviewKey = previewKey;
        var moving = root.sceneState.liveDragNodeLookup || ({});
        var current = root.sceneState.liveNodeGeometry || ({});
        var next = {};
        for (var existing in current) {
            if (Object.prototype.hasOwnProperty.call(current, existing) && !root._ownedIds[existing])
                next[existing] = current[existing];
        }
        var owned = {};
        for (var frameId in frames) {
            if (!Object.prototype.hasOwnProperty.call(frames, frameId) || moving[frameId])
                continue;
            var frame = frames[frameId];
            next[frameId] = {
                "x": Number(frame[0]),
                "y": Number(frame[1]),
                "width": Number(frame[2]),
                "height": Number(frame[3])
            };
            owned[frameId] = true;
        }
        for (var positionId in positions) {
            if (!Object.prototype.hasOwnProperty.call(positions, positionId) || moving[positionId] || owned[positionId])
                continue;
            var payload = root._payload(positionId);
            if (!payload)
                continue;
            var position = positions[positionId];
            next[positionId] = {
                "x": Number(position[0]),
                "y": Number(position[1]),
                "width": Number(payload.width),
                "height": Number(payload.height)
            };
            owned[positionId] = true;
        }
        root._ownedIds = owned;
        root.sceneState.liveNodeGeometry = next;
        if (root.sceneState._requestEdgeRedraw)
            root.sceneState._requestEdgeRedraw();
    }

    function _setDropTargets(targets) {
        var next = {};
        var list = targets || [];
        for (var i = 0; i < list.length; i++)
            next[String(list[i])] = true;
        var changed = false;
        for (var key in next) {
            if (!root.dropTargetLookup[key])
                changed = true;
        }
        for (var old in root.dropTargetLookup) {
            if (!next[old])
                changed = true;
        }
        if (changed)
            root.dropTargetLookup = next;
    }

    function _clearPreview() {
        root._lastPreviewKey = "";
        root._setDropTargets([]);
        var owned = root._ownedIds;
        root._ownedIds = ({});
        if (!root.sceneState)
            return;
        var current = root.sceneState.liveNodeGeometry || ({});
        var next = {};
        var removed = false;
        for (var key in current) {
            if (!Object.prototype.hasOwnProperty.call(current, key))
                continue;
            if (owned[key]) {
                removed = true;
                continue;
            }
            next[key] = current[key];
        }
        if (!removed)
            return;
        root.sceneState.liveNodeGeometry = next;
        if (root.sceneState._requestEdgeRedraw)
            root.sceneState._requestEdgeRedraw();
    }
}
