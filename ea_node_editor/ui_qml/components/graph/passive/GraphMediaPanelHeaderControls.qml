import QtQuick 2.15
import "../surface_controls" as GraphSurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: root
    property var surface: null
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [cropButton.embeddedInteractiveRects, repairButton.embeddedInteractiveRects]
    )

    GraphSurfaceControls.GraphSurfaceButton {
        id: cropButton
        objectName: "graphNodeMediaCropButton"
        z: 6
        host: root.surface ? root.surface.host : null
        visible: root.surface ? root.surface.cropButtonVisible : false
        enabled: visible
        iconName: "crop"
        iconSize: 14
        iconSourceResolver: function(name, size, color) {
            return root.surface ? root.surface._iconSource(name, size, color) : "";
        }
        accentColor: "#4DA8DA"
        foregroundColor: root.surface ? root.surface.cropButtonIconColor : "#f0f2f5"
        baseFillColor: Qt.alpha(root.surface ? root.surface.panelFillColor : "#1b1d22", 0.82)
        baseBorderColor: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.82)
        anchors.right: parent.right
        anchors.rightMargin: 10
        y: root.surface && root.surface.host
            ? Number(root.surface.host.surfaceMetrics.title_top || 0)
                + Math.max(0, (Number(root.surface.host.surfaceMetrics.title_height || 24) - height) * 0.5)
            : 6
        implicitWidth: 28
        text: ""
        onControlStarted: root.surface._beginInlineInteraction()
        onClicked: root.surface.triggerHoverAction()
    }

    GraphSurfaceControls.GraphSurfaceButton {
        id: repairButton
        objectName: "graphNodeMediaRepairButton"
        z: 6
        host: root.surface ? root.surface.host : null
        visible: root.surface ? root.surface.fileIssueActive : false
        enabled: visible
        text: "Repair file..."
        accentColor: "#D98B4B"
        foregroundColor: root.surface ? root.surface.cropButtonIconColor : "#f0f2f5"
        baseFillColor: Qt.alpha(root.surface ? root.surface.panelFillColor : "#1b1d22", 0.88)
        baseBorderColor: Qt.alpha("#D98B4B", 0.78)
        anchors.right: parent.right
        anchors.rightMargin: 10
        y: root.surface && root.surface.host
            ? Number(root.surface.host.surfaceMetrics.title_top || 0)
                + Math.max(0, (Number(root.surface.host.surfaceMetrics.title_height || 24) - height) * 0.5)
            : 6
        onControlStarted: root.surface._beginInlineInteraction()
        onClicked: root.surface.repairFile()
    }

    Rectangle {
        id: issueBadge
        objectName: "graphNodeMediaIssueBadge"
        z: 5
        visible: !!root.surface && root.surface.fileIssueActive
        anchors.right: repairButton.visible ? repairButton.left : parent.right
        anchors.rightMargin: repairButton.visible ? 8 : 10
        y: root.surface && root.surface.host
            ? Number(root.surface.host.surfaceMetrics.title_top || 0)
                + Math.max(0, (Number(root.surface.host.surfaceMetrics.title_height || 24) - height) * 0.5)
            : 6
        radius: 10
        color: Qt.alpha("#D98B4B", 0.22)
        border.width: 1
        border.color: Qt.alpha("#D98B4B", 0.72)
        height: issueBadgeLabel.implicitHeight + 10
        width: issueBadgeLabel.implicitWidth + 16

        Text {
            id: issueBadgeLabel
            anchors.centerIn: parent
            text: "Missing file"
            color: root.surface ? root.surface.cropButtonIconColor : "#F4F8FC"
            font.pixelSize: 10
            font.bold: true
            renderType: root.surface && root.surface.host
                ? root.surface.host.nodeTextRenderType
                : Text.CurveRendering
        }
    }

    Rectangle {
        id: pdfPageBadge
        objectName: "graphNodeMediaPageBadge"
        z: 5
        visible: !!root.surface
            && root.surface.isPdfPanel
            && root.surface.previewState === "ready"
            && root.surface.pdfPageCount > 0
        anchors.right: parent.right
        anchors.rightMargin: root.surface && root.surface.host
            ? Number(root.surface.host.surfaceMetrics.title_right_margin || 10)
            : 10
        y: root.surface && root.surface.host
            ? Number(root.surface.host.surfaceMetrics.title_top || 0)
                + Math.max(0, (Number(root.surface.host.surfaceMetrics.title_height || 28) - height) * 0.5)
            : 6
        radius: 10
        color: root.surface ? root.surface.pdfBadgeFillColor : "#2C85BF"
        border.width: 1
        border.color: root.surface ? root.surface.pdfBadgeBorderColor : "#7FC7FF"
        height: pageBadgeLabel.implicitHeight + 10
        width: pageBadgeLabel.implicitWidth + 16

        Text {
            id: pageBadgeLabel
            anchors.centerIn: parent
            text: "Page " + root.surface.pdfResolvedPageNumber + " / " + root.surface.pdfPageCount
            color: root.surface ? root.surface.pdfBadgeTextColor : "#F4F8FC"
            font.pixelSize: 10
            font.bold: true
            renderType: root.surface && root.surface.host
                ? root.surface.host.nodeTextRenderType
                : Text.CurveRendering
        }
    }
}
