import QtQuick 2.15

Item {
    id: root
    objectName: "graphFlowchartSilhouette"
    property string variant: "process"
    property color fillColor: "#1b1d22"
    property color strokeColor: "#3a3d45"
    property real strokeWidth: 1.0

    function _normalizedVariant() {
        var normalized = String(root.variant || "").trim().toLowerCase();
        if (normalized === "start" || normalized === "end" || normalized === "process" || normalized === "decision"
            || normalized === "document" || normalized === "connector" || normalized === "input_output"
            || normalized === "predefined_process" || normalized === "database") {
            return normalized;
        }
        return "process";
    }

    function _requestPaint() {
        shapeCanvas.requestPaint();
    }

    function _traceRect(ctx, left, top, right, bottom) {
        ctx.moveTo(left, top);
        ctx.lineTo(right, top);
        ctx.lineTo(right, bottom);
        ctx.lineTo(left, bottom);
        ctx.closePath();
    }

    function _traceEllipse(ctx, cx, cy, rx, ry) {
        var kappa = 0.552284749831;
        var ox = rx * kappa;
        var oy = ry * kappa;
        ctx.moveTo(cx - rx, cy);
        ctx.bezierCurveTo(cx - rx, cy - oy, cx - ox, cy - ry, cx, cy - ry);
        ctx.bezierCurveTo(cx + ox, cy - ry, cx + rx, cy - oy, cx + rx, cy);
        ctx.bezierCurveTo(cx + rx, cy + oy, cx + ox, cy + ry, cx, cy + ry);
        ctx.bezierCurveTo(cx - ox, cy + ry, cx - rx, cy + oy, cx - rx, cy);
        ctx.closePath();
    }

    function _traceTopHalfEllipse(ctx, cx, cy, rx, ry) {
        var kappa = 0.552284749831;
        var ox = rx * kappa;
        var oy = ry * kappa;
        ctx.moveTo(cx - rx, cy);
        ctx.bezierCurveTo(cx - rx, cy - oy, cx - ox, cy - ry, cx, cy - ry);
        ctx.bezierCurveTo(cx + ox, cy - ry, cx + rx, cy - oy, cx + rx, cy);
    }

    function _traceBottomHalfEllipseFromRight(ctx, cx, cy, rx, ry) {
        var kappa = 0.552284749831;
        var ox = rx * kappa;
        var oy = ry * kappa;
        ctx.moveTo(cx + rx, cy);
        ctx.bezierCurveTo(cx + rx, cy + oy, cx + ox, cy + ry, cx, cy + ry);
        ctx.bezierCurveTo(cx - ox, cy + ry, cx - rx, cy + oy, cx - rx, cy);
    }

    function _traceTerminator(ctx, left, top, right, bottom) {
        var heightValue = Math.max(0.0, bottom - top);
        var widthValue = Math.max(0.0, right - left);
        var radius = Math.min(heightValue * 0.5, widthValue * 0.5);
        var centerY = top + heightValue * 0.5;
        ctx.moveTo(left + radius, top);
        ctx.lineTo(right - radius, top);
        ctx.arc(right - radius, centerY, radius, -Math.PI / 2.0, Math.PI / 2.0, false);
        ctx.lineTo(left + radius, bottom);
        ctx.arc(left + radius, centerY, radius, Math.PI / 2.0, (Math.PI * 3.0) / 2.0, false);
        ctx.closePath();
    }

    function _traceDecision(ctx, left, top, right, bottom) {
        var centerX = (left + right) * 0.5;
        var centerY = (top + bottom) * 0.5;
        ctx.moveTo(centerX, top);
        ctx.lineTo(right, centerY);
        ctx.lineTo(centerX, bottom);
        ctx.lineTo(left, centerY);
        ctx.closePath();
    }

    function _traceDocument(ctx, left, top, right, bottom) {
        var widthValue = Math.max(0.0, right - left);
        var heightValue = Math.max(0.0, bottom - top);
        var waveDepth = Math.min(heightValue * 0.18, 16.0 + root.strokeWidth);
        ctx.moveTo(left, top);
        ctx.lineTo(right, top);
        ctx.lineTo(right, bottom - waveDepth);
        ctx.bezierCurveTo(
            right - widthValue * 0.14,
            bottom + waveDepth * 0.4,
            left + widthValue * 0.64,
            bottom - waveDepth * 1.15,
            left + widthValue * 0.48,
            bottom - waveDepth * 0.18
        );
        ctx.bezierCurveTo(
            left + widthValue * 0.28,
            bottom + waveDepth * 0.6,
            left + widthValue * 0.12,
            bottom - waveDepth * 0.7,
            left,
            bottom - waveDepth * 0.18
        );
        ctx.closePath();
    }

    function _traceInputOutput(ctx, left, top, right, bottom) {
        var widthValue = Math.max(0.0, right - left);
        var heightValue = Math.max(0.0, bottom - top);
        var slant = Math.min(widthValue * 0.16, heightValue * 0.35);
        ctx.moveTo(left + slant, top);
        ctx.lineTo(right, top);
        ctx.lineTo(right - slant, bottom);
        ctx.lineTo(left, bottom);
        ctx.closePath();
    }

    function _traceDatabaseShell(ctx, left, top, right, bottom) {
        var widthValue = Math.max(0.0, right - left);
        var heightValue = Math.max(0.0, bottom - top);
        var rx = widthValue * 0.5;
        var cap = Math.min(heightValue * 0.18, 18.0 + root.strokeWidth);
        var cx = left + rx;
        var topCy = top + cap;
        var bottomCy = bottom - cap;
        _traceTopHalfEllipse(ctx, cx, topCy, rx, cap);
        ctx.lineTo(right, bottomCy);
        _traceBottomHalfEllipseFromRight(ctx, cx, bottomCy, rx, cap);
        ctx.closePath();
    }

    Canvas {
        id: shapeCanvas
        anchors.fill: parent
        antialiasing: true
        smooth: true
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d");
            if (ctx.reset)
                ctx.reset();
            ctx.clearRect(0, 0, width, height);

            var inset = Math.max(0.5, root.strokeWidth * 0.5);
            var left = inset;
            var top = inset;
            var right = Math.max(left + 1.0, width - inset);
            var bottom = Math.max(top + 1.0, height - inset);
            var variantKey = root._normalizedVariant();

            ctx.fillStyle = root.fillColor;
            ctx.strokeStyle = root.strokeColor;
            ctx.lineWidth = Math.max(1.0, root.strokeWidth);
            ctx.lineJoin = "round";
            ctx.lineCap = "round";

            ctx.beginPath();
            if (variantKey === "start" || variantKey === "end")
                root._traceTerminator(ctx, left, top, right, bottom);
            else if (variantKey === "decision")
                root._traceDecision(ctx, left, top, right, bottom);
            else if (variantKey === "document")
                root._traceDocument(ctx, left, top, right, bottom);
            else if (variantKey === "connector")
                root._traceEllipse(ctx, (left + right) * 0.5, (top + bottom) * 0.5, (right - left) * 0.5, (bottom - top) * 0.5);
            else if (variantKey === "input_output")
                root._traceInputOutput(ctx, left, top, right, bottom);
            else if (variantKey === "database")
                root._traceDatabaseShell(ctx, left, top, right, bottom);
            else
                root._traceRect(ctx, left, top, right, bottom);
            ctx.fill();
            ctx.stroke();

            if (variantKey === "predefined_process") {
                var barInset = Math.min((right - left) * 0.12, 18.0 + inset);
                ctx.beginPath();
                ctx.moveTo(left + barInset, top);
                ctx.lineTo(left + barInset, bottom);
                ctx.moveTo(right - barInset, top);
                ctx.lineTo(right - barInset, bottom);
                ctx.stroke();
            } else if (variantKey === "database") {
                var widthValue = Math.max(0.0, right - left);
                var heightValue = Math.max(0.0, bottom - top);
                var rx = widthValue * 0.5;
                var cap = Math.min(heightValue * 0.18, 18.0 + root.strokeWidth);
                var cx = left + rx;
                var topCy = top + cap;
                var bottomCy = bottom - cap;
                ctx.beginPath();
                root._traceEllipse(ctx, cx, topCy, rx, cap);
                ctx.stroke();
                ctx.beginPath();
                root._traceBottomHalfEllipseFromRight(ctx, cx, bottomCy, rx, cap);
                ctx.stroke();
            }
        }
    }

    onVariantChanged: _requestPaint()
    onFillColorChanged: _requestPaint()
    onStrokeColorChanged: _requestPaint()
    onStrokeWidthChanged: _requestPaint()
    onWidthChanged: _requestPaint()
    onHeightChanged: _requestPaint()
}
