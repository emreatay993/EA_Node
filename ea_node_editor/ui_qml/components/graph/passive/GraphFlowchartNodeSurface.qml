import QtQuick 2.15
import QtQuick.Effects
import ".." as GraphComponents

Item {
    id: surface
    objectName: "graphNodeFlowchartSurface"
    property Item host: null
    readonly property var embeddedInteractiveRects: inlinePropertiesLayer.embeddedInteractiveRects
    readonly property bool shapeShadowVisible: host ? Boolean(host._surfaceShadowVisible) : false
    readonly property bool shapeShadowCacheActive: host ? Boolean(host.surfaceShadowCacheActive) : false
    readonly property string shapeShadowCacheKey: host ? String(host.surfaceShadowCacheKey || "") : ""

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

    GraphComponents.GraphInlinePropertiesLayer {
        id: inlinePropertiesLayer
        anchors.fill: parent
        host: surface.host
    }
}
