import QtQuick 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

Item {
    id: root
    property var viewBridge: null
    property bool showGrid: true
    property bool degradedWindowActive: false
    property int _redrawRequestCount: 0
    readonly property var themePalette: themeBridge.palette
    readonly property color backgroundTopColor: themePalette.canvas_bg
    readonly property color backgroundBottomColor: themePalette.panel_bg
    readonly property color backgroundFillColor: themePalette.canvas_bg
    readonly property color minorGridColor: themePalette.canvas_minor_grid
    readonly property color majorGridColor: themePalette.canvas_major_grid
    readonly property bool effectiveShowGrid: root.showGrid && !root.degradedWindowActive

    function requestGridRedraw() {
        root._redrawRequestCount += 1;
        gridCanvas.requestPaint();
    }

    onShowGridChanged: requestGridRedraw()
    onDegradedWindowActiveChanged: requestGridRedraw()
    onThemePaletteChanged: requestGridRedraw()

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.backgroundTopColor }
            GradientStop { position: 1.0; color: root.backgroundBottomColor }
        }
    }

    Canvas {
        id: gridCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.fillStyle = root.backgroundFillColor;
            ctx.fillRect(0, 0, width, height);
            if (!root.effectiveShowGrid)
                return;

            var zoom = root.viewBridge ? root.viewBridge.zoom_value : 1.0;
            var step = 20 * zoom;
            if (step < 10)
                step = 10;
            var major = step * 5;
            var centerX = root.viewBridge ? root.viewBridge.center_x : 0.0;
            var centerY = root.viewBridge ? root.viewBridge.center_y : 0.0;

            var minorStartX = GraphCanvasLogic.normalizedOffset(step, width * 0.5 - centerX * zoom);
            var minorStartY = GraphCanvasLogic.normalizedOffset(step, height * 0.5 - centerY * zoom);
            var majorStartX = GraphCanvasLogic.normalizedOffset(major, width * 0.5 - centerX * zoom);
            var majorStartY = GraphCanvasLogic.normalizedOffset(major, height * 0.5 - centerY * zoom);

            ctx.lineWidth = 1;
            ctx.strokeStyle = root.minorGridColor;
            ctx.beginPath();
            for (var x = minorStartX; x <= width; x += step) {
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
            }
            for (var y = minorStartY; y <= height; y += step) {
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
            }
            ctx.stroke();

            ctx.strokeStyle = root.majorGridColor;
            ctx.beginPath();
            for (x = majorStartX; x <= width; x += major) {
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
            }
            for (y = majorStartY; y <= height; y += major) {
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
            }
            ctx.stroke();
        }
    }
}
