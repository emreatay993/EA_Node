import QtQuick 2.15

Item {
    id: root
    property Item edgeLayer: null
    property bool inputEnabled: true

    signal edgeClicked(string edgeId, bool additive)
    signal edgeContextRequested(string edgeId, real screenX, real screenY)

    MouseArea {
        anchors.fill: parent
        enabled: root.inputEnabled
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        propagateComposedEvents: true

        onPressed: function(mouse) {
            var edgeId = root.edgeLayer && root.edgeLayer.edgeAtScreen ? root.edgeLayer.edgeAtScreen(mouse.x, mouse.y) : "";
            if (!edgeId) {
                mouse.accepted = false;
                return;
            }
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            if (mouse.button === Qt.LeftButton)
                root.edgeClicked(edgeId, additive);
            else if (mouse.button === Qt.RightButton)
                root.edgeContextRequested(edgeId, mouse.x, mouse.y);
            mouse.accepted = true;
        }
    }
}
