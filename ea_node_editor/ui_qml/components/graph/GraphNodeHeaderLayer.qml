import QtQuick 2.15
import "surface_controls" as SurfaceControls
import "surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "GraphNodeHostHitTesting.js" as GraphNodeHostHitTesting

Item {
    id: root
    objectName: "graphNodeHeaderLayer"
    property Item host: null
    property bool isEditing: false
    readonly property bool sharedHeaderTitleEditable: host ? host.sharedHeaderTitleEditable : false
    readonly property bool headerTitleVisible: host
        ? (!host.isFlowchartSurface || host.isCollapsed)
        : true
    readonly property bool isCommentBackdropNode: host
        ? String(host.surfaceFamily || "") === "comment_backdrop"
        : false
    readonly property bool commentTitleIconVisible: host
        ? root.isCommentBackdropNode && host.isCollapsed
        : false
    readonly property int commentTitleIconSize: 14
    readonly property int commentTitleIconSpacing: 6
    readonly property int nodeTitleIconSize: root.graphSharedTypography
        ? root.graphSharedTypography.nodeTitleIconPixelSize
        : 10
    readonly property int nodeTitleIconSpacing: 6
    readonly property real _commentTitleIconReserveWidth: root.commentTitleIconVisible
        ? root.commentTitleIconSize + root.commentTitleIconSpacing
        : 0
    readonly property string nodeTitleIconSource: root.host && root.host.nodeData
        ? String(root.host.nodeData.icon_source || "")
        : ""
    readonly property bool nodeTitleIconEligible: root.headerTitleVisible
        && !!root.host
        && !root.host.isPassiveNode
        && root.nodeTitleIconSource.length > 0
    readonly property bool nodeTitleIconVisible: root.nodeTitleIconEligible && !root.isEditing
    readonly property real _nodeTitleIconReserveWidth: root.nodeTitleIconEligible
        ? root.nodeTitleIconSize + root.nodeTitleIconSpacing
        : 0
    readonly property real _titleLeadingIconReserveWidth: root.commentTitleIconVisible
        ? root._commentTitleIconReserveWidth
        : root._nodeTitleIconReserveWidth
    readonly property real _headerBadgeReserveWidth: (root.host && root.host.canEnterScope ? 56 : 0)
        + (root.host && root.host.isFailedNode ? 70 : 0)
    readonly property string currentTitle: root.host && root.host.nodeData
        ? String(root.host.nodeData.title || "")
        : ""
    readonly property var graphSharedTypography: root.host ? root.host.graphSharedTypography : null
    readonly property bool usesSharedTitleTypography: root.isCommentBackdropNode || !(root.host && root.host.isPassiveNode)
    readonly property string displayTitle: {
        var title = String(root.currentTitle || "");
        if (root.isCommentBackdropNode && title.trim() === "Comment Backdrop")
            return "Comment";
        return title;
    }
    readonly property string commentTitleIconSource: root.commentTitleIconVisible
        ? uiIcons.sourceSized("comment", root.commentTitleIconSize, String(root.host ? root.host.headerTextColor : "#f0f4fb"))
        : ""
    readonly property real _titleEditorLeftPadding: root.host && root.host._titleCentered
        ? 6 + (root._titleLeadingIconReserveWidth * 0.5)
        : 6 + root._titleLeadingIconReserveWidth
    readonly property real _titleEditorRightPadding: root.host && root.host._titleCentered
        ? 6 + (root._titleLeadingIconReserveWidth * 0.5)
        : 6
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [titleEditorInteractionRegion.embeddedInteractiveRects, openBadgeInteractionRegion.embeddedInteractiveRects]
    )
    z: 3

    function _centeredTitleTextDisplayStart() {
        if (!(root.host && root.host._titleCentered))
            return Number(titleText ? titleText.x : 0);
        var availableWidth = Math.max(0, Number(titleText ? titleText.width : 0));
        var displayWidth = Math.min(availableWidth, Math.max(0, Number(titleText ? titleText.contentWidth : 0)));
        return Number(titleText ? titleText.x : 0) + Math.max(0, (availableWidth - displayWidth) * 0.5);
    }

    function _titleLeadingIconX(iconWidth, spacing) {
        if (!(root.host && root.host._titleCentered))
            return 0;
        return Math.max(
            0,
            root._centeredTitleTextDisplayStart() - Math.max(0, Number(iconWidth)) - Math.max(0, Number(spacing))
        );
    }

    function _beginTitleEdit() {
        if (!root.sharedHeaderTitleEditable || root.isEditing || !root.host || !root.host.nodeData)
            return false;
        root.isEditing = true;
        root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
        return true;
    }

    function _requestScopeOpen() {
        if (!root.host || !root.host.nodeData || !root.host.canEnterScope)
            return false;
        if (root.isEditing)
            root.commitTitleEdit(titleEditor.text);
        root.host.nodeOpenRequested(String(root.host.nodeData.node_id || ""));
        return true;
    }

    function requestTitleEditAt(localX, localY) {
        if (!root.sharedHeaderTitleEditable || !root.headerTitleVisible || root.isEditing)
            return false;
        if (!GraphNodeHostHitTesting.pointInRect(localX, localY, titleHitRegion.interactiveRect))
            return false;
        return root._beginTitleEdit();
    }

    function requestScopeOpenAt(localX, localY) {
        if (!root.host || !root.host.canEnterScope)
            return false;
        if (!GraphNodeHostHitTesting.pointInRect(localX, localY, openBadgeInteractionRegion.interactiveRect))
            return false;
        return root._requestScopeOpen();
    }

    function cancelTitleEdit() {
        if (!root.isEditing)
            return;
        root.isEditing = false;
        titleEditor.text = root.currentTitle;
    }

    function commitTitleEdit(text) {
        if (!root.isEditing)
            return;
        var normalized = String(text || "").trim();
        var current = String(root.currentTitle || "").trim();
        root.isEditing = false;
        if (!normalized.length || normalized === current) {
            titleEditor.text = root.currentTitle;
            return;
        }
        titleEditor.text = normalized;
        if (root.host && root.host.nodeData)
            root.host.inlinePropertyCommitted(String(root.host.nodeData.node_id || ""), "title", normalized);
    }

    function commitTitleEditFromExternalInteraction(localX, localY) {
        if (!root.isEditing)
            return false;
        if (GraphNodeHostHitTesting.pointInRect(localX, localY, titleEditorInteractionRegion.interactiveRect))
            return false;
        root.commitTitleEdit(titleEditor.text);
        return true;
    }

    onCurrentTitleChanged: {
        if (!root.isEditing && titleEditor.text !== root.currentTitle)
            titleEditor.text = root.currentTitle;
    }

    onSharedHeaderTitleEditableChanged: {
        if (!root.sharedHeaderTitleEditable && root.isEditing)
            root.cancelTitleEdit();
    }

    onHeaderTitleVisibleChanged: {
        if (!root.headerTitleVisible && root.isEditing)
            root.cancelTitleEdit();
    }

    Rectangle {
        visible: root.host ? root.host._showAccentBar : false
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 4
        radius: 4
        color: root.host && root.host.nodeData ? root.host.nodeData.accent : "#4AA9D6"
    }

    Rectangle {
        visible: root.host ? root.host._showHeaderBackground : false
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: root.host ? Number(root.host.surfaceMetrics.header_top_margin) : 0
        height: root.host ? Number(root.host.surfaceMetrics.header_height) : 0
        color: root.host ? root.host.headerColor : "transparent"
        border.color: root.host ? root.host.outlineColor : "transparent"
    }

    Item {
        id: titleDisplay
        objectName: "graphNodeTitleDisplay"
        visible: root.headerTitleVisible && !root.isEditing
        anchors.left: parent.left
        anchors.leftMargin: root.host ? root.host._titleLeftMargin : 0
        anchors.right: parent.right
        anchors.rightMargin: root.host ? root.host._titleRightMargin + root._headerBadgeReserveWidth : 0
        y: root.host ? root.host._titleTop : 0
        height: root.host ? root.host._titleHeight : 0

        Image {
            id: nodeTitleIcon
            objectName: "graphNodeTitleIcon"
            visible: root.nodeTitleIconVisible
            source: root.nodeTitleIconSource
            x: root._titleLeadingIconX(width, root.nodeTitleIconSpacing)
            y: Math.round((titleDisplay.height - height) * 0.5)
            width: root.nodeTitleIconSize
            height: root.nodeTitleIconSize
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
            sourceSize.width: root.nodeTitleIconSize
            sourceSize.height: root.nodeTitleIconSize
        }

        Image {
            id: commentTitleIcon
            objectName: "graphNodeCommentTitleIcon"
            visible: root.commentTitleIconVisible && root.commentTitleIconSource.length > 0
            source: root.commentTitleIconSource
            x: root._titleLeadingIconX(width, root.commentTitleIconSpacing)
            y: Math.round((titleDisplay.height - height) * 0.5)
            width: root.commentTitleIconSize
            height: root.commentTitleIconSize
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
            sourceSize.width: root.commentTitleIconSize
            sourceSize.height: root.commentTitleIconSize
        }

        Text {
            id: titleText
            objectName: "graphNodeTitle"
            property int effectiveRenderType: renderType
            x: root._titleLeadingIconReserveWidth > 0
                ? (root.host && root.host._titleCentered
                    ? root._titleLeadingIconReserveWidth * 0.5
                    : root._titleLeadingIconReserveWidth)
                : 0
            width: Math.max(0, titleDisplay.width - x)
            height: titleDisplay.height
            text: root.displayTitle
            color: root.host ? root.host.headerTextColor : "#f0f4fb"
            font.pixelSize: root.usesSharedTitleTypography
                ? (root.graphSharedTypography ? root.graphSharedTypography.nodeTitlePixelSize : 12)
                : (root.host ? root.host.passiveFontPixelSize : 12)
            font.weight: root.host
                ? (root.usesSharedTitleTypography
                    ? (root.graphSharedTypography ? root.graphSharedTypography.nodeTitleFontWeight : Font.Bold)
                    : root.host.passiveFontWeight)
                : Font.Bold
            horizontalAlignment: root.host && root.host._titleCentered ? Text.AlignHCenter : Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
        }
    }

    SurfaceControls.GraphSurfaceInteractiveRegion {
        id: titleHitRegion
        host: root.host
        targetItem: titleDisplay
        enabled: root.sharedHeaderTitleEditable && titleDisplay.visible
    }

    SurfaceControls.GraphSurfaceTextField {
        id: titleEditor
        objectName: "graphNodeTitleEditor"
        visible: root.headerTitleVisible && root.isEditing
        host: root.host
        x: titleDisplay.x
        y: titleDisplay.y
        width: titleDisplay.width
        height: titleDisplay.height
        text: root.currentTitle
        font.pixelSize: titleText.font.pixelSize
        font.weight: titleText.font.weight
        textColor: root.host ? root.host.headerTextColor : "#f0f4fb"
        fillColor: root.host ? Qt.alpha(root.host.surfaceColor, 0.96) : "#f5fafd"
        borderColor: root.host ? Qt.alpha(root.host.outlineColor, 0.9) : "#61798B"
        focusBorderColor: root.host ? root.host.selectedOutlineColor : "#2C85BF"
        topPadding: 0
        bottomPadding: 0
        leftPadding: root._titleEditorLeftPadding
        rightPadding: root._titleEditorRightPadding
        horizontalAlignment: root.host && root.host._titleCentered
            ? TextInput.AlignHCenter
            : TextInput.AlignLeft
        verticalAlignment: TextInput.AlignVCenter

        onVisibleChanged: {
            if (visible) {
                text = root.currentTitle;
                forceActiveFocus();
                cursorPosition = text.length;
                deselect();
            }
        }

        onAccepted: {
            root.commitTitleEdit(text);
        }

        onActiveFocusChanged: {
            if (!activeFocus && root.isEditing)
                root.commitTitleEdit(text);
        }

        Keys.onEscapePressed: function(event) {
            root.cancelTitleEdit();
            event.accepted = true;
        }
    }

    SurfaceControls.GraphSurfaceInteractiveRegion {
        id: titleEditorInteractionRegion
        host: root.host
        targetItem: titleEditor
        enabled: root.sharedHeaderTitleEditable && titleEditor.visible
    }

    Rectangle {
        id: failureBadge
        objectName: "graphNodeFailureBadge"
        visible: root.host ? root.host.isFailedNode : false
        anchors.right: openBadge.visible ? openBadge.left : parent.right
        anchors.rightMargin: openBadge.visible ? 6 : 8
        y: root.host ? root.host._titleTop + Math.max(0, (root.host._titleHeight - height) * 0.5) : 0
        width: 62
        height: 18
        radius: 9
        color: root.host ? root.host.failureBadgeFillColor : "#421617"
        border.color: root.host ? root.host.failureBadgeBorderColor : "#FF8C74"

        Text {
            id: failureBadgeText
            objectName: "graphNodeFailureBadgeText"
            anchors.centerIn: parent
            text: "HALTED"
            color: root.host ? root.host.failureBadgeTextColor : "#FFE5DE"
            font.pixelSize: root.graphSharedTypography ? root.graphSharedTypography.badgePixelSize : 9
            font.weight: root.graphSharedTypography ? root.graphSharedTypography.badgeFontWeight : Font.Bold
            renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
        }
    }

    Rectangle {
        id: openBadge
        objectName: "graphNodeOpenBadge"
        visible: root.host ? root.host.canEnterScope : false
        anchors.right: parent.right
        anchors.rightMargin: 8
        y: root.host ? root.host._titleTop + Math.max(0, (root.host._titleHeight - height) * 0.5) : 0
        width: 48
        height: 16
        radius: 8
        color: root.host ? root.host.scopeBadgeColor : "#1D8CE0"
        border.color: root.host ? root.host.scopeBadgeBorderColor : "#60CDFF"

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor

            onPressed: function(mouse) {
                if (root.isEditing)
                    root.commitTitleEdit(titleEditor.text);
                mouse.accepted = true;
            }

            onClicked: function(mouse) {
                if (mouse.button === Qt.LeftButton)
                    root._requestScopeOpen();
                mouse.accepted = true;
            }

            onDoubleClicked: function(mouse) {
                mouse.accepted = true;
            }
        }

        Text {
            objectName: "graphNodeOpenBadgeText"
            anchors.centerIn: parent
            text: "OPEN"
            color: root.host ? root.host.scopeBadgeTextColor : "#f2f4f8"
            font.pixelSize: root.graphSharedTypography ? root.graphSharedTypography.badgePixelSize : 9
            font.weight: root.graphSharedTypography ? root.graphSharedTypography.badgeFontWeight : Font.Bold
            renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
        }
    }

    SurfaceControls.GraphSurfaceInteractiveRegion {
        id: openBadgeInteractionRegion
        host: root.host
        targetItem: openBadge
        enabled: openBadge.visible
    }
}
