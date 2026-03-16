import QtQuick 2.15
import QtQuick.Shapes 1.15

Item {
    id: root
    objectName: "graphFlowchartSilhouette"
    property string variant: "process"
    property color fillColor: "#1b1d22"
    property color strokeColor: "#3a3d45"
    property real strokeWidth: 1.0
    readonly property string outlinePathData: _outlinePathData()
    readonly property string detailPathData: _detailPathData()

    function _normalizedVariant() {
        var normalized = String(root.variant || "").trim().toLowerCase();
        if (normalized === "start" || normalized === "end" || normalized === "process" || normalized === "decision"
            || normalized === "document" || normalized === "connector" || normalized === "input_output"
            || normalized === "predefined_process" || normalized === "database") {
            return normalized;
        }
        return "process";
    }

    function _fmt(value) {
        var numeric = Number(value);
        if (!isFinite(numeric))
            numeric = 0.0;
        return numeric.toFixed(3);
    }

    function _bounds() {
        var inset = Math.max(0.5, root.strokeWidth * 0.5);
        var left = inset;
        var top = inset;
        var right = Math.max(left + 1.0, root.width - inset);
        var bottom = Math.max(top + 1.0, root.height - inset);
        return {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "widthValue": Math.max(1.0, right - left),
            "heightValue": Math.max(1.0, bottom - top),
            "centerX": (left + right) * 0.5,
            "centerY": (top + bottom) * 0.5
        };
    }

    function _moveTo(x, y) {
        return "M " + _fmt(x) + " " + _fmt(y);
    }

    function _lineTo(x, y) {
        return "L " + _fmt(x) + " " + _fmt(y);
    }

    function _cubicTo(c1x, c1y, c2x, c2y, x, y) {
        return "C "
            + _fmt(c1x) + " " + _fmt(c1y) + " "
            + _fmt(c2x) + " " + _fmt(c2y) + " "
            + _fmt(x) + " " + _fmt(y);
    }

    function _arcTo(rx, ry, largeArc, sweep, x, y) {
        return "A "
            + _fmt(rx) + " " + _fmt(ry) + " 0 "
            + (largeArc ? "1" : "0") + " "
            + (sweep ? "1" : "0") + " "
            + _fmt(x) + " " + _fmt(y);
    }

    function _closePath() {
        return "Z";
    }

    function _traceRect(bounds) {
        return [
            _moveTo(bounds.left, bounds.top),
            _lineTo(bounds.right, bounds.top),
            _lineTo(bounds.right, bounds.bottom),
            _lineTo(bounds.left, bounds.bottom),
            _closePath()
        ].join(" ");
    }

    function _traceTerminator(bounds) {
        var radius = Math.min(bounds.heightValue * 0.5, bounds.widthValue * 0.5);
        return [
            _moveTo(bounds.left + radius, bounds.top),
            _lineTo(bounds.right - radius, bounds.top),
            _arcTo(radius, radius, false, true, bounds.right - radius, bounds.bottom),
            _lineTo(bounds.left + radius, bounds.bottom),
            _arcTo(radius, radius, false, true, bounds.left + radius, bounds.top),
            _closePath()
        ].join(" ");
    }

    function _traceDecision(bounds) {
        return [
            _moveTo(bounds.centerX, bounds.top),
            _lineTo(bounds.right, bounds.centerY),
            _lineTo(bounds.centerX, bounds.bottom),
            _lineTo(bounds.left, bounds.centerY),
            _closePath()
        ].join(" ");
    }

    function _traceDocument(bounds) {
        var waveDepth = Math.min(bounds.heightValue * 0.11, 10.0 + root.strokeWidth * 1.5);
        var waveBase = bounds.bottom - waveDepth * 0.58;
        var waveCrest = bounds.bottom - waveDepth * 1.08;
        var waveTrough = bounds.bottom - waveDepth * 0.12;
        return [
            _moveTo(bounds.left, bounds.top),
            _lineTo(bounds.right, bounds.top),
            _lineTo(bounds.right, waveBase),
            _cubicTo(
                bounds.right - bounds.widthValue * 0.17,
                waveTrough,
                bounds.left + bounds.widthValue * 0.7,
                waveTrough,
                bounds.left + bounds.widthValue * 0.52,
                waveBase - waveDepth * 0.34
            ),
            _cubicTo(
                bounds.left + bounds.widthValue * 0.33,
                waveCrest,
                bounds.left + bounds.widthValue * 0.14,
                waveCrest,
                bounds.left,
                waveBase
            ),
            _closePath()
        ].join(" ");
    }

    function _traceConnector(bounds) {
        var rx = bounds.widthValue * 0.5;
        var ry = bounds.heightValue * 0.5;
        return [
            _moveTo(bounds.centerX - rx, bounds.centerY),
            _arcTo(rx, ry, true, false, bounds.centerX + rx, bounds.centerY),
            _arcTo(rx, ry, true, false, bounds.centerX - rx, bounds.centerY),
            _closePath()
        ].join(" ");
    }

    function _traceInputOutput(bounds) {
        var slant = Math.min(bounds.widthValue * 0.13, bounds.heightValue * 0.26);
        return [
            _moveTo(bounds.left + slant, bounds.top),
            _lineTo(bounds.right, bounds.top),
            _lineTo(bounds.right - slant, bounds.bottom),
            _lineTo(bounds.left, bounds.bottom),
            _closePath()
        ].join(" ");
    }

    function _traceDatabaseShell(bounds) {
        var rx = bounds.widthValue * 0.5;
        var cap = Math.min(bounds.heightValue * 0.13, 14.0 + root.strokeWidth);
        var topCy = bounds.top + cap;
        var bottomCy = bounds.bottom - cap;
        return [
            _moveTo(bounds.left, topCy),
            _arcTo(rx, cap, false, true, bounds.right, topCy),
            _lineTo(bounds.right, bottomCy),
            _arcTo(rx, cap, false, true, bounds.left, bottomCy),
            _lineTo(bounds.left, topCy),
            _closePath()
        ].join(" ");
    }

    function _tracePredefinedBars(bounds) {
        var barInset = Math.min(bounds.widthValue * 0.1, 16.0 + Math.max(0.5, root.strokeWidth * 0.5));
        return [
            _moveTo(bounds.left + barInset, bounds.top),
            _lineTo(bounds.left + barInset, bounds.bottom),
            _moveTo(bounds.right - barInset, bounds.top),
            _lineTo(bounds.right - barInset, bounds.bottom)
        ].join(" ");
    }

    function _traceDatabaseDetails(bounds) {
        var rx = bounds.widthValue * 0.5;
        var cap = Math.min(bounds.heightValue * 0.13, 14.0 + root.strokeWidth);
        var topCy = bounds.top + cap;
        var bottomCy = bounds.bottom - cap;
        return [
            _moveTo(bounds.left, topCy),
            _arcTo(rx, cap, true, false, bounds.right, topCy),
            _arcTo(rx, cap, true, false, bounds.left, topCy),
            _moveTo(bounds.right, bottomCy),
            _arcTo(rx, cap, false, true, bounds.left, bottomCy)
        ].join(" ");
    }

    function _outlinePathData() {
        var bounds = _bounds();
        var variantKey = _normalizedVariant();
        if (variantKey === "start" || variantKey === "end")
            return _traceTerminator(bounds);
        if (variantKey === "decision")
            return _traceDecision(bounds);
        if (variantKey === "document")
            return _traceDocument(bounds);
        if (variantKey === "connector")
            return _traceConnector(bounds);
        if (variantKey === "input_output")
            return _traceInputOutput(bounds);
        if (variantKey === "database")
            return _traceDatabaseShell(bounds);
        return _traceRect(bounds);
    }

    function _detailPathData() {
        var bounds = _bounds();
        var variantKey = _normalizedVariant();
        if (variantKey === "predefined_process")
            return _tracePredefinedBars(bounds);
        if (variantKey === "database")
            return _traceDatabaseDetails(bounds);
        return "";
    }

    Shape {
        id: outlineShape
        objectName: "graphFlowchartVectorShape"
        anchors.fill: parent
        antialiasing: true
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: root.strokeColor
            strokeWidth: Math.max(1.0, root.strokeWidth)
            fillColor: root.fillColor
            joinStyle: ShapePath.RoundJoin
            capStyle: ShapePath.RoundCap

            PathSvg {
                path: root.outlinePathData
            }
        }
    }

    Shape {
        id: detailShape
        objectName: "graphFlowchartVectorDetails"
        anchors.fill: parent
        visible: root.detailPathData.length > 0
        antialiasing: true
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: root.strokeColor
            strokeWidth: Math.max(1.0, root.strokeWidth)
            fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin
            capStyle: ShapePath.RoundCap

            PathSvg {
                path: root.detailPathData
            }
        }
    }
}
