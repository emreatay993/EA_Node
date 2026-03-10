import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"

Rectangle {
    id: root
    color: "#202020"
    property var sceneBridgeRef: sceneBridge
    property var viewBridgeRef: viewBridge

    LibraryWorkflowContextPopup {
        id: libraryWorkflowContextPopup
        anchors.fill: parent
        mainWindowRef: mainWindow
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ShellTitleBar {
            mainWindowRef: mainWindow
        }

        ShellRunToolbar {
            mainWindowRef: mainWindow
            viewBridgeRef: viewBridge
            scriptEditorBridgeRef: scriptEditorBridge
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            NodeLibraryPane {
                id: libraryPane
                mainWindowRef: mainWindow
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
                workspaceTabsBridgeRef: workspaceTabsBridge
                consoleBridgeRef: consoleBridge
            }

            InspectorPane {
                mainWindowRef: mainWindow
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
        mainWindowRef: mainWindow
    }

    ScriptEditorOverlay {
        id: scriptOverlay
        mainWindowRef: mainWindow
        scriptEditorBridgeRef: scriptEditorBridge
        scriptHighlighterBridgeRef: scriptHighlighterBridge
    }

    GraphHintOverlay {
        id: graphHintOverlay
        mainWindowRef: mainWindow
        graphSearchVisible: graphSearchOverlay.visible
    }
}
