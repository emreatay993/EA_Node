import QtQuick 2.15
import QtQuick.Controls 2.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

ComboBox {
    id: control
    property Item host: null
    property Item rectItem: control
    property color textColor: host ? host.inlineInputTextColor : "#f0f2f5"
    property color fillColor: host ? host.inlineInputBackgroundColor : "#22242a"
    property color borderColor: host ? host.inlineInputBorderColor : "#4a4f5a"
    property color focusBorderColor: host ? host.selectedOutlineColor : "#60CDFF"
    property color accentColor: host ? host.selectedOutlineColor : "#60CDFF"
    property color popupFillColor: Qt.darker(fillColor, 1.04)
    property color popupBorderColor: borderColor
    property color disabledTextColor: Qt.alpha(textColor, 0.58)
    readonly property color resolvedTextColor: enabled ? textColor : disabledTextColor
    readonly property color resolvedBackgroundColor: fillColor
    readonly property color resolvedBorderColor: (visualFocus || popup.visible) ? focusBorderColor : borderColor
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

    padding: 0
    leftPadding: 8
    rightPadding: 24
    font.pixelSize: inlineFontPixelSize
    font.weight: inlineFontWeight
    hoverEnabled: true

    onPressedChanged: {
        if (pressed)
            controlStarted();
    }

    contentItem: Text {
        leftPadding: control.leftPadding
        rightPadding: control.rightPadding
        text: control.displayText
        color: control.resolvedTextColor
        font.pixelSize: control.font.pixelSize
        font.weight: control.font.weight
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }

    indicator: Text {
        text: "\u25BE"
        color: control.resolvedTextColor
        font.pixelSize: control.font.pixelSize
        font.weight: control.font.weight
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
    }

    background: Rectangle {
        radius: 3
        color: control.resolvedBackgroundColor
        border.width: 1
        border.color: control.resolvedBorderColor
    }

    delegate: ItemDelegate {
        width: control.width
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            text: modelData
            color: control.resolvedTextColor
            font.pixelSize: control.font.pixelSize
            font.weight: control.font.weight
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            renderType: control.host ? control.host.nodeTextRenderType : Text.CurveRendering
        }
        background: Rectangle {
            color: highlighted ? Qt.alpha(control.accentColor, 0.18) : control.popupFillColor
        }
    }

    popup: Popup {
        y: control.height + 2
        width: control.width
        padding: 1
        implicitHeight: Math.min(contentItem.implicitHeight + padding * 2, 160)

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
        }

        background: Rectangle {
            radius: 4
            color: control.popupFillColor
            border.width: 1
            border.color: control.popupBorderColor
        }
    }
}
