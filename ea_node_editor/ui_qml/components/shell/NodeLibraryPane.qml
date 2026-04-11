import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ShellCollapsibleSidePane {
    id: root
    objectName: "libraryPane"
    readonly property var shellLibraryBridgeRef: shellLibraryBridge
    property var graphCanvasRef
    property var popupHostItem
    property var collapsedCategories: ({})
    signal workflowContextRequested(string workflowId, string workflowScope, real positionX, real positionY)

    paneTitle: "NODE LIBRARY"
    side: "left"
    expandedWidth: 260
    collapseButtonTooltip: "Collapse node library"
    expandHandleTooltip: "Expand node library"

    function categoryKeyForRow(row) {
        if (!row)
            return ""
        return String(row.category_key || "")
    }

    function depthForRow(row) {
        if (!row || row.depth === undefined || row.depth === null)
            return 0
        var depth = Number(row.depth)
        if (!isFinite(depth) || depth < 0)
            return 0
        return Math.floor(depth)
    }

    function rowIndentForRow(row) {
        var baseIndent = 8 + (depthForRow(row) * 14)
        if (row && row.kind !== "category")
            return baseIndent + 10
        return baseIndent
    }

    function isCategoryCollapsed(categoryKey) {
        var normalizedCategoryKey = String(categoryKey || "")
        if (!normalizedCategoryKey.length)
            return true
        var value = collapsedCategories[normalizedCategoryKey]
        if (value === undefined)
            return true
        return !!value
    }

    function setCategoryCollapsed(categoryKey, collapsed) {
        var normalizedCategoryKey = String(categoryKey || "")
        if (!normalizedCategoryKey.length)
            return
        var nextMap = {}
        for (var key in collapsedCategories)
            nextMap[key] = collapsedCategories[key]
        nextMap[normalizedCategoryKey] = !!collapsed
        collapsedCategories = nextMap
    }

    function ancestorsExpanded(ancestorCategoryKeys) {
        if (!ancestorCategoryKeys || ancestorCategoryKeys.length === undefined)
            return true
        for (var index = 0; index < ancestorCategoryKeys.length; ++index) {
            var categoryKey = String(ancestorCategoryKeys[index] || "")
            if (categoryKey.length && isCategoryCollapsed(categoryKey))
                return false
        }
        return true
    }

    function isRowHiddenByAncestors(row) {
        if (!row)
            return true
        return !ancestorsExpanded(row.ancestor_category_keys || [])
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
            var categoryKey = categoryKeyForRow(row)
            if (!categoryKey.length || nextMap[categoryKey] !== undefined)
                continue
            nextMap[categoryKey] = true
            changed = true
        }
        if (changed)
            collapsedCategories = nextMap
    }

    function resetCollapsedState() {
        collapsedCategories = ({})
        ensureCollapsedDefaults(libraryListView.model)
    }

    contentData: [
        TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search nodes..."
            color: root.themePalette.input_fg
            placeholderTextColor: root.themePalette.muted_fg
            background: Rectangle {
                color: root.themePalette.input_bg
                border.color: root.themePalette.input_border
                radius: 3
            }
            onTextChanged: root.shellLibraryBridgeRef.set_library_query(text)
        },

        ListView {
            id: libraryListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.shellLibraryBridgeRef.grouped_node_library_items
            spacing: 0
            Component.onCompleted: root.ensureCollapsedDefaults(model)
            onModelChanged: root.ensureCollapsedDefaults(model)

            delegate: Rectangle {
                id: libraryRow
                objectName: "nodeLibraryRow"
                property bool isCategory: modelData.kind === "category"
                property bool isCustomWorkflow: !isCategory && String(modelData.library_source || "") === "custom_workflow"
                property string workflowScope: String(modelData.workflow_scope || "local")
                property string rowCategoryKey: root.categoryKeyForRow(modelData)
                property string rowTypeId: isCategory ? "" : String(modelData.type_id || "")
                property int rowDepth: root.depthForRow(modelData)
                property real rowIndent: root.rowIndentForRow(modelData)
                property bool hiddenByAncestors: root.isRowHiddenByAncestors(modelData)
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
                height: hiddenByAncestors ? 0 : (isCategory ? 32 : 28)
                color: hiddenByAncestors ? "transparent"
                    : (mouseArea.containsMouse ? root.themePalette.hover : "transparent")
                radius: 4
                visible: !hiddenByAncestors

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
                    anchors.leftMargin: libraryRow.rowIndent
                    spacing: 6

                    Rectangle {
                        width: isCategory ? 0 : 8
                        height: isCategory ? 0 : 8
                        radius: 4
                        visible: !isCategory
                        border.color: root.themePalette.accent
                        border.width: libraryRow.isCustomWorkflow && libraryRow.workflowScope === "local" ? 1.5 : 0
                        color: libraryRow.isCustomWorkflow && libraryRow.workflowScope === "local"
                            ? "transparent"
                            : root.themePalette.accent
                    }

                    Text {
                        text: isCategory
                            ? ((root.isCategoryCollapsed(libraryRow.rowCategoryKey) ? "▸ " : "▾ ") + modelData.label)
                            : modelData.display_name
                        color: isCategory ? root.themePalette.group_title_fg : root.themePalette.app_fg
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
                                libraryRow.rowCategoryKey,
                                !root.isCategoryCollapsed(libraryRow.rowCategoryKey)
                            )
                        } else {
                            root.shellLibraryBridgeRef.request_add_node_from_library(modelData.type_id)
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
    ]

    Connections {
        target: root.shellLibraryBridgeRef
        function onLibraryPaneResetRequested() {
            root.resetCollapsedState()
        }
    }
}
