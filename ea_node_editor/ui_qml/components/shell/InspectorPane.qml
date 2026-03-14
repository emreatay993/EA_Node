import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "MainShellUtils.js" as MainShellUtils

ShellCollapsibleSidePane {
    id: root
    objectName: "inspectorPane"
    property var mainWindowRef
    property string activePortDirection: "in"
    property string selectedPortKey: ""
    property string editingPortKey: ""
    property string editingPortLabel: ""
    readonly property bool hasSelectedNode: !!root.mainWindowRef && root.mainWindowRef.has_selected_node
    readonly property bool isPinInspector: !!root.mainWindowRef && root.mainWindowRef.selected_node_is_subnode_pin
    readonly property bool showPortSection: root.hasSelectedNode && !root.isPinInspector
    readonly property bool canManageSubnodePorts: !!root.mainWindowRef && root.mainWindowRef.selected_node_is_subnode_shell
    readonly property var visiblePortItems: root.portItemsForDirection(activePortDirection)
    readonly property int inputPortCount: root.portItemsForDirection("in").length
    readonly property int outputPortCount: root.portItemsForDirection("out").length
    readonly property color cardBackgroundColor: root.themePalette.inspector_card_bg
    readonly property color sectionHeaderColor: root.themePalette.inspector_section_header_bg
    readonly property color selectedSurfaceColor: root.themePalette.inspector_selected_bg
    readonly property color selectedOutlineColor: root.themePalette.inspector_selected_border

    paneTitle: "PROPERTIES"
    side: "right"
    expandedWidth: 300
    contentSpacing: 0
    collapseButtonTooltip: "Collapse properties pane"
    expandHandleTooltip: "Expand properties pane"

    function portItemsForDirection(direction) {
        var normalizedDirection = String(direction || "").toLowerCase()
        var items = root.mainWindowRef ? (root.mainWindowRef.selected_node_port_items || []) : []
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

    function portItemByKey(portKey) {
        var normalizedKey = String(portKey || "")
        if (!normalizedKey.length)
            return null
        var items = root.mainWindowRef ? (root.mainWindowRef.selected_node_port_items || []) : []
        for (var index = 0; index < items.length; ++index) {
            var item = items[index]
            if (!item)
                continue
            if (String(item.key || "") === normalizedKey)
                return item
        }
        return null
    }

    function syncSelectedPortSelection() {
        if (!showPortSection || visiblePortItems.length === 0) {
            selectedPortKey = ""
            editingPortKey = ""
            editingPortLabel = ""
            return
        }
        if (!hasVisiblePort(selectedPortKey))
            selectedPortKey = String(visiblePortItems[0].key || "")
        if (editingPortKey.length > 0 && !hasVisiblePort(editingPortKey)) {
            editingPortKey = ""
            editingPortLabel = ""
        }
    }

    function addSubnodePort(direction) {
        var normalizedDirection = String(direction || "").toLowerCase()
        if (!root.mainWindowRef)
            return
        var createdPortKey = root.mainWindowRef.request_add_selected_subnode_pin(normalizedDirection)
        if (!String(createdPortKey || "").length)
            return
        activePortDirection = normalizedDirection
        selectedPortKey = String(createdPortKey)
    }

    function selectPort(portKey) {
        var normalizedKey = String(portKey || "")
        if (!normalizedKey.length)
            return
        selectedPortKey = normalizedKey
    }

    function beginPortLabelEdit(portKey) {
        var normalizedKey = String(portKey || "")
        if (!canManageSubnodePorts || !normalizedKey.length)
            return
        var item = portItemByKey(normalizedKey)
        editingPortLabel = String(item ? (item.label || item.key || "") : normalizedKey)
        selectPort(normalizedKey)
        editingPortKey = normalizedKey
    }

    function commitPortLabelEdit(portKey, label) {
        var normalizedKey = String(portKey || "")
        if (editingPortKey !== normalizedKey)
            return
        if (root.mainWindowRef)
            root.mainWindowRef.set_selected_port_label(normalizedKey, String(label || ""))
        editingPortKey = ""
        editingPortLabel = ""
    }

    function cancelPortLabelEdit(portKey) {
        var normalizedKey = String(portKey || "")
        if (editingPortKey === normalizedKey) {
            editingPortKey = ""
            editingPortLabel = ""
        }
    }

    function focusInspectorBackground() {
        if (editingPortKey.length > 0)
            commitPortLabelEdit(editingPortKey, editingPortLabel)
        root.forceActiveFocus()
    }

    function deleteSelectedPort() {
        var normalizedKey = String(selectedPortKey || "")
        if (!root.mainWindowRef || !normalizedKey.length)
            return
        focusInspectorBackground()
        root.mainWindowRef.request_remove_selected_port(normalizedKey)
    }

    onVisiblePortItemsChanged: syncSelectedPortSelection()
    onShowPortSectionChanged: syncSelectedPortSelection()

    Connections {
        target: root.mainWindowRef

        function onSelectedNodeChanged() {
            root.syncSelectedPortSelection()
        }
    }

    component InspectorSectionCard : Rectangle {
        id: card
        property string title: ""
        property string subtitle: ""
        default property alias bodyData: bodyColumn.data

        width: parent ? parent.width : implicitWidth
        radius: 12
        color: root.cardBackgroundColor
        border.color: root.themePalette.border
        border.width: 1
        clip: true
        implicitHeight: cardColumn.implicitHeight

        Column {
            id: cardColumn
            width: parent.width
            spacing: 0

            Rectangle {
                width: parent.width
                height: headerColumn.implicitHeight + 14
                color: root.sectionHeaderColor

                Column {
                    id: headerColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: subtitleLabel.visible ? 2 : 0

                    Text {
                        text: card.title.toUpperCase()
                        color: root.themePalette.group_title_fg
                        font.pixelSize: 10
                        font.bold: true
                        font.letterSpacing: 0.9
                        elide: Text.ElideRight
                    }

                    Text {
                        id: subtitleLabel
                        visible: card.subtitle.length > 0
                        text: card.subtitle
                        color: root.themePalette.muted_fg
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Item {
                width: parent.width
                implicitHeight: bodyColumn.implicitHeight + 18

                Column {
                    id: bodyColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 8
                }
            }
        }
    }

    component InspectorMetadataChip : Rectangle {
        id: chip
        property string labelText: ""
        property string valueText: ""

        color: "transparent"
        height: metadataRow.implicitHeight
        width: Math.min(metadataFlow.width, metadataRow.implicitWidth)

        Row {
            id: metadataRow
            spacing: 8

            Text {
                text: chip.labelText.toUpperCase()
                anchors.verticalCenter: valuePill.verticalCenter
                color: root.themePalette.muted_fg
                font.pixelSize: 9
                font.bold: true
                font.letterSpacing: 0.6
                elide: Text.ElideRight
            }

            Rectangle {
                id: valuePill
                radius: 8
                color: root.themePalette.input_bg
                border.color: root.themePalette.input_border
                border.width: 1
                height: valueLabel.implicitHeight + 10
                width: valueLabel.implicitWidth + 18

                Text {
                    id: valueLabel
                    anchors.centerIn: parent
                    text: chip.valueText
                    color: root.themePalette.panel_title_fg
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                }
            }
        }
    }

    component InspectorButton : Button {
        id: control
        property bool destructive: false
        property bool selectedStyle: false
        property bool compact: false
        property string tooltipText: ""
        readonly property color fillColor: !enabled
            ? root.themePalette.tab_bg
            : destructive
                ? (down ? root.themePalette.inspector_danger_border
                    : (hovered ? root.themePalette.inspector_danger_border : root.themePalette.inspector_danger_bg))
                : selectedStyle
                    ? root.themePalette.accent_strong
                    : (down
                        ? root.themePalette.hover
                        : (hovered ? root.themePalette.hover : root.themePalette.input_bg))
        readonly property color outlineColor: destructive
            ? root.themePalette.inspector_danger_border
            : (selectedStyle ? root.themePalette.accent : root.themePalette.input_border)
        readonly property color labelColor: !enabled
            ? root.themePalette.muted_fg
            : (destructive
                ? root.themePalette.inspector_danger_fg
                : (selectedStyle ? root.themePalette.panel_title_fg : root.themePalette.tab_fg))

        implicitHeight: compact ? 30 : 36
        implicitWidth: Math.max(compact ? 80 : 92, label.implicitWidth + (compact ? 18 : 22))
        hoverEnabled: true
        padding: 0

        ToolTip.visible: hovered && tooltipText.length > 0
        ToolTip.delay: 280
        ToolTip.text: tooltipText

        contentItem: Text {
            id: label
            text: control.text
            color: control.labelColor
            font.pixelSize: control.compact ? 10 : 12
            font.bold: true
            font.letterSpacing: control.compact ? 0.5 : 0.2
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: control.compact ? 10 : 11
            color: control.fillColor
            border.color: control.outlineColor
            border.width: 1
        }
    }

    component InspectorSegmentButton : Button {
        id: control
        property bool selectedStyle: false
        readonly property color fillColor: selectedStyle
            ? root.selectedSurfaceColor
            : (down ? root.themePalette.hover : (hovered ? root.themePalette.hover : "transparent"))
        readonly property color outlineColor: selectedStyle ? root.selectedOutlineColor : "transparent"
        readonly property color labelColor: selectedStyle ? root.themePalette.panel_title_fg : root.themePalette.muted_fg

        implicitHeight: 38
        hoverEnabled: true
        padding: 0

        contentItem: Text {
            text: control.text
            color: control.labelColor
            font.pixelSize: 11
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 9
            color: control.fillColor
            border.color: control.outlineColor
            border.width: 1
        }
    }

    component InspectorCheckBox : CheckBox {
        id: control
        hoverEnabled: true
        spacing: 8
        padding: 0

        indicator: Rectangle {
            implicitWidth: 16
            implicitHeight: 16
            radius: 4
            color: control.checked ? root.themePalette.accent : root.themePalette.input_bg
            border.color: control.checked ? root.themePalette.accent : root.themePalette.input_border
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: control.checked ? "✓" : ""
                color: control.checked ? root.themePalette.panel_bg : "transparent"
                font.pixelSize: 10
                font.bold: true
            }
        }

        contentItem: Text {
            text: control.text
            visible: text.length > 0
            leftPadding: control.indicator.width + control.spacing
            color: root.themePalette.input_fg
            font.pixelSize: 11
            verticalAlignment: Text.AlignVCenter
        }
    }

    component InspectorTextField : TextField {
        id: control
        implicitHeight: 34
        padding: 8
        selectByMouse: true
        color: root.themePalette.input_fg
        selectionColor: root.selectedSurfaceColor
        selectedTextColor: root.themePalette.panel_title_fg

        background: Rectangle {
            radius: 9
            color: root.themePalette.input_bg
            border.color: control.activeFocus ? root.themePalette.accent : root.themePalette.input_border
            border.width: 1
        }
    }

    component InspectorComboBox : ComboBox {
        id: control
        implicitHeight: 34
        leftPadding: 8
        rightPadding: 30
        hoverEnabled: true
        font.pixelSize: 11
        palette.buttonText: root.themePalette.input_fg
        palette.text: root.themePalette.input_fg
        palette.highlight: root.selectedSurfaceColor
        palette.highlightedText: root.themePalette.panel_title_fg
        palette.base: root.themePalette.input_bg
        palette.window: root.cardBackgroundColor

        indicator: Text {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: "▾"
            color: root.themePalette.muted_fg
            font.pixelSize: 11
            font.bold: true
        }

        contentItem: Text {
            leftPadding: 0
            rightPadding: 0
            text: control.displayText
            color: root.themePalette.input_fg
            font: control.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 10
            color: root.themePalette.input_bg
            border.color: control.activeFocus ? root.themePalette.accent : root.themePalette.input_border
            border.width: 1
        }

        delegate: ItemDelegate {
            width: ListView.view ? ListView.view.width : control.width
            highlighted: control.highlightedIndex === index
            contentItem: Text {
                text: modelData
                color: highlighted ? root.themePalette.panel_title_fg : root.themePalette.input_fg
                font.pixelSize: 11
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: highlighted ? root.selectedSurfaceColor : "transparent"
                radius: 7
            }
        }

        popup: Popup {
            y: control.height + 4
            width: control.width
            padding: 4

            background: Rectangle {
                radius: 9
                color: root.cardBackgroundColor
                border.color: root.themePalette.input_border
                border.width: 1
            }

            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
        }
    }

    component InspectorEditableComboBox : ComboBox {
        id: control
        implicitHeight: 34
        editable: true
        leftPadding: 8
        rightPadding: 30
        hoverEnabled: true
        font.pixelSize: 11
        palette.buttonText: root.themePalette.input_fg
        palette.text: root.themePalette.input_fg
        palette.highlight: root.selectedSurfaceColor
        palette.highlightedText: root.themePalette.panel_title_fg
        palette.base: root.themePalette.input_bg
        palette.window: root.cardBackgroundColor

        indicator: Text {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: "▾"
            color: root.themePalette.muted_fg
            font.pixelSize: 11
            font.bold: true
        }

        background: Rectangle {
            radius: 9
            color: root.themePalette.input_bg
            border.color: control.activeFocus ? root.themePalette.accent : root.themePalette.input_border
            border.width: 1
        }

        delegate: ItemDelegate {
            width: ListView.view ? ListView.view.width : control.width
            highlighted: control.highlightedIndex === index
            contentItem: Text {
                text: modelData
                color: highlighted ? root.themePalette.panel_title_fg : root.themePalette.input_fg
                font.pixelSize: 11
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: highlighted ? root.selectedSurfaceColor : "transparent"
                radius: 7
            }
        }

        popup: Popup {
            y: control.height + 4
            width: control.width
            padding: 4

            background: Rectangle {
                radius: 9
                color: root.cardBackgroundColor
                border.color: root.themePalette.input_border
                border.width: 1
            }

            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
        }
    }

    contentData: [
        Rectangle {
            objectName: "inspectorContentSurface"
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            TapHandler {
                enabled: root.editingPortKey.length > 0
                acceptedButtons: Qt.LeftButton
                onTapped: root.focusInspectorBackground()
            }

            ScrollView {
                id: inspectorScroll
                objectName: "inspectorScrollView"
                anchors.fill: parent
                anchors.leftMargin: 2
                anchors.rightMargin: 2
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                TapHandler {
                    enabled: root.editingPortKey.length > 0
                    acceptedButtons: Qt.LeftButton
                    onTapped: root.focusInspectorBackground()
                }

                background: Rectangle {
                    color: "transparent"

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        onTapped: root.focusInspectorBackground()
                    }
                }

                Column {
                    id: inspectorColumn
                    width: inspectorScroll.availableWidth
                    spacing: 10

                    InspectorSectionCard {
                        objectName: "inspectorEmptyStateCard"
                        width: inspectorColumn.width
                        visible: !root.hasSelectedNode
                        title: "No Selection"
                        subtitle: "Select a node on the graph to inspect its properties and exposed ports."

                        Text {
                            width: parent.width
                            text: "The selected node's definition, editable fields, and port exposure controls will appear here."
                            wrapMode: Text.WordWrap
                            color: root.themePalette.muted_fg
                            font.pixelSize: 11
                        }
                    }

                    InspectorSectionCard {
                        objectName: "inspectorNodeDefinitionCard"
                        width: inspectorColumn.width
                        visible: root.hasSelectedNode
                        title: "Node Definition"

                        RowLayout {
                            width: parent.width
                            spacing: 8

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    Layout.fillWidth: true
                                    text: root.mainWindowRef ? root.mainWindowRef.selected_node_title : ""
                                    color: root.themePalette.panel_title_fg
                                    font.pixelSize: 18
                                    font.bold: true
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    visible: text.length > 0
                                    text: root.mainWindowRef ? root.mainWindowRef.selected_node_subtitle : ""
                                    wrapMode: Text.WordWrap
                                    color: root.themePalette.muted_fg
                                    font.pixelSize: 11
                                }
                            }

                            InspectorButton {
                                objectName: "inspectorCollapseButton"
                                visible: root.mainWindowRef && root.mainWindowRef.selected_node_collapsible
                                compact: true
                                selectedStyle: root.mainWindowRef && root.mainWindowRef.selected_node_collapsed
                                text: root.mainWindowRef && root.mainWindowRef.selected_node_collapsed ? "EXPAND" : "COLLAPSE"
                                tooltipText: root.mainWindowRef && root.mainWindowRef.selected_node_collapsed
                                    ? "Expand the selected node body"
                                    : "Collapse the selected node body"
                                onClicked: {
                                    if (!root.mainWindowRef)
                                        return
                                    root.mainWindowRef.set_selected_node_collapsed(!root.mainWindowRef.selected_node_collapsed)
                                }
                            }
                        }

                        Flow {
                            id: metadataFlow
                            width: parent.width
                            spacing: 6
                            visible: root.mainWindowRef && root.mainWindowRef.selected_node_header_items.length > 0

                            Repeater {
                                model: root.mainWindowRef ? root.mainWindowRef.selected_node_header_items : []

                                delegate: InspectorMetadataChip {
                                    labelText: String(modelData.label || "")
                                    valueText: String(modelData.value || "")
                                }
                            }
                        }

                        Rectangle {
                            objectName: "inspectorPinHintBanner"
                            width: parent.width
                            visible: root.isPinInspector
                            radius: 10
                            color: root.selectedSurfaceColor
                            border.color: root.selectedOutlineColor
                            border.width: 1
                            implicitHeight: pinHintText.implicitHeight + 14

                            Text {
                                id: pinHintText
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                text: "Pin ports are configured through Label, Kind, and Data Type."
                                wrapMode: Text.WordWrap
                                color: root.themePalette.panel_title_fg
                                font.pixelSize: 10
                                font.bold: true
                            }
                        }

                        Repeater {
                            model: root.mainWindowRef ? root.mainWindowRef.selected_node_property_items : []

                            delegate: Column {
                                width: parent.width
                                spacing: 4

                                Text {
                                    width: parent.width
                                    text: String(modelData.label || "")
                                    color: root.themePalette.group_title_fg
                                    font.pixelSize: 10
                                    font.bold: true
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    width: parent.width
                                    visible: modelData.type === "bool"
                                    radius: 10
                                    color: root.themePalette.input_bg
                                    border.color: root.themePalette.input_border
                                    border.width: 1
                                    implicitHeight: 38

                                    Row {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        spacing: 8

                                        InspectorCheckBox {
                                            id: boolToggle
                                            checked: !!modelData.value
                                            onToggled: {
                                                if (root.mainWindowRef)
                                                    root.mainWindowRef.set_selected_node_property(modelData.key, checked)
                                            }
                                        }

                                        Text {
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: boolToggle.checked ? "Enabled" : "Disabled"
                                            color: root.themePalette.input_fg
                                            font.pixelSize: 11
                                        }
                                    }
                                }

                                InspectorComboBox {
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
                                        if (!root.mainWindowRef || currentIndex < 0 || currentIndex >= values.length)
                                            return
                                        root.mainWindowRef.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                    }
                                }

                                InspectorEditableComboBox {
                                    id: pinDataTypeEditor
                                    width: parent.width
                                    visible: modelData.type === "str"
                                        && modelData.key === "data_type"
                                        && root.isPinInspector
                                    model: root.mainWindowRef ? root.mainWindowRef.pin_data_type_options : []
                                    currentIndex: {
                                        var values = root.mainWindowRef ? (root.mainWindowRef.pin_data_type_options || []) : []
                                        var value = String(modelData.value || "").toLowerCase()
                                        return values.indexOf(value)
                                    }
                                    Component.onCompleted: editText = String(modelData.value || "")
                                    onActivated: {
                                        var values = root.mainWindowRef ? (root.mainWindowRef.pin_data_type_options || []) : []
                                        if (!root.mainWindowRef || currentIndex < 0 || currentIndex >= values.length)
                                            return
                                        root.mainWindowRef.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                    }
                                    onAccepted: {
                                        if (root.mainWindowRef)
                                            root.mainWindowRef.set_selected_node_property(modelData.key, editText)
                                    }
                                    onActiveFocusChanged: {
                                        if (!activeFocus && root.mainWindowRef)
                                            root.mainWindowRef.set_selected_node_property(modelData.key, editText)
                                    }
                                }

                                InspectorTextField {
                                    width: parent.width
                                    visible: modelData.type !== "bool"
                                        && modelData.type !== "enum"
                                        && !(modelData.type === "str"
                                            && modelData.key === "data_type"
                                            && root.isPinInspector)
                                    text: MainShellUtils.toEditorText(modelData)
                                    onAccepted: {
                                        if (root.mainWindowRef)
                                            root.mainWindowRef.set_selected_node_property(modelData.key, text)
                                    }
                                    onEditingFinished: {
                                        if (root.mainWindowRef)
                                            root.mainWindowRef.set_selected_node_property(modelData.key, text)
                                    }
                                }
                            }
                        }
                    }

                    InspectorSectionCard {
                        objectName: "inspectorPortManagementCard"
                        width: inspectorColumn.width
                        visible: root.showPortSection
                        title: "Port Management"

                        InspectorButton {
                            objectName: "inspectorDeletePortButton"
                            width: parent.width
                            visible: root.canManageSubnodePorts
                            destructive: true
                            enabled: root.selectedPortKey.length > 0
                            text: "Delete"
                            tooltipText: "Delete the selected subnode port"
                            onClicked: root.deleteSelectedPort()
                        }

                        Rectangle {
                            objectName: "inspectorPortTabs"
                            width: parent.width
                            height: 44
                            radius: 11
                            color: root.themePalette.input_bg
                            border.color: root.themePalette.input_border
                            border.width: 1

                            Row {
                                anchors.fill: parent
                                anchors.margins: 3
                                spacing: 4

                                InspectorSegmentButton {
                                    objectName: "inspectorInputsTab"
                                    width: (parent.width - 4) / 2
                                    height: parent.height
                                    text: "INPUTS (" + root.inputPortCount + ")"
                                    selectedStyle: root.activePortDirection === "in"
                                    onClicked: root.activePortDirection = "in"
                                }

                                InspectorSegmentButton {
                                    objectName: "inspectorOutputsTab"
                                    width: (parent.width - 4) / 2
                                    height: parent.height
                                    text: "OUTPUTS (" + root.outputPortCount + ")"
                                    selectedStyle: root.activePortDirection === "out"
                                    onClicked: root.activePortDirection = "out"
                                }
                            }
                        }

                        Text {
                            width: parent.width
                            visible: root.visiblePortItems.length === 0
                            wrapMode: Text.WordWrap
                            text: root.activePortDirection === "in"
                                ? "No input ports are available for the current node."
                                : "No output ports are available for the current node."
                            color: root.themePalette.muted_fg
                            font.pixelSize: 10
                        }

                        Column {
                            objectName: "inspectorPortList"
                            width: parent.width
                            spacing: 4

                            Repeater {
                                model: root.visiblePortItems

                                delegate: Rectangle {
                                    width: parent.width
                                    radius: 9
                                    color: root.selectedPortKey === String(modelData.key || "")
                                        ? root.selectedSurfaceColor
                                        : root.themePalette.input_bg
                                    border.color: root.selectedPortKey === String(modelData.key || "")
                                        ? root.selectedOutlineColor
                                        : root.themePalette.input_border
                                    border.width: 1
                                    implicitHeight: 46

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        spacing: 6

                                        InspectorCheckBox {
                                            Layout.alignment: Qt.AlignVCenter
                                            objectName: "inspectorPortExposedToggle"
                                            property string portKey: String(modelData.key || "")
                                            checked: !!modelData.exposed
                                            onClicked: root.selectPort(modelData.key)
                                            onToggled: {
                                                if (root.mainWindowRef)
                                                    root.mainWindowRef.set_selected_port_exposed(modelData.key, checked)
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 0

                                            Item {
                                                Layout.fillWidth: true
                                                implicitHeight: 18

                                                Text {
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    visible: !portLabelEditor.visible
                                                    text: String(modelData.label || modelData.key || "")
                                                    color: root.themePalette.panel_title_fg
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                    elide: Text.ElideRight
                                                }

                                                TextField {
                                                    id: portLabelEditor
                                                    objectName: "inspectorPortLabelEditor"
                                                    property string portKey: String(modelData.key || "")
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    visible: root.canManageSubnodePorts
                                                        && root.editingPortKey === String(modelData.key || "")
                                                    implicitHeight: 24
                                                    leftPadding: 4
                                                    rightPadding: 4
                                                    topPadding: 1
                                                    bottomPadding: 1
                                                    selectByMouse: true
                                                    text: String(modelData.label || modelData.key || "")
                                                    color: root.themePalette.panel_title_fg
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                    background: Rectangle {
                                                        radius: 6
                                                        color: root.themePalette.input_bg
                                                        border.color: root.themePalette.accent
                                                        border.width: 1
                                                    }
                                                    onVisibleChanged: {
                                                        if (visible)
                                                            text = root.editingPortLabel
                                                    }
                                                    onTextChanged: {
                                                        if (visible)
                                                            root.editingPortLabel = text
                                                    }
                                                    onAccepted: root.commitPortLabelEdit(modelData.key, text)
                                                    onEditingFinished: root.commitPortLabelEdit(modelData.key, text)
                                                    onActiveFocusChanged: {
                                                        if (!activeFocus)
                                                            root.commitPortLabelEdit(modelData.key, text)
                                                    }
                                                    Keys.onEscapePressed: {
                                                        text = String(modelData.label || modelData.key || "")
                                                        root.cancelPortLabelEdit(modelData.key)
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    enabled: root.canManageSubnodePorts && !portLabelEditor.visible
                                                    cursorShape: Qt.IBeamCursor
                                                    onClicked: {
                                                        root.beginPortLabelEdit(modelData.key)
                                                        Qt.callLater(function() {
                                                            portLabelEditor.forceActiveFocus()
                                                            portLabelEditor.selectAll()
                                                        })
                                                    }
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(modelData.kind || "") + " / " + String(modelData.data_type || "any")
                                                color: root.themePalette.muted_fg
                                                font.pixelSize: 9
                                                elide: Text.ElideRight
                                            }
                                        }

                                        Rectangle {
                                            visible: !!modelData.required
                                            Layout.alignment: Qt.AlignVCenter
                                            radius: 8
                                            color: root.sectionHeaderColor
                                            border.color: root.themePalette.input_border
                                            border.width: 1
                                            implicitWidth: requiredLabel.implicitWidth + 10
                                            implicitHeight: requiredLabel.implicitHeight + 6

                                            Text {
                                                id: requiredLabel
                                                anchors.centerIn: parent
                                                text: "REQUIRED"
                                                color: root.themePalette.muted_fg
                                                font.pixelSize: 8
                                                font.bold: true
                                                font.letterSpacing: 0.5
                                            }
                                        }
                                    }

                                    TapHandler {
                                        onTapped: root.selectPort(modelData.key)
                                    }
                                }
                            }
                        }

                        InspectorButton {
                            objectName: "inspectorAddPortButton"
                            width: parent.width
                            visible: root.canManageSubnodePorts
                            text: root.activePortDirection === "in" ? "+ Input" : "+ Output"
                            tooltipText: root.activePortDirection === "in"
                                ? "Add an input port to the selected subnode"
                                : "Add an output port to the selected subnode"
                            onClicked: root.addSubnodePort(root.activePortDirection)
                        }
                    }
                }
            }
        }
    ]
}
