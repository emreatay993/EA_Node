import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".." as Components

Rectangle {
    id: root
    property var workspaceBridgeRef: typeof shellWorkspaceBridge !== "undefined" ? shellWorkspaceBridge : null
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    property var graphActionBridgeRef
    property var graphCanvasStateBridgeRef
    property var graphCanvasCommandBridgeRef
    property var overlayHostItem
    property var uiIconsRef: typeof uiIcons !== "undefined" ? uiIcons : null
    property alias graphCanvasRef: graphCanvas
    readonly property var themePalette: root.themeBridgeRef ? root.themeBridgeRef.palette : ({})
    readonly property string tabStripDensityPreset: String(root.workspaceBridgeRef.graphics_tab_strip_density || "compact")
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
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 10

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
                        model: root.workspaceBridgeRef.active_scope_breadcrumb_items
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
                                themeBridgeRef: root.themeBridgeRef
                                graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                                uiIconsRef: root.uiIconsRef
                                text: String(modelData.label || "")
                                implicitHeight: 22
                                selectedStyle: index === root.workspaceBridgeRef.active_scope_breadcrumb_items.length - 1
                                onClicked: root.workspaceBridgeRef.request_open_scope_breadcrumb(
                                    String(modelData.node_id || "")
                                )
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    implicitHeight: viewControlsStrip.implicitHeight

                    ShellLabeledTabStrip {
                        id: viewControlsStrip
                        objectName: "viewControlsStrip"
                        themeBridgeRef: root.themeBridgeRef
                        graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                        uiIconsRef: root.uiIconsRef
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width)
                        densityPreset: root.tabStripDensityPreset
                        titleText: "VIEWS"
                        model: root.workspaceBridgeRef.active_view_items
                        minTabWidth: 56
                        tabHorizontalPadding: 20
                        contextMenuActions: [
                            { "actionId": "rename", "text": "Rename View" },
                            { "actionId": "delete", "text": "Delete View", "destructive": true }
                        ]
                        createButtonText: "New View"
                        createButtonAccentOutline: true
                        isTabActive: function(itemData) {
                            return !!itemData.active
                        }
                        onTabActivated: function(itemData) {
                            root.workspaceBridgeRef.request_switch_view(itemData.view_id)
                        }
                        onTabMoveRequested: function(fromIndex, toIndex, _itemData) {
                            root.workspaceBridgeRef.request_move_view_tab(fromIndex, toIndex)
                        }
                        onContextMenuActionRequested: function(actionId, itemData) {
                            if (actionId === "rename") {
                                root.workspaceBridgeRef.request_rename_view(String(itemData.view_id || ""))
                                return
                            }
                            if (actionId === "delete")
                                root.workspaceBridgeRef.request_close_view(String(itemData.view_id || ""))
                        }
                        onCreateActivated: root.workspaceBridgeRef.request_create_view()
                    }
                }
            }
        }

        Components.GraphCanvas {
            id: graphCanvas
            Layout.fillWidth: true
            Layout.fillHeight: true
            graphActionBridge: root.graphActionBridgeRef
            canvasStateBridge: root.graphCanvasStateBridgeRef
            canvasCommandBridge: root.graphCanvasCommandBridgeRef
            overlayHostItem: root.overlayHostItem
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.compactTabStripDensity ? 36 : 48
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8

                    ShellLabeledTabStrip {
                        id: workspaceControlsStrip
                        objectName: "workspaceControlsStrip"
                        themeBridgeRef: root.themeBridgeRef
                        graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                        uiIconsRef: root.uiIconsRef
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.alignment: Qt.AlignVCenter
                    densityPreset: root.tabStripDensityPreset
                    titleText: "WORKSPACES"
                    model: root.workspaceBridgeRef.workspace_tabs
                    minTabWidth: 132
                    tabHorizontalPadding: 24
                    contextMenuActions: [
                        { "actionId": "rename", "text": "Rename Workspace" },
                        { "actionId": "delete", "text": "Delete Workspace", "destructive": true }
                    ]
                    createButtonText: "New Workspace"
                    isTabActive: function(itemData) {
                        return itemData.workspace_id === root.workspaceBridgeRef.active_workspace_id
                    }
                    onTabActivated: function(itemData) {
                        root.workspaceBridgeRef.activate_workspace(itemData.workspace_id)
                    }
                    onTabMoveRequested: function(fromIndex, toIndex, _itemData) {
                        root.workspaceBridgeRef.request_move_workspace_tab(fromIndex, toIndex)
                    }
                    onContextMenuActionRequested: function(actionId, itemData) {
                        if (actionId === "rename") {
                            root.workspaceBridgeRef.request_rename_workspace_by_id(String(itemData.workspace_id || ""))
                            return
                        }
                        if (actionId === "delete")
                            root.workspaceBridgeRef.request_close_workspace_by_id(String(itemData.workspace_id || ""))
                    }
                    onCreateActivated: root.workspaceBridgeRef.request_create_workspace()
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
                            themeBridgeRef: root.themeBridgeRef
                            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                            uiIconsRef: root.uiIconsRef
                            text: "Output"
                            selectedStyle: consoleTabs.currentIndex === 0
                            onClicked: consoleTabs.currentIndex = 0
                        }
                        ShellButton {
                            themeBridgeRef: root.themeBridgeRef
                            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                            uiIconsRef: root.uiIconsRef
                            text: "Errors (" + root.workspaceBridgeRef.error_count_value + ")"
                            selectedStyle: consoleTabs.currentIndex === 1
                            onClicked: consoleTabs.currentIndex = 1
                        }
                        ShellButton {
                            themeBridgeRef: root.themeBridgeRef
                            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                            uiIconsRef: root.uiIconsRef
                            text: "Warnings (" + root.workspaceBridgeRef.warning_count_value + ")"
                            selectedStyle: consoleTabs.currentIndex === 2
                            onClicked: consoleTabs.currentIndex = 2
                        }
                        Item { Layout.fillWidth: true }
                        ShellButton {
                            themeBridgeRef: root.themeBridgeRef
                            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
                            uiIconsRef: root.uiIconsRef
                            text: "Clear"
                            onClicked: root.workspaceBridgeRef.clear_all()
                        }
                    }
                }

                StackLayout {
                    id: consoleTabs
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TextArea {
                        readOnly: true
                        text: root.workspaceBridgeRef.output_text
                        color: root.themePalette.app_fg
                        font.family: "Consolas"
                        font.pixelSize: 12
                        wrapMode: TextArea.NoWrap
                        background: Rectangle { color: root.themePalette.console_bg }
                    }
                    TextArea {
                        readOnly: true
                        text: root.workspaceBridgeRef.errors_text
                        color: "#F7A1A1"
                        font.family: "Consolas"
                        font.pixelSize: 12
                        wrapMode: TextArea.NoWrap
                        background: Rectangle { color: root.themePalette.console_bg }
                    }
                    TextArea {
                        readOnly: true
                        text: root.workspaceBridgeRef.warnings_text
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
