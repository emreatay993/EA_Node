import QtQuick 2.15

Item {
    id: surface
    objectName: "graphNodeStandardSurface"
    property Item host: null
    implicitHeight: host ? host.inlineBodyHeight : 0

    GraphInlinePropertiesLayer {
        anchors.fill: parent
        host: surface.host
    }
}
