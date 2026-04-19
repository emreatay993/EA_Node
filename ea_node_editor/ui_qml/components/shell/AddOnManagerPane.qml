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
    border.width: 1
    radius: 6
    clip: true
    focus: visible

    Keys.onEscapePressed: controller.requestClose()

    function categoryAccent(categoryKey) {
        if (categoryKey === "dpf")
            return themePalette.accent
        if (categoryKey === "core")
            return themePalette.accent_strong
        if (categoryKey === "io")
            return themePalette.run_completed
        if (categoryKey === "logic")
            return themePalette.node_card_border
        if (categoryKey === "physics")
            return themePalette.edge_warning
        return themePalette.border
    }

    function rowAccent(row) {
        if (!row)
            return themePalette.border
        if (row.pendingRestart)
            return themePalette.edge_warning
        return categoryAccent(String(row.categoryKey || ""))
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

    function badgeFill(tone) {
        if (tone === "warn")
            return Qt.alpha(themePalette.edge_warning, 0.14)
        if (tone === "core")
            return Qt.alpha(themePalette.accent, 0.14)
        return Qt.alpha(themePalette.run_completed, 0.14)
    }

    function badgeBorder(tone) {
        if (tone === "warn")
            return Qt.alpha(themePalette.edge_warning, 0.38)
        if (tone === "core")
            return Qt.alpha(themePalette.accent, 0.38)
        return Qt.alpha(themePalette.run_completed, 0.38)
    }

    function badgeForeground(tone) {
        if (tone === "warn")
            return themePalette.edge_warning
        if (tone === "core")
            return themePalette.accent
        return themePalette.run_completed
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
                    text: "C"
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
                objectName: "addonManagerCheckUpdatesButton"
                text: "Check for updates"
                enabled: false
            }

            ShellButton {
                objectName: "addonManagerInstallFromFileButton"
                text: "Install from File..."
                enabled: false
            }

            ShellButton {
                objectName: "addonManagerRestartRuntimeButton"
                visible: controller.pendingRestartCount > 0
                text: "Restart Runtime"
                enabled: false
                selectedStyle: visible
                tooltipText: "Runtime restart wiring is not exposed on this surface yet."
            }

            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 18
                color: themePalette.border
                visible: fallbackWorkflowSettingsButton.visible
            }

            ShellButton {
                id: fallbackWorkflowSettingsButton
                objectName: "addonManagerFallbackWorkflowSettingsButton"
                text: "Workflow Settings"
                opacity: 0.82
                tooltipText: "Temporary fallback while add-on-specific settings still live under Workflow Settings."
                onClicked: controller.requestOpenWorkflowSettings()
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
                                    height: 84
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
                                            Layout.preferredWidth: 28
                                            Layout.preferredHeight: 28
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
                                                text: String(modelData.iconGlyph || "A")
                                                color: themePalette.node_header_fg
                                                font.pixelSize: 11
                                                font.bold: true
                                            }
                                        }

                                        Column {
                                            Layout.fillWidth: true
                                            spacing: 4

                                            Row {
                                                spacing: 6

                                                Text {
                                                    objectName: "addonManagerRowTitle"
                                                    width: rowCard.width - 190
                                                    text: String(modelData.displayName || "")
                                                    color: themePalette.panel_title_fg
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    elide: Text.ElideRight
                                                }

                                                Repeater {
                                                    model: modelData.stateBadges || []

                                                    delegate: Rectangle {
                                                        height: 16
                                                        width: badgeText.implicitWidth + 10
                                                        radius: 3
                                                        color: root.badgeFill(String(modelData.tone || "core"))
                                                        border.color: root.badgeBorder(String(modelData.tone || "core"))

                                                        Text {
                                                            id: badgeText
                                                            anchors.centerIn: parent
                                                            text: String(modelData.label || "")
                                                            color: root.badgeForeground(String(modelData.tone || "core"))
                                                            font.pixelSize: 8
                                                            font.bold: true
                                                        }
                                                    }
                                                }
                                            }

                                            Text {
                                                width: rowCard.width - 156
                                                text: String(modelData.summary || modelData.details || "")
                                                color: themePalette.app_fg
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }

                                            Row {
                                                spacing: 8

                                                Text {
                                                    text: String(modelData.categoryLabel || "")
                                                        + (String(modelData.version || "").length > 0
                                                            ? " - v" + String(modelData.version || "")
                                                            : "")
                                                    color: themePalette.muted_fg
                                                    font.pixelSize: 10
                                                    elide: Text.ElideRight
                                                }

                                                Text {
                                                    text: String(modelData.nodeCount || 0) + " nodes"
                                                    color: themePalette.muted_fg
                                                    font.pixelSize: 10
                                                }

                                                Rectangle {
                                                    height: 16
                                                    width: policyBadgeText.implicitWidth + 10
                                                    radius: 3
                                                    color: modelData.supportsHotApply
                                                        ? Qt.alpha(themePalette.run_completed, 0.14)
                                                        : Qt.alpha(themePalette.edge_warning, 0.14)
                                                    border.color: modelData.supportsHotApply
                                                        ? Qt.alpha(themePalette.run_completed, 0.38)
                                                        : Qt.alpha(themePalette.edge_warning, 0.38)

                                                    Text {
                                                        id: policyBadgeText
                                                        anchors.centerIn: parent
                                                        text: String(modelData.policyBadgeLabel || "")
                                                        color: modelData.supportsHotApply
                                                            ? themePalette.run_completed
                                                            : themePalette.edge_warning
                                                        font.pixelSize: 8
                                                        font.bold: true
                                                    }
                                                }
                                            }
                                        }

                                        Column {
                                            spacing: 6

                                            Text {
                                                text: root.statusText(modelData)
                                                color: modelData.pendingRestart
                                                    ? themePalette.edge_warning
                                                    : (modelData.enabled
                                                        ? themePalette.run_completed
                                                        : themePalette.muted_fg)
                                                font.pixelSize: 10
                                                font.bold: true
                                                horizontalAlignment: Text.AlignRight
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
                                            text: String(selectedAddon.iconGlyph || "A")
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

                                            Repeater {
                                                model: selectedAddon.statusBadges || []

                                                delegate: Rectangle {
                                                    height: 18
                                                    width: detailBadgeText.implicitWidth + 10
                                                    radius: 3
                                                    color: root.badgeFill(String(modelData.tone || "core"))
                                                    border.color: root.badgeBorder(String(modelData.tone || "core"))

                                                    Text {
                                                        id: detailBadgeText
                                                        anchors.centerIn: parent
                                                        text: String(modelData.label || "")
                                                        color: root.badgeForeground(String(modelData.tone || "core"))
                                                        font.pixelSize: 8
                                                        font.bold: true
                                                    }
                                                }
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
                                                    text: String(selectedAddon.policyBadgeLabel || "")
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
                                                + (String(selectedAddon.categoryLabel || "").length > 0
                                                    ? " - " + String(selectedAddon.categoryLabel || "")
                                                    : "")
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
                                        text: "Restart now"
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
                                    columns: 5
                                    rowSpacing: 10
                                    columnSpacing: 10
                                    width: parent.width

                                    Repeater {
                                        model: selectedAddon.aboutFacts || []

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 76
                                            radius: 6
                                            color: themePalette.inspector_card_bg
                                            border.color: String(modelData.label || "") === "Activation"
                                                ? root.rowAccent(selectedAddon)
                                                : themePalette.border

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
                                            text: "Python requirement"
                                            color: themePalette.muted_fg
                                            font.pixelSize: 10
                                            font.bold: true
                                        }

                                        Text {
                                            width: parent.width
                                            wrapMode: Text.WordWrap
                                            text: String(selectedAddon.pythonRequirement || "")
                                            color: themePalette.app_fg
                                            font.pixelSize: 12
                                            font.family: "Consolas"
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
                                            text: "Runtime facts"
                                            color: themePalette.muted_fg
                                            font.pixelSize: 10
                                            font.bold: true
                                        }

                                        Text {
                                            width: parent.width
                                            wrapMode: Text.WordWrap
                                            text: String(selectedAddon.policyCopy || "")
                                            color: themePalette.app_fg
                                            font.pixelSize: 12
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
                                        height: 42
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
                                                color: Boolean(modelData.satisfied)
                                                    ? themePalette.run_completed
                                                    : themePalette.edge_warning
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(modelData.name || "")
                                                color: themePalette.app_fg
                                                font.pixelSize: 12
                                            }

                                            Text {
                                                text: String(modelData.statusLabel || "")
                                                color: Boolean(modelData.satisfied)
                                                    ? themePalette.muted_fg
                                                    : themePalette.edge_warning
                                                font.pixelSize: 10
                                                font.family: "Consolas"
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
                                    width: parent.width
                                    radius: 6
                                    color: themePalette.inspector_card_bg
                                    border.color: themePalette.border

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 6

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

                                Text {
                                    visible: (selectedAddon.nodeItems || []).length > 0
                                    text: "Showing " + String(Math.min((selectedAddon.nodeItems || []).length, selectedAddon.nodeCount || 0))
                                        + " of " + String(selectedAddon.nodeCount || 0)
                                        + " descriptors registered by this add-on."
                                    color: themePalette.muted_fg
                                    font.pixelSize: 11
                                }

                                Repeater {
                                    model: (selectedAddon.nodeItems || []).length > 0
                                        ? selectedAddon.nodeItems
                                        : [""]

                                    delegate: Rectangle {
                                        visible: (selectedAddon.nodeItems || []).length > 0
                                        width: parent.width
                                        height: 44
                                        radius: 4
                                        color: index % 2 === 0 ? themePalette.panel_bg : themePalette.panel_alt_bg
                                        border.color: themePalette.border

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 10

                                            Rectangle {
                                                Layout.preferredWidth: 22
                                                Layout.preferredHeight: 22
                                                radius: 4
                                                color: themePalette.node_header_bg
                                                border.color: themePalette.node_card_border

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: String(modelData.displayName || "").length > 0
                                                        ? String(modelData.displayName || "").slice(0, 1).toUpperCase()
                                                        : "N"
                                                    color: themePalette.node_header_fg
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }
                                            }

                                            Column {
                                                Layout.fillWidth: true
                                                spacing: 2

                                                Text {
                                                    text: String(modelData.displayName || "")
                                                    color: themePalette.app_fg
                                                    font.pixelSize: 11
                                                }

                                                Text {
                                                    text: String(modelData.category || "")
                                                        + (String(modelData.runtimeBehavior || "").length > 0
                                                            ? " - " + String(modelData.runtimeBehavior || "")
                                                            : "")
                                                    color: themePalette.muted_fg
                                                    font.pixelSize: 10
                                                }
                                            }

                                            Text {
                                                text: String(modelData.typeId || "")
                                                color: themePalette.muted_fg
                                                font.pixelSize: 10
                                                font.family: "Consolas"
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    visible: (selectedAddon.nodeItems || []).length === 0
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

                            Column {
                                visible: controller.hasSelection && controller.activeTab === "changelog"
                                width: parent.width
                                spacing: 10

                                Repeater {
                                    model: selectedAddon.changelogEntries || []

                                    delegate: Rectangle {
                                        width: parent.width
                                        radius: 6
                                        color: themePalette.inspector_card_bg
                                        border.color: themePalette.border

                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 6

                                            Row {
                                                spacing: 8

                                                Text {
                                                    text: String(modelData.versionLabel || "")
                                                    color: themePalette.accent
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    font.family: "Consolas"
                                                }

                                                Text {
                                                    text: String(modelData.dateLabel || "")
                                                    color: themePalette.muted_fg
                                                    font.pixelSize: 11
                                                }
                                            }

                                            Text {
                                                text: String(modelData.title || "")
                                                color: themePalette.panel_title_fg
                                                font.pixelSize: 12
                                                font.bold: true
                                            }

                                            Repeater {
                                                model: modelData.bullets || []

                                                delegate: Row {
                                                    width: parent.width
                                                    spacing: 8

                                                    Text {
                                                        text: "-"
                                                        color: themePalette.muted_fg
                                                        font.pixelSize: 11
                                                    }

                                                    Text {
                                                        width: detailScroll.availableWidth - 90
                                                        wrapMode: Text.WordWrap
                                                        text: String(modelData || "")
                                                        color: themePalette.app_fg
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
            }
        }
    }
}
