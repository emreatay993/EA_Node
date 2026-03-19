import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    readonly property var themePalette: themeBridge.palette
    color: themePalette.app_bg
    readonly property var canvasBridgeRef: graphCanvasBridge
    readonly property var canvasStateBridgeRef: graphCanvasStateBridge
    readonly property var canvasCommandBridgeRef: graphCanvasCommandBridge
    readonly property var canvasViewBridgeRef: root.canvasStateBridgeRef

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
            viewBridgeRef: root.canvasViewBridgeRef
            scriptEditorBridgeRef: scriptEditorBridge
        }

        RowLayout {
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
                graphCanvasBridgeRef: root.canvasBridgeRef
                graphCanvasStateBridgeRef: root.canvasStateBridgeRef
                graphCanvasCommandBridgeRef: root.canvasCommandBridgeRef
                overlayHostItem: root
            }

            InspectorPane {
            }
        }

        ShellStatusStrip {
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

    ScriptEditorOverlay {
        id: scriptOverlay
        scriptEditorBridgeRef: scriptEditorBridge
        scriptHighlighterBridgeRef: scriptHighlighterBridge
    }

    GraphHintOverlay {
        id: graphHintOverlay
        graphSearchVisible: graphSearchOverlay.visible || connectionQuickInsertOverlay.visible
    }
}
