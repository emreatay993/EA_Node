import QtQuick 2.15
import QtQuick.Controls 2.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

TextArea {
    id: control
    property Item host: null
    property Item rectItem: control
    property color textColor: host ? host.inlineInputTextColor : "#f0f2f5"
    property color fillColor: host ? host.inlineInputBackgroundColor : "#22242a"
    property color borderColor: host ? host.inlineInputBorderColor : "#4a4f5a"
    property color focusBorderColor: host ? host.selectedOutlineColor : "#60CDFF"
    property color disabledTextColor: Qt.alpha(textColor, 0.58)
    readonly property color resolvedTextColor: enabled ? textColor : disabledTextColor
    readonly property color resolvedBackgroundColor: fillColor
    readonly property color resolvedBorderColor: activeFocus ? focusBorderColor : borderColor
    readonly property var interactiveRect: SurfaceControlGeometry.rectFromItem(rectItem, host)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(interactiveRect)

    signal controlStarted()

    implicitHeight: 74
    padding: 6
    wrapMode: TextEdit.Wrap
    selectByMouse: true
    color: resolvedTextColor
    selectionColor: focusBorderColor
    selectedTextColor: host ? host.surfaceColor : "#1b1d22"

    onActiveFocusChanged: {
        if (activeFocus)
            controlStarted();
    }

    background: Rectangle {
        radius: 6
        color: control.resolvedBackgroundColor
        border.width: 1
        border.color: control.resolvedBorderColor
    }
}
