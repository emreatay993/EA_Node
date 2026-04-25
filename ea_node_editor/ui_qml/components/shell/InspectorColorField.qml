import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property var pane
    property string propertyKey: ""
    property string committedText: ""
    readonly property string text: colorField.text
    function _tooltipBridge() {
        return root.pane ? root.pane.graphCanvasStateBridgeRef : null;
    }
    readonly property bool informationalTooltipsEnabled: {
        var bridge = root._tooltipBridge();
        if (bridge && bridge.graphics_show_tooltips !== undefined)
            return Boolean(bridge.graphics_show_tooltips);
        return true;
    }

    implicitWidth: editorRow.implicitWidth
    implicitHeight: editorRow.implicitHeight

    function _normalizedText(value) {
        return String(value || "").trim();
    }

    function _hasValidColor(value) {
        return /^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$/.test(root._normalizedText(value));
    }

    function _swatchFillColor(value) {
        return root._hasValidColor(value)
            ? root._normalizedText(value)
            : "transparent";
    }

    function _swatchBorderColor() {
        return pickButton.hovered
            ? root.pane.themePalette.accent
            : root.pane.themePalette.input_border;
    }

    function syncTextToCommitted() {
        if (colorField.text !== committedText)
            colorField.text = committedText;
    }

    function commitText(value) {
        if (root.pane.inspectorBridgeRef)
            root.pane.inspectorBridgeRef.set_selected_node_property(root.propertyKey, String(value || ""));
    }

    function pickColor() {
        if (!root.pane.inspectorBridgeRef)
            return;
        var selectedColor = root.pane.inspectorBridgeRef.pick_selected_node_property_color(
            root.propertyKey,
            colorField.text
        );
        if (!String(selectedColor || "").length)
            return;
        if (colorField.text !== String(selectedColor))
            colorField.text = String(selectedColor);
        commitText(colorField.text);
    }

    onCommittedTextChanged: {
        if (!colorField.activeFocus)
            syncTextToCommitted();
    }

    Component.onCompleted: syncTextToCommitted()

    RowLayout {
        id: editorRow
        anchors.fill: parent
        spacing: 6

        Button {
            id: pickButton
            objectName: "inspectorColorPickerButton"
            property string propertyKey: root.propertyKey
            Layout.preferredWidth: 34
            Layout.minimumWidth: 34
            Layout.maximumWidth: 34
            Layout.preferredHeight: 34
            Layout.minimumHeight: 34
            Layout.maximumHeight: 34
            enabled: root.enabled
            hoverEnabled: true
            focusPolicy: Qt.NoFocus

            onClicked: root.pickColor()

            ToolTip.visible: root.informationalTooltipsEnabled && hovered
            ToolTip.delay: 280
            ToolTip.text: "Pick color"

            contentItem: Item {
                implicitWidth: 0
                implicitHeight: 0
            }

            background: Rectangle {
                radius: 9
                color: root._swatchFillColor(colorField.text)
                border.width: 1
                border.color: root._swatchBorderColor()

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 5
                    color: root._hasValidColor(colorField.text)
                        ? root._swatchFillColor(colorField.text)
                        : Qt.alpha(root.pane.themePalette.tab_bg, 0.75)
                    border.width: root._hasValidColor(colorField.text) ? 0 : 1
                    border.color: root.pane.themePalette.input_border
                }
            }
        }

        InspectorTextField {
            id: colorField
            pane: root.pane
            objectName: "inspectorColorEditor"
            property string propertyKey: root.propertyKey
            Layout.fillWidth: true
            enabled: root.enabled
            onAccepted: root.commitText(text)
            onEditingFinished: root.commitText(text)
        }
    }
}
