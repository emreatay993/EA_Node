import QtQuick 2.15

Item {
    id: root
    objectName: "graphNodeResizeHandle"
    property Item host: null
    readonly property bool containsMouse: resizeDragArea.containsMouse
    width: root.host ? root.host._resizeHandleSize : 0
    height: root.host ? root.host._resizeHandleSize : 0
    visible: root.host && root.host.nodeData
        ? (!root.host.nodeData.collapsed && !root.host.surfaceInteractionLocked)
        : false
    z: 6

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
                ctx.moveTo(width - off, height - 1);
                ctx.lineTo(width - 1, height - off);
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
        cursorShape: Qt.SizeFDiagCursor
        preventStealing: true
        property real pressGlobalX: 0
        property real pressGlobalY: 0
        property real pressWidth: 0
        property real pressHeight: 0

        onPressed: function(mouse) {
            if (!root.host || !root.host.nodeData)
                return;
            var gp = mapToGlobal(mouse.x, mouse.y);
            pressGlobalX = gp.x;
            pressGlobalY = gp.y;
            pressWidth = root.host.width;
            pressHeight = root.host.height;
            root.host._liveWidth = pressWidth;
            root.host._liveHeight = pressHeight;
            root.host.resizePreviewChanged(root.host.nodeData.node_id, pressWidth, pressHeight, true);
            mouse.accepted = true;
        }

        onPositionChanged: function(mouse) {
            if (!root.host || !pressed)
                return;
            var gp = mapToGlobal(mouse.x, mouse.y);
            var dw = (gp.x - pressGlobalX) / root.host.zoom;
            var dh = (gp.y - pressGlobalY) / root.host.zoom;
            root.host._liveWidth = Math.max(root.host._minNodeWidth, pressWidth + dw);
            root.host._liveHeight = Math.max(root.host._minNodeHeight, pressHeight + dh);
            root.host.resizePreviewChanged(root.host.nodeData.node_id, root.host._liveWidth, root.host._liveHeight, true);
        }

        onReleased: function(_mouse) {
            if (!root.host || !root.host.nodeData || root.host._liveWidth <= 0)
                return;
            var finalWidth = root.host._liveWidth;
            var finalHeight = root.host._liveHeight;
            root.host._liveWidth = 0;
            root.host._liveHeight = 0;
            root.host.resizePreviewChanged(root.host.nodeData.node_id, finalWidth, finalHeight, false);
            root.host.resizeFinished(root.host.nodeData.node_id, finalWidth, finalHeight);
        }

        onCanceled: {
            if (!root.host || !root.host.nodeData)
                return;
            var fallbackWidth = root.host._liveWidth > 0 ? root.host._liveWidth : root.host.width;
            var fallbackHeight = root.host._liveHeight > 0 ? root.host._liveHeight : root.host.height;
            root.host._liveWidth = 0;
            root.host._liveHeight = 0;
            root.host.resizePreviewChanged(root.host.nodeData.node_id, fallbackWidth, fallbackHeight, false);
        }
    }
}
