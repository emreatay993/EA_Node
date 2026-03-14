import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".." as Components

Rectangle {
    id: root
    property var mainWindowRef
    property var sceneBridgeRef
    property var viewBridgeRef
    property var workspaceTabsBridgeRef
    property var consoleBridgeRef
    property var overlayHostItem
    property alias graphCanvasRef: graphCanvas
    readonly property var themePalette: themeBridge.palette
    readonly property string tabStripDensityPreset: mainWindowRef
        ? String(mainWindowRef.graphics_tab_strip_density || "compact")
        : "compact"
    readonly property bool compactTabStripDensity: root.tabStripDensityPreset === "compact"

    Layout.fillWidth: true
    Layout.fillHeight: true
    color: themePalette.panel_bg
    border.color: themePalette.border

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.compactTabStripDensity ? 34 : 44
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 12

                Row {
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2

                    Text {
                        text: "Scope:"
                        color: root.themePalette.muted_fg
                        font.pixelSize: 11
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Repeater {
                        model: root.mainWindowRef.active_scope_breadcrumb_items
                        delegate: Row {
                            spacing: 2

                            Text {
                                visible: index > 0
                                text: "›"
                                color: root.themePalette.muted_fg
                                font.pixelSize: 11
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            ShellButton {
                                text: String(modelData.label || "")
                                implicitHeight: 22
                                selectedStyle: index === root.mainWindowRef.active_scope_breadcrumb_items.length - 1
                                onClicked: root.mainWindowRef.request_open_scope_breadcrumb(
                                    String(modelData.node_id || "")
                                )
                            }
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                ShellLabeledTabStrip {
                    id: viewControlsStrip
                    objectName: "viewControlsStrip"
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    densityPreset: root.tabStripDensityPreset
                    titleText: "VIEWS"
                    model: root.mainWindowRef.active_view_items
                    minTabWidth: 56
                    tabHorizontalPadding: 24
                    createButtonText: "New View"
                    createButtonAccentOutline: true
                    isTabActive: function(itemData) {
                        return !!itemData.active
                    }
                    onTabActivated: function(itemData) {
                        root.mainWindowRef.request_switch_view(itemData.view_id)
                    }
                    onCreateActivated: root.mainWindowRef.request_create_view()
                }
            }
        }

        Components.GraphCanvas {
            id: graphCanvas
            Layout.fillWidth: true
            Layout.fillHeight: true
            mainWindowBridge: root.mainWindowRef
            sceneBridge: root.sceneBridgeRef
            viewBridge: root.viewBridgeRef
            overlayHostItem: root.overlayHostItem
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.compactTabStripDensity ? 36 : 48
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 10

                ShellLabeledTabStrip {
                    id: workspaceControlsStrip
                    objectName: "workspaceControlsStrip"
                    Layout.alignment: Qt.AlignVCenter
                    densityPreset: root.tabStripDensityPreset
                    titleText: "WORKSPACES"
                    model: root.workspaceTabsBridgeRef.tabs
                    minTabWidth: 132
                    tabHorizontalPadding: 28
                    createButtonText: "New Workspace"
                    isTabActive: function(itemData) {
                        return itemData.workspace_id === root.mainWindowRef.active_workspace_id
                    }
                    onTabActivated: function(itemData) {
                        root.workspaceTabsBridgeRef.activate_workspace(itemData.workspace_id)
                    }
                    onCreateActivated: root.mainWindowRef.request_create_workspace()
                }

                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 170
            color: root.themePalette.panel_bg
            border.color: root.themePalette.border

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    color: root.themePalette.toolbar_bg

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
                            text: "Errors (" + root.consoleBridgeRef.error_count_value + ")"
                            selectedStyle: consoleTabs.currentIndex === 1
                            onClicked: consoleTabs.currentIndex = 1
                        }
                        ShellButton {
                            text: "Warnings (" + root.consoleBridgeRef.warning_count_value + ")"
                            selectedStyle: consoleTabs.currentIndex === 2
                            onClicked: consoleTabs.currentIndex = 2
                        }
                        Item { Layout.fillWidth: true }
                        ShellButton {
                            text: "Clear"
                            onClicked: root.consoleBridgeRef.clear_all()
                        }
                    }
                }

                StackLayout {
                    id: consoleTabs
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TextArea {
                        readOnly: true
                        text: root.consoleBridgeRef.output_text
                        color: root.themePalette.app_fg
                        font.family: "Consolas"
                        font.pixelSize: 12
                        wrapMode: TextArea.NoWrap
                        background: Rectangle { color: root.themePalette.console_bg }
                    }
                    TextArea {
                        readOnly: true
                        text: root.consoleBridgeRef.errors_text
                        color: "#F7A1A1"
                        font.family: "Consolas"
                        font.pixelSize: 12
                        wrapMode: TextArea.NoWrap
                        background: Rectangle { color: root.themePalette.console_bg }
                    }
                    TextArea {
                        readOnly: true
                        text: root.consoleBridgeRef.warnings_text
                        color: "#E6D28D"
                        font.family: "Consolas"
                        font.pixelSize: 12
                        wrapMode: TextArea.NoWrap
                        background: Rectangle { color: root.themePalette.console_bg }
                    }
                }
            }
        }
    }
}
