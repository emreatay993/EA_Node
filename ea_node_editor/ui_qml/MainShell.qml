import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"
import "components/shell"
import "components/shell/MainShellUtils.js" as MainShellUtils

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

    Rectangle {
        id: graphSearchOverlay
        visible: mainWindow.graph_search_open
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(parent.width * 0.62, 760)
        height: graphSearchContent.implicitHeight + 20
        color: "#20242B"
        border.color: "#5C8CAF"
        border.width: 1
        radius: 6
        z: 1100
        focus: visible
        activeFocusOnTab: visible

        onVisibleChanged: {
            if (!visible)
                return
            Qt.callLater(function() {
                graphSearchField.forceActiveFocus()
                graphSearchField.selectAll()
            })
        }

        Connections {
            target: mainWindow
            function onGraph_search_changed() {
                var index = Number(mainWindow.graph_search_highlight_index)
                if (!graphSearchOverlay.visible || index < 0 || index >= graphSearchResultsList.count)
                    return
                graphSearchResultsList.positionViewAtIndex(index, ListView.Contain)
            }
        }

        Column {
            id: graphSearchContent
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 10
            spacing: 8

            RowLayout {
                width: parent.width

                Text {
                    text: "Graph Search"
                    color: "#DDE7F6"
                    font.pixelSize: 12
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "Esc to close"
                    color: "#8F9AAF"
                    font.pixelSize: 11
                }
            }

            TextField {
                id: graphSearchField
                width: parent.width
                placeholderText: "Search title, type, type_id, or node_id"
                text: mainWindow.graph_search_query
                selectByMouse: true
                color: "#E7EEF9"
                Keys.priority: Keys.BeforeItem
                background: Rectangle {
                    color: "#2A303A"
                    border.color: "#4B586B"
                    radius: 4
                }
                onTextChanged: mainWindow.set_graph_search_query(text)
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Up) {
                        mainWindow.request_graph_search_move(-1)
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Down) {
                        mainWindow.request_graph_search_move(1)
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                        mainWindow.request_graph_search_accept()
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Escape) {
                        mainWindow.request_close_graph_search()
                        event.accepted = true
                    }
                }
            }

            ListView {
                id: graphSearchResultsList
                width: parent.width
                height: visible ? Math.min(
                    320,
                    Math.max(44, mainWindow.graph_search_results.length * 44)
                ) : 0
                clip: true
                spacing: 2
                model: mainWindow.graph_search_results
                visible: mainWindow.graph_search_results.length > 0

                delegate: Rectangle {
                    width: ListView.view.width
                    height: 42
                    radius: 3
                    color: index === mainWindow.graph_search_highlight_index
                        ? "#35698A"
                        : (resultMouse.containsMouse ? "#2C343F" : "transparent")
                    border.width: index === mainWindow.graph_search_highlight_index ? 1 : 0
                    border.color: index === mainWindow.graph_search_highlight_index ? "#76BDE8" : "transparent"

                    Column {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        anchors.topMargin: 4
                        anchors.bottomMargin: 4
                        spacing: 1

                        Text {
                            width: parent.width
                            text: String(modelData.node_title || "")
                            color: "#E5EEF8"
                            font.pixelSize: 12
                            font.bold: index === mainWindow.graph_search_highlight_index
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: String(modelData.workspace_name || "")
                                + "  |  "
                                + String(modelData.display_name || "")
                                + "  |  "
                                + String(modelData.type_id || "")
                            color: "#A8B4C6"
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        id: resultMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton
                        onEntered: mainWindow.request_graph_search_highlight(index)
                        onClicked: mainWindow.request_graph_search_jump(index)
                    }
                }
            }

            Text {
                visible: mainWindow.graph_search_query.length > 0
                    && mainWindow.graph_search_results.length === 0
                text: "No matching nodes."
                color: "#A8B4C6"
                font.pixelSize: 11
            }

            Text {
                text: "Up/Down to select, Enter to jump"
                color: "#7E899C"
                font.pixelSize: 10
            }
        }
    }

    Rectangle {
        id: scriptOverlay
        visible: scriptEditorBridge.visible
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.42, 520)
        color: "#171A20"
        border.color: "#2D8ED8"
        border.width: 1
        z: 999

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 30
                color: "#22262E"
                border.color: "#2F3540"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    Text {
                        text: scriptEditorBridge.current_node_id ? "Python Script: " + scriptEditorBridge.current_node_id : "Python Script Editor"
                        color: "#E6ECF8"
                        font.pixelSize: 12
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: scriptEditorBridge.dirty ? "*Modified" : "Saved"
                        color: scriptEditorBridge.dirty ? "#60CDFF" : "#95A1B8"
                        font.pixelSize: 11
                    }
                    ShellButton {
                        text: "X"
                        onClicked: mainWindow.set_script_editor_panel_visible(false)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    id: scriptLineGutter
                    Layout.preferredWidth: 52
                    Layout.fillHeight: true
                    color: "#141821"
                    border.color: "#2B313E"
                    clip: true

                    Text {
                        id: scriptLineNumberText
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        y: (scriptEditorScroll.contentItem ? -scriptEditorScroll.contentItem.contentY : 0) + 6
                        text: MainShellUtils.lineNumbersText(scriptEditorArea.lineCount)
                        color: "#6F7B90"
                        font.family: "Consolas"
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignTop
                    }
                }

                ScrollView {
                    id: scriptEditorScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    TextArea {
                        id: scriptEditorArea
                        width: scriptEditorScroll.availableWidth
                        text: scriptEditorBridge.script_text
                        readOnly: !scriptEditorBridge.current_node_id
                        color: "#D0D7E6"
                        font.family: "Consolas"
                        font.pixelSize: 12
                        wrapMode: TextArea.NoWrap
                        background: Rectangle { color: "#1A1D24" }
                        selectByMouse: true
                        persistentSelection: true
                        leftPadding: 8
                        rightPadding: 8
                        topPadding: 6
                        bottomPadding: 6

                        Component.onCompleted: scriptHighlighterBridge.attach_document(textDocument)

                        onTextChanged: {
                            if (text !== scriptEditorBridge.script_text) {
                                scriptEditorBridge.set_script_text(text)
                            }
                            var before = text.slice(0, cursorPosition)
                            var lines = before.split("\n")
                            var line = lines.length
                            var col = lines[lines.length - 1].length + 1
                            var sel = Math.abs(selectionStart - selectionEnd)
                            scriptEditorBridge.set_cursor_metrics(line, col, cursorPosition, sel)
                        }

                        onCursorPositionChanged: {
                            var before = text.slice(0, cursorPosition)
                            var lines = before.split("\n")
                            var line = lines.length
                            var col = lines[lines.length - 1].length + 1
                            var sel = Math.abs(selectionStart - selectionEnd)
                            scriptEditorBridge.set_cursor_metrics(line, col, cursorPosition, sel)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 30
                color: "#22262E"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: scriptEditorBridge.cursor_label
                        color: "#9DA7BC"
                        font.pixelSize: 11
                    }
                    Item { Layout.fillWidth: true }
                    ShellButton {
                        text: "Revert"
                        enabled: scriptEditorBridge.dirty
                        onClicked: scriptEditorBridge.revert()
                    }
                    ShellButton {
                        text: "Apply"
                        enabled: scriptEditorBridge.dirty
                        onClicked: scriptEditorBridge.apply()
                    }
                }
            }
        }
    }

    Rectangle {
        id: graphHintOverlay
        objectName: "graphHintOverlay"
        visible: mainWindow.graph_hint_visible && !graphSearchOverlay.visible
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 32
        width: Math.min(parent.width * 0.68, Math.max(260, graphHintText.implicitWidth + 28))
        height: graphHintText.implicitHeight + 14
        radius: 5
        color: "#CC212A35"
        border.width: 1
        border.color: "#5C8CAF"
        z: 1080

        Text {
            id: graphHintText
            anchors.centerIn: parent
            width: parent.width - 24
            text: mainWindow.graph_hint_message
            color: "#E6F2FF"
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
        }
    }
}
