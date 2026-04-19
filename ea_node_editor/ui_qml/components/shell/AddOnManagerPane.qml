import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import EA.NodeEditor 1.0

Rectangle {
    id: root
    objectName: "addonManagerPane"
    property var requestBridge: typeof addonManagerBridge !== "undefined" ? addonManagerBridge : null
    property var workspaceBridge: typeof shellWorkspaceBridge !== "undefined" ? shellWorkspaceBridge : null
    property var viewerHostServiceRef: typeof viewerHostService !== "undefined" ? viewerHostService : null
    readonly property var themePalette: themeBridge.palette
    readonly property var selectedAddon: controller.selectedAddon
    color: themePalette.app_bg
    border.color: themePalette.border
    focus: visible

    Keys.onEscapePressed: controller.requestClose()

    function rowAccent(row) {
        if (!row)
            return themePalette.border
        if (row.pendingRestart)
            return themePalette.edge_warning
        if (row.supportsHotApply)
            return themePalette.run_completed
        return themePalette.accent
    }

    function statusText(row) {
        if (!row)
            return ""
        if (row.pendingRestart)
            return "Pending restart"
        if (row.unavailable)
            return "Unavailable"
        return row.enabled ? "Enabled" : "Disabled"
    }

    ShellAddOnManagerBridge {
        id: controller
        objectName: "shellAddOnManagerBridge"
        requestBridge: root.requestBridge
        workspaceBridge: root.workspaceBridge
        viewerHostServiceRef: root.viewerHostServiceRef
    }

    Rectangle {
        id: managerToolbar
        objectName: "addonManagerToolbar"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 54
        color: themePalette.toolbar_bg
        border.color: themePalette.border

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 10

            Rectangle {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                radius: 4
                color: themePalette.node_header_bg
                border.color: themePalette.node_card_border

                Text {
                    anchors.centerIn: parent
                    text: "+"
                    color: themePalette.panel_title_fg
                    font.pixelSize: 13
                    font.bold: true
                }
            }

            Text {
                id: toolbarTitle
                objectName: "addonManagerTitle"
                text: "Manage Add-Ons"
                color: themePalette.panel_title_fg
                font.pixelSize: 14
                font.bold: true
            }

            Text {
                objectName: "addonManagerSummary"
                text: controller.summaryText
                color: themePalette.muted_fg
                font.pixelSize: 11
            }

            Rectangle {
                id: pendingBadge
                objectName: "addonManagerPendingBadge"
                visible: controller.pendingRestartCount > 0
                Layout.preferredHeight: 22
                Layout.preferredWidth: pendingBadgeLabel.implicitWidth + 16
                radius: 11
                color: Qt.alpha(themePalette.edge_warning, 0.16)
                border.color: Qt.alpha(themePalette.edge_warning, 0.55)

                Text {
                    id: pendingBadgeLabel
                    anchors.centerIn: parent
                    text: controller.pendingRestartCount + " pending restart"
                    color: themePalette.edge_warning
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            Item {
                Layout.fillWidth: true
            }

            ShellButton {
                text: "Workflow Settings"
                tooltipText: "Open the temporary plugin fallback in Workflow Settings."
                onClicked: controller.requestOpenWorkflowSettings()
            }

            ShellButton {
                text: "Check for updates"
                enabled: false
            }

            ShellButton {
                text: "Install from File..."
                enabled: false
            }

            ShellButton {
                objectName: "addonManagerCloseButton"
                text: "Close"
                onClicked: controller.requestClose()
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: managerToolbar.bottom
        anchors.bottom: parent.bottom
        color: themePalette.app_bg

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                id: listPane
                Layout.preferredWidth: 340
                Layout.fillHeight: true
                color: themePalette.panel_bg
                border.color: themePalette.border

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        color: themePalette.panel_bg
                        border.color: themePalette.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6

                            Repeater {
                                model: [
                                    { "id": "all", "label": "All" },
                                    { "id": "enabled", "label": "Enabled" },
                                    { "id": "disabled", "label": "Disabled" }
                                ]

                                delegate: ShellButton {
                                    objectName: "addonManagerFilter" + modelData.label + "Button"
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    selectedStyle: controller.statusFilter === modelData.id
                                    onClicked: controller.setStatusFilter(modelData.id)
                                }
                            }
                        }
                    }

                    ScrollView {
                        id: listScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: listScroll.availableWidth
                            spacing: 0

                            Rectangle {
                                objectName: "addonManagerEmptyListState"
                                visible: controller.rowCount === 0
                                width: parent.width
                                height: 120
                                color: "transparent"

                                Column {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "No add-ons registered"
                                        color: themePalette.panel_title_fg
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "This build has not published any add-on contracts yet."
                                        color: themePalette.muted_fg
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Repeater {
                                model: controller.filteredRows

                                delegate: Rectangle {
                                    id: rowCard
                                    objectName: "addonManagerRow"
                                    width: parent.width
                                    height: 66
                                    color: modelData.selected
                                        ? themePalette.inspector_selected_bg
                                        : themePalette.panel_bg
                                    border.color: themePalette.border
                                    border.width: 1

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.bottom: parent.bottom
                                        width: 3
                                        color: modelData.selected
                                            ? themePalette.accent
                                            : root.rowAccent(modelData)
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: controller.selectAddon(String(modelData.addonId || ""))
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        spacing: 10

                                        Rectangle {
                                            Layout.preferredWidth: 26
                                            Layout.preferredHeight: 26
                                            radius: 4
                                            color: themePalette.node_header_bg
                                            border.color: themePalette.node_card_border

                                            Rectangle {
                                                anchors.left: parent.left
                                                anchors.top: parent.top
                                                anchors.bottom: parent.bottom
                                                width: 4
                                                color: root.rowAccent(modelData)
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: "A"
                                                color: themePalette.node_header_fg
                                                font.pixelSize: 11
                                                font.bold: true
                                            }
                                        }

                                        Column {
                                            Layout.fillWidth: true
                                            spacing: 2

                                            Text {
                                                objectName: "addonManagerRowTitle"
                                                width: rowCard.width - 120
                                                text: String(modelData.displayName || "")
                                                color: themePalette.panel_title_fg
                                                font.pixelSize: 12
                                                font.bold: true
                                                elide: Text.ElideRight
                                            }

                                            Row {
                                                spacing: 6

                                                Text {
                                                    text: String(modelData.vendor || "")
                                                        + (String(modelData.version || "").length > 0
                                                            ? " - v" + String(modelData.version || "")
                                                            : "")
                                                    color: themePalette.muted_fg
                                                    font.pixelSize: 10
                                                    elide: Text.ElideRight
                                                }

                                                Text {
                                                    text: root.statusText(modelData)
                                                    color: modelData.pendingRestart
                                                        ? themePalette.edge_warning
                                                        : (modelData.enabled
                                                            ? themePalette.run_completed
                                                            : themePalette.muted_fg)
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }
                                            }
                                        }

                                        Switch {
                                            id: rowToggle
                                            objectName: "addonManagerRowToggle"
                                            enabled: !modelData.unavailable
                                            checked: Boolean(modelData.enabled)
                                            onToggled: controller.setAddonEnabled(
                                                String(modelData.addonId || ""),
                                                checked
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: detailPane
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: themePalette.app_bg
                border.color: themePalette.border

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        id: detailHeader
                        Layout.fillWidth: true
                        Layout.preferredHeight: selectedStateColumn.implicitHeight + 28
                        color: themePalette.panel_bg
                        border.color: themePalette.border

                        ColumnLayout {
                            id: selectedStateColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Item {
                                Layout.fillWidth: true
                                Layout.preferredHeight: controller.hasSelection ? headerRow.implicitHeight : emptyHeader.implicitHeight

                                RowLayout {
                                    id: headerRow
                                    anchors.fill: parent
                                    spacing: 12
                                    visible: controller.hasSelection

                                    Rectangle {
                                        Layout.preferredWidth: 42
                                        Layout.preferredHeight: 42
                                        radius: 6
                                        color: themePalette.node_header_bg
                                        border.color: themePalette.node_card_border

                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.top: parent.top
                                            anchors.bottom: parent.bottom
                                            width: 4
                                            color: selectedAddon.pendingRestart
                                                ? themePalette.edge_warning
                                                : (selectedAddon.supportsHotApply
                                                    ? themePalette.run_completed
                                                    : themePalette.accent)
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            text: "A"
                                            color: themePalette.node_header_fg
                                            font.pixelSize: 18
                                            font.bold: true
                                        }
                                    }

                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 3

                                        Row {
                                            spacing: 8

                                            Text {
                                                objectName: "addonManagerDetailTitle"
                                                text: String(selectedAddon.displayName || "")
                                                color: themePalette.panel_title_fg
                                                font.pixelSize: 18
                                                font.bold: true
                                            }

                                            Text {
                                                text: String(selectedAddon.version || "").length > 0
                                                    ? "v" + String(selectedAddon.version || "")
                                                    : ""
                                                color: themePalette.muted_fg
                                                font.pixelSize: 11
                                            }
                                        }

                                        Row {
                                            spacing: 8

                                            Rectangle {
                                                visible: controller.hasSelection
                                                height: 20
                                                width: policyLabel.implicitWidth + 12
                                                radius: 3
                                                color: selectedAddon.supportsHotApply
                                                    ? Qt.alpha(themePalette.run_completed, 0.14)
                                                    : Qt.alpha(themePalette.edge_warning, 0.14)
                                                border.color: selectedAddon.supportsHotApply
                                                    ? Qt.alpha(themePalette.run_completed, 0.38)
                                                    : Qt.alpha(themePalette.edge_warning, 0.38)

                                                Text {
                                                    id: policyLabel
                                                    anchors.centerIn: parent
                                                    text: String(selectedAddon.policyLabel || "")
                                                    color: selectedAddon.supportsHotApply
                                                        ? themePalette.run_completed
                                                        : themePalette.edge_warning
                                                    font.pixelSize: 9
                                                    font.bold: true
                                                }
                                            }

                                            Rectangle {
                                                visible: Boolean(selectedAddon.pendingRestart)
                                                height: 20
                                                width: restartLabel.implicitWidth + 12
                                                radius: 3
                                                color: Qt.alpha(themePalette.edge_warning, 0.14)
                                                border.color: Qt.alpha(themePalette.edge_warning, 0.38)

                                                Text {
                                                    id: restartLabel
                                                    anchors.centerIn: parent
                                                    text: "PENDING RESTART"
                                                    color: themePalette.edge_warning
                                                    font.pixelSize: 9
                                                    font.bold: true
                                                }
                                            }
                                        }

                                        Text {
                                            text: String(selectedAddon.vendor || "")
                                                + (String(selectedAddon.addonId || "").length > 0
                                                    ? " - " + String(selectedAddon.addonId || "")
                                                    : "")
                                            color: themePalette.muted_fg
                                            font.pixelSize: 11
                                        }
                                    }

                                    RowLayout {
                                        spacing: 6

                                        ShellButton {
                                            text: "Preferences..."
                                            enabled: controller.hasSelection
                                            onClicked: controller.requestOpenWorkflowSettings()
                                        }

                                        ShellButton {
                                            objectName: "addonManagerPrimaryToggleButton"
                                            text: Boolean(selectedAddon.enabled) ? "Disable" : "Enable"
                                            selectedStyle: !Boolean(selectedAddon.enabled)
                                            enabled: controller.hasSelection && !Boolean(selectedAddon.unavailable)
                                            onClicked: controller.toggleSelectedAddon()
                                        }
                                    }
                                }

                                Text {
                                    id: emptyHeader
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: !controller.hasSelection
                                    text: "No add-on selected"
                                    color: themePalette.panel_title_fg
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                            }

                            Rectangle {
                                objectName: "addonManagerPendingBanner"
                                visible: Boolean(selectedAddon.pendingRestart)
                                Layout.fillWidth: true
                                Layout.preferredHeight: pendingBannerText.implicitHeight + 18
                                radius: 4
                                color: Qt.alpha(themePalette.edge_warning, 0.10)
                                border.color: Qt.alpha(themePalette.edge_warning, 0.35)

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 10

                                    Text {
                                        text: "!"
                                        color: themePalette.edge_warning
                                        font.pixelSize: 14
                                        font.bold: true
                                    }

                                    Text {
                                        id: pendingBannerText
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: "Pending change. Restart COREX to apply this add-on state."
                                        color: themePalette.app_fg
                                        font.pixelSize: 11
                                    }

                                    ShellButton {
                                        text: "Restart Required"
                                        enabled: false
                                    }
                                }
                            }

                            Rectangle {
                                objectName: "addonManagerErrorBanner"
                                visible: controller.lastError.length > 0
                                Layout.fillWidth: true
                                Layout.preferredHeight: errorBannerText.implicitHeight + 18
                                radius: 4
                                color: Qt.alpha(themePalette.inspector_danger_bg, 0.9)
                                border.color: themePalette.inspector_danger_border

                                Text {
                                    id: errorBannerText
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    wrapMode: Text.WordWrap
                                    text: controller.lastError
                                    color: themePalette.inspector_danger_fg
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        color: themePalette.panel_bg
                        border.color: themePalette.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            spacing: 0

                            Repeater {
                                model: [
                                    { "id": "about", "label": "About" },
                                    { "id": "dependencies", "label": "Dependencies" },
                                    { "id": "nodes", "label": "Nodes" },
                                    { "id": "changelog", "label": "Changelog" }
                                ]

                                delegate: Rectangle {
                                    objectName: "addonManagerTab" + modelData.label
                                    Layout.preferredWidth: tabLabel.implicitWidth + 28
                                    Layout.fillHeight: true
                                    color: "transparent"
                                    border.color: "transparent"

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: 2
                                        color: controller.activeTab === modelData.id
                                            ? themePalette.accent
                                            : "transparent"
                                    }

                                    Text {
                                        id: tabLabel
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        color: controller.activeTab === modelData.id
                                            ? themePalette.panel_title_fg
                                            : themePalette.muted_fg
                                        font.pixelSize: 11
                                        font.bold: controller.activeTab === modelData.id
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: controller.hasSelection
                                        onClicked: controller.setActiveTab(modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    ScrollView {
                        id: detailScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: detailScroll.availableWidth
                            spacing: 14
                            padding: 20

                            Rectangle {
                                objectName: "addonManagerDetailEmptyState"
                                visible: !controller.hasSelection
                                width: parent.width
                                height: 120
                                radius: 6
                                color: themePalette.inspector_card_bg
                                border.color: themePalette.border

                                Column {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "Select an add-on to inspect it."
                                        color: themePalette.panel_title_fg
                                        font.pixelSize: 13
                                        font.bold: true
                                    }

                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "About, dependencies, node registrations, and restart state appear here."
                                        color: themePalette.muted_fg
                                        font.pixelSize: 11
                                    }
                                }
                            }

                            Column {
                                visible: controller.hasSelection && controller.activeTab === "about"
                                width: parent.width
                                spacing: 14

                                Text {
                                    width: parent.width
                                    text: String(selectedAddon.details || selectedAddon.summary || "")
                                    wrapMode: Text.WordWrap
                                    color: themePalette.app_fg
                                    font.pixelSize: 12
                                }

                                GridLayout {
                                    columns: 4
                                    rowSpacing: 10
                                    columnSpacing: 10
                                    width: parent.width

                                    Repeater {
                                        model: [
                                            { "label": "Activation", "value": String(selectedAddon.policyLabel || "") },
                                            { "label": "Status", "value": String(selectedAddon.statusLabel || "") },
                                            { "label": "Nodes", "value": String(selectedAddon.nodeCount || 0) },
                                            { "label": "Dependencies", "value": String((selectedAddon.dependencyItems || []).length) }
                                        ]

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 76
                                            radius: 6
                                            color: themePalette.inspector_card_bg
                                            border.color: themePalette.border

                                            Column {
                                                anchors.fill: parent
                                                anchors.margins: 10
                                                spacing: 6

                                                Text {
                                                    text: String(modelData.label || "")
                                                    color: themePalette.muted_fg
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }

                                                Text {
                                                    text: String(modelData.value || "")
                                                    color: themePalette.app_fg
                                                    font.pixelSize: 12
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    width: parent.width
                                    radius: 6
                                    color: themePalette.inspector_card_bg
                                    border.color: themePalette.border

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 8

                                        Text {
                                            text: "Availability"
                                            color: themePalette.muted_fg
                                            font.pixelSize: 10
                                            font.bold: true
                                        }

                                        Text {
                                            width: parent.width
                                            wrapMode: Text.WordWrap
                                            text: String(selectedAddon.availabilitySummary || "")
                                            color: themePalette.app_fg
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }

                            Column {
                                visible: controller.hasSelection && controller.activeTab === "dependencies"
                                width: parent.width
                                spacing: 10

                                Repeater {
                                    model: (selectedAddon.dependencyItems || []).length > 0
                                        ? selectedAddon.dependencyItems
                                        : [""]

                                    delegate: Rectangle {
                                        visible: (selectedAddon.dependencyItems || []).length > 0
                                        width: parent.width
                                        height: 38
                                        radius: 4
                                        color: themePalette.inspector_card_bg
                                        border.color: themePalette.border

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 8

                                            Rectangle {
                                                Layout.preferredWidth: 6
                                                Layout.preferredHeight: 6
                                                radius: 3
                                                color: themePalette.run_completed
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(modelData || "")
                                                color: themePalette.app_fg
                                                font.pixelSize: 12
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    visible: (selectedAddon.dependencyItems || []).length === 0
                                    width: parent.width
                                    height: 70
                                    radius: 6
                                    color: themePalette.inspector_card_bg
                                    border.color: themePalette.border

                                    Text {
                                        anchors.centerIn: parent
                                        text: "No external dependencies declared."
                                        color: themePalette.muted_fg
                                        font.pixelSize: 12
                                    }
                                }

                                Rectangle {
                                    visible: (selectedAddon.missingDependencies || []).length > 0
                                    width: parent.width
                                    radius: 6
                                    color: Qt.alpha(themePalette.edge_warning, 0.10)
                                    border.color: Qt.alpha(themePalette.edge_warning, 0.35)

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 6

                                        Text {
                                            text: "Missing dependencies"
                                            color: themePalette.edge_warning
                                            font.pixelSize: 10
                                            font.bold: true
                                        }

                                        Text {
                                            width: parent.width
                                            wrapMode: Text.WordWrap
                                            text: (selectedAddon.missingDependencies || []).join(", ")
                                            color: themePalette.app_fg
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }

                            Column {
                                visible: controller.hasSelection && controller.activeTab === "nodes"
                                width: parent.width
                                spacing: 8

                                Repeater {
                                    model: (selectedAddon.providedNodeTypeIds || []).length > 0
                                        ? selectedAddon.providedNodeTypeIds
                                        : [""]

                                    delegate: Rectangle {
                                        visible: (selectedAddon.providedNodeTypeIds || []).length > 0
                                        width: parent.width
                                        height: 36
                                        radius: 4
                                        color: index % 2 === 0 ? themePalette.panel_bg : themePalette.panel_alt_bg
                                        border.color: themePalette.border

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 10

                                            Text {
                                                text: String(modelData || "")
                                                color: themePalette.app_fg
                                                font.pixelSize: 11
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    visible: (selectedAddon.providedNodeTypeIds || []).length === 0
                                    width: parent.width
                                    height: 70
                                    radius: 6
                                    color: themePalette.inspector_card_bg
                                    border.color: themePalette.border

                                    Text {
                                        anchors.centerIn: parent
                                        text: "This add-on does not currently publish node descriptors."
                                        color: themePalette.muted_fg
                                        font.pixelSize: 12
                                    }
                                }
                            }

                            Rectangle {
                                visible: controller.hasSelection && controller.activeTab === "changelog"
                                width: parent.width
                                height: 100
                                radius: 6
                                color: themePalette.inspector_card_bg
                                border.color: themePalette.border

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 6

                                    Text {
                                        text: String(selectedAddon.version || "").length > 0
                                            ? "Current version: v" + String(selectedAddon.version || "")
                                            : "Current version"
                                        color: themePalette.panel_title_fg
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    Text {
                                        width: parent.width
                                        wrapMode: Text.WordWrap
                                        text: "This build does not publish per-add-on changelog entries yet."
                                        color: themePalette.muted_fg
                                        font.pixelSize: 11
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
