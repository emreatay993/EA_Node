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
    property string libraryContextWorkflowId: ""
    property string libraryContextWorkflowScope: "local"

    function openLibraryWorkflowContextPopup(workflowId, workflowScope, positionX, positionY) {
        libraryContextWorkflowId = String(workflowId || "")
        libraryContextWorkflowScope = String(workflowScope || "local")
        var popupWidth = Math.max(1, Number(libraryContextPopup.implicitWidth) || 168)
        var popupHeight = Math.max(1, Number(libraryContextPopup.implicitHeight) || 58)
        libraryContextPopup.x = Math.max(0, Math.min(root.width - popupWidth, Math.round(Number(positionX) || 0)))
        libraryContextPopup.y = Math.max(0, Math.min(root.height - popupHeight, Math.round(Number(positionY) || 0)))
        libraryContextPopup.open()
    }

    onWidthChanged: {
        if (libraryContextPopup.visible)
            libraryContextPopup.close()
    }

    onHeightChanged: {
        if (libraryContextPopup.visible)
            libraryContextPopup.close()
    }

    Popup {
        id: libraryContextPopup
        parent: root
        modal: false
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape
        implicitWidth: 168
        implicitHeight: 58
        z: 1000

        background: Rectangle {
            color: "#2B2F37"
            border.color: "#4A4E58"
            radius: 3
        }

        contentItem: Column {
            spacing: 0

            Rectangle {
                width: libraryContextPopup.implicitWidth
                height: 29
                color: scopeMouseArea.containsMouse ? "#343943" : "transparent"

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    color: "#D7DDE9"
                    font.pixelSize: 11
                    text: root.libraryContextWorkflowScope === "global" ? "Make Project-Only" : "Make Global"
                }

                MouseArea {
                    id: scopeMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        var nextScope = root.libraryContextWorkflowScope === "global" ? "local" : "global"
                        mainWindow.request_set_custom_workflow_scope(root.libraryContextWorkflowId, nextScope)
                        libraryContextPopup.close()
                    }
                }
            }

            Rectangle {
                width: libraryContextPopup.implicitWidth
                height: 29
                color: deleteMouseArea.containsMouse ? "#343943" : "transparent"

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    color: "#D7DDE9"
                    font.pixelSize: 11
                    text: "Delete"
                }

                MouseArea {
                    id: deleteMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        mainWindow.request_delete_custom_workflow_from_library(
                            root.libraryContextWorkflowId,
                            root.libraryContextWorkflowScope
                        )
                        libraryContextPopup.close()
                    }
                }
            }
        }
    }

    Rectangle {
        id: libraryContextBackdrop
        anchors.fill: parent
        color: "transparent"
        visible: libraryContextPopup.visible
        z: 999

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: {
                libraryContextPopup.close()
                mouse.accepted = true
            }
            onWheel: function(wheel) {
                libraryContextPopup.close()
                wheel.accepted = true
            }
        }
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

            Rectangle {
                id: libraryPane
                objectName: "libraryPane"
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                color: "#24262D"
                border.color: "#3D4048"
                property var collapsedCategories: ({})
                function isCategoryCollapsed(category) {
                    var normalizedCategory = String(category || "")
                    if (!normalizedCategory.length)
                        return true
                    var value = collapsedCategories[normalizedCategory]
                    if (value === undefined)
                        return true
                    return !!value
                }
                function setCategoryCollapsed(category, collapsed) {
                    var normalizedCategory = String(category || "")
                    if (!normalizedCategory.length)
                        return
                    var nextMap = {}
                    for (var key in collapsedCategories)
                        nextMap[key] = collapsedCategories[key]
                    nextMap[normalizedCategory] = !!collapsed
                    collapsedCategories = nextMap
                }
                function ensureCollapsedDefaults(rows) {
                    if (!rows || rows.length === undefined)
                        return
                    var nextMap = {}
                    for (var key in collapsedCategories)
                        nextMap[key] = collapsedCategories[key]
                    var changed = false
                    for (var index = 0; index < rows.length; ++index) {
                        var row = rows[index]
                        if (!row || row.kind !== "category")
                            continue
                        var category = String(row.category || "")
                        if (!category.length || nextMap[category] !== undefined)
                            continue
                        nextMap[category] = true
                        changed = true
                    }
                    if (changed)
                        collapsedCategories = nextMap
                }
                function resetCollapsedState() {
                    collapsedCategories = ({})
                    ensureCollapsedDefaults(libraryListView.model)
                }

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
                        id: libraryListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: mainWindow.grouped_node_library_items
                        spacing: 0
                        Component.onCompleted: libraryPane.ensureCollapsedDefaults(model)
                        onModelChanged: libraryPane.ensureCollapsedDefaults(model)
                        delegate: Rectangle {
                            id: libraryRow
                            property bool isCategory: modelData.kind === "category"
                            property bool isCustomWorkflow: !isCategory && String(modelData.library_source || "") === "custom_workflow"
                            property string workflowScope: String(modelData.workflow_scope || "local")
                            property bool hiddenByCategory: !isCategory && libraryPane.isCategoryCollapsed(modelData.category)
                            property var dragPayload: isCategory ? null : {
                                "type_id": String(modelData.type_id || ""),
                                "display_name": String(modelData.display_name || ""),
                                "ports": modelData.ports || [],
                                "library_source": String(modelData.library_source || ""),
                                "workflow_id": String(modelData.workflow_id || ""),
                                "revision": Number(modelData.revision || 1),
                                "workflow_scope": String(modelData.workflow_scope || "local")
                            }
                            width: ListView.view.width
                            height: hiddenByCategory ? 0 : (isCategory ? 32 : 28)
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
                                    border.color: "#60CDFF"
                                    border.width: libraryRow.isCustomWorkflow && libraryRow.workflowScope === "local" ? 1.5 : 0
                                    color: libraryRow.isCustomWorkflow && libraryRow.workflowScope === "local" ? "transparent" : "#60CDFF"
                                }

                                Text {
                                    text: isCategory
                                        ? ((libraryPane.isCategoryCollapsed(modelData.category) ? "▸ " : "▾ ") + modelData.label)
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
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                drag.target: (isCategory || !(pressedButtons & Qt.LeftButton)) ? null : dragProxy
                                drag.axis: Drag.XAndYAxis
                                property real pressStartX: 0
                                property real pressStartY: 0
                                property bool movedState: false
                                onPressed: {
                                    if (mouse.button === Qt.RightButton) {
                                        if (libraryRow.isCustomWorkflow) {
                                            var pointInRoot = libraryRow.mapToItem(root, mouse.x, mouse.y)
                                            root.openLibraryWorkflowContextPopup(
                                                String(modelData.workflow_id || ""),
                                                libraryRow.workflowScope,
                                                pointInRoot.x,
                                                pointInRoot.y
                                            )
                                        }
                                        mouse.accepted = true
                                        return
                                    }
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
                                        libraryPane.setCategoryCollapsed(
                                            modelData.category,
                                            !libraryPane.isCategoryCollapsed(modelData.category)
                                        )
                                    } else {
                                        mainWindow.request_add_node_from_library(modelData.type_id)
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

                Connections {
                    target: mainWindow
                    function onLibraryPaneResetRequested() {
                        libraryPane.resetCollapsedState()
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
                        Layout.preferredHeight: 58
                        color: "#2B2D33"
                        border.color: "#3D414A"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 2

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 28
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
                                            onClicked: mainWindow.request_switch_view(modelData.view_id)
                                        }
                                    }
                                }
                                ShellButton {
                                    text: "+ View"
                                    onClicked: mainWindow.request_create_view()
                                }

                                Text {
                                    text: mainWindow.active_view_name ? ("Active: " + mainWindow.active_view_name) : ""
                                    color: "#AFB7C8"
                                    font.pixelSize: 11
                                }
                            }

                            Row {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 24
                                spacing: 2

                                Text {
                                    text: "Scope:"
                                    color: "#9EA8BB"
                                    font.pixelSize: 11
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Repeater {
                                    model: mainWindow.active_scope_breadcrumb_items
                                    delegate: Row {
                                        spacing: 2

                                        Text {
                                            visible: index > 0
                                            text: "›"
                                            color: "#7F8BA0"
                                            font.pixelSize: 11
                                            anchors.verticalCenter: parent.verticalCenter
                                        }

                                        ShellButton {
                                            text: String(modelData.label || "")
                                            implicitHeight: 22
                                            selectedStyle: index === mainWindow.active_scope_breadcrumb_items.length - 1
                                            onClicked: mainWindow.request_open_scope_breadcrumb(String(modelData.node_id || ""))
                                        }
                                    }
                                }

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
                            ShellButton {
                                y: 4
                                text: "+ Workspace"
                                onClicked: mainWindow.request_create_workspace()
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
