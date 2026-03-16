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
    readonly property bool blocksHostInteraction: loader.item ? Boolean(loader.item.blocksHostInteraction) : false
    readonly property var hoverActionHitRect: loader.item && loader.item.hoverActionHitRect
        ? loader.item.hoverActionHitRect
        : Qt.rect(0, 0, 0, 0)

    function _loadedSurfaceKey(family, _variant) {
        var normalizedFamily = String(family || "standard");
        if (normalizedFamily === "flowchart")
            return "flowchart";
        if (normalizedFamily === "planning")
            return "planning";
        if (normalizedFamily === "annotation")
            return "annotation";
        if (normalizedFamily === "media")
            return "media";
        return "standard";
    }

    function triggerHoverAction() {
        if (loader.item && loader.item.triggerHoverAction)
            loader.item.triggerHoverAction();
    }

    Loader {
        id: loader
        anchors.fill: parent
        active: !!root.host && !!root.nodeData && !Boolean(root.nodeData.collapsed)
        sourceComponent: {
            if (root.loadedSurfaceKey === "flowchart")
                return flowchartSurfaceComponent;
            if (root.loadedSurfaceKey === "planning")
                return planningSurfaceComponent;
            if (root.loadedSurfaceKey === "annotation")
                return annotationSurfaceComponent;
            if (root.loadedSurfaceKey === "media")
                return mediaSurfaceComponent;
            return standardSurfaceComponent;
        }
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

    Component {
        id: planningSurfaceComponent

        GraphPassiveComponents.GraphPlanningCardSurface {
            host: root.host
        }
    }

    Component {
        id: annotationSurfaceComponent

        GraphPassiveComponents.GraphAnnotationNoteSurface {
            host: root.host
        }
    }

    Component {
        id: mediaSurfaceComponent

        GraphPassiveComponents.GraphMediaPanelSurface {
            host: root.host
        }
    }
}
