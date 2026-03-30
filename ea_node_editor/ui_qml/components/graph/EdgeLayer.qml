import QtQuick 2.15
import QtQml 2.15
import "EdgeMath.js" as EdgeMath
import "GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics

Item {
    id: root
    readonly property var edgePalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.edge_palette
        : ({})
    readonly property var shellPalette: typeof themeBridge !== "undefined"
        ? themeBridge.palette
        : ({})
    readonly property var portKindPalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.port_kind_palette
        : ({})
    property var viewBridge: null
    property var sceneBridge: null
    property var edges: []
    property var nodes: []
    property var dragOffsets: ({})
    property var liveNodeGeometry: ({})
    property var selectedEdgeIds: []
    property var visibleSceneRectPayload: ({})
    property string previewEdgeId: ""
    property var dragConnection: null
    property string edgeCrossingStyle: "none"
    property string performanceMode: "full_fidelity"
    property bool transientPerformanceActivityActive: false
    property bool transientDegradedWindowActive: false
    property bool edgeLabelSimplificationActive: false
    property bool inputEnabled: true
    property int _redrawRequestCount: 0
    property bool _viewStateRedrawDirty: false
    property real viewportCullMarginPx: 96.0
    property var _cachedNodeMap: null
    property var _cachedEdgeGeometries: ({})
    property var _visibleEdgeSnapshots: []
    property var _visibleEdgeSnapshotById: ({})
    property int _visibleEdgeSnapshotRevision: 0
    readonly property color selectedStrokeColor: edgePalette.selected_stroke || "#f0f4fb"
    readonly property color previewStrokeColor: edgePalette.preview_stroke || "#60CDFF"
    readonly property color validDragStrokeColor: edgePalette.valid_drag_stroke || "#60CDFF"
    readonly property color invalidDragStrokeColor: edgePalette.invalid_drag_stroke || "#d0d5de"
    readonly property color fallbackStrokeColor: portKindPalette.data || "#7AA8FF"
    readonly property color flowDefaultStrokeColor: shellPalette.muted_fg || invalidDragStrokeColor
    readonly property color flowDefaultLabelTextColor: shellPalette.panel_title_fg || selectedStrokeColor
    readonly property color flowDefaultLabelBackgroundColor: shellPalette.panel_bg || "#1b1d22"
    readonly property color flowDefaultLabelBorderColor: shellPalette.border || "#3a3d45"
    property real flowLabelHideZoomThreshold: 0.55
    property real flowLabelSimplifyZoomThreshold: 0.85
    property real edgeCrossingGapScreenPx: 14.0
    property real edgeCrossingAnchorGuardScreenPx: 18.0
    property real edgeCrossingMergeScreenPx: 6.0
    property real edgeCrossingSampleStepScreenPx: 10.0

    signal edgeClicked(string edgeId, bool additive)
    signal edgeContextRequested(string edgeId, real screenX, real screenY)

    QtObject {
        id: viewportMath

        function zoomValue() {
            var zoom = viewBridge ? Number(viewBridge.zoom_value) : 1.0;
            if (!isFinite(zoom) || zoom <= 0.0001)
                return 1.0;
            return zoom;
        }

        function viewportTransform() {
            var zoom = zoomValue();
            var centerX = viewBridge ? Number(viewBridge.center_x) : 0.0;
            var centerY = viewBridge ? Number(viewBridge.center_y) : 0.0;
            if (!isFinite(centerX))
                centerX = 0.0;
            if (!isFinite(centerY))
                centerY = 0.0;
            return {
                "zoom": zoom,
                "offsetX": root.width * 0.5 - centerX * zoom,
                "offsetY": root.height * 0.5 - centerY * zoom
            };
        }

        function sceneXToScreen(worldX, viewportTransform) {
            return Number(worldX) * viewportTransform.zoom + viewportTransform.offsetX;
        }

        function sceneYToScreen(worldY, viewportTransform) {
            return Number(worldY) * viewportTransform.zoom + viewportTransform.offsetY;
        }

        function screenToSceneX(screenX, viewportTransform) {
            return (Number(screenX) - viewportTransform.offsetX) / viewportTransform.zoom;
        }

        function screenToSceneY(screenY, viewportTransform) {
            return (Number(screenY) - viewportTransform.offsetY) / viewportTransform.zoom;
        }

        function screenLengthToScene(screenLengthPx, viewportTransformArg) {
            var transform = viewportTransformArg || viewportTransform();
            return Math.max(0.0, Number(screenLengthPx || 0.0)) / transform.zoom;
        }

        function screenMarginToScene(screenMarginPx) {
            return screenLengthToScene(screenMarginPx);
        }

        function dashPatternToScene(screenPattern, viewportTransformArg) {
            var pattern = screenPattern || [];
            var scenePattern = [];
            for (var i = 0; i < pattern.length; i++)
                scenePattern.push(screenLengthToScene(pattern[i], viewportTransformArg));
            return scenePattern;
        }

        function applyViewportTransform(ctx, viewportTransform) {
            ctx.translate(viewportTransform.offsetX, viewportTransform.offsetY);
            ctx.scale(viewportTransform.zoom, viewportTransform.zoom);
        }
    }

    QtObject {
        id: flowStylePolicy

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
            if (!arrowHead) {
                var arrow = style.arrow;
                if (arrow)
                    arrowHead = styleString(arrow.kind).toLowerCase();
            }
            if (arrowHead === "open" || arrowHead === "none")
                return arrowHead;
            return "filled";
        }

        function flowStrokeColor(edge, selected, previewed) {
            if (selected)
                return root.selectedStrokeColor;
            if (previewed)
                return root.previewStrokeColor;
            var style = flowStyle(edge);
            return styleString(style.stroke_color || style.color) || root.flowDefaultStrokeColor;
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
    }

    QtObject {
        id: edgeRenderer

        function traceBezierGeometry(ctx, geometry) {
            ctx.moveTo(geometry.sx, geometry.sy);
            ctx.bezierCurveTo(
                geometry.c1x,
                geometry.c1y,
                geometry.c2x,
                geometry.c2y,
                geometry.tx,
                geometry.ty
            );
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
            if (!segment || segment.length <= 1e-6)
                return;
            if (endDistance - startDistance <= 1e-6)
                return;
            var startFraction = EdgeMath.clamp(
                (startDistance - segment.startDistance) / segment.length,
                0.0,
                1.0
            );
            var endFraction = EdgeMath.clamp(
                (endDistance - segment.startDistance) / segment.length,
                0.0,
                1.0
            );
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
                while (rangeIndex < ranges.length
                       && Number(ranges[rangeIndex].endDistance) <= segmentStart + 1e-6) {
                    rangeIndex += 1;
                }
                var visibleStart = segmentStart;
                var scanIndex = rangeIndex;
                while (scanIndex < ranges.length
                       && Number(ranges[scanIndex].startDistance) < segmentEnd - 1e-6) {
                    var gapRange = ranges[scanIndex];
                    var gapStart = Number(gapRange.startDistance);
                    var gapEnd = Number(gapRange.endDistance);
                    if (gapStart > visibleStart + 1e-6) {
                        _tracePolylineSegmentSpan(
                            ctx,
                            segment,
                            visibleStart,
                            Math.min(gapStart, segmentEnd)
                        );
                    }
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
            var arrowHead = flowStylePolicy.flowArrowHead(edge);
            if (arrowHead === "none")
                return;
            var anchor = edgeAnchor(geometry, 1.0);
            if (!anchor)
                return;
            var tipX = anchor.x;
            var tipY = anchor.y;
            var size = viewportMath.screenLengthToScene(Math.max(6.0, 8.0 * zoom), viewportTransform);
            var wing = viewportMath.screenLengthToScene(Math.max(3.0, 4.5 * zoom), viewportTransform);
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
            ctx.lineWidth = viewportMath.screenLengthToScene(Math.max(1.0, 1.4 * zoom), viewportTransform);
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
    }

    QtObject {
        id: edgeCrossingPolicy

        function decorationEnabled() {
            return root.edgeCrossingStyle === "gap_break"
                && root.performanceMode === "full_fidelity"
                && !root.transientPerformanceActivityActive
                && !root.transientDegradedWindowActive;
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
            var sceneStep = viewportMath.screenLengthToScene(root.edgeCrossingSampleStepScreenPx, viewportTransform);
            var points = EdgeMath.sampleGeometryPolyline(snapshot.geometry, sceneStep);
            var metrics = EdgeMath.polylineMetrics(points);
            if (!metrics.points.length || !metrics.segments.length || !metrics.bounds)
                return null;
            snapshot.crossingSamplePoints = metrics.points;
            return {
                "snapshot": snapshot,
                "points": metrics.points,
                "metrics": metrics
            };
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
                    var intersection = EdgeMath.segmentIntersection(
                        underSegment.a,
                        underSegment.b,
                        overSegment.a,
                        overSegment.b
                    );
                    if (!intersection)
                        continue;
                    var underDistance = underSegment.startDistance + underSegment.length * intersection.tA;
                    var overDistance = overSegment.startDistance + overSegment.length * intersection.tB;
                    if (EdgeMath.distanceNearPolylineEndpoints(
                            underDistance,
                            underMetrics.totalLength,
                            anchorMarginScene
                        )) {
                        continue;
                    }
                    if (EdgeMath.distanceNearPolylineEndpoints(
                            overDistance,
                            overMetrics.totalLength,
                            anchorMarginScene
                        )) {
                        continue;
                    }
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

            var gapHalfScene = viewportMath.screenLengthToScene(
                root.edgeCrossingGapScreenPx * 0.5,
                viewportTransform
            );
            var anchorMarginScene = viewportMath.screenLengthToScene(
                root.edgeCrossingAnchorGuardScreenPx,
                viewportTransform
            );
            var mergeGapScene = viewportMath.screenLengthToScene(
                root.edgeCrossingMergeScreenPx,
                viewportTransform
            );
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
                        _rawBreakRangesForPair(
                            underModel,
                            samplingModels[j],
                            gapHalfScene,
                            anchorMarginScene
                        )
                    );
                }
                var merged = EdgeMath.mergeBreakRanges(
                    rawRanges,
                    mergeGapScene,
                    underModel.metrics.totalLength
                );
                underModel.snapshot.crossingBreaks = _enrichedBreakRanges(
                    merged,
                    underModel.points,
                    underModel.metrics.totalLength
                );
            }

            return ordered;
        }
    }

    QtObject {
        id: flowLabelPolicy

        function edgeLabelText(edge) {
            return String(edge && edge.label ? edge.label : "").trim();
        }

        function flowLabelMode(edge) {
            if (!flowStylePolicy.edgeIsFlow(edge) || !edgeLabelText(edge))
                return "hidden";
            if (root.edgeLabelSimplificationActive)
                return "hidden";
            var zoom = root.viewBridge ? root.viewBridge.zoom_value : 1.0;
            if (zoom < root.flowLabelHideZoomThreshold)
                return "hidden";
            if (zoom < root.flowLabelSimplifyZoomThreshold)
                return "text";
            return "pill";
        }

        function flowLabelTextColor(edge) {
            return flowStylePolicy.styleString(flowStylePolicy.flowStyle(edge).label_text_color)
                || root.flowDefaultLabelTextColor;
        }

        function flowLabelBackgroundColor(edge) {
            return flowStylePolicy.styleString(flowStylePolicy.flowStyle(edge).label_background_color)
                || root.flowDefaultLabelBackgroundColor;
        }

        function flowLabelBorderColor(edge, selected, previewed) {
            if (selected || previewed)
                return flowStylePolicy.flowStrokeColor(edge, selected, previewed);
            return root.flowDefaultLabelBorderColor;
        }

        function flowLabelAnchorScene(geometry) {
            var anchor = null;
            if (geometry && geometry.route === "pipe") {
                var pipePoints = geometry.pipe_points || [];
                var longestHorizontal = null;
                for (var i = 1; i < pipePoints.length; i++) {
                    var start = pipePoints[i - 1];
                    var end = pipePoints[i];
                    var dx = end.x - start.x;
                    var dy = end.y - start.y;
                    if (Math.abs(dy) > 0.01)
                        continue;
                    var length = Math.abs(dx);
                    if (!longestHorizontal || length > longestHorizontal.length) {
                        longestHorizontal = {
                            "x": (start.x + end.x) * 0.5,
                            "y": start.y,
                            "dx": dx >= 0.0 ? 1.0 : -1.0,
                            "dy": 0.0,
                            "angle": dx >= 0.0 ? 0.0 : 180.0,
                            "length": length
                        };
                    }
                }
                anchor = longestHorizontal || edgeRenderer.edgeAnchor(geometry, 0.5);
            } else {
                anchor = edgeRenderer.edgeAnchor(geometry, 0.5);
            }
            if (!anchor)
                return null;
            var normalX = -anchor.dy;
            var normalY = anchor.dx;
            if (normalY > 0.0) {
                normalX = -normalX;
                normalY = -normalY;
            }
            return {
                "x": anchor.x,
                "y": anchor.y,
                "dx": anchor.dx,
                "dy": anchor.dy,
                "normal_x": normalX,
                "normal_y": normalY,
                "angle": anchor.angle
            };
        }

        function flowLabelAnchor(labelAnchorScene) {
            if (!labelAnchorScene)
                return null;
            return {
                "screen_x": root.sceneToScreenX(labelAnchorScene.x) + Number(labelAnchorScene.normal_x) * 18.0,
                "screen_y": root.sceneToScreenY(labelAnchorScene.y) + Number(labelAnchorScene.normal_y) * 18.0,
                "angle": labelAnchorScene.angle
            };
        }
    }

    function requestRedraw() {
        root._viewStateRedrawDirty = false;
        root._refreshVisibleEdgeSnapshots();
        root._redrawRequestCount += 1;
        edgeCanvas.requestPaint();
    }

    function markViewStateRedrawDirty() {
        root._viewStateRedrawDirty = true;
    }

    function flushViewStateRedraw() {
        if (!root._viewStateRedrawDirty)
            return false;
        requestRedraw();
        return true;
    }

    function _invalidateGeometryCache() {
        root._cachedNodeMap = null;
        root._cachedEdgeGeometries = ({});
    }

    function _getNodeMap() {
        if (root._cachedNodeMap !== null)
            return root._cachedNodeMap;
        root._cachedNodeMap = root._nodeMap();
        return root._cachedNodeMap;
    }

    function _getCachedEdgeGeometry(edge, nodeById) {
        var edgeId = edge.edge_id;
        var cached = root._cachedEdgeGeometries[edgeId];
        if (cached !== undefined)
            return cached;
        var geometry = root._edgeGeometry(edge, nodeById);
        root._cachedEdgeGeometries[edgeId] = geometry;
        return geometry;
    }

    function sceneToScreenX(worldX) {
        return viewportMath.sceneXToScreen(worldX, viewportMath.viewportTransform());
    }

    function sceneToScreenY(worldY) {
        return viewportMath.sceneYToScreen(worldY, viewportMath.viewportTransform());
    }

    function _edgeAnchor(geometry, fraction) {
        return edgeRenderer.edgeAnchor(geometry, fraction);
    }

    function _expandedVisibleSceneBounds() {
        var payload = root.visibleSceneRectPayload;
        if ((!payload || payload.width === undefined || payload.height === undefined) && root.viewBridge)
            payload = root.viewBridge.visible_scene_rect_payload;
        if (!payload)
            return null;
        var x = Number(payload.x);
        var y = Number(payload.y);
        var width = Number(payload.width);
        var height = Number(payload.height);
        if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height) || width <= 0.0 || height <= 0.0)
            return null;
        var sceneMargin = viewportMath.screenMarginToScene(root.viewportCullMarginPx);
        return {
            "left": x - sceneMargin,
            "top": y - sceneMargin,
            "right": x + width + sceneMargin,
            "bottom": y + height + sceneMargin
        };
    }

    function _rectIntersects(a, b) {
        if (!a || !b)
            return true;
        return a.left <= b.right
            && a.right >= b.left
            && a.top <= b.bottom
            && a.bottom >= b.top;
    }

    function _sceneBoundsForPoints(points) {
        if (!points || !points.length)
            return null;
        var minX = Number.POSITIVE_INFINITY;
        var minY = Number.POSITIVE_INFINITY;
        var maxX = Number.NEGATIVE_INFINITY;
        var maxY = Number.NEGATIVE_INFINITY;
        for (var i = 0; i < points.length; i++) {
            var point = points[i];
            if (!point)
                continue;
            var x = Number(point.x);
            var y = Number(point.y);
            if (!isFinite(x) || !isFinite(y))
                continue;
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        }
        if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY))
            return null;
        return {
            "left": minX,
            "top": minY,
            "right": maxX,
            "bottom": maxY
        };
    }

    function _nodeMap() {
        var byId = {};
        var sceneNodes = root.nodes || [];
        var liveGeometry = root.liveNodeGeometry || {};
        for (var i = 0; i < sceneNodes.length; i++) {
            var node = sceneNodes[i];
            if (!node || !node.node_id)
                continue;
            var overlay = liveGeometry[node.node_id];
            if (!overlay || node.collapsed) {
                byId[node.node_id] = node;
                continue;
            }
            var merged = {};
            for (var key in node) {
                if (Object.prototype.hasOwnProperty.call(node, key))
                    merged[key] = node[key];
            }
            var liveX = Number(overlay.x);
            var liveY = Number(overlay.y);
            var liveWidth = Number(overlay.width);
            var liveHeight = Number(overlay.height);
            if (isFinite(liveX))
                merged.x = liveX;
            if (isFinite(liveY))
                merged.y = liveY;
            if (isFinite(liveWidth) && liveWidth > 0.0)
                merged.width = liveWidth;
            if (isFinite(liveHeight) && liveHeight > 0.0)
                merged.height = liveHeight;
            byId[node.node_id] = merged;
        }
        return byId;
    }

    function _portScenePoint(node, portKey) {
        if (!node || !portKey)
            return null;
        var ports = node.ports || [];
        var inputRow = 0;
        var outputRow = 0;
        for (var i = 0; i < ports.length; i++) {
            var port = ports[i];
            if (!port)
                continue;
            if (String(port.key || "") === String(portKey))
                return GraphNodeSurfaceMetrics.portScenePointForPort(node, port, inputRow, outputRow);
            var direction = GraphNodeSurfaceMetrics.portLayoutDirection(port);
            if (direction === "in")
                inputRow += 1;
            else if (direction === "out")
                outputRow += 1;
        }
        return null;
    }

    function _nodeBounds(nodeId, nodeOffset, nodeById) {
        var node = nodeById[nodeId];
        if (!node)
            return null;
        var ox = nodeOffset ? nodeOffset.dx : 0.0;
        var oy = nodeOffset ? nodeOffset.dy : 0.0;
        return {
            "left": node.x + ox,
            "top": node.y + oy,
            "right": node.x + node.width + ox,
            "bottom": node.y + node.height + oy,
            "x": node.x + ox,
            "y": node.y + oy,
            "width": node.width,
            "height": node.height
        };
    }

    function _normalizedCardinalSide(side, fallback) {
        var normalized = String(side || "").trim().toLowerCase();
        if (normalized === "top" || normalized === "right" || normalized === "bottom" || normalized === "left")
            return normalized;
        return String(fallback || "").trim().toLowerCase();
    }

    function _coerceBounds(boundsPayload) {
        if (!boundsPayload)
            return null;
        var x = Number(boundsPayload.x);
        var y = Number(boundsPayload.y);
        var width = Number(boundsPayload.width);
        var height = Number(boundsPayload.height);
        if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height) || width <= 0.0 || height <= 0.0)
            return null;
        return {
            "left": x,
            "top": y,
            "right": x + width,
            "bottom": y + height,
            "x": x,
            "y": y,
            "width": width,
            "height": height
        };
    }

    function _offsetBounds(bounds, dx, dy) {
        if (!bounds)
            return null;
        var offsetX = Number(dx);
        var offsetY = Number(dy);
        if (!isFinite(offsetX))
            offsetX = 0.0;
        if (!isFinite(offsetY))
            offsetY = 0.0;
        return {
            "left": bounds.left + offsetX,
            "top": bounds.top + offsetY,
            "right": bounds.right + offsetX,
            "bottom": bounds.bottom + offsetY,
            "x": bounds.x + offsetX,
            "y": bounds.y + offsetY,
            "width": bounds.width,
            "height": bounds.height
        };
    }

    function _overlayBounds(bounds, overlay) {
        if (!bounds)
            return null;
        if (!overlay)
            return bounds;
        var x = Number(overlay.x);
        var y = Number(overlay.y);
        var width = Number(overlay.width);
        var height = Number(overlay.height);
        var nextX = isFinite(x) ? x : bounds.x;
        var nextY = isFinite(y) ? y : bounds.y;
        var nextWidth = isFinite(width) && width > 0.0 ? width : bounds.width;
        var nextHeight = isFinite(height) && height > 0.0 ? height : bounds.height;
        return {
            "left": nextX,
            "top": nextY,
            "right": nextX + nextWidth,
            "bottom": nextY + nextHeight,
            "x": nextX,
            "y": nextY,
            "width": nextWidth,
            "height": nextHeight
        };
    }

    function _edgeAnchorBounds(edge, prefix, nodeById) {
        var anchorNodeId = String(edge && edge[prefix + "_anchor_node_id"] || "");
        var nodeOffset = root.dragOffsets ? root.dragOffsets[anchorNodeId] : null;
        var nodeBounds = anchorNodeId ? root._nodeBounds(anchorNodeId, nodeOffset, nodeById) : null;
        if (nodeBounds)
            return nodeBounds;

        var bounds = root._coerceBounds(edge ? edge[prefix + "_anchor_bounds"] : null);
        if (!bounds)
            return null;
        var overlay = root.liveNodeGeometry ? root.liveNodeGeometry[anchorNodeId] : null;
        bounds = root._overlayBounds(bounds, overlay);
        if (nodeOffset)
            bounds = root._offsetBounds(bounds, nodeOffset.dx, nodeOffset.dy);
        return bounds;
    }

    function _clampToRange(value, low, high) {
        var numeric = Number(value);
        var minimum = Number(low);
        var maximum = Number(high);
        if (!isFinite(numeric))
            numeric = (minimum + maximum) * 0.5;
        if (!isFinite(minimum) || !isFinite(maximum))
            return numeric;
        if (minimum > maximum)
            return (minimum + maximum) * 0.5;
        return Math.min(maximum, Math.max(minimum, numeric));
    }

    function _perimeterPoint(bounds, side, towardPoint) {
        if (!bounds)
            return null;
        var normalizedSide = root._normalizedCardinalSide(side, "right");
        var towardX = towardPoint ? Number(towardPoint.x) : (bounds.left + bounds.right) * 0.5;
        var towardY = towardPoint ? Number(towardPoint.y) : (bounds.top + bounds.bottom) * 0.5;
        if (!isFinite(towardX))
            towardX = (bounds.left + bounds.right) * 0.5;
        if (!isFinite(towardY))
            towardY = (bounds.top + bounds.bottom) * 0.5;
        var insetX = Math.min(12.0, bounds.width * 0.5);
        var insetY = Math.min(12.0, bounds.height * 0.5);
        if (normalizedSide === "left") {
            return {
                "x": bounds.left,
                "y": root._clampToRange(towardY, bounds.top + insetY, bounds.bottom - insetY)
            };
        }
        if (normalizedSide === "right") {
            return {
                "x": bounds.right,
                "y": root._clampToRange(towardY, bounds.top + insetY, bounds.bottom - insetY)
            };
        }
        if (normalizedSide === "top") {
            return {
                "x": root._clampToRange(towardX, bounds.left + insetX, bounds.right - insetX),
                "y": bounds.top
            };
        }
        return {
            "x": root._clampToRange(towardX, bounds.left + insetX, bounds.right - insetX),
            "y": bounds.bottom
        };
    }

    function _edgeEndpointState(edge, prefix, nodeById, oppositePoint) {
        var pointX = Number(edge && edge[prefix === "source" ? "sx" : "tx"] || 0.0);
        var pointY = Number(edge && edge[prefix === "source" ? "sy" : "ty"] || 0.0);
        var anchorNodeId = String(edge && edge[prefix + "_anchor_node_id"] || edge && edge[prefix + "_node_id"] || "");
        var portKey = String(edge && edge[prefix + "_port_key"] || "");
        var fallbackSide = prefix === "source" ? "right" : "left";
        var side = root._normalizedCardinalSide(
            edge && edge[prefix + "_anchor_side"],
            root._normalizedCardinalSide(edge && edge[prefix + "_port_side"], fallbackSide)
        );
        var anchorKind = String(edge && edge[prefix + "_anchor_kind"] || "node");
        var bounds = root._edgeAnchorBounds(edge, prefix, nodeById);
        if (anchorKind === "node") {
            var anchorNode = nodeById[anchorNodeId];
            var portPoint = root._portScenePoint(anchorNode, portKey);
            if (portPoint) {
                // Drag previews keep the scene payload static, so edge anchors need the
                // transient node offset applied explicitly while the node is moving.
                var nodeOffset = root.dragOffsets ? root.dragOffsets[anchorNodeId] : null;
                var offsetX = nodeOffset ? Number(nodeOffset.dx) : 0.0;
                var offsetY = nodeOffset ? Number(nodeOffset.dy) : 0.0;
                if (!isFinite(offsetX))
                    offsetX = 0.0;
                if (!isFinite(offsetY))
                    offsetY = 0.0;
                return {
                    "point": {"x": portPoint.x + offsetX, "y": portPoint.y + offsetY},
                    "bounds": bounds,
                    "side": side
                };
            }
        }
        if (bounds) {
            return {
                "point": root._perimeterPoint(bounds, side, oppositePoint),
                "bounds": bounds,
                "side": side
            };
        }
        return {
            "point": {"x": pointX, "y": pointY},
            "bounds": bounds,
            "side": side
        };
    }

    function _routeLength(sourceX, sourceY, sourceStubX, targetX, targetY, targetStubX, routeY) {
        return Math.abs(sourceStubX - sourceX)
            + Math.abs(routeY - sourceY)
            + Math.abs(sourceStubX - targetStubX)
            + Math.abs(targetY - routeY)
            + Math.abs(targetX - targetStubX);
    }

    function _buildLegacyPipePoints(edge, sourceBounds, targetBounds, sourceX, sourceY, targetX, targetY, nodeById) {
        if (!sourceBounds && edge && edge.source_node_id)
            sourceBounds = _nodeBounds(edge.source_node_id, null, nodeById);
        if (!targetBounds && edge && edge.target_node_id)
            targetBounds = _nodeBounds(edge.target_node_id, null, nodeById);
        var laneBias = edge.lane_bias || 0.0;
        var stub = Math.min(72.0, Math.max(32.0, Math.max(44.0, Math.abs(targetX - sourceX) * 0.2)));
        var sourceStubX;
        var targetStubX;
        var sourceTop;
        var sourceBottom;
        var targetTop;
        var targetBottom;

        if (sourceBounds && targetBounds) {
            sourceStubX = Math.max(sourceBounds.right, sourceX) + stub;
            targetStubX = Math.min(targetBounds.left, targetX) - stub;
            sourceTop = sourceBounds.top;
            sourceBottom = sourceBounds.bottom;
            targetTop = targetBounds.top;
            targetBottom = targetBounds.bottom;
        } else {
            sourceStubX = sourceX + stub;
            targetStubX = targetX - stub;
            sourceTop = Math.min(sourceY, targetY) - 40.0;
            sourceBottom = Math.max(sourceY, targetY) + 40.0;
            targetTop = sourceTop;
            targetBottom = sourceBottom;
        }

        if (sourceStubX <= targetStubX) {
            var midX = (sourceStubX + targetStubX) * 0.5;
            sourceStubX = midX + 22.0;
            targetStubX = midX - 22.0;
        }

        var verticalClearance = 56.0 * 0.6 + Math.abs(laneBias) * 0.8;
        var topBound = Math.min(sourceTop, targetTop);
        var bottomBound = Math.max(sourceBottom, targetBottom);
        var topRouteY = topBound - verticalClearance - Math.max(0.0, laneBias);
        var bottomRouteY = bottomBound + verticalClearance + Math.max(0.0, -laneBias);
        var candidates = [{"y": topRouteY, "priority": 1}, {"y": bottomRouteY, "priority": 1}];

        var middleLow = null;
        var middleHigh = null;
        if (sourceBottom + 10.0 <= targetTop - 10.0) {
            middleLow = sourceBottom + 10.0;
            middleHigh = targetTop - 10.0;
        } else if (targetBottom + 10.0 <= sourceTop - 10.0) {
            middleLow = targetBottom + 10.0;
            middleHigh = sourceTop - 10.0;
        }

        if (middleLow !== null && middleHigh !== null && middleLow <= middleHigh) {
            var preferredMiddle = (sourceY + targetY) * 0.5 + laneBias * 0.35;
            var middleRouteY = EdgeMath.clamp(preferredMiddle, middleLow, middleHigh);
            candidates.push({"y": middleRouteY, "priority": 0});
        }

        var best = candidates[0];
        var bestLength = _routeLength(sourceX, sourceY, sourceStubX, targetX, targetY, targetStubX, best.y);
        for (var c = 1; c < candidates.length; c++) {
            var candidate = candidates[c];
            var candidateLength = _routeLength(
                sourceX,
                sourceY,
                sourceStubX,
                targetX,
                targetY,
                targetStubX,
                candidate.y
            );
            if (candidateLength < bestLength
                || (Math.abs(candidateLength - bestLength) < 0.01 && candidate.priority < best.priority)) {
                best = candidate;
                bestLength = candidateLength;
            }
        }

        return [
            {"x": sourceX, "y": sourceY},
            {"x": sourceStubX, "y": sourceY},
            {"x": sourceStubX, "y": best.y},
            {"x": targetStubX, "y": best.y},
            {"x": targetStubX, "y": targetY},
            {"x": targetX, "y": targetY}
        ];
    }

    function _buildFlowPipePoints(sourceX, sourceY, targetX, targetY, edge, sourceBounds, targetBounds, sourceSide, targetSide) {
        return EdgeMath.flowPipeRoute(
            {"x": sourceX, "y": sourceY},
            {"x": targetX, "y": targetY},
            {
                "sourceSide": String(sourceSide || edge && edge.source_anchor_side || edge && edge.source_port_side || ""),
                "targetSide": String(targetSide || edge && edge.target_anchor_side || edge && edge.target_port_side || ""),
                "sourceBounds": sourceBounds,
                "targetBounds": targetBounds,
                "laneBias": Number(edge && edge.lane_bias || 0.0)
            }
        );
    }

    function _previewIsFlow(connection) {
        if (!connection)
            return false;
        var sourceKind = String(connection.source_kind || "").trim().toLowerCase();
        var targetKind = String(connection.target_kind || "").trim().toLowerCase();
        if (sourceKind === "flow" && (!targetKind || targetKind === "flow"))
            return true;
        return !!String(connection.origin_side || "").trim()
            || !!String(connection.target_side || "").trim();
    }

    function _previewFallbackTargetSide(sourceX, sourceY, targetX, targetY) {
        var dx = Number(targetX) - Number(sourceX);
        var dy = Number(targetY) - Number(sourceY);
        if (Math.abs(dx) >= Math.abs(dy))
            return dx >= 0.0 ? "left" : "right";
        return dy >= 0.0 ? "top" : "bottom";
    }

    function _edgeGeometry(edge, nodeById) {
        var sxWorld = edge.sx;
        var syWorld = edge.sy;
        var txWorld = edge.tx;
        var tyWorld = edge.ty;
        var c1xWorld = edge.c1x;
        var c1yWorld = edge.c1y;
        var c2xWorld = edge.c2x;
        var c2yWorld = edge.c2y;
        var sourceState = root._edgeEndpointState(edge, "source", nodeById, {"x": txWorld, "y": tyWorld});
        var targetState = root._edgeEndpointState(
            edge,
            "target",
            nodeById,
            sourceState && sourceState.point ? sourceState.point : {"x": sxWorld, "y": syWorld}
        );
        sourceState = root._edgeEndpointState(
            edge,
            "source",
            nodeById,
            targetState && targetState.point ? targetState.point : {"x": txWorld, "y": tyWorld}
        );
        if (sourceState && sourceState.point) {
            c1xWorld += sourceState.point.x - sxWorld;
            c1yWorld += sourceState.point.y - syWorld;
            sxWorld = sourceState.point.x;
            syWorld = sourceState.point.y;
        }
        if (targetState && targetState.point) {
            c2xWorld += targetState.point.x - txWorld;
            c2yWorld += targetState.point.y - tyWorld;
            txWorld = targetState.point.x;
            tyWorld = targetState.point.y;
        }

        var pipePoints = edge.pipe_points || [];
        if (edge.route === "pipe") {
            var sourceBounds = sourceState ? sourceState.bounds : null;
            var targetBounds = targetState ? targetState.bounds : null;
            var sourceSide = sourceState ? sourceState.side : root._normalizedCardinalSide(edge.source_anchor_side, edge.source_port_side);
            var targetSide = targetState ? targetState.side : root._normalizedCardinalSide(edge.target_anchor_side, edge.target_port_side);
            pipePoints = flowStylePolicy.edgeIsFlow(edge)
                ? _buildFlowPipePoints(
                    sxWorld,
                    syWorld,
                    txWorld,
                    tyWorld,
                    edge,
                    sourceBounds,
                    targetBounds,
                    sourceSide,
                    targetSide
                )
                : _buildLegacyPipePoints(
                    edge,
                    sourceBounds,
                    targetBounds,
                    sxWorld,
                    syWorld,
                    txWorld,
                    tyWorld,
                    nodeById
                );
            var pipeHandles = EdgeMath.pipeControlHandles(pipePoints);
            c1xWorld = pipeHandles.first.x;
            c1yWorld = pipeHandles.first.y;
            c2xWorld = pipeHandles.last.x;
            c2yWorld = pipeHandles.last.y;
        }

        return {
            "sx": sxWorld,
            "sy": syWorld,
            "tx": txWorld,
            "ty": tyWorld,
            "c1x": c1xWorld,
            "c1y": c1yWorld,
            "c2x": c2xWorld,
            "c2y": c2yWorld,
            "route": edge.route,
            "pipe_points": pipePoints
        };
    }

    function _geometrySceneBounds(geometry) {
        if (!geometry)
            return null;
        if (geometry.route === "pipe")
            return root._sceneBoundsForPoints(geometry.pipe_points || []);
        return root._sceneBoundsForPoints([
            {"x": geometry.sx, "y": geometry.sy},
            {"x": geometry.c1x, "y": geometry.c1y},
            {"x": geometry.c2x, "y": geometry.c2y},
            {"x": geometry.tx, "y": geometry.ty}
        ]);
    }

    function _edgeCullState(edge, nodeById, viewportBounds) {
        var geometry = root._getCachedEdgeGeometry(edge, nodeById);
        var sceneBounds = root._geometrySceneBounds(geometry);
        var visibleBounds = viewportBounds || root._expandedVisibleSceneBounds();
        var culled = sceneBounds && visibleBounds ? !root._rectIntersects(sceneBounds, visibleBounds) : false;
        return {
            "culled": culled,
            "geometry": culled ? null : geometry
        };
    }

    function _dragGeometry(connection) {
        if (!connection)
            return null;
        var sourceX = Number(connection.start_x);
        var sourceY = Number(connection.start_y);
        var targetX = Number(connection.target_x);
        var targetY = Number(connection.target_y);
        var dominantDistance = Math.max(Math.abs(targetX - sourceX), Math.abs(targetY - sourceY));
        var handle = Math.max(42.0, Math.min(170.0, dominantDistance * 0.42));
        var sourceDirection = String(connection.source_direction || "out");
        var originSide = GraphNodeSurfaceMetrics.portCardinalSide({"side": connection.origin_side});
        var targetSide = GraphNodeSurfaceMetrics.portCardinalSide({"side": connection.target_side});
        var flowPreview = root._previewIsFlow(connection);
        if (flowPreview) {
            var nodeById = root._getNodeMap();
            var sourceBounds = connection.source_node_id ? root._nodeBounds(connection.source_node_id, null, nodeById) : null;
            var targetBounds = connection.target_node_id ? root._nodeBounds(connection.target_node_id, null, nodeById) : null;
            var resolvedSourceSide = EdgeMath.normalizeCardinalSide(
                originSide,
                sourceDirection === "in" ? "left" : "right"
            );
            var resolvedTargetSide = EdgeMath.normalizeCardinalSide(
                targetSide,
                root._previewFallbackTargetSide(
                    sourceX,
                    sourceY,
                    targetX,
                    targetY
                )
            );
            var pipePoints = EdgeMath.flowPipeRoute(
                {"x": sourceX, "y": sourceY},
                {"x": targetX, "y": targetY},
                {
                    "sourceSide": resolvedSourceSide,
                    "targetSide": resolvedTargetSide,
                    "sourceBounds": sourceBounds,
                    "targetBounds": targetBounds,
                    "laneBias": 0.0
                }
            );
            var pipeHandles = EdgeMath.pipeControlHandles(pipePoints);
            return {
                "sx": sourceX,
                "sy": sourceY,
                "tx": targetX,
                "ty": targetY,
                "c1x": pipeHandles.first.x,
                "c1y": pipeHandles.first.y,
                "c2x": pipeHandles.last.x,
                "c2y": pipeHandles.last.y,
                "route": "pipe",
                "pipe_points": pipePoints
            };
        }
        var sourceNormal = originSide
            ? GraphNodeSurfaceMetrics.flowchartAnchorNormal(originSide)
            : (sourceDirection === "in" ? {"x": -1.0, "y": 0.0} : {"x": 1.0, "y": 0.0});
        var targetNormal = targetSide
            ? GraphNodeSurfaceMetrics.flowchartAnchorNormal(targetSide)
            : (sourceDirection === "in" ? {"x": 1.0, "y": 0.0} : {"x": -1.0, "y": 0.0});
        return {
            "sx": sourceX,
            "sy": sourceY,
            "tx": targetX,
            "ty": targetY,
            "c1x": sourceX + sourceNormal.x * handle,
            "c1y": sourceY + sourceNormal.y * handle,
            "c2x": targetX + targetNormal.x * handle,
            "c2y": targetY + targetNormal.y * handle,
            "route": "bezier",
            "pipe_points": []
        };
    }

    function _buildVisibleEdgeSnapshots(revision) {
        var snapshots = [];
        var snapshotById = {};
        var edgesList = root.edges || [];
        var nodeById = root._getNodeMap();
        var viewportBounds = root._expandedVisibleSceneBounds();
        var viewportTransform = viewportMath.viewportTransform();

        for (var i = 0; i < edgesList.length; i++) {
            var edge = edgesList[i];
            if (!edge || !edge.edge_id)
                continue;
            var edgeId = String(edge.edge_id);
            var cullState = root._edgeCullState(edge, nodeById, viewportBounds);
            var geometry = cullState && !cullState.culled ? cullState.geometry : null;
            var selected = root._isSelected(edgeId);
            var previewed = root.previewEdgeId && root.previewEdgeId === edgeId;
            var labelMode = flowLabelPolicy.flowLabelMode(edge);
            var snapshot = {
                "revision": revision,
                "edgeId": edgeId,
                "edgeData": edge,
                "culled": cullState ? Boolean(cullState.culled) : false,
                "geometry": geometry,
                "selected": selected,
                "previewed": Boolean(previewed),
                "flowEdge": flowStylePolicy.edgeIsFlow(edge),
                "labelText": flowLabelPolicy.edgeLabelText(edge),
                "labelMode": labelMode,
                "drawOrderIndex": i,
                "crossingBreaks": [],
                "crossingSamplePoints": [],
                "labelAnchorScene": labelMode !== "hidden" && geometry
                    ? flowLabelPolicy.flowLabelAnchorScene(geometry)
                    : null
            };
            snapshots.push(snapshot);
            snapshotById[edgeId] = snapshot;
        }

        snapshots = edgeCrossingPolicy.applyCrossingMetadata(snapshots, viewportTransform);

        return {
            "snapshots": snapshots,
            "snapshotById": snapshotById
        };
    }

    function _refreshVisibleEdgeSnapshots() {
        var nextRevision = root._visibleEdgeSnapshotRevision + 1;
        var model = root._buildVisibleEdgeSnapshots(nextRevision);
        root._visibleEdgeSnapshots = model.snapshots;
        root._visibleEdgeSnapshotById = model.snapshotById;
        root._visibleEdgeSnapshotRevision = nextRevision;
    }

    function _visibleEdgeSnapshot(edgeId) {
        var normalized = String(edgeId || "");
        if (!normalized)
            return null;
        return root._visibleEdgeSnapshotById[normalized] || null;
    }

    function _isSelected(edgeId) {
        return (root.selectedEdgeIds || []).indexOf(edgeId) >= 0;
    }

    function _edgeDistanceAtScreen(geometry, screenX, screenY, viewportTransform) {
        if (!geometry)
            return Number.POSITIVE_INFINITY;
        var sceneX = viewportMath.screenToSceneX(screenX, viewportTransform);
        var sceneY = viewportMath.screenToSceneY(screenY, viewportTransform);
        if (geometry.route === "pipe") {
            return EdgeMath.distancePolyline(sceneX, sceneY, geometry.pipe_points || []);
        }

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

    function edgeAtScreen(screenX, screenY) {
        var snapshots = root._visibleEdgeSnapshots || [];
        if (!snapshots.length && (root.edges || []).length) {
            root._refreshVisibleEdgeSnapshots();
            snapshots = root._visibleEdgeSnapshots || [];
        }
        if (!snapshots.length)
            return "";
        var viewportTransform = viewportMath.viewportTransform();
        var bestId = "";
        var bestDistance = Number.POSITIVE_INFINITY;
        var threshold = viewportMath.screenLengthToScene(8.0, viewportTransform);
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

    Canvas {
        id: edgeCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var zoom = viewportMath.zoomValue();
            var snapshots = root._visibleEdgeSnapshots || [];
            var viewportTransform = viewportMath.viewportTransform();

            ctx.save();
            viewportMath.applyViewportTransform(ctx, viewportTransform);

            for (var i = 0; i < snapshots.length; i++) {
                var snapshot = snapshots[i];
                if (!snapshot || snapshot.culled || !snapshot.geometry)
                    continue;
                var edge = snapshot.edgeData;
                var geometry = snapshot.geometry;
                var selected = snapshot.selected;
                var previewed = snapshot.previewed;
                var flowEdge = snapshot.flowEdge;
                var crossingBreaks = snapshot.crossingBreaks || [];
                ctx.save();
                ctx.beginPath();
                if (crossingBreaks.length > 0)
                    edgeRenderer.traceBrokenGeometry(ctx, geometry, snapshot.crossingSamplePoints || [], crossingBreaks);
                else
                    edgeRenderer.traceGeometry(ctx, geometry);

                if (flowEdge) {
                    var flowStrokeColor = flowStylePolicy.flowStrokeColor(edge, selected, previewed);
                    ctx.strokeStyle = flowStrokeColor;
                    ctx.lineWidth = viewportMath.screenLengthToScene(
                        flowStylePolicy.flowStrokeWidth(edge, selected, previewed, zoom),
                        viewportTransform
                    );
                    ctx.setLineDash(
                        viewportMath.dashPatternToScene(flowStylePolicy.flowDashPattern(edge, zoom), viewportTransform)
                    );
                    ctx.stroke();
                    edgeRenderer.drawFlowArrowHead(ctx, geometry, edge, flowStrokeColor, zoom, viewportTransform);
                } else {
                    ctx.strokeStyle = selected
                        ? root.selectedStrokeColor
                        : (previewed ? root.previewStrokeColor : (edge.color || root.fallbackStrokeColor));
                    ctx.lineWidth = viewportMath.screenLengthToScene(
                        Math.max(1.0, (selected ? 3.0 : (previewed ? 2.8 : 2.0)) * zoom),
                        viewportTransform
                    );
                    ctx.stroke();
                }
                ctx.restore();
            }

            var liveDrag = root.dragConnection;
            if (liveDrag) {
                var dragGeometry = root._dragGeometry(liveDrag);
                if (dragGeometry) {
                    ctx.save();
                    ctx.beginPath();
                    edgeRenderer.traceGeometry(ctx, dragGeometry);
                    ctx.strokeStyle = liveDrag.valid_drop ? root.validDragStrokeColor : root.invalidDragStrokeColor;
                    ctx.lineWidth = viewportMath.screenLengthToScene(
                        Math.max(1.0, (liveDrag.valid_drop ? 2.7 : 2.0) * zoom),
                        viewportTransform
                    );
                    ctx.setLineDash(
                        viewportMath.dashPatternToScene(
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

    Item {
        id: flowLabelLayer
        anchors.fill: parent

        Repeater {
            model: root.edges || []

            delegate: Item {
                objectName: "graphEdgeFlowLabelItem"
                property var edgeData: modelData
                property string edgeId: String(edgeData && edgeData.edge_id || "")
                property var snapshotData: edgeId ? root._visibleEdgeSnapshot(edgeId) : null
                property string labelText: snapshotData ? String(snapshotData.labelText || "") : ""
                property string labelMode: snapshotData ? String(snapshotData.labelMode || "hidden") : "hidden"
                property bool labelRequested: labelMode !== "hidden"
                property var snapshotRevision: snapshotData ? snapshotData.revision : 0
                property bool culledByViewport: labelRequested && snapshotData ? Boolean(snapshotData.culled) : false
                property bool pillVisible: labelMode === "pill"
                property real anchorScreenX: labelAnchor ? labelAnchor.screen_x : 0.0
                property real anchorScreenY: labelAnchor ? labelAnchor.screen_y : 0.0
                property var geometry: labelRequested && !culledByViewport && snapshotData ? snapshotData.geometry : null
                property var labelAnchorScene: labelRequested && !culledByViewport && snapshotData
                    ? snapshotData.labelAnchorScene
                    : null
                property var labelAnchor: labelAnchorScene ? flowLabelPolicy.flowLabelAnchor(labelAnchorScene) : null
                property bool hitTestMatches: visible
                property bool selectedEdge: snapshotData ? Boolean(snapshotData.selected) : false
                property bool previewedEdge: snapshotData ? Boolean(snapshotData.previewed) : false
                property real horizontalPadding: pillVisible ? 9.0 : 1.0
                property real verticalPadding: pillVisible ? 5.0 : 0.0
                property real maximumTextWidth: pillVisible ? 180.0 : 110.0
                visible: labelRequested && !culledByViewport && labelAnchor !== null
                width: labelTextItem.width + horizontalPadding * 2.0
                height: labelTextItem.height + verticalPadding * 2.0
                x: anchorScreenX - width * 0.5
                y: anchorScreenY - height * 0.5

                Rectangle {
                    objectName: "graphEdgeFlowLabelPill"
                    anchors.fill: parent
                    radius: height * 0.5
                    visible: parent.pillVisible
                    color: flowLabelPolicy.flowLabelBackgroundColor(parent.edgeData)
                    border.width: 1
                    border.color: flowLabelPolicy.flowLabelBorderColor(
                        parent.edgeData,
                        parent.selectedEdge,
                        parent.previewedEdge
                    )
                }

                Text {
                    id: labelTextItem
                    objectName: "graphEdgeFlowLabelText"
                    anchors.centerIn: parent
                    width: Math.min(parent.maximumTextWidth, implicitWidth)
                    text: parent.labelText
                    color: flowLabelPolicy.flowLabelTextColor(parent.edgeData)
                    font.pixelSize: parent.pillVisible ? 12 : 11
                    font.weight: parent.pillVisible ? Font.DemiBold : Font.Medium
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    MouseArea {
        id: edgeHitArea
        anchors.fill: parent
        enabled: root.inputEnabled
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        propagateComposedEvents: true

        onPressed: function(mouse) {
            var edgeId = root.edgeAtScreen(mouse.x, mouse.y);
            if (!edgeId) {
                mouse.accepted = false;
                return;
            }
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            if (mouse.button === Qt.LeftButton) {
                root.edgeClicked(edgeId, additive);
            } else if (mouse.button === Qt.RightButton) {
                root.edgeContextRequested(edgeId, mouse.x, mouse.y);
            }
            mouse.accepted = true;
        }
    }

    onEdgesChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onNodesChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onDragOffsetsChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onLiveNodeGeometryChanged: { _invalidateGeometryCache(); requestRedraw(); }
    onSelectedEdgeIdsChanged: requestRedraw()
    onPreviewEdgeIdChanged: requestRedraw()
    onDragConnectionChanged: requestRedraw()
    onEdgePaletteChanged: requestRedraw()
    onShellPaletteChanged: requestRedraw()
    onPortKindPaletteChanged: requestRedraw()
    onEdgeCrossingStyleChanged: requestRedraw()
    onPerformanceModeChanged: requestRedraw()
    onTransientPerformanceActivityActiveChanged: {
        if (root.transientPerformanceActivityActive)
            markViewStateRedrawDirty()
        else
            requestRedraw()
    }
    onTransientDegradedWindowActiveChanged: requestRedraw()
    onEdgeLabelSimplificationActiveChanged: requestRedraw()

}
