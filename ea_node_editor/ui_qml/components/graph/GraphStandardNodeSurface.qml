import QtQuick 2.15

Item {
    id: surface
    objectName: "graphNodeStandardSurface"
    property Item host: null
    readonly property var embeddedInteractiveRects: inlinePropertiesLayer.embeddedInteractiveRects
    implicitHeight: host ? host.inlineBodyHeight : 0

    GraphInlinePropertiesLayer {
        id: inlinePropertiesLayer
        anchors.fill: parent
        host: surface.host
    }
}
