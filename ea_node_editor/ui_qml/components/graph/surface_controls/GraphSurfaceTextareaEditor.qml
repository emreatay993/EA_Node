import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: root
    property Item host: null
    property alias fieldFont: textareaField.font
    property alias fieldFillColor: textareaField.fillColor
    property alias fieldBorderColor: textareaField.borderColor
    property alias fieldFocusBorderColor: textareaField.focusBorderColor
    property alias fieldTextColor: textareaField.textColor
    property alias fieldLeftPadding: textareaField.leftPadding
    property alias fieldRightPadding: textareaField.rightPadding
    property alias fieldTopPadding: textareaField.topPadding
    property alias fieldBottomPadding: textareaField.bottomPadding
    property bool showActionButtons: true
    property string propertyKey: ""
    property string committedText: ""
    property string fieldObjectName: "graphSurfaceTextareaField"
    property string applyButtonObjectName: "graphSurfaceTextareaApplyButton"
    property string resetButtonObjectName: "graphSurfaceTextareaResetButton"
    readonly property string draftText: textareaField.text
    readonly property bool dirty: draftText !== committedText
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [
            textareaField.embeddedInteractiveRects,
            root.showActionButtons ? applyButton.embeddedInteractiveRects : [],
            root.showActionButtons ? resetButton.embeddedInteractiveRects : []
        ]
    )
    implicitWidth: editorColumn.implicitWidth
    implicitHeight: editorColumn.implicitHeight

    signal controlStarted()
    signal commitRequested(string text)

    function syncDraftToCommitted() {
        if (textareaField.text !== committedText)
            textareaField.text = committedText;
    }

    function resetDraft() {
        syncDraftToCommitted();
    }

    function commitDraft() {
        commitRequested(textareaField.text);
    }

    function activateEditor() {
        textareaField.forceActiveFocus();
        textareaField.cursorPosition = textareaField.length;
        textareaField.deselect();
    }

    onCommittedTextChanged: {
        if (!textareaField.activeFocus || !dirty)
            syncDraftToCommitted();
    }

    Component.onCompleted: syncDraftToCommitted()

    ColumnLayout {
        id: editorColumn
        anchors.fill: parent
        spacing: 6

        GraphSurfaceTextArea {
            id: textareaField
            objectName: root.fieldObjectName
            property string propertyKey: root.propertyKey
            Layout.fillWidth: true
            visible: root.visible
            enabled: root.enabled
            host: root.host
            onControlStarted: root.controlStarted()
            Keys.onPressed: function(event) {
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                        && (event.modifiers & Qt.ControlModifier)) {
                    root.commitDraft();
                    event.accepted = true;
                } else if (event.key === Qt.Key_Escape) {
                    root.resetDraft();
                    event.accepted = true;
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            GraphSurfaceButton {
                id: applyButton
                objectName: root.applyButtonObjectName
                property string propertyKey: root.propertyKey
                visible: root.visible && root.showActionButtons
                enabled: root.showActionButtons && root.enabled && root.dirty
                host: root.host
                text: "Apply"
                onControlStarted: root.controlStarted()
                onClicked: root.commitDraft()
            }

            GraphSurfaceButton {
                id: resetButton
                objectName: root.resetButtonObjectName
                property string propertyKey: root.propertyKey
                visible: root.visible && root.showActionButtons
                enabled: root.showActionButtons && root.enabled && root.dirty
                host: root.host
                text: "Reset"
                onControlStarted: root.controlStarted()
                onClicked: root.resetDraft()
            }

            Text {
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
                text: root.dirty ? "Ctrl+Enter to commit" : "Committed"
                color: root.host ? root.host.inlineDrivenTextColor : "#bdc5d3"
                font.pixelSize: root.host && root.host.graphSharedTypography
                    ? root.host.graphSharedTypography.inlinePropertyPixelSize
                    : 10
                elide: Text.ElideRight
                renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }
}
