import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    objectName: "graphInlinePropertiesLayer"
    property Item host: null
    readonly property var inlineProperties: host ? host.inlineProperties : []
    readonly property var embeddedInteractiveRects: root._embeddedInteractiveRects()
    implicitHeight: host ? host.inlineBodyHeight : 0
    visible: inlineProperties.length > 0

    function _embeddedInteractiveRects() {
        var rects = [];
        if (!host || inlinePropertyRepeater.count <= 0)
            return rects;
        for (var index = 0; index < inlinePropertyRepeater.count; index++) {
            var row = inlinePropertyRepeater.itemAt(index);
            if (!row || !row.visible)
                continue;
            var rowWidth = Number(row.width || 0);
            var rowHeight = Number(row.height || 0);
            if (!(rowWidth > 0) || !(rowHeight > 0))
                continue;
            var topLeft = inlineControlsColumn.mapToItem(host, Number(row.x || 0), Number(row.y || 0));
            rects.push({
                "x": Number(topLeft.x || 0),
                "y": Number(topLeft.y || 0),
                "width": rowWidth,
                "height": rowHeight
            });
        }
        return rects;
    }

    Column {
        id: inlineControlsColumn
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 8) : 8
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 8) : 8
        anchors.top: parent.top
        anchors.topMargin: host ? Number(host.surfaceMetrics.body_top || 30) : 30
        spacing: host ? host._inlineRowSpacing : 4
        visible: inlineProperties.length > 0

        Repeater {
            id: inlinePropertyRepeater
            model: inlineProperties
            delegate: Rectangle {
                width: inlineControlsColumn.width
                height: host ? host._inlineRowHeight : 26
                radius: 4
                color: host ? host.inlineRowColor : "#24262c"
                border.color: host ? host.inlineRowBorderColor : "#4a4f5a"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    spacing: 6

                    Text {
                        Layout.preferredWidth: 78
                        text: String(modelData.label || modelData.key || "")
                        color: host ? host.inlineLabelColor : "#d0d5de"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    CheckBox {
                        visible: modelData.inline_editor === "toggle"
                        enabled: !modelData.overridden_by_input
                        checked: !!modelData.value
                        onClicked: {
                            if (host && host.nodeData)
                                host.inlinePropertyCommitted(host.nodeData.node_id, modelData.key, checked);
                        }
                    }

                    ComboBox {
                        visible: modelData.inline_editor === "enum"
                        Layout.fillWidth: true
                        enabled: !modelData.overridden_by_input
                        model: modelData.enum_values || []
                        currentIndex: {
                            var values = modelData.enum_values || [];
                            var value = String(modelData.value || "");
                            var matchIndex = values.indexOf(value);
                            return matchIndex >= 0 ? matchIndex : 0;
                        }
                        onActivated: {
                            var values = modelData.enum_values || [];
                            if (!host || !host.nodeData || currentIndex < 0 || currentIndex >= values.length)
                                return;
                            host.inlinePropertyCommitted(host.nodeData.node_id, modelData.key, String(values[currentIndex]));
                        }
                    }

                    TextField {
                        visible: modelData.inline_editor === "text" || modelData.inline_editor === "number"
                        Layout.fillWidth: true
                        enabled: !modelData.overridden_by_input
                        text: host ? host.inlineEditorText(modelData) : ""
                        selectByMouse: true
                        color: host ? host.inlineInputTextColor : "#f0f2f5"
                        background: Rectangle {
                            color: host ? host.inlineInputBackgroundColor : "#22242a"
                            border.color: host ? host.inlineInputBorderColor : "#4a4f5a"
                            radius: 3
                        }
                        onAccepted: {
                            if (host && host.nodeData)
                                host.inlinePropertyCommitted(host.nodeData.node_id, modelData.key, text);
                        }
                        onEditingFinished: {
                            if (host && host.nodeData)
                                host.inlinePropertyCommitted(host.nodeData.node_id, modelData.key, text);
                        }
                    }

                    Text {
                        visible: modelData.overridden_by_input
                        Layout.fillWidth: true
                        text: "Driven by " + String(modelData.input_port_label || "input")
                        color: host ? host.inlineDrivenTextColor : "#bdc5d3"
                        font.pixelSize: 9
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }
        }
    }
}
