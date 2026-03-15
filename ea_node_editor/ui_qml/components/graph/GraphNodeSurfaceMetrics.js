.pragma library

var STANDARD_DEFAULT_WIDTH = 210.0;
var STANDARD_MIN_WIDTH = 120.0;
var STANDARD_MIN_HEIGHT = 50.0;
var STANDARD_COLLAPSED_WIDTH = 130.0;
var STANDARD_COLLAPSED_HEIGHT = 36.0;
var STANDARD_HEADER_HEIGHT = 24.0;
var STANDARD_HEADER_TOP_MARGIN = 4.0;
var STANDARD_BODY_TOP = 30.0;
var STANDARD_PORT_HEIGHT = 18.0;
var STANDARD_INLINE_ROW_HEIGHT = 26.0;
var STANDARD_INLINE_ROW_SPACING = 4.0;
var STANDARD_INLINE_SECTION_PADDING = 8.0;
var STANDARD_PORT_CENTER_OFFSET = 6.0;
var STANDARD_PORT_SIDE_MARGIN = 8.0;
var STANDARD_PORT_DOT_RADIUS = 3.5;
var STANDARD_RESIZE_HANDLE_SIZE = 16.0;
var STANDARD_BOTTOM_PADDING = 8.0;

var FLOWCHART_COLLAPSED_WIDTH = 140.0;
var FLOWCHART_COLLAPSED_HEIGHT = 40.0;
var FLOWCHART_TITLE_HEIGHT = 24.0;
var FLOWCHART_PORT_HEIGHT = 18.0;
var FLOWCHART_PORT_CENTER_OFFSET = 6.0;
var FLOWCHART_PORT_DOT_RADIUS = 4.0;
var FLOWCHART_RESIZE_HANDLE_SIZE = 16.0;
var FLOWCHART_INLINE_GAP = 8.0;
var FLOWCHART_PORT_SECTION_TOP = 12.0;

var PASSIVE_SURFACE_RESIZE_HANDLE_SIZE = 16.0;

function _metricNumber(source, key, fallback) {
    var value = source ? Number(source[key]) : NaN;
    if (!isFinite(value))
        value = fallback;
    return value;
}

function _metricBool(source, key, fallback) {
    if (!source || source[key] === undefined)
        return Boolean(fallback);
    return Boolean(source[key]);
}

function inlineBodyHeight(node) {
    var inlineProperties = node && node.inline_properties ? node.inline_properties : [];
    var count = inlineProperties.length;
    if (count <= 0)
        return 0.0;
    return 8.0 + count * 26.0 + Math.max(0, count - 1) * 4.0;
}

function _visiblePortCounts(node) {
    var ports = node && node.ports ? node.ports : [];
    var inputCount = 0;
    var outputCount = 0;
    for (var i = 0; i < ports.length; i++) {
        var port = ports[i];
        if (!port || port.exposed === false)
            continue;
        if (String(port.direction || "") === "in")
            inputCount += 1;
        else if (String(port.direction || "") === "out")
            outputCount += 1;
    }
    return {
        "inputCount": inputCount,
        "outputCount": outputCount,
        "portCount": Math.max(inputCount, outputCount, 1)
    };
}

function _normalizedFlowchartVariant(value) {
    var variant = String(value || "").trim().toLowerCase();
    if (variant === "start" || variant === "end" || variant === "process" || variant === "decision"
        || variant === "document" || variant === "connector" || variant === "input_output"
        || variant === "predefined_process" || variant === "database") {
        return variant;
    }
    return "process";
}

