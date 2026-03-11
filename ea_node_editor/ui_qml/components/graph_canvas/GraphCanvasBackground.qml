import QtQuick 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

Item {
    id: root
    property var viewBridge: null

    function requestGridRedraw() {
        gridCanvas.requestPaint();
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#1D1F24" }
            GradientStop { position: 1.0; color: "#1A1C20" }
        }
    }

    Canvas {
        id: gridCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.fillStyle = "#1D1F24";
            ctx.fillRect(0, 0, width, height);

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
            ctx.strokeStyle = "#2A2E37";
            for (var x = minorStartX; x <= width; x += step) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }
            for (var y = minorStartY; y <= height; y += step) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }

            ctx.strokeStyle = "#323746";
            for (x = majorStartX; x <= width; x += major) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }
            for (y = majorStartY; y <= height; y += major) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }
        }
    }
}
