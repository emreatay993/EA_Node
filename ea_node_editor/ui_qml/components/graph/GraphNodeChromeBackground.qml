import QtQuick 2.15
import QtQuick.Effects

Item {
    id: root
    objectName: "graphNodeChromeBackgroundLayer"
    property Item host: null
    z: 0

    RectangularShadow {
        id: cardShadow
        objectName: "graphNodeShadow"
        visible: root.host ? root.host._shadowVisible : false
        anchors.fill: cardChrome
        z: 0
        offset.x: 0
        offset.y: root.host ? root.host.shadowOffset : 4
        blur: Math.max(0.0, Math.min(1.0, (root.host ? root.host.shadowSoftness : 50) / 100.0))
        spread: Math.max(0.0, Math.min(1.0, (root.host ? root.host.shadowStrength : 70) / 100.0))
        radius: root.host ? root.host.resolvedCornerRadius : 0
        color: Qt.rgba(0, 0, 0, (root.host ? root.host.shadowStrength : 70) / 100.0)
        cached: false
    }

    Rectangle {
        id: cardChrome
        objectName: "graphNodeChrome"
        anchors.fill: parent
        z: 1
        visible: root.host ? root.host._useHostChrome : false
        color: root.host ? root.host.surfaceColor : "transparent"
        border.width: root.host ? root.host.resolvedBorderWidth : 0
        border.color: root.host
            ? (root.host.isSelected ? root.host.selectedOutlineColor : root.host.outlineColor)
            : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius : 0
    }
}
