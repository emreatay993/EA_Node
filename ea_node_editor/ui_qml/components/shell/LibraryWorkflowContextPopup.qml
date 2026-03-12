import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root
    property var mainWindowRef
    property string libraryContextWorkflowId: ""
    property string libraryContextWorkflowScope: "local"
    readonly property var themePalette: themeBridge.palette

    function openPopup(workflowId, workflowScope, positionX, positionY) {
        libraryContextWorkflowId = String(workflowId || "")
        libraryContextWorkflowScope = String(workflowScope || "local")
        var popupWidth = Math.max(1, Number(libraryContextPopup.implicitWidth) || 168)
        var popupHeight = Math.max(1, Number(libraryContextPopup.implicitHeight) || 58)
        libraryContextPopup.x = Math.max(0, Math.min(root.width - popupWidth, Math.round(Number(positionX) || 0)))
        libraryContextPopup.y = Math.max(0, Math.min(root.height - popupHeight, Math.round(Number(positionY) || 0)))
        libraryContextPopup.open()
    }

    onWidthChanged: {
        if (libraryContextPopup.visible)
            libraryContextPopup.close()
    }

    onHeightChanged: {
        if (libraryContextPopup.visible)
            libraryContextPopup.close()
    }

    Popup {
        id: libraryContextPopup
        parent: root
        modal: false
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape
        implicitWidth: 168
        implicitHeight: 58
        z: 1000

        background: Rectangle {
            color: root.themePalette.tab_bg
            border.color: root.themePalette.input_border
            radius: 3
        }

        contentItem: Column {
            spacing: 0

            Rectangle {
                width: libraryContextPopup.implicitWidth
                height: 29
                color: scopeMouseArea.containsMouse ? root.themePalette.hover : "transparent"

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    color: root.themePalette.app_fg
                    font.pixelSize: 11
                    text: root.libraryContextWorkflowScope === "global" ? "Make Project-Only" : "Make Global"
                }

                MouseArea {
                    id: scopeMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        var nextScope = root.libraryContextWorkflowScope === "global" ? "local" : "global"
                        root.mainWindowRef.request_set_custom_workflow_scope(root.libraryContextWorkflowId, nextScope)
                        libraryContextPopup.close()
                    }
                }
            }

            Rectangle {
                width: libraryContextPopup.implicitWidth
                height: 29
                color: deleteMouseArea.containsMouse ? root.themePalette.hover : "transparent"

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    color: root.themePalette.app_fg
                    font.pixelSize: 11
                    text: "Delete"
                }

                MouseArea {
                    id: deleteMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        root.mainWindowRef.request_delete_custom_workflow_from_library(
                            root.libraryContextWorkflowId,
                            root.libraryContextWorkflowScope
                        )
                        libraryContextPopup.close()
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        visible: libraryContextPopup.visible
        z: 999

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: {
                libraryContextPopup.close()
                mouse.accepted = true
            }
            onWheel: function(wheel) {
                libraryContextPopup.close()
                wheel.accepted = true
            }
        }
    }
}
