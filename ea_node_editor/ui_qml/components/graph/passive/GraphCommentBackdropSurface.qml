import QtQuick 2.15
import "../surface_controls" as SurfaceControls

Item {
    id: surface
    objectName: "graphNodeCommentBackdropSurface"
    property Item host: null
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    readonly property bool inputOverlayMode: host
        ? String(host.surfaceVariant || "") === "comment_backdrop_input_overlay"
        : false
    // During a live resize the selected overlay host drops the inline editor,
    // but keeps a cheap wrapped-text preview so the user can still tune line
    // wrapping while dragging.
    readonly property bool livePreviewActive: host && host._liveGeometryActive
    readonly property bool livePreviewShellVisible: surface.livePreviewActive && !surface.inputOverlayMode
    readonly property bool heavyContentVisible: !surface.inputOverlayMode && !surface.livePreviewActive
    readonly property bool selectedHost: host ? (host.canvasItem ? host.isSelected : true) : false
    readonly property bool editingShellVisible: surface.inputOverlayMode
        && !surface.livePreviewActive
        && surface.selectedHost
    readonly property bool overlayPreviewTextVisible: surface.inputOverlayMode
        && surface.livePreviewActive
        && surface.selectedHost
    readonly property bool primaryReadOnlyTextVisible: !surface.inputOverlayMode
        && (!surface.livePreviewActive || !surface.selectedHost)
    readonly property bool readOnlyTextVisible: surface.overlayPreviewTextVisible
        || surface.primaryReadOnlyTextVisible
    readonly property string bodyValue: _value("body")
    readonly property var embeddedInteractiveRects: surface.editingShellVisible
        ? bodyEditor.embeddedInteractiveRects
        : []
    readonly property color backdropFillColor: _backdropFillColor()
    readonly property color backdropGlassTopColor: host
        ? Qt.alpha(Qt.lighter(host.surfaceColor, host.hasPassiveFillOverride ? 1.12 : 1.22), host.hasPassiveFillOverride ? 0.26 : 0.2)
        : Qt.rgba(0.21, 0.24, 0.29, 0.2)
    readonly property color backdropGlassBottomColor: host
        ? Qt.alpha(Qt.darker(host.surfaceColor, host.hasPassiveFillOverride ? 1.04 : 1.08), host.hasPassiveFillOverride ? 0.34 : 0.26)
        : Qt.rgba(0.12, 0.14, 0.18, 0.26)
    readonly property color backdropBorderColor: host && host.isSelected
        ? host.selectedOutlineColor
        : (host
            ? Qt.alpha(host.outlineColor, host.hasPassiveBorderOverride ? 0.96 : 0.8)
            : "#4a4f5a")
    readonly property color backdropInnerBorderColor: host
        ? Qt.rgba(1.0, 1.0, 1.0, host.isSelected ? 0.18 : 0.11)
        : Qt.rgba(1.0, 1.0, 1.0, 0.11)
    readonly property color accentColor: host
        ? Qt.alpha(host.scopeBadgeColor, host.isSelected ? 0.28 : 0.18)
        : "#4d9fff"
    readonly property color sheenTopColor: host
        ? Qt.rgba(1.0, 1.0, 1.0, host.isSelected ? 0.18 : 0.12)
        : Qt.rgba(1.0, 1.0, 1.0, 0.12)
    readonly property color sheenBottomColor: Qt.rgba(1.0, 1.0, 1.0, 0.0)
    readonly property color lowerTintColor: host
        ? Qt.alpha(host.scopeBadgeColor, host.isSelected ? 0.14 : 0.08)
        : Qt.rgba(0.3, 0.62, 1.0, 0.08)
    readonly property color bodyTextColor: host ? Qt.alpha(host.inlineInputTextColor, 0.9) : "#f0f2f5"
    readonly property color mutedTextColor: host ? Qt.alpha(host.inlineDrivenTextColor, 0.82) : "#bdc5d3"
    readonly property color labelTextColor: host ? Qt.alpha(host.inlineLabelColor, 0.9) : "#d0d5de"
    readonly property real bodyFontSize: host ? Number(host.passiveFontPixelSize || 12) : 12
    readonly property bool bodyFontBold: false
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

    function _beginInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _commitBody(value) {
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), "body", value);
    }

    Rectangle {
        visible: surface.heavyContentVisible
        anchors.fill: parent
        radius: host ? Math.max(8, Number(host.resolvedCornerRadius || 10) + 2) : 10
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.0; color: surface.backdropGlassTopColor }
            GradientStop { position: 0.32; color: surface.backdropFillColor }
            GradientStop { position: 1.0; color: surface.backdropGlassBottomColor }
        }
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.backdropBorderColor
    }

    Rectangle {
        visible: surface.heavyContentVisible
        anchors.fill: parent
        anchors.margins: 1
        radius: host ? Math.max(7, Number(host.resolvedCornerRadius || 10) + 1) : 9
        color: "transparent"
        border.width: 1
        border.color: surface.backdropInnerBorderColor
    }

    Rectangle {
        visible: surface.heavyContentVisible
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(56, parent.height * 0.46)
        radius: host ? Math.max(8, Number(host.resolvedCornerRadius || 10) + 2) : 10
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.0; color: surface.sheenTopColor }
            GradientStop { position: 1.0; color: surface.sheenBottomColor }
        }
    }

    Rectangle {
        visible: surface.heavyContentVisible
        anchors.fill: parent
        radius: host ? Math.max(8, Number(host.resolvedCornerRadius || 10) + 2) : 10
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.0, 0.0, 0.0, 0.0) }
            GradientStop { position: 1.0; color: surface.lowerTintColor }
        }
    }

    Rectangle {
        visible: surface.heavyContentVisible
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(32, host ? Number(host.surfaceMetrics.body_top || 52) - 12 : 40)
        color: surface.accentColor
        opacity: 0.7
    }

    Rectangle {
        visible: surface.livePreviewShellVisible
        anchors.fill: parent
        radius: host ? Math.max(8, Number(host.resolvedCornerRadius || 10) + 2) : 10
        color: surface.backdropFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.backdropBorderColor
    }

    Rectangle {
        visible: surface.livePreviewShellVisible
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(32, host ? Number(host.surfaceMetrics.body_top || 52) - 12 : 40)
        color: surface.accentColor
        opacity: 0.55
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

            Text {
                visible: surface.readOnlyTextVisible && surface.bodyValue.length > 0
                objectName: "graphNodeCommentBackdropBodyText"
                width: parent.width
                text: surface.bodyValue
                color: surface.bodyTextColor
                font.pixelSize: surface.bodyFontSize
                font.bold: surface.bodyFontBold
                wrapMode: Text.WordWrap
                maximumLineCount: 8
                elide: Text.ElideRight
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            Text {
                visible: surface.readOnlyTextVisible && surface.bodyValue.length === 0
                width: parent.width
                text: "Backdrop notes stay on the standard graph document path in P01."
                color: surface.mutedTextColor
                font.pixelSize: surface.bodyFontSize
                font.bold: surface.bodyFontBold
                wrapMode: Text.WordWrap
                maximumLineCount: 4
                elide: Text.ElideRight
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            SurfaceControls.GraphSurfaceTextareaEditor {
                id: bodyEditor
                objectName: "graphCommentBackdropBodyEditor"
                visible: surface.editingShellVisible
                width: parent.width
                host: surface.host
                propertyKey: "body"
                committedText: surface.bodyValue
                showActionButtons: false
                fieldFont.pixelSize: surface.bodyFontSize
                fieldFont.bold: surface.bodyFontBold
                fieldTextColor: surface.bodyTextColor
                fieldFillColor: "transparent"
                fieldBorderColor: "transparent"
                fieldFocusBorderColor: "transparent"
                fieldLeftPadding: 0
                fieldRightPadding: 0
                fieldTopPadding: 0
                fieldBottomPadding: 0
                fieldObjectName: "graphCommentBackdropBodyEditorField"
                applyButtonObjectName: "graphCommentBackdropBodyApplyButton"
                resetButtonObjectName: "graphCommentBackdropBodyResetButton"
                onControlStarted: surface._beginInteraction()
                onCommitRequested: function(value) {
                    surface._commitBody(value);
                }
            }
        }
    }
}
