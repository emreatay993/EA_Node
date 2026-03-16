import QtQuick 2.15
import QtQuick.Controls 2.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

Button {
    id: control
    property Item host: null
    property Item rectItem: control
    property string iconName: ""
    property int iconSize: 14
    property var iconSourceResolver: null
    property bool externalHover: false
    property color accentColor: "#4DA8DA"
    property color foregroundColor: host ? host.headerTextColor : "#f0f2f5"
    property color baseFillColor: host ? Qt.alpha(host.inlineInputBackgroundColor, 0.92) : "#22242a"
    property color baseBorderColor: host ? Qt.alpha(host.inlineInputBorderColor, 0.92) : "#4a4f5a"
    property color pressedFillColor: Qt.alpha(accentColor, 0.35)
    property color hoverFillColor: Qt.alpha(accentColor, 0.22)
    property color pressedBorderColor: Qt.alpha(accentColor, 0.95)
    property color hoverBorderColor: Qt.alpha(accentColor, 0.85)
    property color disabledForegroundColor: Qt.alpha(foregroundColor, 0.55)
    property real chromeRadius: 6
    property real idleBorderWidth: 1
    property real hoverBorderWidth: 1.5
    property int contentHorizontalPadding: 7
    property int contentVerticalPadding: 4
    readonly property bool hoverVisualActive: hovered || externalHover
    readonly property color resolvedForegroundColor: !enabled
        ? disabledForegroundColor
        : (hoverVisualActive ? accentColor : foregroundColor)
    readonly property color resolvedFillColor: down
        ? pressedFillColor
        : (hoverVisualActive ? hoverFillColor : baseFillColor)
    readonly property color resolvedBorderColor: down
        ? pressedBorderColor
        : (hoverVisualActive ? hoverBorderColor : baseBorderColor)
    readonly property real resolvedBorderWidth: hoverVisualActive ? hoverBorderWidth : idleBorderWidth
    readonly property string resolvedIconSource: {
        if (typeof iconSourceResolver !== "function")
            return "";
        return String(iconSourceResolver(iconName, iconSize, String(resolvedForegroundColor)) || "");
    }
    readonly property var interactiveRect: SurfaceControlGeometry.rectFromItem(rectItem, host)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(interactiveRect)

    signal controlStarted()

    implicitHeight: Math.max(24, contentRow.implicitHeight + contentVerticalPadding * 2)
    implicitWidth: Math.max(28, contentRow.implicitWidth + contentHorizontalPadding * 2)
    padding: 0
    hoverEnabled: true
    focusPolicy: Qt.NoFocus

    onPressedChanged: {
        if (pressed)
            controlStarted();
    }

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: control.text.length > 0 && iconImage.visible ? 6 : 0

            Image {
                id: iconImage
                visible: control.resolvedIconSource.length > 0
                source: control.resolvedIconSource
                width: control.iconSize
                height: control.iconSize
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true
                sourceSize.width: control.iconSize
                sourceSize.height: control.iconSize
            }

            Text {
                visible: control.text.length > 0
                text: control.text
                color: control.resolvedForegroundColor
                font.pixelSize: 10
                font.bold: true
                verticalAlignment: Text.AlignVCenter
                renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }

    background: Rectangle {
        radius: control.chromeRadius
        color: control.resolvedFillColor
        border.width: control.resolvedBorderWidth
        border.color: control.resolvedBorderColor
    }
}
