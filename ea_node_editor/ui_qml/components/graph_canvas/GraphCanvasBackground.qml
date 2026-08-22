import QtQuick 2.15
import QtQuick.Window 2.15
import QtQml 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic
import "CanvasBackgroundStyle.js" as CanvasBackgroundStyle

Item {
    id: root
    property var viewBridge: null
    property string canvasBackgroundVariant: "theme"
    property bool showGrid: true
    property string gridStyle: "lines"
    property string gridRendererPreference: "tiled"
    property int _redrawRequestCount: 0
    property bool _viewStateRedrawDirty: false
    property int _gridCacheBuildCount: 0
    property int profileGridUpdateCount: 0
    property real profileLastGridUpdateMs: 0.0
    property real profileLastGridPaintMs: 0.0
    property int profileGridItemCount: 0
    property int profileGridMinorItemCount: 0
    property int profileGridMajorItemCount: 0
    property int profileGridRowCount: 0
    property int profileGridColumnCount: 0
    property real _zoomBucketScaleLimit: 1.15
    property real _committedZoom: 1.0
    property real _committedCenterX: 0.0
    property real _committedCenterY: 0.0
    property real _cachedGridStep: 0.0
    property real _cachedGridPeriod: 0.0
    property real _gridScale: 1.0
    readonly property var themePalette: themeBridge.palette
    readonly property string effectiveBackgroundVariant: CanvasBackgroundStyle.effectiveVariant(root.canvasBackgroundVariant)
    readonly property color backgroundTopColor: root.backgroundFillColor
    readonly property color backgroundBottomColor: root.effectiveBackgroundVariant === "theme"
        ? themePalette.panel_bg
        : root.backgroundFillColor
    readonly property color backgroundFillColor: CanvasBackgroundStyle.fillColor(
        root.canvasBackgroundVariant,
        themePalette
    )
    readonly property color minorGridColor: {
        if (root.effectiveBackgroundVariant === "dark")
            return "#2b2f38";
        if (root.effectiveBackgroundVariant === "light" || root.effectiveBackgroundVariant === "white")
            return "#d9dfe8";
        return themePalette.canvas_minor_grid;
    }
    readonly property color majorGridColor: {
        if (root.effectiveBackgroundVariant === "dark")
            return "#323746";
        if (root.effectiveBackgroundVariant === "light" || root.effectiveBackgroundVariant === "white")
            return "#c0c9d6";
        return themePalette.canvas_major_grid;
    }
    readonly property bool effectiveShowGrid: root.showGrid
    readonly property string effectiveGridStyle: root.gridStyle === "points" ? "points" : "lines"
    readonly property real minorGridPointSize: 1.75
    readonly property real majorGridPointSize: 2.75
    readonly property string activeGridRendererKind: root._normalizedGridRendererPreference(root.gridRendererPreference)
    readonly property string profileGridRendererKind: root.effectiveShowGrid ? root.activeGridRendererKind : "none"
    readonly property bool _useCanvasGridRenderer: root.activeGridRendererKind === "canvas"
    readonly property bool _useTiledGridRenderer: root.activeGridRendererKind === "tiled"
    readonly property real _devicePixelRatio: Math.max(1.0, Number(Screen.devicePixelRatio || 1.0))

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

    function _normalizedGridRendererPreference(value) {
        var renderer = String(value || "").toLowerCase().trim();
        if (renderer === "canvas")
            return "canvas";
        return "tiled";
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
            var cachedPeriod = currentStep * 5.0;
            root._cachedGridStep = currentStep;
            root._cachedGridPeriod = cachedPeriod;
            root._gridCacheBuildCount += 1;
        }

        root._gridScale = currentStep / Math.max(0.0001, root._cachedGridStep);
    }

    function requestGridRedraw(forceRebuild) {
        var startedMs = Date.now();
        root._viewStateRedrawDirty = false;
        root._syncCommittedViewState();
        root._ensureGridCache(Boolean(forceRebuild));
        root._redrawRequestCount += 1;
        root.profileLastGridUpdateMs = 0.0;
        root.profileLastGridPaintMs = 0.0;
        root._syncGridItemMetrics();
        if (!root.effectiveShowGrid)
            return;
        if (root._useCanvasGridRenderer && gridCanvas) {
            gridCanvas.requestPaint();
            return;
        }
        _recordGridUpdate(startedMs);
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

    function _gridAnchorX() {
        return root.width * 0.5 - root._committedCenterX * root._committedZoom;
    }

    function _gridAnchorY() {
        return root.height * 0.5 - root._committedCenterY * root._committedZoom;
    }

    function _gridOffsetX(step) {
        var currentStep = _currentGridStep();
        if (step !== undefined)
            currentStep = Number(step);
        if (!(currentStep > 0.0))
            return 0.0;
        return GraphCanvasLogic.normalizedOffset(currentStep, root._gridAnchorX());
    }

    function _gridOffsetY(step) {
        var currentStep = _currentGridStep();
        if (step !== undefined)
            currentStep = Number(step);
        if (!(currentStep > 0.0))
            return 0.0;
        return GraphCanvasLogic.normalizedOffset(currentStep, root._gridAnchorY());
    }

    function _recordGridUpdate(startedMs) {
        root.profileGridUpdateCount += 1;
        root.profileLastGridUpdateMs = Math.max(0.0, Date.now() - Number(startedMs || Date.now()));
    }

    function _estimatedCanvasGridItemCount() {
        if (!root.effectiveShowGrid)
            return 0;

        var minorStep = root._currentGridStep();
        var majorStep = root._currentGridPeriod();
        if (!(minorStep > 0.0) || !(majorStep > 0.0))
            return 0;

        var minorColumns = Math.max(0, Math.ceil((root.width - root._gridOffsetX(minorStep)) / minorStep) + 1);
        var minorRows = Math.max(0, Math.ceil((root.height - root._gridOffsetY(minorStep)) / minorStep) + 1);
        var majorColumns = Math.max(0, Math.ceil((root.width - root._gridOffsetX(majorStep)) / majorStep) + 1);
        var majorRows = Math.max(0, Math.ceil((root.height - root._gridOffsetY(majorStep)) / majorStep) + 1);
        if (root.effectiveGridStyle === "points")
            return minorColumns * minorRows + majorColumns * majorRows;
        return minorColumns + minorRows + majorColumns + majorRows;
    }

    function _syncGridItemMetrics() {
        if (!root.effectiveShowGrid) {
            root.profileGridItemCount = 0;
            root.profileGridMinorItemCount = 0;
            root.profileGridMajorItemCount = 0;
            root.profileGridRowCount = 0;
            root.profileGridColumnCount = 0;
            return;
        }

        if (root._useTiledGridRenderer) {
            root.profileGridItemCount = Number(tiledGridRenderer.profileGridItemCount || 0);
            root.profileGridMinorItemCount = Number(tiledGridRenderer.profileGridMinorItemCount || 0);
            root.profileGridMajorItemCount = Number(tiledGridRenderer.profileGridMajorItemCount || 0);
            root.profileGridRowCount = Number(tiledGridRenderer.profileGridRowCount || 0);
            root.profileGridColumnCount = Number(tiledGridRenderer.profileGridColumnCount || 0);
            return;
        }

        root.profileGridItemCount = _estimatedCanvasGridItemCount();
        root.profileGridMinorItemCount = 0;
        root.profileGridMajorItemCount = 0;
        root.profileGridRowCount = 0;
        root.profileGridColumnCount = 0;
    }

    onShowGridChanged: requestGridRedraw(true)
    onGridStyleChanged: requestGridRedraw(false)
    onCanvasBackgroundVariantChanged: requestGridRedraw(true)
    onGridRendererPreferenceChanged: requestGridRedraw(true)
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

    GraphCanvasGridTiled {
        id: tiledGridRenderer
        anchors.fill: parent
        visible: root.effectiveShowGrid && root._useTiledGridRenderer
        gridVisible: root.effectiveShowGrid && root._useTiledGridRenderer
        gridStyle: root.effectiveGridStyle
        minorGridColor: root.minorGridColor
        majorGridColor: root.majorGridColor
        minorStep: root._currentGridStep()
        majorStep: root._currentGridPeriod()
        minorOffsetX: root._gridOffsetX(root._currentGridStep())
        minorOffsetY: root._gridOffsetY(root._currentGridStep())
        majorOffsetX: root._gridOffsetX(root._currentGridPeriod())
        majorOffsetY: root._gridOffsetY(root._currentGridPeriod())
        minorPointSize: root.minorGridPointSize
        majorPointSize: root.majorGridPointSize
        devicePixelRatio: root._devicePixelRatio
        updateRevision: root._redrawRequestCount
    }

    Canvas {
        id: gridCanvas
        objectName: "graphCanvasGridCanvasFallback"
        anchors.fill: parent
        visible: root.effectiveShowGrid && root._useCanvasGridRenderer
        antialiasing: false

        function drawLineGrid(ctx, minorStep, majorStep) {
            var minorX = root._gridOffsetX(minorStep);
            var minorY = root._gridOffsetY(minorStep);
            var majorX = root._gridOffsetX(majorStep);
            var majorY = root._gridOffsetY(majorStep);

            ctx.fillStyle = root.minorGridColor;
            for (var x = minorX; x <= width; x += minorStep)
                ctx.fillRect(Math.round(x), 0, 1, height);
            for (var y = minorY; y <= height; y += minorStep)
                ctx.fillRect(0, Math.round(y), width, 1);

            ctx.fillStyle = root.majorGridColor;
            for (var majorVertical = majorX; majorVertical <= width; majorVertical += majorStep)
                ctx.fillRect(Math.round(majorVertical), 0, 1, height);
            for (var majorHorizontal = majorY; majorHorizontal <= height; majorHorizontal += majorStep)
                ctx.fillRect(0, Math.round(majorHorizontal), width, 1);
        }

        function drawPointGrid(ctx, minorStep, majorStep) {
            var minorX = root._gridOffsetX(minorStep);
            var minorY = root._gridOffsetY(minorStep);
            var majorX = root._gridOffsetX(majorStep);
            var majorY = root._gridOffsetY(majorStep);
            var minorHalf = root.minorGridPointSize * 0.5;
            var majorHalf = root.majorGridPointSize * 0.5;

            ctx.fillStyle = root.minorGridColor;
            for (var y = minorY; y <= height; y += minorStep) {
                for (var x = minorX; x <= width; x += minorStep)
                    ctx.fillRect(x - minorHalf, y - minorHalf, root.minorGridPointSize, root.minorGridPointSize);
            }

            ctx.fillStyle = root.majorGridColor;
            for (var majorRow = majorY; majorRow <= height; majorRow += majorStep) {
                for (var majorColumn = majorX; majorColumn <= width; majorColumn += majorStep) {
                    ctx.fillRect(
                        majorColumn - majorHalf,
                        majorRow - majorHalf,
                        root.majorGridPointSize,
                        root.majorGridPointSize
                    );
                }
            }
        }

        onPaint: {
            var startedMs = Date.now();
            var ctx = getContext("2d");
            ctx.reset();
            root.profileLastGridUpdateMs = 0.0;
            root.profileLastGridPaintMs = 0.0;

            if (!root.effectiveShowGrid)
                return;

            var minorStep = root._currentGridStep();
            var majorStep = root._currentGridPeriod();
            if (!(minorStep > 0.0) || !(majorStep > 0.0))
                return;

            if (root.effectiveGridStyle === "points")
                drawPointGrid(ctx, minorStep, majorStep);
            else
                drawLineGrid(ctx, minorStep, majorStep);

            root._recordGridUpdate(startedMs);
            root.profileLastGridPaintMs = root.profileLastGridUpdateMs;
            root._syncGridItemMetrics();
        }

    }
}
