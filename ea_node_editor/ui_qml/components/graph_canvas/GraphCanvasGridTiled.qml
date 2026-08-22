import QtQuick 2.15
import QtQuick.Window 2.15

Item {
    id: root
    objectName: "graphCanvasGridTiledRenderer"

    property bool gridVisible: true
    property string gridStyle: "lines"
    property color minorGridColor: "#2b3440"
    property color majorGridColor: "#3f4d5f"
    property real minorStep: 20.0
    property real majorStep: 100.0
    property real minorOffsetX: 0.0
    property real minorOffsetY: 0.0
    property real majorOffsetX: 0.0
    property real majorOffsetY: 0.0
    property real minorPointSize: 1.75
    property real majorPointSize: 2.75
    property real devicePixelRatio: Screen.devicePixelRatio
    property int updateRevision: 0

    readonly property real effectiveDevicePixelRatio: root._positiveNumber(root.devicePixelRatio, 1.0)
    readonly property real linePixelSize: Math.max(0.25, 1.0 / root.effectiveDevicePixelRatio)
    readonly property real minorPointPixelSize: Math.max(root.linePixelSize, root.minorPointSize / root.effectiveDevicePixelRatio)
    readonly property real majorPointPixelSize: Math.max(root.linePixelSize, root.majorPointSize / root.effectiveDevicePixelRatio)
    readonly property real _minorStep: root._positiveNumber(root.minorStep, 0.0)
    readonly property real _majorStep: root._positiveNumber(root.majorStep, 0.0)
    readonly property real _minorOffsetX: root._normalizedOffset(root.minorOffsetX, root._minorStep)
    readonly property real _minorOffsetY: root._normalizedOffset(root.minorOffsetY, root._minorStep)
    readonly property real _majorOffsetX: root._normalizedOffset(root.majorOffsetX, root._majorStep)
    readonly property real _majorOffsetY: root._normalizedOffset(root.majorOffsetY, root._majorStep)
    readonly property bool effectiveGridVisible: root.gridVisible
        && root.width > 0.0
        && root.height > 0.0
        && root._minorStep > 0.0
        && root._majorStep > 0.0
    readonly property bool pointStyle: root.gridStyle === "points"
    readonly property int minorColumnCount: root.effectiveGridVisible ? root._countAlong(root.width, root._minorOffsetX, root._minorStep) : 0
    readonly property int minorRowCount: root.effectiveGridVisible ? root._countAlong(root.height, root._minorOffsetY, root._minorStep) : 0
    readonly property int majorColumnCount: root.effectiveGridVisible ? root._countAlong(root.width, root._majorOffsetX, root._majorStep) : 0
    readonly property int majorRowCount: root.effectiveGridVisible ? root._countAlong(root.height, root._majorOffsetY, root._majorStep) : 0
    readonly property int profileGridMinorItemCount: root.effectiveGridVisible
        ? (root.pointStyle ? (root.minorRowCount + root.minorRowCount * root.minorColumnCount) : (root.minorColumnCount + root.minorRowCount))
        : 0
    readonly property int profileGridMajorItemCount: root.effectiveGridVisible
        ? (root.pointStyle ? (root.majorRowCount + root.majorRowCount * root.majorColumnCount) : (root.majorColumnCount + root.majorRowCount))
        : 0
    readonly property int profileGridItemCount: root.profileGridMinorItemCount + root.profileGridMajorItemCount
    readonly property int profileGridRowCount: root.minorRowCount + root.majorRowCount
    readonly property int profileGridColumnCount: root.minorColumnCount + root.majorColumnCount

    function _positiveNumber(value, fallback) {
        var number = Number(value);
        if (!isFinite(number) || number <= 0.0)
            return fallback;
        return number;
    }

    function _normalizedOffset(offset, step) {
        if (!(step > 0.0))
            return 0.0;
        var value = Number(offset);
        if (!isFinite(value))
            return 0.0;
        while (value < 0.0)
            value += step;
        while (value >= step)
            value -= step;
        return value;
    }

    function _countAlong(length, offset, step) {
        if (!(length > 0.0) || !(step > 0.0))
            return 0;
        var count = Math.ceil((length - offset) / step) + 1;
        return Math.max(0, Math.min(4096, count));
    }

    Item {
        id: lineGrid
        anchors.fill: parent
        visible: root.effectiveGridVisible && !root.pointStyle

        Repeater {
            model: lineGrid.visible ? root.minorColumnCount : 0

            Rectangle {
                x: Math.round(root._minorOffsetX + index * root._minorStep) - root.linePixelSize * 0.5
                y: 0.0
                width: root.linePixelSize
                height: root.height
                color: root.minorGridColor
                antialiasing: false
            }
        }

        Repeater {
            model: lineGrid.visible ? root.minorRowCount : 0

            Rectangle {
                x: 0.0
                y: Math.round(root._minorOffsetY + index * root._minorStep) - root.linePixelSize * 0.5
                width: root.width
                height: root.linePixelSize
                color: root.minorGridColor
                antialiasing: false
            }
        }

        Repeater {
            model: lineGrid.visible ? root.majorColumnCount : 0

            Rectangle {
                x: Math.round(root._majorOffsetX + index * root._majorStep) - root.linePixelSize * 0.5
                y: 0.0
                width: root.linePixelSize
                height: root.height
                color: root.majorGridColor
                antialiasing: false
            }
        }

        Repeater {
            model: lineGrid.visible ? root.majorRowCount : 0

            Rectangle {
                x: 0.0
                y: Math.round(root._majorOffsetY + index * root._majorStep) - root.linePixelSize * 0.5
                width: root.width
                height: root.linePixelSize
                color: root.majorGridColor
                antialiasing: false
            }
        }
    }

    Item {
        id: pointGrid
        anchors.fill: parent
        visible: root.effectiveGridVisible && root.pointStyle

        Repeater {
            model: pointGrid.visible ? root.minorRowCount : 0

            Item {
                width: root.width
                height: root.minorPointPixelSize
                y: root._minorOffsetY + index * root._minorStep - root.minorPointPixelSize * 0.5

                Repeater {
                    model: root.minorColumnCount

                    Rectangle {
                        x: root._minorOffsetX + index * root._minorStep - root.minorPointPixelSize * 0.5
                        y: 0.0
                        width: root.minorPointPixelSize
                        height: root.minorPointPixelSize
                        radius: 0.0
                        color: root.minorGridColor
                        antialiasing: false
                    }
                }
            }
        }

        Repeater {
            model: pointGrid.visible ? root.majorRowCount : 0

            Item {
                width: root.width
                height: root.majorPointPixelSize
                y: root._majorOffsetY + index * root._majorStep - root.majorPointPixelSize * 0.5

                Repeater {
                    model: root.majorColumnCount

                    Rectangle {
                        x: root._majorOffsetX + index * root._majorStep - root.majorPointPixelSize * 0.5
                        y: 0.0
                        width: root.majorPointPixelSize
                        height: root.majorPointPixelSize
                        radius: 0.0
                        color: root.majorGridColor
                        antialiasing: false
                    }
                }
            }
        }
    }
}