function _flowchartVariantLayout(variant) {
    var normalized = _normalizedFlowchartVariant(variant);
    switch (normalized) {
    case "start":
    case "end":
        return {
            "defaultWidth": 228.0,
            "minWidth": 152.0,
            "minHeight": 78.0,
            "titleTop": 18.0,
            "titleLeftMargin": 34.0,
            "titleRightMargin": 34.0,
            "bodyLeftMargin": 30.0,
            "bodyRightMargin": 30.0,
            "bodyBottomMargin": 16.0,
            "square": false
        };
    case "decision":
        return {
            "defaultWidth": 236.0,
            "minWidth": 192.0,
            "minHeight": 128.0,
            "titleTop": 26.0,
            "titleLeftMargin": 66.0,
            "titleRightMargin": 66.0,
            "bodyLeftMargin": 46.0,
            "bodyRightMargin": 46.0,
            "bodyBottomMargin": 22.0,
            "square": false
        };
    case "document":
        return {
            "defaultWidth": 228.0,
            "minWidth": 176.0,
            "minHeight": 104.0,
            "titleTop": 18.0,
            "titleLeftMargin": 24.0,
            "titleRightMargin": 24.0,
            "bodyLeftMargin": 20.0,
            "bodyRightMargin": 20.0,
            "bodyBottomMargin": 24.0,
            "square": false
        };
    case "connector":
        return {
            "defaultWidth": 108.0,
            "minWidth": 92.0,
            "minHeight": 92.0,
            "titleTop": 18.0,
            "titleLeftMargin": 20.0,
            "titleRightMargin": 20.0,
            "bodyLeftMargin": 20.0,
            "bodyRightMargin": 20.0,
            "bodyBottomMargin": 18.0,
            "square": true
        };
    case "input_output":
        return {
            "defaultWidth": 236.0,
            "minWidth": 182.0,
            "minHeight": 94.0,
            "titleTop": 20.0,
            "titleLeftMargin": 34.0,
            "titleRightMargin": 34.0,
            "bodyLeftMargin": 28.0,
            "bodyRightMargin": 28.0,
            "bodyBottomMargin": 18.0,
            "square": false
        };
    case "predefined_process":
        return {
            "defaultWidth": 236.0,
            "minWidth": 182.0,
            "minHeight": 94.0,
            "titleTop": 20.0,
            "titleLeftMargin": 36.0,
            "titleRightMargin": 36.0,
            "bodyLeftMargin": 30.0,
            "bodyRightMargin": 30.0,
            "bodyBottomMargin": 18.0,
            "square": false
        };
    case "database":
        return {
            "defaultWidth": 228.0,
            "minWidth": 180.0,
            "minHeight": 128.0,
            "titleTop": 24.0,
            "titleLeftMargin": 30.0,
            "titleRightMargin": 30.0,
            "bodyLeftMargin": 24.0,
            "bodyRightMargin": 24.0,
            "bodyBottomMargin": 22.0,
            "square": false
        };
    case "process":
    default:
        return {
            "defaultWidth": 224.0,
            "minWidth": 156.0,
            "minHeight": 84.0,
            "titleTop": 18.0,
            "titleLeftMargin": 20.0,
            "titleRightMargin": 20.0,
            "bodyLeftMargin": 18.0,
            "bodyRightMargin": 18.0,
            "bodyBottomMargin": 16.0,
            "square": false
        };
    }
}

function _normalizedPlanningVariant(value) {
    var variant = String(value || "").trim().toLowerCase();
    if (variant === "task_card" || variant === "milestone_card" || variant === "risk_card" || variant === "decision_card")
        return variant;
    return "task_card";
}

