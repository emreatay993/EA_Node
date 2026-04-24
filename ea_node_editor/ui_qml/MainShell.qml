import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    readonly property var themePalette: themeBridge.palette
    color: themePalette.app_bg
    readonly property var graphActionBridgeRef: graphActionBridge
    readonly property var canvasStateBridgeRef: graphCanvasStateBridge
    readonly property var canvasCommandBridgeRef: graphCanvasCommandBridge
    readonly property var canvasViewBridgeRef: graphCanvasViewBridge

    LibraryWorkflowContextPopup {
        id: libraryWorkflowContextPopup
        anchors.fill: parent
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ShellTitleBar {
        }

        ShellRunToolbar {
            id: shellRunToolbar
            viewBridgeRef: root.canvasViewBridgeRef
            scriptEditorBridgeRef: scriptEditorBridge
        }

        RowLayout {
            id: shellWorkspaceRow
            objectName: "shellWorkspaceRow"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            NodeLibraryPane {
                id: libraryPane
                graphCanvasRef: workspaceCenterPane.graphCanvasRef
                popupHostItem: root
                onWorkflowContextRequested: function(workflowId, workflowScope, positionX, positionY) {
                    libraryWorkflowContextPopup.openPopup(workflowId, workflowScope, positionX, positionY)
                }
            }

            WorkspaceCenterPane {
                id: workspaceCenterPane
                graphActionBridgeRef: root.graphActionBridgeRef
                graphCanvasStateBridgeRef: root.canvasStateBridgeRef
                graphCanvasCommandBridgeRef: root.canvasCommandBridgeRef
                overlayHostItem: root
            }

            InspectorPane {
            }
        }

        ShellStatusStrip {
            id: shellStatusStrip
            canvasStateBridgeRef: root.canvasStateBridgeRef
            canvasCommandBridgeRef: root.canvasCommandBridgeRef
            statusEngineRef: statusEngine
            statusJobsRef: statusJobs
            statusMetricsRef: statusMetrics
            statusNotificationsRef: statusNotifications
        }
    }

    GraphSearchOverlay {
        id: graphSearchOverlay
    }

    ConnectionQuickInsertOverlay {
        id: connectionQuickInsertOverlay
    }

    Item {
        id: addonManagerOverlayHost
        objectName: "addonManagerOverlayHost"
        x: 0
        y: shellWorkspaceRow.y
        width: root.width
        height: shellWorkspaceRow.height
        visible: addonManagerBridge.open
        z: 70

        Rectangle {
            id: addonManagerScrim
            objectName: "addonManagerScrim"
            anchors.fill: parent
            color: Qt.alpha(themePalette.app_bg, 0.68)

            MouseArea {
                anchors.fill: parent
                enabled: parent.visible
                onClicked: addonManagerBridge.requestClose()
            }
        }

        AddOnManagerPane {
            id: addonManagerPane
            objectName: "addonManagerPane"
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.topMargin: 10
            anchors.rightMargin: 12
            anchors.bottomMargin: 10
            width: Math.min(parent.width - 24, 1040)
            requestBridge: addonManagerBridge
            workspaceBridge: shellWorkspaceBridge
            viewerHostServiceRef: viewerHostService
            z: 1
        }
    }

    ScriptEditorOverlay {
        id: scriptOverlay
        scriptEditorBridgeRef: scriptEditorBridge
        scriptHighlighterBridgeRef: scriptHighlighterBridge
    }

    GraphHintOverlay {
        id: graphHintOverlay
        graphSearchVisible: graphSearchOverlay.visible || connectionQuickInsertOverlay.visible
    }

    ContentFullscreenOverlay {
        id: contentFullscreenOverlay
        anchors.fill: parent
        bridgeRef: contentFullscreenBridge
    }
}
