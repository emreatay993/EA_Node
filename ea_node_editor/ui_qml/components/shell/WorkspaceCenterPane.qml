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

    Layout.fillWidth: true
    Layout.fillHeight: true
    color: themePalette.panel_bg
    border.color: themePalette.border

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

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
                        text: "Workspace: " + root.mainWindowRef.active_workspace_name
                        color: root.themePalette.panel_title_fg
                        font.pixelSize: 12
                        font.bold: true
                    }

                    Item { Layout.fillWidth: true }

                    Row {
                        spacing: 4
                        Repeater {
                            model: root.mainWindowRef.active_view_items
                            delegate: ShellButton {
                                text: modelData.label
                                selectedStyle: !!modelData.active
                                onClicked: root.mainWindowRef.request_switch_view(modelData.view_id)
                            }
                        }
                    }
                    ShellButton {
                        text: "+ View"
                        onClicked: root.mainWindowRef.request_create_view()
                    }

                    Text {
                        text: root.mainWindowRef.active_view_name
                            ? ("Active: " + root.mainWindowRef.active_view_name)
                            : ""
                        color: root.themePalette.muted_fg
                        font.pixelSize: 11
                    }
                }

                Row {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 24
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
            Layout.preferredHeight: 32
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

            Row {
                anchors.fill: parent
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                spacing: 4

                Repeater {
                    model: root.workspaceTabsBridgeRef.tabs
                    delegate: Rectangle {
                        height: 24
                        width: Math.max(120, tabText.implicitWidth + 24)
                        y: 4
                        radius: 4
                        color: modelData.workspace_id === root.mainWindowRef.active_workspace_id
                            ? root.themePalette.tab_selected_bg
                            : root.themePalette.tab_bg
                        border.color: modelData.workspace_id === root.mainWindowRef.active_workspace_id
                            ? root.themePalette.accent
                            : root.themePalette.border

                        Text {
                            id: tabText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: modelData.workspace_id === root.mainWindowRef.active_workspace_id
                                ? root.themePalette.tab_selected_fg
                                : root.themePalette.tab_fg
                            font.pixelSize: 12
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.workspaceTabsBridgeRef.activate_workspace(modelData.workspace_id)
                        }
                    }
                }
                ShellButton {
                    y: 4
                    text: "+ Workspace"
                    onClicked: root.mainWindowRef.request_create_workspace()
                }
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