function _planningVariantLayout(variant) {
    switch (_normalizedPlanningVariant(variant)) {
    case "milestone_card":
        return {
            "defaultWidth": 248.0,
            "defaultHeight": 156.0,
            "minWidth": 190.0,
            "minHeight": 136.0,
            "titleTop": 12.0,
            "titleHeight": 24.0,
            "titleLeftMargin": 14.0,
            "titleRightMargin": 14.0,
            "bodyTop": 44.0,
            "bodyHeight": 100.0,
            "bodyLeftMargin": 14.0,
            "bodyRightMargin": 14.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    case "risk_card":
        return {
            "defaultWidth": 252.0,
            "defaultHeight": 180.0,
            "minWidth": 196.0,
            "minHeight": 156.0,
            "titleTop": 12.0,
            "titleHeight": 24.0,
            "titleLeftMargin": 14.0,
            "titleRightMargin": 14.0,
            "bodyTop": 44.0,
            "bodyHeight": 124.0,
            "bodyLeftMargin": 14.0,
            "bodyRightMargin": 14.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    case "decision_card":
        return {
            "defaultWidth": 252.0,
            "defaultHeight": 180.0,
            "minWidth": 196.0,
            "minHeight": 156.0,
            "titleTop": 12.0,
            "titleHeight": 24.0,
            "titleLeftMargin": 14.0,
            "titleRightMargin": 14.0,
            "bodyTop": 44.0,
            "bodyHeight": 124.0,
            "bodyLeftMargin": 14.0,
            "bodyRightMargin": 14.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    case "task_card":
    default:
        return {
            "defaultWidth": 248.0,
            "defaultHeight": 168.0,
            "minWidth": 190.0,
            "minHeight": 148.0,
            "titleTop": 12.0,
            "titleHeight": 24.0,
            "titleLeftMargin": 14.0,
            "titleRightMargin": 14.0,
            "bodyTop": 44.0,
            "bodyHeight": 112.0,
            "bodyLeftMargin": 14.0,
            "bodyRightMargin": 14.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    }
}

function _normalizedAnnotationVariant(value) {
    var variant = String(value || "").trim().toLowerCase();
    if (variant === "sticky_note" || variant === "callout" || variant === "section_header")
        return variant;
    return "sticky_note";
}

function _annotationVariantLayout(variant) {
    switch (_normalizedAnnotationVariant(variant)) {
    case "callout":
        return {
            "defaultWidth": 236.0,
            "defaultHeight": 156.0,
            "minWidth": 184.0,
            "minHeight": 132.0,
            "titleTop": 14.0,
            "titleHeight": 22.0,
            "titleLeftMargin": 16.0,
            "titleRightMargin": 16.0,
            "bodyTop": 42.0,
            "bodyHeight": 102.0,
            "bodyLeftMargin": 16.0,
            "bodyRightMargin": 16.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    case "section_header":
        return {
            "defaultWidth": 280.0,
            "defaultHeight": 112.0,
            "minWidth": 220.0,
            "minHeight": 96.0,
            "titleTop": 18.0,
            "titleHeight": 24.0,
            "titleLeftMargin": 18.0,
            "titleRightMargin": 18.0,
            "bodyTop": 52.0,
            "bodyHeight": 34.0,
            "bodyLeftMargin": 18.0,
            "bodyRightMargin": 18.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    case "sticky_note":
    default:
        return {
            "defaultWidth": 228.0,
            "defaultHeight": 152.0,
            "minWidth": 176.0,
            "minHeight": 128.0,
            "titleTop": 14.0,
            "titleHeight": 22.0,
            "titleLeftMargin": 14.0,
            "titleRightMargin": 14.0,
            "bodyTop": 42.0,
            "bodyHeight": 98.0,
            "bodyLeftMargin": 14.0,
            "bodyRightMargin": 14.0,
            "bodyBottomMargin": 12.0,
            "titleCentered": false
        };
    }
}

function _resolvedDimension(value, fallback) {
    var numeric = Number(value);
    if (!(numeric > 0.0))
        numeric = fallback;
    return numeric;
}

function _standardSurfaceMetrics(node, source) {
    var portCount = _visiblePortCounts(node).portCount;
    var bodyHeight = _metricNumber(source, "body_height", inlineBodyHeight(node));
    return {
        "default_width": _metricNumber(source, "default_width", STANDARD_DEFAULT_WIDTH),
        "default_height": _metricNumber(
            source,
            "default_height",
            STANDARD_HEADER_HEIGHT + bodyHeight + portCount * STANDARD_PORT_HEIGHT + STANDARD_BOTTOM_PADDING
        ),
        "min_width": _metricNumber(source, "min_width", STANDARD_MIN_WIDTH),
        "min_height": _metricNumber(source, "min_height", STANDARD_MIN_HEIGHT),
        "collapsed_width": _metricNumber(source, "collapsed_width", STANDARD_COLLAPSED_WIDTH),
        "collapsed_height": _metricNumber(source, "collapsed_height", STANDARD_COLLAPSED_HEIGHT),
        "header_height": _metricNumber(source, "header_height", STANDARD_HEADER_HEIGHT),
        "header_top_margin": _metricNumber(source, "header_top_margin", STANDARD_HEADER_TOP_MARGIN),
        "body_top": _metricNumber(source, "body_top", STANDARD_BODY_TOP),
        "body_height": bodyHeight,
        "port_top": _metricNumber(source, "port_top", STANDARD_BODY_TOP + bodyHeight),
        "port_height": _metricNumber(source, "port_height", STANDARD_PORT_HEIGHT),
        "port_center_offset": _metricNumber(source, "port_center_offset", STANDARD_PORT_CENTER_OFFSET),
        "port_side_margin": _metricNumber(source, "port_side_margin", STANDARD_PORT_SIDE_MARGIN),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", STANDARD_PORT_DOT_RADIUS),
        "resize_handle_size": _metricNumber(source, "resize_handle_size", STANDARD_RESIZE_HANDLE_SIZE),
        "title_top": _metricNumber(source, "title_top", STANDARD_HEADER_TOP_MARGIN),
        "title_height": _metricNumber(source, "title_height", STANDARD_HEADER_HEIGHT),
        "title_left_margin": _metricNumber(source, "title_left_margin", 10.0),
        "title_right_margin": _metricNumber(source, "title_right_margin", 10.0),
        "title_centered": _metricBool(source, "title_centered", false),
        "body_left_margin": _metricNumber(source, "body_left_margin", 8.0),
        "body_right_margin": _metricNumber(source, "body_right_margin", 8.0),
        "body_bottom_margin": _metricNumber(source, "body_bottom_margin", STANDARD_BOTTOM_PADDING),
        "show_header_background": _metricBool(source, "show_header_background", true),
        "show_accent_bar": _metricBool(source, "show_accent_bar", true),
        "use_host_chrome": _metricBool(source, "use_host_chrome", true)
    };
}

function _flowchartSurfaceMetrics(node, source) {
    var layout = _flowchartVariantLayout(node && node.surface_variant);
    var portCount = _visiblePortCounts(node).portCount;
    var bodyHeight = _metricNumber(source, "body_height", inlineBodyHeight(node));
    var basePortSectionTop = bodyHeight > 0.0
        ? layout.titleTop + FLOWCHART_TITLE_HEIGHT + FLOWCHART_INLINE_GAP + bodyHeight + FLOWCHART_INLINE_GAP
        : FLOWCHART_PORT_SECTION_TOP;
    var defaultHeight = Math.max(
        layout.minHeight,
        basePortSectionTop + portCount * FLOWCHART_PORT_HEIGHT + layout.bodyBottomMargin
    );
    var defaultWidth = layout.defaultWidth;
    var minWidth = layout.minWidth;
    if (layout.square) {
        defaultWidth = Math.max(defaultWidth, defaultHeight);
        minWidth = Math.max(minWidth, layout.minHeight);
    }
    defaultHeight = _metricNumber(source, "default_height", defaultHeight);
    defaultWidth = _metricNumber(source, "default_width", defaultWidth);
    minWidth = _metricNumber(source, "min_width", minWidth);
    var minHeight = _metricNumber(source, "min_height", layout.minHeight);
    var activeWidth = _resolvedDimension(node && node.width, defaultWidth);
    var activeHeight = _resolvedDimension(node && node.height, defaultHeight);
    var titleTop = bodyHeight > 0.0
        ? layout.titleTop
        : Math.max(12.0, (activeHeight - FLOWCHART_TITLE_HEIGHT) * 0.5);
    titleTop = _metricNumber(source, "title_top", titleTop);
    var bodyTop = _metricNumber(source, "body_top", titleTop + FLOWCHART_TITLE_HEIGHT + FLOWCHART_INLINE_GAP);
    var portSectionTop = bodyHeight > 0.0
        ? bodyTop + bodyHeight + FLOWCHART_INLINE_GAP
        : FLOWCHART_PORT_SECTION_TOP;
    var availablePortHeight = Math.max(
        portCount * FLOWCHART_PORT_HEIGHT,
        activeHeight - portSectionTop - layout.bodyBottomMargin
    );
    return {
        "default_width": defaultWidth,
        "default_height": defaultHeight,
        "min_width": minWidth,
        "min_height": minHeight,
        "collapsed_width": _metricNumber(source, "collapsed_width", FLOWCHART_COLLAPSED_WIDTH),
        "collapsed_height": _metricNumber(source, "collapsed_height", FLOWCHART_COLLAPSED_HEIGHT),
        "header_height": _metricNumber(source, "header_height", 0.0),
        "header_top_margin": _metricNumber(source, "header_top_margin", 0.0),
        "body_top": bodyTop,
        "body_height": bodyHeight,
        "port_top": _metricNumber(
            source,
            "port_top",
            portSectionTop + Math.max(0.0, (availablePortHeight - portCount * FLOWCHART_PORT_HEIGHT) * 0.5)
        ),
        "port_height": _metricNumber(source, "port_height", FLOWCHART_PORT_HEIGHT),
        "port_center_offset": _metricNumber(source, "port_center_offset", FLOWCHART_PORT_CENTER_OFFSET),
        "port_side_margin": _metricNumber(source, "port_side_margin", 0.0),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", FLOWCHART_PORT_DOT_RADIUS),
        "resize_handle_size": _metricNumber(source, "resize_handle_size", FLOWCHART_RESIZE_HANDLE_SIZE),
        "title_top": titleTop,
        "title_height": _metricNumber(source, "title_height", FLOWCHART_TITLE_HEIGHT),
        "title_left_margin": _metricNumber(source, "title_left_margin", layout.titleLeftMargin),
        "title_right_margin": _metricNumber(source, "title_right_margin", layout.titleRightMargin),
        "title_centered": _metricBool(source, "title_centered", true),
        "body_left_margin": _metricNumber(source, "body_left_margin", layout.bodyLeftMargin),
        "body_right_margin": _metricNumber(source, "body_right_margin", layout.bodyRightMargin),
        "body_bottom_margin": _metricNumber(source, "body_bottom_margin", layout.bodyBottomMargin),
        "show_header_background": _metricBool(source, "show_header_background", false),
        "show_accent_bar": _metricBool(source, "show_accent_bar", false),
        "use_host_chrome": _metricBool(source, "use_host_chrome", false)
    };
}

function _passivePanelSurfaceMetrics(node, source, layout) {
    var activeHeight = _resolvedDimension(node && node.height, layout.defaultHeight);
    var bodyTop = _metricNumber(source, "body_top", layout.bodyTop);
    var bodyBottomMargin = _metricNumber(source, "body_bottom_margin", layout.bodyBottomMargin);
    var bodyHeight = _metricNumber(
        source,
        "body_height",
        Math.max(layout.bodyHeight, activeHeight - bodyTop - bodyBottomMargin)
    );
    return {
        "default_width": _metricNumber(source, "default_width", layout.defaultWidth),
        "default_height": _metricNumber(source, "default_height", layout.defaultHeight),
        "min_width": _metricNumber(source, "min_width", layout.minWidth),
        "min_height": _metricNumber(source, "min_height", layout.minHeight),
        "collapsed_width": _metricNumber(source, "collapsed_width", STANDARD_COLLAPSED_WIDTH),
        "collapsed_height": _metricNumber(source, "collapsed_height", STANDARD_COLLAPSED_HEIGHT),
        "header_height": _metricNumber(source, "header_height", 0.0),
        "header_top_margin": _metricNumber(source, "header_top_margin", 0.0),
        "body_top": bodyTop,
        "body_height": bodyHeight,
        "port_top": _metricNumber(source, "port_top", activeHeight - bodyBottomMargin),
        "port_height": _metricNumber(source, "port_height", 0.0),
        "port_center_offset": _metricNumber(source, "port_center_offset", 0.0),
        "port_side_margin": _metricNumber(source, "port_side_margin", STANDARD_PORT_SIDE_MARGIN),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", STANDARD_PORT_DOT_RADIUS),
        "resize_handle_size": _metricNumber(source, "resize_handle_size", PASSIVE_SURFACE_RESIZE_HANDLE_SIZE),
        "title_top": _metricNumber(source, "title_top", layout.titleTop),
        "title_height": _metricNumber(source, "title_height", layout.titleHeight),
        "title_left_margin": _metricNumber(source, "title_left_margin", layout.titleLeftMargin),
        "title_right_margin": _metricNumber(source, "title_right_margin", layout.titleRightMargin),
        "title_centered": _metricBool(source, "title_centered", layout.titleCentered),
        "body_left_margin": _metricNumber(source, "body_left_margin", layout.bodyLeftMargin),
        "body_right_margin": _metricNumber(source, "body_right_margin", layout.bodyRightMargin),
        "body_bottom_margin": bodyBottomMargin,
        "show_header_background": _metricBool(source, "show_header_background", false),
        "show_accent_bar": _metricBool(source, "show_accent_bar", false),
        "use_host_chrome": _metricBool(source, "use_host_chrome", true)
    };
}

function surfaceMetrics(node) {
    var source = node && node.surface_metrics ? node.surface_metrics : null;
    var family = String(node && node.surface_family || "standard");
    if (family === "flowchart")
        return _flowchartSurfaceMetrics(node, source);
    if (family === "planning")
        return _passivePanelSurfaceMetrics(node, source, _planningVariantLayout(node && node.surface_variant));
    if (family === "annotation")
        return _passivePanelSurfaceMetrics(node, source, _annotationVariantLayout(node && node.surface_variant));
    return _standardSurfaceMetrics(node, source);
}

function _flowchartHorizontalBounds(variant, width, height, localY) {
    if (!(width > 0.0) || !(height > 0.0))
        return {"left": 0.0, "right": Math.max(0.0, width)};
    var yValue = Math.max(0.0, Math.min(height, localY));
    if (variant === "start" || variant === "end") {
        var radius = Math.min(width * 0.5, height * 0.5);
        var cy = height * 0.5;
        var dy = Math.max(-radius, Math.min(radius, yValue - cy));
        var dx = Math.sqrt(Math.max(0.0, radius * radius - dy * dy));
        var left = radius - dx;
        return {"left": left, "right": width - left};
    }
    if (variant === "decision") {
        var leftDecision = Math.abs((height * 0.5) - yValue) * width / height;
        return {"left": leftDecision, "right": width - leftDecision};
    }
    if (variant === "connector") {
        var rx = width * 0.5;
        var ry = height * 0.5;
        var cyConnector = height * 0.5;
        var dyConnector = Math.max(-ry, Math.min(ry, yValue - cyConnector));
        if (!(ry > 0.0))
            return {"left": 0.0, "right": width};
        var factor = Math.sqrt(Math.max(0.0, 1.0 - (dyConnector * dyConnector) / (ry * ry)));
        var dxConnector = rx * factor;
        return {"left": rx - dxConnector, "right": rx + dxConnector};
    }
    if (variant === "input_output") {
        var slant = Math.min(width * 0.13, height * 0.26);
        var leftIo = Math.max(0.0, slant * (1.0 - (yValue / height)));
        return {"left": leftIo, "right": width - leftIo};
    }
    return {"left": 0.0, "right": width};
}

function localPortPoint(node, direction, rowIndex, widthOverride, heightOverride) {
    if (!node)
        return {"x": 0.0, "y": 0.0};
    var metrics = surfaceMetrics(node);
    var widthValue = _resolvedDimension(widthOverride !== undefined ? widthOverride : node.width, metrics.default_width);
    var heightValue = _resolvedDimension(heightOverride !== undefined ? heightOverride : node.height, metrics.default_height);
    if (node.collapsed) {
        return {
            "x": String(direction || "") === "in" ? 0.0 : widthValue,
            "y": metrics.collapsed_height * 0.5
        };
    }
    var localY = metrics.port_top + metrics.port_center_offset + metrics.port_height * Number(rowIndex);
    if (String(node.surface_family || "standard") === "flowchart") {
        var bounds = _flowchartHorizontalBounds(
            _normalizedFlowchartVariant(node.surface_variant),
            widthValue,
            heightValue,
            localY
        );
        return {
            "x": String(direction || "") === "in" ? bounds.left : bounds.right,
            "y": localY
        };
    }
    return {
        "x": String(direction || "") === "in"
            ? metrics.port_side_margin + metrics.port_dot_radius
            : widthValue - metrics.port_side_margin - metrics.port_dot_radius,
        "y": localY
    };
}

function portScenePoint(node, direction, rowIndex, widthOverride, heightOverride) {
    if (!node)
        return {"x": 0.0, "y": 0.0};
    var localPoint = localPortPoint(node, direction, rowIndex, widthOverride, heightOverride);
    return {
        "x": Number(node.x || 0.0) + localPoint.x,
        "y": Number(node.y || 0.0) + localPoint.y
    };
}

function portScenePointForPort(node, port, inputRow, outputRow, widthOverride, heightOverride) {
    if (!node || !port)
        return {"x": 0.0, "y": 0.0};
    var direction = String(port.direction || "");
    return portScenePoint(
        node,
        direction,
        direction === "in" ? inputRow : outputRow,
        widthOverride,
        heightOverride
    );
}
