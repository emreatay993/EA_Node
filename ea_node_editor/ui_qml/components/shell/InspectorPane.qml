import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "MainShellUtils.js" as MainShellUtils

Rectangle {
    id: root
    property var mainWindowRef
    property bool paneCollapsed: false
    property string activePortDirection: "in"
    property string selectedPortKey: ""
    property int collapsedRailWidth: 0
    property int collapsedHandleWidth: 30
    property int collapsedTabTopMargin: 112
    property real animatedPaneWidth: root.paneCollapsed ? root.collapsedRailWidth : 300
    property real expandedContentOpacity: root.paneCollapsed ? 0 : 1
    property real collapsedHandleShift: root.paneCollapsed ? 0 : 12
    readonly property var themePalette: themeBridge.palette
    readonly property bool showPortSection: root.mainWindowRef.has_selected_node
        && !root.mainWindowRef.selected_node_is_subnode_pin
    readonly property bool canManageSubnodePorts: root.mainWindowRef.selected_node_is_subnode_shell
    readonly property var visiblePortItems: root.portItemsForDirection(activePortDirection)

    Layout.preferredWidth: root.animatedPaneWidth
    Layout.fillHeight: true
    color: root.paneCollapsed ? "transparent" : themePalette.panel_alt_bg
    border.color: root.paneCollapsed ? "transparent" : themePalette.border
    clip: false

    Behavior on animatedPaneWidth {
        NumberAnimation {
            duration: 240
            easing.type: Easing.InOutCubic
        }
    }

    Behavior on expandedContentOpacity {
        NumberAnimation {
            duration: 150
            easing.type: Easing.OutCubic
        }
    }

    function portItemsForDirection(direction) {
        var normalizedDirection = String(direction || "").toLowerCase()
        var items = root.mainWindowRef.selected_node_port_items || []
        var filtered = []
        for (var index = 0; index < items.length; ++index) {
            var item = items[index]
            if (!item)
                continue
            if (String(item.direction || "").toLowerCase() !== normalizedDirection)
                continue
            filtered.push(item)
        }
        return filtered
    }

    function hasVisiblePort(portKey) {
        var normalizedKey = String(portKey || "")
        if (!normalizedKey.length)
            return false
        for (var index = 0; index < visiblePortItems.length; ++index) {
            var item = visiblePortItems[index]
            if (String(item.key || "") === normalizedKey)
                return true
        }
        return false
    }

    function syncSelectedPortSelection() {
        if (!showPortSection || visiblePortItems.length === 0) {
            selectedPortKey = ""
            return
        }
        if (!hasVisiblePort(selectedPortKey))
            selectedPortKey = String(visiblePortItems[0].key || "")
    }

    function addSubnodePort(direction) {
        var normalizedDirection = String(direction || "").toLowerCase()
        var createdPortKey = root.mainWindowRef.request_add_selected_subnode_pin(normalizedDirection)
        if (!String(createdPortKey || "").length)
            return
        activePortDirection = normalizedDirection
        selectedPortKey = String(createdPortKey)
    }

    onVisiblePortItemsChanged: syncSelectedPortSelection()
    onShowPortSectionChanged: syncSelectedPortSelection()

    Connections {
        target: root.mainWindowRef

        function onSelectedNodeChanged() {
            root.syncSelectedPortSelection()
        }
    }

    Rectangle {
        width: root.collapsedHandleWidth
        height: Math.max(132, collapsedTabLabel.implicitWidth + 44)
        anchors.top: parent.top
        anchors.topMargin: root.collapsedTabTopMargin
        anchors.right: parent.right
        visible: root.paneCollapsed || opacity > 0.01
        z: 2
        color: root.themePalette.panel_bg
        border.color: root.themePalette.border
        radius: 10
        opacity: root.paneCollapsed ? 1 : 0

        transform: Translate {
            id: collapsedHandleTranslate
            x: root.collapsedHandleShift
            Behavior on x {
                NumberAnimation {
                    duration: 170
                    easing.type: Easing.OutCubic
                }
            }
        }

        Behavior on opacity {
            NumberAnimation {
                duration: 140
                easing.type: Easing.OutCubic
            }
        }

        Rectangle {
            width: 10
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            color: parent.color
        }

        Column {
            anchors.centerIn: parent
            spacing: 6

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "‹"
                color: root.themePalette.group_title_fg
                font.pixelSize: 15
                font.bold: true
            }

            Item {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 14
                height: collapsedTabLabel.implicitWidth + 6

                Text {
                    id: collapsedTabLabel
                    anchors.centerIn: parent
                    rotation: -90
                    transformOrigin: Item.Center
                    text: "PROPERTIES"
                    color: root.themePalette.group_title_fg
                    font.pixelSize: 11
                    font.bold: true
                    renderType: Text.NativeRendering
                }
            }
        }

        TapHandler {
            enabled: root.paneCollapsed
            onTapped: root.paneCollapsed = false
        }
    }

    Item {
        anchors.fill: parent
        visible: root.expandedContentOpacity > 0.01
        opacity: root.expandedContentOpacity
        enabled: root.expandedContentOpacity > 0.99
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    text: "PROPERTIES"
                    color: root.themePalette.group_title_fg
                    font.pixelSize: 12
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                ShellButton {
                    text: "›"
                    tooltipText: "Collapse properties pane"
                    onClicked: root.paneCollapsed = true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: root.mainWindowRef.has_selected_node
                color: root.themePalette.panel_bg
                border.color: root.themePalette.border
                radius: 10
                implicitHeight: heroContent.implicitHeight + 26

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: 1
                    anchors.rightMargin: 1
                    anchors.topMargin: 1
                    height: 4
                    radius: 10
                    color: root.themePalette.accent
                }

                ColumnLayout {
                    id: heroContent
                    anchors.fill: parent
                    anchors.margins: 12
                    anchors.topMargin: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: root.mainWindowRef.selected_node_title
                                color: root.themePalette.panel_title_fg
                                font.pixelSize: 18
                                font.bold: true
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: text.length > 0
                                text: root.mainWindowRef.selected_node_subtitle
                                wrapMode: Text.WordWrap
                                color: root.themePalette.muted_fg
                                font.pixelSize: 11
                            }
                        }

                        ShellButton {
                            visible: root.mainWindowRef.selected_node_collapsible
                            text: root.mainWindowRef.selected_node_collapsed ? "Expand Node" : "Collapse Node"
                            selectedStyle: root.mainWindowRef.selected_node_collapsed
                            tooltipText: root.mainWindowRef.selected_node_collapsed
                                ? "Expand the selected node body"
                                : "Collapse the selected node body"
                            onClicked: root.mainWindowRef.set_selected_node_collapsed(!root.mainWindowRef.selected_node_collapsed)
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        width: parent.width
                        spacing: 6
                        visible: root.mainWindowRef.selected_node_header_items.length > 0

                        Repeater {
                            model: root.mainWindowRef.selected_node_header_items

                            delegate: Rectangle {
                                height: 28
                                width: chipRow.implicitWidth + 18
                                radius: 14
                                color: root.themePalette.accent_strong
                                border.color: root.themePalette.accent

                                Row {
                                    id: chipRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        text: modelData.label
                                        color: root.themePalette.accent
                                        font.pixelSize: 10
                                        font.bold: true
                                    }

                                    Text {
                                        text: modelData.value
                                        color: root.themePalette.tab_selected_fg
                                        font.pixelSize: 10
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: root.themePalette.panel_bg
                border.color: root.themePalette.border
                radius: 8

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
                            visible: !root.mainWindowRef.has_selected_node
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: "Select a node to edit properties and port exposure."
                            color: root.themePalette.muted_fg
                            font.pixelSize: 12
                        }

                        Text {
                            visible: root.mainWindowRef.selected_node_is_subnode_pin
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: "Pin ports are configured through Label, Kind, and Data Type."
                            color: root.themePalette.accent
                            font.pixelSize: 10
                        }

                        Repeater {
                            model: root.mainWindowRef.selected_node_property_items

                            delegate: Column {
                                width: inspectorColumn.width
                                spacing: 4
                                visible: root.mainWindowRef.has_selected_node

                                Text {
                                    width: parent.width
                                    text: modelData.label
                                    color: root.themePalette.tab_fg
                                    font.pixelSize: 11
                                }

                                CheckBox {
                                    width: parent.width
                                    visible: modelData.type === "bool"
                                    checked: !!modelData.value
                                    onToggled: root.mainWindowRef.set_selected_node_property(modelData.key, checked)
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
                                        root.mainWindowRef.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                    }
                                }

                                ComboBox {
                                    id: pinDataTypeEditor
                                    width: parent.width
                                    visible: modelData.type === "str"
                                        && modelData.key === "data_type"
                                        && root.mainWindowRef.selected_node_is_subnode_pin
                                    editable: true
                                    model: root.mainWindowRef.pin_data_type_options
                                    currentIndex: {
                                        var values = root.mainWindowRef.pin_data_type_options || []
                                        var value = String(modelData.value || "").toLowerCase()
                                        var index = values.indexOf(value)
                                        return index
                                    }
                                    Component.onCompleted: {
                                        if (visible)
                                            editText = String(modelData.value || "")
                                    }
                                    onActivated: {
                                        var values = root.mainWindowRef.pin_data_type_options || []
                                        if (currentIndex < 0 || currentIndex >= values.length)
                                            return
                                        root.mainWindowRef.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                    }
                                    onAccepted: root.mainWindowRef.set_selected_node_property(modelData.key, editText)
                                    onActiveFocusChanged: {
                                        if (!activeFocus)
                                            root.mainWindowRef.set_selected_node_property(modelData.key, editText)
                                    }
                                }

                                TextField {
                                    width: parent.width
                                    visible: modelData.type !== "bool"
                                        && modelData.type !== "enum"
                                        && !(modelData.type === "str"
                                            && modelData.key === "data_type"
                                            && root.mainWindowRef.selected_node_is_subnode_pin)
                                    text: MainShellUtils.toEditorText(modelData)
                                    selectByMouse: true
                                    color: root.themePalette.input_fg
                                    background: Rectangle {
                                        color: root.themePalette.input_bg
                                        border.color: root.themePalette.input_border
                                        radius: 3
                                    }
                                    onAccepted: root.mainWindowRef.set_selected_node_property(modelData.key, text)
                                    onEditingFinished: root.mainWindowRef.set_selected_node_property(modelData.key, text)
                                }
                            }
                        }

                        Column {
                            width: inspectorColumn.width
                            spacing: 8
                            visible: root.showPortSection

                            RowLayout {
                                width: parent.width
                                spacing: 6

                                Text {
                                    text: "Ports"
                                    color: root.themePalette.muted_fg
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                Item { Layout.fillWidth: true }

                                ShellButton {
                                    visible: root.canManageSubnodePorts
                                    text: "+ Input"
                                    tooltipText: "Add an input port to the selected subnode"
                                    onClicked: root.addSubnodePort("in")
                                }

                                ShellButton {
                                    visible: root.canManageSubnodePorts
                                    text: "+ Output"
                                    tooltipText: "Add an output port to the selected subnode"
                                    onClicked: root.addSubnodePort("out")
                                }

                                ShellButton {
                                    visible: root.canManageSubnodePorts
                                    enabled: root.selectedPortKey.length > 0
                                    text: "Delete"
                                    tooltipText: "Delete the selected subnode port"
                                    onClicked: {
                                        if (!enabled)
                                            return
                                        root.mainWindowRef.request_remove_node(root.selectedPortKey)
                                    }
                                }
                            }

                            RowLayout {
                                width: parent.width
                                spacing: 6

                                ShellButton {
                                    text: "Inputs (" + root.portItemsForDirection("in").length + ")"
                                    selectedStyle: root.activePortDirection === "in"
                                    onClicked: root.activePortDirection = "in"
                                }

                                ShellButton {
                                    text: "Outputs (" + root.portItemsForDirection("out").length + ")"
                                    selectedStyle: root.activePortDirection === "out"
                                    onClicked: root.activePortDirection = "out"
                                }
                            }

                            Text {
                                visible: root.visiblePortItems.length === 0
                                width: parent.width
                                wrapMode: Text.WordWrap
                                text: root.activePortDirection === "in"
                                    ? "No input ports available."
                                    : "No output ports available."
                                color: root.themePalette.muted_fg
                                font.pixelSize: 11
                            }

                            Repeater {
                                model: root.visiblePortItems

                                delegate: Rectangle {
                                    width: inspectorColumn.width
                                    height: 42
                                    radius: 4
                                    color: root.selectedPortKey === String(modelData.key || "")
                                        ? root.themePalette.hover
                                        : root.themePalette.tab_bg
                                    border.color: root.selectedPortKey === String(modelData.key || "")
                                        ? root.themePalette.accent
                                        : root.themePalette.border

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        anchors.rightMargin: 6
                                        spacing: 6

                                        CheckBox {
                                            checked: !!modelData.exposed
                                            onToggled: root.mainWindowRef.set_selected_port_exposed(modelData.key, checked)
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 0

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(modelData.label || modelData.key || "")
                                                color: root.themePalette.app_fg
                                                font.pixelSize: 11
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(modelData.kind || "") + " / " + String(modelData.data_type || "any")
                                                color: root.themePalette.muted_fg
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }

                                        Text {
                                            text: modelData.required ? "Required" : ""
                                            color: root.themePalette.muted_fg
                                            font.pixelSize: 10
                                            visible: text.length > 0
                                        }
                                    }

                                    TapHandler {
                                        onTapped: root.selectedPortKey = String(modelData.key || "")
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
