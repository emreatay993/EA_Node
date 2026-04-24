import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    readonly property var shellContextRef: shellContext
    readonly property var themePalette: root.shellContextRef.themeBridge.palette
    color: themePalette.app_bg
    readonly property var graphActionBridgeRef: root.shellContextRef.graphActionBridge
    readonly property var canvasStateBridgeRef: root.shellContextRef.graphCanvasStateBridge
    readonly property var canvasCommandBridgeRef: root.shellContextRef.graphCanvasCommandBridge
    readonly property var canvasViewBridgeRef: root.shellContextRef.graphCanvasViewBridge

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
            scriptEditorBridgeRef: root.shellContextRef.scriptEditorBridge
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
                workspaceBridgeRef: root.shellContextRef.shellWorkspaceBridge
                themeBridgeRef: root.shellContextRef.themeBridge
                overlayHostItem: root
            }

            InspectorPane {
            }
        }

        ShellStatusStrip {
            id: shellStatusStrip
            canvasStateBridgeRef: root.canvasStateBridgeRef
            canvasCommandBridgeRef: root.canvasCommandBridgeRef
            statusEngineRef: root.shellContextRef.statusEngine
            statusJobsRef: root.shellContextRef.statusJobs
            statusMetricsRef: root.shellContextRef.statusMetrics
            statusNotificationsRef: root.shellContextRef.statusNotifications
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
        visible: root.shellContextRef.addonManagerBridge.open
        z: 70

        Rectangle {
            id: addonManagerScrim
            objectName: "addonManagerScrim"
            anchors.fill: parent
            color: Qt.alpha(themePalette.app_bg, 0.68)

            MouseArea {
                anchors.fill: parent
                enabled: parent.visible
                onClicked: root.shellContextRef.addonManagerBridge.requestClose()
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
            requestBridge: root.shellContextRef.addonManagerBridge
            workspaceBridge: root.shellContextRef.shellWorkspaceBridge
            viewerHostServiceRef: root.shellContextRef.viewerHostService
            z: 1
        }
    }

    ScriptEditorOverlay {
        id: scriptOverlay
        scriptEditorBridgeRef: root.shellContextRef.scriptEditorBridge
        scriptHighlighterBridgeRef: root.shellContextRef.scriptHighlighterBridge
    }

    GraphHintOverlay {
        id: graphHintOverlay
        graphSearchVisible: graphSearchOverlay.visible || connectionQuickInsertOverlay.visible
    }

    ContentFullscreenOverlay {
        id: contentFullscreenOverlay
        anchors.fill: parent
        bridgeRef: root.shellContextRef.contentFullscreenBridge
    }
}
