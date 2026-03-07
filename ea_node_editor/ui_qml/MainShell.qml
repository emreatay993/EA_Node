import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"

Rectangle {
    id: root
    color: "#202020"
    property var sceneBridgeRef: sceneBridge
    property var viewBridgeRef: viewBridge

    function toEditorText(item) {
        if (!item)
            return ""
        if (item.type === "json") {
            try {
                return JSON.stringify(item.value)
            } catch (error) {
                return ""
            }
        }
        if (item.value === undefined || item.value === null)
            return ""
        return String(item.value)
    }

    function comboOptionValue(model, index) {
        if (!model || index < 0 || index >= model.length)
            return ""
        var entry = model[index]
        if (!entry || entry.value === undefined || entry.value === null)
            return ""
        return String(entry.value)
    }

    function lineNumbersText(lineCount) {
        var count = Math.max(1, Number(lineCount) || 1)
        var lines = ""
        for (var i = 1; i <= count; i++) {
            lines += i
            if (i < count)
                lines += "\n"
        }
        return lines
    }

    component ShellButton: ToolButton {
        id: control
        property bool selectedStyle: false
        implicitHeight: 24
        implicitWidth: Math.max(64, label.implicitWidth + 16)
        padding: 0
        hoverEnabled: true

        contentItem: Text {
            id: label
            text: control.text
            color: control.selectedStyle ? "#DFF2FF" : "#D8DEEA"
            font.pixelSize: 11
            font.bold: control.selectedStyle
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: 2
            border.color: control.down ? "#5A606B" : "#4A4E58"
            color: control.selectedStyle
                ? "#2A4F68"
                : (control.down ? "#3A3E46" : (control.hovered ? "#343943" : "#2B2F37"))
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            color: "#1F2024"
            border.color: "#383838"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 8
                spacing: 8

                Text {
                    text: "Engineering"
                    color: "#C7D2E2"
                    font.pixelSize: 13
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: mainWindow.project_display_name
                    color: "#9AA1B0"
                    font.pixelSize: 11
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: "#2B2D33"
            border.color: "#3A3D44"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                ShellButton {
                    text: "Open"
                    onClicked: mainWindow.open_project_from_qml()
                }
                ShellButton {
                    text: "Save"
                    onClicked: mainWindow.save_project_from_qml()
                }
                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#474B54" }
                ShellButton {
                    text: "Run"
                    onClicked: mainWindow.run_from_qml()
                }
                ShellButton {
                    text: "Pause"
                    onClicked: mainWindow.pause_resume_from_qml()
                }
                ShellButton {
                    text: "Stop"
                    onClicked: mainWindow.stop_from_qml()
                }
                ShellButton {
                    text: "Connect"
                    onClicked: mainWindow.connect_selected_from_qml()
                }
                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#474B54" }
                ShellButton {
                    text: "+ Workspace"
                    onClicked: mainWindow.create_workspace_from_qml()
                }
                ShellButton {
                    text: "+ View"
                    onClicked: mainWindow.create_view_from_qml()
                }
                ShellButton {
                    text: "Settings"
                    onClicked: mainWindow.open_workflow_settings()
                }
                ShellButton {
                    text: scriptEditorBridge.visible ? "Hide Script" : "Script"
                    onClicked: mainWindow.toggle_script_editor()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "Zoom: " + Math.round(viewBridge.zoom_value * 100) + "%"
                    color: "#BDC4D2"
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                id: libraryPane
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                color: "#24262D"
                border.color: "#3D4048"
                property var collapsedCategories: ({})

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    Text {
                        text: "NODE LIBRARY"
                        color: "#AAB2C3"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    TextField {
                        id: searchField
                        Layout.fillWidth: true
                        placeholderText: "Search nodes..."
                        color: "#E6EDF8"
                        background: Rectangle {
                            color: "#2C2F37"
                            border.color: "#4A4E58"
                            radius: 3
                        }
                        onTextChanged: mainWindow.set_library_query(text)
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: mainWindow.grouped_node_library_items
                        spacing: 2
                        delegate: Rectangle {
                            id: libraryRow
                            property bool isCategory: modelData.kind === "category"
                            property bool hiddenByCategory: !isCategory && !!libraryPane.collapsedCategories[modelData.category]
                            property var dragPayload: isCategory ? null : {
                                "type_id": String(modelData.type_id || ""),
                                "display_name": String(modelData.display_name || ""),
                                "ports": modelData.ports || []
                            }
                            width: ListView.view.width
                            height: hiddenByCategory ? 0 : (isCategory ? 30 : 26)
                            color: hiddenByCategory ? "transparent"
                                : (mouseArea.containsMouse ? "#31343D" : "transparent")
                            radius: 4
                            visible: !hiddenByCategory

                            Item {
                                id: dragProxy
                                width: parent.width
                                height: parent.height
                                x: 0
                                y: 0
                                opacity: 0
                                Drag.active: !libraryRow.isCategory && mouseArea.drag.active
                                Drag.source: libraryRow
                                Drag.keys: ["ea-node-library"]
                                Drag.supportedActions: Qt.CopyAction
                                Drag.hotSpot.x: mouseArea.mouseX
                                Drag.hotSpot.y: mouseArea.mouseY
                                Drag.mimeData: libraryRow.dragPayload
                                    ? {
                                        "application/x-ea-node-library":
                                            JSON.stringify(libraryRow.dragPayload)
                                    }
                                    : ({})
                            }

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: isCategory ? 8 : 18
                                spacing: 6

                                Rectangle {
                                    width: isCategory ? 0 : 8
                                    height: isCategory ? 0 : 8
                                    radius: 4
                                    visible: !isCategory
                                    color: "#60CDFF"
                                }

                                Text {
                                    text: isCategory
                                        ? ((libraryPane.collapsedCategories[modelData.category] ? "▸ " : "▾ ") + modelData.label)
                                        : modelData.display_name
                                    color: isCategory ? "#CFD6E3" : "#D7DDE9"
                                    font.pixelSize: isCategory ? 12 : 11
                                    font.bold: isCategory
                                }
                            }

                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                preventStealing: true
                                acceptedButtons: Qt.LeftButton
                                drag.target: isCategory ? null : dragProxy
                                drag.axis: Drag.XAndYAxis
                                property real pressStartX: 0
                                property real pressStartY: 0
                                property bool movedState: false
                                onPressed: {
                                    if (mouse.button !== Qt.LeftButton)
                                        return
                                    dragProxy.x = 0
                                    dragProxy.y = 0
                                    graphCanvas.clearLibraryDropPreview()
                                    pressStartX = mouse.x
                                    pressStartY = mouse.y
                                    movedState = false
                                    mouse.accepted = true
                                }
                                onPositionChanged: {
                                    if (!pressed)
                                        return
                                    if (Math.abs(mouse.x - pressStartX) >= 2 || Math.abs(mouse.y - pressStartY) >= 2)
                                        movedState = true
                                    if (!movedState || isCategory)
                                        return
                                    var canvasPoint = mouseArea.mapToItem(graphCanvas, mouse.x, mouse.y)
                                    if (graphCanvas.isPointInCanvas(canvasPoint.x, canvasPoint.y))
                                        graphCanvas.updateLibraryDropPreview(canvasPoint.x, canvasPoint.y, libraryRow.dragPayload)
                                    else
                                        graphCanvas.clearLibraryDropPreview()
                                }
                                onReleased: {
                                    if (mouse.button !== Qt.LeftButton)
                                        return
                                    if (movedState) {
                                        if (!isCategory) {
                                            var canvasPoint = mouseArea.mapToItem(graphCanvas, mouse.x, mouse.y)
                                            if (graphCanvas.isPointInCanvas(canvasPoint.x, canvasPoint.y))
                                                graphCanvas.performLibraryDrop(canvasPoint.x, canvasPoint.y, libraryRow.dragPayload)
                                            else
                                                graphCanvas.clearLibraryDropPreview()
                                        } else {
                                            graphCanvas.clearLibraryDropPreview()
                                        }
                                        Qt.callLater(function() {
                                            dragProxy.x = 0
                                            dragProxy.y = 0
                                        })
                                        movedState = false
                                        return
                                    }
                                    if (isCategory) {
                                        var nextState = !libraryPane.collapsedCategories[modelData.category]
                                        var nextMap = {}
                                        for (var key in libraryPane.collapsedCategories)
                                            nextMap[key] = libraryPane.collapsedCategories[key]
                                        nextMap[modelData.category] = nextState
                                        libraryPane.collapsedCategories = nextMap
                                    } else {
                                        mainWindow.add_node_from_library(modelData.type_id)
                                    }
                                }
                                onCanceled: {
                                    movedState = false
                                    graphCanvas.clearLibraryDropPreview()
                                    Qt.callLater(function() {
                                        dragProxy.x = 0
                                        dragProxy.y = 0
                                    })
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#1B1D22"
                border.color: "#363A43"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        color: "#2B2D33"
                        border.color: "#3D414A"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8

                            Text {
                                text: "Workspace: " + mainWindow.active_workspace_name
                                color: "#D9DFEA"
                                font.pixelSize: 12
                                font.bold: true
                            }

                            Item { Layout.fillWidth: true }

                            Row {
                                spacing: 4
                                Repeater {
                                    model: mainWindow.active_view_items
                                    delegate: ShellButton {
                                        text: modelData.label
                                        selectedStyle: !!modelData.active
                                        onClicked: mainWindow.switch_view_from_qml(modelData.view_id)
                                    }
                                }
                            }

                            Text {
                                text: mainWindow.active_view_name ? ("Active: " + mainWindow.active_view_name) : ""
                                color: "#AFB7C8"
                                font.pixelSize: 11
                            }
                        }
                    }

                    GraphCanvas {
                        id: graphCanvas
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        mainWindowBridge: mainWindow
                        sceneBridge: root.sceneBridgeRef
                        viewBridge: root.viewBridgeRef
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        color: "#2A2C33"
                        border.color: "#3C4049"

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 6
                            anchors.rightMargin: 6
                            spacing: 4

                            Repeater {
                                model: workspaceTabsBridge.tabs
                                delegate: Rectangle {
                                    height: 24
                                    width: Math.max(120, tabText.implicitWidth + 24)
                                    y: 4
                                    radius: 4
                                    color: modelData.workspace_id === mainWindow.active_workspace_id ? "#3C4452" : "#2A2C33"
                                    border.color: modelData.workspace_id === mainWindow.active_workspace_id ? "#60CDFF" : "#444955"

                                    Text {
                                        id: tabText
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        color: "#E0E7F4"
                                        font.pixelSize: 12
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: workspaceTabsBridge.activate_workspace(modelData.workspace_id)
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 170
                        color: "#1F2228"
                        border.color: "#3B3F48"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 30
                                color: "#2A2D34"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 6
                                    anchors.rightMargin: 6
                                    spacing: 8

                                    ShellButton {
                                        text: "Output"
                                        selectedStyle: consoleTabs.currentIndex === 0
                                        onClicked: consoleTabs.currentIndex = 0
                                    }
                                    ShellButton {
                                        text: "Errors (" + consoleBridge.error_count_value + ")"
                                        selectedStyle: consoleTabs.currentIndex === 1
                                        onClicked: consoleTabs.currentIndex = 1
                                    }
                                    ShellButton {
                                        text: "Warnings (" + consoleBridge.warning_count_value + ")"
                                        selectedStyle: consoleTabs.currentIndex === 2
                                        onClicked: consoleTabs.currentIndex = 2
                                    }
                                    Item { Layout.fillWidth: true }
                                    ShellButton {
                                        text: "Clear"
                                        onClicked: consoleBridge.clear_all()
                                    }
                                }
                            }

                            StackLayout {
                                id: consoleTabs
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                TextArea {
                                    readOnly: true
                                    text: consoleBridge.output_text
                                    color: "#CBD3E2"
                                    font.family: "Consolas"
                                    font.pixelSize: 12
                                    wrapMode: TextArea.NoWrap
                                    background: Rectangle { color: "#1D2026" }
                                }
                                TextArea {
                                    readOnly: true
                                    text: consoleBridge.errors_text
                                    color: "#F7A1A1"
                                    font.family: "Consolas"
                                    font.pixelSize: 12
                                    wrapMode: TextArea.NoWrap
                                    background: Rectangle { color: "#1D2026" }
                                }
                                TextArea {
                                    readOnly: true
                                    text: consoleBridge.warnings_text
                                    color: "#E6D28D"
                                    font.family: "Consolas"
                                    font.pixelSize: 12
                                    wrapMode: TextArea.NoWrap
                                    background: Rectangle { color: "#1D2026" }
                                }
                            }
                        }
                    }
                }
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

                                        Loader {
                                            width: parent.width
                                            sourceComponent: modelData.type === "bool" ? boolPropertyEditor
                                                : (modelData.type === "enum" ? enumPropertyEditor : textPropertyEditor)
                                        }
                                    }
                                }

                                Text {
                                    visible: mainWindow.has_selected_node
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
                                        visible: mainWindow.has_selected_node

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
                                                text: modelData.direction + ":" + modelData.key + " [" + modelData.kind + " / " + modelData.data_type + "]"
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

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
            color: "#0D88C9"
            border.color: "#55B8E7"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 10

                Text { text: statusEngine.icon_value + " " + statusEngine.text_value; color: "#00131D"; font.pixelSize: 11; font.bold: true }
                Text { text: statusJobs.icon_value + " " + statusJobs.text_value; color: "#022234"; font.pixelSize: 11 }
                Text { text: statusMetrics.icon_value + " " + statusMetrics.text_value; color: "#022234"; font.pixelSize: 11 }
                Item { Layout.fillWidth: true }
                Text { text: statusNotifications.icon_value + " " + statusNotifications.text_value; color: "#022234"; font.pixelSize: 11 }
            }
        }
    }

    Component {
        id: boolPropertyEditor
        CheckBox {
            checked: !!modelData.value
            onToggled: mainWindow.set_selected_node_property(modelData.key, checked)
        }
    }

    Component {
        id: enumPropertyEditor
        ComboBox {
            width: parent ? parent.width : 200
            model: modelData.enum_values || []
            currentIndex: Math.max(0, model.indexOf(String(modelData.value)))
            onActivated: mainWindow.set_selected_node_property(modelData.key, currentText)
        }
    }

    Component {
        id: textPropertyEditor
        TextField {
            width: parent ? parent.width : 200
            text: root.toEditorText(modelData)
            selectByMouse: true
            color: "#E6EDF8"
            background: Rectangle {
                color: "#272B33"
                border.color: "#434955"
                radius: 3
            }
            onEditingFinished: mainWindow.set_selected_node_property(modelData.key, text)
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
                        onClicked: mainWindow.toggle_script_editor(false)
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
                        text: root.lineNumbersText(scriptEditorArea.lineCount)
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
}
