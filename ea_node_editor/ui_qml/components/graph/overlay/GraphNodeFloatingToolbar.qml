import QtQuick 2.15
import QtQuick.Controls 2.15
import "../surface_controls" as GraphSurfaceControls
import "../../shell" as ShellComponents
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "toolbar_positioning.js" as ToolbarPositioning
import "../../common/contrast_utils.js" as ContrastUtils
import "../../common/TooltipCopy.js" as TooltipCopy

Item {
    id: root
    objectName: "graphNodeFloatingToolbar"

    property Item host: null
    property var canvasItem: null
    property var viewBridge: null
    property var visibleSceneRectPayload: ({})

    readonly property bool hostValid: !!root.host
    readonly property var hostNodeData: root.hostValid ? root.host.nodeData : null
    readonly property bool toolbarActive: root.hostValid && Boolean(root.host.toolbarActive)
    readonly property var toolbarMetrics: {
        if (!root.hostValid)
            return ({});
        var metrics = root.host.surfaceMetrics || {};
        return metrics.floating_toolbar ? metrics.floating_toolbar : ({});
    }
    readonly property var actionList: {
        if (!root.hostValid)
            return [];
        var actions = root.host.availableActions;
        return Array.isArray(actions) ? actions : [];
    }
    // compact_pill / minimal_ghost group surface-specific buttons on the left
    // and common (rename/duplicate/delete/...) buttons on the right so the two
    // families read as distinct groups separated by a thin divider. Other styles
    // keep the source order.
    readonly property bool _groupBySurfaceFamily:
        root.style === "compact_pill" || root.style === "minimal_ghost"
    readonly property var _orderedActions: {
        var all = root.actionList;
        if (!Array.isArray(all) || all.length === 0)
            return [];
        if (!root._groupBySurfaceFamily)
            return all;
        var surface = [];
        var common = [];
        for (var i = 0; i < all.length; i++) {
            var item = all[i] || {};
            if (String(item.kind || "") === "common")
                common.push(item);
            else
                surface.push(item);
        }
        return surface.concat(common);
    }
    readonly property color _requestedAccentColor: root.hostValid ? root.host.nodeThemeColor : "#4DA8DA"
    readonly property color _shellAccentColor: (typeof themeBridge !== "undefined"
            && themeBridge
            && themeBridge.palette
            && themeBridge.palette.accent)
        ? themeBridge.palette.accent
        : "#1D8CE0"
    // Chrome colors track the host's theme / shell palette so the toolbar
    // follows both graph-theme switches (dark/light) and per-node passive
    // overrides (shell colors) instead of staying hardcoded-dark.
    readonly property color _chromeBaseFill: root.hostValid ? root.host.surfaceColor : "#1b1d22"
    readonly property color _chromeBaseBorder: root.hostValid ? root.host.outlineColor : "#3a3d45"
    readonly property color _rawHeaderText: root.hostValid ? root.host.headerTextColor : "#f0f4fb"
    // Ghost icons float on the shell's canvas_bg but headerTextColor comes from the graph theme â€” some pairs drop below WCAG 3:1, so fall back to shell app_fg.
    readonly property string _canvasBg: (typeof themeBridge !== "undefined" && themeBridge && themeBridge.palette) ? String(themeBridge.palette.canvas_bg || "") : ""
    readonly property color _shellFallbackFg: (typeof themeBridge !== "undefined" && themeBridge && themeBridge.palette && themeBridge.palette.app_fg) ? themeBridge.palette.app_fg : "#f0f4fb"
    readonly property color _chromeForeground: {
        if (!root.hostValid || root.style !== "minimal_ghost")
            return root._rawHeaderText;
        return ContrastUtils.pickReadableForeground(root._rawHeaderText, root._shellFallbackFg, root._canvasBg, 3.0);
    }
    readonly property color accentColor: root._readableActionAccentColor()

    function _canvasStateBridge() {
        if (root.canvasItem) {
            if (root.canvasItem.canvasStateBridgeRef)
                return root.canvasItem.canvasStateBridgeRef;
        }
        return null;
    }

    function _readableActionAccentColor() {
        var background = root.style === "minimal_ghost" && root._canvasBg.length > 0
            ? root._canvasBg
            : String(root._chromeFillColor);
        var candidates = [
            String(root._requestedAccentColor),
            String(root._shellAccentColor),
            String(root._chromeForeground)
        ];
        for (var i = 0; i < candidates.length; i++) {
            var candidate = candidates[i];
            if (!ContrastUtils.parseColor(candidate))
                continue;
            if (ContrastUtils.contrastRatio(candidate, background) >= 1.8)
                return candidate;
        }
        return String(root._shellAccentColor);
    }

    function _actionColor(action, key, fallback) {
        var value = String(action && action[key] !== undefined ? action[key] : "").trim();
        if (value.length > 0 && ContrastUtils.parseColor(value))
            return value;
        return fallback;
    }

    function _dispatchToolbarAction(action) {
        if (!root.host)
            return false;
        var actionId = String(action && action.id !== undefined ? action.id : "");
        if (!actionId.length)
            return false;
        // `kind` is the routing discriminator, not the boolean result of the
        // dispatch. A surface action that is handled but produces no state
        // change (e.g. the colour picker is cancelled, or an already-applied
        // value is re-selected) returns false. That must not fall through to a
        // node action: the node router finds no descriptor for a surface action
        // id and re-routes it straight back to dispatchSurfaceAction, which
        // re-triggers the action and re-opens the colour dialog.
        var actionKind = String(action && action.kind || "");
        if ((actionKind === "surface" || actionKind === "media") && root.host.dispatchSurfaceAction)
            return Boolean(root.host.dispatchSurfaceAction(actionId));
        root.host.dispatchNodeAction(actionId, null);
        return true;
    }

    readonly property string style: {
        var bridge = root._canvasStateBridge();
        if (bridge && bridge.graphics_floating_toolbar_style !== undefined) {
            var value = String(bridge.graphics_floating_toolbar_style || "").toLowerCase();
            if (value === "compact_pill" || value === "segmented_bar" || value === "minimal_ghost")
                return value;
        }
        return "compact_pill";
    }

    readonly property string size: {
        var bridge = root._canvasStateBridge();
        if (bridge && bridge.graphics_floating_toolbar_size !== undefined) {
            var value = String(bridge.graphics_floating_toolbar_size || "").toLowerCase();
            if (value === "small" || value === "medium" || value === "large")
                return value;
        }
        return "small";
    }

    readonly property real _sizeScale: {
        if (root.size === "large") return 1.5;
        if (root.size === "medium") return 1.25;
        return 1.0;
    }

    readonly property bool _hasChrome: root.style !== "minimal_ghost"
    readonly property real _chromeRadius: {
        if (root.style === "compact_pill") return 999;
        if (root.style === "segmented_bar") return 7;
        return 0;
    }
    readonly property color _chromeFillColor: {
        if (root.style === "compact_pill")
            return Qt.rgba(root._chromeBaseFill.r, root._chromeBaseFill.g, root._chromeBaseFill.b, 0.96);
        if (root.style === "segmented_bar") return root._chromeBaseFill;
        return "transparent";
    }
    readonly property color _chromeBorderColor: {
        if (root.style === "compact_pill") return Qt.alpha(root._chromeBaseBorder, 0.55);
        if (root.style === "segmented_bar") return root._chromeBaseBorder;
        return "transparent";
    }
    readonly property real _chromeBorderWidth: root._hasChrome ? 1 : 0
    readonly property real _chromeInternalPadding: {
        var base;
        if (root.style === "compact_pill") base = 3;
        else if (root.style === "segmented_bar") base = 0;
        else base = 2;
        return base * root._sizeScale;
    }
    readonly property real _chromeButtonGap: {
        var base;
        if (root.style === "compact_pill") base = 2;
        else if (root.style === "segmented_bar") base = 0;
        else base = 2;
        return base * root._sizeScale;
    }
    readonly property bool _chromeClip: root.style === "segmented_bar"
    readonly property real _buttonChromeRadius: {
        if (root.style === "compact_pill") return 999;
        if (root.style === "segmented_bar") return 0;
        return 5;
    }
    readonly property int _buttonHPadding: {
        var base;
        if (root.style === "compact_pill") base = 7;
        else if (root.style === "segmented_bar") base = 12;
        else base = 6;
        return Math.round(base * root._sizeScale);
    }
    readonly property int _buttonVPadding: {
        var base;
        if (root.style === "compact_pill") base = 7;
        else if (root.style === "segmented_bar") base = 6;
        else base = 6;
        return Math.round(base * root._sizeScale);
    }
    readonly property int _buttonIconSize: {
        var base;
        if (root.style === "compact_pill") base = 15;
        else if (root.style === "segmented_bar") base = 14;
        else base = 14;
        return Math.round(base * root._sizeScale);
    }
    readonly property color _buttonHoverFillColor: {
        if (root.style === "minimal_ghost") return Qt.alpha(root._chromeForeground, 0.10);
        return Qt.alpha(root.accentColor, 0.18);
    }
    readonly property color _segmentedDividerColor: Qt.alpha(root._chromeBaseBorder, 0.75)
    readonly property color _minimalSeparatorColor: Qt.alpha(root._chromeForeground, 0.18)
    readonly property color _caretFillColor: root._hasChrome ? root._chromeFillColor : Qt.alpha(root.accentColor, 0.55)
    readonly property color _caretBorderColor: root._hasChrome ? root._chromeBorderColor : Qt.alpha(root.accentColor, 0.55)

    readonly property real gapFromNode: Number(toolbarMetrics.gap_from_node || 6)
    readonly property real safetyMargin: Number(toolbarMetrics.safety_margin || 8)
    readonly property real hysteresis: Number(toolbarMetrics.hysteresis || 8)
    readonly property int animationDuration: Number(toolbarMetrics.animation_duration_ms || 180)
    readonly property real toolbarHeightMetric: Number(toolbarMetrics.toolbar_height || 32)
    readonly property real _rawZoom: Number(
        root.viewBridge && root.viewBridge.zoom_value !== undefined
            ? root.viewBridge.zoom_value
            : 1.0
    )
    readonly property real _effectiveZoom: isFinite(root._rawZoom)
        ? Math.max(0.1, root._rawZoom)
        : 1.0

    readonly property var embeddedInteractiveRects: root.visible
        ? SurfaceControlGeometry.combineRectLists([
            SurfaceControlGeometry.rectList(SurfaceControlGeometry.rectFromItem(chromeContainer, root.host)),
            SurfaceControlGeometry.rectList(SurfaceControlGeometry.rectFromItem(actionPopover, root.host))
        ])
        : []
    readonly property rect toolbarRect: Qt.rect(root.x, root.y, root.width, root.height)

    property bool flipped: false
    Binding {
        target: root.host
        property: "floatingToolbarFlipped"
        value: root.flipped
        when: root.hostValid
    }
    Binding {
        target: root.host
        property: "floatingToolbarZoom"
        value: root._effectiveZoom
        when: root.hostValid
    }
    property bool runMenuVisible: false
    property real runMenuX: 0
    property real runMenuY: 0
    property var runMenuActions: []
    property bool actionPopoverVisible: false
    property real actionPopoverX: 0
    property real actionPopoverY: 0
    property real _lastPositionedActionPopoverImplicitWidth: -1
    property real _lastPositionedActionPopoverImplicitHeight: -1
    property real actionPopoverAnchorCenterX: 0
    property string actionPopoverOwnerId: ""
    property string actionPopoverLayout: "row"
    property var actionPopoverActions: []
    property string actionPopoverActionKind: "surface"
    property int actionPopoverFontSizeValue: 18
    property int actionPopoverFontSizeMin: 6
    property int actionPopoverFontSizeMax: 144
    property string actionPopoverFontSizeSetActionPrefix: "text_font_size_set:"
    property string actionPopoverFontSizePreviewActionPrefix: "text_font_size_preview:"
    property bool actionPopoverFontSizeDirty: false
    property int actionPopoverPageValue: 1
    property int actionPopoverPageMin: 1
    property int actionPopoverPageMax: 1
    property string actionPopoverPageSetActionPrefix: "pdf_page_set:"
    property int actionPopoverSourceStorageIndex: 0
    property string actionPopoverFilterText: ""
    readonly property int floatingToolbarPrimaryLevel: 1
    readonly property int floatingToolbarPopoverLevel: 2
    readonly property int floatingToolbarNestedPopoverLevel: 3
    readonly property int _popoverControlHeight: root._floatingToolbarControlHeight(root.floatingToolbarPopoverLevel)
    readonly property int _popoverIconSize: root._floatingToolbarIconSize(root.floatingToolbarPopoverLevel)
    readonly property int _popoverTextPixelSize: root._floatingToolbarTextPixelSize(root.floatingToolbarPopoverLevel)
    readonly property int _popoverHorizontalPadding: root._floatingToolbarHorizontalPadding(root.floatingToolbarPopoverLevel)
    readonly property int _popoverIconOnlyHorizontalPadding: root._floatingToolbarIconOnlyHorizontalPadding(root.floatingToolbarPopoverLevel)
    readonly property int _popoverVerticalPadding: root._floatingToolbarVerticalPadding(root.floatingToolbarPopoverLevel)
    readonly property int _popoverRadius: root._floatingToolbarRadius(root.floatingToolbarPopoverLevel)

    readonly property var nodeLocalRect: {
        if (!root.hostValid || !root.hostNodeData)
            return ({ x: 0, y: 0, width: 0, height: 0 });
        // host.x already folds in worldOffset plus the active drag (drag.target
        // mutates host.x directly during a drag). liveDragDx/Dy contribute the
        // multi-selection translate applied to non-anchor nodes via transform.
        var dragDx = root.host.dragTranslateX !== undefined
            ? Number(root.host.dragTranslateX || 0)
            : 0.0;
        var dragDy = root.host.dragTranslateY !== undefined
            ? Number(root.host.dragTranslateY || 0)
            : 0.0;
        return {
            x: Number(root.host.x || 0) + dragDx,
            y: Number(root.host.y || 0) + dragDy,
            width: Number(root.host.width || 0),
            height: Number(root.host.height || 0)
        };
    }
    readonly property var viewportLocalRect: {
        var payload = root.visibleSceneRectPayload || {};
        var offset = root.hostValid ? Number(root.host.worldOffset || 0) : 0;
        return {
            x: Number(payload.x || 0) + offset,
            y: Number(payload.y || 0) + offset,
            width: Number(payload.width || 0),
            height: Number(payload.height || 0)
        };
    }
    readonly property size toolbarSize: Qt.size(
        Math.max(1, chromeContainer.implicitWidth),
        Math.max(1, chromeContainer.implicitHeight)
    )
    readonly property var anchor: ToolbarPositioning.computeAnchor(
        root.nodeLocalRect,
        { width: root.toolbarSize.width, height: root.toolbarSize.height },
        root.viewportLocalRect,
        {
            gap_from_node: root.gapFromNode,
            safety_margin: root.safetyMargin,
            hysteresis: root.hysteresis
        },
        root.flipped
    )

    // `anchor` reads root.flipped for hysteresis, and used to write root.flipped
    // straight back here — since onAnchorChanged runs synchronously inside the
    // anchor property's own assignment, that write re-entered the still-settling
    // anchor binding and tripped QML's binding-loop detector. Deferring the sync
    // via Qt.callLater lets the assignment finish before flipped is updated;
    // repeated calls with the same function reference coalesce into one.
    onAnchorChanged: Qt.callLater(root._syncFlippedFromAnchor)

    function _syncFlippedFromAnchor() {
        if (Boolean(root.anchor.flipped) !== root.flipped)
            root.flipped = Boolean(root.anchor.flipped);
    }

    readonly property bool _nodeDragActive: root.hostValid && Boolean(root.host.hostDragActive)

    visible: root.toolbarActive && root.actionList.length > 0 && !root._nodeDragActive
    x: Number(root.anchor.x)
    y: Number(root.anchor.y)
    width: chromeContainer.implicitWidth
    height: chromeContainer.implicitHeight
    opacity: root.visible ? 1.0 : 0.0
    z: 40
    activeFocusOnTab: root.visible

    Behavior on opacity {
        NumberAnimation {
            duration: root.animationDuration
            easing.type: Easing.InOutCubic
        }
    }

    transform: Translate {
        id: slideTransform
        y: root.visible ? 0 : (root.flipped ? -root.gapFromNode : root.gapFromNode)
        Behavior on y {
            NumberAnimation {
                duration: root.animationDuration
                easing.type: Easing.OutCubic
            }
        }
    }

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    function _actionChecked(action) {
        var item = action || {};
        if (item.checked !== undefined)
            return Boolean(item.checked);
        return false;
    }

    function _menuActionsFor(action) {
        var item = action || {};
        var menuActions = item.menuActions;
        if (Array.isArray(menuActions))
            return menuActions;
        if (menuActions && menuActions.length !== undefined) {
            var resolved = [];
            for (var i = 0; i < menuActions.length; i++)
                resolved.push(menuActions[i]);
            return resolved;
        }
        return [];
    }

    function _popoverActionsFor(action) {
        var item = action || {};
        var popoverActions = item.popoverActions;
        if (Array.isArray(popoverActions))
            return popoverActions;
        if (popoverActions && popoverActions.length !== undefined) {
            var resolved = [];
            for (var i = 0; i < popoverActions.length; i++)
                resolved.push(popoverActions[i]);
            return resolved;
        }
        return [];
    }

    function _toolbarActionById(actionId) {
        var normalized = String(actionId || "");
        if (!normalized.length)
            return null;
        for (var index = 0; index < root.actionList.length; index++) {
            var action = root.actionList[index] || {};
            if (String(action.id || "") === normalized)
                return action;
        }
        return null;
    }

    function _refreshActionPopoverActions() {
        if (!root.actionPopoverVisible)
            return false;
        var action = root._toolbarActionById(root.actionPopoverOwnerId);
        var popoverActions = root._popoverActionsFor(action);
        if (!popoverActions.length)
            return false;
        root.actionPopoverActions = popoverActions;
        root.actionPopoverActionKind = String(action && action.kind !== undefined
            ? action.kind
            : root.actionPopoverActionKind);
        root.actionPopoverSourceStorageIndex = root._checkedPopoverActionIndex(popoverActions);
        root._positionActionPopover();
        Qt.callLater(root._positionActionPopover);
        return true;
    }

    function _filteredPopoverActions() {
        var filter = String(root.actionPopoverFilterText || "").trim().toLowerCase();
        if (!filter.length)
            return root.actionPopoverActions;
        var exact = [];
        var prefix = [];
        var contains = [];
        for (var index = 0; index < root.actionPopoverActions.length; index++) {
            var action = root.actionPopoverActions[index] || {};
            var label = String(action.label || action.toolbar_text || "");
            var normalized = label.toLowerCase();
            if (normalized === filter)
                exact.push(action);
            else if (normalized.indexOf(filter) === 0)
                prefix.push(action);
            else if (normalized.indexOf(filter) >= 0)
                contains.push(action);
        }
        return exact.concat(prefix, contains);
    }

    function _checkedPopoverActionIndex(actions) {
        var values = actions || [];
        for (var index = 0; index < values.length; index++) {
            if (root._actionChecked(values[index]))
                return index;
        }
        return values.length > 0 ? 0 : -1;
    }

    function _sourceStorageLabels() {
        var labels = [];
        for (var index = 0; index < root.actionPopoverActions.length; index++)
            labels.push(root._actionToolbarText(root.actionPopoverActions[index]));
        return labels;
    }

    function _sourceStorageActionAt(index) {
        if (!root.actionPopoverActions.length)
            return null;
        var boundedIndex = Math.max(
            0,
            Math.min(root.actionPopoverActions.length - 1, Math.round(Number(index || 0)))
        );
        return root.actionPopoverActions[boundedIndex] || null;
    }

    function _dispatchSourceStorageSelection(index) {
        var action = root._sourceStorageActionAt(index);
        if (!action)
            return false;
        return root._dispatchPopoverAction(action);
    }

    function _popoverActionById(actionId) {
        var normalized = String(actionId || "");
        for (var index = 0; index < root.actionPopoverActions.length; index++) {
            var action = root.actionPopoverActions[index] || {};
            if (String(action.id || "") === normalized)
                return action;
        }
        return null;
    }

    function _actionToolbarText(action) {
        var item = action || {};
        var toolbarText = String(item.toolbar_text !== undefined ? item.toolbar_text : "");
        if (toolbarText.length > 0)
            return toolbarText;
        return String(item.label || "");
    }

    function _actionTooltipText(action) {
        var item = action || {};
        var label = String(item.label || "");
        var description = String(item.description || "");
        return description.length > 0 ? label + "\n" + description : label;
    }

    function _actionToolbarIcon(action) {
        var item = action || {};
        var toolbarText = String(item.toolbar_text !== undefined ? item.toolbar_text : "");
        if (toolbarText.length > 0 && String(item.icon || "").length === 0)
            return "";
        return String(item.icon || "");
    }

    function _actionIconOnly(action) {
        var item = action || {};
        return String(item.toolbar_text !== undefined ? item.toolbar_text : "").length === 0;
    }

    function _floatingToolbarDepth(level) {
        var numeric = Math.round(Number(level));
        return isFinite(numeric) && numeric > 0 ? numeric : root.floatingToolbarPrimaryLevel;
    }

    function _floatingToolbarControlHeight(level) {
        var depth = root._floatingToolbarDepth(level);
        var baseVerticalPadding = Math.max(6, Math.round(8 * root._sizeScale));
        var baseHeight = Math.max(24, Math.round(root._buttonIconSize + baseVerticalPadding));
        var step = Math.max(1, Math.round(2 * root._sizeScale));
        return Math.max(22, baseHeight - Math.max(0, depth - root.floatingToolbarPrimaryLevel) * step);
    }

    function _floatingToolbarIconSize(level) {
        var depth = root._floatingToolbarDepth(level);
        var step = Math.max(1, Math.round(2 * root._sizeScale));
        return Math.max(12, root._buttonIconSize - Math.max(0, depth - root.floatingToolbarPrimaryLevel) * step);
    }

    function _floatingToolbarTextPixelSize(level) {
        var depth = root._floatingToolbarDepth(level);
        var baseSize = Math.max(11, Math.round(13 * root._sizeScale));
        var step = Math.max(1, Math.round(1 * root._sizeScale));
        return Math.max(10, baseSize - Math.max(0, depth - root.floatingToolbarPrimaryLevel) * step);
    }

    function _floatingToolbarHorizontalPadding(level) {
        var depth = root._floatingToolbarDepth(level);
        return Math.max(5, Math.round(7 * root._sizeScale) - Math.max(0, depth - root.floatingToolbarPrimaryLevel));
    }

    function _floatingToolbarIconOnlyHorizontalPadding(level) {
        var depth = root._floatingToolbarDepth(level);
        return Math.max(4, Math.round(5 * root._sizeScale) - Math.max(0, depth - root.floatingToolbarPrimaryLevel));
    }

    function _floatingToolbarVerticalPadding(level) {
        var controlHeight = root._floatingToolbarControlHeight(level);
        var iconSize = root._floatingToolbarIconSize(level);
        return Math.max(2, Math.floor((controlHeight - iconSize) * 0.5));
    }

    function _floatingToolbarRadius(level) {
        var depth = root._floatingToolbarDepth(level);
        return Math.max(4, Math.round(6 * root._sizeScale) - Math.max(0, depth - root.floatingToolbarPrimaryLevel));
    }

    function _boundedInteger(value, minimum, maximum, fallback) {
        var minValue = Math.round(Number(minimum));
        var maxValue = Math.round(Number(maximum));
        if (!isFinite(minValue))
            minValue = 0;
        if (!isFinite(maxValue) || maxValue < minValue)
            maxValue = minValue;
        var numeric = Math.round(Number(value));
        if (!isFinite(numeric))
            numeric = Math.round(Number(fallback));
        if (!isFinite(numeric))
            numeric = minValue;
        return Math.max(minValue, Math.min(maxValue, numeric));
    }

    function _sanitizeIntegerText(value) {
        return String(value === undefined || value === null ? "" : value).replace(/[^0-9]/g, "");
    }

    function _flushActionPopoverDraft() {
        if (root.actionPopoverActionKind === "surface"
                && root.host
                && root.host.dispatchSurfaceAction)
            root.host.dispatchSurfaceAction("text_style_flush");
    }

    function _closeActionPopover(flushDraft) {
        if (Boolean(flushDraft))
            root._flushActionPopoverDraft();
        root.actionPopoverVisible = false;
        root.actionPopoverFontSizeDirty = false;
        root.actionPopoverFilterText = "";
        root._lastPositionedActionPopoverImplicitWidth = -1;
        root._lastPositionedActionPopoverImplicitHeight = -1;
    }

    function _previewFontSizeValue(value) {
        var nextSize = root._boundedInteger(
            value,
            root.actionPopoverFontSizeMin,
            root.actionPopoverFontSizeMax,
            root.actionPopoverFontSizeValue
        );
        root.actionPopoverFontSizeValue = nextSize;
        root._syncFontSizeEditor(true);
        root.actionPopoverFontSizeDirty = true;
        return root._dispatchToolbarAction({
            "id": root.actionPopoverFontSizePreviewActionPrefix + String(nextSize),
            "kind": root.actionPopoverActionKind || "surface"
        });
    }

    function _commitFontSizeValue(value) {
        var nextSize = root._boundedInteger(
            value,
            root.actionPopoverFontSizeMin,
            root.actionPopoverFontSizeMax,
            root.actionPopoverFontSizeValue
        );
        root.actionPopoverFontSizeValue = nextSize;
        root._syncFontSizeEditor(true);
        root.actionPopoverFontSizeDirty = false;
        return root._dispatchToolbarAction({
            "id": root.actionPopoverFontSizeSetActionPrefix + String(nextSize),
            "kind": root.actionPopoverActionKind || "surface"
        });
    }

    function _commitFontSizeText(value) {
        var cleaned = root._sanitizeIntegerText(value);
        if (cleaned.length === 0) {
            root.actionPopoverFontSizeValue = root.actionPopoverFontSizeValue;
            return false;
        }
        return root._commitFontSizeValue(Number(cleaned));
    }

    function _syncFontSizeEditor(force) {
        if (fontSizeField && (Boolean(force) || !fontSizeField.activeFocus))
            fontSizeField.text = String(root.actionPopoverFontSizeValue);
    }

    function _commitPageNumberValue(value) {
        var nextPage = root._boundedInteger(
            value,
            root.actionPopoverPageMin,
            root.actionPopoverPageMax,
            root.actionPopoverPageValue
        );
        root.actionPopoverPageValue = nextPage;
        root._syncPageNumberEditor(true);
        return root._dispatchToolbarAction({
            "id": root.actionPopoverPageSetActionPrefix + String(nextPage),
            "kind": root.actionPopoverActionKind || "surface"
        });
    }

    function _commitPageNumberText(value) {
        var cleaned = root._sanitizeIntegerText(value);
        if (cleaned.length === 0) {
            root._syncPageNumberEditor(true);
            return false;
        }
        return root._commitPageNumberValue(Number(cleaned));
    }

    function _syncPageNumberEditor(force) {
        if (pdfPageField && (Boolean(force) || !pdfPageField.activeFocus))
            pdfPageField.text = String(root.actionPopoverPageValue);
    }

    function _positionActionPopover() {
        var popoverWidth = Math.max(1, Number(actionPopover.implicitWidth || actionPopover.width || 1));
        var popoverHeight = Math.max(1, Number(actionPopover.implicitHeight || actionPopover.height || 1));
        var edgeAllowance = 32;
        root.actionPopoverX = Math.max(
            -edgeAllowance,
            Math.min(
                chromeContainer.width - popoverWidth + edgeAllowance,
                root.actionPopoverAnchorCenterX - popoverWidth / 2
            )
        );
        root.actionPopoverY = root.flipped
            ? chromeContainer.height + 6
            : -popoverHeight - 6;
        root._lastPositionedActionPopoverImplicitWidth = popoverWidth;
        root._lastPositionedActionPopoverImplicitHeight = popoverHeight;
    }

    function _positionActionPopoverIfSizeMoved() {
        if (!root.actionPopoverVisible)
            return;
        var popoverWidth = Math.max(1, Number(actionPopover.implicitWidth || actionPopover.width || 1));
        var popoverHeight = Math.max(1, Number(actionPopover.implicitHeight || actionPopover.height || 1));
        if (root._lastPositionedActionPopoverImplicitWidth < 0
                || Math.abs(popoverWidth - root._lastPositionedActionPopoverImplicitWidth) >= 0.5
                || Math.abs(popoverHeight - root._lastPositionedActionPopoverImplicitHeight) >= 0.5) {
            root._positionActionPopover();
        }
    }

    function openActionPopover(action, anchorItem) {
        var popoverActions = root._popoverActionsFor(action);
        if (!popoverActions.length || !anchorItem)
            return;
        var ownerId = String(action && action.id !== undefined ? action.id : "");
        if (root.actionPopoverVisible && root.actionPopoverOwnerId === ownerId) {
            root._closeActionPopover(true);
            return;
        }
        root.runMenuVisible = false;
        root.actionPopoverOwnerId = ownerId;
        root.actionPopoverLayout = String(action && action.popover_layout !== undefined
            ? action.popover_layout
            : "row");
        root.actionPopoverActions = popoverActions;
        root.actionPopoverActionKind = String(action && action.kind !== undefined ? action.kind : "surface");
        root.actionPopoverFontSizeMin = root._boundedInteger(
            action && action.font_size_min !== undefined ? action.font_size_min : 6,
            1,
            999,
            6
        );
        root.actionPopoverFontSizeMax = root._boundedInteger(
            action && action.font_size_max !== undefined ? action.font_size_max : 144,
            root.actionPopoverFontSizeMin,
            999,
            144
        );
        root.actionPopoverFontSizeValue = root._boundedInteger(
            action && action.font_size_value !== undefined ? action.font_size_value : root.actionPopoverFontSizeValue,
            root.actionPopoverFontSizeMin,
            root.actionPopoverFontSizeMax,
            root.actionPopoverFontSizeMin
        );
        root.actionPopoverFontSizeSetActionPrefix = String(
            action && action.font_size_set_action_prefix !== undefined
                ? action.font_size_set_action_prefix
                : "text_font_size_set:"
        );
        root.actionPopoverFontSizePreviewActionPrefix = String(
            action && action.font_size_preview_action_prefix !== undefined
                ? action.font_size_preview_action_prefix
                : "text_font_size_preview:"
        );
        root.actionPopoverPageMin = root._boundedInteger(
            action && action.page_min !== undefined ? action.page_min : 1,
            1,
            99999,
            1
        );
        root.actionPopoverPageMax = root._boundedInteger(
            action && action.page_max !== undefined ? action.page_max : root.actionPopoverPageMin,
            root.actionPopoverPageMin,
            99999,
            root.actionPopoverPageMin
        );
        root.actionPopoverPageValue = root._boundedInteger(
            action && action.page_value !== undefined ? action.page_value : root.actionPopoverPageValue,
            root.actionPopoverPageMin,
            root.actionPopoverPageMax,
            root.actionPopoverPageMin
        );
        root.actionPopoverPageSetActionPrefix = String(
            action && action.page_set_action_prefix !== undefined
                ? action.page_set_action_prefix
                : "pdf_page_set:"
        );
        root.actionPopoverSourceStorageIndex = root._checkedPopoverActionIndex(popoverActions);
        root.actionPopoverFontSizeDirty = false;
        root.actionPopoverFilterText = "";
        var anchor = anchorItem.mapToItem(root, anchorItem.width / 2, 0);
        root.actionPopoverAnchorCenterX = anchor.x;
        root.actionPopoverVisible = true;
        root._positionActionPopover();
        Qt.callLater(root._positionActionPopover);
        Qt.callLater(root._syncFontSizeEditor);
        Qt.callLater(root._syncPageNumberEditor);
        if (root.actionPopoverLayout === "font_family")
            Qt.callLater(function() {
                if (fontFamilySearchField)
                    fontFamilySearchField.forceActiveFocus();
            });
    }

    function _dispatchPopoverAction(action) {
        var dispatched = root._dispatchToolbarAction(action);
        if (Boolean(action && action.close_popover)) {
            root._closeActionPopover(true);
        } else {
            Qt.callLater(root._refreshActionPopoverActions);
        }
        return dispatched;
    }

    onActionListChanged: root._refreshActionPopoverActions()

    function openActionMenu(action, anchorItem) {
        root.runMenuActions = root._menuActionsFor(action);
        if (!root.runMenuActions.length || !anchorItem)
            return;
        root._closeActionPopover(true);
        var anchor = anchorItem.mapToItem(root, 0, root.flipped ? anchorItem.height + 4 : -4);
        root.runMenuX = anchor.x - 4;
        var estimatedHeight = 18 + root.runMenuActions.length * 35;
        root.runMenuY = root.flipped ? anchor.y : anchor.y - estimatedHeight;
        root.runMenuVisible = true;
    }

    // Propagate hover state back to the host so toolbarActiveSource stays true
    // while the cursor is on the chrome or in the gap bridging it to the node.
    // The gap bridge widens the effective hover target across the visible gap
    // so slow cursor movement does not race the 120 ms grace timer.
    readonly property bool pointerOnToolbar: chromeHoverHandler.hovered
        || bridgeHoverHandler.hovered
        || actionPopoverHoverHandler.hovered
        || actionPopoverBridgeHoverHandler.hovered
        || runMenuHoverHandler.hovered
        || runMenuBridgeHoverHandler.hovered
    onPointerOnToolbarChanged: {
        if (root.hostValid)
            root.host.toolbarPointerInside = root.pointerOnToolbar;
    }
    onHostChanged: {
        if (_previousHost && _previousHost.toolbarPointerInside !== undefined)
            _previousHost.toolbarPointerInside = false;
        _previousHost = root.host;
        if (root.hostValid)
            root.host.toolbarPointerInside = root.pointerOnToolbar;
        root.runMenuVisible = false;
        root._closeActionPopover(false);
    }
    property Item _previousHost: null

    HoverHandler {
        id: chromeHoverHandler
    }

    Item {
        id: hoverBridge
        objectName: "graphNodeFloatingToolbarHoverBridge"
        width: chromeContainer.width
        height: Math.max(1, root.gapFromNode)
        x: 0
        y: root.flipped ? -height : chromeContainer.height

        HoverHandler {
            id: bridgeHoverHandler
        }
    }

    readonly property real _ownerCenterX: {
        if (!root.hostValid)
            return chromeContainer.width / 2;
        var rect = root.nodeLocalRect;
        return rect.x + rect.width / 2 - root.x;
    }

    Rectangle {
        id: ownershipCaret
        objectName: "graphNodeFloatingToolbarCaret"
        visible: root._hasChrome
        z: -1
        width: 9
        height: 9
        rotation: 45
        antialiasing: true
        color: root._caretFillColor
        border.width: 1
        border.color: root._caretBorderColor

        readonly property real caretEdgeMargin: 6
        readonly property real clampedCenterX: Math.max(
            caretEdgeMargin + width / 2,
            Math.min(
                chromeContainer.width - caretEdgeMargin - width / 2,
                root._ownerCenterX
            )
        )
        x: clampedCenterX - width / 2
        y: root.flipped
            ? -height / 2 - 0.5
            : chromeContainer.height - height / 2 + 0.5
    }

    Image {
        id: ownershipChevron
        objectName: "graphNodeFloatingToolbarChevron"
        visible: !root._hasChrome
        z: -1
        width: 24
        height: 24
        smooth: true
        antialiasing: true
        source: root._iconSource(
            root.flipped ? "chevron-down" : "chevron-up",
            24,
            root._chromeForeground
        )
        sourceSize: Qt.size(24, 24)

        readonly property real clampedCenterX: Math.max(
            width / 2,
            Math.min(
                chromeContainer.width - width / 2,
                root._ownerCenterX
            )
        )
        x: clampedCenterX - width / 2
        y: root.flipped ? -height + 8 : chromeContainer.height - 9
    }

    Rectangle {
        id: chromeContainer
        objectName: "graphNodeFloatingToolbarChrome"
        radius: root._chromeRadius
        color: root._chromeFillColor
        border.width: root._chromeBorderWidth
        border.color: root._chromeBorderColor
        clip: root._chromeClip

        implicitWidth: buttonRow.implicitWidth + root._chromeInternalPadding * 2
        implicitHeight: Math.max(root.toolbarHeightMetric, buttonRow.implicitHeight + root._chromeInternalPadding * 2)

        Row {
            id: buttonRow
            anchors.centerIn: parent
            spacing: root._chromeButtonGap

            Repeater {
                id: buttonRepeater
                model: root._orderedActions

                Row {
                    id: buttonCell
                    spacing: 0
                    height: actionButton.implicitHeight

                    readonly property bool _isFirst: index === 0
                    readonly property bool _isLast: index === buttonRepeater.count - 1
                    readonly property bool _isDestructive: Boolean(modelData.destructive)
                    readonly property bool _isCommon: String((modelData || {}).kind || "") === "common"
                    readonly property var _menuActions: root._menuActionsFor(modelData)
                    readonly property bool _hasMenu: buttonCell._menuActions.length > 0
                    readonly property var _popoverActions: root._popoverActionsFor(modelData)
                    readonly property bool _hasPopover: buttonCell._popoverActions.length > 0
                    readonly property bool _startsCommonGroup: {
                        if (!root._groupBySurfaceFamily || !buttonCell._isCommon || buttonCell._isFirst)
                            return false;
                        var prev = root._orderedActions[index - 1] || {};
                        return String(prev.kind || "") !== "common";
                    }
                    readonly property bool _showLeadingSeparator:
                        buttonCell._startsCommonGroup
                        || Boolean((modelData || {}).separator_before)
                        || (index > 0 && Boolean((root._orderedActions[index - 1] || {}).separator_after))
                        || (root.style === "minimal_ghost" && buttonCell._isDestructive && !buttonCell._isFirst)

                    Item {
                        id: leadingSeparatorSlot
                        visible: buttonCell._showLeadingSeparator
                        width: visible ? 9 : 0
                        height: buttonCell.height
                        Rectangle {
                            anchors.centerIn: parent
                            width: 1
                            height: parent.height - 8
                            color: root._minimalSeparatorColor
                        }
                    }

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: actionButton
                        objectName: "graphNodeFloatingToolbarAction_" + String(modelData.id || "")
                        host: root.host
                        text: root._actionToolbarText(modelData)
                        iconName: root._actionToolbarIcon(modelData)
                        iconOnly: root._actionIconOnly(modelData)
                        iconSize: root._buttonIconSize
                        iconSourceResolver: function(name, size, color) {
                            return root._iconSource(name, size, color);
                        }
                        accentColor: buttonCell._isDestructive
                            ? "#D94F4F"
                            : root._actionColor(modelData, "accent_color", root.accentColor)
                        foregroundColor: root._actionColor(modelData, "foreground_color", root._chromeForeground)
                        enabled: modelData.enabled !== false
                        active: root._actionChecked(modelData)
                        chromeRadius: root._buttonChromeRadius
                        contentHorizontalPadding: root._buttonHPadding
                        contentVerticalPadding: root._buttonVPadding
                        tooltipText: root._actionTooltipText(modelData)
                        tooltipCategory: "general"
                        tooltipScreenStablePositioning: true
                        tooltipAnchorScale: root._effectiveZoom
                        tooltipScreenGap: 8
                        tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                        baseFillColor: "transparent"
                        baseBorderColor: "transparent"
                        hoverFillColor: root._buttonHoverFillColor
                        hoverBorderColor: root._buttonHoverFillColor
                        hoverBorderWidth: 1
                        focusPolicy: Qt.TabFocus
                        onControlStarted: {
                            // A live viewer can republish this model when focus clears.
                            // Let fullscreen dispatch prepare the surface after the click
                            // so the pressed delegate survives through mouse release.
                            if (String(modelData.id || "") === "fullscreen")
                                return;
                            if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                        }
                        onClicked: {
                            if (!root.host)
                                return;
                            root.runMenuVisible = false;
                            if (buttonCell._hasPopover)
                                root.openActionPopover(modelData, actionButton);
                            else
                                root._dispatchToolbarAction(modelData);
                        }
                        Keys.onReturnPressed: actionButton.clicked()
                        Keys.onEnterPressed: actionButton.clicked()
                    }

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: actionMenuButton
                        objectName: "graphNodeFloatingToolbarActionMenu_" + String(modelData.id || "")
                        visible: buttonCell._hasMenu
                        host: root.host
                        text: String(modelData.label || "") + " menu"
                        iconName: "chevron-down"
                        iconOnly: true
                        iconSize: Math.max(10, root._buttonIconSize - 3)
                        iconSourceResolver: function(name, size, color) {
                            return root._iconSource(name, size, color);
                        }
                        foregroundColor: root._chromeForeground
                        accentColor: root.accentColor
                        enabled: modelData.enabled !== false
                        chromeRadius: root._buttonChromeRadius
                        contentHorizontalPadding: Math.max(4, Math.round(root._buttonHPadding * 0.55))
                        contentVerticalPadding: root._buttonVPadding
                        tooltipText: String(modelData.label || "") + TooltipCopy.text(tooltipCopyBridge, "fullscreen.toolbar.options_suffix")
                        tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "fullscreen.toolbar.options_suffix")
                        tooltipScreenStablePositioning: true
                        tooltipAnchorScale: root._effectiveZoom
                        tooltipScreenGap: 8
                        tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                        baseFillColor: "transparent"
                        baseBorderColor: "transparent"
                        hoverFillColor: root._buttonHoverFillColor
                        hoverBorderColor: root._buttonHoverFillColor
                        hoverBorderWidth: 1
                        focusPolicy: Qt.TabFocus
                        onControlStarted: {
                            if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                        }
                        onClicked: root.openActionMenu(modelData, actionMenuButton)
                        Keys.onReturnPressed: actionMenuButton.clicked()
                        Keys.onEnterPressed: actionMenuButton.clicked()
                    }

                    Rectangle {
                        id: trailingDivider
                        visible: root.style === "segmented_bar" && !buttonCell._isLast
                        width: visible ? 1 : 0
                        height: buttonCell.height
                        color: root._segmentedDividerColor
                    }
                }
            }
        }
    }

    Item {
        id: actionPopoverBridge
        objectName: "graphNodeFloatingToolbarActionPopoverBridge"
        visible: actionPopover.visible
        x: Math.min(0, actionPopover.x)
        y: root.flipped ? chromeContainer.height : actionPopover.y + actionPopover.height
        width: Math.max(chromeContainer.width, actionPopover.x + actionPopover.width) - x
        height: 6
        z: 79

        HoverHandler {
            id: actionPopoverBridgeHoverHandler
        }
    }

    Rectangle {
        id: actionPopover
        objectName: "graphNodeFloatingToolbarActionPopover"
        visible: root.visible && root.actionPopoverVisible && root.actionPopoverActions.length > 0
        x: root.actionPopoverX
        y: root.actionPopoverY
        z: 80
        radius: 14
        antialiasing: true
        color: Qt.alpha(root._chromeBaseFill, 0.98)
        border.width: 1
        border.color: Qt.alpha(root._chromeBaseBorder, 0.72)

        readonly property real innerPadding: Math.round(6 * root._sizeScale)

        implicitWidth: actionPopoverContent.implicitWidth + innerPadding * 2
        implicitHeight: actionPopoverContent.implicitHeight + innerPadding * 2
        width: implicitWidth
        height: implicitHeight

        onImplicitWidthChanged: {
            root._positionActionPopoverIfSizeMoved();
        }
        onImplicitHeightChanged: {
            root._positionActionPopoverIfSizeMoved();
        }

        HoverHandler {
            id: actionPopoverHoverHandler
        }

        Item {
            id: actionPopoverContent
            anchors.centerIn: parent
            implicitWidth: root.actionPopoverLayout === "font_size"
                ? fontSizePopoverPanel.implicitWidth
                : (root.actionPopoverLayout === "font_family"
                    ? fontFamilyPopoverPanel.preferredWidth
                    : (root.actionPopoverLayout === "pdf_page"
                        ? pdfPagePopoverPanel.implicitWidth
                        : (root.actionPopoverLayout === "source_storage"
                            ? sourceStoragePopoverPanel.implicitWidth
                            : (root.actionPopoverLayout === "video_bookmarks"
                                ? videoBookmarksPopoverPanel.implicitWidth
                                : actionPopoverRow.implicitWidth))))
            implicitHeight: root.actionPopoverLayout === "font_size"
                ? fontSizePopoverPanel.implicitHeight
                : (root.actionPopoverLayout === "font_family"
                    ? fontFamilyPopoverPanel.preferredHeight
                    : (root.actionPopoverLayout === "pdf_page"
                        ? pdfPagePopoverPanel.implicitHeight
                        : (root.actionPopoverLayout === "source_storage"
                            ? sourceStoragePopoverPanel.implicitHeight
                            : (root.actionPopoverLayout === "video_bookmarks"
                                ? videoBookmarksPopoverPanel.implicitHeight
                                : actionPopoverRow.implicitHeight))))

            Row {
                id: actionPopoverRow
                visible: root.actionPopoverLayout !== "font_size"
                    && root.actionPopoverLayout !== "font_family"
                    && root.actionPopoverLayout !== "pdf_page"
                    && root.actionPopoverLayout !== "source_storage"
                    && root.actionPopoverLayout !== "video_bookmarks"
                anchors.centerIn: parent
                spacing: root._popoverIconOnlyHorizontalPadding

                Repeater {
                    model: root.actionPopoverLayout === "font_size"
                        || root.actionPopoverLayout === "font_family"
                        || root.actionPopoverLayout === "pdf_page"
                        || root.actionPopoverLayout === "source_storage"
                        || root.actionPopoverLayout === "video_bookmarks"
                        ? []
                        : root.actionPopoverActions

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: popoverActionButton
                        objectName: "graphNodeFloatingToolbarPopoverAction_" + String(modelData.id || "")
                        host: root.host
                        text: root._actionToolbarText(modelData)
                        iconName: root._actionToolbarIcon(modelData)
                        iconOnly: root._actionIconOnly(modelData)
                        iconSize: root._popoverIconSize
                        controlHeight: root._popoverControlHeight
                        chromeRadius: root._popoverRadius
                        contentVerticalPadding: root._popoverVerticalPadding
                        iconSourceResolver: function(name, size, color) {
                            return root._iconSource(name, size, color);
                        }
                        accentColor: root._actionColor(modelData, "accent_color", root.accentColor)
                        foregroundColor: root._actionColor(modelData, "foreground_color", root._chromeForeground)
                        enabled: modelData.enabled !== false
                        active: root._actionChecked(modelData)
                        contentHorizontalPadding: root._actionIconOnly(modelData)
                            ? root._popoverIconOnlyHorizontalPadding
                            : root._popoverHorizontalPadding
                        tooltipText: root._actionTooltipText(modelData)
                        tooltipCategory: "general"
                        tooltipScreenStablePositioning: true
                        tooltipAnchorScale: root._effectiveZoom
                        tooltipScreenGap: 8
                        tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                        baseFillColor: "transparent"
                        baseBorderColor: "transparent"
                        hoverFillColor: root._buttonHoverFillColor
                        hoverBorderColor: root._buttonHoverFillColor
                        activeFillColor: Qt.alpha(root.accentColor, 0.30)
                        activeBorderColor: Qt.alpha(root.accentColor, 0.82)
                        hoverBorderWidth: 1
                        focusPolicy: Qt.TabFocus
                        onControlStarted: {
                            if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                        }
                        onClicked: root._dispatchPopoverAction(modelData)
                        Keys.onReturnPressed: popoverActionButton.clicked()
                        Keys.onEnterPressed: popoverActionButton.clicked()
                    }
                }
            }

            Row {
                id: sourceStoragePopoverPanel
                objectName: "graphNodeFloatingToolbarSourceStoragePanel"
                visible: root.actionPopoverLayout === "source_storage"
                anchors.centerIn: parent
                spacing: root._popoverHorizontalPadding

                GraphSurfaceControls.GraphSurfaceComboBox {
                    id: sourceStorageCombo
                    controlHeight: root._popoverControlHeight
                    controlRadius: root._popoverRadius
                    contentLeftPadding: root._popoverHorizontalPadding
                    contentRightPadding: Math.max(20, root._popoverHorizontalPadding + 14)
                    indicatorRightMargin: root._popoverHorizontalPadding
                    popupControlHeight: root._floatingToolbarControlHeight(root.floatingToolbarNestedPopoverLevel)
                    objectName: "graphNodeFloatingToolbarSourceStorageCombo"
                    host: root.host
                    width: Math.round(112 * root._sizeScale)
                    height: root._popoverControlHeight
                    model: root._sourceStorageLabels()
                    currentIndex: root.actionPopoverSourceStorageIndex
                    enabled: root.actionPopoverActions.length > 1
                    font.pixelSize: root._popoverTextPixelSize
                    font.weight: Font.DemiBold
                    fillColor: Qt.alpha(root._chromeForeground, 0.10)
                    borderColor: Qt.alpha(root._chromeForeground, 0.20)
                    focusBorderColor: root.accentColor
                    accentColor: root.accentColor
                    textColor: root._chromeForeground
                    popupFillColor: root._chromeBaseFill
                    popupBorderColor: Qt.alpha(root._chromeBaseBorder, 0.82)
                    onControlStarted: {
                        if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                            root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                    }
                    onActivated: root.actionPopoverSourceStorageIndex = currentIndex
                }

                GraphSurfaceControls.GraphSurfaceButton {
                    id: sourceStorageBrowseButton
                    objectName: "graphNodeFloatingToolbarSourceBrowseButton"
                    host: root.host
                    text: "Browse"
                    iconName: "folder-open"
                    iconOnly: false
                    iconSize: root._popoverIconSize
                    controlHeight: root._popoverControlHeight
                    chromeRadius: root._popoverRadius
                    contentVerticalPadding: root._popoverVerticalPadding
                    font.pixelSize: root._popoverTextPixelSize
                    iconSourceResolver: function(name, size, color) {
                        return root._iconSource(name, size, color);
                    }
                    accentColor: root.accentColor
                    foregroundColor: root._chromeForeground
                    enabled: root._sourceStorageActionAt(sourceStorageCombo.currentIndex) !== null
                        && root._sourceStorageActionAt(sourceStorageCombo.currentIndex).enabled !== false
                    contentHorizontalPadding: root._popoverHorizontalPadding
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.source.choose_file")
                    tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "fullscreen.source.choose_file")
                    tooltipScreenStablePositioning: true
                    tooltipAnchorScale: root._effectiveZoom
                    tooltipScreenGap: 8
                    tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                    baseFillColor: "transparent"
                    baseBorderColor: "transparent"
                    hoverFillColor: root._buttonHoverFillColor
                    hoverBorderColor: root._buttonHoverFillColor
                    hoverBorderWidth: 1
                    focusPolicy: Qt.TabFocus
                    onControlStarted: {
                        if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                            root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                    }
                    onClicked: root._dispatchSourceStorageSelection(sourceStorageCombo.currentIndex)
                    Keys.onReturnPressed: sourceStorageBrowseButton.clicked()
                    Keys.onEnterPressed: sourceStorageBrowseButton.clicked()
                }
            }

            Item {
                id: videoBookmarksPopoverPanel
                objectName: "graphNodeFloatingToolbarVideoBookmarksPanel"
                visible: root.actionPopoverLayout === "video_bookmarks"
                anchors.centerIn: parent
                readonly property int preferredWidth: root._popoverControlHeight * 7
                    + root._popoverHorizontalPadding * 6
                readonly property int preferredHeight: root._popoverControlHeight * 7
                    + root._popoverVerticalPadding * 8
                implicitWidth: preferredWidth
                implicitHeight: Math.min(
                    preferredHeight,
                    Math.max(root._popoverControlHeight, videoBookmarkColumn.implicitHeight)
                )

                ScrollView {
                    id: videoBookmarkScroll
                    objectName: "graphNodeFloatingToolbarVideoBookmarkScroll"
                    width: videoBookmarksPopoverPanel.preferredWidth
                    height: videoBookmarksPopoverPanel.implicitHeight
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: videoBookmarkColumn.implicitHeight > height
                        ? ScrollBar.AsNeeded
                        : ScrollBar.AlwaysOff

                    Column {
                        id: videoBookmarkColumn
                        objectName: "graphNodeFloatingToolbarVideoBookmarkList"
                        width: videoBookmarkScroll.width
                        spacing: root._popoverVerticalPadding

                        Repeater {
                            model: root.actionPopoverLayout === "video_bookmarks" ? root.actionPopoverActions : []

                            Item {
                                id: videoBookmarkDelegate
                                readonly property var actionData: modelData || ({})
                                readonly property bool addRow: String(actionData.role || "") === "add"
                                readonly property bool bookmarkRow: String(actionData.role || "") === "bookmark"
                                width: videoBookmarkColumn.width
                                height: addRow
                                    ? addBookmarkButton.implicitHeight
                                    : Math.max(root._popoverControlHeight, bookmarkRowContent.implicitHeight)

                                GraphSurfaceControls.GraphSurfaceButton {
                                    id: addBookmarkButton
                                    objectName: "graphNodeFloatingToolbarPopoverAction_" + String(videoBookmarkDelegate.actionData.id || "")
                                    visible: videoBookmarkDelegate.addRow
                                    width: parent.width
                                    host: root.host
                                    text: root._actionToolbarText(videoBookmarkDelegate.actionData)
                                    iconName: root._actionToolbarIcon(videoBookmarkDelegate.actionData)
                                    iconOnly: false
                                    iconSize: root._popoverIconSize
                                    controlHeight: root._popoverControlHeight
                                    chromeRadius: root._popoverRadius
                                    contentVerticalPadding: root._popoverVerticalPadding
                                    font.pixelSize: root._popoverTextPixelSize
                                    iconSourceResolver: function(name, size, color) {
                                        return root._iconSource(name, size, color);
                                    }
                                    accentColor: root.accentColor
                                    foregroundColor: root._chromeForeground
                                    enabled: videoBookmarkDelegate.actionData.enabled !== false
                                    contentHorizontalPadding: root._popoverHorizontalPadding
                                    tooltipText: String(videoBookmarkDelegate.actionData.label || "")
                                    tooltipCategory: "general"
                                    tooltipScreenStablePositioning: true
                                    tooltipAnchorScale: root._effectiveZoom
                                    tooltipScreenGap: 8
                                    tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                                    baseFillColor: Qt.alpha(root._chromeForeground, 0.08)
                                    baseBorderColor: Qt.alpha(root._chromeForeground, 0.12)
                                    hoverFillColor: root._buttonHoverFillColor
                                    hoverBorderColor: root._buttonHoverFillColor
                                    hoverBorderWidth: 1
                                    focusPolicy: Qt.TabFocus
                                    onControlStarted: {
                                        if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                            root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                                    }
                                    onClicked: root._dispatchPopoverAction(videoBookmarkDelegate.actionData)
                                    Keys.onReturnPressed: addBookmarkButton.clicked()
                                    Keys.onEnterPressed: addBookmarkButton.clicked()
                                }

                                Row {
                                    id: bookmarkRowContent
                                    visible: videoBookmarkDelegate.bookmarkRow
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: root._popoverIconOnlyHorizontalPadding

                                    TextField {
                                        id: bookmarkLabelField
                                        objectName: "graphNodeFloatingToolbarVideoBookmarkLabel_" + String(videoBookmarkDelegate.actionData.bookmark_id || "")
                                        width: Math.max(82, videoBookmarkColumn.width
                                            - jumpBookmarkButton.width
                                            - deleteBookmarkButton.width
                                            - root._popoverIconOnlyHorizontalPadding * 2)
                                        height: root._popoverControlHeight
                                        text: String(videoBookmarkDelegate.actionData.label || "")
                                        placeholderText: String(videoBookmarkDelegate.actionData.time_text || "")
                                        color: root._chromeForeground
                                        placeholderTextColor: Qt.alpha(root._chromeForeground, 0.52)
                                        selectedTextColor: root._chromeForeground
                                        selectionColor: Qt.alpha(root.accentColor, 0.45)
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: root._popoverTextPixelSize
                                        selectByMouse: true
                                        background: Rectangle {
                                            radius: root._popoverRadius
                                            color: Qt.alpha(root._chromeForeground, 0.08)
                                            border.width: bookmarkLabelField.activeFocus ? 1 : 0
                                            border.color: Qt.alpha(root.accentColor, 0.72)
                                        }
                                        onEditingFinished: {
                                            var original = String(videoBookmarkDelegate.actionData.label || "");
                                            var updated = String(bookmarkLabelField.text || "").trim();
                                            if (updated.length > 0 && updated !== original) {
                                                root._dispatchPopoverAction({
                                                    "id": String(videoBookmarkDelegate.actionData.rename_action_prefix || "")
                                                        + encodeURIComponent(updated),
                                                    "kind": root.actionPopoverActionKind || "surface",
                                                    "close_popover": false
                                                });
                                            }
                                        }
                                        Keys.onEscapePressed: {
                                            bookmarkLabelField.text = String(videoBookmarkDelegate.actionData.label || "");
                                            bookmarkLabelField.focus = false;
                                        }
                                    }

                                    GraphSurfaceControls.GraphSurfaceButton {
                                        id: jumpBookmarkButton
                                        objectName: "graphNodeFloatingToolbarVideoBookmarkJump_" + String(videoBookmarkDelegate.actionData.bookmark_id || "")
                                        host: root.host
                                        text: "Jump"
                                        iconName: root._actionToolbarIcon(videoBookmarkDelegate.actionData)
                                        iconOnly: true
                                        iconSize: root._popoverIconSize
                                        controlHeight: root._popoverControlHeight
                                        chromeRadius: root._popoverRadius
                                        contentVerticalPadding: root._popoverVerticalPadding
                                        iconSourceResolver: function(name, size, color) {
                                            return root._iconSource(name, size, color);
                                        }
                                        accentColor: root.accentColor
                                        foregroundColor: root._chromeForeground
                                        contentHorizontalPadding: root._popoverIconOnlyHorizontalPadding
                                            tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.bookmark_jump")
                                            tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "fullscreen.video.bookmark_jump")
                                        tooltipScreenStablePositioning: true
                                        tooltipAnchorScale: root._effectiveZoom
                                        tooltipScreenGap: 8
                                        tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                                        baseFillColor: "transparent"
                                        baseBorderColor: "transparent"
                                        hoverFillColor: root._buttonHoverFillColor
                                        hoverBorderColor: root._buttonHoverFillColor
                                        hoverBorderWidth: 1
                                        focusPolicy: Qt.TabFocus
                                        onControlStarted: {
                                            if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                                root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                                        }
                                        onClicked: root._dispatchPopoverAction(videoBookmarkDelegate.actionData)
                                        Keys.onReturnPressed: jumpBookmarkButton.clicked()
                                        Keys.onEnterPressed: jumpBookmarkButton.clicked()
                                    }

                                    GraphSurfaceControls.GraphSurfaceButton {
                                        id: deleteBookmarkButton
                                        objectName: "graphNodeFloatingToolbarVideoBookmarkDelete_" + String(videoBookmarkDelegate.actionData.bookmark_id || "")
                                        host: root.host
                                        text: "Delete"
                                        iconName: "x"
                                        iconOnly: true
                                        iconSize: root._popoverIconSize
                                        controlHeight: root._popoverControlHeight
                                        chromeRadius: root._popoverRadius
                                        contentVerticalPadding: root._popoverVerticalPadding
                                        iconSourceResolver: function(name, size, color) {
                                            return root._iconSource(name, size, color);
                                        }
                                        accentColor: "#D94F4F"
                                        foregroundColor: root._chromeForeground
                                        contentHorizontalPadding: root._popoverIconOnlyHorizontalPadding
                                            tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.bookmark_delete")
                                            tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "fullscreen.video.bookmark_delete")
                                        tooltipScreenStablePositioning: true
                                        tooltipAnchorScale: root._effectiveZoom
                                        tooltipScreenGap: 8
                                        tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                                        baseFillColor: "transparent"
                                        baseBorderColor: "transparent"
                                        hoverFillColor: Qt.alpha("#D94F4F", 0.22)
                                        hoverBorderColor: Qt.alpha("#D94F4F", 0.42)
                                        hoverBorderWidth: 1
                                        focusPolicy: Qt.TabFocus
                                        onControlStarted: {
                                            if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                                root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                                        }
                                        onClicked: root._dispatchPopoverAction({
                                            "id": String(videoBookmarkDelegate.actionData.delete_action_id || ""),
                                            "kind": root.actionPopoverActionKind || "surface",
                                            "close_popover": false
                                        })
                                        Keys.onReturnPressed: deleteBookmarkButton.clicked()
                                        Keys.onEnterPressed: deleteBookmarkButton.clicked()
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Row {
                id: fontSizePopoverPanel
                objectName: "graphNodeFloatingToolbarFontSizePanel"
                visible: root.actionPopoverLayout === "font_size"
                anchors.centerIn: parent
                spacing: root._popoverHorizontalPadding

                TextField {
                    id: fontSizeField
                    objectName: "graphNodeFloatingToolbarFontSizeField"
                    width: Math.round(56 * root._sizeScale)
                    height: root._popoverControlHeight
                    text: String(root.actionPopoverFontSizeValue)
                    color: root._chromeForeground
                    selectedTextColor: root._chromeForeground
                    selectionColor: Qt.alpha(root.accentColor, 0.45)
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Math.max(root._popoverTextPixelSize, root._popoverIconSize)
                    font.weight: Font.DemiBold
                    selectByMouse: true
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator {
                        bottom: root.actionPopoverFontSizeMin
                        top: root.actionPopoverFontSizeMax
                    }
                    background: Rectangle {
                        radius: root._popoverRadius
                        color: Qt.alpha(root._chromeForeground, 0.10)
                        border.width: fontSizeField.activeFocus ? 1 : 0
                        border.color: Qt.alpha(root.accentColor, 0.72)
                    }
                    onTextEdited: {
                        var cleaned = root._sanitizeIntegerText(fontSizeField.text);
                        if (cleaned !== fontSizeField.text) {
                            var nextCursor = Math.min(cleaned.length, fontSizeField.cursorPosition);
                            fontSizeField.text = cleaned;
                            fontSizeField.cursorPosition = nextCursor;
                        }
                    }
                    onActiveFocusChanged: {
                        if (!fontSizeField.activeFocus)
                            root._commitFontSizeText(fontSizeField.text);
                    }
                    Keys.onReturnPressed: {
                        root._commitFontSizeText(fontSizeField.text);
                        fontSizeField.selectAll();
                    }
                    Keys.onEnterPressed: {
                        root._commitFontSizeText(fontSizeField.text);
                        fontSizeField.selectAll();
                    }
                    Keys.onEscapePressed: {
                        fontSizeField.text = String(root.actionPopoverFontSizeValue);
                        fontSizeField.focus = false;
                    }
                }

                Slider {
                    id: fontSizeSlider
                    objectName: "graphNodeFloatingToolbarFontSizeSlider"
                    width: Math.round(240 * root._sizeScale)
                    height: root._popoverControlHeight
                    from: root.actionPopoverFontSizeMin
                    to: root.actionPopoverFontSizeMax
                    value: root.actionPopoverFontSizeValue
                    stepSize: 1
                    snapMode: Slider.SnapAlways
                    live: true
                    onMoved: root._previewFontSizeValue(Math.round(fontSizeSlider.value))
                    onPressedChanged: {
                        if (!fontSizeSlider.pressed && root.actionPopoverFontSizeDirty)
                            root._commitFontSizeValue(Math.round(fontSizeSlider.value));
                    }
                    background: Rectangle {
                        x: fontSizeSlider.leftPadding
                        y: fontSizeSlider.topPadding + fontSizeSlider.availableHeight / 2 - height / 2
                        width: fontSizeSlider.availableWidth
                        height: Math.max(3, root._floatingToolbarVerticalPadding(root.floatingToolbarNestedPopoverLevel))
                        radius: height / 2
                        color: Qt.alpha(root._chromeForeground, 0.30)

                        Rectangle {
                            width: fontSizeSlider.visualPosition * parent.width
                            height: parent.height
                            radius: parent.radius
                            color: Qt.alpha(root.accentColor, 0.92)
                        }
                    }
                    handle: Rectangle {
                        x: fontSizeSlider.leftPadding
                            + fontSizeSlider.visualPosition * (fontSizeSlider.availableWidth - width)
                        y: fontSizeSlider.topPadding
                            + fontSizeSlider.availableHeight / 2 - height / 2
                        width: root._popoverIconSize
                        height: width
                        radius: width / 2
                        antialiasing: true
                        color: root.accentColor
                        border.width: Math.max(1, Math.round(1 * root._sizeScale))
                        border.color: root._chromeForeground
                    }
                }

                Rectangle {
                    id: fontSizeStepper
                    objectName: "graphNodeFloatingToolbarFontSizeStepper"
                    radius: root._popoverRadius
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.alpha(root._chromeForeground, 0.14)
                    implicitWidth: fontSizeStepperRow.implicitWidth + root._popoverVerticalPadding
                    implicitHeight: Math.max(root._popoverControlHeight, fontSizeStepperRow.implicitHeight)

                    Row {
                        id: fontSizeStepperRow
                        anchors.centerIn: parent
                        spacing: 0

                        Repeater {
                            model: root.actionPopoverLayout === "font_size" ? root.actionPopoverActions : []

                            GraphSurfaceControls.GraphSurfaceButton {
                                id: fontSizeStepButton
                                objectName: "graphNodeFloatingToolbarPopoverAction_" + String(modelData.id || "")
                                host: root.host
                                text: root._actionToolbarText(modelData)
                                iconName: root._actionToolbarIcon(modelData)
                                iconOnly: false
                                iconSize: root._popoverIconSize
                                controlHeight: root._popoverControlHeight
                                iconSourceResolver: function(name, size, color) {
                                    return root._iconSource(name, size, color);
                                }
                                accentColor: root.accentColor
                                foregroundColor: root._chromeForeground
                                enabled: modelData.enabled !== false
                                chromeRadius: root._popoverRadius
                                contentHorizontalPadding: root._popoverHorizontalPadding
                                contentVerticalPadding: root._popoverVerticalPadding
                                font.pixelSize: root._popoverTextPixelSize
                                tooltipText: root._actionTooltipText(modelData)
                                tooltipCategory: "general"
                                tooltipScreenStablePositioning: true
                                tooltipAnchorScale: root._effectiveZoom
                                tooltipScreenGap: 8
                                tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                                baseFillColor: "transparent"
                                baseBorderColor: "transparent"
                                hoverFillColor: root._buttonHoverFillColor
                                hoverBorderColor: root._buttonHoverFillColor
                                hoverBorderWidth: 1
                                focusPolicy: Qt.TabFocus
                                onControlStarted: {
                                    if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                                        root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                                }
                                onClicked: root._dispatchPopoverAction(modelData)
                                Keys.onReturnPressed: fontSizeStepButton.clicked()
                                Keys.onEnterPressed: fontSizeStepButton.clicked()
                            }
                        }
                    }
                }
            }

            Row {
                id: pdfPagePopoverPanel
                objectName: "graphNodeFloatingToolbarPdfPagePanel"
                visible: root.actionPopoverLayout === "pdf_page"
                anchors.centerIn: parent
                spacing: Math.round(8 * root._sizeScale)

                readonly property var previousAction: root._popoverActionById("pdf_page_previous") || ({})
                readonly property var nextAction: root._popoverActionById("pdf_page_next") || ({})

                GraphSurfaceControls.GraphSurfaceButton {
                    id: pdfPreviousButton
                    objectName: "graphNodeFloatingToolbarPopoverAction_pdf_page_previous"
                    host: root.host
                    text: ""
                    iconName: root._actionToolbarIcon(pdfPagePopoverPanel.previousAction)
                    iconOnly: true
                    iconSize: root._popoverIconSize
                        controlHeight: root._popoverControlHeight
                        chromeRadius: root._popoverRadius
                        contentVerticalPadding: root._popoverVerticalPadding
                    iconSourceResolver: function(name, size, color) {
                        return root._iconSource(name, size, color);
                    }
                    accentColor: root.accentColor
                    foregroundColor: root._chromeForeground
                    enabled: root.actionPopoverPageValue > root.actionPopoverPageMin
                    contentHorizontalPadding: root._popoverIconOnlyHorizontalPadding
                    tooltipText: String(pdfPagePopoverPanel.previousAction.label || TooltipCopy.text(tooltipCopyBridge, "fullscreen.pdf.previous_page_short"))
                    tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "fullscreen.pdf.previous_page_short")
                    tooltipScreenStablePositioning: true
                    tooltipAnchorScale: root._effectiveZoom
                    tooltipScreenGap: 8
                    tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                    baseFillColor: "transparent"
                    baseBorderColor: "transparent"
                    hoverFillColor: root._buttonHoverFillColor
                    hoverBorderColor: root._buttonHoverFillColor
                    hoverBorderWidth: 1
                    focusPolicy: Qt.TabFocus
                    onControlStarted: {
                        if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                            root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                    }
                    onClicked: root._commitPageNumberValue(root.actionPopoverPageValue - 1)
                    Keys.onReturnPressed: pdfPreviousButton.clicked()
                    Keys.onEnterPressed: pdfPreviousButton.clicked()
                }

                TextField {
                    id: pdfPageField
                    objectName: "graphNodeFloatingToolbarPdfPageField"
                    width: Math.round(58 * root._sizeScale)
                    height: root._popoverControlHeight
                    text: String(root.actionPopoverPageValue)
                    color: root._chromeForeground
                    selectedTextColor: root._chromeForeground
                    selectionColor: Qt.alpha(root.accentColor, 0.45)
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Math.max(root._popoverTextPixelSize, root._popoverIconSize)
                    font.weight: Font.DemiBold
                    selectByMouse: true
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator {
                        bottom: root.actionPopoverPageMin
                        top: root.actionPopoverPageMax
                    }
                    background: Rectangle {
                        radius: root._popoverRadius
                        color: Qt.alpha(root._chromeForeground, 0.10)
                        border.width: pdfPageField.activeFocus ? 1 : 0
                        border.color: Qt.alpha(root.accentColor, 0.72)
                    }
                    onTextEdited: {
                        var cleaned = root._sanitizeIntegerText(pdfPageField.text);
                        if (cleaned !== pdfPageField.text) {
                            var nextCursor = Math.min(cleaned.length, pdfPageField.cursorPosition);
                            pdfPageField.text = cleaned;
                            pdfPageField.cursorPosition = nextCursor;
                        }
                    }
                    onActiveFocusChanged: {
                        if (!pdfPageField.activeFocus)
                            root._commitPageNumberText(pdfPageField.text);
                    }
                    Keys.onReturnPressed: {
                        root._commitPageNumberText(pdfPageField.text);
                        pdfPageField.selectAll();
                    }
                    Keys.onEnterPressed: {
                        root._commitPageNumberText(pdfPageField.text);
                        pdfPageField.selectAll();
                    }
                    Keys.onEscapePressed: {
                        root._syncPageNumberEditor(true);
                        pdfPageField.focus = false;
                    }
                }

                Text {
                    objectName: "graphNodeFloatingToolbarPdfPageTotalLabel"
                    height: root._popoverControlHeight
                    text: "/ " + String(root.actionPopoverPageMax)
                    color: Qt.alpha(root._chromeForeground, 0.72)
                    font.pixelSize: root._popoverTextPixelSize
                    verticalAlignment: Text.AlignVCenter
                }

                GraphSurfaceControls.GraphSurfaceButton {
                    id: pdfNextButton
                    objectName: "graphNodeFloatingToolbarPopoverAction_pdf_page_next"
                    host: root.host
                    text: ""
                    iconName: root._actionToolbarIcon(pdfPagePopoverPanel.nextAction)
                    iconOnly: true
                    iconSize: root._popoverIconSize
                        controlHeight: root._popoverControlHeight
                        chromeRadius: root._popoverRadius
                        contentVerticalPadding: root._popoverVerticalPadding
                    iconSourceResolver: function(name, size, color) {
                        return root._iconSource(name, size, color);
                    }
                    accentColor: root.accentColor
                    foregroundColor: root._chromeForeground
                    enabled: root.actionPopoverPageValue < root.actionPopoverPageMax
                    contentHorizontalPadding: root._popoverIconOnlyHorizontalPadding
                    tooltipText: String(pdfPagePopoverPanel.nextAction.label || TooltipCopy.text(tooltipCopyBridge, "fullscreen.pdf.next_page_short"))
                    tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "fullscreen.pdf.next_page_short")
                    tooltipScreenStablePositioning: true
                    tooltipAnchorScale: root._effectiveZoom
                    tooltipScreenGap: 8
                    tooltipScreenStablePlacement: root.flipped ? "below" : "above"
                    baseFillColor: "transparent"
                    baseBorderColor: "transparent"
                    hoverFillColor: root._buttonHoverFillColor
                    hoverBorderColor: root._buttonHoverFillColor
                    hoverBorderWidth: 1
                    focusPolicy: Qt.TabFocus
                    onControlStarted: {
                        if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                            root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                    }
                    onClicked: root._commitPageNumberValue(root.actionPopoverPageValue + 1)
                    Keys.onReturnPressed: pdfNextButton.clicked()
                    Keys.onEnterPressed: pdfNextButton.clicked()
                }
            }

            Column {
                id: fontFamilyPopoverPanel
                objectName: "graphNodeFloatingToolbarFontFamilyPanel"
                visible: root.actionPopoverLayout === "font_family"
                anchors.centerIn: parent
                spacing: root._popoverVerticalPadding
                width: preferredWidth
                height: preferredHeight
                readonly property real preferredWidth: Math.round(220 * root._sizeScale)
                readonly property real preferredHeight: fontFamilySearchField.height
                    + spacing
                    + fontFamilyListFrame.height
                readonly property var filteredActions: root._filteredPopoverActions()

                TextField {
                    id: fontFamilySearchField
                    objectName: "graphNodeFloatingToolbarFontFamilyField"
                    width: parent.width
                    height: root._popoverControlHeight
                    text: root.actionPopoverFilterText
                    placeholderText: "Search fonts"
                    color: root._chromeForeground
                    placeholderTextColor: Qt.alpha(root._chromeForeground, 0.58)
                    selectedTextColor: root._chromeForeground
                    selectionColor: Qt.alpha(root.accentColor, 0.45)
                    font.pixelSize: root._popoverTextPixelSize
                    selectByMouse: true
                    background: Rectangle {
                        radius: root._popoverRadius
                        color: Qt.alpha(root._chromeForeground, 0.10)
                        border.width: fontFamilySearchField.activeFocus ? 1 : 0
                        border.color: Qt.alpha(root.accentColor, 0.72)
                    }
                    onTextEdited: root.actionPopoverFilterText = fontFamilySearchField.text
                    onActiveFocusChanged: {
                        if (fontFamilySearchField.activeFocus
                                && fontFamilySearchField.text !== root.actionPopoverFilterText)
                            fontFamilySearchField.text = root.actionPopoverFilterText;
                    }
                    Keys.onDownPressed: {
                        fontFamilyList.forceActiveFocus();
                        if (fontFamilyList.currentIndex < 0 && fontFamilyPopoverPanel.filteredActions.length > 0)
                            fontFamilyList.currentIndex = 0;
                    }
                    Keys.onEscapePressed: root._closeActionPopover(true)
                    Keys.onReturnPressed: {
                        if (fontFamilyPopoverPanel.filteredActions.length > 0)
                            root._dispatchPopoverAction(fontFamilyPopoverPanel.filteredActions[0]);
                    }
                    Keys.onEnterPressed: {
                        if (fontFamilyPopoverPanel.filteredActions.length > 0)
                            root._dispatchPopoverAction(fontFamilyPopoverPanel.filteredActions[0]);
                    }
                }

                Rectangle {
                    id: fontFamilyListFrame
                    width: parent.width
                    height: preferredHeight
                    radius: root._popoverRadius
                    color: Qt.alpha(root._chromeForeground, 0.06)
                    border.width: 1
                    border.color: Qt.alpha(root._chromeForeground, 0.12)
                    readonly property real preferredHeight: Math.min(
                        fontFamilyList.contentHeight,
                        Math.round(220 * root._sizeScale)
                    )

                    ListView {
                        id: fontFamilyList
                        objectName: "graphNodeFloatingToolbarFontFamilyList"
                        anchors.fill: parent
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: fontFamilyPopoverPanel.visible ? fontFamilyPopoverPanel.filteredActions : []
                        currentIndex: root._checkedPopoverActionIndex(fontFamilyPopoverPanel.filteredActions)
                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                            interactive: true
                        }

                        delegate: ItemDelegate {
                            id: fontFamilyActionButton
                            objectName: "graphNodeFloatingToolbarPopoverAction_" + String(modelData.id || "")
                            width: ListView.view ? ListView.view.width : fontFamilyPopoverPanel.width
                            height: root._floatingToolbarControlHeight(root.floatingToolbarNestedPopoverLevel)
                            highlighted: ListView.isCurrentItem || root._actionChecked(modelData)

                            contentItem: Text {
                                text: String(modelData.label || "")
                                color: fontFamilyActionButton.highlighted
                                    ? root.accentColor
                                    : root._chromeForeground
                                font.pixelSize: root._floatingToolbarTextPixelSize(root.floatingToolbarNestedPopoverLevel)
                                font.family: String(modelData.font_family || "").length > 0
                                    ? String(modelData.font_family || "")
                                    : Qt.application.font.family
                                font.weight: root._actionChecked(modelData) ? Font.DemiBold : Font.Normal
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }

                            background: Rectangle {
                                radius: root._floatingToolbarRadius(root.floatingToolbarNestedPopoverLevel)
                                color: fontFamilyActionButton.down
                                    ? Qt.alpha(root.accentColor, 0.26)
                                    : (fontFamilyActionButton.highlighted
                                        ? Qt.alpha(root.accentColor, 0.16)
                                        : "transparent")
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root._dispatchPopoverAction(modelData)
                            }

                            onClicked: root._dispatchPopoverAction(modelData)
                            Keys.onReturnPressed: fontFamilyActionButton.clicked()
                            Keys.onEnterPressed: fontFamilyActionButton.clicked()
                        }

                        Keys.onEscapePressed: {
                            fontFamilySearchField.forceActiveFocus();
                            root._closeActionPopover(true);
                        }
                    }
                }
            }
        }
    }

    // Bridges the gap between the toolbar chrome and the run menu so the cursor
    // never falls through to a node beneath the overlay (e.g. a group backdrop)
    // while reaching for a menu item. Without it the backdrop claims the active
    // toolbar host mid-gap, switching the toolbar's host and closing the menu.
    Item {
        id: runMenuBridge
        objectName: "graphNodeFloatingToolbarRunMenuBridge"
        visible: actionDropdown.visible
        x: Math.min(0, actionDropdown.x)
        width: Math.max(chromeContainer.width, actionDropdown.x + actionDropdown.width) - x
        y: root.flipped
            ? chromeContainer.height
            : (actionDropdown.y + actionDropdown.panelHeight)
        height: root.flipped
            ? Math.max(0, actionDropdown.y - chromeContainer.height)
            : Math.max(0, -(actionDropdown.y + actionDropdown.panelHeight))
        z: 79

        HoverHandler {
            id: runMenuBridgeHoverHandler
        }
    }

    ShellComponents.ShellContextMenu {
        id: actionDropdown
        objectName: "graphNodeFloatingToolbarRunMenu"
        visible: root.visible && root.runMenuVisible && root.runMenuActions.length > 0
        x: root.runMenuX
        y: root.runMenuY
        z: 80
        minimumWidth: 196

        HoverHandler {
            id: runMenuHoverHandler
        }
        actions: {
            var resolved = [];
            var source = root.runMenuActions || [];
            for (var i = 0; i < source.length; i++) {
                var action = source[i] || {};
                resolved.push({
                    actionId: String(action.actionId || action.id || ""),
                    text: String(action.text || action.label || ""),
                    enabled: action.enabled !== false,
                    visible: action.visible !== false,
                    destructive: Boolean(action.destructive)
                });
            }
            return resolved;
        }
        onActionTriggered: function(actionId) {
            root.runMenuVisible = false;
            if (root.host)
                root.host.dispatchNodeAction(String(actionId || ""), null);
        }
    }
}
