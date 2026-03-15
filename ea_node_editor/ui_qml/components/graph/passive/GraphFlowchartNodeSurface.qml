import QtQuick 2.15
import ".." as GraphComponents

Item {
    id: surface
    objectName: "graphNodeFlowchartSurface"
    property Item host: null

    FlowchartShapeCanvas {
        anchors.fill: parent
        variant: host ? host.surfaceVariant : ""
        fillColor: host ? host.surfaceColor : "#1b1d22"
        strokeColor: host
            ? (host.nodeData && host.nodeData.selected ? host.selectedOutlineColor : host.outlineColor)
            : "#3a3d45"
        strokeWidth: host && host.nodeData && host.nodeData.selected ? 2 : 1
    }

    GraphComponents.GraphInlinePropertiesLayer {
        anchors.fill: parent
        host: surface.host
    }
}
