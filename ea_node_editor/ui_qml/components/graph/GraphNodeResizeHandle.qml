import QtQuick 2.15

Item {
    id: root
    objectName: "graphNodeResizeHandle"
    property Item host: null
    property string cornerRole: "bottomRight"
    readonly property bool containsMouse: resizeDragArea.containsMouse
    readonly property bool dragActive: resizeDragArea.pressed
    readonly property bool _leftCorner: cornerRole === "topLeft" || cornerRole === "bottomLeft"
    readonly property bool _rightCorner: cornerRole === "topRight" || cornerRole === "bottomRight"
    readonly property bool _topCorner: cornerRole === "topLeft" || cornerRole === "topRight"
    readonly property bool _bottomCorner: cornerRole === "bottomLeft" || cornerRole === "bottomRight"
    readonly property bool _forwardDiagonal: cornerRole === "topLeft" || cornerRole === "bottomRight"
    width: root.host ? root.host._resizeHandleSize : 0
    height: root.host ? root.host._resizeHandleSize : 0
    visible: root.host ? root.host._resizeHandlesVisible : false
    z: 6
    anchors.left: root._leftCorner ? parent.left : undefined
    anchors.right: root._rightCorner ? parent.right : undefined
    anchors.top: root._topCorner ? parent.top : undefined
    anchors.bottom: root._bottomCorner ? parent.bottom : undefined

    Canvas {
        id: resizeGrip
        anchors.fill: parent
        visible: parent.visible

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            ctx.strokeStyle = root.host ? root.host.outlineColor : "#3a3d45";
            ctx.lineWidth = 1.2;
            ctx.lineCap = "round";
            for (var i = 1; i <= 3; i++) {
                var off = i * 3.5;
                ctx.beginPath();
                var startX = root._leftCorner ? off : width - off;
                var startY = root._topCorner ? 1 : height - 1;
                var endX = root._leftCorner ? 1 : width - 1;
                var endY = root._topCorner ? off : height - off;
                ctx.moveTo(startX, startY);
                ctx.lineTo(endX, endY);
                ctx.stroke();
            }
        }
    }

    MouseArea {
        id: resizeDragArea
        objectName: "graphNodeResizeDragArea"
        anchors.fill: parent
        enabled: root.host ? !root.host.surfaceInteractionLocked : false
        hoverEnabled: true
        cursorShape: root._forwardDiagonal ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor
        preventStealing: true
        property real pressGlobalX: 0
        property real pressGlobalY: 0
        property real pressX: 0
        property real pressY: 0
        property real pressWidth: 0
        property real pressHeight: 0

        function updatePreviewFromDelta(deltaX, deltaY, active) {
            if (!root.host || !root.host.nodeData)
                return;
            var minWidth = root.host._minNodeWidth;
            var minHeight = root.host._minNodeHeight;
            var left = pressX;
            var top = pressY;
            var right = pressX + pressWidth;
            var bottom = pressY + pressHeight;

            if (root._leftCorner)
                left = pressX + deltaX;
            else
                right = pressX + pressWidth + deltaX;

            if (root._topCorner)
                top = pressY + deltaY;
            else
                bottom = pressY + pressHeight + deltaY;

            if ((right - left) < minWidth) {
                if (root._leftCorner)
                    left = right - minWidth;
                else
                    right = left + minWidth;
            }
            if ((bottom - top) < minHeight) {
                if (root._topCorner)
                    top = bottom - minHeight;
                else
                    bottom = top + minHeight;
            }

            root.host._liveGeometryActive = true;
            root.host._liveX = left;
            root.host._liveY = top;
            root.host._liveWidth = right - left;
            root.host._liveHeight = bottom - top;
            root.host.resizePreviewChanged(
                root.host.nodeData.node_id,
                root.host._liveX,
                root.host._liveY,
                root.host._liveWidth,
                root.host._liveHeight,
                active
            );
        }

        onPressed: function(mouse) {
            if (!root.host || !root.host.nodeData)
                return;
            var gp = mapToGlobal(mouse.x, mouse.y);
            pressGlobalX = gp.x;
            pressGlobalY = gp.y;
            pressX = root.host._liveGeometryActive ? root.host._liveX : Number(root.host.nodeData.x);
            pressY = root.host._liveGeometryActive ? root.host._liveY : Number(root.host.nodeData.y);
            pressWidth = root.host.width;
            pressHeight = root.host.height;
            updatePreviewFromDelta(0.0, 0.0, true);
            mouse.accepted = true;
        }

        onPositionChanged: function(mouse) {
            if (!root.host || !pressed)
                return;
            var gp = mapToGlobal(mouse.x, mouse.y);
            var zoom = root.host.currentViewportZoom ? root.host.currentViewportZoom() : 1.0;
            var dx = (gp.x - pressGlobalX) / zoom;
            var dy = (gp.y - pressGlobalY) / zoom;
            updatePreviewFromDelta(dx, dy, true);
        }

        onReleased: function(_mouse) {
            if (!root.host || !root.host.nodeData || !root.host._liveGeometryActive)
                return;
            var finalX = root.host._liveX;
            var finalY = root.host._liveY;
            var finalWidth = root.host._liveWidth;
            var finalHeight = root.host._liveHeight;
            root.host.resizePreviewChanged(
                root.host.nodeData.node_id,
                finalX,
                finalY,
                finalWidth,
                finalHeight,
                false
            );
            root.host.resizeFinished(root.host.nodeData.node_id, finalX, finalY, finalWidth, finalHeight);
            root.host._liveGeometryActive = false;
        }

        onCanceled: {
            if (!root.host || !root.host.nodeData)
                return;
            var fallbackX = root.host._liveGeometryActive ? root.host._liveX : Number(root.host.nodeData.x);
            var fallbackY = root.host._liveGeometryActive ? root.host._liveY : Number(root.host.nodeData.y);
            var fallbackWidth = root.host._liveGeometryActive ? root.host._liveWidth : root.host.width;
            var fallbackHeight = root.host._liveGeometryActive ? root.host._liveHeight : root.host.height;
            root.host.resizePreviewChanged(
                root.host.nodeData.node_id,
                fallbackX,
                fallbackY,
                fallbackWidth,
                fallbackHeight,
                false
            );
            root.host._liveGeometryActive = false;
        }
    }
}
