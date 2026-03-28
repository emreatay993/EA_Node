import QtQuick 2.15
import QtQml 2.15

Item {
    id: root
    property Item canvasItem: null
    property var sceneStateBridge: null
    property var viewStateBridge: null
    property var sceneState: null
    property var interactionState: null
    property var canvasPerformancePolicy: null
    property var viewportController: null
    property var edgeLayerItem: null
    visible: false
    width: 0
    height: 0

    function requestEdgeRedraw() {
        if (root.edgeLayerItem && root.edgeLayerItem.requestRedraw)
            root.edgeLayerItem.requestRedraw();
    }

    function _clearTransientSceneState() {
        if (root.sceneState) {
            root.sceneState.liveDragOffsets = ({});
            root.sceneState.liveNodeGeometry = ({});
        }
        if (root.interactionState && root.interactionState._clearWireDragState)
            root.interactionState._clearWireDragState();
    }

    function handleSceneMutation() {
        if (root.canvasPerformancePolicy && root.canvasPerformancePolicy.noteStructuralMutation)
            root.canvasPerformancePolicy.noteStructuralMutation();
        root._clearTransientSceneState();
        if (root.sceneState && root.sceneState.syncEdgePayload)
            root.sceneState.syncEdgePayload();
    }

    function resetCanvasSceneState() {
        if (root.canvasPerformancePolicy && root.canvasPerformancePolicy.clearStructuralMutation)
            root.canvasPerformancePolicy.clearStructuralMutation();
        if (root.sceneState) {
            root.sceneState.liveDragOffsets = ({});
            root.sceneState.liveNodeGeometry = ({});
            if (root.sceneState.syncEdgePayload)
                root.sceneState.syncEdgePayload();
        }
        if (root.interactionState && root.interactionState.resetSceneBridgeState)
            root.interactionState.resetSceneBridgeState();
    }

    Connections {
        target: root.sceneStateBridge
        ignoreUnknownSignals: true

        function onScene_edges_changed() {
            root.handleSceneMutation();
        }

        function onScene_nodes_changed() {
            root.handleSceneMutation();
        }

        function onEdges_changed() {
            root.handleSceneMutation();
        }

        function onNodes_changed() {
            root.handleSceneMutation();
        }
    }

    Connections {
        target: root.viewStateBridge
        ignoreUnknownSignals: true

        function onView_state_changed() {
            if (root.viewportController && root.viewportController.requestViewStateRedraw)
                root.viewportController.requestViewStateRedraw();
        }
    }
}
