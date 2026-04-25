import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var workspaceBridgeRef: typeof shellWorkspaceBridge !== "undefined" ? shellWorkspaceBridge : null
    property var viewBridgeRef
    property var scriptEditorBridgeRef
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    property var graphCanvasStateBridgeRef: typeof graphCanvasStateBridge !== "undefined" ? graphCanvasStateBridge : null
    property var uiIconsRef: typeof uiIcons !== "undefined" ? uiIcons : null
    readonly property var themePalette: root.themeBridgeRef ? root.themeBridgeRef.palette : ({})

    Layout.fillWidth: true
    Layout.preferredHeight: 38
    color: themePalette.toolbar_bg
    border.color: themePalette.border

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 6

        ShellButton {
            objectName: "shellRunToolbarRunButton"
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
            iconName: "run"
            enabled: root.workspaceBridgeRef.active_workspace_can_run
            onClicked: root.workspaceBridgeRef.request_run_workflow()
        }
        ShellButton {
            objectName: "shellRunToolbarPauseButton"
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
            iconName: "pause"
            tooltipText: "Pause / Resume"
            enabled: root.workspaceBridgeRef.active_workspace_can_pause
            onClicked: root.workspaceBridgeRef.request_toggle_run_pause()
        }
        ShellButton {
            objectName: "shellRunToolbarStopButton"
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
            iconName: "stop"
            enabled: root.workspaceBridgeRef.active_workspace_can_stop
            onClicked: root.workspaceBridgeRef.request_stop_workflow()
        }
        Item { Layout.fillWidth: true }
        Text {
            text: "Zoom: " + Math.round(root.viewBridgeRef.zoom_value * 100) + "%"
            color: root.themePalette.muted_fg
            font.pixelSize: 12
        }
        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.themePalette.border }
        ShellButton {
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
            text: "Settings"
            onClicked: root.workspaceBridgeRef.show_workflow_settings_dialog()
        }
        ShellButton {
            themeBridgeRef: root.themeBridgeRef
            graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef
            uiIconsRef: root.uiIconsRef
            text: root.scriptEditorBridgeRef.visible ? "Hide Script" : "Script"
            selectedStyle: root.scriptEditorBridgeRef.visible
            onClicked: root.workspaceBridgeRef.set_script_editor_panel_visible()
        }
    }
}
