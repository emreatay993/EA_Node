import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../common" as Common
import ".." as GraphComponents
import "../GraphActionPresentation.js" as GraphActionPresentation
import "../surface_controls" as GraphSurfaceControls

Item {
    id: root
    objectName: "graphEdgeFloatingToolbar"

    property Item canvasItem: null
    property Item edgeLayer: null
    property var canvasActionRouter: null
    property var viewBridge: null
    property var themePalette: ({})
    property string editingEdgeId: ""

    readonly property var selectedEdgeIds: root.canvasItem && root.canvasItem.selectedEdgeIds
        ? root.canvasItem.selectedEdgeIds
        : []
    readonly property string selectedEdgeId: root.selectedEdgeIds && root.selectedEdgeIds.length === 1
        ? String(root.selectedEdgeIds[0] || "").trim()
        : ""
    readonly property string activeEdgeId: root.editingEdgeId.length > 0
        ? root.editingEdgeId
        : root.selectedEdgeId
    readonly property int edgeTopologyRevision: root.edgeLayer
        ? Number(root.edgeLayer._edgeTopologyRevision || 0)
        : 0
    readonly property var activeEdgePayload: {
        var revision = root.edgeTopologyRevision;
        void(revision);
        return root._edgePayload(root.activeEdgeId);
    }
    readonly property bool activeDataWire: root.selectedEdgeId.length > 0
        && root.activeEdgeId === root.selectedEdgeId
        && Boolean(root.activeEdgePayload && root.activeEdgePayload.active_data_wire)
    readonly property bool flowEdgeActive: root.activeEdgeId.length > 0 && root._edgeSupportsFlowStyle(root.activeEdgeId)
    readonly property var activeSnapshot: root._edgeSnapshot(root.activeEdgeId)
    readonly property var activeAnchorScene: root._edgeAnchorScene(root.activeSnapshot)
    readonly property bool anchorAvailable: root.activeAnchorScene !== null
    readonly property real anchorScreenX: root.anchorAvailable && root.edgeLayer
        ? root.edgeLayer.sceneToScreenX(root.activeAnchorScene.x)
        : 0.0
    readonly property real anchorScreenY: root.anchorAvailable && root.edgeLayer
        ? root.edgeLayer.sceneToScreenY(root.activeAnchorScene.y)
        : 0.0
    readonly property bool labelEditorActive: root.editingEdgeId.length > 0
    readonly property bool toolbarVisible: root.activeEdgeId.length > 0
        && root.anchorAvailable
        && !(root.canvasItem && (
            root.canvasItem.edgeContextVisible
            || root.canvasItem.nodeContextVisible
            || root.canvasItem.selectionContextVisible
            || root.canvasItem.canvasOptionsVisible
        ))
    readonly property var activeFlowStyle: root._flowStyle(root.activeEdgePayload)
    readonly property string activeLabelText: String(root.activeEdgePayload && root.activeEdgePayload.label || "").trim()
    readonly property string toolbarPathMode: GraphActionPresentation.normalizeEdgePathMode(
        root._visualStyle(root.activeEdgePayload).path_mode
    )
    readonly property string toolbarDisplayMode: GraphActionPresentation.normalizeEdgeDisplayMode(
        root._visualStyle(root.activeEdgePayload).display_mode
    )
    readonly property string toolbarPatternGlyphKind: root._currentStrokePattern()
    readonly property string toolbarArrowStartKind: root._currentArrowKind("start")
    readonly property string toolbarArrowEndKind: root._currentArrowKind("end")
    readonly property string toolbarPatternIconName: root._strokePatternIconName(root.toolbarPatternGlyphKind)
    readonly property string toolbarLabelOrientation: GraphActionPresentation.normalizeEdgeLabelOrientation(
        root.activeFlowStyle.label_orientation
    )
    readonly property bool toolbarLabelPositioned: root._hasLabelPosition(root.activeFlowStyle)
    readonly property color accentColor: String(root.activeFlowStyle.stroke_color || root.activeFlowStyle.color || root._paletteColor("accent", "#6BA6FF"))
    readonly property color chromeFillColor: root._paletteColor("toolbar_bg", root._paletteColor("panel_bg", "#20242d"))
    readonly property color chromeBorderColor: root._paletteColor("border", "#4b5568")
    readonly property color foregroundColor: root._paletteColor("panel_title_fg", root._paletteColor("app_fg", "#e7edf8"))
    readonly property color mutedForegroundColor: root._paletteColor("muted_fg", "#98a2b3")
    readonly property int effectiveGraphLabelPixelSize: root._effectiveGraphLabelPixelSize()
    readonly property string activeLabelMode: root.activeSnapshot
        ? String(root.activeSnapshot.labelMode || "")
        : ""
    readonly property bool labelEditorPillVisible: root.activeLabelMode !== "text"
    readonly property real labelEditorHorizontalPadding: root.labelEditorPillVisible ? 10.0 : 1.0
    readonly property real labelEditorVerticalPadding: root.labelEditorPillVisible ? 6.0 : 0.0
    readonly property real labelEditorMaximumTextWidth: root.labelEditorPillVisible ? 220.0 : 120.0
    readonly property real labelEditorMinimumTextWidth: 18.0
    readonly property real labelEditorTextWidth: Math.max(root.labelEditorMinimumTextWidth, Math.ceil(labelEditorMeasure.implicitWidth))
    readonly property real labelEditorTextHeight: Math.ceil(labelEditor.contentHeight)
    readonly property real labelEditorFrameWidth: Math.min(
        root.labelEditorMaximumTextWidth + root.labelEditorHorizontalPadding * 2.0,
        root.labelEditorTextWidth + root.labelEditorHorizontalPadding * 2.0
    )
    readonly property real labelEditorFrameHeight: Math.max(
        root.labelEditorTextHeight + root.labelEditorVerticalPadding * 2.0,
        root.labelEditorPillVisible ? 22.0 : root.labelEditorTextHeight
    )
    readonly property color labelEditorTextColor: root._flowLabelTextColor()
    readonly property color labelEditorBackgroundColor: root._flowLabelBackgroundColor()
    readonly property color labelEditorSelectionColor: Qt.alpha(root.accentColor, 0.36)
    readonly property real gapFromEdge: 54.0
    readonly property real safetyMargin: 8.0
    readonly property bool flipped: root.anchorScreenY - root.gapFromEdge - toolbarChrome.implicitHeight < root.safetyMargin
    readonly property real preferredX: root.anchorScreenX - toolbarChrome.implicitWidth * 0.5
    readonly property real preferredY: root.flipped
        ? root.anchorScreenY + 28.0
        : root.anchorScreenY - root.gapFromEdge - toolbarChrome.implicitHeight
    readonly property real toolbarX: root._clamp(
        root.preferredX,
        root.safetyMargin,
        Math.max(root.safetyMargin, width - toolbarChrome.implicitWidth - root.safetyMargin)
    )
    readonly property real toolbarY: root._clamp(
        root.preferredY,
        root.safetyMargin,
        Math.max(root.safetyMargin, height - toolbarChrome.implicitHeight - root.safetyMargin)
    )
    readonly property var toolbarActions: GraphActionPresentation.edgeToolbarActions({
        "edgePayload": root.activeEdgePayload,
        "activeDataWire": root.activeDataWire,
        "flowEdgeActive": root.flowEdgeActive,
        "displayMode": root.toolbarDisplayMode,
        "hasLabel": root.activeLabelText.length > 0,
        "reversible": Boolean(root.activeEdgePayload && root.activeEdgePayload.reversible)
    })
    readonly property var colorChoices: [
        "#8E8E8E", "#E06C75", "#E5C07B", "#98C379",
        "#56B6C2", "#61AFEF", "#C678DD", "#F0F4FB"
    ]
    readonly property var patternChoices: [
        { "label": "Solid", "value": "solid" },
        { "label": "Dashed", "value": "dashed" },
        { "label": "Dotted", "value": "dotted" }
    ]
    readonly property var pathModeChoices: GraphActionPresentation.edgePathChoices()
    readonly property var displayModeChoices: GraphActionPresentation.edgeDisplayChoices()
    readonly property var arrowChoices: GraphActionPresentation.edgeArrowKindChoices()
    readonly property var arrowEnds: GraphActionPresentation.edgeArrowEnds()
    readonly property var labelOrientationChoices: GraphActionPresentation.edgeLabelOrientationChoices()
    readonly property int stylePopupClosePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    visible: root.toolbarVisible || root.labelEditorActive
    z: 950

    onActiveEdgeIdChanged: root._closeStylePopups(null)
    onToolbarVisibleChanged: {
        if (!root.toolbarVisible)
            root._closeStylePopups(null);
    }

    function _paletteColor(key, fallback) {
        var source = root.themePalette || ({});
        var value = String(source[key] || "").trim();
        return value.length ? value : fallback;
    }

    function _clamp(value, minimum, maximum) {
        var numeric = Number(value);
        if (!isFinite(numeric))
            numeric = Number(minimum || 0);
        return Math.max(Number(minimum || 0), Math.min(Number(maximum || minimum || 0), numeric));
    }

    function _styleString(value) {
        var text = String(value || "").trim();
        return text.length ? text : "";
    }

    function _effectiveGraphLabelPixelSize() {
        var numeric = NaN;
        if (root.canvasItem && root.canvasItem.prefs)
            numeric = Number(root.canvasItem.prefs.graphLabelPixelSize);
        if (!isFinite(numeric) && root.edgeLayer && root.edgeLayer.graphLabelPixelSize !== undefined)
            numeric = Number(root.edgeLayer.graphLabelPixelSize);
        if (!isFinite(numeric))
            numeric = 10;
        return Math.max(8, Math.min(18, Math.round(numeric)));
    }

    function _edgeLayerColor(propertyName, fallback) {
        if (!root.edgeLayer || root.edgeLayer[propertyName] === undefined)
            return fallback;
        var value = root.edgeLayer[propertyName];
        return String(value || "").trim().length ? value : fallback;
    }

    function _flowLabelTextColor() {
        var explicitColor = root._styleString(root.activeFlowStyle.label_text_color);
        if (explicitColor.length)
            return explicitColor;
        return root._edgeLayerColor("flowDefaultLabelTextColor", root.foregroundColor);
    }

    function _flowLabelBackgroundColor() {
        var explicitColor = root._styleString(root.activeFlowStyle.label_background_color);
        if (explicitColor.length)
            return explicitColor;
        return "transparent";
    }

    function _actionRouter() {
        return root.canvasActionRouter
            || (root.canvasItem && root.canvasItem.canvasActionRouter ? root.canvasItem.canvasActionRouter : null);
    }

    function _sceneCommandBridge() {
        return root.canvasItem && root.canvasItem.sceneCommandBridge
            ? root.canvasItem.sceneCommandBridge
            : null;
    }

    function _requestEdgeRedraw() {
        if (root.canvasItem && root.canvasItem.requestEdgeRedraw)
            root.canvasItem.requestEdgeRedraw();
    }

    function _edgeSupportsFlowStyle(edgeId) {
        var actionRouter = root._actionRouter();
        if (actionRouter && actionRouter.edgeSupportsFlowStyle)
            return Boolean(actionRouter.edgeSupportsFlowStyle(edgeId));
        return root.canvasItem && root.canvasItem._edgeSupportsFlowStyle
            ? Boolean(root.canvasItem._edgeSupportsFlowStyle(edgeId))
            : false;
    }

    function _edgePayload(edgeId) {
        if (!root.canvasItem || !root.canvasItem._sceneEdgePayload)
            return null;
        return root.canvasItem._sceneEdgePayload(String(edgeId || "").trim());
    }

    function _flowStyle(edgePayload) {
        if (!edgePayload)
            return ({});
        return edgePayload.flow_style || edgePayload.visual_style || ({});
    }

    function _visualStyle(edgePayload) {
        return edgePayload && edgePayload.visual_style ? edgePayload.visual_style : ({});
    }

    function _edgeSnapshot(edgeId) {
        if (!root.edgeLayer || !root.edgeLayer._visibleEdgeSnapshot)
            return null;
        return root.edgeLayer._visibleEdgeSnapshot(String(edgeId || "").trim());
    }

    function _edgeAnchorScene(snapshot) {
        if (!snapshot || Boolean(snapshot.culled) || !snapshot.geometry)
            return null;
        if (root.edgeLayer
                && root.edgeLayer.labelDragEdgeId
                && root.edgeLayer.labelDragEdgeId === String(snapshot.edgeId || "")
                && root.edgeLayer.labelDragAnchorScene)
            return root.edgeLayer.labelDragAnchorScene;
        if (snapshot.labelAnchorScene)
            return snapshot.labelAnchorScene;
        if (root.edgeLayer && root.edgeLayer._edgeAnchor)
            return root.edgeLayer._edgeAnchor(snapshot.geometry, 0.5);
        return null;
    }

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    function _edgeActionId(key) {
        var actionRouter = root._actionRouter();
        return actionRouter && actionRouter.edgeContextActionId
            ? actionRouter.edgeContextActionId(key)
            : String(key || "");
    }

    function _dispatchGraphEdgeAction(actionKey) {
        var edgeId = root.activeEdgeId;
        var actionId = root._edgeActionId(actionKey);
        var actionRouter = root._actionRouter();
        if (!edgeId.length || !actionId.length)
            return false;
        if (actionRouter && actionRouter.handleEdgeToolbarAction)
            return Boolean(actionRouter.handleEdgeToolbarAction(actionId, edgeId));
        if (actionRouter && actionRouter.triggerGraphAction)
            return Boolean(actionRouter.triggerGraphAction(actionId, { "edge_id": edgeId }));
        return false;
    }

    function _setFlowEdgeVisualStyle(updates) {
        var edgeId = root.activeEdgeId;
        var actionRouter = root._actionRouter();
        if (!edgeId.length)
            return false;
        if (actionRouter && actionRouter.setFlowEdgeVisualStyle)
            return Boolean(actionRouter.setFlowEdgeVisualStyle(edgeId, updates || ({})));
        var bridge = root._sceneCommandBridge();
        if (!bridge || !bridge.set_edge_visual_style)
            return false;
        var accepted = bridge.set_edge_visual_style(edgeId, updates || ({}));
        if (accepted === false)
            return false;
        root._requestEdgeRedraw();
        return true;
    }

    function _setEdgePathMode(pathMode) {
        var edgeId = root.activeEdgeId;
        var mode = GraphActionPresentation.normalizeEdgePathMode(pathMode);
        var actionRouter = root._actionRouter();
        if (!edgeId.length)
            return false;
        if (actionRouter && actionRouter.setEdgePathMode)
            return Boolean(actionRouter.setEdgePathMode(edgeId, mode));
        var bridge = root._sceneCommandBridge();
        if (!bridge || !bridge.set_edge_visual_style)
            return false;
        var source = root._visualStyle(root.activeEdgePayload);
        var next = {};
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key))
                next[key] = source[key];
        }
        if (mode === "auto")
            delete next.path_mode;
        else
            next.path_mode = mode;
        var accepted = bridge.set_edge_visual_style(edgeId, next);
        if (accepted === false)
            return false;
        root._requestEdgeRedraw();
        return true;
    }

    function _clearFlowEdgeLabel() {
        var edgeId = root.activeEdgeId;
        var actionRouter = root._actionRouter();
        if (!edgeId.length)
            return false;
        if (actionRouter && actionRouter.clearFlowEdgeLabel)
            return Boolean(actionRouter.clearFlowEdgeLabel(edgeId));
        var bridge = root._sceneCommandBridge();
        if (!bridge || !bridge.clear_edge_label)
            return false;
        var accepted = bridge.clear_edge_label(edgeId);
        if (accepted === false)
            return false;
        root._requestEdgeRedraw();
        return true;
    }

    function _setEdgeLabel(edgeId, label) {
        var bridge = root._sceneCommandBridge();
        if (!bridge || !bridge.set_edge_label)
            return false;
        var accepted = bridge.set_edge_label(String(edgeId || ""), String(label || ""));
        if (accepted === false)
            return false;
        root._requestEdgeRedraw();
        return true;
    }

    function _sceneBoundsForActiveEdge() {
        var snapshot = root.activeSnapshot;
        if (!snapshot || !snapshot.geometry)
            return null;
        var geometry = snapshot.geometry;
        var points = geometry.pipe_points && geometry.pipe_points.length
            ? geometry.pipe_points
            : [
                { "x": geometry.sx, "y": geometry.sy },
                { "x": geometry.c1x, "y": geometry.c1y },
                { "x": geometry.c2x, "y": geometry.c2y },
                { "x": geometry.tx, "y": geometry.ty }
            ];
        var minX = Number.POSITIVE_INFINITY;
        var minY = Number.POSITIVE_INFINITY;
        var maxX = Number.NEGATIVE_INFINITY;
        var maxY = Number.NEGATIVE_INFINITY;
        for (var i = 0; i < points.length; i++) {
            var point = points[i] || ({});
            var x = Number(point.x);
            var y = Number(point.y);
            if (!isFinite(x) || !isFinite(y))
                continue;
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        }
        if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY))
            return null;
        return {
            "x": minX,
            "y": minY,
            "width": Math.max(1.0, maxX - minX),
            "height": Math.max(1.0, maxY - minY)
        };
    }

    function _frameActiveEdge() {
        if (!root.canvasItem || !root.canvasItem.frameSceneRectPayload)
            return false;
        var bounds = root._sceneBoundsForActiveEdge();
        if (!bounds)
            return false;
        return Boolean(root.canvasItem.frameSceneRectPayload(bounds, 88.0));
    }

    function _currentStrokePattern() {
        var value = String(root.activeFlowStyle.stroke_pattern || root.activeFlowStyle.stroke || "solid").toLowerCase();
        return value === "dashed" || value === "dotted" ? value : "solid";
    }

    function _strokePatternIconName(pattern) {
        var value = String(pattern || "solid").toLowerCase();
        if (value === "dashed")
            return "edge-path-dashed";
        if (value === "dotted")
            return "edge-path-dotted";
        return "edge-path-solid";
    }

    function _currentArrowKind(end) {
        var style = root.activeFlowStyle;
        var value = String(end === "start" ? (style.arrow_tail || "") : (style.arrow_head || "")).toLowerCase();
        if (!value && end !== "start" && style.arrow)
            value = String(style.arrow.kind || "").toLowerCase();
        return GraphActionPresentation.normalizeEdgeArrowKind(value, end);
    }

    function _hasLabelPosition(style) {
        var value = style ? style.label_position : undefined;
        return value !== undefined && value !== null && value !== "" && isFinite(Number(value));
    }

    function _buttonActive(action) {
        var id = String(action && action.id || "");
        if (id === "path_mode")
            return pathModePopup.opened;
        if (id === "display_mode")
            return displayModePopup.opened;
        if (id === "stroke_pattern")
            return patternPopup.opened;
        if (id === "arrow_head")
            return arrowPopup.opened;
        if (id === "flow_edge_label_layout")
            return labelLayoutPopup.opened;
        return false;
    }

    function _openPopup(popup, button) {
        if (!popup || !button)
            return;
        if (popup.opened) {
            popup.close();
            return;
        }
        root._closeStylePopups(popup);
        var local = button.mapToItem(root, button.width * 0.5, button.height + 8);
        popup.x = root._clamp(local.x - popup.implicitWidth * 0.5, 0, Math.max(0, root.width - popup.implicitWidth));
        popup.y = root.flipped ? -popup.implicitHeight - 8 : local.y;
        popup.open();
    }

    function _closeStylePopups(exceptPopup) {
        if (colorPopup !== exceptPopup && colorPopup.opened)
            colorPopup.close();
        if (pathModePopup !== exceptPopup && pathModePopup.opened)
            pathModePopup.close();
        if (displayModePopup !== exceptPopup && displayModePopup.opened)
            displayModePopup.close();
        if (patternPopup !== exceptPopup && patternPopup.opened)
            patternPopup.close();
        if (arrowPopup !== exceptPopup && arrowPopup.opened)
            arrowPopup.close();
        if (labelLayoutPopup !== exceptPopup && labelLayoutPopup.opened)
            labelLayoutPopup.close();
    }

    function _stylePopupClosesOutsidePopup() {
        return (root.stylePopupClosePolicy & Popup.CloseOnPressOutside) !== 0
            && (root.stylePopupClosePolicy & Popup.CloseOnPressOutsideParent) === 0;
    }

    function _handleToolbarAction(action, button) {
        var id = String(action && action.id || "");
        var popover = String(action && action.popover || "");
        if (popover === "color") {
            root._openPopup(colorPopup, button);
            return;
        }
        if (popover === "path_mode") {
            root._openPopup(pathModePopup, button);
            return;
        }
        if (popover === "display_mode") {
            root._openPopup(displayModePopup, button);
            return;
        }
        if (popover === "pattern") {
            root._openPopup(patternPopup, button);
            return;
        }
        if (popover === "arrow") {
            root._openPopup(arrowPopup, button);
            return;
        }
        if (popover === "label_layout") {
            root._openPopup(labelLayoutPopup, button);
            return;
        }
        root._closeStylePopups(null);
        if (id === "frame_edge") {
            root._frameActiveEdge();
        } else if (id === "toggle_edge_enabled") {
            if (root.canvasItem && root.canvasItem.toggleSelectedEdgesEnabled)
                root.canvasItem.toggleSelectedEdgesEnabled(root.activeEdgeId);
        } else if (id === "edit_flow_edge_label") {
            root.beginLabelEdit(root.activeEdgeId);
        } else if (id === "clear_flow_edge_label") {
            root._clearFlowEdgeLabel();
        } else if (id === "remove_edge") {
            root._dispatchGraphEdgeAction("remove_edge");
        } else if (id === "edit_flow_edge_style"
                   || id === "copy_flow_edge_style"
                   || id === "paste_flow_edge_style"
                   || id === "reset_flow_edge_style"
                   || id === "reverse_flow_edge") {
            root._dispatchGraphEdgeAction(id);
        }
    }

    function beginLabelEdit(edgeId) {
        var normalized = String(edgeId || "").trim();
        if (!normalized.length || !root._edgeSupportsFlowStyle(normalized))
            return false;
        var snapshot = root._edgeSnapshot(normalized);
        if (!root._edgeAnchorScene(snapshot))
            return false;
        root.editingEdgeId = normalized;
        if (root.canvasItem && root.canvasItem.setExclusiveEdgeSelection)
            root.canvasItem.setExclusiveEdgeSelection(normalized);
        var payload = root._edgePayload(normalized);
        labelEditor.text = String(payload && payload.label || "");
        labelEditor.forceActiveFocus();
        labelEditor.selectAll();
        return true;
    }

    function commitLabelEdit() {
        var edgeId = root.editingEdgeId;
        if (!edgeId.length)
            return false;
        var label = labelEditor.text;
        if (!root._setEdgeLabel(edgeId, label))
            return false;
        root.editingEdgeId = "";
        return true;
    }

    function cancelLabelEdit() {
        if (!root.editingEdgeId.length)
            return false;
        root.editingEdgeId = "";
        return true;
    }

    function insertLabelLineBreak() {
        if (!root.labelEditorActive)
            return false;
        if (labelEditor.selectionEnd > labelEditor.selectionStart)
            labelEditor.remove(labelEditor.selectionStart, labelEditor.selectionEnd);
        labelEditor.insert(labelEditor.cursorPosition, "\n");
        return true;
    }

    function _handleLabelEditorReturn(event) {
        // Shift+Enter starts a new label line; Enter commits.
        if (event.modifiers & Qt.ShiftModifier)
            root.insertLabelLineBreak();
        else
            root.commitLabelEdit();
        event.accepted = true;
    }

    GraphComponents.GraphSharedTypography {
        id: labelEditorTypography
        objectName: "graphEdgeLabelEditorSharedTypography"
        graphLabelPixelSize: root.effectiveGraphLabelPixelSize
    }

    Text {
        // Natural width of the widest label line; the editor wraps past the label maximum.
        id: labelEditorMeasure
        visible: false
        font: labelEditor.font
        text: labelEditor.text.length ? labelEditor.text : "M"
        textFormat: Text.PlainText
        wrapMode: Text.NoWrap
    }

    Rectangle {
        id: toolbarChrome
        objectName: "graphEdgeFloatingToolbarChrome"
        visible: root.toolbarVisible
        x: root.toolbarX
        y: root.toolbarY
        radius: 7
        color: root.chromeFillColor
        opacity: 0.96
        border.width: 1
        border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        implicitWidth: buttonRow.implicitWidth + 8
        implicitHeight: Math.max(34, buttonRow.implicitHeight + 8)
        width: implicitWidth
        height: implicitHeight

        Row {
            id: buttonRow
            anchors.centerIn: parent
            spacing: 4

            Repeater {
                model: root.toolbarActions

                GraphSurfaceControls.GraphSurfaceButton {
                    id: actionButton
                    readonly property string actionId: String(modelData.id || "")
                    readonly property bool styleGlyphAction: actionId === "stroke_pattern" || actionId === "arrow_head"
                    readonly property string currentPatternGlyphKind: actionId === "stroke_pattern" ? root._currentStrokePattern() : ""
                    objectName: "graphEdgeFloatingToolbarAction_" + String(modelData.id || "")
                    text: styleGlyphAction ? "" : String(modelData.label || "")
                    iconName: styleGlyphAction ? "" : String(modelData.icon || "")
                    iconOnly: true
                    checked: Boolean(modelData.checked)
                    iconSize: 18
                    width: styleGlyphAction ? 38 : implicitWidth
                    height: styleGlyphAction ? 34 : implicitHeight
                    iconSourceResolver: function(name, size, color) {
                        return root._iconSource(name, size, color);
                    }
                    foregroundColor: root.mutedForegroundColor
                    accentColor: Boolean(modelData.destructive) ? "#D94F4F" : root.accentColor
                    enabled: modelData.enabled !== false
                    active: root._buttonActive(modelData)
                    chromeRadius: 6
                    contentHorizontalPadding: 8
                    contentVerticalPadding: 8
                    tooltipText: String(modelData.label || "")
                    tooltipCategory: "general"
                    tooltipScreenStablePositioning: true
                    tooltipAnchorScale: root.viewBridge ? Number(root.viewBridge.zoom_value || 1.0) : 1.0
                    tooltipScreenGap: 8
                    tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                    baseFillColor: "transparent"
                    baseBorderColor: "transparent"
                    idleBorderWidth: 0
                    hoverFillColor: Qt.alpha(root.foregroundColor, 0.10)
                    hoverBorderColor: Qt.alpha(root.foregroundColor, 0.10)
                    hoverBorderWidth: 1
                    onClicked: root._handleToolbarAction(modelData, actionButton)

                    Image {
                        objectName: "graphEdgeToolbarPatternGlyph"
                        visible: actionButton.actionId === "stroke_pattern"
                        anchors.centerIn: parent
                        source: root._iconSource(root.toolbarPatternIconName, 24, String(actionButton.resolvedForegroundColor))
                        width: 24
                        height: 24
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        mipmap: true
                        sourceSize.width: 24
                        sourceSize.height: 24
                    }

                    EdgeArrowGlyph {
                        objectName: "graphEdgeToolbarArrowGlyph"
                        visible: actionButton.actionId === "arrow_head"
                        anchors.centerIn: parent
                        width: 30
                        height: 22
                        startKind: root.toolbarArrowStartKind
                        endKind: root.toolbarArrowEndKind
                        color: actionButton.resolvedForegroundColor
                    }
                }
            }
        }
    }

    Item {
        id: labelEditorFrame
        objectName: "graphEdgeLabelInlineEditorFrame"
        visible: root.labelEditorActive && root.anchorAvailable
        x: root.anchorScreenX - root.labelEditorFrameWidth * 0.5
        y: root.anchorScreenY - root.labelEditorFrameHeight * 0.5
        width: root.labelEditorFrameWidth
        height: root.labelEditorFrameHeight
        clip: true

        Rectangle {
            id: labelEditorBackground
            objectName: "graphEdgeLabelInlineEditorBackground"
            readonly property int effectiveBorderWidth: border.width
            readonly property bool pillVisible: root.labelEditorPillVisible
            anchors.fill: parent
            radius: 5
            visible: root.labelEditorPillVisible
            color: root.labelEditorBackgroundColor
            border.width: 0
            border.color: "transparent"
        }

        TextEdit {
            id: labelEditor
            objectName: "graphEdgeLabelInlineEditor"
            anchors.fill: parent
            anchors.leftMargin: root.labelEditorHorizontalPadding
            anchors.rightMargin: root.labelEditorHorizontalPadding
            anchors.topMargin: root.labelEditorVerticalPadding
            anchors.bottomMargin: root.labelEditorVerticalPadding
            clip: true
            selectByMouse: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.Wrap
            color: root.labelEditorTextColor
            selectedTextColor: root._paletteColor("selection_fg", "#ffffff")
            selectionColor: root._paletteColor("selection_bg", root.labelEditorSelectionColor)
            font.pixelSize: root.labelEditorPillVisible
                ? labelEditorTypography.edgePillPixelSize
                : labelEditorTypography.edgeLabelPixelSize
            font.weight: root.labelEditorPillVisible
                ? labelEditorTypography.edgePillFontWeight
                : labelEditorTypography.edgeLabelFontWeight
            horizontalAlignment: TextEdit.AlignHCenter
            verticalAlignment: TextEdit.AlignVCenter
            renderType: Text.NativeRendering
            Keys.onReturnPressed: function(event) {
                root._handleLabelEditorReturn(event);
            }
            Keys.onEnterPressed: function(event) {
                root._handleLabelEditorReturn(event);
            }
            Keys.onEscapePressed: function(event) {
                root.cancelLabelEdit();
                event.accepted = true;
            }
            onActiveFocusChanged: {
                if (!activeFocus && root.labelEditorActive)
                    root.commitLabelEdit();
            }
        }
    }

    Popup {
        id: displayModePopup
        objectName: "graphEdgeDisplayModePopup"
        parent: root
        modal: false
        focus: true
        padding: 6
        closePolicy: root.stylePopupClosePolicy
        background: Rectangle {
            radius: 7
            color: root.chromeFillColor
            border.width: 1
            border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        }
        contentItem: Row {
            spacing: 8
            Repeater {
                model: root.displayModeChoices
                Button {
                    id: displayModeChoiceButton
                    objectName: "graphEdgeDisplayModeChoice_" + String(modelData.value || "")
                    text: String(modelData.label || "")
                    width: 62
                    height: 34
                    padding: 0
                    checkable: true
                    checked: root.toolbarDisplayMode === String(modelData.value || "")
                    autoExclusive: true
                    onClicked: {
                        var mode = String(modelData.value || "default");
                        if (root.canvasItem && root.canvasItem.setEdgesDisplayMode) {
                            root.canvasItem.setEdgesDisplayMode([root.activeEdgeId], mode);
                            displayModePopup.close();
                        }
                    }
                    contentItem: Text {
                        text: String(modelData.label || "")
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: root.toolbarDisplayMode === String(modelData.value || "")
                            ? root.accentColor
                            : root.foregroundColor
                        font.pixelSize: 12
                        font.bold: root.toolbarDisplayMode === String(modelData.value || "")
                    }
                    background: Rectangle {
                        radius: 5
                        color: root.toolbarDisplayMode === String(modelData.value || "")
                            ? Qt.alpha(root.accentColor, 0.16)
                            : (displayModeChoiceButton.hovered ? Qt.alpha(root.foregroundColor, 0.10) : "transparent")
                    }
                }
            }
        }
    }

    Popup {
        id: colorPopup
        objectName: "graphEdgeColorPopup"
        parent: root
        modal: false
        focus: true
        padding: 8
        closePolicy: root.stylePopupClosePolicy
        background: Rectangle {
            radius: 7
            color: root.chromeFillColor
            border.width: 1
            border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        }
        contentItem: Grid {
            columns: 4
            spacing: 6
            Repeater {
                model: root.colorChoices
                Button {
                    objectName: "graphEdgeColorSwatch_" + String(modelData).replace("#", "")
                    width: 26
                    height: 26
                    padding: 0
                    onClicked: {
                        if (root._setFlowEdgeVisualStyle({ "stroke_color": String(modelData) }))
                            colorPopup.close();
                    }
                    contentItem: Item {}
                    background: Rectangle {
                        radius: 4
                        color: String(modelData)
                        border.width: String(modelData).toLowerCase() === String(root.activeFlowStyle.stroke_color || "").toLowerCase() ? 2 : 1
                        border.color: root.foregroundColor
                    }
                }
            }
        }
    }

    Popup {
        id: pathModePopup
        objectName: "graphEdgePathModePopup"
        parent: root
        modal: false
        focus: true
        padding: 6
        closePolicy: root.stylePopupClosePolicy
        background: Rectangle {
            radius: 7
            color: root.chromeFillColor
            border.width: 1
            border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        }
        contentItem: Row {
            spacing: 8
            Repeater {
                model: root.pathModeChoices
                Button {
                    id: pathModeChoiceButton
                    objectName: "graphEdgePathModeChoice_" + String(modelData.value || "")
                    text: String(modelData.label || "")
                    width: 58
                    height: 34
                    padding: 0
                    Common.ManagedToolTip {
                        policyBridge: root.canvasItem && root.canvasItem.canvasStateBridgeRef
                            ? root.canvasItem.canvasStateBridgeRef
                            : null
                        category: "general"
                        active: pathModeChoiceButton.hovered
                        text: pathModeChoiceButton.text
                    }
                    onClicked: {
                        if (root._setEdgePathMode(String(modelData.value || "auto")))
                            pathModePopup.close();
                    }
                    contentItem: Text {
                        text: String(modelData.label || "")
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: root.toolbarPathMode === String(modelData.value || "")
                            ? root.accentColor
                            : root.foregroundColor
                        font.pixelSize: 12
                        font.bold: root.toolbarPathMode === String(modelData.value || "")
                    }
                    background: Rectangle {
                        radius: 5
                        color: root.toolbarPathMode === String(modelData.value || "")
                            ? Qt.alpha(root.accentColor, 0.16)
                            : (pathModeChoiceButton.hovered ? Qt.alpha(root.foregroundColor, 0.10) : "transparent")
                    }
                }
            }
        }
    }

    Popup {
        id: patternPopup
        objectName: "graphEdgePatternPopup"
        parent: root
        modal: false
        focus: true
        padding: 6
        closePolicy: root.stylePopupClosePolicy
        background: Rectangle {
            radius: 7
            color: root.chromeFillColor
            border.width: 1
            border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        }
        contentItem: Row {
            spacing: 8
            Repeater {
                model: root.patternChoices
                Button {
                    id: patternChoiceButton
                    objectName: "graphEdgePatternChoice_" + String(modelData.value || "")
                    text: String(modelData.label || "")
                    width: 52
                    height: 38
                    padding: 0
                    Common.ManagedToolTip {
                        policyBridge: root.canvasItem && root.canvasItem.canvasStateBridgeRef
                            ? root.canvasItem.canvasStateBridgeRef
                            : null
                        category: "general"
                        active: patternChoiceButton.hovered
                        text: patternChoiceButton.text
                    }
                    onClicked: {
                        if (root._setFlowEdgeVisualStyle({ "stroke_pattern": String(modelData.value || "solid") }))
                            patternPopup.close();
                    }
                    contentItem: Item {
                        readonly property string patternKind: String(modelData.value || "solid")
                        objectName: "graphEdgePatternIcon_" + String(modelData.value || "")
                        implicitWidth: 56
                        implicitHeight: 24

                        Image {
                            anchors.centerIn: parent
                            source: root._iconSource(
                                root._strokePatternIconName(parent.patternKind),
                                26,
                                String(root._currentStrokePattern() === parent.patternKind ? root.accentColor : root.foregroundColor)
                            )
                            width: 26
                            height: 26
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            sourceSize.width: 26
                            sourceSize.height: 26
                        }
                    }
                    background: Rectangle {
                        radius: 5
                        color: root._currentStrokePattern() === String(modelData.value || "")
                            ? Qt.alpha(root.accentColor, 0.16)
                            : (patternChoiceButton.hovered ? Qt.alpha(root.foregroundColor, 0.10) : "transparent")
                    }
                }
            }
        }
    }

    Popup {
        id: arrowPopup
        objectName: "graphEdgeArrowPopup"
        parent: root
        modal: false
        focus: true
        padding: 6
        closePolicy: root.stylePopupClosePolicy
        background: Rectangle {
            radius: 7
            color: root.chromeFillColor
            border.width: 1
            border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        }
        contentItem: Column {
            spacing: 4
            Repeater {
                model: root.arrowEnds
                Row {
                    id: arrowEndRow
                    readonly property var endSpec: modelData
                    spacing: 4

                    Text {
                        width: 36
                        height: 30
                        text: String(arrowEndRow.endSpec.label || "")
                        color: root.mutedForegroundColor
                        font.pixelSize: 11
                        verticalAlignment: Text.AlignVCenter
                    }

                    Repeater {
                        model: root.arrowChoices
                        Button {
                            id: arrowChoiceButton
                            readonly property string arrowKind: String(modelData.value || "none")
                            readonly property string arrowEnd: String(arrowEndRow.endSpec.end || "end")
                            readonly property bool choiceSelected: root._currentArrowKind(arrowEnd) === arrowKind
                            objectName: "graphEdgeArrowChoice_" + arrowEnd + "_" + arrowKind
                            text: String(arrowEndRow.endSpec.label || "") + ": " + String(modelData.label || "")
                            width: 40
                            height: 30
                            padding: 0
                            Common.ManagedToolTip {
                                policyBridge: root.canvasItem && root.canvasItem.canvasStateBridgeRef
                                    ? root.canvasItem.canvasStateBridgeRef
                                    : null
                                category: "general"
                                active: arrowChoiceButton.hovered
                                text: arrowChoiceButton.text
                            }
                            onClicked: {
                                // Stays open so both ends can be set in one visit.
                                var update = {};
                                update[String(arrowEndRow.endSpec.styleKey || "arrow_head")] = arrowChoiceButton.arrowKind;
                                root._setFlowEdgeVisualStyle(update);
                            }
                            contentItem: Item {
                                implicitWidth: 40
                                implicitHeight: 30

                                EdgeArrowGlyph {
                                    anchors.centerIn: parent
                                    width: 32
                                    height: 22
                                    startKind: arrowChoiceButton.arrowEnd === "start" ? arrowChoiceButton.arrowKind : "none"
                                    endKind: arrowChoiceButton.arrowEnd === "end" ? arrowChoiceButton.arrowKind : "none"
                                    color: arrowChoiceButton.choiceSelected ? root.accentColor : root.foregroundColor
                                }
                            }
                            background: Rectangle {
                                radius: 5
                                color: arrowChoiceButton.choiceSelected
                                    ? Qt.alpha(root.accentColor, 0.16)
                                    : (arrowChoiceButton.hovered ? Qt.alpha(root.foregroundColor, 0.10) : "transparent")
                            }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: labelLayoutPopup
        objectName: "graphEdgeLabelLayoutPopup"
        parent: root
        modal: false
        focus: true
        padding: 6
        closePolicy: root.stylePopupClosePolicy
        background: Rectangle {
            radius: 7
            color: root.chromeFillColor
            border.width: 1
            border.color: Qt.alpha(root.chromeBorderColor, 0.74)
        }
        contentItem: Row {
            spacing: 8
            Repeater {
                model: root.labelOrientationChoices
                Button {
                    id: labelOrientationChoiceButton
                    readonly property string orientation: String(modelData.value || "horizontal")
                    readonly property bool choiceSelected: root.toolbarLabelOrientation === orientation
                    objectName: "graphEdgeLabelOrientationChoice_" + orientation
                    text: String(modelData.label || "")
                    width: 82
                    height: 34
                    padding: 0
                    onClicked: {
                        root._setFlowEdgeVisualStyle({
                            "label_orientation": labelOrientationChoiceButton.orientation === "follow_path" ? "follow_path" : ""
                        });
                    }
                    contentItem: Text {
                        text: labelOrientationChoiceButton.text
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: labelOrientationChoiceButton.choiceSelected ? root.accentColor : root.foregroundColor
                        font.pixelSize: 12
                        font.bold: labelOrientationChoiceButton.choiceSelected
                    }
                    background: Rectangle {
                        radius: 5
                        color: labelOrientationChoiceButton.choiceSelected
                            ? Qt.alpha(root.accentColor, 0.16)
                            : (labelOrientationChoiceButton.hovered ? Qt.alpha(root.foregroundColor, 0.10) : "transparent")
                    }
                }
            }

            Rectangle {
                width: 1
                height: 22
                anchors.verticalCenter: parent.verticalCenter
                color: Qt.alpha(root.chromeBorderColor, 0.74)
            }

            Button {
                id: labelAutoPositionButton
                objectName: "graphEdgeLabelAutoPositionButton"
                text: "Auto position"
                enabled: root.toolbarLabelPositioned
                width: 96
                height: 34
                padding: 0
                Common.ManagedToolTip {
                    policyBridge: root.canvasItem && root.canvasItem.canvasStateBridgeRef
                        ? root.canvasItem.canvasStateBridgeRef
                        : null
                    category: "general"
                    active: labelAutoPositionButton.hovered
                    text: "Return a dragged label to its automatic place"
                }
                onClicked: root._setFlowEdgeVisualStyle({ "label_position": "" })
                contentItem: Text {
                    text: labelAutoPositionButton.text
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: labelAutoPositionButton.enabled ? root.foregroundColor : root.mutedForegroundColor
                    opacity: labelAutoPositionButton.enabled ? 1.0 : 0.55
                    font.pixelSize: 12
                }
                background: Rectangle {
                    radius: 5
                    color: labelAutoPositionButton.hovered && labelAutoPositionButton.enabled
                        ? Qt.alpha(root.foregroundColor, 0.10)
                        : "transparent"
                }
            }
        }
    }
}
