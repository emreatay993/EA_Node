import QtQuick 2.15
import QtQuick.Effects
import ".." as GraphComponents
import "../surface_controls" as SurfaceControls
import "../GraphNodeHostHitTesting.js" as GraphNodeHostHitTesting

Item {
    id: surface
    objectName: "graphNodeFlowchartSurface"
    property Item host: null
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    property bool editingBody: false
    readonly property var embeddedInteractiveRects: bodyEditor.visible
        ? bodyEditor.embeddedInteractiveRects
        : inlinePropertiesLayer.embeddedInteractiveRects
    readonly property bool shapeShadowVisible: host ? Boolean(host._surfaceShadowVisible) : false
    readonly property bool shapeShadowCacheActive: host ? Boolean(host.surfaceShadowCacheActive) : false
    readonly property string shapeShadowCacheKey: host ? String(host.surfaceShadowCacheKey || "") : ""
    readonly property string bodyValue: _resolvedBodyText()
    readonly property color bodyTextColor: host ? host.headerTextColor : "#173247"
    readonly property real bodyFontSize: host ? Number(host.passiveFontPixelSize || 12) : 12
    readonly property bool bodyFontBold: host ? Boolean(host.passiveFontBold) : false
    readonly property real bodyVerticalInset: host
        ? Math.max(12, Number(host.surfaceMetrics.body_bottom_margin || 16))
        : 16

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

    function _beginInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _beginBodyEdit() {
        if (surface.editingBody)
            return true;
        if (!host || !host.nodeData)
            return false;
        surface.editingBody = true;
        surface._beginInteraction();
        Qt.callLater(function() {
            bodyEditor.syncDraftToCommitted();
            bodyEditor.activateEditor();
        });
        return true;
    }

    function _commitBody(value) {
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), "body", value);
        surface.editingBody = false;
    }

    function _cancelBodyEdit() {
        bodyEditor.resetDraft();
        surface.editingBody = false;
    }

    function requestInlineEditAt(localX, localY) {
        if (surface.editingBody)
            return GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditorInteractionRegion.interactiveRect);
        if (!GraphNodeHostHitTesting.pointInRect(localX, localY, bodyDisplayInteractionRegion.interactiveRect))
            return false;
        return surface._beginBodyEdit();
    }

    function commitInlineEditFromExternalInteraction(localX, localY) {
        if (!surface.editingBody)
            return false;
        if (GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditorInteractionRegion.interactiveRect))
            return false;
        surface._commitBody(bodyEditor.draftText);
        return true;
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
        id: bodyBounds
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 18) : 18
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 18) : 18
        anchors.top: parent.top
        anchors.topMargin: surface.bodyVerticalInset
        anchors.bottom: parent.bottom
        anchors.bottomMargin: surface.bodyVerticalInset
        clip: true

        Text {
            id: flowchartBodyText
            objectName: "graphNodeFlowchartBodyText"
            property int effectiveRenderType: renderType
            visible: !surface.editingBody
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

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyDisplayInteractionRegion
            host: surface.host
            targetItem: flowchartBodyText
            enabled: flowchartBodyText.visible
        }

        SurfaceControls.GraphSurfaceTextareaEditor {
            id: bodyEditor
            objectName: "graphNodeFlowchartBodyEditor"
            visible: surface.editingBody
            width: parent.width
            host: surface.host
            propertyKey: "body"
            committedText: surface._propertyText("body")
            showActionButtons: false
            fieldFont.pixelSize: surface.bodyFontSize
            fieldFont.bold: surface.bodyFontBold
            fieldObjectName: "graphNodeFlowchartBodyEditorField"
            applyButtonObjectName: "graphNodeFlowchartBodyApplyButton"
            resetButtonObjectName: "graphNodeFlowchartBodyResetButton"
            onControlStarted: surface._beginInteraction()
            onCommitRequested: function(value) {
                surface._commitBody(value);
            }
            Keys.onEscapePressed: function(event) {
                surface._cancelBodyEdit();
                event.accepted = true;
            }
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyEditorInteractionRegion
            host: surface.host
            targetItem: bodyEditor
            enabled: bodyEditor.visible
        }
    }

    GraphComponents.GraphInlinePropertiesLayer {
        id: inlinePropertiesLayer
        anchors.fill: parent
        host: surface.host
    }
}
