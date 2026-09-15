// Purpose: Compact, controlled zoom editor for toolbars and status bars.
// Map: docs/agent_maps/subsystems/qml_shell_and_bridges.md
// Tests: tests/qml_quick/tst_zoom_control.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // The parent owns zoom. Requests never overwrite this input binding.
    property real zoom: 100
    property real minZoom: 10
    property real maxZoom: 500
    property real defaultZoom: 100
    property bool showPercentSymbol: false
    property bool editableValue: true
    property int zoomDecimals: 0
    property real sliderStep: 1
    property real keyboardStep: 10
    property real wheelStep: 10
    property int sliderWidth: 110
    property var themePalette: ({})
    readonly property color foreground: themePalette.muted_fg || "#aeb4bf"
    readonly property color accent: themePalette.accent || "#60cdff"
    readonly property color trackColor: themePalette.input_border || themePalette.border || "#4a4f5a"
    readonly property string formattedZoom: Number(zoom).toFixed(Math.max(0, Math.min(6, zoomDecimals)))
        + (showPercentSymbol ? "%" : "")

    signal zoomRequested(real percent)
    signal zoomStarted()
    signal zoomFinished()

    implicitWidth: row.implicitWidth
    implicitHeight: 24
    opacity: enabled ? 1 : 0.5

    function setZoom(value) {
        var numeric = Number(value);
        if (!isFinite(numeric))
            return;
        var clamped = Math.max(minZoom, Math.min(maxZoom, numeric));
        if (Math.abs(clamped - zoom) > 0.000001)
            zoomRequested(clamped);
    }
    function zoomIn() { setZoom(zoom + keyboardStep); }
    function zoomOut() { setZoom(zoom - keyboardStep); }
    function resetZoom() { setZoom(defaultZoom); }

    function restoreEditor() {
        valueField.dirty = false;
        valueField.text = formattedZoom;
    }
    function commitEditor() {
        if (!valueField.dirty)
            return;
        var input = valueField.text.trim();
        // Validate the whole entry; do not accept numeric prefixes of junk.
        if (/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*%?$/.test(input)) {
            zoomStarted();
            setZoom(Number(input.replace(/\s*%$/, "")));
            zoomFinished();
        }
        restoreEditor();
    }

    // External wheel, fit, reset, and workspace changes also replace stale drafts.
    onZoomChanged: restoreEditor()
    onFormattedZoomChanged: restoreEditor()
    Component.onCompleted: restoreEditor()

    RowLayout {
        id: row
        anchors.fill: parent
        spacing: 6

        Text {
            text: qsTr("Zoom")
            color: root.foreground
            font.pixelSize: 11
            Layout.alignment: Qt.AlignVCenter
        }

        Slider {
            id: slider
            objectName: "zoomControlSlider"
            Layout.preferredWidth: root.sliderWidth
            Layout.preferredHeight: root.implicitHeight
            from: root.minZoom
            to: root.maxZoom
            value: root.zoom
            stepSize: root.sliderStep
            snapMode: Slider.SnapAlways
            live: true
            padding: 5
            hoverEnabled: true
            wheelEnabled: false
            Accessible.name: qsTr("Viewport zoom")
            Accessible.description: Number(root.zoom).toFixed(root.zoomDecimals) + qsTr(" percent")

            onPressedChanged: {
                if (pressed) root.zoomStarted();
                else root.zoomFinished();
            }
            onMoved: {
                if (!pressed) root.zoomStarted();
                root.setZoom(value);
                if (!pressed) root.zoomFinished();
            }
            Keys.onLeftPressed: root.zoomOut()
            Keys.onRightPressed: root.zoomIn()
            Keys.onDownPressed: root.zoomOut()
            Keys.onUpPressed: root.zoomIn()
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Home) {
                    root.resetZoom();
                    event.accepted = true;
                }
            }

            background: Rectangle {
                x: slider.leftPadding
                y: (slider.height - height) / 2
                width: slider.availableWidth
                height: 2
                radius: 1
                color: root.trackColor
            }
            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                y: (slider.height - height) / 2
                width: 10
                height: 10
                radius: 5
                color: slider.pressed ? root.accent : (root.themePalette.input_bg || "#22242a")
                border.width: 1
                border.color: slider.hovered || slider.activeFocus ? root.accent : root.foreground
            }
            WheelHandler {
                onWheel: function(event) {
                    root.zoomStarted();
                    root.setZoom(root.zoom * Math.pow(1 + root.wheelStep / 100, event.angleDelta.y / 120));
                    root.zoomFinished();
                    event.accepted = true;
                }
            }
        }

        TextField {
            id: valueField
            objectName: "zoomControlValue"
            property bool dirty: false
            Layout.preferredWidth: root.zoomDecimals > 0 ? 55 : 45
            Layout.preferredHeight: root.implicitHeight
            Layout.leftMargin: 2
            readOnly: !root.editableValue
            selectByMouse: true
            hoverEnabled: true
            leftPadding: 3
            rightPadding: 3
            topPadding: 0
            bottomPadding: 0
            horizontalAlignment: TextInput.AlignHCenter
            verticalAlignment: TextInput.AlignVCenter
            color: root.themePalette.input_fg || root.foreground
            font.pixelSize: 11
            Accessible.name: qsTr("Zoom percentage")
            Accessible.description: qsTr("Enter a zoom percentage. Right-click for Reset Zoom.")
            onTextEdited: dirty = true
            onAccepted: root.commitEditor()
            onEditingFinished: root.commitEditor()
            Keys.onEscapePressed: root.restoreEditor()
            background: Rectangle {
                color: valueField.activeFocus ? (root.themePalette.input_bg || "#22242a") : "transparent"
                radius: 2
                border.width: 1
                border.color: valueField.activeFocus ? root.accent
                    : (valueField.hovered && root.editableValue ? root.trackColor : "transparent")
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: resetMenu.popup()
    }
    Menu {
        id: resetMenu
        objectName: "zoomControlMenu"
        MenuItem {
            text: qsTr("Reset Zoom")
            onTriggered: root.resetZoom()
        }
    }
}
