import QtQuick 2.15

Item {
    id: root
    property var surface: null
    readonly property var embeddedInteractiveRects: []

    Rectangle {
        id: issueBadge
        objectName: "graphNodeMediaIssueBadge"
        z: 5
        visible: !!root.surface && root.surface.fileIssueActive
        anchors.right: parent.right
        anchors.rightMargin: 10
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
        anchors.right: issueBadge.visible ? issueBadge.left : parent.right
        anchors.rightMargin: issueBadge.visible
            ? 8
            : (root.surface && root.surface.host
                ? Number(root.surface.host.surfaceMetrics.title_right_margin || 10)
                : 10)
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
