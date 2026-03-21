import QtQuick 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

Item {
    id: root
    property var viewBridge: null
    property bool showGrid: true
    property bool degradedWindowActive: false
    property int _redrawRequestCount: 0
    property bool _viewStateRedrawDirty: false
    property int _gridCacheBuildCount: 0
    property real _zoomBucketScaleLimit: 1.15
    property real _committedZoom: 1.0
    property real _committedCenterX: 0.0
    property real _committedCenterY: 0.0
    property real _cachedGridStep: 0.0
    property real _cachedGridPeriod: 0.0
    property real _gridScale: 1.0
    property real _gridContentWidth: 0.0
    property real _gridContentHeight: 0.0
    property int _minorVerticalLineCount: 0
    property int _minorHorizontalLineCount: 0
    property int _majorVerticalLineCount: 0
    property int _majorHorizontalLineCount: 0
    readonly property var themePalette: themeBridge.palette
    readonly property color backgroundTopColor: themePalette.canvas_bg
    readonly property color backgroundBottomColor: themePalette.panel_bg
    readonly property color backgroundFillColor: themePalette.canvas_bg
    readonly property color minorGridColor: themePalette.canvas_minor_grid
    readonly property color majorGridColor: themePalette.canvas_major_grid
    readonly property bool effectiveShowGrid: root.showGrid && !root.degradedWindowActive

    function _normalizedZoom(value) {
        var zoom = Number(value);
        if (!isFinite(zoom) || zoom <= 0.0001)
            return 1.0;
        return zoom;
    }

    function _gridStepForZoom(zoomValue) {
        var step = 20.0 * _normalizedZoom(zoomValue);
        if (step < 10.0)
            step = 10.0;
        return step;
    }

    function _syncCommittedViewState() {
        root._committedZoom = _normalizedZoom(root.viewBridge ? root.viewBridge.zoom_value : 1.0);

        var centerX = Number(root.viewBridge ? root.viewBridge.center_x : 0.0);
        if (!isFinite(centerX))
            centerX = 0.0;
        root._committedCenterX = centerX;

        var centerY = Number(root.viewBridge ? root.viewBridge.center_y : 0.0);
        if (!isFinite(centerY))
            centerY = 0.0;
        root._committedCenterY = centerY;
    }

    function _resetGridCache() {
        root._cachedGridStep = 0.0;
        root._cachedGridPeriod = 0.0;
        root._gridScale = 1.0;
        root._gridContentWidth = 0.0;
        root._gridContentHeight = 0.0;
        root._minorVerticalLineCount = 0;
        root._minorHorizontalLineCount = 0;
        root._majorVerticalLineCount = 0;
        root._majorHorizontalLineCount = 0;
    }

    function _ensureGridCache(forceRebuild) {
        if (!root.effectiveShowGrid) {
            _resetGridCache();
            return;
        }

        var currentStep = _gridStepForZoom(root._committedZoom);
        var rebuild = Boolean(forceRebuild) || !(root._cachedGridStep > 0.0);
        if (!rebuild) {
            rebuild = currentStep > root._cachedGridStep * root._zoomBucketScaleLimit
                || currentStep < root._cachedGridStep / root._zoomBucketScaleLimit;
        }

        if (rebuild) {
            var minScale = 1.0 / root._zoomBucketScaleLimit;
            var cachedPeriod = currentStep * 5.0;
            root._cachedGridStep = currentStep;
            root._cachedGridPeriod = cachedPeriod;
            root._gridContentWidth = Math.max(
                cachedPeriod * 2.0,
                root.width / minScale + cachedPeriod * 2.0
            );
            root._gridContentHeight = Math.max(
                cachedPeriod * 2.0,
                root.height / minScale + cachedPeriod * 2.0
            );
            root._minorVerticalLineCount = Math.max(0, Math.ceil(root._gridContentWidth / currentStep) + 1);
            root._minorHorizontalLineCount = Math.max(0, Math.ceil(root._gridContentHeight / currentStep) + 1);
            root._majorVerticalLineCount = Math.max(0, Math.ceil(root._gridContentWidth / cachedPeriod) + 1);
            root._majorHorizontalLineCount = Math.max(0, Math.ceil(root._gridContentHeight / cachedPeriod) + 1);
            root._gridCacheBuildCount += 1;
        }

        root._gridScale = currentStep / Math.max(0.0001, root._cachedGridStep);
    }

    function requestGridRedraw(forceRebuild) {
        root._viewStateRedrawDirty = false;
        root._syncCommittedViewState();
        root._ensureGridCache(Boolean(forceRebuild));
        root._redrawRequestCount += 1;
    }

    function markViewStateRedrawDirty() {
        root._viewStateRedrawDirty = true;
    }

    function flushViewStateRedraw() {
        if (!root._viewStateRedrawDirty)
            return false;
        requestGridRedraw(false);
        return true;
    }

    function _currentGridStep() {
        if (!(root._cachedGridStep > 0.0))
            return 0.0;
        return root._cachedGridStep * root._gridScale;
    }

    function _currentGridPeriod() {
        if (!(root._cachedGridPeriod > 0.0))
            return 0.0;
        return root._cachedGridPeriod * root._gridScale;
    }

    function _gridOffsetX() {
        var currentStep = _currentGridStep();
        var currentPeriod = _currentGridPeriod();
        if (!(currentStep > 0.0) || !(currentPeriod > 0.0))
            return 0.0;
        var anchor = root.width * 0.5 - root._committedCenterX * root._committedZoom;
        var offset = GraphCanvasLogic.normalizedOffset(currentStep, anchor);
        return offset - currentPeriod;
    }

    function _gridOffsetY() {
        var currentStep = _currentGridStep();
        var currentPeriod = _currentGridPeriod();
        if (!(currentStep > 0.0) || !(currentPeriod > 0.0))
            return 0.0;
        var anchor = root.height * 0.5 - root._committedCenterY * root._committedZoom;
        var offset = GraphCanvasLogic.normalizedOffset(currentStep, anchor);
        return offset - currentPeriod;
    }

    function _majorLocalOriginX() {
        var currentStep = _currentGridStep();
        var currentPeriod = _currentGridPeriod();
        if (!(currentStep > 0.0) || !(currentPeriod > 0.0))
            return 0.0;
        var anchor = root.width * 0.5 - root._committedCenterX * root._committedZoom;
        var minorOffset = GraphCanvasLogic.normalizedOffset(currentStep, anchor);
        var majorOffset = GraphCanvasLogic.normalizedOffset(currentPeriod, anchor);
        return (majorOffset - minorOffset + currentPeriod) / Math.max(0.0001, root._gridScale);
    }

    function _majorLocalOriginY() {
        var currentStep = _currentGridStep();
        var currentPeriod = _currentGridPeriod();
        if (!(currentStep > 0.0) || !(currentPeriod > 0.0))
            return 0.0;
        var anchor = root.height * 0.5 - root._committedCenterY * root._committedZoom;
        var minorOffset = GraphCanvasLogic.normalizedOffset(currentStep, anchor);
        var majorOffset = GraphCanvasLogic.normalizedOffset(currentPeriod, anchor);
        return (majorOffset - minorOffset + currentPeriod) / Math.max(0.0001, root._gridScale);
    }

    onShowGridChanged: requestGridRedraw(true)
    onDegradedWindowActiveChanged: requestGridRedraw(true)
    onThemePaletteChanged: requestGridRedraw(true)
    onWidthChanged: requestGridRedraw(true)
    onHeightChanged: requestGridRedraw(true)

    Component.onCompleted: requestGridRedraw(true)

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.backgroundTopColor }
            GradientStop { position: 1.0; color: root.backgroundBottomColor }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.backgroundFillColor
    }

    Item {
        anchors.fill: parent
        clip: true
        visible: root.effectiveShowGrid

        Item {
            id: gridContent
            x: root._gridOffsetX()
            y: root._gridOffsetY()
            width: root._gridContentWidth
            height: root._gridContentHeight
            scale: root._gridScale
            transformOrigin: Item.TopLeft

            Repeater {
                model: root._minorVerticalLineCount
                delegate: Rectangle {
                    x: index * root._cachedGridStep
                    y: 0
                    width: 1.0 / Math.max(0.0001, root._gridScale)
                    height: gridContent.height
                    color: root.minorGridColor
                }
            }

            Repeater {
                model: root._minorHorizontalLineCount
                delegate: Rectangle {
                    x: 0
                    y: index * root._cachedGridStep
                    width: gridContent.width
                    height: 1.0 / Math.max(0.0001, root._gridScale)
                    color: root.minorGridColor
                }
            }

            Repeater {
                model: root._majorVerticalLineCount
                delegate: Rectangle {
                    x: root._majorLocalOriginX() + index * root._cachedGridPeriod
                    y: 0
                    width: 1.0 / Math.max(0.0001, root._gridScale)
                    height: gridContent.height
                    color: root.majorGridColor
                }
            }

            Repeater {
                model: root._majorHorizontalLineCount
                delegate: Rectangle {
                    x: 0
                    y: root._majorLocalOriginY() + index * root._cachedGridPeriod
                    width: gridContent.width
                    height: 1.0 / Math.max(0.0001, root._gridScale)
                    color: root.majorGridColor
                }
            }
        }
    }
}
