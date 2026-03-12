import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    objectName: "connectionQuickInsertOverlay"
    property var mainWindowRef

    function _wheelDeltaY(wheel) {
        if (!wheel)
            return 0
        if (wheel.angleDelta && wheel.angleDelta.y !== undefined)
            return Number(wheel.angleDelta.y)
        if (wheel.pixelDelta && wheel.pixelDelta.y !== undefined)
            return Number(wheel.pixelDelta.y)
        return 0
    }

    function _clamp(value, minValue, maxValue) {
        return Math.max(minValue, Math.min(maxValue, value))
    }

    function _scrollResultsByWheel(wheel) {
        if (!quickInsertResults.visible)
            return
        var deltaY = root._wheelDeltaY(wheel)
        if (Math.abs(deltaY) < 0.001)
            return
        var step = (-deltaY / 120.0) * 40.0
        if (Math.abs(step) < 1.0)
            step = deltaY > 0 ? -24.0 : 24.0
        var maxContentY = Math.max(0, quickInsertResults.contentHeight - quickInsertResults.height)
        quickInsertResults.contentY = root._clamp(
            quickInsertResults.contentY + step,
            0,
            maxContentY
        )
    }

    visible: !!root.mainWindowRef && root.mainWindowRef.connection_quick_insert_open
    width: Math.min(parent.width * 0.34, 360)
    height: quickInsertContent.implicitHeight + 20
    color: "#20242B"
    border.color: "#76BDE8"
    border.width: 1
    radius: 6
    z: 1120
    focus: visible
    activeFocusOnTab: visible

    x: {
        if (!parent || !root.mainWindowRef)
            return 0
        var preferred = Number(root.mainWindowRef.connection_quick_insert_overlay_x || 0) + 12
        return Math.max(8, Math.min(parent.width - width - 8, preferred))
    }
    y: {
        if (!parent || !root.mainWindowRef)
            return 0
        var preferred = Number(root.mainWindowRef.connection_quick_insert_overlay_y || 0) + 12
        return Math.max(8, Math.min(parent.height - height - 8, preferred))
    }

    onVisibleChanged: {
        if (!visible)
            return
        Qt.callLater(function() {
            quickInsertField.forceActiveFocus()
            quickInsertField.selectAll()
        })
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton
        propagateComposedEvents: true
        onWheel: function(wheel) {
            root._scrollResultsByWheel(wheel)
            wheel.accepted = true
        }
    }

    Connections {
        target: root.mainWindowRef
        function onConnection_quick_insert_changed() {
            var index = Number(root.mainWindowRef.connection_quick_insert_highlight_index)
            if (!root.visible || index < 0 || index >= quickInsertResults.count)
                return
            quickInsertResults.positionViewAtIndex(index, ListView.Contain)
        }
    }

    Column {
        id: quickInsertContent
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 8

        RowLayout {
            width: parent.width

            Text {
                text: "Quick Insert"
                color: "#DDE7F6"
                font.pixelSize: 12
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Esc"
                color: "#8F9AAF"
                font.pixelSize: 11
            }
        }

        Text {
            width: parent.width
            text: root.mainWindowRef ? root.mainWindowRef.connection_quick_insert_source_summary : ""
            color: "#9FB5C9"
            font.pixelSize: 10
            elide: Text.ElideRight
        }

        TextField {
            id: quickInsertField
            width: parent.width
            placeholderText: "Insert compatible node..."
            text: root.mainWindowRef ? root.mainWindowRef.connection_quick_insert_query : ""
            selectByMouse: true
            color: "#E7EEF9"
            Keys.priority: Keys.BeforeItem
            background: Rectangle {
                color: "#2A303A"
                border.color: "#4B586B"
                radius: 4
            }
            onTextChanged: root.mainWindowRef.set_connection_quick_insert_query(text)
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Up) {
                    root.mainWindowRef.request_connection_quick_insert_move(-1)
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Down) {
                    root.mainWindowRef.request_connection_quick_insert_move(1)
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                    root.mainWindowRef.request_connection_quick_insert_accept()
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Escape) {
                    root.mainWindowRef.request_close_connection_quick_insert()
                    event.accepted = true
                }
            }
        }

        ListView {
            id: quickInsertResults
            width: parent.width
            height: visible ? Math.min(
                280,
                Math.max(64, root.mainWindowRef.connection_quick_insert_results.length * 66)
            ) : 0
            clip: true
            spacing: 2
            model: root.mainWindowRef ? root.mainWindowRef.connection_quick_insert_results : []
            visible: model.length > 0

            delegate: Rectangle {
                width: ListView.view.width
                height: 64
                radius: 3
                color: index === root.mainWindowRef.connection_quick_insert_highlight_index
                    ? "#35698A"
                    : (resultMouse.containsMouse ? "#2C343F" : "transparent")
                border.width: index === root.mainWindowRef.connection_quick_insert_highlight_index ? 1 : 0
                border.color: index === root.mainWindowRef.connection_quick_insert_highlight_index ? "#76BDE8" : "transparent"

                Column {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    anchors.topMargin: 7
                    anchors.bottomMargin: 7
                    spacing: 2

                    Text {
                        width: parent.width
                        text: String(modelData.display_name || "")
                        color: "#E5EEF8"
                        font.pixelSize: 12
                        font.bold: index === root.mainWindowRef.connection_quick_insert_highlight_index
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width
                        text: String(modelData.category || "")
                            + "  |  "
                            + String(modelData.type_id || "")
                        color: "#A8B4C6"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width
                        text: (modelData.compatible_port_labels || []).join(", ")
                        color: "#8EC9A6"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: resultMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    onEntered: root.mainWindowRef.request_connection_quick_insert_highlight(index)
                    onClicked: root.mainWindowRef.request_connection_quick_insert_choose(index)
                }
            }
        }

        Text {
            visible: root.mainWindowRef
                && root.mainWindowRef.connection_quick_insert_results.length === 0
            width: parent.width
            wrapMode: Text.WordWrap
            text: "No compatible nodes."
            color: "#A8B4C6"
            font.pixelSize: 11
        }
    }
}
