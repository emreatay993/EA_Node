import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    objectName: "inspectorHelpPane"

    property var themePalette: themeBridge.palette
    property string titleText: helpBridge.title
    property string markdownText: helpBridge.markdown
    property bool hasMarkdown: helpBridge.has_help

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 2
        anchors.rightMargin: 2
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: root.themePalette.inspector_section_header_bg
            border.color: root.themePalette.border

            Text {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                verticalAlignment: Text.AlignVCenter
                text: root.hasMarkdown
                    ? (root.titleText.length > 0 ? root.titleText : "Operator Help")
                    : "Operator Help"
                color: root.themePalette.panel_title_fg
                font.pixelSize: 12
                font.bold: true
                elide: Text.ElideRight
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: root.themePalette.panel_bg
            border.color: root.themePalette.border

            Text {
                anchors.centerIn: parent
                visible: !root.hasMarkdown
                width: parent.width - 40
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: "Select a DPF operator node and press F1 (or right-click → Help) to view its specification here."
                color: root.themePalette.muted_fg
                font.pixelSize: 11
            }

            ScrollView {
                id: helpScroll
                objectName: "helpScrollView"
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                visible: root.hasMarkdown
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded

                TextArea {
                    id: helpText
                    objectName: "helpMarkdownText"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextArea.WrapAtWordBoundaryOrAnywhere
                    textFormat: TextEdit.MarkdownText
                    text: root.markdownText
                    color: root.themePalette.app_fg
                    font.pixelSize: 12
                    background: Rectangle { color: "transparent" }

                    Component.onCompleted: helpBridge.apply_document_spacing(textDocument)
                    onTextChanged: helpBridge.apply_document_spacing(textDocument)
                }
            }
        }
    }
}
