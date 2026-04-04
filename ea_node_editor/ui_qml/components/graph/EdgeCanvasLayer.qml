import QtQuick 2.15
import "EdgeMath.js" as EdgeMath
import "EdgeViewportMath.js" as EdgeViewportMath

Item {
    id: root
    property Item edgeLayer: null
    function edgeIsFlow(edge) {
        if (!edge)
            return false;
        if (String(edge.edge_family || "") === "flow")
            return true;
        return String(edge.source_port_kind || "") === "flow"
            && String(edge.target_port_kind || "") === "flow";
    }
    function flowStyle(edge) {
        if (!edge)
            return ({});
        if (edge.flow_style)
            return edge.flow_style;
        return edge.visual_style || ({});
    }
    function styleString(value) {
        return String(value || "").trim();
    }
    function stylePositiveNumber(value, fallback) {
        var numeric = Number(value);
        if (!isFinite(numeric) || numeric <= 0.0)
            return fallback;
        return numeric;
    }
    function flowStrokePattern(edge) {
        var style = flowStyle(edge);
        var pattern = styleString(style.stroke_pattern || style.stroke).toLowerCase();
        if (pattern === "dashed" || pattern === "dotted")
            return pattern;
        return "solid";
    }
    function flowArrowHead(edge) {
        var style = flowStyle(edge);
        var arrowHead = styleString(style.arrow_head).toLowerCase();
        if (!arrowHead && style.arrow)
            arrowHead = styleString(style.arrow.kind).toLowerCase();
        if (arrowHead === "open" || arrowHead === "none")
            return arrowHead;
        return "filled";
    }
    function flowStrokeColor(edge, selected, previewed) {
        if (selected)
            return root.edgeLayer.selectedStrokeColor;
        if (previewed)
            return root.edgeLayer.previewStrokeColor;
        return styleString(flowStyle(edge).stroke_color || flowStyle(edge).color) || root.edgeLayer.flowDefaultStrokeColor;
    }
    function flowStrokeWidth(edge, selected, previewed, zoom) {
        var baseWidth = stylePositiveNumber(flowStyle(edge).stroke_width, 2.0);
        if (selected)
            baseWidth = Math.max(baseWidth, 3.0);
        else if (previewed)
            baseWidth = Math.max(baseWidth, 2.8);
        return Math.max(1.0, baseWidth * zoom);
    }
    function flowDashPattern(edge, zoom) {
        var unit = Math.max(1.0, zoom);
        var pattern = flowStrokePattern(edge);
        if (pattern === "dashed")
            return [Math.max(3.0, 8.0 * unit), Math.max(2.0, 5.0 * unit)];
        if (pattern === "dotted")
            return [Math.max(1.0, 1.0 * unit), Math.max(2.0, 4.0 * unit)];
        return [];
    }
    function traceBezierGeometry(ctx, geometry) {
        ctx.moveTo(geometry.sx, geometry.sy);
        ctx.bezierCurveTo(geometry.c1x, geometry.c1y, geometry.c2x, geometry.c2y, geometry.tx, geometry.ty);
    }
    function tracePolylineGeometry(ctx, points) {
        var polylinePoints = points || [];
        for (var i = 0; i < polylinePoints.length; i++) {
            var point = polylinePoints[i];
            if (i === 0)
                ctx.moveTo(point.x, point.y);
            else
                ctx.lineTo(point.x, point.y);
        }
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
    }
    function _tracePolylineSegmentSpan(ctx, segment, startDistance, endDistance) {
        if (!segment || segment.length <= 1e-6 || endDistance - startDistance <= 1e-6)
            return;
        var startFraction = EdgeMath.clamp((startDistance - segment.startDistance) / segment.length, 0.0, 1.0);
        var endFraction = EdgeMath.clamp((endDistance - segment.startDistance) / segment.length, 0.0, 1.0);
        if (endFraction - startFraction <= 1e-6)
            return;
        var startPoint = {
            "x": segment.a.x + (segment.b.x - segment.a.x) * startFraction,
            "y": segment.a.y + (segment.b.y - segment.a.y) * startFraction
        };
        var endPoint = {
            "x": segment.a.x + (segment.b.x - segment.a.x) * endFraction,
            "y": segment.a.y + (segment.b.y - segment.a.y) * endFraction
        };
        ctx.moveTo(startPoint.x, startPoint.y);
        ctx.lineTo(endPoint.x, endPoint.y);
    }

    function traceBrokenGeometry(ctx, geometry, sampledPoints, breakRanges) {
        var metrics = EdgeMath.polylineMetrics(sampledPoints || []);
        if (!metrics.points.length) {
            traceGeometry(ctx, geometry);
            return;
        }
        if (!(breakRanges || []).length) {
            tracePolylineGeometry(ctx, metrics.points);
            return;
        }
        var ranges = breakRanges || [];
        var rangeIndex = 0;
        var segments = metrics.segments || [];
        ctx.lineJoin = "round";
        ctx.lineCap = "round";

        for (var i = 0; i < segments.length; i++) {
            var segment = segments[i];
            var segmentStart = segment.startDistance;
            var segmentEnd = segment.endDistance;
            while (rangeIndex < ranges.length && Number(ranges[rangeIndex].endDistance) <= segmentStart + 1e-6)
                rangeIndex += 1;
            var visibleStart = segmentStart;
            var scanIndex = rangeIndex;
            while (scanIndex < ranges.length && Number(ranges[scanIndex].startDistance) < segmentEnd - 1e-6) {
                var gapRange = ranges[scanIndex];
                var gapStart = Number(gapRange.startDistance);
                var gapEnd = Number(gapRange.endDistance);
                if (gapStart > visibleStart + 1e-6)
                    _tracePolylineSegmentSpan(ctx, segment, visibleStart, Math.min(gapStart, segmentEnd));
                visibleStart = Math.max(visibleStart, Math.min(segmentEnd, gapEnd));
                if (gapEnd <= segmentEnd + 1e-6)
                    scanIndex += 1;
                else
                    break;
            }
            if (visibleStart < segmentEnd - 1e-6)
                _tracePolylineSegmentSpan(ctx, segment, visibleStart, segmentEnd);
            rangeIndex = scanIndex;
        }
    }

    function traceGeometry(ctx, geometry) {
        if (!geometry)
            return;
        if (geometry.route === "pipe") {
            tracePolylineGeometry(ctx, geometry.pipe_points || []);
            return;
        }
        traceBezierGeometry(ctx, geometry);
    }

    function edgeAnchor(geometry, fraction) {
        if (!geometry)
            return null;
        if (geometry.route === "pipe")
            return EdgeMath.pointTangentAlongPolyline(geometry.pipe_points || [], fraction);
        return EdgeMath.pointTangentAlongBezier(
            geometry.sx,
            geometry.sy,
            geometry.c1x,
            geometry.c1y,
            geometry.c2x,
            geometry.c2y,
            geometry.tx,
            geometry.ty,
            fraction,
            40
        );
    }

    function drawFlowArrowHead(ctx, geometry, edge, strokeColor, zoom, viewportTransform) {
        var arrowHead = flowArrowHead(edge);
        if (arrowHead === "none")
            return;
        var anchor = edgeAnchor(geometry, 1.0);
        if (!anchor)
            return;
        var tipX = anchor.x;
        var tipY = anchor.y;
        var size = EdgeViewportMath.screenLengthToScene(Math.max(6.0, 8.0 * zoom), viewportTransform);
        var wing = EdgeViewportMath.screenLengthToScene(Math.max(3.0, 4.5 * zoom), viewportTransform);
        var baseX = tipX - anchor.dx * size;
        var baseY = tipY - anchor.dy * size;
        var normalX = -anchor.dy;
        var normalY = anchor.dx;
        var leftX = baseX + normalX * wing;
        var leftY = baseY + normalY * wing;
        var rightX = baseX - normalX * wing;
        var rightY = baseY - normalY * wing;

        ctx.save();
        ctx.setLineDash([]);
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.strokeStyle = strokeColor;
        ctx.fillStyle = strokeColor;
        ctx.lineWidth = EdgeViewportMath.screenLengthToScene(Math.max(1.0, 1.4 * zoom), viewportTransform);
        ctx.beginPath();
        ctx.moveTo(leftX, leftY);
        ctx.lineTo(tipX, tipY);
        ctx.lineTo(rightX, rightY);
        if (arrowHead === "filled") {
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        } else {
            ctx.stroke();
        }
        ctx.restore();
    }

    function decorationEnabled() {
        return root.edgeLayer.edgeCrossingStyle === "gap_break"
            && root.edgeLayer.performanceMode === "full_fidelity"
            && !root.edgeLayer.transientPerformanceActivityActive
            && !root.edgeLayer.transientDegradedWindowActive;
    }

    function _resetSnapshot(snapshot) {
        if (!snapshot)
            return;
        snapshot.crossingBreaks = [];
        snapshot.crossingSamplePoints = [];
        snapshot.drawOrderIndex = -1;
    }

    function orderSnapshotsForDraw(snapshots) {
        var background = [];
        var elevated = [];
        var sourceSnapshots = snapshots || [];
        for (var i = 0; i < sourceSnapshots.length; i++) {
            var snapshot = sourceSnapshots[i];
            if (!snapshot)
                continue;
            _resetSnapshot(snapshot);
            if (snapshot.previewed || snapshot.selected)
                elevated.push(snapshot);
            else
                background.push(snapshot);
        }
        var ordered = background.concat(elevated);
        for (i = 0; i < ordered.length; i++)
            ordered[i].drawOrderIndex = i;
        return ordered;
    }

    function _samplingModelForSnapshot(snapshot, viewportTransform) {
        if (!snapshot || snapshot.culled || !snapshot.geometry)
            return null;
        var sceneStep = EdgeViewportMath.screenLengthToScene(root.edgeLayer.edgeCrossingSampleStepScreenPx, viewportTransform);
        var points = EdgeMath.sampleGeometryPolyline(snapshot.geometry, sceneStep);
        var metrics = EdgeMath.polylineMetrics(points);
        if (!metrics.points.length || !metrics.segments.length || !metrics.bounds)
            return null;
        snapshot.crossingSamplePoints = metrics.points;
        return {"snapshot": snapshot, "points": metrics.points, "metrics": metrics};
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
        var ordered = orderSnapshotsForDraw(snapshots);
        if (!decorationEnabled())
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
            for (var j = i + 1; j < samplingModels.length; j++) {
                rawRanges = rawRanges.concat(
                    _rawBreakRangesForPair(underModel, samplingModels[j], gapHalfScene, anchorMarginScene)
                );
            }
            var merged = EdgeMath.mergeBreakRanges(rawRanges, mergeGapScene, underModel.metrics.totalLength);
            underModel.snapshot.crossingBreaks = _enrichedBreakRanges(merged, underModel.points, underModel.metrics.totalLength);
        }

        return ordered;
    }

    function requestCanvasPaint() {
        edgeCanvas.requestPaint();
    }

    Canvas {
        id: edgeCanvas
        anchors.fill: parent
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            if (!root.edgeLayer)
                return;
            var zoom = EdgeViewportMath.zoomValue(root.edgeLayer);
            var snapshots = root.edgeLayer._visibleEdgeSnapshots || [];
            var viewportTransform = EdgeViewportMath.viewportTransform(root.edgeLayer);

            ctx.save();
            EdgeViewportMath.applyViewportTransform(ctx, viewportTransform);

            for (var i = 0; i < snapshots.length; i++) {
                var snapshot = snapshots[i];
                if (!snapshot || snapshot.culled || !snapshot.geometry)
                    continue;
                var edge = snapshot.edgeData;
                var geometry = snapshot.geometry;
                var selected = snapshot.selected;
                var previewed = snapshot.previewed;
                var crossingBreaks = snapshot.crossingBreaks || [];
                ctx.save();
                ctx.beginPath();
                if (crossingBreaks.length > 0)
                    root.traceBrokenGeometry(ctx, geometry, snapshot.crossingSamplePoints || [], crossingBreaks);
                else
                    root.traceGeometry(ctx, geometry);

                if (snapshot.flowEdge) {
                    var flowStrokeColor = root.flowStrokeColor(edge, selected, previewed);
                    ctx.strokeStyle = flowStrokeColor;
                    ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
                        root.flowStrokeWidth(edge, selected, previewed, zoom),
                        viewportTransform
                    );
                    ctx.setLineDash(
                        EdgeViewportMath.dashPatternToScene(root.flowDashPattern(edge, zoom), viewportTransform)
                    );
                    ctx.stroke();
                    root.drawFlowArrowHead(ctx, geometry, edge, flowStrokeColor, zoom, viewportTransform);
                } else {
                    ctx.strokeStyle = selected
                        ? root.edgeLayer.selectedStrokeColor
                        : (previewed ? root.edgeLayer.previewStrokeColor : (edge.color || root.edgeLayer.fallbackStrokeColor));
                    ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
                        Math.max(1.0, (selected ? 3.0 : (previewed ? 2.8 : 2.0)) * zoom),
                        viewportTransform
                    );
                    ctx.stroke();
                }
                ctx.restore();
            }

            var liveDrag = root.edgeLayer.dragConnection;
            if (liveDrag) {
                var dragGeometry = root.edgeLayer._dragGeometry(liveDrag);
                if (dragGeometry) {
                    ctx.save();
                    ctx.beginPath();
                    root.traceGeometry(ctx, dragGeometry);
                    ctx.strokeStyle = liveDrag.valid_drop
                        ? root.edgeLayer.validDragStrokeColor
                        : root.edgeLayer.invalidDragStrokeColor;
                    ctx.lineWidth = EdgeViewportMath.screenLengthToScene(
                        Math.max(1.0, (liveDrag.valid_drop ? 2.7 : 2.0) * zoom),
                        viewportTransform
                    );
                    ctx.setLineDash(
                        EdgeViewportMath.dashPatternToScene(
                            [Math.max(2.0, 6.0 * zoom), Math.max(1.0, 4.0 * zoom)],
                            viewportTransform
                        )
                    );
                    ctx.lineCap = "round";
                    ctx.stroke();
                    ctx.restore();
                }
            }

            ctx.restore();
        }
    }
}
