import QtQuick 2.15
import "../surface_controls" as SurfaceControls
import "../GraphNodeHostHitTesting.js" as GraphNodeHostHitTesting

Item {
    id: surface
    objectName: "graphNodeAnnotationSurface"
    property Item host: null
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    readonly property string annotationVariant: host ? String(host.surfaceVariant || "") : ""
    readonly property color noteFillColor: _noteFillColor()
    readonly property color noteBorderColor: host && host.isSelected
        ? host.selectedOutlineColor
        : (host && host.hasPassiveBorderOverride
            ? host.outlineColor
            : (host ? Qt.lighter(host.outlineColor, 1.08) : "#4a4f5a"))
    readonly property color primaryTextColor: host ? host.inlineInputTextColor : "#f0f2f5"
    readonly property color secondaryTextColor: host ? host.inlineDrivenTextColor : "#bdc5d3"
    readonly property color labelTextColor: host ? host.inlineLabelColor : "#d0d5de"
    readonly property string bodyValue: _value("body")
    readonly property string subtitleValue: _value("subtitle")
    readonly property real bodyFontSize: host ? Number(host.passiveFontPixelSize || 12) : 12
    readonly property real labelFontSize: Math.max(9, bodyFontSize - 2)
    readonly property string editableBodyKey: annotationVariant === "section_header" ? "subtitle" : "body"
    readonly property string editableBodyValue: annotationVariant === "section_header" ? subtitleValue : bodyValue
    readonly property int bodyEditorLineCount: annotationVariant === "section_header"
        ? 2
        : (annotationVariant === "sticky_note" ? 5 : 4)
    readonly property real bodyEditorHeight: Math.max(
        bodyFontSize * bodyEditorLineCount * 1.45,
        bodyFontSize + 12
    )
    readonly property var embeddedInteractiveRects: bodyEditor.visible
        ? bodyEditor.embeddedInteractiveRects
        : (annotationVariant === "section_header"
            ? sectionSubtitleDoubleClickTarget.embeddedInteractiveRects
            : [])
    property bool editingBody: false
    property bool bodyEditGestureArmed: false
    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

    function _value(key) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function _noteFillColor() {
        if (host && host.hasPassiveFillOverride)
            return host.surfaceColor;
        if (annotationVariant === "section_header")
            return Qt.alpha(host ? host.headerColor : "#2a2b30", 0.22);
        if (annotationVariant === "callout")
            return Qt.darker(host ? host.inlineRowColor : "#24262c", 1.04);
        return Qt.lighter(host ? host.inlineRowColor : "#24262c", 1.08);
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
        surface.bodyEditGestureArmed = true;
        surface._beginInteraction();
        Qt.callLater(function() {
            bodyEditor.syncDraftToCommitted();
            bodyEditor.activateEditor();
            Qt.callLater(function() {
                surface.bodyEditGestureArmed = false;
            });
        });
        return true;
    }

    function _commitBody(value) {
        var nextValue = String(value === undefined || value === null ? "" : value);
        if (surface.bodyEditGestureArmed && nextValue === surface._value(surface.editableBodyKey))
            return;
        if (nextValue === surface._value(surface.editableBodyKey)) {
            surface.bodyEditGestureArmed = false;
            surface.editingBody = false;
            return;
        }
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), surface.editableBodyKey, nextValue);
        surface.bodyEditGestureArmed = false;
        surface.editingBody = false;
    }

    function _cancelBodyEdit() {
        bodyEditor.resetDraft();
        surface.bodyEditGestureArmed = false;
        surface.editingBody = false;
    }

    function requestInlineEditAt(localX, localY) {
        if (surface.editingBody)
            return GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditorInteractionRegion.interactiveRect);
        if (annotationVariant === "section_header") {
            if (GraphNodeHostHitTesting.pointInRect(localX, localY, bodyDisplayInteractionRegion.interactiveRect))
                return surface._beginBodyEdit();
            if (GraphNodeHostHitTesting.pointInRect(localX, localY, bodyBounds))
                return surface._beginBodyEdit();
            return false;
        }
        if (GraphNodeHostHitTesting.pointInRect(localX, localY, bodyDisplayInteractionRegion.interactiveRect))
            return surface._beginBodyEdit();
        if (GraphNodeHostHitTesting.pointInRect(localX, localY, emptyBodyInteractionRegion.interactiveRect))
            return surface._beginBodyEdit();
        return false;
    }

    function commitInlineEditFromExternalInteraction(localX, localY) {
        if (!surface.editingBody)
            return false;
        if (surface.bodyEditGestureArmed)
            return false;
        if (GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditorInteractionRegion.interactiveRect))
            return false;
        surface._commitBody(bodyEditor.draftText);
        return true;
    }

    Rectangle {
        anchors.fill: parent
        radius: annotationVariant === "section_header"
            ? Math.max(4, host ? Number(host.resolvedCornerRadius || 6) - 2 : 4)
            : (host ? Number(host.resolvedCornerRadius || 6) : 6)
        color: surface.noteFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.noteBorderColor
    }

    Rectangle {
        visible: annotationVariant === "sticky_note"
        width: 18
        height: 18
        anchors.top: parent.top
        anchors.right: parent.right
        color: Qt.darker(surface.noteFillColor, 1.12)
        border.width: 1
        border.color: surface.noteBorderColor
        transform: Rotation {
            angle: 45
            origin.x: 0
            origin.y: 0
        }
    }

    Rectangle {
        visible: annotationVariant === "callout"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 6
        color: host ? host.scopeBadgeColor : "#1D8CE0"
    }

    Rectangle {
        visible: annotationVariant === "section_header"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 3
        color: host ? host.scopeBadgeColor : "#1D8CE0"
    }

    Item {
        id: bodyBounds
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 14) : 14
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 14) : 14
        anchors.top: parent.top
        anchors.topMargin: host ? Number(host.surfaceMetrics.body_top || 42) : 42
        anchors.bottom: parent.bottom
        anchors.bottomMargin: host ? Number(host.surfaceMetrics.body_bottom_margin || 12) : 12
        clip: true

        Column {
            anchors.fill: parent
            spacing: annotationVariant === "section_header" ? 6 : 8

            Row {
                visible: annotationVariant === "callout"
                width: parent.width
                spacing: 8

                Rectangle {
                    width: 18
                    height: 18
                    radius: 9
                    color: Qt.alpha(host ? host.scopeBadgeColor : "#1D8CE0", 0.22)
                    border.width: 1
                    border.color: host ? host.scopeBadgeColor : "#1D8CE0"

                Text {
                    anchors.centerIn: parent
                    text: "!"
                    color: host ? host.scopeBadgeTextColor : "#f2f4f8"
                    font.pixelSize: Math.max(11, surface.bodyFontSize - 1)
                    font.bold: true
                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                }
            }

            Text {
                text: "CALLOUT"
                color: surface.labelTextColor
                font.pixelSize: surface.labelFontSize
                font.bold: true
                opacity: 0.86
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }
        }

            Text {
                id: annotationBodyText
                objectName: "graphNodeAnnotationBodyText"
                property int effectiveRenderType: renderType
                enabled: false
                visible: annotationVariant !== "section_header" && surface.bodyValue.length > 0 && !surface.editingBody
                width: parent.width
                text: surface.bodyValue
                color: surface.primaryTextColor
                font.pixelSize: surface.bodyFontSize
                font.bold: host ? Boolean(host.passiveFontBold) : false
                wrapMode: Text.WordWrap
                maximumLineCount: annotationVariant === "sticky_note" ? 5 : 4
                elide: Text.ElideRight
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            Text {
                id: sectionSubtitleText
                objectName: "graphNodeAnnotationSubtitleText"
                enabled: false
                visible: annotationVariant === "section_header" && surface.subtitleValue.length > 0 && !surface.editingBody
                width: parent.width
                text: surface.subtitleValue
                color: surface.secondaryTextColor
                font.pixelSize: surface.bodyFontSize
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            SurfaceControls.GraphSurfaceInlineTextEditor {
                id: bodyEditor
                objectName: "graphNodeAnnotationBodyEditor"
                visible: surface.editingBody
                width: parent.width
                height: Math.min(bodyBounds.height, surface.bodyEditorHeight)
                host: surface.host
                committedText: surface.editableBodyValue
                fontPixelSize: surface.bodyFontSize
                fontBold: host ? Boolean(host.passiveFontBold) : false
                textColor: surface.annotationVariant === "section_header"
                    ? surface.secondaryTextColor
                    : surface.primaryTextColor
                fieldObjectName: surface.annotationVariant === "section_header"
                    ? "graphNodeAnnotationSubtitleEditorField"
                    : "graphNodeAnnotationBodyEditorField"
                centerTextVertically: surface.annotationVariant === "section_header"
                commitOnFocusLoss: surface.annotationVariant !== "section_header"
                onControlStarted: surface._beginInteraction()
                onCommitRequested: function(value) {
                    surface._commitBody(value);
                }
                onCancelRequested: {
                    surface._cancelBodyEdit();
                }
            }
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyDisplayInteractionRegion
            host: surface.host
            targetItem: surface.annotationVariant === "section_header" ? sectionSubtitleText : annotationBodyText
            enabled: !surface.editingBody
                && (surface.annotationVariant === "section_header"
                    ? sectionSubtitleText.visible
                    : annotationBodyText.visible)
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: emptyBodyInteractionRegion
            host: surface.host
            targetItem: bodyBounds
            enabled: !surface.editingBody
                && surface.annotationVariant !== "section_header"
                && surface.bodyValue.length === 0
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyEditorInteractionRegion
            host: surface.host
            targetItem: surface.annotationVariant === "section_header" ? bodyBounds : bodyEditor
            enabled: surface.editingBody
        }
    }

    SurfaceControls.GraphSurfaceDoubleClickTarget {
        id: sectionSubtitleDoubleClickTarget
        host: surface.host
        targetItem: sectionSubtitleText
        enabled: annotationVariant === "section_header"
            && sectionSubtitleText.visible
            && !surface.editingBody
    }

    Connections {
        target: sectionSubtitleDoubleClickTarget

        function onClicked() {
            if (surface.host && surface.host.nodeData)
                surface.host.nodeClicked(String(surface.host.nodeData.node_id || ""), false);
        }

        function onDoubleClicked() {
            surface._beginBodyEdit();
        }
    }

}
