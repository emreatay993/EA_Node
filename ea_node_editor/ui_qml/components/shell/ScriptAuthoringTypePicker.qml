// Purpose: Search registered port types with examples and exact Python spellings.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    property var pane
    property var editor
    property string value: ""
    property bool listItems: false
    property var choices: []
    property var selected: ({})
    property var detail: ({})
    signal chosen(string typeId)
    spacing: 4
    function refresh() {
        choices = editor ? editor.query_types(search.text, listItems, value) : [];
        detail = choices.length ? choices[0] : ({});
        var all = editor ? editor.query_types("", listItems, value) : [];
        selected = ({});
        for (var i = 0; i < all.length; i++)
            if (all[i].type_id === value || all[i].expression === value) selected = all[i];
    }
    onValueChanged: refresh()
    Component.onCompleted: refresh()
    ScriptAuthoringButton { tooltipCategory: "general";
        objectName: "scriptTypePickerButton"
        Layout.fillWidth: true
        implicitHeight: 34
        themeBridgeRef: root.pane.themeBridgeRef
        graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
        uiIconsRef: root.pane.uiIconsRef
        text: root.selected.label || "Choose a data type…"
        onClicked: { root.refresh(); popup.open(); search.forceActiveFocus(); }
    }
    Text {
        Layout.fillWidth: true
        text: root.selected.expression || "Select an explicit type for this port."
        color: root.pane.themePalette.muted_fg
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    Popup {
        id: popup
        objectName: "scriptTypePickerPopup"
        parent: Overlay.overlay
        x: Math.max(0, (parent.width - width) / 2)
        y: Math.max(0, (parent.height - height) / 2)
        width: Math.min(530, parent.width - 24)
        height: Math.min(580, parent.height - 32)
        modal: true
        padding: 14
        background: Rectangle { color: root.pane.themePalette.panel_bg; border.color: root.pane.themePalette.border; radius: 2 }
        ColumnLayout {
            anchors.fill: parent
            Text { text: "Choose a data type"; color: root.pane.themePalette.panel_title_fg; font.bold: true; font.pixelSize: 17 }
            ScriptAuthoringTextField {
                id: search
                objectName: "scriptTypeSearch"
                pane: root.pane
                Layout.fillWidth: true
                placeholderText: "Search type, Python name, DataFrame, decimal…"
                onTextChanged: root.refresh()
                Keys.onDownPressed: typeList.forceActiveFocus()
            }
            ListView {
                id: typeList
                objectName: "scriptTypeResults"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: root.choices
                spacing: 0
                keyNavigationEnabled: true
                onCurrentIndexChanged: if (currentIndex >= 0 && currentIndex < root.choices.length) root.detail = root.choices[currentIndex]
                ScrollBar.vertical: ScrollBar {}
                Keys.onReturnPressed: if (currentItem) currentItem.choose()
                delegate: ItemDelegate {
                    objectName: "scriptTypeChoice_" + modelData.type_id
                    width: typeList.width
                    height: 33
                    enabled: !modelData.missing
                    highlighted: ListView.isCurrentItem
                    function choose() { root.chosen(modelData.type_id); popup.close(); }
                    onClicked: choose()
                    onHoveredChanged: if (hovered) root.detail = modelData
                    background: Rectangle { color: parent.highlighted || parent.hovered ? root.pane.selectedSurfaceColor : "transparent" }
                    contentItem: RowLayout {
                        spacing: 8
                        Image {
                            Layout.preferredWidth: 16; Layout.preferredHeight: 16
                            source: root.pane.uiIconsRef
                                ? root.pane.uiIconsRef.sourceSized(root.pane.uiIconsRef.has(modelData.icon_key) ? modelData.icon_key : "code", 16, String(root.pane.themePalette.input_fg)) : ""
                        }
                        Text { Layout.preferredWidth: 155; text: modelData.label; color: root.pane.themePalette.input_fg; font.pixelSize: 12; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: modelData.expression; color: root.pane.themePalette.muted_fg; font.family: "Consolas"; font.pixelSize: 11; elide: Text.ElideMiddle }
                        Text { Layout.preferredWidth: 76; text: modelData.family; color: root.pane.themePalette.muted_fg; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: root.pane.themePalette.border }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 98
                spacing: 3
                Text { Layout.fillWidth: true; text: root.detail.label || ""; color: root.pane.themePalette.input_fg; font.pixelSize: 12; font.weight: Font.DemiBold }
                Text { Layout.fillWidth: true; text: root.detail.expression || ""; color: root.pane.themePalette.accent; font.family: "Consolas"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                Text { Layout.fillWidth: true; visible: !!root.detail.description; text: root.detail.description || ""; color: root.pane.themePalette.input_fg; font.pixelSize: 11; wrapMode: Text.Wrap }
                Text { Layout.fillWidth: true; text: root.detail.example ? "Example: " + root.detail.example : ""; color: root.pane.themePalette.muted_fg; font.pixelSize: 11; wrapMode: Text.Wrap }
            }
            Text { visible: !root.choices.length; text: "No registered types match this search."; color: root.pane.themePalette.muted_fg }
            ScriptAuthoringButton { tooltipCategory: "general"; Layout.alignment: Qt.AlignRight; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Cancel"; onClicked: popup.close() }
        }
    }
}
