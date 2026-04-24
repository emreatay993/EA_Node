import QtQuick 2.15

Item {
    id: root
    property Item edgeLayer: null
    property Item canvasLayer: null
    readonly property int effectiveGraphLabelPixelSize: {
        var numeric = NaN;
        if (root.canvasLayer && root.canvasLayer.graphLabelPixelSize !== undefined)
            numeric = Number(root.canvasLayer.graphLabelPixelSize);
        if (!isFinite(numeric) && root.canvasLayer && root.canvasLayer.canvasStateBridgeRef)
            numeric = Number(root.canvasLayer.canvasStateBridgeRef.graphics_graph_label_pixel_size);
        if (!isFinite(numeric)
                && root.edgeLayer
                && root.edgeLayer.parent
                && root.edgeLayer.parent.canvasItem
                && root.edgeLayer.parent.canvasItem.graphLabelPixelSize !== undefined) {
            numeric = Number(root.edgeLayer.parent.canvasItem.graphLabelPixelSize);
        }
        if (!isFinite(numeric)
                && root.edgeLayer
                && root.edgeLayer.parent
                && root.edgeLayer.parent.canvasItem
                && root.edgeLayer.parent.canvasItem.canvasStateBridgeRef) {
            numeric = Number(root.edgeLayer.parent.canvasItem.canvasStateBridgeRef.graphics_graph_label_pixel_size);
        }
        if (!isFinite(numeric) && root.edgeLayer && root.edgeLayer.graphLabelPixelSize !== undefined)
            numeric = Number(root.edgeLayer.graphLabelPixelSize);
        if (!isFinite(numeric))
            numeric = 10;
        return Math.max(8, Math.min(18, Math.round(numeric)));
    }
    readonly property var graphSharedTypography: sharedTypographyState

    GraphSharedTypography {
        id: sharedTypographyState
        objectName: "graphEdgeSharedTypography"
        graphLabelPixelSize: root.effectiveGraphLabelPixelSize
    }

    function edgeLabelText(edge) {
        return String(edge && edge.label ? edge.label : "").trim();
    }

    function flowLabelMode(edge) {
        if (!root.edgeLayer || !root.canvasLayer || !root.canvasLayer.edgeIsFlow(edge) || !edgeLabelText(edge))
            return "hidden";
        if (root.edgeLayer.edgeLabelSimplificationActive)
            return "hidden";
        var zoom = root.edgeLayer.viewBridge ? root.edgeLayer.viewBridge.zoom_value : 1.0;
        if (zoom < root.edgeLayer.flowLabelHideZoomThreshold)
            return "hidden";
        if (zoom < root.edgeLayer.flowLabelSimplifyZoomThreshold)
            return "text";
        return "pill";
    }

    function flowLabelTextColor(edge) {
        return root.canvasLayer
            ? (root.canvasLayer.styleString(root.canvasLayer.flowStyle(edge).label_text_color) || root.edgeLayer.flowDefaultLabelTextColor)
            : root.edgeLayer.flowDefaultLabelTextColor;
    }

    function flowLabelBackgroundColor(edge) {
        return root.canvasLayer
            ? (root.canvasLayer.styleString(root.canvasLayer.flowStyle(edge).label_background_color) || root.edgeLayer.flowDefaultLabelBackgroundColor)
            : root.edgeLayer.flowDefaultLabelBackgroundColor;
    }

    function flowLabelBorderColor(edge, selected, previewed) {
        if ((selected || previewed) && root.canvasLayer)
            return root.canvasLayer.flowStrokeColor(edge, selected, previewed);
        return root.edgeLayer.flowDefaultLabelBorderColor;
    }

    function flowLabelAnchorScene(geometry) {
        var anchor = null;
        if (geometry && geometry.route === "pipe") {
            var pipePoints = geometry.pipe_points || [];
            var longestHorizontal = null;
            for (var i = 1; i < pipePoints.length; i++) {
                var start = pipePoints[i - 1];
                var end = pipePoints[i];
                var dx = end.x - start.x;
                var dy = end.y - start.y;
                if (Math.abs(dy) > 0.01)
                    continue;
                var length = Math.abs(dx);
                if (!longestHorizontal || length > longestHorizontal.length) {
                    longestHorizontal = {
                        "x": (start.x + end.x) * 0.5,
                        "y": start.y,
                        "dx": dx >= 0.0 ? 1.0 : -1.0,
                        "dy": 0.0,
                        "angle": dx >= 0.0 ? 0.0 : 180.0,
                        "length": length
                    };
                }
            }
            anchor = longestHorizontal || root.edgeLayer._edgeAnchor(geometry, 0.5);
        } else {
            anchor = root.edgeLayer._edgeAnchor(geometry, 0.5);
        }
        if (!anchor)
            return null;
        var normalX = -anchor.dy;
        var normalY = anchor.dx;
        if (normalY > 0.0) {
            normalX = -normalX;
            normalY = -normalY;
        }
        return {
            "x": anchor.x,
            "y": anchor.y,
            "dx": anchor.dx,
            "dy": anchor.dy,
            "normal_x": normalX,
            "normal_y": normalY,
            "angle": anchor.angle
        };
    }

    function flowLabelAnchor(labelAnchorScene) {
        if (!labelAnchorScene || !root.edgeLayer)
            return null;
        return {
            "screen_x": root.edgeLayer.sceneToScreenX(labelAnchorScene.x) + Number(labelAnchorScene.normal_x) * 18.0,
            "screen_y": root.edgeLayer.sceneToScreenY(labelAnchorScene.y) + Number(labelAnchorScene.normal_y) * 18.0,
            "angle": labelAnchorScene.angle
        };
    }

    Repeater {
        model: root.edgeLayer ? (root.edgeLayer.edges || []) : []

        delegate: Item {
            objectName: "graphEdgeFlowLabelItem"
            property var edgeData: modelData
            property string edgeId: String(edgeData && edgeData.edge_id || "")
            property var snapshotData: edgeId && root.edgeLayer ? root.edgeLayer._visibleEdgeSnapshot(edgeId) : null
            property string labelText: snapshotData ? String(snapshotData.labelText || "") : ""
            property string labelMode: snapshotData ? String(snapshotData.labelMode || "hidden") : "hidden"
            property bool labelRequested: labelMode !== "hidden"
            property var snapshotRevision: snapshotData ? snapshotData.revision : 0
            property bool culledByViewport: labelRequested && snapshotData ? Boolean(snapshotData.culled) : false
            property bool pillVisible: labelMode === "pill"
            property real anchorScreenX: labelAnchor ? labelAnchor.screen_x : 0.0
            property real anchorScreenY: labelAnchor ? labelAnchor.screen_y : 0.0
            property var geometry: labelRequested && !culledByViewport && snapshotData ? snapshotData.geometry : null
            property var labelAnchorScene: labelRequested && !culledByViewport && snapshotData ? snapshotData.labelAnchorScene : null
            property var labelAnchor: labelAnchorScene ? root.flowLabelAnchor(labelAnchorScene) : null
            property bool hitTestMatches: visible
            property bool selectedEdge: snapshotData ? Boolean(snapshotData.selected) : false
            property bool previewedEdge: snapshotData ? Boolean(snapshotData.previewed) : false
            property real horizontalPadding: pillVisible ? 9.0 : 1.0
            property real verticalPadding: pillVisible ? 5.0 : 0.0
            property real maximumTextWidth: pillVisible ? 180.0 : 110.0
            visible: labelRequested && !culledByViewport && labelAnchor !== null
            width: labelTextItem.width + horizontalPadding * 2.0
            height: labelTextItem.height + verticalPadding * 2.0
            x: anchorScreenX - width * 0.5
            y: anchorScreenY - height * 0.5

            Rectangle {
                objectName: "graphEdgeFlowLabelPill"
                anchors.fill: parent
                radius: height * 0.5
                visible: parent.pillVisible
                color: root.flowLabelBackgroundColor(parent.edgeData)
                border.width: 1
                border.color: root.flowLabelBorderColor(parent.edgeData, parent.selectedEdge, parent.previewedEdge)
            }

            Text {
                id: labelTextItem
                objectName: "graphEdgeFlowLabelText"
                anchors.centerIn: parent
                width: Math.min(parent.maximumTextWidth, implicitWidth)
                text: parent.labelText
                color: root.flowLabelTextColor(parent.edgeData)
                font.pixelSize: parent.pillVisible
                    ? root.graphSharedTypography.edgePillPixelSize
                    : root.graphSharedTypography.edgeLabelPixelSize
                font.weight: parent.pillVisible
                    ? root.graphSharedTypography.edgePillFontWeight
                    : root.graphSharedTypography.edgeLabelFontWeight
                wrapMode: Text.NoWrap
                elide: Text.ElideRight
                renderType: Text.NativeRendering
            }
        }
    }
}
