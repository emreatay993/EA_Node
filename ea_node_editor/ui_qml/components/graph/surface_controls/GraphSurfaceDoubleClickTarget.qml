import QtQuick 2.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: root
    property Item host: null
    property Item targetItem: null
    property bool enabled: true
    readonly property var interactiveRect: enabled
        ? SurfaceControlGeometry.rectFromItem(targetItem, host)
        : null
    readonly property var embeddedInteractiveRects: enabled
        ? SurfaceControlGeometry.rectList(interactiveRect)
        : []

    signal singleClicked()
    signal doubleClicked()

    x: interactiveRect ? interactiveRect.x : 0
    y: interactiveRect ? interactiveRect.y : 0
    width: interactiveRect ? interactiveRect.width : 0
    height: interactiveRect ? interactiveRect.height : 0
    visible: enabled && interactiveRect !== null

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled
        acceptedButtons: Qt.LeftButton
        hoverEnabled: false
        propagateComposedEvents: false

        onClicked: {
            root.singleClicked();
        }

        onDoubleClicked: function(mouse) {
            root.doubleClicked();
            mouse.accepted = true;
        }
    }
}
