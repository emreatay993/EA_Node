import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "MainShellUtils.js" as MainShellUtils

Rectangle {
    id: root
    property var mainWindowRef
    readonly property var workspaceBridgeRef: shellWorkspaceBridge
    property var scriptEditorBridgeRef
    property var scriptHighlighterBridgeRef
    readonly property var themePalette: themeBridge.palette

    visible: root.scriptEditorBridgeRef.visible
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.bottom: parent.bottom
    width: Math.min(parent.width * 0.42, 520)
    color: themePalette.panel_bg
    border.color: themePalette.accent
    border.width: 1
    z: 999

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: root.themePalette.toolbar_bg
            border.color: root.themePalette.border
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                Text {
                    text: root.scriptEditorBridgeRef.current_node_label
                        ? "Python Script: " + root.scriptEditorBridgeRef.current_node_label
                        : "Python Script Editor"
                    color: root.themePalette.panel_title_fg
                    font.pixelSize: 12
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: root.scriptEditorBridgeRef.dirty ? "*Modified" : "Saved"
                    color: root.scriptEditorBridgeRef.dirty
                        ? root.themePalette.accent
                        : root.themePalette.muted_fg
                    font.pixelSize: 11
                }
                ShellButton {
                    text: "X"
                    onClicked: root.workspaceBridgeRef.set_script_editor_panel_visible(false)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                id: scriptLineGutter
                Layout.preferredWidth: 52
                Layout.fillHeight: true
                color: root.themePalette.console_bg
                border.color: root.themePalette.border
                clip: true

                Text {
                    id: scriptLineNumberText
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    y: (scriptEditorScroll.contentItem ? -scriptEditorScroll.contentItem.contentY : 0) + 6
                    text: MainShellUtils.lineNumbersText(scriptEditorArea.lineCount)
                    color: root.themePalette.muted_fg
                    font.family: "Consolas"
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignTop
                }
            }

            ScrollView {
                id: scriptEditorScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                TextArea {
                    id: scriptEditorArea
                    width: scriptEditorScroll.availableWidth
                    text: root.scriptEditorBridgeRef.script_text
                    readOnly: !root.scriptEditorBridgeRef.current_node_id
                    color: root.themePalette.input_fg
                    font.family: "Consolas"
                    font.pixelSize: 12
                    wrapMode: TextArea.NoWrap
                    background: Rectangle { color: root.themePalette.console_bg }
                    selectByMouse: true
                    persistentSelection: true
                    leftPadding: 8
                    rightPadding: 8
                    topPadding: 6
                    bottomPadding: 6

                    Component.onCompleted: root.scriptHighlighterBridgeRef.attach_document(textDocument)

                    onTextChanged: {
                        if (text !== root.scriptEditorBridgeRef.script_text) {
                            root.scriptEditorBridgeRef.set_script_text(text)
                        }
                        var before = text.slice(0, cursorPosition)
                        var lines = before.split("\n")
                        var line = lines.length
                        var col = lines[lines.length - 1].length + 1
                        var sel = Math.abs(selectionStart - selectionEnd)
                        root.scriptEditorBridgeRef.set_cursor_metrics(line, col, cursorPosition, sel)
                    }

                    onCursorPositionChanged: {
                        var before = text.slice(0, cursorPosition)
                        var lines = before.split("\n")
                        var line = lines.length
                        var col = lines[lines.length - 1].length + 1
                        var sel = Math.abs(selectionStart - selectionEnd)
                        root.scriptEditorBridgeRef.set_cursor_metrics(line, col, cursorPosition, sel)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: root.themePalette.toolbar_bg
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                Text {
                    text: root.scriptEditorBridgeRef.cursor_label
                    color: root.themePalette.muted_fg
                    font.pixelSize: 11
                }
                Item { Layout.fillWidth: true }
                ShellButton {
                    text: "Revert"
                    enabled: root.scriptEditorBridgeRef.dirty
                    onClicked: root.scriptEditorBridgeRef.revert()
                }
                ShellButton {
                    text: "Apply"
                    enabled: root.scriptEditorBridgeRef.dirty
                    onClicked: root.scriptEditorBridgeRef.apply()
                }
            }
        }
    }
}
