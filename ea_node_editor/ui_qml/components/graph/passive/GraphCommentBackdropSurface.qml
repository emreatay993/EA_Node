import QtQuick 2.15

Item {
    id: surface
    objectName: "graphNodeCommentBackdropSurface"
    property Item host: null
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    readonly property string bodyValue: _value("body")
    readonly property color backdropFillColor: _backdropFillColor()
    readonly property color backdropBorderColor: host && host.isSelected
        ? host.selectedOutlineColor
        : (host
            ? Qt.alpha(host.outlineColor, host.hasPassiveBorderOverride ? 0.96 : 0.8)
            : "#4a4f5a")
    readonly property color accentColor: host
        ? Qt.alpha(host.scopeBadgeColor, host.isSelected ? 0.48 : 0.3)
        : "#4d9fff"
    readonly property color bodyTextColor: host ? Qt.alpha(host.inlineInputTextColor, 0.9) : "#f0f2f5"
    readonly property color mutedTextColor: host ? Qt.alpha(host.inlineDrivenTextColor, 0.82) : "#bdc5d3"
    readonly property color labelTextColor: host ? Qt.alpha(host.inlineLabelColor, 0.9) : "#d0d5de"
    readonly property real bodyFontSize: host ? Number(host.passiveFontPixelSize || 12) : 12
    readonly property real labelFontSize: Math.max(9, bodyFontSize - 2)
    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

    function _value(key) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function _backdropFillColor() {
        var base = host ? host.surfaceColor : "#1b1d22";
        if (host && host.hasPassiveFillOverride)
            return Qt.alpha(base, 0.34);
        return Qt.alpha(Qt.lighter(base, 1.1), 0.22);
    }

    Rectangle {
        anchors.fill: parent
        radius: host ? Math.max(8, Number(host.resolvedCornerRadius || 10) + 2) : 10
        color: surface.backdropFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.backdropBorderColor
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(32, host ? Number(host.surfaceMetrics.body_top || 52) - 12 : 40)
        color: surface.accentColor
        opacity: 0.42
    }

    Item {
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 18) : 18
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 18) : 18
        anchors.top: parent.top
        anchors.topMargin: host ? Number(host.surfaceMetrics.body_top || 52) : 52
        anchors.bottom: parent.bottom
        anchors.bottomMargin: host ? Number(host.surfaceMetrics.body_bottom_margin || 18) : 18
        clip: true

        Column {
            anchors.fill: parent
            spacing: 10

            Row {
                spacing: 8

                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    color: host ? host.scopeBadgeColor : "#4d9fff"
                    opacity: 0.86
                }

                Text {
                    text: "BACKDROP"
                    color: surface.labelTextColor
                    font.pixelSize: surface.labelFontSize
                    font.bold: true
                    font.letterSpacing: 0.8
                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                }
            }

            Text {
                objectName: "graphNodeCommentBackdropBodyText"
                visible: surface.bodyValue.length > 0
                width: parent.width
                text: surface.bodyValue
                color: surface.bodyTextColor
                font.pixelSize: surface.bodyFontSize
                wrapMode: Text.WordWrap
                maximumLineCount: 8
                elide: Text.ElideRight
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            Text {
                visible: surface.bodyValue.length === 0
                width: parent.width
                text: "Backdrop notes stay on the standard graph document path in P01."
                color: surface.mutedTextColor
                font.pixelSize: surface.bodyFontSize
                wrapMode: Text.WordWrap
                maximumLineCount: 4
                elide: Text.ElideRight
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }
}
