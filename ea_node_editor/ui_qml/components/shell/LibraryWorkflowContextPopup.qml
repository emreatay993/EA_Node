import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root
    readonly property var shellLibraryBridgeRef: shellLibraryBridge
    property string libraryContextWorkflowId: ""
    property string libraryContextWorkflowScope: ""
    readonly property var contextMenuActions: [
        { "actionId": "rename", "text": "Rename" },
        {
            "actionId": "scope",
            "text": root.libraryContextWorkflowScope === "global" ? "Make Project-Only" : "Make Global"
        },
        { "actionId": "delete", "text": "Delete", "destructive": true }
    ]
    readonly property var themePalette: themeBridge.palette

    function openPopup(workflowId, workflowScope, positionX, positionY) {
        libraryContextWorkflowId = String(workflowId || "")
        libraryContextWorkflowScope = String(workflowScope || "")
        var popupWidth = Math.max(1, Number(libraryContextPopup.implicitWidth) || 168)
        var popupHeight = Math.max(1, Number(libraryContextPopup.implicitHeight) || 114)
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
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        implicitWidth: workflowContextMenu.implicitWidth
        implicitHeight: workflowContextMenu.implicitHeight
        z: 1000

        background: Item {}

        contentItem: ShellContextMenu {
            id: workflowContextMenu
            minimumWidth: 188
            actions: root.contextMenuActions
            onActionTriggered: function(actionId) {
                if (actionId === "rename") {
                    root.shellLibraryBridgeRef.request_rename_custom_workflow_from_library(
                        root.libraryContextWorkflowId,
                        root.libraryContextWorkflowScope
                    )
                } else if (actionId === "scope") {
                    var nextScope = root.libraryContextWorkflowScope === "global" ? "local" : "global"
                    root.shellLibraryBridgeRef.request_set_custom_workflow_scope(root.libraryContextWorkflowId, nextScope)
                } else if (actionId === "delete") {
                    root.shellLibraryBridgeRef.request_delete_custom_workflow_from_library(
                        root.libraryContextWorkflowId,
                        root.libraryContextWorkflowScope
                    )
                }
                libraryContextPopup.close()
            }
        }
    }
}
