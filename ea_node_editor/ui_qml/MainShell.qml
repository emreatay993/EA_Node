import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    readonly property var shellContextRef: shellContext
    readonly property var shellLibraryBridgeRef: root.shellContextRef.shellLibraryBridge
    readonly property var shellWorkspaceBridgeRef: root.shellContextRef.shellWorkspaceBridge
    readonly property var shellInspectorBridgeRef: root.shellContextRef.shellInspectorBridge
    readonly property var addonManagerBridgeRef: root.shellContextRef.addonManagerBridge
    readonly property var themeBridgeRef: root.shellContextRef.themeBridge
    readonly property var graphThemeBridgeRef: root.shellContextRef.graphThemeBridge
    readonly property var uiIconsRef: root.shellContextRef.uiIcons
    readonly property var statusEngineRef: root.shellContextRef.statusEngine
    readonly property var statusJobsRef: root.shellContextRef.statusJobs
    readonly property var statusMetricsRef: root.shellContextRef.statusMetrics
    readonly property var statusNotificationsRef: root.shellContextRef.statusNotifications
    readonly property var helpBridgeRef: root.shellContextRef.helpBridge
    readonly property var contentFullscreenBridgeRef: root.shellContextRef.contentFullscreenBridge
    readonly property var viewerSessionBridgeRef: root.shellContextRef.viewerSessionBridge
    readonly property var viewerHostServiceRef: root.shellContextRef.viewerHostService
    readonly property var scriptEditorBridgeRef: root.shellContextRef.scriptEditorBridge
    readonly property var scriptHighlighterBridgeRef: root.shellContextRef.scriptHighlighterBridge
    readonly property var themePalette: root.themeBridgeRef.palette
    color: themePalette.app_bg
    readonly property var graphActionBridgeRef: root.shellContextRef.graphActionBridge
    readonly property var canvasStateBridgeRef: root.shellContextRef.graphCanvasStateBridge
    readonly property var canvasCommandBridgeRef: root.shellContextRef.graphCanvasCommandBridge
    readonly property var canvasViewBridgeRef: root.shellContextRef.graphCanvasViewBridge

    LibraryWorkflowContextPopup {
        id: libraryWorkflowContextPopup
        anchors.fill: parent
        shellLibraryBridgeRef: root.shellLibraryBridgeRef
        themeBridgeRef: root.themeBridgeRef
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ShellTitleBar {
            workspaceBridgeRef: root.shellWorkspaceBridgeRef
            themeBridgeRef: root.themeBridgeRef
        }

        ShellRunToolbar {
            id: shellRunToolbar
            workspaceBridgeRef: root.shellWorkspaceBridgeRef
            viewBridgeRef: root.canvasViewBridgeRef
            scriptEditorBridgeRef: root.scriptEditorBridgeRef
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.canvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
        }

        RowLayout {
            id: shellWorkspaceRow
            objectName: "shellWorkspaceRow"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            NodeLibraryPane {
                id: libraryPane
                shellLibraryBridgeRef: root.shellLibraryBridgeRef
                themeBridgeRef: root.themeBridgeRef
                graphCanvasStateBridgeRef: root.canvasStateBridgeRef
                uiIconsRef: root.uiIconsRef
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
                workspaceBridgeRef: root.shellWorkspaceBridgeRef
                themeBridgeRef: root.themeBridgeRef
                uiIconsRef: root.uiIconsRef
                overlayHostItem: root
            }

            InspectorPane {
                inspectorBridgeRef: root.shellInspectorBridgeRef
                helpBridgeRef: root.helpBridgeRef
                themeBridgeRef: root.themeBridgeRef
                graphCanvasStateBridgeRef: root.canvasStateBridgeRef
                uiIconsRef: root.uiIconsRef
            }
        }

        ShellStatusStrip {
            id: shellStatusStrip
            canvasStateBridgeRef: root.canvasStateBridgeRef
            canvasCommandBridgeRef: root.canvasCommandBridgeRef
            statusEngineRef: root.statusEngineRef
            statusJobsRef: root.statusJobsRef
            statusMetricsRef: root.statusMetricsRef
            statusNotificationsRef: root.statusNotificationsRef
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.canvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
        }
    }

    GraphSearchOverlay {
        id: graphSearchOverlay
        shellLibraryBridgeRef: root.shellLibraryBridgeRef
        themeBridgeRef: root.themeBridgeRef
        graphCanvasStateBridgeRef: root.canvasStateBridgeRef
        uiIconsRef: root.uiIconsRef
    }

    ConnectionQuickInsertOverlay {
        id: connectionQuickInsertOverlay
        shellLibraryBridgeRef: root.shellLibraryBridgeRef
        themeBridgeRef: root.themeBridgeRef
    }

    Item {
        id: addonManagerOverlayHost
        objectName: "addonManagerOverlayHost"
        x: 0
        y: shellWorkspaceRow.y
        width: root.width
        height: shellWorkspaceRow.height
        visible: root.addonManagerBridgeRef.open
        z: 70

        Rectangle {
            id: addonManagerScrim
            objectName: "addonManagerScrim"
            anchors.fill: parent
            color: Qt.alpha(themePalette.app_bg, 0.68)

            MouseArea {
                anchors.fill: parent
                enabled: parent.visible
                onClicked: root.addonManagerBridgeRef.requestClose()
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
            requestBridge: root.addonManagerBridgeRef
            workspaceBridge: root.shellWorkspaceBridgeRef
            viewerHostServiceRef: root.viewerHostServiceRef
            themeBridgeRef: root.themeBridgeRef
            graphThemeBridgeRef: root.graphThemeBridgeRef
            graphCanvasStateBridgeRef: root.canvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
            z: 1
        }
    }

    ScriptEditorOverlay {
        id: scriptOverlay
        workspaceBridgeRef: root.shellWorkspaceBridgeRef
        scriptEditorBridgeRef: root.scriptEditorBridgeRef
        scriptHighlighterBridgeRef: root.scriptHighlighterBridgeRef
        themeBridgeRef: root.themeBridgeRef
        graphCanvasStateBridgeRef: root.canvasStateBridgeRef
        uiIconsRef: root.uiIconsRef
    }

    GraphHintOverlay {
        id: graphHintOverlay
        shellLibraryBridgeRef: root.shellLibraryBridgeRef
        themeBridgeRef: root.themeBridgeRef
        graphSearchVisible: graphSearchOverlay.visible || connectionQuickInsertOverlay.visible
    }

    ContentFullscreenOverlay {
        id: contentFullscreenOverlay
        anchors.fill: parent
        bridgeRef: root.contentFullscreenBridgeRef
    }
}
