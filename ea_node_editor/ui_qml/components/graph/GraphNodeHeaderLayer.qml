import QtQuick 2.15

Item {
    id: root
    objectName: "graphNodeHeaderLayer"
    property Item host: null
    z: 3

    Rectangle {
        visible: root.host ? root.host._showAccentBar : false
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 4
        radius: 4
        color: root.host && root.host.nodeData ? root.host.nodeData.accent : "#4AA9D6"
    }

    Rectangle {
        visible: root.host ? root.host._showHeaderBackground : false
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: root.host ? Number(root.host.surfaceMetrics.header_top_margin) : 0
        height: root.host ? Number(root.host.surfaceMetrics.header_height) : 0
        color: root.host ? root.host.headerColor : "transparent"
        border.color: root.host ? root.host.outlineColor : "transparent"
    }

    Text {
        objectName: "graphNodeTitle"
        property int effectiveRenderType: renderType
        anchors.left: parent.left
        anchors.leftMargin: root.host ? root.host._titleLeftMargin : 0
        anchors.right: parent.right
        anchors.rightMargin: root.host ? root.host._titleRightMargin + (root.host.canEnterScope ? 56 : 0) : 0
        y: root.host ? root.host._titleTop : 0
        height: root.host ? root.host._titleHeight : 0
        text: root.host && root.host.nodeData ? root.host.nodeData.title : ""
        color: root.host ? root.host.headerTextColor : "#f0f4fb"
        font.pixelSize: root.host && root.host.isPassiveNode ? root.host.passiveFontPixelSize : 12
        font.bold: root.host ? (root.host.isPassiveNode ? root.host.passiveFontBold : true) : true
        horizontalAlignment: root.host && root.host._titleCentered ? Text.AlignHCenter : Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
    }

    Rectangle {
        visible: root.host ? root.host.canEnterScope : false
        anchors.right: parent.right
        anchors.rightMargin: 8
        y: root.host ? root.host._titleTop + Math.max(0, (root.host._titleHeight - height) * 0.5) : 0
        width: 48
        height: 16
        radius: 8
        color: root.host ? root.host.scopeBadgeColor : "#1D8CE0"
        border.color: root.host ? root.host.scopeBadgeBorderColor : "#60CDFF"

        Text {
            anchors.centerIn: parent
            text: "OPEN"
            color: root.host ? root.host.scopeBadgeTextColor : "#f2f4f8"
            font.pixelSize: 9
            font.bold: true
            renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
        }
    }
}
