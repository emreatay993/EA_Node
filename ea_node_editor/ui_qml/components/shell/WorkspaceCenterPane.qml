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

    function countLabel(items, singularLabel, pluralLabel) {
        var count = items && items.length ? items.length : 0
        return count + " " + (count === 1 ? singularLabel : pluralLabel)
    }

    Layout.fillWidth: true
    Layout.fillHeight: true
    color: themePalette.panel_bg
    border.color: themePalette.border

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    spacing: 12

                    ColumnLayout {
                        spacing: 1

                        Text {
                            text: "WORKSPACE"
                            color: root.themePalette.muted_fg
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1.1
                        }

                        Text {
                            text: root.mainWindowRef.active_workspace_name
                            color: root.themePalette.panel_title_fg
                            font.pixelSize: 18
                            font.bold: true
                            elide: Text.ElideRight
                        }
                    }

                    Item { Layout.fillWidth: true }

                    ColumnLayout {
                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                        spacing: 4

                        Rectangle {
                            id: viewControlsCard
                            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                            implicitWidth: viewControlsRow.implicitWidth + 16
                            implicitHeight: viewControlsRow.implicitHeight + 10
                            radius: 12
                            color: root.themePalette.panel_alt_bg
                            border.color: root.themePalette.border

                            Row {
                                id: viewControlsRow
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                anchors.topMargin: 5
                                anchors.bottomMargin: 5
                                spacing: 6

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "VIEWS"
                                    color: root.themePalette.muted_fg
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.letterSpacing: 1.0
                                }

                                Repeater {
                                    model: root.mainWindowRef.active_view_items
                                    delegate: Rectangle {
                                        id: viewTab
                                        property bool active: !!modelData.active
                                        height: 28
                                        width: Math.max(56, viewTabLabel.implicitWidth + 24)
                                        radius: 9
                                        color: active
                                            ? root.themePalette.tab_selected_bg
                                            : (viewTabMouse.containsMouse
                                                ? root.themePalette.hover
                                                : "transparent")
                                        border.width: active || viewTabMouse.containsMouse ? 1 : 0
                                        border.color: active
                                            ? root.themePalette.accent
                                            : root.themePalette.input_border

                                        Text {
                                            id: viewTabLabel
                                            anchors.centerIn: parent
                                            text: modelData.label
                                            color: active
                                                ? root.themePalette.tab_selected_fg
                                                : root.themePalette.tab_fg
                                            font.pixelSize: 12
                                            font.bold: active
                                        }

                                        MouseArea {
                                            id: viewTabMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.mainWindowRef.request_switch_view(modelData.view_id)
                                        }
                                    }
                                }

                                ShellCreateButton {
                                    text: "New View"
                                    accentOutline: true
                                    onClicked: root.mainWindowRef.request_create_view()
                                }
                            }
                        }

                        Text {
                            Layout.alignment: Qt.AlignRight
                            text: root.countLabel(root.mainWindowRef.active_view_items, "view", "views")
                            color: root.themePalette.muted_fg
                            font.pixelSize: 11
                        }
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
            Layout.preferredHeight: 48
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 10

                Text {
                    Layout.alignment: Qt.AlignVCenter
                    text: "WORKSPACES"
                    color: root.themePalette.muted_fg
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.1
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    implicitHeight: 36
                    radius: 12
                    color: root.themePalette.panel_alt_bg
                    border.color: root.themePalette.border

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        anchors.topMargin: 4
                        anchors.bottomMargin: 4
                        spacing: 6

                        Repeater {
                            model: root.workspaceTabsBridgeRef.tabs
                            delegate: Rectangle {
                                id: workspaceTab
                                property bool active: modelData.workspace_id === root.mainWindowRef.active_workspace_id
                                height: 28
                                width: Math.max(132, workspaceTabLabel.implicitWidth + 28)
                                radius: 9
                                color: active
                                    ? root.themePalette.tab_selected_bg
                                    : (workspaceTabMouse.containsMouse
                                        ? root.themePalette.hover
                                        : "transparent")
                                border.width: active || workspaceTabMouse.containsMouse ? 1 : 0
                                border.color: active
                                    ? root.themePalette.accent
                                    : root.themePalette.input_border

                                Text {
                                    id: workspaceTabLabel
                                    anchors.centerIn: parent
                                    text: modelData.label
                                    color: active
                                        ? root.themePalette.tab_selected_fg
                                        : root.themePalette.tab_fg
                                    font.pixelSize: 12
                                    font.bold: active
                                }

                                MouseArea {
                                    id: workspaceTabMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.workspaceTabsBridgeRef.activate_workspace(modelData.workspace_id)
                                }
                            }
                        }

                        ShellCreateButton {
                            text: "New Workspace"
                            onClicked: root.mainWindowRef.request_create_workspace()
                        }
                    }
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
