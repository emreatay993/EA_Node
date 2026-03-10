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

            Rectangle {
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                color: "#252830"
                border.color: "#3D414A"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Text {
                        text: "PROPERTIES"
                        color: "#AEB6C7"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: mainWindow.selected_node_summary
                        color: "#D8DEEA"
                        font.pixelSize: 12
                    }

                    ToolButton {
                        text: mainWindow.selected_node_collapsed ? "Expand Node" : "Collapse Node"
                        enabled: mainWindow.has_selected_node && mainWindow.selected_node_collapsible
                        onClicked: mainWindow.set_selected_node_collapsed(!mainWindow.selected_node_collapsed)
                    }

                    ToolButton {
                        text: "Publish Selected Subnode"
                        enabled: mainWindow.selected_node_is_subnode_shell
                        onClicked: mainWindow.request_publish_custom_workflow_from_selected()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#1E2128"
                        border.color: "#353942"
                        radius: 4

                        ScrollView {
                            id: inspectorScroll
                            anchors.fill: parent
                            anchors.margins: 8
                            clip: true
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                            Column {
                                id: inspectorColumn
                                width: inspectorScroll.availableWidth
                                spacing: 10

                                Text {
                                    visible: !mainWindow.has_selected_node
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    text: "Select a node to edit properties and port exposure."
                                    color: "#8E98AC"
                                    font.pixelSize: 12
                                }

                                Text {
                                    visible: mainWindow.has_selected_node
                                    text: "Properties"
                                    color: "#9DA7BC"
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                Text {
                                    visible: mainWindow.selected_node_is_subnode_pin
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    text: "Pin ports are configured through Label, Kind, and Data Type."
                                    color: "#8FB8D8"
                                    font.pixelSize: 10
                                }

                                Repeater {
                                    model: mainWindow.selected_node_property_items
                                    delegate: Column {
                                        width: inspectorColumn.width
                                        spacing: 4
                                        visible: mainWindow.has_selected_node

                                        Text {
                                            width: parent.width
                                            text: modelData.label
                                            color: "#C8D0E0"
                                            font.pixelSize: 11
                                        }

                                        CheckBox {
                                            width: parent.width
                                            visible: modelData.type === "bool"
                                            checked: !!modelData.value
                                            onToggled: mainWindow.set_selected_node_property(modelData.key, checked)
                                        }

                                        ComboBox {
                                            width: parent.width
                                            visible: modelData.type === "enum"
                                            model: modelData.enum_values || []
                                            currentIndex: {
                                                var values = modelData.enum_values || []
                                                var value = String(modelData.value || "")
                                                var index = values.indexOf(value)
                                                return index >= 0 ? index : 0
                                            }
                                            onActivated: {
                                                var values = modelData.enum_values || []
                                                if (currentIndex < 0 || currentIndex >= values.length)
                                                    return
                                                mainWindow.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                            }
                                        }

                                        ComboBox {
                                            id: pinDataTypeEditor
                                            width: parent.width
                                            visible: modelData.type === "str"
                                                && modelData.key === "data_type"
                                                && mainWindow.selected_node_is_subnode_pin
                                            editable: true
                                            model: mainWindow.pin_data_type_options
                                            currentIndex: {
                                                var values = mainWindow.pin_data_type_options || []
                                                var value = String(modelData.value || "").toLowerCase()
                                                var index = values.indexOf(value)
                                                return index
                                            }
                                            Component.onCompleted: {
                                                if (visible)
                                                    editText = String(modelData.value || "")
                                            }
                                            onActivated: {
                                                var values = mainWindow.pin_data_type_options || []
                                                if (currentIndex < 0 || currentIndex >= values.length)
                                                    return
                                                mainWindow.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                            }
                                            onAccepted: mainWindow.set_selected_node_property(modelData.key, editText)
                                            onActiveFocusChanged: {
                                                if (!activeFocus)
                                                    mainWindow.set_selected_node_property(modelData.key, editText)
                                            }
                                        }

                                        TextField {
                                            width: parent.width
                                            visible: modelData.type !== "bool"
                                                && modelData.type !== "enum"
                                                && !(modelData.type === "str"
                                                    && modelData.key === "data_type"
                                                    && mainWindow.selected_node_is_subnode_pin)
                                            text: MainShellUtils.toEditorText(modelData)
                                            selectByMouse: true
                                            color: "#E6EDF8"
                                            background: Rectangle {
                                                color: "#272B33"
                                                border.color: "#434955"
                                                radius: 3
                                            }
                                            onAccepted: mainWindow.set_selected_node_property(modelData.key, text)
                                            onEditingFinished: mainWindow.set_selected_node_property(modelData.key, text)
                                        }
                                    }
                                }

                                Text {
                                    visible: mainWindow.has_selected_node && !mainWindow.selected_node_is_subnode_pin
                                    text: "Exposed Ports"
                                    color: "#9DA7BC"
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                Repeater {
                                    model: mainWindow.selected_node_port_items
                                    delegate: Rectangle {
                                        width: inspectorColumn.width
                                        height: 32
                                        color: "#232730"
                                        border.color: "#3A404A"
                                        radius: 3
                                        visible: mainWindow.has_selected_node && !mainWindow.selected_node_is_subnode_pin

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 6
                                            anchors.rightMargin: 6
                                            spacing: 6

                                            CheckBox {
                                                checked: modelData.exposed
                                                onToggled: mainWindow.set_selected_port_exposed(modelData.key, checked)
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.direction + ":" + (modelData.label || modelData.key) + " [" + modelData.kind + " / " + modelData.data_type + "]"
                                                color: "#CBD3E2"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
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
