import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    objectName: "libraryPane"
    property var mainWindowRef
    property var graphCanvasRef
    property var popupHostItem
    property var collapsedCategories: ({})
    signal workflowContextRequested(string workflowId, string workflowScope, real positionX, real positionY)

    Layout.preferredWidth: 260
    Layout.fillHeight: true
    color: "#24262D"
    border.color: "#3D4048"

    function isCategoryCollapsed(category) {
        var normalizedCategory = String(category || "")
        if (!normalizedCategory.length)
            return true
        var value = collapsedCategories[normalizedCategory]
        if (value === undefined)
            return true
        return !!value
    }

    function setCategoryCollapsed(category, collapsed) {
        var normalizedCategory = String(category || "")
        if (!normalizedCategory.length)
            return
        var nextMap = {}
        for (var key in collapsedCategories)
            nextMap[key] = collapsedCategories[key]
        nextMap[normalizedCategory] = !!collapsed
        collapsedCategories = nextMap
    }

    function ensureCollapsedDefaults(rows) {
        if (!rows || rows.length === undefined)
            return
        var nextMap = {}
        for (var key in collapsedCategories)
            nextMap[key] = collapsedCategories[key]
        var changed = false
        for (var index = 0; index < rows.length; ++index) {
            var row = rows[index]
            if (!row || row.kind !== "category")
                continue
            var category = String(row.category || "")
            if (!category.length || nextMap[category] !== undefined)
                continue
            nextMap[category] = true
            changed = true
        }
        if (changed)
            collapsedCategories = nextMap
    }

    function resetCollapsedState() {
        collapsedCategories = ({})
        ensureCollapsedDefaults(libraryListView.model)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        Text {
            text: "NODE LIBRARY"
            color: "#AAB2C3"
            font.pixelSize: 12
            font.bold: true
        }

        TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search nodes..."
            color: "#E6EDF8"
            background: Rectangle {
                color: "#2C2F37"
                border.color: "#4A4E58"
                radius: 3
            }
            onTextChanged: root.mainWindowRef.set_library_query(text)
        }

        ListView {
            id: libraryListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.mainWindowRef.grouped_node_library_items
            spacing: 0
            Component.onCompleted: root.ensureCollapsedDefaults(model)
            onModelChanged: root.ensureCollapsedDefaults(model)

            delegate: Rectangle {
                id: libraryRow
                property bool isCategory: modelData.kind === "category"
                property bool isCustomWorkflow: !isCategory && String(modelData.library_source || "") === "custom_workflow"
                property string workflowScope: String(modelData.workflow_scope || "local")
                property bool hiddenByCategory: !isCategory && root.isCategoryCollapsed(modelData.category)
                property var dragPayload: isCategory ? null : {
                    "type_id": String(modelData.type_id || ""),
                    "display_name": String(modelData.display_name || ""),
                    "ports": modelData.ports || [],
                    "library_source": String(modelData.library_source || ""),
                    "workflow_id": String(modelData.workflow_id || ""),
                    "revision": Number(modelData.revision || 1),
                    "workflow_scope": String(modelData.workflow_scope || "local")
                }
                width: ListView.view.width
                height: hiddenByCategory ? 0 : (isCategory ? 32 : 28)
                color: hiddenByCategory ? "transparent"
                    : (mouseArea.containsMouse ? "#31343D" : "transparent")
                radius: 4
                visible: !hiddenByCategory

                Item {
                    id: dragProxy
                    width: parent.width
                    height: parent.height
                    x: 0
                    y: 0
                    opacity: 0
                    Drag.active: !libraryRow.isCategory && mouseArea.drag.active
                    Drag.source: libraryRow
                    Drag.keys: ["ea-node-library"]
                    Drag.supportedActions: Qt.CopyAction
                    Drag.hotSpot.x: mouseArea.mouseX
                    Drag.hotSpot.y: mouseArea.mouseY
                    Drag.mimeData: libraryRow.dragPayload
                        ? {
                            "application/x-ea-node-library":
                                JSON.stringify(libraryRow.dragPayload)
                        }
                        : ({})
                }

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: isCategory ? 8 : 18
                    spacing: 6

                    Rectangle {
                        width: isCategory ? 0 : 8
                        height: isCategory ? 0 : 8
                        radius: 4
                        visible: !isCategory
                        border.color: "#60CDFF"
                        border.width: libraryRow.isCustomWorkflow && libraryRow.workflowScope === "local" ? 1.5 : 0
                        color: libraryRow.isCustomWorkflow && libraryRow.workflowScope === "local" ? "transparent" : "#60CDFF"
                    }

                    Text {
                        text: isCategory
                            ? ((root.isCategoryCollapsed(modelData.category) ? "▸ " : "▾ ") + modelData.label)
                            : modelData.display_name
                        color: isCategory ? "#CFD6E3" : "#D7DDE9"
                        font.pixelSize: isCategory ? 12 : 11
                        font.bold: isCategory
                    }
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    preventStealing: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    drag.target: (isCategory || !(pressedButtons & Qt.LeftButton)) ? null : dragProxy
                    drag.axis: Drag.XAndYAxis
                    property real pressStartX: 0
                    property real pressStartY: 0
                    property bool movedState: false

                    onPressed: {
                        if (mouse.button === Qt.RightButton) {
                            if (libraryRow.isCustomWorkflow) {
                                var popupHost = root.popupHostItem ? root.popupHostItem : root
                                var pointInHost = libraryRow.mapToItem(popupHost, mouse.x, mouse.y)
                                root.workflowContextRequested(
                                    String(modelData.workflow_id || ""),
                                    libraryRow.workflowScope,
                                    pointInHost.x,
                                    pointInHost.y
                                )
                            }
                            mouse.accepted = true
                            return
                        }
                        if (mouse.button !== Qt.LeftButton)
                            return
                        dragProxy.x = 0
                        dragProxy.y = 0
                        root.graphCanvasRef.clearLibraryDropPreview()
                        pressStartX = mouse.x
                        pressStartY = mouse.y
                        movedState = false
                        mouse.accepted = true
                    }

                    onPositionChanged: {
                        if (!pressed)
                            return
                        if (Math.abs(mouse.x - pressStartX) >= 2 || Math.abs(mouse.y - pressStartY) >= 2)
                            movedState = true
                        if (!movedState || isCategory)
                            return
                        var canvasPoint = mouseArea.mapToItem(root.graphCanvasRef, mouse.x, mouse.y)
                        if (root.graphCanvasRef.isPointInCanvas(canvasPoint.x, canvasPoint.y))
                            root.graphCanvasRef.updateLibraryDropPreview(canvasPoint.x, canvasPoint.y, libraryRow.dragPayload)
                        else
                            root.graphCanvasRef.clearLibraryDropPreview()
                    }

                    onReleased: {
                        if (mouse.button !== Qt.LeftButton)
                            return
                        if (movedState) {
                            if (!isCategory) {
                                var canvasPoint = mouseArea.mapToItem(root.graphCanvasRef, mouse.x, mouse.y)
                                if (root.graphCanvasRef.isPointInCanvas(canvasPoint.x, canvasPoint.y))
                                    root.graphCanvasRef.performLibraryDrop(canvasPoint.x, canvasPoint.y, libraryRow.dragPayload)
                                else
                                    root.graphCanvasRef.clearLibraryDropPreview()
                            } else {
                                root.graphCanvasRef.clearLibraryDropPreview()
                            }
                            Qt.callLater(function() {
                                dragProxy.x = 0
                                dragProxy.y = 0
                            })
                            movedState = false
                            return
                        }
                        if (isCategory) {
                            root.setCategoryCollapsed(
                                modelData.category,
                                !root.isCategoryCollapsed(modelData.category)
                            )
                        } else {
                            root.mainWindowRef.request_add_node_from_library(modelData.type_id)
                        }
                    }

                    onCanceled: {
                        movedState = false
                        root.graphCanvasRef.clearLibraryDropPreview()
                        Qt.callLater(function() {
                            dragProxy.x = 0
                            dragProxy.y = 0
                        })
                    }
                }
            }
        }
    }

    Connections {
        target: root.mainWindowRef
        function onLibraryPaneResetRequested() {
            root.resetCollapsedState()
        }
    }
}
