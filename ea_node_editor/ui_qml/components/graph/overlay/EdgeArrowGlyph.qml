import QtQuick 2.15
import "../EdgeArrowPaint.js" as EdgeArrowPaint
import "../EdgePaintPolicy.js" as EdgePaintPolicy

// Toolbar/popover preview of a flow edge's end markers, drawn with the canvas marker geometry.
Canvas {
    id: root
    objectName: "graphEdgeArrowGlyph"

    property string startKind: "none"
    property string endKind: "filled"
    property color color: "#E7EDF8"
    property real lineWidth: 1.8
    property real markerBaseWidth: 1.6
    property real endInset: 3.0

    implicitWidth: 30
    implicitHeight: 20
    renderTarget: Canvas.Image
    antialiasing: true

    onStartKindChanged: requestPaint()
    onEndKindChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d");
        ctx.reset();
        var y = height * 0.5;
        var x0 = root.endInset;
        var x1 = width - root.endInset;
        var start = EdgePaintPolicy.flowArrowMarkerMetrics(root.startKind, root.markerBaseWidth, root.lineWidth, 0.0);
        var end = EdgePaintPolicy.flowArrowMarkerMetrics(root.endKind, root.markerBaseWidth, root.lineWidth, 0.0);
        var lineStart = x0 + (start ? start.lineInset : 0.0);
        var lineEnd = x1 - (end ? end.lineInset : 0.0);
        if (lineEnd > lineStart) {
            ctx.save();
            ctx.strokeStyle = root.color;
            ctx.lineWidth = root.lineWidth;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(lineStart, y);
            ctx.lineTo(lineEnd, y);
            ctx.stroke();
            ctx.restore();
        }
        EdgeArrowPaint.paintMarkerShape(ctx, EdgePaintPolicy.flowArrowMarkerShape(start, x0, y, -1.0, 0.0), root.color);
        EdgeArrowPaint.paintMarkerShape(ctx, EdgePaintPolicy.flowArrowMarkerShape(end, x1, y, 1.0, 0.0), root.color);
    }
}
