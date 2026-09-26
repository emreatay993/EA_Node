import QtQuick 2.15
import "EdgeArrowPaint.js" as EdgeArrowPaint
import "EdgeMath.js" as EdgeMath
import "EdgePaintPolicy.js" as EdgePaintPolicy
import "EdgeViewportMath.js" as EdgeViewportMath

Item {
    id: root
    objectName: "graphCanvasEdgeCanvasLayer"
    property Item edgeLayer: null
    property var paintSnapshots: edgeLayer ? edgeLayer._visibleEdgeSnapshots : []
    readonly property var canvasStateBridgeRef: root.edgeLayer
        && root.edgeLayer.sceneBridge
        ? root.edgeLayer.sceneBridge
        : null
    property real profileLastPaintMs: 0.0
    property int profilePaintCount: 0
    property var _paintDiagnosticsByEdgeId: ({})
    property int _paintDiagnosticsRevision: 0
    property real _paintViewportZoom: 1.0
    property real _paintViewportOffsetX: 0.0
    property real _paintViewportOffsetY: 0.0
    readonly property var _currentViewportTransform: root.edgeLayer
        ? EdgeViewportMath.viewportTransform(root.edgeLayer)
        : ({"zoom": root._paintViewportZoom, "offsetX": root._paintViewportOffsetX, "offsetY": root._paintViewportOffsetY})
    readonly property int effectiveGraphLabelPixelSize: {
        var numeric = NaN;
        if (root.canvasStateBridgeRef)
            numeric = Number(root.canvasStateBridgeRef.graphics_graph_label_pixel_size);
        if (root.edgeLayer
                && root.edgeLayer.parent
                && root.edgeLayer.parent.canvasItem
                && root.edgeLayer.parent.canvasItem.prefs) {
            numeric = Number(root.edgeLayer.parent.canvasItem.prefs.graphLabelPixelSize);
        }
        if (!isFinite(numeric) && root.edgeLayer && root.edgeLayer.graphLabelPixelSize !== undefined)
            numeric = Number(root.edgeLayer.graphLabelPixelSize);
        if (!isFinite(numeric))
            numeric = 10;
        return Math.max(8, Math.min(18, Math.round(numeric)));
    }
    readonly property var graphSharedTypography: edgeLabelGapTypography
    readonly property bool viewportTransformCompensationActive: root.edgeLayer
        ? Boolean(root.edgeLayer._viewStateRedrawDirty)
        : false
    readonly property real viewportTransformCompensationScale: {
        if (!root.viewportTransformCompensationActive)
            return 1.0;
        var paintedZoom = Number(root._paintViewportZoom);
        var currentZoom = Number((root._currentViewportTransform || {}).zoom);
        if (!isFinite(paintedZoom) || paintedZoom <= 0.0001)
            paintedZoom = 1.0;
        if (!isFinite(currentZoom) || currentZoom <= 0.0001)
            currentZoom = paintedZoom;
        return currentZoom / paintedZoom;
    }
    readonly property real viewportTransformCompensationX: {
        if (!root.viewportTransformCompensationActive)
            return 0.0;
        var current = root._currentViewportTransform || ({});
        return Number(current.offsetX || 0.0) - root._paintViewportOffsetX * root.viewportTransformCompensationScale;
    }
    readonly property real viewportTransformCompensationY: {
        if (!root.viewportTransformCompensationActive)
            return 0.0;
        var current = root._currentViewportTransform || ({});
        return Number(current.offsetY || 0.0) - root._paintViewportOffsetY * root.viewportTransformCompensationScale;
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
    }
    function clearCanvasPaintDiagnostics() {
        root._paintDiagnosticsByEdgeId = ({});
        root._paintDiagnosticsRevision += 1;
    }
    function standardStrokeOffsetVector(geometry, offsetScreenPx, viewportTransform) {
        var dx = Number(geometry.tx || 0.0) - Number(geometry.sx || 0.0);
        var dy = Number(geometry.ty || 0.0) - Number(geometry.sy || 0.0);
        var length = Math.sqrt(dx * dx + dy * dy);
        if (!isFinite(length) || length <= 1e-6)
            return {"x": 0.0, "y": 0.0};
        // Signed: parallel strokes sit on both sides of the path (screenLengthToScene clamps at 0).
        var sceneOffset = Number(offsetScreenPx || 0.0) / viewportTransform.zoom;
        return {"x": -dy * sceneOffset / length, "y": dx * sceneOffset / length};
    }
    function drawDragConnectionMarker(ctx, geometry, markerText, strokeColor, viewportTransform, plain) {
        if (!ctx || !geometry || !String(markerText || "").length)
            return;
        var dx = Number(geometry.tx || 0.0) - Number(geometry.sx || 0.0);
        var dy = Number(geometry.ty || 0.0) - Number(geometry.sy || 0.0);
        var length = Math.sqrt(dx * dx + dy * dy);
        if (!isFinite(length) || length <= 1e-6)
            return;
        var lead = EdgeViewportMath.screenLengthToScene(16.0, viewportTransform);
        var radius = EdgeViewportMath.screenLengthToScene(7.0, viewportTransform);
        var centerX = Number(geometry.tx) - dx * lead / length;
        var centerY = Number(geometry.ty) - dy * lead / length;
        ctx.save();
        ctx.setLineDash([]);
        if (!plain) {
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0.0, Math.PI * 2.0);
            ctx.fillStyle = String(root.shellPalette.canvas_bg || "#151821");
            ctx.fill();
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = EdgeViewportMath.screenLengthToScene(1.5, viewportTransform);
            ctx.stroke();
        }
        ctx.fillStyle = strokeColor;
        ctx.font = "600 " + EdgeViewportMath.screenLengthToScene(plain ? 13.0 : 10.0, viewportTransform) + "px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(markerText), centerX, centerY);
        ctx.restore();
    }
    // Traces EdgeMath.edgeBodyPieces: one connected sub-path per piece.
    function traceBodyPieces(ctx, pieces) {
        var source = pieces || [];
        for (var i = 0; i < source.length; i++) {
            var cubic = source[i].cubic;
            if (cubic) {
                ctx.moveTo(cubic[0].x, cubic[0].y);
                ctx.bezierCurveTo(cubic[1].x, cubic[1].y, cubic[2].x, cubic[2].y, cubic[3].x, cubic[3].y);
                continue;
            }
            var points = source[i].points || [];
            for (var j = 0; j < points.length; j++) {
                if (j === 0)
                    ctx.moveTo(points[j].x, points[j].y);
                else
                    ctx.lineTo(points[j].x, points[j].y);
            }
        }
    }

    function traceGeometry(ctx, geometry) {
        root.traceBodyPieces(ctx, EdgeMath.edgeBodyPieces(geometry, [], [], 0.0, 0.0));
    }

    function standardEdgeStrokeStyle(ctx, geometry, paintState) {
        if (!ctx || !geometry || !paintState || paintState.gradientKind === "none")
            return paintState ? paintState.strokeColor : root.edgeLayer.fallbackStrokeColor;
        var gradient = ctx.createLinearGradient(
            Number(geometry.sx),
            Number(geometry.sy),
            Number(geometry.tx),
            Number(geometry.ty)
        );
        var sampled = EdgeMath.sampleGeometryPolyline(geometry, 12.0);
        var totalLength = EdgeMath.polylineMetrics(sampled).totalLength;
        var viewport = root.edgeLayer ? EdgeViewportMath.viewportTransform(root.edgeLayer) : ({"zoom": 1.0});
        var fadeScene = EdgeViewportMath.screenLengthToScene(96.0, viewport);
        var fadeRatio = totalLength > 1e-6
            ? Math.max(0.02, Math.min(0.5, fadeScene / totalLength))
            : 0.5;
        var stops = EdgePaintPolicy.standardEdgeGradientStops(root.edgeLayer, paintState, fadeRatio);
        for (var i = 0; i < stops.length; i++)
            gradient.addColorStop(Number(stops[i].position), stops[i].color);
        return gradient;
    }

    function drawHiddenEndpointArcs(ctx, geometry, paintState, viewportTransform) {
        var frames = EdgeMath.endpointArcFrames(
            geometry,
            EdgeViewportMath.screenLengthToScene(4.0, viewportTransform)
        );
        if (!frames)
            return;
        var colors = EdgePaintPolicy.hiddenEndpointArcColors(root.edgeLayer, paintState);
        ctx.save();
        ctx.globalAlpha = EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_ALPHA;
        ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
            EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_STROKE_WIDTH_SCREEN_PX,
            viewportTransform
        );
        ctx.lineCap = "round";
        ctx.setLineDash([]);
        var radii = root.hiddenEndpointArcRadiiScreenPx();
        for (var i = 0; i < radii.length; i++) {
            var radius = EdgeViewportMath.screenLengthToScene(Number(radii[i]), viewportTransform);
            ctx.strokeStyle = colors.source;
            ctx.beginPath();
            ctx.arc(
                frames.source.x,
                frames.source.y,
                radius,
                frames.source.angle - Math.PI * 0.5,
                frames.source.angle + Math.PI * 0.5
            );
            ctx.stroke();
            ctx.strokeStyle = colors.target;
            ctx.beginPath();
            ctx.arc(
                frames.target.x,
                frames.target.y,
                radius,
                frames.target.angle - Math.PI * 0.5,
                frames.target.angle + Math.PI * 0.5
            );
            ctx.stroke();
        }
        ctx.restore();
    }

    function hiddenEndpointArcRadiiScreenPx() {
        return EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_RADII_SCREEN_PX;
    }

    function drawDisabledMarker(ctx, geometry, strokeColor, strokeAlpha, viewportTransform) {
        var anchor = EdgeMath.edgeAnchor(geometry, 0.5);
        if (!anchor)
            return;
        var radius = EdgeViewportMath.screenLengthToScene(
            EdgePaintPolicy.DISABLED_MARKER_RADIUS_SCREEN_PX,
            viewportTransform
        );
        ctx.save();
        ctx.globalAlpha = Number(strokeAlpha || 1.0);
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
            EdgePaintPolicy.DISABLED_MARKER_STROKE_WIDTH_SCREEN_PX,
            viewportTransform
        );
        ctx.lineCap = "round";
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(anchor.x - radius, anchor.y - radius);
        ctx.lineTo(anchor.x + radius, anchor.y + radius);
        ctx.moveTo(anchor.x - radius, anchor.y + radius);
        ctx.lineTo(anchor.x + radius, anchor.y - radius);
        ctx.stroke();
        ctx.restore();
    }

    function drawFlowArrowMarkers(ctx, geometry, markers, strokeColor) {
        if (!markers || (!markers.start && !markers.end))
            return;
        var total = EdgeMath.geometryLength(geometry);
        var ends = [
            {"metrics": markers.start, "atTarget": false},
            {"metrics": markers.end, "atTarget": true}
        ];
        for (var i = 0; i < ends.length; i++) {
            var metrics = ends[i].metrics;
            if (!metrics)
                continue;
            var frame = EdgeMath.edgeEndMarkerFrame(
                geometry,
                ends[i].atTarget,
                Number(metrics.extent) + Number(metrics.offset),
                total
            );
            if (!frame)
                continue;
            EdgeArrowPaint.paintMarkerShape(
                ctx,
                EdgePaintPolicy.flowArrowMarkerShape(metrics, frame.x, frame.y, frame.dx, frame.dy),
                strokeColor
            );
        }
    }

    function decorationEnabled() {
        return root.edgeLayer.edgeCrossingStyle === "gap_break";
    }

    function shouldReuseCrossingMetadata() {
        return root.edgeLayer.edgeCrossingStyle === "gap_break"
            && root.edgeLayer.viewportInteractionActive;
    }

    function _resetSnapshot(snapshot, preserveCrossingMetadata) {
        if (!snapshot)
            return;
        if (!preserveCrossingMetadata) {
            snapshot.crossingBreaks = [];
            snapshot.crossingSamplePoints = [];
        }
        snapshot.drawOrderIndex = -1;
    }

    function orderSnapshotsForDraw(snapshots, preserveCrossingMetadata) {
        var background = [];
        var emphasized = [];
        var elevated = [];
        var sourceSnapshots = snapshots || [];
        var preserve = Boolean(preserveCrossingMetadata);
        for (var i = 0; i < sourceSnapshots.length; i++) {
            var snapshot = sourceSnapshots[i];
            if (!snapshot)
                continue;
            _resetSnapshot(snapshot, preserve);
            if (snapshot.previewed || snapshot.selected)
                elevated.push(snapshot);
            else if (snapshot.activeDataWire
                    && (snapshot.sourceNodeSelected
                        || snapshot.targetNodeSelected
                        || Boolean(snapshot.edgeData && snapshot.edgeData.data_type_warning)))
                emphasized.push(snapshot);
            else
                background.push(snapshot);
        }
        var ordered = background.concat(emphasized).concat(elevated);
        for (i = 0; i < ordered.length; i++)
            ordered[i].drawOrderIndex = i;
        return ordered;
    }

    function _samplingModelForSnapshot(snapshot, viewportTransform) {
        if (!snapshot || snapshot.culled || !snapshot.geometry)
            return null;
        if (snapshot.displayMode === "hidden")
            return null;
        var sceneStep = EdgeViewportMath.screenLengthToScene(root.edgeLayer.edgeCrossingSampleStepScreenPx, viewportTransform);
        var points = EdgeMath.sampleGeometryPolyline(snapshot.geometry, sceneStep);
        var metrics = EdgeMath.polylineMetrics(points);
        if (!metrics.points.length || !metrics.segments.length || !metrics.bounds)
            return null;
        snapshot.crossingSamplePoints = metrics.points;
        return {"snapshot": snapshot, "points": metrics.points, "metrics": metrics};
    }

    function _snapshotNeedsLabelBreak(snapshot) {
        if (!snapshot || snapshot.culled || !snapshot.geometry || !snapshot.flowEdge)
            return false;
        if (!snapshot.labelAnchorScene)
            return false;
        if (String(snapshot.labelMode || "hidden") === "hidden")
            return false;
        return String(snapshot.labelText || "").trim().length > 0;
    }

    function _hasLabelBreakCandidates(snapshots) {
        var source = snapshots || [];
        for (var i = 0; i < source.length; i++) {
            if (root._snapshotNeedsLabelBreak(source[i]))
                return true;
        }
        return false;
    }

    function _flowLabelScale(viewportTransform) {
        if (!root.edgeLayer)
            return 1.0;
        var zoom = Number((viewportTransform || {}).zoom);
        var threshold = Number(root.edgeLayer.flowLabelHideZoomThreshold);
        if (!isFinite(zoom) || !isFinite(threshold) || threshold <= 0.0 || zoom >= threshold)
            return 1.0;
        return Math.max(0.35, Math.min(1.0, zoom / threshold));
    }

    function _flowLabelMeasuredSize(labelText, labelMode) {
        var pillMode = String(labelMode || "hidden") === "pill";
        labelGapMeasure.font.pixelSize = pillMode
            ? root.graphSharedTypography.edgePillPixelSize
            : root.graphSharedTypography.edgeLabelPixelSize;
        labelGapMeasure.font.weight = pillMode
            ? root.graphSharedTypography.edgePillFontWeight
            : root.graphSharedTypography.edgeLabelFontWeight;
        labelGapMeasure.maximumTextWidth = EdgePaintPolicy.flowLabelMaximumTextWidth(pillMode);
        labelGapMeasure.text = String(labelText || "").length ? String(labelText || "") : "M";
        var horizontalPadding = pillMode ? 10.0 : 8.0;
        var verticalPadding = pillMode ? 6.0 : 3.0;
        return {
            "width": Math.ceil(labelGapMeasure.width) + horizontalPadding * 2.0,
            "height": Math.ceil(labelGapMeasure.height) + verticalPadding * 2.0
        };
    }

    function _labelAnchorForSnapshot(snapshot) {
        if (root.edgeLayer
                && root.edgeLayer.labelDragEdgeId
                && root.edgeLayer.labelDragEdgeId === snapshot.edgeId
                && root.edgeLayer.labelDragAnchorScene)
            return root.edgeLayer.labelDragAnchorScene;
        return snapshot.labelAnchorScene || ({});
    }

    function _labelBreakRangeForModel(model, viewportTransform) {
        if (!model || !root._snapshotNeedsLabelBreak(model.snapshot))
            return null;
        var snapshot = model.snapshot;
        var anchor = root._labelAnchorForSnapshot(snapshot);
        var centerDistance = EdgeMath.nearestDistanceAlongPolyline(model.metrics, anchor.x, anchor.y);
        if (!isFinite(centerDistance))
            return null;
        var labelSize = root._flowLabelMeasuredSize(snapshot.labelText, snapshot.labelMode);
        var labelScale = root._flowLabelScale(viewportTransform);
        var tangentX = Number(anchor.dx);
        var tangentY = Number(anchor.dy);
        if (!isFinite(tangentX) || !isFinite(tangentY)) {
            var centerFraction = model.metrics.totalLength > 1e-6 ? centerDistance / model.metrics.totalLength : 0.5;
            var tangent = EdgeMath.pointTangentAlongPolyline(model.points, centerFraction);
            tangentX = tangent ? Number(tangent.dx) : 1.0;
            tangentY = tangent ? Number(tangent.dy) : 0.0;
        }
        var widthScreen = Number(labelSize.width) * labelScale;
        var heightScreen = Number(labelSize.height) * labelScale;
        // Project the (possibly path-rotated) label box onto the tangent.
        var rotation = Number(anchor.rotation || 0.0) * Math.PI / 180.0;
        var axisX = Math.cos(rotation);
        var axisY = Math.sin(rotation);
        var halfGapScreen = Math.abs(tangentX * axisX + tangentY * axisY) * widthScreen * 0.5
            + Math.abs(-tangentX * axisY + tangentY * axisX) * heightScreen * 0.5
            + 3.0;
        var halfGapScene = EdgeViewportMath.screenLengthToScene(Math.max(6.0, halfGapScreen), viewportTransform);
        return {
            "startDistance": centerDistance - halfGapScene,
            "endDistance": centerDistance + halfGapScene
        };
    }

    function _applyLabelBreakMetadata(samplingModels, viewportTransform, mergeGapScene) {
        var models = samplingModels || [];
        for (var i = 0; i < models.length; i++) {
            var model = models[i];
            var labelBreak = root._labelBreakRangeForModel(model, viewportTransform);
            if (!labelBreak)
                continue;
            var rawRanges = (model.snapshot.crossingBreaks || []).concat([labelBreak]);
            var merged = EdgeMath.mergeBreakRanges(rawRanges, mergeGapScene, model.metrics.totalLength);
            model.snapshot.crossingBreaks = root._enrichedBreakRanges(merged, model.points, model.metrics.totalLength);
        }
    }

    function _rawBreakRangesForPair(underModel, overModel, gapHalfScene, anchorMarginScene) {
        var ranges = [];
        if (!underModel || !overModel)
            return ranges;
        var underMetrics = underModel.metrics;
        var overMetrics = overModel.metrics;
        if (!EdgeMath.rectsIntersect(underMetrics.bounds, overMetrics.bounds))
            return ranges;
        var underSegments = underMetrics.segments || [];
        var overSegments = overMetrics.segments || [];
        for (var i = 0; i < underSegments.length; i++) {
            var underSegment = underSegments[i];
            for (var j = 0; j < overSegments.length; j++) {
                var overSegment = overSegments[j];
                if (!EdgeMath.rectsIntersect(underSegment.bounds, overSegment.bounds))
                    continue;
                var intersection = EdgeMath.segmentIntersection(underSegment.a, underSegment.b, overSegment.a, overSegment.b);
                if (!intersection)
                    continue;
                var underDistance = underSegment.startDistance + underSegment.length * intersection.tA;
                var overDistance = overSegment.startDistance + overSegment.length * intersection.tB;
                if (EdgeMath.distanceNearPolylineEndpoints(underDistance, underMetrics.totalLength, anchorMarginScene))
                    continue;
                if (EdgeMath.distanceNearPolylineEndpoints(overDistance, overMetrics.totalLength, anchorMarginScene))
                    continue;
                ranges.push({
                    "startDistance": underDistance - gapHalfScene,
                    "endDistance": underDistance + gapHalfScene
                });
            }
        }
        return ranges;
    }

    function _enrichedBreakRanges(ranges, points, totalLength) {
        var enriched = [];
        var mergedRanges = ranges || [];
        for (var i = 0; i < mergedRanges.length; i++) {
            var range = mergedRanges[i];
            var centerDistance = (Number(range.startDistance) + Number(range.endDistance)) * 0.5;
            var fraction = totalLength > 1e-6 ? centerDistance / totalLength : 0.5;
            var tangent = EdgeMath.pointTangentAlongPolyline(points, fraction);
            enriched.push({
                "startDistance": Number(range.startDistance),
                "endDistance": Number(range.endDistance),
                "centerDistance": centerDistance,
                "centerX": tangent ? Number(tangent.x) : 0.0,
                "centerY": tangent ? Number(tangent.y) : 0.0,
                "tangentX": tangent ? Number(tangent.dx) : 1.0,
                "tangentY": tangent ? Number(tangent.dy) : 0.0
            });
        }
        return enriched;
    }

    function applyCrossingMetadata(snapshots, viewportTransform) {
        var ordered = orderSnapshotsForDraw(snapshots, false);
        var crossingDecorationEnabled = decorationEnabled();
        var labelBreaksNeeded = root._hasLabelBreakCandidates(ordered);
        if (!crossingDecorationEnabled && !labelBreaksNeeded)
            return ordered;

        var gapHalfScene = EdgeViewportMath.screenLengthToScene(root.edgeLayer.edgeCrossingGapScreenPx * 0.5, viewportTransform);
        var anchorMarginScene = EdgeViewportMath.screenLengthToScene(root.edgeLayer.edgeCrossingAnchorGuardScreenPx, viewportTransform);
        var mergeGapScene = EdgeViewportMath.screenLengthToScene(root.edgeLayer.edgeCrossingMergeScreenPx, viewportTransform);
        var samplingModels = [];
        var i;

        for (i = 0; i < ordered.length; i++) {
            var model = _samplingModelForSnapshot(ordered[i], viewportTransform);
            if (model)
                samplingModels.push(model);
        }

        for (i = 0; i < samplingModels.length; i++) {
            var underModel = samplingModels[i];
            var rawRanges = [];
            if (crossingDecorationEnabled && !underModel.snapshot.selected && !underModel.snapshot.previewed) {
                for (var j = i + 1; j < samplingModels.length; j++) {
                    rawRanges = rawRanges.concat(
                        _rawBreakRangesForPair(underModel, samplingModels[j], gapHalfScene, anchorMarginScene)
                    );
                }
                var merged = EdgeMath.mergeBreakRanges(rawRanges, mergeGapScene, underModel.metrics.totalLength);
                underModel.snapshot.crossingBreaks = _enrichedBreakRanges(merged, underModel.points, underModel.metrics.totalLength);
            }
        }
        if (labelBreaksNeeded)
            root._applyLabelBreakMetadata(samplingModels, viewportTransform, mergeGapScene);

        return ordered;
    }

    function requestCanvasPaint() {
        edgeCanvas.requestPaint();
    }

    Item {
        id: canvasTransformLayer
        objectName: "graphCanvasEdgeCanvasTransformLayer"
        width: root.width
        height: root.height
        transformOrigin: Item.TopLeft
        x: root.viewportTransformCompensationX
        y: root.viewportTransformCompensationY
        scale: root.viewportTransformCompensationScale

        Canvas {
            id: edgeCanvas
            anchors.fill: parent
            renderTarget: Canvas.Image

            onPaint: {
                var startedMs = Date.now();
                var ctx = getContext("2d");
                ctx.reset();
                if (!root.edgeLayer) {
                    root._paintDiagnosticsByEdgeId = ({});
                    root._paintDiagnosticsRevision += 1;
                    root._recordPaint(startedMs);
                    return;
                }
                var zoom = EdgeViewportMath.zoomValue(root.edgeLayer);
                var snapshots = root.paintSnapshots || [];
                var viewportTransform = EdgeViewportMath.viewportTransform(root.edgeLayer);
                var paintDiagnosticsByEdgeId = {};
                root._rememberPaintViewport(viewportTransform);
                ctx.save();
                EdgeViewportMath.applyViewportTransform(ctx, viewportTransform);

                for (var i = 0; i < snapshots.length; i++) {
                    var snapshot = snapshots[i];
                    if (!snapshot || snapshot.culled || !snapshot.geometry)
                        continue;
                    var edge = snapshot.edgeData;
                    var geometry = snapshot.geometry;
                    var crossingBreaks = snapshot.crossingBreaks || [];
                    ctx.save();

                    if (snapshot.flowEdge) {
                        var flowPaint = EdgePaintPolicy.flowEdgePaintState(root.edgeLayer, snapshot, edge, zoom);
                        ctx.beginPath();
                        root.traceBodyPieces(ctx, EdgeMath.edgeBodyPieces(
                            geometry,
                            snapshot.crossingSamplePoints || [],
                            crossingBreaks,
                            flowPaint.lineTrimStart,
                            flowPaint.lineTrimEnd
                        ));
                        ctx.strokeStyle = flowPaint.strokeColor;
                        ctx.lineWidth = flowPaint.strokeWidthScene;
                        ctx.lineCap = "round";
                        ctx.lineJoin = "round";
                        ctx.setLineDash(EdgePaintPolicy.dashPatternInStrokeWidths(
                            flowPaint.dashPatternScreenPx,
                            flowPaint.strokeWidthScreenPx
                        ));
                        ctx.stroke();
                        root.drawFlowArrowMarkers(ctx, geometry, flowPaint.markers, flowPaint.strokeColor);
                        paintDiagnosticsByEdgeId[snapshot.edgeId] = flowPaint;
                    } else {
                        var standardPaint = EdgePaintPolicy.standardEdgePaintState(
                            root.edgeLayer,
                            snapshot,
                            edge,
                            zoom
                        );
                        if (standardPaint.endpointArcsVisible) {
                            root.drawHiddenEndpointArcs(
                                ctx,
                                geometry,
                                standardPaint,
                                viewportTransform
                            );
                        } else if (standardPaint.bodyVisible) {
                            ctx.globalAlpha = standardPaint.strokeAlpha;
                            ctx.strokeStyle = root.standardEdgeStrokeStyle(ctx, geometry, standardPaint);
                            ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
                                standardPaint.strokeWidthScreenPx,
                                viewportTransform
                            );
                            var standardDashPattern = EdgePaintPolicy.dashPatternInStrokeWidths(
                                standardPaint.dashPatternScreenPx,
                                standardPaint.strokeWidthScreenPx
                            );
                            ctx.setLineDash(standardDashPattern);
                            ctx.lineCap = "round";
                            ctx.lineJoin = "round";
                            var standardPieces = EdgeMath.edgeBodyPieces(
                                geometry,
                                snapshot.crossingSamplePoints || [],
                                crossingBreaks,
                                0.0,
                                0.0
                            );
                            var strokeOffsets = standardPaint.strokeOffsetsScreenPx || [0.0];
                            for (var strokeIndex = 0; strokeIndex < strokeOffsets.length; ++strokeIndex) {
                                var offset = root.standardStrokeOffsetVector(
                                    geometry,
                                    Number(strokeOffsets[strokeIndex] || 0.0),
                                    viewportTransform
                                );
                                ctx.save();
                                ctx.translate(offset.x, offset.y);
                                ctx.beginPath();
                                root.traceBodyPieces(ctx, standardPieces);
                                ctx.stroke();
                                ctx.restore();
                            }
                        }
                        if (standardPaint.disabledMarkerVisible) {
                            root.drawDisabledMarker(
                                ctx,
                                geometry,
                                standardPaint.disabledMarkerColor,
                                standardPaint.disabledMarkerAlpha,
                                viewportTransform
                            );
                        }
                        paintDiagnosticsByEdgeId[snapshot.edgeId] = standardPaint;
                    }
                    ctx.restore();
                }

                var liveDrags = root.edgeLayer.dragConnectionList();
                for (var liveDragIndex = 0; liveDragIndex < liveDrags.length; liveDragIndex++) {
                    var liveDrag = liveDrags[liveDragIndex];
                    var dragGeometry = root.edgeLayer._dragGeometry(liveDrag);
                    if (dragGeometry) {
                        var dragStrokeColor = EdgePaintPolicy.dragConnectionStrokeColor(
                            root.edgeLayer,
                            liveDrag
                        );
                        ctx.save();
                        ctx.beginPath();
                        root.traceGeometry(ctx, dragGeometry);
                        ctx.strokeStyle = dragStrokeColor;
                        ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
                            EdgePaintPolicy.dragConnectionStrokeWidthScreenPx(
                                root.edgeLayer,
                                liveDrag,
                                zoom
                            ),
                            viewportTransform
                        );
                        ctx.setLineDash(
                            EdgePaintPolicy.dashPatternInStrokeWidths(
                                EdgePaintPolicy.dragConnectionDashPattern(
                                    root.edgeLayer,
                                    liveDrag,
                                    zoom
                                ),
                                EdgePaintPolicy.dragConnectionStrokeWidthScreenPx(root.edgeLayer, liveDrag, zoom)
                            )
                        );
                        ctx.lineCap = "round";
                        ctx.lineJoin = "round";
                        ctx.stroke();
                        if (EdgePaintPolicy.dragConnectionMarkerVisible(root.edgeLayer, liveDrag)) {
                            root.drawDragConnectionMarker(
                                ctx,
                                dragGeometry,
                                EdgePaintPolicy.dragConnectionMarkerText(root.edgeLayer, liveDrag),
                                EdgePaintPolicy.dragConnectionMarkerColor(
                                    root.edgeLayer,
                                    liveDrag,
                                    dragStrokeColor
                                ),
                                viewportTransform,
                                EdgePaintPolicy.dragConnectionMarkerPlain(root.edgeLayer, liveDrag)
                            );
                        }
                        ctx.restore();
                    }
                }

                ctx.restore();
                root._paintDiagnosticsByEdgeId = paintDiagnosticsByEdgeId;
                root._paintDiagnosticsRevision += 1;
                root._recordPaint(startedMs);
            }
        }
    }

    GraphSharedTypography {
        id: edgeLabelGapTypography
        objectName: "graphEdgeCanvasSharedTypography"
        graphLabelPixelSize: root.effectiveGraphLabelPixelSize
    }

    Text {
        // Mirrors the label delegate's wrapping so the line gap fits multi-line labels.
        id: labelGapMeasure
        property real maximumTextWidth: EdgePaintPolicy.flowLabelMaximumTextWidth(true)
        visible: false
        width: Math.min(maximumTextWidth, implicitWidth)
        text: "M"
        wrapMode: Text.Wrap
        maximumLineCount: EdgePaintPolicy.FLOW_LABEL_MAX_LINES
        elide: Text.ElideRight
    }
}
