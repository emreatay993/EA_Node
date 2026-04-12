import QtQuick 2.15
import QtQuick.Controls 2.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

TextField {
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
    readonly property var typography: host && host.graphSharedTypography ? host.graphSharedTypography : null
    readonly property int inlineFontPixelSize: {
        var numeric = Number(typography ? typography.inlinePropertyPixelSize : NaN);
        return isFinite(numeric) ? Math.round(numeric) : 10;
    }
    readonly property int inlineFontWeight: {
        var numeric = Number(typography ? typography.inlinePropertyFontWeight : NaN);
        return isFinite(numeric) ? Math.round(numeric) : Font.Normal;
    }
    readonly property real verticalTextPadding: {
        var fieldHeight = Number(control.height);
        var contentHeight = Number(control.contentHeight);
        if (!isFinite(fieldHeight) || fieldHeight <= 0 || !isFinite(contentHeight) || contentHeight <= 0)
            return 3;
        return Math.max(3, Math.floor((fieldHeight - contentHeight) * 0.5));
    }
    readonly property var interactiveRect: SurfaceControlGeometry.rectFromItem(rectItem, host)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(interactiveRect)

    signal controlStarted()

    padding: 0
    leftPadding: 8
    rightPadding: 8
    topPadding: verticalTextPadding
    bottomPadding: verticalTextPadding
    selectByMouse: true
    color: resolvedTextColor
    selectionColor: focusBorderColor
    selectedTextColor: host ? host.surfaceColor : "#1b1d22"
    font.pixelSize: inlineFontPixelSize
    font.weight: inlineFontWeight
    renderType: host ? host.nodeTextRenderType : Text.CurveRendering

    onActiveFocusChanged: {
        if (activeFocus)
            controlStarted();
    }

    background: Rectangle {
        radius: 3
        color: control.resolvedBackgroundColor
        border.width: 1
        border.color: control.resolvedBorderColor
    }
}
