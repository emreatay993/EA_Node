import QtQuick 2.15

Item {
    id: root
    objectName: "graphNativeExplorerSurface"
    property Item host: null
    readonly property string currentPath: _propertyString("current_path")
    readonly property real panelLeft: Math.max(6.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_left_margin || 8.0 : 8.0))
    readonly property real panelRight: Math.max(6.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_right_margin || 8.0 : 8.0))
    readonly property real panelTop: Math.max(30.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_top || 30.0 : 30.0))
    readonly property real panelBottom: Math.max(6.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_bottom_margin || 8.0 : 8.0))
    readonly property var embeddedInteractiveRects: [
        {
            "x": nativeViewport.x,
            "y": nativeViewport.y,
            "width": nativeViewport.width,
            "height": nativeViewport.height
        }
    ]
    readonly property var surfaceActions: []
    readonly property bool blocksHostInteraction: false

    implicitHeight: Math.max(260.0, height)
    clip: true

    function _propertyString(key) {
        if (!host || !host.nodeData)
            return "";
        var properties = host.nodeData.properties || ({});
        return String(properties[key] || host.nodeData[key] || "");
    }

    Rectangle {
        id: nativeViewport
        objectName: "graphNodeViewerViewport"
        x: root.panelLeft
        y: root.panelTop
        width: Math.max(0.0, root.width - root.panelLeft - root.panelRight)
        height: Math.max(0.0, root.height - root.panelTop - root.panelBottom)
        color: "#101318"
        border.width: 1
        border.color: "#2c3442"
        radius: 2
        clip: true

        Text {
            objectName: "graphNativeExplorerPlaceholder"
            anchors.centerIn: parent
            width: Math.max(120, parent.width - 24)
            text: root.currentPath.length > 0 ? root.currentPath : "Windows Explorer"
            color: "#8f9aab"
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideMiddle
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }
    }
}
