import QtQuick 2.15
import QtQuick.Controls 2.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

CheckBox {
    id: control
    property Item host: null
    property Item rectItem: control
    property color textColor: host ? host.inlineInputTextColor : "#f0f2f5"
    property color fillColor: host ? host.inlineInputBackgroundColor : "#22242a"
    property color borderColor: host ? host.inlineInputBorderColor : "#4a4f5a"
    property color accentColor: host ? host.selectedOutlineColor : "#60CDFF"
    property color indicatorCheckColor: host ? host.surfaceColor : "#1b1d22"
    property color disabledTextColor: Qt.alpha(textColor, 0.58)
    readonly property color resolvedTextColor: enabled ? textColor : disabledTextColor
    readonly property color resolvedIndicatorFillColor: checked ? accentColor : fillColor
    readonly property color resolvedIndicatorBorderColor: checked ? accentColor : borderColor
    readonly property var interactiveRect: SurfaceControlGeometry.rectFromItem(rectItem, host)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(interactiveRect)

    signal controlStarted()

    spacing: 6
    padding: 0
    hoverEnabled: true

    onPressedChanged: {
        if (pressed)
            controlStarted();
    }

    indicator: Rectangle {
        implicitWidth: 14
        implicitHeight: 14
        radius: 3
        color: control.resolvedIndicatorFillColor
        border.width: 1
        border.color: control.resolvedIndicatorBorderColor
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            visible: control.checked
            text: "\u2713"
            color: control.indicatorCheckColor
            font.pixelSize: 10
            font.bold: true
            renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
        }
    }

    contentItem: Text {
        text: control.text
        color: control.resolvedTextColor
        font.pixelSize: 10
        leftPadding: control.indicator.width + control.spacing
        verticalAlignment: Text.AlignVCenter
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }
}
