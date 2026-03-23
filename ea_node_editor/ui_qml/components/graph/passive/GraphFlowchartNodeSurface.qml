import QtQuick 2.15
import QtQuick.Effects
import ".." as GraphComponents

Item {
    id: surface
    objectName: "graphNodeFlowchartSurface"
    property Item host: null
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    readonly property var embeddedInteractiveRects: inlinePropertiesLayer.embeddedInteractiveRects
    readonly property bool shapeShadowVisible: host ? Boolean(host._surfaceShadowVisible) : false
    readonly property bool shapeShadowCacheActive: host ? Boolean(host.surfaceShadowCacheActive) : false
    readonly property string shapeShadowCacheKey: host ? String(host.surfaceShadowCacheKey || "") : ""
    readonly property string bodyValue: _resolvedBodyText()
    readonly property color bodyTextColor: host ? host.headerTextColor : "#173247"
    readonly property real bodyFontSize: host ? Number(host.passiveFontPixelSize || 12) : 12
    readonly property bool bodyFontBold: host ? Boolean(host.passiveFontBold) : false

    function _propertyText(key) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function _resolvedBodyText() {
        var body = surface._propertyText("body");
        if (body.trim().length > 0)
            return body;
        var title = host && host.nodeData ? String(host.nodeData.title || "") : "";
        if (title.trim().length > 0)
            return title;
        return host && host.nodeData ? String(host.nodeData.display_name || "") : "";
    }

    FlowchartShapeCanvas {
        id: flowchartShapeSource
        anchors.fill: parent
        visible: !surface.shapeShadowVisible
        variant: host ? host.surfaceVariant : ""
        fillColor: host ? host.surfaceColor : "#1b1d22"
        strokeColor: host
            ? (host.isSelected ? host.selectedOutlineColor : host.outlineColor)
            : "#3a3d45"
        strokeWidth: host ? Number(host.resolvedBorderWidth || 1) : 1
    }

    FlowchartShapeCanvas {
        id: flowchartShadowSource
        anchors.fill: parent
        visible: false
        layer.enabled: surface.shapeShadowCacheActive
        variant: host ? host.surfaceVariant : ""
        fillColor: host ? host.surfaceColor : "#1b1d22"
        strokeColor: host
            ? (host.isSelected ? host.selectedOutlineColor : host.outlineColor)
            : "#3a3d45"
        strokeWidth: host ? Number(host.resolvedBorderWidth || 1) : 1
    }

    MultiEffect {
        id: flowchartShadow
        objectName: "graphNodeFlowchartShadow"
        property bool cacheActive: surface.shapeShadowCacheActive
        property string cacheKey: surface.shapeShadowCacheKey
        visible: surface.shapeShadowVisible
        anchors.fill: flowchartShadowSource
        source: flowchartShadowSource
        shadowEnabled: true
        shadowColor: "#000000"
        shadowOpacity: host ? Math.max(0.0, Math.min(1.0, Number(host.shadowStrength || 0) / 100.0)) : 0.7
        blurMax: 40
        shadowBlur: host ? Math.max(0.0, Math.min(1.0, Number(host.shadowSoftness || 0) / 100.0)) : 0.5
        shadowHorizontalOffset: 0
        shadowVerticalOffset: host ? Number(host.shadowOffset || 0) : 4
    }

    Item {
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 18) : 18
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 18) : 18
        anchors.top: parent.top
        anchors.topMargin: host ? Number(host.surfaceMetrics.title_top || 18) : 18
        anchors.bottom: parent.bottom
        anchors.bottomMargin: host ? Number(host.surfaceMetrics.body_bottom_margin || 16) : 16
        clip: true

        Text {
            id: flowchartBodyText
            objectName: "graphNodeFlowchartBodyText"
            property int effectiveRenderType: renderType
            anchors.fill: parent
            text: surface.bodyValue
            color: surface.bodyTextColor
            font.pixelSize: surface.bodyFontSize
            font.bold: surface.bodyFontBold
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }
    }

    GraphComponents.GraphInlinePropertiesLayer {
        id: inlinePropertiesLayer
        anchors.fill: parent
        host: surface.host
    }
}
