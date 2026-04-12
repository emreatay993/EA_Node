import QtQml 2.15
import "GraphNodeHostHitTesting.js" as GraphNodeHostHitTesting

QtObject {
    id: root
    property var host: null
    property var surfaceLoader: null
    property var headerLayer: null

    function pointerInCanvas(mouseArea, mouse) {
        if (!root.host || !root.host.canvasItem)
            return {"x": 0.0, "y": 0.0};
        return mouseArea.mapToItem(root.host.canvasItem, mouse.x, mouse.y);
    }

    function isResizeHandlePoint(localX, localY) {
        if (!root.host)
            return false;
        return GraphNodeHostHitTesting.resizeHandleContainsPoint(
            localX,
            localY,
            root.host.width,
            root.host.height,
            root.host._resizeHandleSize,
            root.host._resizeHandleHitSize,
            root.host.nodeData ? Boolean(root.host.nodeData.collapsed) : true
        );
    }

    function pointInRect(localX, localY, rectLike) {
        return GraphNodeHostHitTesting.pointInRect(localX, localY, rectLike);
    }

    function pointInEmbeddedInteractiveRect(localX, localY) {
        if (GraphNodeHostHitTesting.pointInAnyRect(localX, localY, root.surfaceLoader.embeddedInteractiveRects))
            return true;
        return GraphNodeHostHitTesting.pointInAnyRect(localX, localY, root.headerLayer.embeddedInteractiveRects);
    }

    function surfaceClaimsBodyInteractionAt(localX, localY) {
        if (GraphNodeHostHitTesting.claimsBodyInteraction(localX, localY, root.surfaceLoader.embeddedInteractiveRects))
            return true;
        return GraphNodeHostHitTesting.claimsBodyInteraction(localX, localY, root.headerLayer.embeddedInteractiveRects);
    }

    function requestInlineTitleEditAt(localX, localY) {
        if (root.headerLayer.requestTitleEditAt(localX, localY))
            return true;
        return root.surfaceLoader.requestInlineEditAt(localX, localY);
    }

    function requestScopeOpenAt(localX, localY) {
        return root.headerLayer.requestScopeOpenAt(localX, localY);
    }

    function commitInlineTitleEditAt(localX, localY) {
        if (root.headerLayer.commitTitleEditFromExternalInteraction(localX, localY))
            return true;
        return root.surfaceLoader.commitInlineEditFromExternalInteraction(localX, localY);
    }
}
