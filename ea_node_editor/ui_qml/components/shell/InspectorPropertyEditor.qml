import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "MainShellUtils.js" as MainShellUtils

Column {
    id: propertyEditor
    property var pane
    property var propertyItem: ({})
    readonly property string propertyKey: String(propertyItem ? propertyItem.key || "" : "")
    readonly property string editorMode: String(propertyItem ? propertyItem.editor_mode || "" : "")
    readonly property string propertyValueText: String(
        propertyItem && propertyItem.value !== undefined && propertyItem.value !== null
            ? propertyItem.value
            : ""
    )

    width: parent ? parent.width : implicitWidth
    spacing: 4

    Text {
        width: parent.width
        text: String(propertyEditor.propertyItem.label || "")
        color: propertyEditor.pane.themePalette.group_title_fg
        font.pixelSize: 10
        font.bold: true
        elide: Text.ElideRight
    }

    Rectangle {
        width: parent.width
        visible: propertyEditor.editorMode === "toggle"
        radius: 10
        color: propertyEditor.pane.themePalette.input_bg
        border.color: propertyEditor.pane.themePalette.input_border
        border.width: 1
        implicitHeight: 38

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 8

            InspectorCheckBox {
                id: boolToggle
                pane: propertyEditor.pane
                checked: !!propertyEditor.propertyItem.value
                onToggled: {
                    if (propertyEditor.pane.inspectorBridgeRef)
                        propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, checked)
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: boolToggle.checked ? "Enabled" : "Disabled"
                color: propertyEditor.pane.themePalette.input_fg
                font.pixelSize: 11
            }
        }
    }

    InspectorComboBox {
        width: parent.width
        pane: propertyEditor.pane
        visible: propertyEditor.editorMode === "enum"
        model: propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values ? propertyEditor.propertyItem.enum_values : []
        currentIndex: {
            var values = propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
                ? propertyEditor.propertyItem.enum_values
                : []
            var value = String(propertyEditor.propertyItem && propertyEditor.propertyItem.value || "")
            var index = values.indexOf(value)
            return index >= 0 ? index : 0
        }
        onActivated: {
            var values = propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
                ? propertyEditor.propertyItem.enum_values
                : []
            if (!propertyEditor.pane.inspectorBridgeRef || currentIndex < 0 || currentIndex >= values.length)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                propertyEditor.propertyKey,
                String(values[currentIndex])
            )
        }
    }

    InspectorEditableComboBox {
        id: pinDataTypeEditor
        pane: propertyEditor.pane
        width: parent.width
        visible: propertyEditor.pane.isPinInspector
            && propertyEditor.propertyKey === "data_type"
        model: propertyEditor.pane.pinDataTypeOptions
        currentIndex: {
            var values = propertyEditor.pane.pinDataTypeOptions
            var value = String(propertyEditor.propertyItem && propertyEditor.propertyItem.value || "").toLowerCase()
            return values.indexOf(value)
        }
        onActivated: {
            var values = propertyEditor.pane.pinDataTypeOptions
            if (!propertyEditor.pane.inspectorBridgeRef || currentIndex < 0 || currentIndex >= values.length)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                propertyEditor.propertyKey,
                String(values[currentIndex])
            )
        }
        onAccepted: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, editText)
        }
        onActiveFocusChanged: {
            if (!activeFocus && propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, editText)
        }
        Component.onCompleted: editText = propertyEditor.propertyValueText
        onVisibleChanged: {
            if (visible && !activeFocus)
                editText = propertyEditor.propertyValueText
        }
    }

    Column {
        id: textareaEditorGroup
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "textarea"
        spacing: 6
        property string propertyKey: propertyEditor.propertyKey
        property string committedText: MainShellUtils.toEditorText(propertyEditor.propertyItem)
        property string draftText: committedText
        property bool draftDirty: draftText !== committedText

        function syncDraftToCommitted() {
            draftText = committedText
            if (textareaEditor.text !== committedText)
                textareaEditor.text = committedText
        }

        function commitDraft() {
            if (!propertyEditor.pane.inspectorBridgeRef)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyKey, draftText)
        }

        onCommittedTextChanged: {
            if (!textareaEditor.activeFocus || !draftDirty)
                syncDraftToCommitted()
        }

        InspectorTextArea {
            id: textareaEditor
            pane: propertyEditor.pane
            objectName: "inspectorTextareaEditor"
            property string propertyKey: textareaEditorGroup.propertyKey
            width: parent.width
            text: textareaEditorGroup.draftText
            onTextChanged: {
                if (textareaEditorGroup.draftText !== text)
                    textareaEditorGroup.draftText = text
            }
            Keys.onPressed: function(event) {
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                        && (event.modifiers & Qt.ControlModifier)) {
                    textareaEditorGroup.commitDraft()
                    event.accepted = true
                } else if (event.key === Qt.Key_Escape) {
                    textareaEditorGroup.syncDraftToCommitted()
                    event.accepted = true
                }
            }
        }

        RowLayout {
            width: parent.width
            spacing: 6

            InspectorButton {
                pane: propertyEditor.pane
                objectName: "inspectorTextareaApplyButton"
                property string propertyKey: textareaEditorGroup.propertyKey
                compact: true
                enabled: textareaEditorGroup.draftDirty
                text: "Apply"
                onClicked: textareaEditorGroup.commitDraft()
            }

            InspectorButton {
                pane: propertyEditor.pane
                objectName: "inspectorTextareaResetButton"
                property string propertyKey: textareaEditorGroup.propertyKey
                compact: true
                enabled: textareaEditorGroup.draftDirty
                text: "Reset"
                onClicked: textareaEditorGroup.syncDraftToCommitted()
            }

            Text {
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
                text: textareaEditorGroup.draftDirty
                    ? "Ctrl+Enter to commit"
                    : "Committed"
                color: propertyEditor.pane.themePalette.muted_fg
                font.pixelSize: 10
                elide: Text.ElideRight
            }
        }
    }

    RowLayout {
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "path"
        spacing: 6

        InspectorTextField {
            id: pathEditor
            pane: propertyEditor.pane
            objectName: "inspectorPathEditor"
            property string propertyKey: propertyEditor.propertyKey
            Layout.fillWidth: true
            text: MainShellUtils.toEditorText(propertyEditor.propertyItem)
            onAccepted: {
                if (propertyEditor.pane.inspectorBridgeRef)
                    propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
            }
            onEditingFinished: {
                if (propertyEditor.pane.inspectorBridgeRef)
                    propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
            }
        }

        InspectorButton {
            pane: propertyEditor.pane
            objectName: "inspectorPathBrowseButton"
            property string propertyKey: propertyEditor.propertyKey
            compact: true
            text: "Browse"
            onClicked: {
                if (!propertyEditor.pane.inspectorBridgeRef)
                    return
                var selectedPath = propertyEditor.pane.inspectorBridgeRef.browse_selected_node_property_path(
                    propertyEditor.propertyKey,
                    pathEditor.text
                )
                if (!String(selectedPath || "").length)
                    return
                pathEditor.text = String(selectedPath)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, pathEditor.text)
            }
        }
    }

    InspectorTextField {
        pane: propertyEditor.pane
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "text"
        text: MainShellUtils.toEditorText(propertyEditor.propertyItem)
        onAccepted: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
        }
        onEditingFinished: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
        }
    }
}
