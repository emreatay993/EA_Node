import QtQuick 2.15
import "passive" as GraphPassiveComponents

Item {
    id: root
    objectName: "graphNodeSurfaceLoader"
    property Item host: null
    property var nodeData: host ? host.nodeData : null
    property string surfaceFamily: host ? host.surfaceFamily : "standard"
    property string surfaceVariant: host ? host.surfaceVariant : ""
    readonly property string loadedSurfaceKey: _loadedSurfaceKey(surfaceFamily, surfaceVariant)
    readonly property real contentHeight: {
        if (!host || !nodeData)
            return 0.0;
        if (loader.item && Number(loader.item.implicitHeight) > 0.0)
            return Number(loader.item.implicitHeight);
        if (host.surfaceMetrics)
            return Number(host.surfaceMetrics.body_height || 0.0);
        return 0.0;
    }

    function _loadedSurfaceKey(family, _variant) {
        if (String(family || "standard") === "flowchart")
            return "flowchart";
        return "standard";
    }

    Loader {
        id: loader
        anchors.fill: parent
        active: !!root.host && !!root.nodeData && !Boolean(root.nodeData.collapsed)
        sourceComponent: root.loadedSurfaceKey === "flowchart" ? flowchartSurfaceComponent : standardSurfaceComponent
    }

    Component {
        id: standardSurfaceComponent

        GraphStandardNodeSurface {
            host: root.host
        }
    }

    Component {
        id: flowchartSurfaceComponent

        GraphPassiveComponents.GraphFlowchartNodeSurface {
            host: root.host
        }
    }
}
