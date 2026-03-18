import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    readonly property var themePalette: themeBridge.palette
    color: themePalette.app_bg
    property var sceneBridgeRef: sceneBridge
    property var viewBridgeRef: viewBridge

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
            viewBridgeRef: viewBridge
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
                mainWindowRef: mainWindow
                sceneBridgeRef: root.sceneBridgeRef
                viewBridgeRef: root.viewBridgeRef
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
