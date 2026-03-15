import QtQuick 2.15

Item {
    id: surface
    objectName: "graphNodePlanningSurface"
    property Item host: null
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    readonly property string planningVariant: host ? String(host.surfaceVariant || "") : ""
    readonly property color panelFillColor: Qt.darker(host ? host.surfaceColor : "#1b1d22", 1.06)
    readonly property color panelBorderColor: host ? Qt.lighter(host.outlineColor, 1.12) : "#4a4f5a"
    readonly property color bodyTextColor: host ? host.inlineInputTextColor : "#f0f2f5"
    readonly property color mutedTextColor: host ? host.inlineDrivenTextColor : "#bdc5d3"
    readonly property color metaLabelColor: host ? host.inlineLabelColor : "#d0d5de"
    readonly property string bodyValue: _value("body")
    readonly property string leftMetaLabel: _leftMetaLabel()
    readonly property string leftMetaValue: _leftMetaValue()
    readonly property string rightMetaLabel: _rightMetaLabel()
    readonly property string rightMetaValue: _rightMetaValue()
    readonly property string detailMetaLabel: _detailMetaLabel()
    readonly property string detailMetaValue: _detailMetaValue()
    readonly property string chipText: _chipText()
    readonly property color chipFillColor: _chipFillColor()
    readonly property color chipBorderColor: Qt.lighter(chipFillColor, 1.16)
    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

    function _value(key) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function _variantLabel() {
        switch (planningVariant) {
        case "milestone_card":
            return "MILESTONE";
        case "risk_card":
            return "RISK";
        case "decision_card":
            return "DECISION";
        case "task_card":
        default:
            return "TASK";
        }
    }

    function _chipText() {
        switch (planningVariant) {
        case "milestone_card":
            return _value("status").replace("_", " ");
        case "risk_card":
            return _value("severity");
        case "decision_card":
            return _value("state");
        case "task_card":
        default:
            return _value("status").replace("_", " ");
        }
    }

    function _chipFillColor() {
        var key = _chipText();
        if (key === "done" || key === "decided")
            return "#2f8f68";
        if (key === "in progress" || key === "planned" || key === "open")
            return "#2c6fb2";
        if (key === "blocked" || key === "at risk" || key === "high")
            return "#b65f2a";
        if (key === "critical")
            return "#b04444";
        if (key === "low")
            return "#4f7aa7";
        if (key === "medium")
            return "#8a6d34";
        if (key === "deferred" || key === "todo")
            return "#5c6470";
        return "#4a6178";
    }

    function _leftMetaLabel() {
        switch (planningVariant) {
        case "task_card":
            return "Owner";
        case "milestone_card":
            return "Target";
        default:
            return "";
        }
    }

    function _leftMetaValue() {
        switch (planningVariant) {
        case "task_card":
            return _value("owner");
        case "milestone_card":
            return _value("target_date");
        default:
            return "";
        }
    }

    function _rightMetaLabel() {
        if (planningVariant === "task_card")
            return "Due";
        return "";
    }

    function _rightMetaValue() {
        if (planningVariant === "task_card")
            return _value("due_date");
        return "";
    }

    function _detailMetaLabel() {
        switch (planningVariant) {
        case "risk_card":
            return "Mitigation";
        case "decision_card":
            return "Outcome";
        default:
            return "";
        }
    }

    function _detailMetaValue() {
        switch (planningVariant) {
        case "risk_card":
            return _value("mitigation");
        case "decision_card":
            return _value("outcome");
        default:
            return "";
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 6
        color: surface.panelFillColor
        border.width: 1
        border.color: surface.panelBorderColor
    }

    Item {
        id: bodyBounds
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 14) : 14
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 14) : 14
        anchors.top: parent.top
        anchors.topMargin: host ? Number(host.surfaceMetrics.body_top || 44) : 44
        anchors.bottom: parent.bottom
        anchors.bottomMargin: host ? Number(host.surfaceMetrics.body_bottom_margin || 12) : 12
        clip: true

        Column {
            anchors.fill: parent
            spacing: 8

            Row {
                width: parent.width
                spacing: 8

                Text {
                    id: variantLabel
                    text: surface._variantLabel()
                    color: surface.metaLabelColor
                    font.pixelSize: 10
                    font.bold: true
                    opacity: 0.86
                }

                Item {
                    width: Math.max(0, parent.width - variantLabel.implicitWidth - statusChip.implicitWidth - 8)
                    height: 1
                }

                Rectangle {
                    id: statusChip
                    visible: surface.chipText.length > 0
                    radius: 9
                    color: surface.chipFillColor
                    border.width: 1
                    border.color: surface.chipBorderColor
                    height: 18
                    width: chipTextLabel.implicitWidth + 12

                    Text {
                        id: chipTextLabel
                        anchors.centerIn: parent
                        text: surface.chipText.toUpperCase()
                        color: "#f5f7fb"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }

            Text {
                visible: surface.bodyValue.length > 0
                width: parent.width
                text: surface.bodyValue
                color: surface.bodyTextColor
                wrapMode: Text.WordWrap
                maximumLineCount: surface.planningVariant === "milestone_card" ? 4 : 5
                elide: Text.ElideRight
            }

            Row {
                visible: surface.leftMetaValue.length > 0 || surface.rightMetaValue.length > 0
                width: parent.width
                spacing: 10

                Column {
                    visible: surface.leftMetaValue.length > 0
                    width: surface.rightMetaValue.length > 0 ? (parent.width - parent.spacing) * 0.5 : parent.width
                    spacing: 2

                    Text {
                        text: surface.leftMetaLabel
                        color: surface.metaLabelColor
                        font.pixelSize: 9
                        font.bold: true
                    }

                    Text {
                        width: parent.width
                        text: surface.leftMetaValue
                        color: surface.mutedTextColor
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }

                Column {
                    visible: surface.rightMetaValue.length > 0
                    width: surface.leftMetaValue.length > 0 ? (parent.width - parent.spacing) * 0.5 : parent.width
                    spacing: 2

                    Text {
                        text: surface.rightMetaLabel
                        color: surface.metaLabelColor
                        font.pixelSize: 9
                        font.bold: true
                    }

                    Text {
                        width: parent.width
                        text: surface.rightMetaValue
                        color: surface.mutedTextColor
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }
            }

            Column {
                visible: surface.detailMetaValue.length > 0
                width: parent.width
                spacing: 2

                Text {
                    text: surface.detailMetaLabel
                    color: surface.metaLabelColor
                    font.pixelSize: 9
                    font.bold: true
                }

                Text {
                    width: parent.width
                    text: surface.detailMetaValue
                    color: surface.mutedTextColor
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
            }
        }
    }
}
