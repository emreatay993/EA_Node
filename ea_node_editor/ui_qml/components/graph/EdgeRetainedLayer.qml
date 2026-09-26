// Purpose: Paint visible standard and flow edges as retained Shape delegates, one per edge, from EdgePaintPolicy and EdgeMath facts.
// Map: feature_routes/edge_routing_labels_progress.md
// Tests: tests/test_edge_snapshot_spatial_index.py, tests/test_flow_edge_labels.py

import QtQuick 2.15
import QtQml 2.15
import QtQuick.Shapes
import "EdgeMath.js" as EdgeMath
import "EdgePaintPolicy.js" as EdgePaintPolicy
import "EdgeViewportMath.js" as EdgeViewportMath

Item {
    id: root
    objectName: "graphCanvasEdgeRetainedLayer"
    property Item edgeLayer: null
    property bool rendererSupported: true
    property real profileLastPaintMs: 0.0
    property int profilePaintCount: 0
    property int profileRetainedDelegateCreateCount: 0
    property int profileRetainedDelegateDestroyCount: 0
    property int profileRetainedModelEntryUpdateCount: 0
    property int profileRetainedModelEntrySkipCount: 0
    // Paint state of every visible edge, including those painted by the Canvas overlay.
    property var _paintDiagnosticsByEdgeId: ({})
    property int _paintDiagnosticsRevision: 0
    // Visible edges the Canvas overlay paints instead of a retained delegate, with the reason.
    property var _canvasEdgeReasonById: ({})
    property var _retainedEdgeModel: []
    // Entries are built in screen pixels of this paint transform. It is kept while the zoom is
    // unchanged, so a pan moves the transform layer below instead of rebuilding every delegate;
    // a zoom change, or a pan farther than paintOriginMaxDriftPx, rebases it.
    property real _paintViewportZoom: 1.0
    property real _paintViewportOffsetX: 0.0
    property real _paintViewportOffsetY: 0.0
    property bool _paintViewportValid: false
    property real paintOriginMaxDriftPx: 16384.0
    // Per-edge entry cache: an edge whose inputs are unchanged reuses its entry and paint state.
    property var _entryCacheById: ({})
    property int profileRetainedEntryCacheHitCount: 0
    property int profileRetainedEntryBuildCount: 0
    readonly property var _currentViewportTransform: root.edgeLayer
        ? EdgeViewportMath.viewportTransform(root.edgeLayer)
        : ({"zoom": root._paintViewportZoom, "offsetX": root._paintViewportOffsetX, "offsetY": root._paintViewportOffsetY})
    readonly property real viewportTransformCompensationScale: {
        var paintedZoom = Number(root._paintViewportZoom);
        var currentZoom = Number((root._currentViewportTransform || {}).zoom);
        if (!isFinite(paintedZoom) || paintedZoom <= 0.0001)
            paintedZoom = 1.0;
        if (!isFinite(currentZoom) || currentZoom <= 0.0001)
            currentZoom = paintedZoom;
        return currentZoom / paintedZoom;
    }
    readonly property real viewportTransformCompensationX: {
        var current = root._currentViewportTransform || ({});
        return Number(current.offsetX || 0.0) - root._paintViewportOffsetX * root.viewportTransformCompensationScale;
    }
    readonly property real viewportTransformCompensationY: {
        var current = root._currentViewportTransform || ({});
        return Number(current.offsetY || 0.0) - root._paintViewportOffsetY * root.viewportTransformCompensationScale;
    }
    readonly property int retainedEdgeCount: retainedEdgeModel.count

    ListModel {
        id: retainedEdgeModel
        dynamicRoles: true
    }

    function _recordPaint(startedMs) {
        root.profileLastPaintMs = Math.max(0.0, Date.now() - Number(startedMs || Date.now()));
        root.profilePaintCount += 1;
    }

    function _rememberPaintViewport(viewportTransform) {
        var viewport = viewportTransform || ({});
        var zoom = Number(viewport.zoom);
        root._paintViewportZoom = isFinite(zoom) && zoom > 0.0001 ? zoom : 1.0;
        var offsetX = Number(viewport.offsetX);
        var offsetY = Number(viewport.offsetY);
        root._paintViewportOffsetX = isFinite(offsetX) ? offsetX : 0.0;
        root._paintViewportOffsetY = isFinite(offsetY) ? offsetY : 0.0;
        root._paintViewportValid = true;
    }

    function _paintTransformFor(current) {
        if (!root._paintViewportValid
                || Math.abs(Number(current.zoom) - root._paintViewportZoom) > 1e-9
                || Math.abs(Number(current.offsetX) - root._paintViewportOffsetX) > root.paintOriginMaxDriftPx
                || Math.abs(Number(current.offsetY) - root._paintViewportOffsetY) > root.paintOriginMaxDriftPx)
            root._rememberPaintViewport(current);
        return {
            "zoom": root._paintViewportZoom,
            "offsetX": root._paintViewportOffsetX,
            "offsetY": root._paintViewportOffsetY
        };
    }

    function needsSelectionOverlay(snapshot) {
        // Keep the shared background / node-highlight / direct-selection order
        // when a node-highlight gradient needs the Canvas overlay.
        return Boolean(snapshot && !snapshot.culled && (snapshot.selected || snapshot.previewed
            || (snapshot.activeDataWire && (snapshot.sourceNodeSelected || snapshot.targetNodeSelected))));
    }

    // Why a visible edge paints through the Canvas overlay: "" (retained delegate only),
    // "selection_overlay" (the delegate stays alive but hidden), or a Canvas-only reason:
    // "invalid_type_gradient" (ShapePath has no stroke gradients) or "unsupported_route".
    function canvasOverlayReason(snapshot) {
        if (!snapshot || snapshot.culled || !snapshot.geometry)
            return "";
        var route = String(snapshot.geometry.route || "bezier");
        if (route !== "bezier" && route !== "pipe")
            return "unsupported_route";
        if (snapshot.activeDataWire && Boolean(snapshot.edgeData && snapshot.edgeData.data_type_warning))
            return "invalid_type_gradient";
        return root.needsSelectionOverlay(snapshot) ? "selection_overlay" : "";
    }

    function paintStateForSnapshot(snapshot, zoom) {
        var edge = snapshot.edgeData || ({});
        return snapshot.flowEdge
            ? EdgePaintPolicy.flowEdgePaintState(root.edgeLayer, snapshot, edge, zoom)
            : EdgePaintPolicy.standardEdgePaintState(root.edgeLayer, snapshot, edge, zoom);
    }

    function _svgX(sceneX, viewportTransform, offsetX) {
        return (EdgeViewportMath.sceneXToScreen(sceneX, viewportTransform) + offsetX).toFixed(3);
    }

    function _svgY(sceneY, viewportTransform, offsetY) {
        return (EdgeViewportMath.sceneYToScreen(sceneY, viewportTransform) + offsetY).toFixed(3);
    }

    // SVG path of EdgeMath.edgeBodyPieces in screen pixels, one copy per parallel stroke offset.
    function _svgBodyPath(pieces, viewportTransform, strokeOffsets) {
        var parts = [];
        for (var o = 0; o < strokeOffsets.length; o++) {
            var dx = Number(strokeOffsets[o].x || 0.0);
            var dy = Number(strokeOffsets[o].y || 0.0);
            for (var i = 0; i < pieces.length; i++) {
                var cubic = pieces[i].cubic;
                if (cubic) {
                    parts.push(
                        "M", root._svgX(cubic[0].x, viewportTransform, dx), root._svgY(cubic[0].y, viewportTransform, dy),
                        "C", root._svgX(cubic[1].x, viewportTransform, dx), root._svgY(cubic[1].y, viewportTransform, dy),
                        root._svgX(cubic[2].x, viewportTransform, dx), root._svgY(cubic[2].y, viewportTransform, dy),
                        root._svgX(cubic[3].x, viewportTransform, dx), root._svgY(cubic[3].y, viewportTransform, dy)
                    );
                    continue;
                }
                var points = pieces[i].points || [];
                for (var p = 0; p < points.length; p++) {
                    parts.push(
                        p === 0 ? "M" : "L",
                        root._svgX(points[p].x, viewportTransform, dx),
                        root._svgY(points[p].y, viewportTransform, dy)
                    );
                }
            }
        }
        return parts.join(" ");
    }

    // Flow arrowhead slot: the same outline EdgeArrowPaint.js paints on the Canvas.
    function _flowMarkerSlot(geometry, metrics, atTarget, totalLength, viewportTransform, zoom) {
        if (!metrics)
            return null;
        var frame = EdgeMath.edgeEndMarkerFrame(
            geometry,
            atTarget,
            Number(metrics.extent) + Number(metrics.offset),
            totalLength
        );
        var shape = frame
            ? EdgePaintPolicy.flowArrowMarkerShape(metrics, frame.x, frame.y, frame.dx, frame.dy)
            : null;
        if (!shape)
            return null;
        var parts = [];
        for (var i = 0; i < shape.points.length; i++) {
            parts.push(
                i === 0 ? "M" : "L",
                root._svgX(shape.points[i].x, viewportTransform, 0.0),
                root._svgY(shape.points[i].y, viewportTransform, 0.0)
            );
        }
        if (shape.closed)
            parts.push("Z");
        return {
            "path": parts.join(" "),
            "filled": Boolean(shape.filled),
            "strokeWidth": Math.max(0.01, Number(shape.strokeWidth) || 1.0) * zoom
        };
    }

    // Three half circles facing along the path at one end, as two quarter arcs each.
    function _svgEndpointArcs(frame, viewportTransform) {
        var centerX = EdgeViewportMath.sceneXToScreen(frame.x, viewportTransform);
        var centerY = EdgeViewportMath.sceneYToScreen(frame.y, viewportTransform);
        var radii = EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_RADII_SCREEN_PX;
        var parts = [];
        for (var i = 0; i < radii.length; i++) {
            var radius = Number(radii[i]);
            var r = radius.toFixed(3);
            for (var step = 0; step < 3; step++) {
                var angle = frame.angle + (step - 1) * Math.PI * 0.5;
                var x = (centerX + Math.cos(angle) * radius).toFixed(3);
                var y = (centerY + Math.sin(angle) * radius).toFixed(3);
                if (step === 0)
                    parts.push("M", x, y);
                else
                    parts.push("A", r, r, "0 0 1", x, y);
            }
        }
        return parts.join(" ");
    }

    function _svgDisabledMarker(geometry, viewportTransform) {
        var anchor = EdgeMath.edgeAnchor(geometry, 0.5);
        if (!anchor)
            return "";
        var x = EdgeViewportMath.sceneXToScreen(Number(anchor.x), viewportTransform);
        var y = EdgeViewportMath.sceneYToScreen(Number(anchor.y), viewportTransform);
        var r = EdgePaintPolicy.DISABLED_MARKER_RADIUS_SCREEN_PX;
        return [
            "M", (x - r).toFixed(3), (y - r).toFixed(3), "L", (x + r).toFixed(3), (y + r).toFixed(3),
            "M", (x - r).toFixed(3), (y + r).toFixed(3), "L", (x + r).toFixed(3), (y - r).toFixed(3)
        ].join(" ");
    }

    function _fixed(value, digits) {
        var numeric = Number(value);
        if (!isFinite(numeric))
            numeric = 0.0;
        return numeric.toFixed(digits);
    }

    function _numberArrayKey(values) {
        var parts = [];
        for (var i = 0; i < (values || []).length; i++)
            parts.push(root._fixed(values[i], 3));
        return parts.join(",");
    }

    function _contentKeyForEntry(entry) {
        return [
            entry.selectionOverlay ? "selection-overlay" : "retained",
            root._fixed(entry.opacity, 4),
            entry.bodyPath,
            String(entry.strokeColor || ""),
            root._fixed(entry.strokeWidthScreenPx, 4),
            root._numberArrayKey(entry.dashPattern),
            entry.startMarkerPath,
            String(entry.startMarkerColor || ""),
            entry.startMarkerFilled ? "filled" : "open",
            root._fixed(entry.startMarkerStrokeWidth, 4),
            entry.endMarkerPath,
            String(entry.endMarkerColor || ""),
            entry.endMarkerFilled ? "filled" : "open",
            root._fixed(entry.endMarkerStrokeWidth, 4),
            entry.disabledMarkerPath,
            String(entry.disabledMarkerColor || "")
        ].join("|");
    }

    function _screenStrokeOffsets(geometry, strokeOffsetsScreenPx) {
        var dx = Number(geometry.tx || 0.0) - Number(geometry.sx || 0.0);
        var dy = Number(geometry.ty || 0.0) - Number(geometry.sy || 0.0);
        var length = Math.sqrt(dx * dx + dy * dy);
        var offsets = strokeOffsetsScreenPx || [0.0];
        var result = [];
        for (var i = 0; i < offsets.length; ++i) {
            var offset = Number(offsets[i] || 0.0);
            result.push(length > 1e-6
                ? {"x": -dy * offset / length, "y": dx * offset / length}
                : {"x": 0.0, "y": 0.0});
        }
        return result;
    }

    function _entryForSnapshot(snapshot, paintState, viewportTransform, zoom) {
        var geometry = snapshot.geometry || ({});
        var samplePoints = snapshot.crossingSamplePoints || [];
        var breaks = snapshot.crossingBreaks || [];
        var entry = {
            "edgeId": String(snapshot.edgeId || ""),
            "drawOrderIndex": Number(snapshot.drawOrderIndex || 0),
            "selectionOverlay": root.needsSelectionOverlay(snapshot),
            "opacity": Number(paintState.strokeAlpha || 0.0),
            "bodyPath": "",
            "strokeColor": paintState.strokeColor,
            "strokeWidthScreenPx": Math.max(1.0, Number(paintState.strokeWidthScreenPx || 1.0)),
            "dashed": false,
            "dashPattern": [],
            "startMarkerPath": "",
            "startMarkerColor": paintState.strokeColor,
            "startMarkerFilled": false,
            "startMarkerStrokeWidth": 1.0,
            "endMarkerPath": "",
            "endMarkerColor": paintState.strokeColor,
            "endMarkerFilled": false,
            "endMarkerStrokeWidth": 1.0,
            "disabledMarkerPath": "",
            "disabledMarkerColor": paintState.disabledMarkerColor || paintState.strokeColor
        };
        var dashPattern = EdgePaintPolicy.dashPatternInStrokeWidths(
            paintState.dashPatternScreenPx || [],
            paintState.strokeWidthScreenPx
        );
        entry.dashed = dashPattern.length > 0;
        entry.dashPattern = dashPattern;
        if (paintState.flowEdge) {
            entry.bodyPath = root._svgBodyPath(
                EdgeMath.edgeBodyPieces(
                    geometry,
                    samplePoints,
                    breaks,
                    paintState.lineTrimStart,
                    paintState.lineTrimEnd
                ),
                viewportTransform,
                [{"x": 0.0, "y": 0.0}]
            );
            var markers = paintState.markers || ({});
            var totalLength = markers.start || markers.end ? EdgeMath.geometryLength(geometry) : 0.0;
            var startMarker = root._flowMarkerSlot(geometry, markers.start, false, totalLength, viewportTransform, zoom);
            var endMarker = root._flowMarkerSlot(geometry, markers.end, true, totalLength, viewportTransform, zoom);
            if (startMarker) {
                entry.startMarkerPath = startMarker.path;
                entry.startMarkerFilled = startMarker.filled;
                entry.startMarkerStrokeWidth = startMarker.strokeWidth;
            }
            if (endMarker) {
                entry.endMarkerPath = endMarker.path;
                entry.endMarkerFilled = endMarker.filled;
                entry.endMarkerStrokeWidth = endMarker.strokeWidth;
            }
        } else if (paintState.endpointArcsVisible) {
            // Hidden wires show only their endpoint arcs.
            var frames = EdgeMath.endpointArcFrames(
                geometry,
                EdgeViewportMath.screenLengthToScene(4.0, viewportTransform)
            );
            var arcColors = EdgePaintPolicy.hiddenEndpointArcColors(root.edgeLayer, paintState);
            entry.opacity = EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_ALPHA;
            if (frames) {
                entry.startMarkerPath = root._svgEndpointArcs(frames.source, viewportTransform);
                entry.endMarkerPath = root._svgEndpointArcs(frames.target, viewportTransform);
            }
            entry.startMarkerColor = arcColors.source;
            entry.endMarkerColor = arcColors.target;
            entry.startMarkerStrokeWidth = EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_STROKE_WIDTH_SCREEN_PX;
            entry.endMarkerStrokeWidth = EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_STROKE_WIDTH_SCREEN_PX;
        } else if (paintState.bodyVisible) {
            entry.bodyPath = root._svgBodyPath(
                EdgeMath.edgeBodyPieces(geometry, samplePoints, breaks, 0.0, 0.0),
                viewportTransform,
                root._screenStrokeOffsets(geometry, paintState.strokeOffsetsScreenPx || [0.0])
            );
        }
        // The X shares the body's alpha: the policy fades both only for faint wires.
        if (paintState.disabledMarkerVisible)
            entry.disabledMarkerPath = root._svgDisabledMarker(geometry, viewportTransform);
        entry.contentKey = root._contentKeyForEntry(entry);
        return entry;
    }

    function clearRetainedPaint() {
        root._retainedEdgeModel = [];
        retainedEdgeModel.clear();
        root._rowEdgeIds = [];
        root._rowContentKeys = [];
        root._rowDrawOrders = [];
        root._paintDiagnosticsByEdgeId = ({});
        root._canvasEdgeReasonById = ({});
        root._entryCacheById = ({});
        root._paintViewportValid = false;
        root._paintDiagnosticsRevision += 1;
    }

    // Snapshot facts an entry depends on besides the edge payload, geometry, output previews,
    // theme, and paint transform, which the cache compares by identity or revision.
    function _snapshotStateKey(snapshot) {
        var parts = [
            snapshot.selected ? "s" : "-",
            snapshot.previewed ? "p" : "-",
            snapshot.replacementPreviewed ? "r" : "-",
            snapshot.sourceNodeSelected ? "a" : "-",
            snapshot.targetNodeSelected ? "b" : "-",
            snapshot.hiddenUnrevealed ? "h" : "-",
            root.edgeLayer.wireSelectionModeHeld ? "w" : "-"
        ];
        var breaks = snapshot.crossingBreaks || [];
        for (var i = 0; i < breaks.length; i++)
            parts.push(root._fixed(breaks[i].startDistance, 3), root._fixed(breaks[i].endDistance, 3));
        return parts.join("|");
    }

    function _cachedRecordFor(cached, snapshot, transformKey, stateKey) {
        return Boolean(cached
            && cached.edgeData === snapshot.edgeData
            && cached.geometry === snapshot.geometry
            && cached.previewLookup === root.edgeLayer.outputPreviewLookup
            && cached.themeRevision === root.edgeLayer._themeRevision
            && cached.transformKey === transformKey
            && cached.stateKey === stateKey);
    }

    // Row edge ids, content keys, and draw orders mirroring retainedEdgeModel, so the sync
    // never reads the model back.
    property var _rowEdgeIds: []
    property var _rowContentKeys: []
    property var _rowDrawOrders: []

    function _setRetainedModelEntry(row, entry) {
        if (root._rowDrawOrders[row] !== entry.drawOrderIndex) {
            retainedEdgeModel.setProperty(row, "drawOrderIndex", entry.drawOrderIndex);
            root._rowDrawOrders[row] = entry.drawOrderIndex;
        }
        if (root._rowEdgeIds[row] === entry.edgeId && root._rowContentKeys[row] === entry.contentKey) {
            root.profileRetainedModelEntrySkipCount += 1;
            return;
        }
        if (root._rowEdgeIds[row] !== entry.edgeId) {
            retainedEdgeModel.setProperty(row, "edgeId", entry.edgeId);
            root._rowEdgeIds[row] = entry.edgeId;
        }
        retainedEdgeModel.setProperty(row, "edgeEntry", entry);
        root._rowContentKeys[row] = entry.contentKey;
        root.profileRetainedModelEntryUpdateCount += 1;
    }

    // Rows stay where they are: z comes from each row's draw order, so an edge that scrolls
    // out of view hands its row, and its live Shape delegate, to an edge scrolling in.
    function _syncRetainedEdgeModel(entries) {
        var source = entries || [];
        var rowIds = root._rowEdgeIds;
        var rowById = {};
        for (var row = 0; row < rowIds.length; row++)
            rowById[rowIds[row]] = row;
        var nextIds = {};
        for (var i = 0; i < source.length; i++)
            nextIds[source[i].edgeId] = true;
        var freeRows = [];
        for (row = 0; row < rowIds.length; row++) {
            if (!nextIds[rowIds[row]])
                freeRows.push(row);
        }
        var arrivals = [];
        for (i = 0; i < source.length; i++) {
            var existingRow = rowById[source[i].edgeId];
            if (existingRow === undefined)
                arrivals.push(source[i]);
            else
                root._setRetainedModelEntry(existingRow, source[i]);
        }
        for (i = 0; i < arrivals.length; i++) {
            var entry = arrivals[i];
            if (i < freeRows.length) {
                root._setRetainedModelEntry(freeRows[i], entry);
                continue;
            }
            retainedEdgeModel.append({
                "edgeId": entry.edgeId, "edgeEntry": entry, "drawOrderIndex": entry.drawOrderIndex
            });
            rowIds.push(entry.edgeId);
            root._rowContentKeys.push(entry.contentKey);
            root._rowDrawOrders.push(entry.drawOrderIndex);
        }
        for (var unused = freeRows.length - 1; unused >= arrivals.length; unused--) {
            var removedRow = freeRows[unused];
            retainedEdgeModel.remove(removedRow);
            rowIds.splice(removedRow, 1);
            root._rowContentKeys.splice(removedRow, 1);
            root._rowDrawOrders.splice(removedRow, 1);
        }
    }

    function requestRetainedPaint() {
        var startedMs = Date.now();
        if (!root.edgeLayer) {
            root.clearRetainedPaint();
            root._recordPaint(startedMs);
            return;
        }
        var snapshots = root.edgeLayer._visibleEdgeSnapshots || [];
        var paintTransform = root._paintTransformFor(EdgeViewportMath.viewportTransform(root.edgeLayer));
        var zoom = paintTransform.zoom;
        var transformKey = [
            root._fixed(paintTransform.zoom, 6),
            root._fixed(paintTransform.offsetX, 3),
            root._fixed(paintTransform.offsetY, 3)
        ].join("|");
        var previousCache = root._entryCacheById || ({});
        var nextCache = {};
        var retainedModel = [];
        var diagnosticsByEdgeId = {};
        var canvasEdgeReasonById = {};
        for (var i = 0; i < snapshots.length; i++) {
            var snapshot = snapshots[i];
            if (!snapshot || snapshot.culled || !snapshot.geometry)
                continue;
            var edgeId = String(snapshot.edgeId || "");
            var stateKey = root._snapshotStateKey(snapshot);
            var record = previousCache[edgeId];
            if (root._cachedRecordFor(record, snapshot, transformKey, stateKey)) {
                root.profileRetainedEntryCacheHitCount += 1;
            } else {
                var paintState = root.paintStateForSnapshot(snapshot, zoom);
                var reason = root.canvasOverlayReason(snapshot);
                var canvasOnly = Boolean(reason && reason !== "selection_overlay");
                record = {
                    "edgeData": snapshot.edgeData,
                    "geometry": snapshot.geometry,
                    "previewLookup": root.edgeLayer.outputPreviewLookup,
                    "themeRevision": root.edgeLayer._themeRevision,
                    "transformKey": transformKey,
                    "stateKey": stateKey,
                    "paintState": paintState,
                    "reason": reason,
                    "entry": canvasOnly ? null : root._entryForSnapshot(snapshot, paintState, paintTransform, zoom)
                };
                root.profileRetainedEntryBuildCount += 1;
            }
            nextCache[edgeId] = record;
            diagnosticsByEdgeId[edgeId] = record.paintState;
            if (!record.entry) {
                canvasEdgeReasonById[edgeId] = record.reason;
                continue;
            }
            record.entry.drawOrderIndex = Number(snapshot.drawOrderIndex || 0);
            retainedModel.push(record.entry);
        }
        root._entryCacheById = nextCache;
        root._retainedEdgeModel = retainedModel;
        root._syncRetainedEdgeModel(retainedModel);
        root._paintDiagnosticsByEdgeId = diagnosticsByEdgeId;
        root._canvasEdgeReasonById = canvasEdgeReasonById;
        root._paintDiagnosticsRevision += 1;
        root._recordPaint(startedMs);
    }

    Item {
        id: retainedTransformLayer
        objectName: "graphCanvasEdgeRetainedTransformLayer"
        width: root.width
        height: root.height
        transformOrigin: Item.TopLeft
        x: root.viewportTransformCompensationX
        y: root.viewportTransformCompensationY
        scale: root.viewportTransformCompensationScale

        Repeater {
            model: retainedEdgeModel
            // One Shape per edge. CurveRenderer antialiases on GPU backends like the Canvas does.
            delegate: Shape {
                id: retainedEdgeDelegate
                property var edgeEntry: model.edgeEntry || ({})
                z: Number(model.drawOrderIndex || 0)
                visible: !edgeEntry.selectionOverlay
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                opacity: Math.max(0.0, Math.min(1.0, Number(edgeEntry.opacity || 0.0)))
                Component.onCompleted: root.profileRetainedDelegateCreateCount += 1
                Component.onDestruction: root.profileRetainedDelegateDestroyCount += 1

                ShapePath {
                    fillColor: "transparent"
                    strokeColor: retainedEdgeDelegate.edgeEntry.bodyPath
                        ? retainedEdgeDelegate.edgeEntry.strokeColor
                        : "transparent"
                    strokeWidth: Number(retainedEdgeDelegate.edgeEntry.strokeWidthScreenPx || 1.0)
                    capStyle: ShapePath.RoundCap
                    joinStyle: ShapePath.RoundJoin
                    strokeStyle: retainedEdgeDelegate.edgeEntry.dashed
                        ? ShapePath.DashLine
                        : ShapePath.SolidLine
                    dashPattern: retainedEdgeDelegate.edgeEntry.dashPattern || []
                    PathSvg {
                        // Pieces restart the dash pattern; corners inside a piece keep its phase.
                        path: retainedEdgeDelegate.edgeEntry.bodyPath || ""
                    }
                }

                ShapePath {
                    fillColor: retainedEdgeDelegate.edgeEntry.startMarkerFilled
                        ? retainedEdgeDelegate.edgeEntry.startMarkerColor
                        : "transparent"
                    strokeColor: retainedEdgeDelegate.edgeEntry.startMarkerPath
                        ? retainedEdgeDelegate.edgeEntry.startMarkerColor
                        : "transparent"
                    strokeWidth: Number(retainedEdgeDelegate.edgeEntry.startMarkerStrokeWidth || 1.0)
                    capStyle: ShapePath.RoundCap
                    joinStyle: ShapePath.RoundJoin
                    PathSvg { path: retainedEdgeDelegate.edgeEntry.startMarkerPath || "" }
                }

                ShapePath {
                    fillColor: retainedEdgeDelegate.edgeEntry.endMarkerFilled
                        ? retainedEdgeDelegate.edgeEntry.endMarkerColor
                        : "transparent"
                    strokeColor: retainedEdgeDelegate.edgeEntry.endMarkerPath
                        ? retainedEdgeDelegate.edgeEntry.endMarkerColor
                        : "transparent"
                    strokeWidth: Number(retainedEdgeDelegate.edgeEntry.endMarkerStrokeWidth || 1.0)
                    capStyle: ShapePath.RoundCap
                    joinStyle: ShapePath.RoundJoin
                    PathSvg { path: retainedEdgeDelegate.edgeEntry.endMarkerPath || "" }
                }

                ShapePath {
                    fillColor: "transparent"
                    strokeColor: retainedEdgeDelegate.edgeEntry.disabledMarkerPath
                        ? retainedEdgeDelegate.edgeEntry.disabledMarkerColor
                        : "transparent"
                    strokeWidth: EdgePaintPolicy.DISABLED_MARKER_STROKE_WIDTH_SCREEN_PX
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: retainedEdgeDelegate.edgeEntry.disabledMarkerPath || "" }
                }
            }
        }
    }
}
