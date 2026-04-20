import QtQuick 2.15
import QtQuick.Layouts 1.15
import "SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: root
    property Item host: null
    property string propertyKey: ""
    property string committedText: ""
    property string fieldObjectName: "graphSurfacePathEditorField"
    property string browseButtonObjectName: "graphSurfacePathEditorBrowseButton"
    property string browseButtonText: "Browse"
    property var browsePathResolver: null
    readonly property string text: pathField.text
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [pathField.embeddedInteractiveRects, browseButton.embeddedInteractiveRects]
    )
    implicitWidth: editorRow.implicitWidth
    implicitHeight: editorRow.implicitHeight

    signal controlStarted()
    signal commitRequested(string text)

    function _resolveBrowsePath(currentPath) {
        if (typeof browsePathResolver !== "function")
            return "";
        return String(browsePathResolver(String(currentPath || "")) || "");
    }

    function syncTextToCommitted() {
        if (pathField.text !== committedText)
            pathField.text = committedText;
    }

    onCommittedTextChanged: {
        if (!pathField.activeFocus)
            syncTextToCommitted();
    }

    Component.onCompleted: syncTextToCommitted()

    RowLayout {
        id: editorRow
        anchors.fill: parent
        spacing: 6

        GraphSurfaceTextField {
            id: pathField
            objectName: root.fieldObjectName
            property string propertyKey: root.propertyKey
            Layout.fillWidth: true
            visible: root.visible
            enabled: root.enabled
            host: root.host
            // Read-only hint shown when no path is set yet; disappears as
            // soon as the user types or a path is committed.
            placeholderText: "..."
            onControlStarted: root.controlStarted()
            onAccepted: root.commitRequested(text)
            onEditingFinished: root.commitRequested(text)
        }

        GraphSurfaceButton {
            id: browseButton
            objectName: root.browseButtonObjectName
            property string propertyKey: root.propertyKey
            visible: root.visible
            enabled: root.enabled
            host: root.host
            text: root.browseButtonText
            onControlStarted: root.controlStarted()
            onClicked: {
                var selectedPath = root._resolveBrowsePath(pathField.text);
                if (!selectedPath.length)
                    return;
                if (pathField.text !== selectedPath)
                    pathField.text = selectedPath;
                root.commitRequested(pathField.text);
            }
        }
    }
}
