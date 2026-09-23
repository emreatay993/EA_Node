import QtQuick 2.15
import QtQuick.Templates as T
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

T.CheckBox {
    id: control
    property Item host: null
    property Item rectItem: control
    property color textColor: host ? host.inlineInputTextColor : "#f0f2f5"
    property color fillColor: host ? host.inlineInputBackgroundColor : "#22242a"
    property color borderColor: host ? host.inlineInputBorderColor : "#4a4f5a"
    property color accentColor: host ? host.selectedOutlineColor : "#60CDFF"
    property color indicatorCheckColor: host ? host.surfaceColor : "#1b1d22"
    property real switchTrackWidth: 28
    property real switchTrackHeight: 14
    property color disabledTextColor: Qt.alpha(textColor, 0.58)
    readonly property color resolvedTextColor: enabled ? textColor : disabledTextColor
    readonly property color resolvedIndicatorFillColor: enabled
        ? (checked ? accentColor : fillColor)
        : (host && typeof host.inlineRowColor !== "undefined"
            ? host.inlineRowColor
            : Qt.darker(fillColor, 1.08))
    readonly property color resolvedIndicatorBorderColor: enabled
        ? (checked ? accentColor : borderColor)
        : disabledTextColor
    readonly property var typography: host && host.graphSharedTypography ? host.graphSharedTypography : null
    readonly property int inlineFontPixelSize: {
        var numeric = Number(typography ? typography.inlinePropertyPixelSize : NaN);
        return isFinite(numeric) ? Math.round(numeric) : 10;
    }
    readonly property int inlineFontWeight: {
        var numeric = Number(typography ? typography.inlinePropertyFontWeight : NaN);
        return isFinite(numeric) ? Math.round(numeric) : Font.Normal;
    }
    readonly property var interactiveRect: SurfaceControlGeometry.rectFromItem(rectItem, host)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(interactiveRect)

    signal controlStarted()

    implicitWidth: Math.max(switchTrackWidth, implicitContentWidth)
    implicitHeight: Math.max(switchTrackHeight, implicitContentHeight)
    spacing: 6
    padding: 0
    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0
    leftInset: 0
    rightInset: 0
    topInset: 0
    bottomInset: 0
    font.pixelSize: inlineFontPixelSize
    font.weight: inlineFontWeight
    hoverEnabled: enabled
    activeFocusOnTab: enabled
    Accessible.name: text.length ? text : "Boolean value"

    onPressedChanged: {
        if (pressed)
            controlStarted();
    }

    // Pill toggle switch: track keeps the checked\u2192accent fill/border
    // semantics exported via resolvedIndicator*Color (pinned by
    // tests/test_graph_surface_input_controls.py), knob slides left/right.
    indicator: GraphSurfaceCapsule {
        objectName: "graphSurfaceSwitchTrack"
        implicitWidth: control.switchTrackWidth
        implicitHeight: control.switchTrackHeight
        width: control.switchTrackWidth
        height: control.switchTrackHeight
        x: control.mirrored ? control.width - control.rightPadding - width : control.leftPadding
        y: control.topPadding + (control.availableHeight - height) * 0.5
        fillColor: control.resolvedIndicatorFillColor
        borderWidth: 1
        borderColor: control.enabled && (control.hovered || control.pressed)
            ? control.accentColor : control.resolvedIndicatorBorderColor

        GraphSurfaceCapsule {
            objectName: "graphSurfaceSwitchKnob"
            width: Math.max(0, parent.height - 4)
            height: width
            anchors.verticalCenter: parent.verticalCenter
            x: control.checked !== control.mirrored ? parent.width - width - 2 : 2
            fillColor: !control.enabled
                ? control.disabledTextColor
                : (control.checked
                ? control.indicatorCheckColor
                : Qt.alpha(control.textColor, 0.75))

            Behavior on x {
                NumberAnimation {
                    duration: 110
                    easing.type: Easing.OutCubic
                }
            }
        }
    }

    contentItem: Text {
        text: control.text
        color: control.resolvedTextColor
        font.pixelSize: control.font.pixelSize
        font.weight: control.font.weight
        leftPadding: !control.mirrored && control.text.length ? control.indicator.width + control.spacing : 0
        rightPadding: control.mirrored && control.text.length ? control.indicator.width + control.spacing : 0
        verticalAlignment: Text.AlignVCenter
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }

    Rectangle {
        objectName: "graphSurfaceSwitchFocusIndicator"
        anchors.fill: parent
        visible: control.enabled && (control.visualFocus || control.activeFocus)
        color: "transparent"
        radius: 3
        border.width: 1
        border.color: control.accentColor
    }
}
