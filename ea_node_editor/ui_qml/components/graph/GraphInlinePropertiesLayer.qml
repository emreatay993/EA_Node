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
    readonly property real _textareaRowHeight: 104
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
            var rectList = row.currentInteractiveRectList();
            for (var rectIndex = 0; rectIndex < rectList.length; rectIndex++) {
                var rect = rectList[rectIndex];
                total += Number(rect.x || 0)
                    + Number(rect.y || 0)
                    + Number(rect.width || 0)
                    + Number(rect.height || 0);
            }
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

    function _rowHeightFor(modelData) {
        if (modelData && modelData.inline_editor === "textarea")
            return root._textareaRowHeight;
        return host ? host._inlineRowHeight : 26;
    }

    function _statusChipVariant(modelData) {
        return String(modelData && modelData.status_chip_variant || "").trim().toLowerCase();
    }

    function _statusChipFillColor(modelData) {
        var variant = root._statusChipVariant(modelData);
        if (variant === "stored")
            return host ? Qt.alpha(host.scopeBadgeColor, 0.92) : "#1D8CE0";
        if (variant === "memory")
            return host ? Qt.alpha(host.inlineRowBorderColor, 0.72) : "#4a4f5a";
        return host ? Qt.alpha(host.inlineRowBorderColor, 0.72) : "#4a4f5a";
    }

    function _statusChipBorderColor(modelData) {
        var variant = root._statusChipVariant(modelData);
        if (variant === "stored")
            return host ? Qt.alpha(host.scopeBadgeBorderColor, 0.96) : "#60CDFF";
        if (variant === "memory")
            return host ? Qt.alpha(host.inlineLabelColor, 0.78) : "#bdc5d3";
        return host ? Qt.alpha(host.inlineLabelColor, 0.78) : "#bdc5d3";
    }

    function _statusChipTextColor(modelData) {
        var variant = root._statusChipVariant(modelData);
        if (variant === "stored")
            return host ? host.scopeBadgeTextColor : "#f2f4f8";
        if (variant === "memory")
            return host ? host.inlineLabelColor : "#d0d5de";
        return host ? host.inlineLabelColor : "#d0d5de";
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
                height: root._rowHeightFor(modelData)
                radius: 4
                color: host ? host.inlineRowColor : "#24262c"
                border.color: host ? host.inlineRowBorderColor : "#4a4f5a"
                function currentInteractiveRectList() {
                    return SurfaceControlGeometry.combineRectLists(
                        [
                            toggleEditor.embeddedInteractiveRects,
                            enumEditor.embeddedInteractiveRects,
                            valueEditor.embeddedInteractiveRects,
                            pathEditor.embeddedInteractiveRects,
                            textareaEditor.embeddedInteractiveRects
                        ]
                    );
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    spacing: 6

                    Text {
                        Layout.preferredWidth: 78
                        Layout.alignment: modelData.inline_editor === "textarea"
                            ? Qt.AlignTop
                            : Qt.AlignVCenter
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

                    Rectangle {
                        id: statusChip
                        objectName: "graphNodeInlineStatusChip"
                        property string propertyKey: String(modelData.key || "")
                        visible: String(modelData.status_chip_text || "").length > 0
                        Layout.alignment: Qt.AlignVCenter
                        radius: 9
                        height: 18
                        width: statusChipLabel.implicitWidth + 12
                        color: root._statusChipFillColor(modelData)
                        border.color: root._statusChipBorderColor(modelData)

                        Text {
                            id: statusChipLabel
                            objectName: "graphNodeInlineStatusChipLabel"
                            property string propertyKey: String(modelData.key || "")
                            anchors.centerIn: parent
                            text: String(modelData.status_chip_text || "")
                            color: root._statusChipTextColor(modelData)
                            font.pixelSize: 9
                            font.bold: true
                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
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

                    SurfaceControls.GraphSurfacePathEditor {
                        id: pathEditor
                        visible: modelData.inline_editor === "path"
                        Layout.fillWidth: true
                        enabled: !modelData.overridden_by_input
                        host: root.host
                        propertyKey: String(modelData.key || "")
                        committedText: host ? host.inlineEditorText(modelData) : ""
                        fieldObjectName: "graphNodeInlinePathEditor"
                        browseButtonObjectName: "graphNodeInlinePathBrowseButton"
                        browsePathResolver: function(currentPath) {
                            if (!host || !host.browseNodePropertyPath)
                                return "";
                            return host.browseNodePropertyPath(modelData.key, currentPath);
                        }
                        onControlStarted: root._beginInteraction()
                        onCommitRequested: function(value) {
                            root._commitInlineProperty(modelData.key, value);
                        }
                    }

                    SurfaceControls.GraphSurfaceTextareaEditor {
                        id: textareaEditor
                        visible: modelData.inline_editor === "textarea"
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        enabled: !modelData.overridden_by_input
                        host: root.host
                        propertyKey: String(modelData.key || "")
                        committedText: host ? host.inlineEditorText(modelData) : ""
                        fieldObjectName: "graphNodeInlineTextareaEditor"
                        applyButtonObjectName: "graphNodeInlineTextareaApplyButton"
                        resetButtonObjectName: "graphNodeInlineTextareaResetButton"
                        onControlStarted: root._beginInteraction()
                        onCommitRequested: function(value) {
                            root._commitInlineProperty(modelData.key, value);
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
