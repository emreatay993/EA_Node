import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    readonly property var themePalette: themeBridge.palette
    color: themePalette.app_bg
    readonly property var canvasBridgeRef: (typeof graphCanvasBridge !== "undefined" && graphCanvasBridge)
        ? graphCanvasBridge
        : null
    readonly property var canvasShellBridgeRef: root.canvasBridgeRef
        ? root.canvasBridgeRef
        : ((typeof mainWindow !== "undefined" && mainWindow)
            ? mainWindow
            : null)
    readonly property var canvasSceneBridgeRef: root.canvasBridgeRef
        ? root.canvasBridgeRef
        : ((typeof sceneBridge !== "undefined" && sceneBridge)
            ? sceneBridge
            : null)
    readonly property var canvasViewBridgeRef: root.canvasBridgeRef
        ? root.canvasBridgeRef
        : ((typeof viewBridge !== "undefined" && viewBridge)
            ? viewBridge
            : null)

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
                canvasShellCompatRef: root.canvasShellBridgeRef
                canvasSceneCompatRef: root.canvasSceneBridgeRef
                canvasViewCompatRef: root.canvasViewBridgeRef
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
