import QtQuick 2.15
import ".." as GraphShared
import QtQuick.Effects
import ".." as GraphComponents
import "../surface_controls" as SurfaceControls
import "../GraphNodeHostHitTesting.js" as GraphNodeHostHitTesting
import "../GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics
import "FlowchartShapeGeometry.js" as FlowchartShapeGeometry

GraphShared.GraphSurfaceBase {
    id: surface
    property bool editingTitle: false
    objectName: "graphNodeFlowchartSurface"
    property bool editingBody: false
    property bool editingBodyTop: false
    property bool editingBodyRight: false
    readonly property bool isCubeSurface: _variantKey() === "isometric_cube"
    readonly property var embeddedInteractiveRects: _activeInlineEditor() !== null
        ? _activeInlineEditor().embeddedInteractiveRects
        : inlinePropertiesLayer.embeddedInteractiveRects
    readonly property bool shapeShadowVisible: host ? Boolean(host._surfaceShadowVisible) : false
    readonly property bool shapeShadowCacheActive: host ? Boolean(host.surfaceShadowCacheActive) : false
    readonly property string shapeShadowCacheKey: host ? String(host.surfaceShadowCacheKey || "") : ""
    readonly property string bodyValue: _resolvedBodyText()
    readonly property color bodyTextColor: host ? host.headerTextColor : "#173247"
    readonly property real bodyFontSize: host ? Number(host.passiveFontPixelSize || 12) : 12
    readonly property bool bodyFontBold: host ? Boolean(host.passiveFontBold) : false
    readonly property real bodyVerticalInset: host
        ? Math.max(12, Number(host.surfaceMetrics.body_bottom_margin || 16))
        : 16
    readonly property real bodyLeftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 18) : 18
    readonly property real bodyRightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 18) : 18
    readonly property string bodyTextPlacement: GraphNodeSurfaceMetrics.flowchartBodyTextPlacement(_variantKey())
    readonly property real shapeCanvasHeight: bodyTextPlacement === "below_shape"
        ? Math.max(0, surface.height * (1.0 - FlowchartShapeGeometry.BELOW_SHAPE_BAND_FRACTION))
        : surface.height
    readonly property real isometricCubeOffset: Math.min(surface.width * 0.24, surface.height * 0.5)
    readonly property real isometricFrontFaceCenterY: (surface.height + surface.isometricCubeOffset) * 0.5
    readonly property real bodyStrokeWidth: host ? Number(host.resolvedBorderWidth || 1) : 1
    readonly property var bodyTextMargins: ({
        "left": surface.bodyLeftMargin,
        "right": surface.bodyRightMargin,
        "vertical": surface.bodyVerticalInset
    })
    // The body text rectangle: the contract placement resolved against this silhouette.
    readonly property var bodyTextRegion: surface._bodyTextRegionFor(surface.width, surface.height)
    // Double-click still edits the body anywhere in the former margin box.
    readonly property var bodyEditHitRegion: surface._bodyEditHitRegion()
    readonly property var bodyFitModes: ["clip", "grow", "shrink"]
    readonly property string bodyFitMode: surface.isTimestampSurface
        ? "clip"
        : surface._normalizedBodyFitMode(surface.propString("body_fit", "clip"))
    readonly property bool bodyGrowToFit: surface.bodyFitMode === "grow"
    readonly property bool bodyShrinkToFit: surface.bodyFitMode === "shrink"
    // Square variants keep their aspect ratio when grow-to-fit enlarges them.
    readonly property bool bodyAspectLocked: GraphNodeSurfaceMetrics.flowchartVariantSquare(_variantKey())
    readonly property bool bodyTextOverflowing: !surface.isTimestampSurface && bodyRichText.contentOverflowing
    readonly property bool bodyStylePreviewActive: Object.keys(bodyRichText.draftStyle || ({})).length > 0
    property bool _growPending: false
    property bool _growPreviewActive: false
    property var _growPreviewBase: null
    readonly property string _growInputKey: surface.bodyGrowToFit
        ? [
            bodyRichText.measuredText,
            bodyRichText.measuredTextIsPlain,
            bodyRichText.resolvedFontFamily,
            bodyRichText.fontSizeValue,
            bodyRichText.resolvedFontWeight,
            bodyRichText.italicValue,
            bodyRichText.underlineValue,
            bodyRichText.strikeoutValue,
            bodyRichText.letterSpacingValue,
            bodyRichText.lineHeightValue,
            bodyRichText.resolvedTextWrapMode,
            bodyRichText.paddingValue,
            bodyRichText.editorVisible,
            bodyRichText.textCommitPending,
            surface.bodyStylePreviewActive
        ].join("\u001f")
        : ""
    readonly property bool bodyFallbackSuppressed: _bodyFallbackSuppressed()
    readonly property bool isTimestampSurface: _variantKey() === "timestamp"
    readonly property string timestampBodyPlaceholder: "%date{ddd mmm dd yyyy HH:MM:ss}%"
    readonly property bool timestampLive: surface.isTimestampSurface && surface._propertyBool("live", false)
    property bool timestampManualEditorOpen: false
    property string timestampSnapshotText: _timestampText()
    property string timestampNowText: _timestampText()
    readonly property string timestampManualEditorText: _timestampManualEditorText()
    readonly property var surfaceActions: surface.isTimestampSurface
        ? _surfaceActions()
        : surface._withTextFitAction(
            _activeRichTextBlock() !== null ? _activeRichTextBlock().surfaceActions : bodyRichText.surfaceActions
        )

    function _propertyText(key) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function _propertyBool(key, fallback) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return Boolean(fallback);
        if (typeof value === "boolean")
            return value;
        if (typeof value === "number")
            return value !== 0;
        var normalized = String(value || "").trim().toLowerCase();
        if (normalized === "true" || normalized === "1" || normalized === "yes" || normalized === "on")
            return true;
        if (normalized === "false" || normalized === "0" || normalized === "no" || normalized === "off")
            return false;
        return Boolean(fallback);
    }

    function _variantKey() {
        return host ? String(host.surfaceVariant || "").trim().toLowerCase() : "";
    }

    function _bodyTextRegionFor(width, height) {
        return FlowchartShapeGeometry.bodyTextRegion(
            surface._variantKey(),
            surface.bodyTextPlacement,
            width,
            height,
            surface.bodyStrokeWidth,
            surface.bodyTextMargins
        );
    }

    function _bodyEditHitRegion() {
        var region = surface.bodyTextRegion;
        var placement = surface.bodyTextPlacement;
        if (placement === "center" || placement === "below_shape" || placement === "front_face"
                || placement === "cube_front_face")
            return region;
        var box = FlowchartShapeGeometry.bodyTextRegion(
            surface._variantKey(),
            "center",
            surface.width,
            surface.height,
            surface.bodyStrokeWidth,
            surface.bodyTextMargins
        );
        var left = Math.min(region.x, box.x);
        var top = Math.min(region.y, box.y);
        return {
            "x": left,
            "y": top,
            "width": Math.max(region.x + region.width, box.x + box.width) - left,
            "height": Math.max(region.y + region.height, box.y + box.height) - top
        };
    }

    function _normalizedBodyFitMode(value) {
        var normalized = String(value || "").trim().toLowerCase();
        return surface.bodyFitModes.indexOf(normalized) >= 0 ? normalized : "clip";
    }

    function _textFitAction() {
        var mode = surface.bodyFitMode;
        var icons = {"clip": "crop", "grow": "fit-height", "shrink": "text-decrease"};
        var labels = {
            "clip": "Clip overflowing text",
            "grow": "Grow shape to fit text",
            "shrink": "Shrink text to fit"
        };
        var choices = [];
        for (var index = 0; index < surface.bodyFitModes.length; ++index) {
            var choice = surface.bodyFitModes[index];
            choices.push({
                "id": "text_fit_" + choice,
                "label": labels[choice],
                "icon": icons[choice],
                "kind": "surface",
                "checked": mode === choice,
                "close_popover": true
            });
        }
        return {
            "id": "text_fit_group",
            "label": "Text fit: " + labels[mode],
            "icon": icons[mode],
            "kind": "surface",
            "checked": mode !== "clip",
            "popover_layout": "row",
            "popoverActions": choices
        };
    }

    function _withTextFitAction(actions) {
        var source = actions || [];
        var result = [];
        var inserted = false;
        for (var index = 0; index < source.length; ++index) {
            result.push(source[index]);
            if (!inserted && source[index] && source[index].id === "text_wrap_group") {
                result.push(surface._textFitAction());
                inserted = true;
            }
        }
        if (!inserted)
            result.push(surface._textFitAction());
        return result;
    }

    function _setBodyFitMode(mode) {
        var normalized = String(mode || "").trim().toLowerCase();
        if (surface.isTimestampSurface || surface.bodyFitModes.indexOf(normalized) < 0)
            return false;
        if (normalized !== surface.bodyFitMode)
            surface._commitProperty("body_fit", normalized);
        return true;
    }

    // True when the body text, laid out at its current style, fits the region a
    // node of this size gives it (height only: growing never cures wide words).
    function _textFitsBody(width, height) {
        var region = surface._bodyTextRegionFor(width, height);
        var padding = Math.max(0.0, Number(bodyRichText.paddingValue) || 0.0);
        var innerWidth = region.width - 2.0 * padding;
        var innerHeight = region.height - 2.0 * padding;
        if (!(innerWidth >= 1.0) || !(innerHeight >= 1.0))
            return false;
        var measured = bodyRichText.measureContent(innerWidth, bodyRichText.fontSizeValue);
        return measured.height <= innerHeight + 0.5;
    }

    function _grownBodySize(width, height) {
        var fitsAt = function(candidateWidth, candidateHeight) {
            return surface._textFitsBody(candidateWidth, candidateHeight);
        };
        return surface.bodyAspectLocked
            ? FlowchartShapeGeometry.growScaleToFit(fitsAt, width, height)
            : FlowchartShapeGeometry.growHeightToFit(fitsAt, width, height);
    }

    // Resize handles ask this while dragging so grow-to-fit keeps the text inside.
    function minimumNodeHeightForWidth(width) {
        if (!surface.bodyGrowToFit || !host || bodyRichText.measuredText.length === 0)
            return 0.0;
        var minimum = Math.max(1.0, Number(host._minNodeHeight) || 1.0);
        var grown = FlowchartShapeGeometry.growHeightToFit(function(candidateWidth, candidateHeight) {
            return surface._textFitsBody(candidateWidth, candidateHeight);
        }, width, minimum);
        return grown ? grown.height : minimum;
    }

    function _committedGeometry() {
        if (!host || !host.nodeData || host._liveGeometryActive)
            return null;
        var geometry = {
            "x": Number(host.nodeData.x),
            "y": Number(host.nodeData.y),
            "width": Number(host.width),
            "height": Number(host.height)
        };
        if (!isFinite(geometry.x) || !isFinite(geometry.y)
                || !(geometry.width > 0.0) || !(geometry.height > 0.0))
            return null;
        return geometry;
    }

    function _scheduleGrowToFit() {
        if (!surface.bodyGrowToFit && !surface._growPreviewActive) {
            surface._growPending = false;
            return;
        }
        surface._growPending = surface.bodyGrowToFit;
        growToFitTimer.restart();
    }

    function _endGrowPreview() {
        if (!surface._growPreviewActive)
            return;
        var base = surface._growPreviewBase;
        surface._growPreviewActive = false;
        surface._growPreviewBase = null;
        if (host && host.nodeData && base) {
            host._liveWidth = base.width;
            host._liveHeight = base.height;
            host.resizePreviewChanged(String(host.nodeData.node_id || ""), base.x, base.y, base.width, base.height, false);
        }
        if (host)
            host._liveGeometryActive = false;
    }

    // Grow-to-fit: preview while the text or its style is being edited, then
    // persist through the normal resize commit so the size saves and undoes.
    function _applyGrowToFit() {
        surface._growPending = false;
        if (!host || !host.nodeData)
            return;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return;
        if (!surface.bodyGrowToFit || surface.isTimestampSurface
                || host.surfaceInteractionLocked || host.isCollapsed) {
            surface._endGrowPreview();
            return;
        }
        if (host._resizeInteractionActive || bodyRichText.textCommitPending)
            return;
        var base = surface._growPreviewActive ? surface._growPreviewBase : surface._committedGeometry();
        if (!base)
            return;
        var grown = surface._grownBodySize(base.width, base.height);
        var targetWidth = grown ? Math.max(base.width, grown.width) : base.width;
        var targetHeight = grown ? Math.max(base.height, grown.height) : base.height;
        var changed = Math.abs(targetWidth - base.width) >= 0.5 || Math.abs(targetHeight - base.height) >= 0.5;
        if (bodyRichText.editorVisible || surface.bodyStylePreviewActive) {
            if (!changed) {
                surface._endGrowPreview();
                return;
            }
            if (!surface._growPreviewActive) {
                surface._growPreviewBase = base;
                surface._growPreviewActive = true;
                host._liveGeometryActive = true;
                host._liveX = base.x;
                host._liveY = base.y;
            }
            host._liveWidth = targetWidth;
            host._liveHeight = targetHeight;
            host.resizePreviewChanged(nodeId, base.x, base.y, targetWidth, targetHeight, true);
            return;
        }
        var previewed = surface._growPreviewActive;
        if (previewed) {
            surface._growPreviewActive = false;
            surface._growPreviewBase = null;
            host._liveWidth = targetWidth;
            host._liveHeight = targetHeight;
            host.resizePreviewChanged(nodeId, base.x, base.y, targetWidth, targetHeight, false);
        }
        if (changed)
            host.resizeFinished(nodeId, base.x, base.y, targetWidth, targetHeight);
        if (previewed)
            host._liveGeometryActive = false;
    }

    // How the body text fits, as the automation node.fit_text op reports it.
    function textFitReport() {
        return {
            "mode": surface.bodyFitMode,
            "overflowing": surface.bodyTextOverflowing,
            "overflow_mark": String(bodyRichText.overflowMark || ""),
            "font_size": bodyRichText.fontSizeValue,
            "rendered_font_size": bodyRichText.effectiveFontSize,
            "aspect_locked": surface.bodyAspectLocked
        };
    }

    // Applies a scheduled grow-to-fit now instead of on the next event-loop turn, so an
    // automation op can keep the resize inside its own undo step.
    function settleTextFit() {
        if (surface._growPending || surface.bodyGrowToFit) {
            growToFitTimer.stop();
            surface._applyGrowToFit();
        }
        return surface.textFitReport();
    }

    function _bodyFallbackSuppressed() {
        var variantKey = surface._variantKey();
        return variantKey === "card"
            || variantKey === "callout"
            || variantKey === "multi_document"
            || variantKey === "tick"
            || variantKey === "timestamp"
            || variantKey === "message"
            || variantKey === "isometric_cube"
            || variantKey === "cube"
            || variantKey === "actor"
            || variantKey === "star"
            || variantKey === "x";
    }

    function _formatTimestamp(date) {
        var days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        function pad(value) {
            return value < 10 ? "0" + value : String(value);
        }
        return days[date.getDay()] + " "
            + months[date.getMonth()] + " "
            + pad(date.getDate()) + " "
            + date.getFullYear() + " "
            + pad(date.getHours()) + ":"
            + pad(date.getMinutes()) + ":"
            + pad(date.getSeconds());
    }

    function _timestampText() {
        return surface._formatTimestamp(new Date());
    }

    function _isTimestampPlaceholder(value) {
        return String(value || "").trim() === surface.timestampBodyPlaceholder;
    }

    function _timestampManualEditorText() {
        var body = surface._propertyText("body").trim();
        if (!surface.isTimestampSurface)
            return body;
        if (!body.length || surface._isTimestampPlaceholder(body) || surface.timestampLive)
            return surface.timestampNowText.length > 0 ? surface.timestampNowText : surface._timestampText();
        return body;
    }

    function _surfaceActions() {
        if (!surface.isTimestampSurface)
            return [];
        return [
            {
                "id": "timestamp_toggle_live",
                "label": surface.timestampLive ? "Freeze live timestamp" : "Live timestamp",
                "icon": "keep-live",
                "kind": "timestamp",
                "enabled": true,
                "primary": surface.timestampLive,
                "checked": surface.timestampLive
            },
            {
                "id": "timestamp_update_now",
                "label": "Update to current time",
                "icon": "clock-update",
                "kind": "timestamp",
                "enabled": !surface.timestampLive,
                "primary": false
            },
            {
                "id": "timestamp_edit_manual",
                "label": "Set timestamp manually",
                "icon": "calendar",
                "kind": "timestamp",
                "enabled": true,
                "primary": false
            }
        ];
    }

    function _resolvedBodyText() {
        var body = surface._propertyText("body");
        if (surface.isTimestampSurface) {
            if (surface.timestampLive)
                return surface.timestampNowText;
            if (surface._isTimestampPlaceholder(body))
                return surface.timestampSnapshotText;
        }
        if (body.trim().length > 0)
            return body;
        if (surface.bodyFallbackSuppressed)
            return "";
        var title = host && host.nodeData ? String(host.nodeData.title || "") : "";
        if (title.trim().length > 0)
            return title;
        return host && host.nodeData ? String(host.nodeData.display_name || "") : "";
    }

    function _titleValue() {
        if (!host || !host.nodeData)
            return "";
        var title = String(host.nodeData.title || "");
        if (title.trim().length > 0)
            return title;
        return String(host.nodeData.display_name || "");
    }

    function _commitProperty(key, value) {
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), String(key || ""), value);
    }

    function _beginInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _activeInlineEditor() {
        if (surface.editingTitle && titleEditor.visible)
            return titleEditor;
        if (!surface.isTimestampSurface && bodyRichText.editorVisible)
            return bodyRichText;
        if (surface.isCubeSurface && bodyTopRichText.editorVisible)
            return bodyTopRichText;
        if (surface.isCubeSurface && bodyRightRichText.editorVisible)
            return bodyRightRichText;
        if (surface.editingBody && bodyEditor.visible)
            return bodyEditor;
        return null;
    }

    function _commitActiveBodyEditor() {
        if (surface.isCubeSurface && bodyTopRichText.editorVisible)
            bodyTopRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        if (surface.isCubeSurface && bodyRightRichText.editorVisible)
            bodyRightRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        if (!surface.isTimestampSurface && bodyRichText.editorVisible)
            bodyRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        if (surface.editingBody && bodyEditor.visible)
            surface._commitBody(bodyEditor.draftText);
    }

    function _beginTitleEdit() {
        if (surface.editingTitle)
            return true;
        if (!host || !host.nodeData)
            return false;
        surface._commitActiveBodyEditor();
        surface.editingTitle = true;
        surface._beginInteraction();
        return true;
    }

    function _commitTitle(value) {
        var nextValue = String(value === undefined || value === null ? "" : value).trim();
        var current = surface._titleValue().trim();
        surface.editingTitle = false;
        if (!nextValue.length || nextValue === current) {
            titleEditor.text = surface._titleValue();
            return;
        }
        titleEditor.text = nextValue;
        surface._commitProperty("title", nextValue);
    }

    function _cancelTitleEdit() {
        titleEditor.text = surface._titleValue();
        surface.editingTitle = false;
    }

    function _activeRichTextBlock() {
        if (surface.isCubeSurface && bodyTopRichText.editorVisible)
            return bodyTopRichText;
        if (surface.isCubeSurface && bodyRightRichText.editorVisible)
            return bodyRightRichText;
        if (!surface.isTimestampSurface)
            return bodyRichText;
        return null;
    }

    function _commitActiveCubeFace() {
        if (surface.isCubeSurface && bodyTopRichText.editorVisible)
            bodyTopRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        if (surface.isCubeSurface && bodyRightRichText.editorVisible)
            bodyRightRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
    }

    function _beginBodyEdit() {
        if (surface.editingBody)
            return true;
        if (!host || !host.nodeData)
            return false;
        surface._commitActiveCubeFace();
        if (!surface.isTimestampSurface)
            return bodyRichText.requestInlineEditAt(bodyRichText.width * 0.5, bodyRichText.height * 0.5);
        surface.editingBody = true;
        surface._beginInteraction();
        Qt.callLater(function() {
            bodyEditor.syncDraftToCommitted();
            bodyEditor.activateEditor();
        });
        return true;
    }

    function _commitBody(value) {
        var nextValue = String(value === undefined || value === null ? "" : value);
        if (nextValue === surface._propertyText("body")) {
            surface.editingBody = false;
            return;
        }
        surface._commitProperty("body", nextValue);
        surface.editingBody = false;
    }

    function _beginBodyTopEdit() {
        if (surface.editingBodyTop)
            return true;
        if (!host || !host.nodeData)
            return false;
        if (bodyRichText.editorVisible)
            bodyRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        if (bodyRightRichText.editorVisible)
            bodyRightRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        return bodyTopRichText.requestInlineEditAt(bodyTopRichText.width * 0.5, bodyTopRichText.height * 0.5);
    }

    function _commitBodyTop(value) {
        var nextValue = String(value === undefined || value === null ? "" : value);
        if (nextValue === surface._propertyText("body_top")) {
            surface.editingBodyTop = false;
            return;
        }
        surface._commitProperty("body_top", nextValue);
        surface.editingBodyTop = false;
    }

    function _cancelBodyTopEdit() {
        bodyTopRichText._cancelTextEdit();
        surface.editingBodyTop = false;
    }

    function _beginBodyRightEdit() {
        if (surface.editingBodyRight)
            return true;
        if (!host || !host.nodeData)
            return false;
        if (bodyRichText.editorVisible)
            bodyRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        if (bodyTopRichText.editorVisible)
            bodyTopRichText.commitInlineEditFromExternalInteraction(-9999, -9999);
        return bodyRightRichText.requestInlineEditAt(bodyRightRichText.width * 0.5, bodyRightRichText.height * 0.5);
    }

    function _commitBodyRight(value) {
        var nextValue = String(value === undefined || value === null ? "" : value);
        if (nextValue === surface._propertyText("body_right")) {
            surface.editingBodyRight = false;
            return;
        }
        surface._commitProperty("body_right", nextValue);
        surface.editingBodyRight = false;
    }

    function _cancelBodyRightEdit() {
        bodyRightRichText._cancelTextEdit();
        surface.editingBodyRight = false;
    }

    function _commitLive(value) {
        var nextValue = Boolean(value);
        if (surface.timestampLive === nextValue)
            return;
        surface._commitProperty("live", nextValue);
    }

    function _setTimestampLive(enabled) {
        if (!surface.isTimestampSurface)
            return false;
        if (Boolean(enabled)) {
            surface.timestampNowText = surface._timestampText();
            surface._commitLive(true);
            return true;
        }
        var frozenText = surface._timestampText();
        surface.timestampNowText = frozenText;
        surface.timestampSnapshotText = frozenText;
        surface._commitLive(false);
        surface._commitBody(frozenText);
        return true;
    }

    function _updateTimestampNow() {
        if (!surface.isTimestampSurface || surface.timestampLive)
            return false;
        var nextValue = surface._timestampText();
        surface.timestampSnapshotText = nextValue;
        surface._commitLive(false);
        surface._commitBody(nextValue);
        return true;
    }

    function _openTimestampManualEditor() {
        if (!surface.isTimestampSurface)
            return false;
        surface.timestampManualEditorOpen = true;
        surface._beginInteraction();
        return true;
    }

    function acceptTimestampManualEdit(value) {
        if (!surface.isTimestampSurface)
            return false;
        var nextValue = String(value === undefined || value === null ? "" : value).trim();
        if (!nextValue.length)
            nextValue = surface._timestampText();
        surface.timestampManualEditorOpen = false;
        surface.timestampSnapshotText = nextValue;
        surface._commitLive(false);
        surface._commitBody(nextValue);
        return true;
    }

    function cancelTimestampManualEdit() {
        surface.timestampManualEditorOpen = false;
    }

    function _cancelBodyEdit() {
        bodyEditor.resetDraft();
        surface.editingBody = false;
    }

    function dispatchSurfaceAction(actionId) {
        var normalized = String(actionId || "");
        if (normalized === "timestamp_toggle_live")
            return surface._setTimestampLive(!surface.timestampLive);
        if (normalized === "timestamp_update_now")
            return surface._updateTimestampNow();
        if (normalized === "timestamp_edit_manual")
            return surface._openTimestampManualEditor();
        if (normalized === "text_fit_clip" || normalized === "text_fit_grow" || normalized === "text_fit_shrink")
            return surface._setBodyFitMode(normalized.substring("text_fit_".length));
        var richTextBlock = surface._activeRichTextBlock();
        if (richTextBlock !== null)
            return richTextBlock.dispatchSurfaceAction(actionId);
        return false;
    }

    function requestInlineEditAt(localX, localY) {
        if (surface.editingTitle)
            return GraphNodeHostHitTesting.pointInRect(localX, localY, titleEditor.interactiveRect);
        if (surface.isCubeSurface) {
            if (bodyTopRichText.requestInlineEditAt(localX, localY))
                return true;
            if (bodyRightRichText.requestInlineEditAt(localX, localY))
                return true;
        }
        if (!surface.isTimestampSurface) {
            if (bodyRichText.requestInlineEditAt(localX, localY))
                return true;
            if (bodyRichText.editorVisible
                    || !GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditInteractionRegion.interactiveRect))
                return false;
            return surface._beginBodyEdit();
        }
        if (surface.editingBody)
            return GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditorInteractionRegion.interactiveRect);
        if (!GraphNodeHostHitTesting.pointInRect(localX, localY, bodyDisplayInteractionRegion.interactiveRect))
            return false;
        return surface._beginBodyEdit();
    }

    function beginInlineTitleEdit() {
        return surface._beginTitleEdit();
    }

    function commitInlineEditFromExternalInteraction(localX, localY) {
        if (surface.editingTitle) {
            if (GraphNodeHostHitTesting.pointInRect(localX, localY, titleEditor.interactiveRect))
                return false;
            surface._commitTitle(titleEditor.text);
            return true;
        }
        if (surface.isCubeSurface && bodyTopRichText.editorVisible) {
            if (!bodyTopRichText.commitInlineEditFromExternalInteraction(localX, localY))
                return false;
            return true;
        }
        if (surface.isCubeSurface && bodyRightRichText.editorVisible) {
            if (!bodyRightRichText.commitInlineEditFromExternalInteraction(localX, localY))
                return false;
            return true;
        }
        if (!surface.isTimestampSurface)
            return bodyRichText.commitInlineEditFromExternalInteraction(localX, localY);
        if (!surface.editingBody)
            return false;
        if (GraphNodeHostHitTesting.pointInRect(localX, localY, bodyEditorInteractionRegion.interactiveRect))
            return false;
        surface._commitBody(bodyEditor.draftText);
        return true;
    }

    onTimestampLiveChanged: {
        surface.timestampNowText = surface._timestampText();
        if (!surface.timestampLive)
            surface.timestampSnapshotText = surface.timestampNowText;
    }

    onVisibleChanged: {
        if (!visible)
            surface.timestampManualEditorOpen = false;
    }

    on_GrowInputKeyChanged: surface._scheduleGrowToFit()
    // New, pasted, and reopened grow-to-fit shapes fit their text on load too.
    Component.onCompleted: surface._scheduleGrowToFit()

    Timer {
        id: growToFitTimer
        interval: 0
        onTriggered: surface._applyGrowToFit()
    }

    Connections {
        target: surface.host

        function on_ResizeInteractionActiveChanged() {
            if (surface.host && !surface.host._resizeInteractionActive)
                surface._scheduleGrowToFit();
        }
    }

    Timer {
        id: timestampLiveTimer
        interval: 1000
        repeat: true
        running: surface.timestampLive && surface.visible
        triggeredOnStart: true
        onTriggered: {
            surface.timestampNowText = surface._timestampText();
        }
    }

    // Shape-aware selection glow: a glow-coloured copy of the flowchart silhouette
    // blurred by a MultiEffect, so the selection bloom follows the actual shape
    // (actor, cylinder, callout, …) instead of the card rectangle. Mirrors the shape
    // shadow pattern above. Full-fidelity only; suppressed under any execution state.
    // The rectangular card glow in GraphNodeChromeBackground is gated off for flowchart
    // surfaces (isFlowchartSurface) so the two never both render.
    FlowchartShapeCanvas {
        id: flowchartSelectedGlowSource
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: surface.shapeCanvasHeight
        visible: false
        variant: host ? host.surfaceVariant : ""
        gradientActive: false
        fillColor: host ? host.selectedGlowColor : "transparent"
        strokeColor: host ? host.selectedGlowColor : "transparent"
        strokeWidth: host ? Number(host.resolvedBorderWidth || 1) : 1
    }

    MultiEffect {
        id: flowchartSelectedHalo
        objectName: "graphNodeFlowchartSelectedHalo"
        anchors.fill: flowchartSelectedGlowSource
        source: flowchartSelectedGlowSource
        z: -1
        autoPaddingEnabled: true
        blurEnabled: true
        blur: 1.0
        blurMax: 40
        saturation: 0.35
        visible: opacity > 0.01
        opacity: (host
            && host.isSelected
            && !host.isRunningNode
            && !host.isFailedNode
            && !host.isWarningNode
            && !host.isCompletedNode
            && !host.isFreshRunNode
            && !host.isSelectedRunPreviewNode) ? 0.85 : 0.0
        Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.InOutCubic } }
    }

    FlowchartShapeCanvas {
        id: flowchartShapeSource
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: surface.shapeCanvasHeight
        visible: !surface.shapeShadowVisible
        variant: host ? host.surfaceVariant : ""
        fillColor: host ? host.surfaceColor : "#1b1d22"
        gradientActive: host ? host.bodyGradientActive : false
        gradientStartColor: host ? host.bodyGradientStartColor : fillColor
        gradientEndColor: host ? host.bodyGradientEndColor : fillColor
        gradientDirection: host ? host.bodyGradientDirection : "south"
        strokeColor: host
            ? (host.isFailedNode
                ? host.failureOutlineColor
                : (host.isRunningNode
                    ? host.runningOutlineColor
                    : (host.isWarningNode
                        ? host.warningOutlineColor
                        : (host.isCompletedNode || host.isFreshRunNode
                            ? host.completedOutlineColor
                            : (host.isSelected ? host.selectedOutlineColor : host.outlineColor)))))
            : "#3a3d45"
        strokeWidth: host ? Number(host.resolvedBorderWidth || 1) : 1
    }

    FlowchartShapeCanvas {
        id: flowchartShadowSource
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: surface.shapeCanvasHeight
        visible: false
        layer.enabled: surface.shapeShadowCacheActive
        variant: host ? host.surfaceVariant : ""
        fillColor: host ? host.surfaceColor : "#1b1d22"
        gradientActive: host ? host.bodyGradientActive : false
        gradientStartColor: host ? host.bodyGradientStartColor : fillColor
        gradientEndColor: host ? host.bodyGradientEndColor : fillColor
        gradientDirection: host ? host.bodyGradientDirection : "south"
        strokeColor: host
            ? (host.isSelected ? host.selectedOutlineColor : host.outlineColor)
            : "#3a3d45"
        strokeWidth: host ? Number(host.resolvedBorderWidth || 1) : 1
    }

    MultiEffect {
        id: flowchartShadow
        objectName: "graphNodeFlowchartShadow"
        property bool cacheActive: surface.shapeShadowCacheActive
        property string cacheKey: surface.shapeShadowCacheKey
        visible: surface.shapeShadowVisible
        anchors.fill: flowchartShadowSource
        source: flowchartShadowSource
        shadowEnabled: true
        shadowColor: "#000000"
        shadowOpacity: host ? Math.max(0.0, Math.min(1.0, Number(host.shadowStrength || 0) / 100.0)) : 0.7
        blurMax: 40
        shadowBlur: host ? Math.max(0.0, Math.min(1.0, Number(host.shadowSoftness || 0) / 100.0)) : 0.5
        shadowHorizontalOffset: 0
        shadowVerticalOffset: host ? Number(host.shadowOffset || 0) : 4
    }

    Item {
        id: bodyEditTarget
        visible: false
        x: surface.bodyEditHitRegion.x
        y: surface.bodyEditHitRegion.y
        width: surface.bodyEditHitRegion.width
        height: surface.bodyEditHitRegion.height
    }

    SurfaceControls.GraphSurfaceInteractiveRegion {
        id: bodyEditInteractionRegion
        host: surface.host
        targetItem: bodyEditTarget
        enabled: !surface.isTimestampSurface && bodyRichText.visible
    }

    Item {
        id: bodyBounds
        objectName: "graphNodeFlowchartBodyBounds"
        x: surface.bodyTextRegion.x
        y: surface.bodyTextRegion.y
        width: surface.bodyTextRegion.width
        height: surface.bodyTextRegion.height
        clip: true

        Text {
            id: flowchartBodyText
            objectName: surface.isTimestampSurface ? "graphNodeFlowchartBodyText" : ""
            property int effectiveRenderType: renderType
            visible: surface.isTimestampSurface && !surface.editingBody && !surface.editingTitle
            anchors.fill: parent
            text: surface.bodyValue
            color: surface.bodyTextColor
            font.pixelSize: surface.bodyFontSize
            font.bold: surface.bodyFontBold
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }

        GraphRichTextBlock {
            id: bodyRichText
            objectName: "graphNodeFlowchartRichTextBlock"
            visible: !surface.isTimestampSurface && !surface.editingTitle
            anchors.fill: parent
            host: surface.host
            contentPropertyKey: "body"
            formatPropertyKey: "body_format"
            stylePropertyPrefix: "body_"
            defaultText: surface.bodyValue
            useDefaultTextWhenBlank: true
            defaultFormat: "plain"
            placeholderValue: "Body"
            defaultFontSize: surface.bodyFontSize
            defaultFontBold: surface.bodyFontBold
            defaultTextColor: surface.bodyTextColor
            defaultHorizontalAlignment: "center"
            defaultVerticalAlignment: "middle"
            defaultLineHeight: 1.0
            defaultPadding: 0
            renderedTextObjectName: "graphNodeFlowchartBodyText"
            editorWrapperObjectName: "graphNodeFlowchartBodyEditor"
            editorObjectName: "graphNodeFlowchartBodyEditorField"
            fitMeasurementEnabled: !surface.isTimestampSurface
            shrinkToFit: surface.bodyShrinkToFit
            overflowIndicatorEnabled: !surface.isTimestampSurface && !surface._growPending
            overflowIndicatorObjectName: "graphNodeFlowchartBodyOverflowIndicator"
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyDisplayInteractionRegion
            host: surface.host
            targetItem: surface.isTimestampSurface ? flowchartBodyText : bodyRichText
            enabled: surface.isTimestampSurface ? flowchartBodyText.visible : bodyRichText.visible
        }

        SurfaceControls.GraphSurfaceInlineTextEditor {
            id: bodyEditor
            objectName: surface.isTimestampSurface ? "graphNodeFlowchartBodyEditor" : ""
            anchors.fill: parent
            visible: surface.isTimestampSurface && surface.editingBody && !surface.editingTitle
            host: surface.host
            committedText: surface._propertyText("body")
            fontPixelSize: surface.bodyFontSize
            fontBold: surface.bodyFontBold
            textColor: surface.bodyTextColor
            fieldObjectName: surface.isTimestampSurface ? "graphNodeFlowchartBodyEditorField" : ""
            horizontalAlignment: TextInput.AlignHCenter
            centerTextVertically: true
            onControlStarted: surface._beginInteraction()
            onCommitRequested: function(value) {
                surface._commitBody(value);
            }
            onCancelRequested: {
                surface._cancelBodyEdit();
            }
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyEditorInteractionRegion
            host: surface.host
            targetItem: bodyEditor
            enabled: bodyEditor.visible
        }

        SurfaceControls.GraphSurfaceTextField {
            id: titleEditor
            objectName: "graphNodeFlowchartTitleEditor"
            anchors.fill: parent
            visible: surface.editingTitle
            host: surface.host
            text: surface._titleValue()
            textColor: surface.bodyTextColor
            fillColor: "transparent"
            borderColor: "transparent"
            focusBorderColor: "transparent"
            leftPadding: 0
            rightPadding: 0
            horizontalAlignment: TextInput.AlignHCenter
            verticalAlignment: TextInput.AlignVCenter
            font.pixelSize: surface.bodyFontSize
            font.weight: surface.bodyFontBold ? Font.Bold : Font.Normal

            onVisibleChanged: {
                if (visible) {
                    text = surface._titleValue();
                    forceActiveFocus();
                    cursorPosition = text.length;
                    deselect();
                }
            }

            onAccepted: {
                surface._commitTitle(text);
            }

            onActiveFocusChanged: {
                if (!activeFocus && surface.editingTitle)
                    surface._commitTitle(text);
            }

            Keys.onEscapePressed: function(event) {
                surface._cancelTitleEdit();
                event.accepted = true;
            }
        }
    }

    Item {
        id: cubeTopFaceBounds
        visible: surface.isCubeSurface
        x: parent.width * 0.30
        width: parent.width * 0.40
        y: Math.max(0, surface.isometricCubeOffset * 0.5)
        height: Math.max(16, surface.isometricCubeOffset)
        clip: true

        Text {
            id: cubeTopFaceText
            objectName: ""
            anchors.fill: parent
            visible: false
            text: surface._propertyText("body_top")
            color: surface.bodyTextColor
            font.pixelSize: surface.bodyFontSize
            font.bold: surface.bodyFontBold
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }

        GraphRichTextBlock {
            id: bodyTopRichText
            objectName: "graphNodeFlowchartBodyTopRichTextBlock"
            anchors.fill: parent
            visible: surface.isCubeSurface
            host: surface.host
            contentPropertyKey: "body_top"
            formatPropertyKey: "body_top_format"
            stylePropertyPrefix: "body_top_"
            defaultText: ""
            defaultFormat: "plain"
            placeholderValue: "Top Face"
            defaultFontSize: surface.bodyFontSize
            defaultFontBold: surface.bodyFontBold
            defaultTextColor: surface.bodyTextColor
            defaultHorizontalAlignment: "center"
            defaultVerticalAlignment: "middle"
            defaultLineHeight: 1.0
            defaultPadding: 0
            renderedTextObjectName: "graphNodeFlowchartBodyTopText"
            editorWrapperObjectName: "graphNodeFlowchartBodyTopEditor"
            editorObjectName: "graphNodeFlowchartBodyTopEditorField"
            fitMeasurementEnabled: surface.isCubeSurface
            shrinkToFit: surface.bodyShrinkToFit
            overflowIndicatorEnabled: surface.isCubeSurface
            overflowIndicatorObjectName: "graphNodeFlowchartBodyTopOverflowIndicator"
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyTopDisplayInteractionRegion
            host: surface.host
            targetItem: bodyTopRichText
            enabled: bodyTopRichText.visible && surface.isCubeSurface
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyTopEditorInteractionRegion
            host: surface.host
            targetItem: bodyTopRichText
            enabled: bodyTopRichText.visible && bodyTopRichText.editorVisible
        }
    }

    Item {
        id: cubeRightFaceBounds
        visible: surface.isCubeSurface
        readonly property real rightFaceHeight: Math.max(
            16,
            Math.min(
                parent.height * 0.32,
                parent.height - 2 * surface.isometricCubeOffset - 2 * surface.bodyVerticalInset
            )
        )
        x: parent.width * 0.55
        width: parent.width * 0.40
        y: Math.max(0, surface.isometricFrontFaceCenterY - rightFaceHeight * 0.5)
        height: rightFaceHeight
        clip: true

        Text {
            id: cubeRightFaceText
            objectName: ""
            anchors.fill: parent
            visible: false
            text: surface._propertyText("body_right")
            color: surface.bodyTextColor
            font.pixelSize: surface.bodyFontSize
            font.bold: surface.bodyFontBold
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }

        GraphRichTextBlock {
            id: bodyRightRichText
            objectName: "graphNodeFlowchartBodyRightRichTextBlock"
            anchors.fill: parent
            visible: surface.isCubeSurface
            host: surface.host
            contentPropertyKey: "body_right"
            formatPropertyKey: "body_right_format"
            stylePropertyPrefix: "body_right_"
            defaultText: ""
            defaultFormat: "plain"
            placeholderValue: "Right Face"
            defaultFontSize: surface.bodyFontSize
            defaultFontBold: surface.bodyFontBold
            defaultTextColor: surface.bodyTextColor
            defaultHorizontalAlignment: "center"
            defaultVerticalAlignment: "middle"
            defaultLineHeight: 1.0
            defaultPadding: 0
            renderedTextObjectName: "graphNodeFlowchartBodyRightText"
            editorWrapperObjectName: "graphNodeFlowchartBodyRightEditor"
            editorObjectName: "graphNodeFlowchartBodyRightEditorField"
            fitMeasurementEnabled: surface.isCubeSurface
            shrinkToFit: surface.bodyShrinkToFit
            overflowIndicatorEnabled: surface.isCubeSurface
            overflowIndicatorObjectName: "graphNodeFlowchartBodyRightOverflowIndicator"
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyRightDisplayInteractionRegion
            host: surface.host
            targetItem: bodyRightRichText
            enabled: bodyRightRichText.visible && surface.isCubeSurface
        }

        SurfaceControls.GraphSurfaceInteractiveRegion {
            id: bodyRightEditorInteractionRegion
            host: surface.host
            targetItem: bodyRightRichText
            enabled: bodyRightRichText.visible && bodyRightRichText.editorVisible
        }
    }

    GraphComponents.GraphInlinePropertiesLayer {
        id: inlinePropertiesLayer
        anchors.fill: parent
        host: surface.host
    }
}
