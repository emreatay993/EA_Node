import QtQuick 2.15

Item {
    id: root
    property var canvasItem: null
    property var viewBridge: null
    property var sceneModel: []
    property bool backdropInputOverlay: false

    width: canvasItem ? canvasItem.worldSize : 0
    height: canvasItem ? canvasItem.worldSize : 0
    transformOrigin: Item.TopLeft
    scale: viewBridge ? viewBridge.zoom_value : 1.0
    x: canvasItem
        ? canvasItem.width * 0.5 - ((viewBridge ? viewBridge.center_x : 0) + canvasItem.worldOffset) * scale
        : 0.0
    y: canvasItem
        ? canvasItem.height * 0.5 - ((viewBridge ? viewBridge.center_y : 0) + canvasItem.worldOffset) * scale
        : 0.0

    Repeater {
        model: root.sceneModel
        delegate: GraphCanvasNodeDelegate {
            canvasItem: root.canvasItem
            backdropInputOverlay: root.backdropInputOverlay
        }
    }
}
