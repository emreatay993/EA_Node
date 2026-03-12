import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var mainWindowRef
    property var viewBridgeRef
    property var scriptEditorBridgeRef
    readonly property var themePalette: themeBridge.palette

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
            iconName: "run"
            onClicked: root.mainWindowRef.request_run_workflow()
        }
        ShellButton {
            iconName: "pause"
            tooltipText: "Pause / Resume"
            onClicked: root.mainWindowRef.request_toggle_run_pause()
        }
        ShellButton {
            iconName: "stop"
            onClicked: root.mainWindowRef.request_stop_workflow()
        }
        Item { Layout.fillWidth: true }
        Text {
            text: "Zoom: " + Math.round(root.viewBridgeRef.zoom_value * 100) + "%"
            color: root.themePalette.muted_fg
            font.pixelSize: 12
        }
        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.themePalette.border }
        ShellButton {
            text: "Settings"
            onClicked: root.mainWindowRef.show_workflow_settings_dialog()
        }
        ShellButton {
            text: root.scriptEditorBridgeRef.visible ? "Hide Script" : "Script"
            selectedStyle: root.scriptEditorBridgeRef.visible
            onClicked: root.mainWindowRef.set_script_editor_panel_visible()
        }
    }
}
