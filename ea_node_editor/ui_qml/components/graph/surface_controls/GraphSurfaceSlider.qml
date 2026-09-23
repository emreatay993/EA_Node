import QtQuick 2.15
import QtQuick.Templates as T
import "SurfaceControlGeometry.js" as SurfaceControlGeometry
import "SurfaceValueFormatter.js" as SurfaceValueFormatter

// Inline "slider" property editor: thin rounded track with accent fill and a
// round knob. Commits on release only (one inlinePropertyCommitted per drag,
// so one undo entry); keyboard/wheel moves commit immediately.
T.Slider {
    id: control
    property Item host: null
    property Item rectItem: control
    property int knobDiameter: 14
    property color accentColor: host ? host.selectedOutlineColor : "#60CDFF"
    property color trackColor: host ? host.inlineInputBorderColor : "#4a4f5a"
    property color knobFillColor: pressed ? "#f0f0f0" : "#fafafa"
    property color knobBorderColor: pressed || hovered ? accentColor : "#b6b8bc"
    property color textColor: host ? host.inlineInputTextColor : "#f0f2f5"
    property color disabledColor: host && typeof host.inlineDrivenTextColor !== "undefined"
        ? host.inlineDrivenTextColor
        : "#95a0b8"
    property int controlHeight: 20
    property bool showRangeCaptions: false
    property bool displayValueAvailable: true
    property string valueType: "float"
    property int continuousPrecision: 3
    property int captionGap: 2
    property bool _pressCommitArmed: false
    property bool _bindingBlocked: false
    readonly property bool interactionActive: pressed || _bindingBlocked
    readonly property var typography: host && host.graphSharedTypography ? host.graphSharedTypography : null
    readonly property int captionPixelSize: {
        var numeric = Number(typography ? typography.inlinePropertyPixelSize : NaN);
        return isFinite(numeric) ? Math.round(numeric) : 10;
    }
    readonly property int captionHeight: Math.max(12, captionPixelSize + 4)
    readonly property int captionReserve: showRangeCaptions ? captionGap + captionHeight : 0
    readonly property string minimumCaptionText: SurfaceValueFormatter.format(
        from,
        valueType,
        stepSize,
        continuousPrecision
    )
    readonly property string currentCaptionText: displayValueAvailable
        ? SurfaceValueFormatter.format(value, valueType, stepSize, continuousPrecision)
        : "\u2014"
    readonly property string maximumCaptionText: SurfaceValueFormatter.format(
        to,
        valueType,
        stepSize,
        continuousPrecision
    )
    readonly property var interactiveRect: SurfaceControlGeometry.rectFromItem(rectItem, host)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(interactiveRect)

    signal controlStarted()
    signal commitRequested(real value)

    implicitWidth: 80
    implicitHeight: Math.max(16, controlHeight) + captionReserve
    padding: 0
    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: captionReserve
    leftInset: 0
    rightInset: 0
    topInset: 0
    bottomInset: 0
    hoverEnabled: enabled
    live: true
    activeFocusOnTab: enabled
    Accessible.name: "Scalar value"
    Accessible.description: "Minimum " + minimumCaptionText
        + ", current " + currentCaptionText
        + ", maximum " + maximumCaptionText + "."

    onPressedChanged: {
        if (pressed) {
            _pressCommitArmed = true;
            _bindingBlocked = true;
            controlStarted();
            return;
        }
        if (_pressCommitArmed) {
            _pressCommitArmed = false;
            commitRequested(control.value);
            Qt.callLater(function() { control._bindingBlocked = false; });
        }
    }

    // Keyboard arrows and wheel change value without a press cycle.
    onMoved: {
        if (!pressed) {
            _bindingBlocked = true;
            commitRequested(control.value);
            Qt.callLater(function() { control._bindingBlocked = false; });
        }
    }

    background: GraphSurfaceSliderTrack {
        objectName: "graphSurfaceSliderTrack"
        x: control.leftPadding
        y: control.topPadding
        width: control.availableWidth
        height: control.availableHeight
        activeStart: control.mirrored ? control.handle.x + control.handle.width * 0.5 - x : 0
        activeEnd: control.mirrored ? width : control.handle.x + control.handle.width * 0.5 - x
        trackColor: control.enabled ? control.trackColor : Qt.alpha(control.disabledColor, 0.42)
        activeColor: control.enabled ? control.accentColor : control.disabledColor
    }

    handle: GraphSurfaceSliderHandle {
        objectName: "graphSurfaceSliderHandle"
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight * 0.5 - height * 0.5
        width: control.knobDiameter
        height: control.knobDiameter
        fillColor: control.enabled ? control.knobFillColor : Qt.alpha(control.disabledColor, 0.28)
        borderColor: control.enabled ? control.knobBorderColor : control.disabledColor
        depthColor: control.enabled ? "#24000000" : "transparent"

        Behavior on borderColor {
            ColorAnimation { duration: 90 }
        }
    }

    Rectangle {
        objectName: "graphSurfaceSliderFocusIndicator"
        anchors.fill: parent
        z: 20
        visible: control.enabled && (control.visualFocus || control.activeFocus)
        color: "transparent"
        radius: Math.max(4, control.knobDiameter * 0.35)
        border.width: 1
        border.color: control.accentColor
    }

    Text {
        objectName: "graphSurfaceSliderMinimumCaption"
        visible: control.showRangeCaptions
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        height: control.captionHeight
        text: control.minimumCaptionText
        color: control.enabled ? control.textColor : control.disabledColor
        font.pixelSize: control.captionPixelSize
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }

    Text {
        objectName: "graphSurfaceSliderCurrentCaption"
        visible: control.showRangeCaptions
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        height: control.captionHeight
        text: control.currentCaptionText
        color: control.enabled ? control.textColor : control.disabledColor
        font.pixelSize: control.captionPixelSize
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }

    Text {
        objectName: "graphSurfaceSliderMaximumCaption"
        visible: control.showRangeCaptions
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: control.captionHeight
        text: control.maximumCaptionText
        color: control.enabled ? control.textColor : control.disabledColor
        font.pixelSize: control.captionPixelSize
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }
}
