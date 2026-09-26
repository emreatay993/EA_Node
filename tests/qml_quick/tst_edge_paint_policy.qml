import QtQuick 2.15
import QtTest 1.3
import "../../ea_node_editor/ui_qml/components/graph/EdgeMath.js" as EdgeMath
import "../../ea_node_editor/ui_qml/components/graph/EdgePaintPolicy.js" as EdgePaintPolicy

TestCase {
    id: testCase
    name: "EdgePaintPolicy"
    width: 320
    height: 240
    visible: true
    when: windowShown

    QtObject {
        id: edgeLayer
        property string activeDefaultStrokeColor: "#a7adb2"
        property string activeSelectedStrokeColor: "#75b4e7"
        property string selectedStrokeColor: "#f0f4fb"
        property string previewStrokeColor: "#60cdff"
        property string fallbackStrokeColor: "#7aa8ff"
        property string inactiveStrokeColor: "#7f8796"
        property string dangerStrokeColor: "#ff543e"
        property string flowDefaultStrokeColor: "#95a0b8"
        property string validDragStrokeColor: "#60cdff"
        property string invalidDragStrokeColor: "#d0d5de"
        property bool wireSelectionModeHeld: false

        function edgeValueState(edge) {
            return String(edge && edge.test_state || "current")
        }

        function dragConnectionActiveDataWire(connection) {
            return Boolean(connection && connection.active_data_wire)
        }
    }

    function edge(overrides) {
        var value = {
            "active_data_wire": true,
            "data_access": "item",
            "enabled": true,
            "data_type_warning": false,
            "visual_style": {"display_mode": "default"},
            "color": "#7aa8ff",
            "test_state": "current"
        }
        var updates = overrides || {}
        for (var key in updates)
            value[key] = updates[key]
        return value
    }

    function snapshot(overrides) {
        var value = {
            "selected": false,
            "previewed": false,
            "replacementPreviewed": false,
            "sourceNodeSelected": false,
            "targetNodeSelected": false
        }
        var updates = overrides || {}
        for (var key in updates)
            value[key] = updates[key]
        return value
    }

    function paint(edgeOverrides, snapshotOverrides, zoom) {
        return EdgePaintPolicy.standardEdgePaintState(
            edgeLayer,
            snapshot(snapshotOverrides),
            edge(edgeOverrides),
            zoom === undefined ? 1.0 : zoom
        )
    }

    function test_standard_structure_display_and_marker_state() {
        var item = paint({}, {})
        compare(item.structure, "single")
        compare(item.displayMode, "default")
        compare(item.strokeCount, 1)
        compare(JSON.stringify(item.strokeOffsetsScreenPx), "[0]")
        compare(JSON.stringify(item.dashPatternScreenPx), "[]")
        compare(item.strokeColor, edgeLayer.activeDefaultStrokeColor)

        var faintList = paint({
            "data_access": "list",
            "visual_style": {"display_mode": "faint"}
        }, {})
        compare(faintList.structure, "list")
        compare(faintList.strokeAlpha, 0.30)
        compare(JSON.stringify(faintList.dashPatternScreenPx), "[1,4]")

        var tree = paint({"data_access": "tree"}, {})
        compare(tree.structure, "tree")
        compare(JSON.stringify(tree.dashPatternScreenPx), "[8,5]")

        var empty = paint({"data_access": "tree", "test_state": "empty"}, {})
        compare(empty.structure, "empty")
        compare(empty.strokeCount, 2)
        compare(JSON.stringify(empty.strokeOffsetsScreenPx), "[-1.5,1.5]")

        var disabled = paint({"enabled": false, "data_access": "list"}, {})
        verify(disabled.disabledMarkerVisible)
        compare(disabled.disabledMarkerColor, edgeLayer.dangerStrokeColor)
    }

    function test_hidden_selection_and_invalid_gradient_priority() {
        var hidden = paint({"visual_style": {"display_mode": "hidden"}}, {})
        verify(!hidden.bodyVisible)
        verify(hidden.endpointArcsVisible)

        var selectedHidden = paint(
            {"visual_style": {"display_mode": "hidden"}},
            {"selected": true}
        )
        verify(selectedHidden.bodyVisible)
        verify(!selectedHidden.endpointArcsVisible)
        compare(selectedHidden.strokeColor, edgeLayer.activeSelectedStrokeColor)

        var invalid = paint(
            {"data_type_warning": true},
            {"sourceNodeSelected": true}
        )
        verify(invalid.invalidGradient)
        compare(invalid.gradientKind, "invalid_target")
        var stops = EdgePaintPolicy.standardEdgeGradientStops(edgeLayer, invalid, 0.2)
        compare(stops.length, 3)
        compare(stops[0].color, edgeLayer.activeSelectedStrokeColor)
        compare(stops[2].color, edgeLayer.dangerStrokeColor)
    }

    function test_active_base_color_ignores_projected_edge_color() {
        var edgeColors = ["#253247", "#e5e7eb"]
        for (var index = 0; index < edgeColors.length; ++index) {
            var normal = paint({"color": edgeColors[index]}, {})
            compare(normal.baseColor, edgeLayer.activeDefaultStrokeColor)
            compare(normal.strokeColor, edgeLayer.activeDefaultStrokeColor)
            verify(normal.baseColor !== edgeColors[index])

            var empty = paint({"color": edgeColors[index], "test_state": "empty"}, {})
            compare(empty.baseColor, edgeLayer.activeDefaultStrokeColor)
            compare(empty.strokeColor, edgeLayer.activeDefaultStrokeColor)
            compare(empty.structure, "empty")

            var disabled = paint({"color": edgeColors[index], "enabled": false}, {})
            compare(disabled.baseColor, edgeLayer.activeDefaultStrokeColor)
            compare(disabled.strokeColor, edgeLayer.activeDefaultStrokeColor)
            compare(disabled.strokeAlpha, 1.0)

            var invalid = paint({"color": edgeColors[index], "data_type_warning": true}, {})
            compare(invalid.baseColor, edgeLayer.activeDefaultStrokeColor)
            compare(invalid.strokeColor, edgeLayer.activeDefaultStrokeColor)
            verify(invalid.invalidGradient)
            compare(invalid.gradientKind, "invalid_target")
        }
    }

    function test_flow_and_drag_preview_policy() {
        var flow = {
            "edge_family": "flow",
            "flow_style": {
                "stroke_pattern": "dotted",
                "stroke_color": "#123456",
                "stroke_width": 2.5,
                "arrow_head": "open"
            }
        }
        verify(EdgePaintPolicy.edgeIsFlow(flow))
        compare(EdgePaintPolicy.flowStrokePattern(flow), "dotted")
        compare(EdgePaintPolicy.flowArrowHead(flow), "open")
        compare(EdgePaintPolicy.flowStrokeColor(edgeLayer, flow, false, false), "#123456")
        compare(EdgePaintPolicy.flowStrokeWidth(flow, false, false, 2.0), 5.0)
        compare(JSON.stringify(EdgePaintPolicy.flowDashPattern(flow, 2.0)), "[2,8]")

        var append = {"connection_mode": "append", "valid_drop": true, "active_data_wire": true}
        compare(EdgePaintPolicy.dragConnectionMode(append), "append")
        compare(EdgePaintPolicy.dragConnectionMarkerText(edgeLayer, append), "+")
        verify(EdgePaintPolicy.dragConnectionMarkerVisible(edgeLayer, append))
        verify(EdgePaintPolicy.dragConnectionMarkerPlain(edgeLayer, append))
        compare(
            EdgePaintPolicy.dragConnectionMarkerColor(edgeLayer, append, "#ffffff"),
            "#419248"
        )
        compare(JSON.stringify(EdgePaintPolicy.dragConnectionDashPattern(edgeLayer, append, 1.0)), "[]")
    }

    function test_passive_standard_and_drag_preview_state_stay_legacy() {
        var passive = paint({
            "active_data_wire": false,
            "color": "#445566",
            "stroke_count": 1
        }, {"selected": true}, 0.5)
        compare(passive.strokeColor, edgeLayer.selectedStrokeColor)
        compare(passive.strokeWidthScreenPx, 1.5)

        var passiveDisabled = paint({
            "active_data_wire": false,
            "enabled": false,
            "color": "#445566",
            "stroke_count": 1
        }, {}, 0.5)
        compare(passiveDisabled.strokeAlpha, 1.0)
        verify(!passiveDisabled.disabledMarkerVisible)

        var activeModes = ["connect", "replace", "append", "copy", "noop"]
        for (var activeIndex = 0; activeIndex < activeModes.length; ++activeIndex) {
            var activeDrag = {
                "connection_mode": activeModes[activeIndex],
                "source_kind": "data",
                "active_data_wire": true,
                "valid_drop": true
            }
            compare(
                JSON.stringify(EdgePaintPolicy.dragConnectionDashPattern(edgeLayer, activeDrag, 1.0)),
                "[]"
            )
            compare(
                EdgePaintPolicy.dragConnectionStrokeColor(edgeLayer, activeDrag),
                edgeLayer.activeDefaultStrokeColor
            )
            compare(
                EdgePaintPolicy.dragConnectionStrokeWidthScreenPx(edgeLayer, activeDrag, 1.75),
                2.0
            )
            if (activeModes[activeIndex] === "noop") {
                compare(EdgePaintPolicy.dragConnectionMarkerText(edgeLayer, activeDrag), "")
                verify(!EdgePaintPolicy.dragConnectionMarkerVisible(edgeLayer, activeDrag))
            }
        }

        var activeInterruptedModes = ["disconnect", "rewire"]
        for (var interruptedIndex = 0; interruptedIndex < activeInterruptedModes.length; ++interruptedIndex) {
            var interrupted = {
                "connection_mode": activeInterruptedModes[interruptedIndex],
                "source_kind": "data",
                "active_data_wire": true,
                "valid_drop": false
            }
            verify(EdgePaintPolicy.dragConnectionDashPattern(edgeLayer, interrupted, 1.0).length > 0)
            compare(
                EdgePaintPolicy.dragConnectionStrokeColor(edgeLayer, interrupted),
                edgeLayer.activeDefaultStrokeColor
            )
            compare(EdgePaintPolicy.dragConnectionMarkerText(edgeLayer, interrupted), "")
            verify(!EdgePaintPolicy.dragConnectionMarkerVisible(edgeLayer, interrupted))
        }

        var legacyModes = [
            {"mode": "replace", "marker": "R"},
            {"mode": "noop", "marker": "="},
            {"mode": "append", "marker": "+"}
        ]
        for (var legacyIndex = 0; legacyIndex < legacyModes.length; ++legacyIndex) {
            var legacy = {
                "connection_mode": legacyModes[legacyIndex].mode,
                "source_kind": "flow",
                "active_data_wire": false,
                "valid_drop": true
            }
            compare(
                EdgePaintPolicy.dragConnectionMarkerText(edgeLayer, legacy),
                legacyModes[legacyIndex].marker
            )
            verify(EdgePaintPolicy.dragConnectionMarkerVisible(edgeLayer, legacy))
            verify(!EdgePaintPolicy.dragConnectionMarkerPlain(edgeLayer, legacy))
            compare(
                EdgePaintPolicy.dragConnectionMarkerColor(edgeLayer, legacy, edgeLayer.validDragStrokeColor),
                edgeLayer.validDragStrokeColor
            )
            verify(EdgePaintPolicy.dragConnectionDashPattern(edgeLayer, legacy, 1.0).length > 0)
        }
    }

    function near(actual, expected, tolerance, message) {
        verify(Math.abs(Number(actual) - Number(expected)) <= (tolerance === undefined ? 0.001 : tolerance),
            (message || "") + " expected " + expected + " got " + actual)
    }

    function test_flow_arrow_ends_default_and_normalize() {
        var plain = {"edge_family": "flow", "flow_style": {}}
        compare(EdgePaintPolicy.flowArrowHead(plain), "filled")
        compare(EdgePaintPolicy.flowArrowTail(plain), "none")
        var both = {"edge_family": "flow", "flow_style": {"arrow_head": " OPEN ", "arrow_tail": "filled"}}
        compare(EdgePaintPolicy.flowArrowHead(both), "open")
        compare(EdgePaintPolicy.flowArrowTail(both), "filled")
        var legacy = {"edge_family": "flow", "visual_style": {"arrow": {"kind": "none"}}}
        compare(EdgePaintPolicy.flowArrowHead(legacy), "none")
        var unknown = {"edge_family": "flow", "flow_style": {"arrow_head": "diamond", "arrow_tail": "circle"}}
        compare(EdgePaintPolicy.flowArrowHead(unknown), "filled")
        compare(EdgePaintPolicy.flowArrowTail(unknown), "none")
        compare(JSON.stringify(EdgePaintPolicy.FLOW_ARROW_KINDS), JSON.stringify(["filled", "open", "none"]))
    }

    function test_flow_arrow_heads_scale_with_style_width_and_shorten_the_stroke() {
        compare(EdgePaintPolicy.flowArrowMarkerMetrics("none", 2.0, 2.0, 0.0), null)
        var thin = EdgePaintPolicy.flowArrowMarkerMetrics("filled", 2.0, 2.0, 0.0)
        near(thin.extent, 8.0)
        near(thin.halfWidth, 4.5)
        var thick = EdgePaintPolicy.flowArrowMarkerMetrics("filled", 8.0, 8.0, 0.0)
        near(thick.extent, 26.0)
        near(thick.halfWidth / thick.extent, 0.5625)
        // Selection thickens the stroke, not the head: size follows the style width only.
        var selected = EdgePaintPolicy.flowArrowMarkerMetrics("filled", 2.0, 3.0, 0.0)
        near(selected.extent, thin.extent)
        // Zoomed-out floor keeps the head legible.
        near(EdgePaintPolicy.flowArrowMarkerMetrics("filled", 1.0, 1.0, 12.0).extent, 12.0)

        // The stroke ends inside a filled head (hidden under the fill) ...
        verify(thin.filled)
        verify(thin.lineInset > thin.offset && thin.lineInset < thin.extent)
        // ... and at an open head's apex, drawn at the edge width.
        var open = EdgePaintPolicy.flowArrowMarkerMetrics("open", 4.0, 4.0, 0.0)
        verify(!open.filled)
        near(open.strokeWidth, 4.0)
        near(open.lineInset, open.offset)
        near(open.offset, 2.0)

        var edge = {"edge_family": "flow", "flow_style": {"stroke_width": 4, "arrow_tail": "open"}}
        var markers = EdgePaintPolicy.flowArrowMarkers(edge, 4.0, 8.0)
        compare(markers.start.kind, "open")
        compare(markers.end.kind, "filled")
        near(markers.end.extent, 14.0)
    }

    function test_flow_arrow_shape_points_along_the_path_toward_the_tip() {
        var metrics = EdgePaintPolicy.flowArrowMarkerMetrics("filled", 2.0, 2.0, 0.0)
        var end = EdgePaintPolicy.flowArrowMarkerShape(metrics, 100.0, 50.0, 1.0, 0.0)
        verify(end.closed && end.filled)
        compare(end.points.length, 3)
        near(end.points[1].x, 100.0 - metrics.offset)
        near(end.points[1].y, 50.0)
        near(end.points[0].x, 100.0 - metrics.offset - metrics.extent)
        near(Math.abs(end.points[0].y - end.points[2].y), 2.0 * metrics.halfWidth)
        // A start arrow passes the reversed start direction, so it points back at the source.
        var start = EdgePaintPolicy.flowArrowMarkerShape(metrics, 0.0, 50.0, -1.0, 0.0)
        near(start.points[1].x, metrics.offset)
        verify(start.points[0].x > start.points[1].x)
        var open = EdgePaintPolicy.flowArrowMarkerShape(
            EdgePaintPolicy.flowArrowMarkerMetrics("open", 2.0, 2.0, 0.0), 0.0, 0.0, 0.0, 1.0)
        verify(!open.closed && !open.filled)
        near(open.points[1].y, -1.0)
        compare(EdgePaintPolicy.flowArrowMarkerShape(metrics, 0.0, 0.0, 0.0, 0.0), null)
    }

    function test_flow_edge_paint_state_is_what_both_renderers_paint() {
        var edge = {
            "edge_family": "flow",
            "flow_style": {"stroke_width": 3, "stroke_pattern": "dashed", "arrow_tail": "filled", "arrow_head": "open"}
        }
        var state = EdgePaintPolicy.flowEdgePaintState(edgeLayer, snapshot({}), edge, 0.5)
        verify(state.flowEdge)
        compare(state.strokeColor, edgeLayer.flowDefaultStrokeColor)
        near(state.strokeWidthScreenPx, 1.5)
        // Scene units: the Canvas strokes these under the viewport scale.
        near(state.strokeWidthScene, 3.0)
        compare(JSON.stringify(state.dashPatternScreenPx), JSON.stringify(EdgePaintPolicy.flowDashPattern(edge, 0.5)))
        compare(state.arrowTail, "filled")
        compare(state.arrowHead, "open")
        near(state.arrowTailExtent, state.markers.start.extent)
        near(state.lineTrimStart, state.markers.start.lineInset)
        near(state.lineTrimEnd, state.markers.end.lineInset)
        // Markers keep 6 screen px, never under 8 scene units, however far out the view zooms.
        near(EdgePaintPolicy.flowMarkerMinLength(1.0), 8.0)
        near(EdgePaintPolicy.flowMarkerMinLength(0.25), 24.0)
        near(EdgePaintPolicy.flowEdgePaintState(edgeLayer, snapshot({}), edge, 0.25).markers.end.extent, 24.0)

        var selected = EdgePaintPolicy.flowEdgePaintState(edgeLayer, snapshot({"selected": true}), {"edge_family": "flow", "flow_style": {}}, 1.0)
        verify(selected.selected)
        compare(selected.strokeColor, edgeLayer.selectedStrokeColor)
        near(selected.strokeWidthScreenPx, 3.0)
        compare(selected.arrowTail, "none")
        near(selected.lineTrimStart, 0.0)
    }

    function pieceLength(piece) {
        if (piece.cubic) {
            var c = piece.cubic
            return EdgeMath.geometryLength({
                "route": "bezier", "sx": c[0].x, "sy": c[0].y, "c1x": c[1].x, "c1y": c[1].y,
                "c2x": c[2].x, "c2y": c[2].y, "tx": c[3].x, "ty": c[3].y
            })
        }
        return EdgeMath.polylineMetrics(piece.points).totalLength
    }

    function test_edge_body_pieces_trim_ends_and_cut_gaps() {
        var bezier = {"route": "bezier", "sx": 0, "sy": 0, "c1x": 40, "c1y": 0, "c2x": 60, "c2y": 80, "tx": 100, "ty": 80}
        var whole = EdgeMath.edgeBodyPieces(bezier, [], [], 0.0, 0.0)
        compare(whole.length, 1)
        compare(whole[0].cubic.length, 4)
        near(whole[0].cubic[3].x, 100.0)
        var trimmed = EdgeMath.edgeBodyPieces(bezier, [], [], 5.0, 12.0)
        var expected = EdgeMath.trimGeometry(bezier, 5.0, 12.0)
        near(trimmed[0].cubic[0].x, expected.sx)
        near(trimmed[0].cubic[3].y, expected.ty)

        // Pipes stay one connected polyline, so a dash keeps its phase through corners.
        var pipe = {"route": "pipe", "pipe_points": [{"x": 0, "y": 0}, {"x": 60, "y": 0}, {"x": 60, "y": 40}]}
        var pipePieces = EdgeMath.edgeBodyPieces(pipe, [], [], 0.0, 10.0)
        compare(pipePieces.length, 1)
        compare(pipePieces[0].points.length, 3)
        near(pipePieces[0].points[2].y, 30.0)

        // Gaps (crossing or label breaks along the samples) split the body into pieces; the
        // end trims become gaps too, and a corner inside a piece stays one run.
        var samples = pipe.pipe_points
        var gaps = [{"startDistance": 20.0, "endDistance": 30.0}]
        var pieces = EdgeMath.edgeBodyPieces(pipe, samples, gaps, 4.0, 6.0)
        compare(pieces.length, 2)
        near(pieces[0].points[0].x, 4.0)
        near(pieces[0].points[pieces[0].points.length - 1].x, 20.0)
        near(pieces[1].points[0].x, 30.0)
        compare(pieces[1].points.length, 3)
        near(pieces[1].points[2].y, 34.0)
        near(pieceLength(pieces[0]) + pieceLength(pieces[1]), 100.0 - 10.0 - 4.0 - 6.0)
        // Overlapping gaps merge; a gap covering everything leaves nothing to stroke.
        compare(EdgeMath.edgeBodyPieces(pipe, samples, [{"startDistance": 10, "endDistance": 50}, {"startDistance": 40, "endDistance": 70}], 0, 0).length, 2)
        compare(EdgeMath.edgeBodyPieces(pipe, samples, [{"startDistance": -5, "endDistance": 105}], 0, 0).length, 0)
        compare(EdgeMath.edgeBodyPieces(pipe, [], [], 60.0, 40.0).length, 0)
    }

    function test_hidden_endpoint_arcs_face_along_the_path_with_end_colors() {
        var pipe = {"route": "pipe", "pipe_points": [{"x": 0, "y": 0}, {"x": 0, "y": 50}, {"x": 80, "y": 50}]}
        var frames = EdgeMath.endpointArcFrames(pipe, 4.0)
        near(frames.source.x, 0.0)
        near(frames.source.angle, Math.PI * 0.5)
        near(frames.target.x, 80.0)
        near(Math.abs(frames.target.angle), Math.PI)
        compare(EdgeMath.endpointArcFrames({"route": "pipe", "pipe_points": []}, 4.0), null)

        compare(JSON.stringify(EdgePaintPolicy.HIDDEN_ENDPOINT_ARC_RADII_SCREEN_PX), "[9,12,15]")
        var hidden = paint({"visual_style": {"display_mode": "hidden"}}, {})
        var plain = EdgePaintPolicy.hiddenEndpointArcColors(edgeLayer, hidden)
        compare(plain.source, edgeLayer.activeDefaultStrokeColor)
        compare(plain.target, edgeLayer.activeDefaultStrokeColor)
        var selectedSource = EdgePaintPolicy.hiddenEndpointArcColors(
            edgeLayer, paint({"visual_style": {"display_mode": "hidden"}}, {"sourceNodeSelected": true}))
        compare(selectedSource.source, edgeLayer.activeSelectedStrokeColor)
        var invalid = EdgePaintPolicy.hiddenEndpointArcColors(
            edgeLayer, paint({"visual_style": {"display_mode": "hidden"}, "data_type_warning": true}, {"targetNodeSelected": true}))
        compare(invalid.target, edgeLayer.dangerStrokeColor)
    }

    function test_trim_geometry_shortens_pipes_and_beziers_by_arc_length() {
        var pipe = {"route": "pipe", "pipe_points": [{"x": 0, "y": 0}, {"x": 60, "y": 0}, {"x": 60, "y": 40}]}
        near(EdgeMath.geometryLength(pipe), 100.0)
        var trimmedPipe = EdgeMath.trimGeometry(pipe, 10.0, 25.0)
        compare(trimmedPipe.route, "pipe")
        near(trimmedPipe.sx, 10.0)
        near(trimmedPipe.ty, 15.0)
        near(EdgeMath.geometryLength(trimmedPipe), 65.0)
        compare(EdgeMath.trimGeometry(pipe, 0.0, 0.0), pipe)
        compare(EdgeMath.trimGeometry(pipe, 60.0, 40.0), null)

        var bezier = {"route": "bezier", "sx": 0, "sy": 0, "c1x": 40, "c1y": 0, "c2x": 60, "c2y": 80, "tx": 100, "ty": 80}
        var total = EdgeMath.geometryLength(bezier)
        var trimmed = EdgeMath.trimGeometry(bezier, 0.0, 12.0)
        compare(trimmed.route, "bezier")
        near(trimmed.sx, 0.0)
        near(EdgeMath.geometryLength(trimmed), total - 12.0, 0.2)
        // The trimmed end still lies on the original curve.
        var onCurve = EdgeMath.edgeAnchor(bezier, (total - 12.0) / total)
        near(trimmed.tx, onCurve.x, 0.3)
        near(trimmed.ty, onCurve.y, 0.3)
    }

    function test_end_marker_frames_point_into_each_endpoint() {
        var line = {"route": "pipe", "pipe_points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]}
        var end = EdgeMath.edgeEndMarkerFrame(line, true, 8.0, 100.0)
        near(end.x, 100.0)
        near(end.dx, 1.0)
        var start = EdgeMath.edgeEndMarkerFrame(line, false, 8.0, 100.0)
        near(start.x, 0.0)
        near(start.dx, -1.0)
        // A head spanning a corner follows the chord over its own length.
        var corner = {"route": "pipe", "pipe_points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 4}]}
        var bent = EdgeMath.edgeEndMarkerFrame(corner, true, 8.0, 104.0)
        verify(bent.dx > 0.6 && bent.dy > 0.4)
    }

    function test_label_position_orientation_and_upright_rotation() {
        verify(isNaN(EdgePaintPolicy.flowLabelPosition({"flow_style": {}})))
        near(EdgePaintPolicy.flowLabelPosition({"flow_style": {"label_position": 0.3}}), 0.3)
        near(EdgePaintPolicy.flowLabelPosition({"flow_style": {"label_position": 1.7}}), 1.0)
        verify(EdgePaintPolicy.flowLabelFollowsPath({"flow_style": {"label_orientation": "follow_path"}}))
        verify(!EdgePaintPolicy.flowLabelFollowsPath({"flow_style": {}}))
        compare(EdgePaintPolicy.flowLabelPlacementKey({"flow_style": {}}), "auto|level")
        compare(
            EdgePaintPolicy.flowLabelPlacementKey({"flow_style": {"label_position": 0.25, "label_orientation": "follow_path"}}),
            "0.2500|path"
        )
        var angles = [[0, 0], [45, 45], [90, 90], [135, -45], [180, 0], [-90, 90], [270, 90], [-135, 45], [315, -45]]
        for (var index = 0; index < angles.length; ++index)
            near(EdgeMath.uprightLabelAngle(angles[index][0]), angles[index][1], 0.001, "angle " + angles[index][0])
    }

    function test_nearest_fraction_projects_onto_the_path() {
        var pipe = {"route": "pipe", "pipe_points": [{"x": 0, "y": 0}, {"x": 60, "y": 0}, {"x": 60, "y": 40}]}
        near(EdgeMath.nearestFractionOnGeometry(pipe, 30.0, -12.0, 4.0), 0.3)
        near(EdgeMath.nearestFractionOnGeometry(pipe, 90.0, 30.0, 4.0), 0.9)
        near(EdgeMath.nearestFractionOnGeometry(pipe, -50.0, 0.0, 4.0), 0.0)
    }

    function test_edge_anchor_is_geometry_owned() {
        var bezier = EdgeMath.edgeAnchor({
            "route": "bezier",
            "sx": 0.0,
            "sy": 0.0,
            "c1x": 25.0,
            "c1y": 0.0,
            "c2x": 75.0,
            "c2y": 0.0,
            "tx": 100.0,
            "ty": 0.0
        }, 0.5)
        verify(bezier !== null)
        verify(Math.abs(bezier.x - 50.0) < 0.01)
        verify(Math.abs(bezier.y) < 0.01)

        var pipe = EdgeMath.edgeAnchor({
            "route": "pipe",
            "pipe_points": [{"x": 0.0, "y": 0.0}, {"x": 40.0, "y": 0.0}]
        }, 0.25)
        verify(pipe !== null)
        verify(Math.abs(pipe.x - 10.0) < 0.01)
        verify(Math.abs(pipe.y) < 0.01)
    }

    function test_forward_bezier_lead_mirrors_python_standard_route() {
        compare(EdgeMath.EDGE_FORWARD_LEAD_MIN, 56.0)
        compare(EdgeMath.forwardBezierLead(0.0), 56.0)
        compare(EdgeMath.forwardBezierLead(112.0), 56.0)
        compare(EdgeMath.forwardBezierLead(300.0), 150.0)
        compare(EdgeMath.forwardBezierLead(-300.0), 150.0)
    }

    function test_forward_bezier_lead_delta_is_zero_at_rest_and_signed_when_live() {
        compare(EdgeMath.forwardBezierLeadDelta(400.0, 0.0), 0.0)
        compare(EdgeMath.forwardBezierLeadDelta(400.0, NaN), 0.0)
        compare(EdgeMath.forwardBezierLeadDelta(NaN, 20.0), 0.0)
        compare(EdgeMath.forwardBezierLeadDelta(400.0, -120.0), -60.0)
        compare(EdgeMath.forwardBezierLeadDelta(400.0, 120.0), 60.0)
        // Only the unclamped part of the chord change reaches the handle.
        compare(EdgeMath.forwardBezierLeadDelta(150.0, -100.0), -19.0)
        compare(EdgeMath.forwardBezierLeadDelta(-300.0, 100.0), -50.0)
    }
}
