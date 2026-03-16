import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "surface_controls" as SurfaceControls
import "surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: root
    objectName: "graphInlinePropertiesLayer"
    property Item host: null
    readonly property var inlineProperties: host ? host.inlineProperties : []
    readonly property real _interactiveRectGeometryKey: {
        var total = inlinePropertyRepeater.count;
        total += inlineControlsColumn.x + inlineControlsColumn.y + inlineControlsColumn.width + inlineControlsColumn.height;
        for (var index = 0; index < inlinePropertyRepeater.count; index++) {
            var row = inlinePropertyRepeater.itemAt(index);
            if (!row)
                continue;
            total += row.x + row.y + row.width + row.height;
            total += row.childrenRect.x + row.childrenRect.y + row.childrenRect.width + row.childrenRect.height;
            total += row.visible ? 1 : 0;
        }
        return total;
    }
    readonly property var embeddedInteractiveRects: {
        var _geometryKey = root._interactiveRectGeometryKey;
        return root._embeddedInteractiveRects();
    }
    implicitHeight: host ? host.inlineBodyHeight : 0
    visible: inlineProperties.length > 0

    function _beginInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _commitInlineProperty(key, value) {
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), key, value);
    }

    function _embeddedInteractiveRects() {
        if (!host || inlinePropertyRepeater.count <= 0)
            return [];
        var rectLists = [];
        for (var index = 0; index < inlinePropertyRepeater.count; index++) {
            var row = inlinePropertyRepeater.itemAt(index);
            if (!row || !row.visible)
                continue;
            var rectList = row.currentInteractiveRectList();
            if (rectList && rectList.length > 0)
                rectLists.push(rectList);
        }
        return SurfaceControlGeometry.combineRectLists(rectLists);
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
                id: inlineRow
                width: inlineControlsColumn.width
                height: host ? host._inlineRowHeight : 26
                radius: 4
                color: host ? host.inlineRowColor : "#24262c"
                border.color: host ? host.inlineRowBorderColor : "#4a4f5a"
                function currentInteractiveRectList() {
                    return SurfaceControlGeometry.collectVisibleItemRects(
                        [toggleEditor, enumEditor, valueEditor],
                        root.host
                    );
                }

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

                    SurfaceControls.GraphSurfaceCheckBox {
                        id: toggleEditor
                        visible: modelData.inline_editor === "toggle"
                        enabled: !modelData.overridden_by_input
                        checked: !!modelData.value
                        host: root.host
                        text: ""
                        onControlStarted: root._beginInteraction()
                        onClicked: {
                            root._commitInlineProperty(modelData.key, checked);
                        }
                    }

                    SurfaceControls.GraphSurfaceComboBox {
                        id: enumEditor
                        visible: modelData.inline_editor === "enum"
                        Layout.fillWidth: true
                        enabled: !modelData.overridden_by_input
                        host: root.host
                        model: modelData.enum_values || []
                        currentIndex: {
                            var values = modelData.enum_values || [];
                            var value = String(modelData.value || "");
                            var matchIndex = values.indexOf(value);
                            return matchIndex >= 0 ? matchIndex : 0;
                        }
                        onControlStarted: root._beginInteraction()
                        onActivated: {
                            var values = modelData.enum_values || [];
                            if (currentIndex < 0 || currentIndex >= values.length)
                                return;
                            root._commitInlineProperty(modelData.key, String(values[currentIndex]));
                        }
                    }

                    SurfaceControls.GraphSurfaceTextField {
                        id: valueEditor
                        visible: modelData.inline_editor === "text" || modelData.inline_editor === "number"
                        Layout.fillWidth: true
                        enabled: !modelData.overridden_by_input
                        host: root.host
                        text: host ? host.inlineEditorText(modelData) : ""
                        onControlStarted: root._beginInteraction()
                        onAccepted: {
                            root._commitInlineProperty(modelData.key, text);
                        }
                        onEditingFinished: {
                            root._commitInlineProperty(modelData.key, text);
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
