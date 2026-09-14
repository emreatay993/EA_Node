// Purpose: Themed member/schema selector supporting virtual archive models and draft display text.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15

ComboBox {
    id: control
    implicitWidth: 160
    implicitHeight: 36
    leftPadding: 11
    rightPadding: 30
    hoverEnabled: true
    font.pixelSize: 12
    contentItem: Text {
        text: control.displayText
        font: control.font
        color: control.enabled ? control.palette.text : control.palette.placeholderText
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideMiddle
    }
    indicator: Item {
        anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
        width: 10; height: 8
        Rectangle { x: 1; y: 3; width: 6; height: 1.5; radius: 0.75; rotation: 45; color: control.palette.placeholderText }
        Rectangle { x: 5; y: 3; width: 6; height: 1.5; radius: 0.75; rotation: -45; color: control.palette.placeholderText }
    }
    background: Rectangle {
        radius: 7; color: control.palette.base
        border.color: control.activeFocus ? control.palette.highlight : control.palette.mid
        border.width: control.activeFocus ? 2 : 1
    }
    delegate: ItemDelegate {
        required property int index
        width: ListView.view ? ListView.view.width : control.width
        height: 34
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            text: control.textAt(index); font.pixelSize: 12; elide: Text.ElideMiddle
            color: control.palette.text; verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle { radius: 5; color: highlighted ? Qt.alpha(control.palette.highlight, 0.15) : "transparent" }
    }
    popup: Popup {
        y: control.height + 5; width: control.width; padding: 5
        background: Rectangle { radius: 9; color: control.palette.base; border.color: control.palette.mid }
        contentItem: ListView {
            clip: true; implicitHeight: Math.min(contentHeight, 280)
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { }
        }
    }
}
