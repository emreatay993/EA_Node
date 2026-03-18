.pragma library
.import "GraphNodeSurfaceMetricContract.js" as SurfaceMetricContract

function _contract() {
    return SurfaceMetricContract.contract();
}

function _contractSection(key) {
    var value = _contract()[key];
    return value && typeof value === "object" ? value : {};
}

function _contractNumber(source, key) {
    var value = source ? Number(source[key]) : NaN;
    return isFinite(value) ? value : NaN;
}

function _metricNumber(source, key, fallback) {
    var value = source ? Number(source[key]) : NaN;
    if (!isFinite(value))
        value = fallback;
    return isFinite(value) ? value : 0.0;
}

function _metricBool(source, key, fallback) {
    if (!source || source[key] === undefined)
        return Boolean(fallback);
    return Boolean(source[key]);
}

function _inlineContract() {
    return _contractSection("inline");
}

function _standardContract() {
    return _contractSection("standard");
}

function _passiveContract() {
    return _contractSection("passive");
}

function _flowchartContract() {
    return _contractSection("flowchart");
}

function _planningContract() {
    return _contractSection("planning");
}

function _annotationContract() {
    return _contractSection("annotation");
}

function _mediaContract() {
    return _contractSection("media");
}

function _variantLayouts(section) {
    var layouts = section ? section.variants : null;
    return layouts && typeof layouts === "object" ? layouts : {};
}

function _normalizedVariant(value, layouts, fallback) {
    var variant = String(value || "").trim().toLowerCase();
    return layouts && layouts[variant] !== undefined ? variant : fallback;
}

function inlineBodyHeight(node) {
    var inlineProperties = node && node.inline_properties ? node.inline_properties : [];
    var count = inlineProperties.length;
    if (count <= 0)
        return 0.0;
    var inlineContract = _inlineContract();
    var rowHeight = _contractNumber(inlineContract, "row_height");
    var textareaRowHeight = _contractNumber(inlineContract, "textarea_row_height");
    var rowSpacing = _contractNumber(inlineContract, "row_spacing");
    var sectionPadding = _contractNumber(inlineContract, "section_padding");
    var totalRowHeight = 0.0;
    for (var i = 0; i < inlineProperties.length; i++) {
        var propertyItem = inlineProperties[i];
        totalRowHeight += String(propertyItem && propertyItem.inline_editor || "").toLowerCase() === "textarea"
            ? textareaRowHeight
            : rowHeight;
    }
    return sectionPadding + totalRowHeight + Math.max(0, count - 1) * rowSpacing;
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

function _flowchartVariantLayout(variant) {
    var contract = _flowchartContract();
    var layouts = _variantLayouts(contract);
    var normalized = _normalizedVariant(variant, layouts, "process");
    var layout = layouts[normalized];
    return layout && typeof layout === "object" ? layout : {};
}

function _planningVariantLayout(variant) {
    var contract = _planningContract();
    var layouts = _variantLayouts(contract);
    var normalized = _normalizedVariant(variant, layouts, "task_card");
    var layout = layouts[normalized];
    return layout && typeof layout === "object" ? layout : {};
}

function _annotationVariantLayout(variant) {
    var contract = _annotationContract();
    var layouts = _variantLayouts(contract);
    var normalized = _normalizedVariant(variant, layouts, "sticky_note");
    var layout = layouts[normalized];
    return layout && typeof layout === "object" ? layout : {};
}

function _mediaVariantLayout(variant) {
    var contract = _mediaContract();
    var layouts = _variantLayouts(contract);
    var normalized = _normalizedVariant(variant, layouts, "image_panel");
    var layout = layouts[normalized];
    return layout && typeof layout === "object" ? layout : {};
}

function _resolvedDimension(value, fallback) {
    var numeric = Number(value);
    if (!(numeric > 0.0))
        numeric = fallback;
    return isFinite(numeric) ? numeric : 0.0;
}

function _standardSurfaceMetrics(node, source) {
    var standard = _standardContract();
    var portCount = _visiblePortCounts(node).portCount;
    var headerHeight = _contractNumber(standard, "header_height");
    var portHeight = _contractNumber(standard, "port_height");
    var bottomPadding = _contractNumber(standard, "bottom_padding");
    var bodyTop = _contractNumber(standard, "body_top");
    var bodyHeight = _metricNumber(source, "body_height", inlineBodyHeight(node));
    return {
        "default_width": _metricNumber(source, "default_width", _contractNumber(standard, "default_width")),
        "default_height": _metricNumber(
            source,
            "default_height",
            headerHeight + bodyHeight + portCount * portHeight + bottomPadding
        ),
        "min_width": _metricNumber(source, "min_width", _contractNumber(standard, "min_width")),
        "min_height": _metricNumber(source, "min_height", _contractNumber(standard, "min_height")),
        "collapsed_width": _metricNumber(source, "collapsed_width", _contractNumber(standard, "collapsed_width")),
        "collapsed_height": _metricNumber(source, "collapsed_height", _contractNumber(standard, "collapsed_height")),
        "header_height": _metricNumber(source, "header_height", headerHeight),
        "header_top_margin": _metricNumber(source, "header_top_margin", _contractNumber(standard, "header_top_margin")),
        "body_top": _metricNumber(source, "body_top", bodyTop),
        "body_height": bodyHeight,
        "port_top": _metricNumber(source, "port_top", bodyTop + bodyHeight),
        "port_height": _metricNumber(source, "port_height", portHeight),
        "port_center_offset": _metricNumber(
            source,
            "port_center_offset",
            _contractNumber(standard, "port_center_offset")
        ),
        "port_side_margin": _metricNumber(source, "port_side_margin", _contractNumber(standard, "port_side_margin")),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", _contractNumber(standard, "port_dot_radius")),
        "resize_handle_size": _metricNumber(
            source,
            "resize_handle_size",
            _contractNumber(standard, "resize_handle_size")
        ),
        "title_top": _metricNumber(source, "title_top", _contractNumber(standard, "header_top_margin")),
        "title_height": _metricNumber(source, "title_height", headerHeight),
        "title_left_margin": _metricNumber(
            source,
            "title_left_margin",
            _contractNumber(standard, "title_left_margin")
        ),
        "title_right_margin": _metricNumber(
            source,
            "title_right_margin",
            _contractNumber(standard, "title_right_margin")
        ),
        "title_centered": _metricBool(source, "title_centered", false),
        "body_left_margin": _metricNumber(
            source,
            "body_left_margin",
            _contractNumber(standard, "body_left_margin")
        ),
        "body_right_margin": _metricNumber(
            source,
            "body_right_margin",
            _contractNumber(standard, "body_right_margin")
        ),
        "body_bottom_margin": _metricNumber(source, "body_bottom_margin", bottomPadding),
        "show_header_background": _metricBool(
            source,
            "show_header_background",
            Boolean(standard.show_header_background)
        ),
        "show_accent_bar": _metricBool(source, "show_accent_bar", Boolean(standard.show_accent_bar)),
        "use_host_chrome": _metricBool(source, "use_host_chrome", Boolean(standard.use_host_chrome))
    };
}

function _flowchartSurfaceMetrics(node, source) {
    var contract = _flowchartContract();
    var layout = _flowchartVariantLayout(node && node.surface_variant);
    var portCount = _visiblePortCounts(node).portCount;
    var bodyHeight = _metricNumber(source, "body_height", inlineBodyHeight(node));
    var titleHeight = _contractNumber(contract, "title_height");
    var portHeight = _contractNumber(contract, "port_height");
    var inlineGap = _contractNumber(contract, "inline_gap");
    var defaultPortSectionTop = _contractNumber(contract, "port_section_top");
    var basePortSectionTop = bodyHeight > 0.0
        ? _contractNumber(layout, "title_top") + titleHeight + inlineGap + bodyHeight + inlineGap
        : defaultPortSectionTop;
    var defaultHeight = Math.max(
        _contractNumber(layout, "min_height"),
        basePortSectionTop + portCount * portHeight + _contractNumber(layout, "body_bottom_margin")
    );
    var defaultWidth = _contractNumber(layout, "default_width");
    var minWidth = _contractNumber(layout, "min_width");
    if (Boolean(layout.square)) {
        defaultWidth = Math.max(defaultWidth, defaultHeight);
        minWidth = Math.max(minWidth, _contractNumber(layout, "min_height"));
    }
    defaultHeight = _metricNumber(source, "default_height", defaultHeight);
    defaultWidth = _metricNumber(source, "default_width", defaultWidth);
    minWidth = _metricNumber(source, "min_width", minWidth);
    var minHeight = _metricNumber(source, "min_height", _contractNumber(layout, "min_height"));
    var activeHeight = _resolvedDimension(node && node.height, defaultHeight);
    var titleTop = bodyHeight > 0.0
        ? _contractNumber(layout, "title_top")
        : Math.max(12.0, (activeHeight - titleHeight) * 0.5);
    titleTop = _metricNumber(source, "title_top", titleTop);
    var bodyTop = _metricNumber(source, "body_top", titleTop + titleHeight + inlineGap);
    var portSectionTop = bodyHeight > 0.0
        ? bodyTop + bodyHeight + inlineGap
        : defaultPortSectionTop;
    var availablePortHeight = Math.max(
        portCount * portHeight,
        activeHeight - portSectionTop - _contractNumber(layout, "body_bottom_margin")
    );
    return {
        "default_width": defaultWidth,
        "default_height": defaultHeight,
        "min_width": minWidth,
        "min_height": minHeight,
        "collapsed_width": _metricNumber(source, "collapsed_width", _contractNumber(contract, "collapsed_width")),
        "collapsed_height": _metricNumber(source, "collapsed_height", _contractNumber(contract, "collapsed_height")),
        "header_height": _metricNumber(source, "header_height", 0.0),
        "header_top_margin": _metricNumber(source, "header_top_margin", 0.0),
        "body_top": bodyTop,
        "body_height": bodyHeight,
        "port_top": _metricNumber(
            source,
            "port_top",
            portSectionTop + Math.max(0.0, (availablePortHeight - portCount * portHeight) * 0.5)
        ),
        "port_height": _metricNumber(source, "port_height", portHeight),
        "port_center_offset": _metricNumber(
            source,
            "port_center_offset",
            _contractNumber(contract, "port_center_offset")
        ),
        "port_side_margin": _metricNumber(source, "port_side_margin", 0.0),
        "port_dot_radius": _metricNumber(
            source,
            "port_dot_radius",
            _contractNumber(contract, "port_dot_radius")
        ),
        "resize_handle_size": _metricNumber(
            source,
            "resize_handle_size",
            _contractNumber(contract, "resize_handle_size")
        ),
        "title_top": titleTop,
        "title_height": _metricNumber(source, "title_height", titleHeight),
        "title_left_margin": _metricNumber(
            source,
            "title_left_margin",
            _contractNumber(layout, "title_left_margin")
        ),
        "title_right_margin": _metricNumber(
            source,
            "title_right_margin",
            _contractNumber(layout, "title_right_margin")
        ),
        "title_centered": _metricBool(source, "title_centered", true),
        "body_left_margin": _metricNumber(
            source,
            "body_left_margin",
            _contractNumber(layout, "body_left_margin")
        ),
        "body_right_margin": _metricNumber(
            source,
            "body_right_margin",
            _contractNumber(layout, "body_right_margin")
        ),
        "body_bottom_margin": _metricNumber(
            source,
            "body_bottom_margin",
            _contractNumber(layout, "body_bottom_margin")
        ),
        "show_header_background": _metricBool(source, "show_header_background", false),
        "show_accent_bar": _metricBool(source, "show_accent_bar", false),
        "use_host_chrome": _metricBool(source, "use_host_chrome", false)
    };
}

function _passivePanelSurfaceMetrics(node, source, layout) {
    var passive = _passiveContract();
    var activeHeight = _resolvedDimension(node && node.height, _contractNumber(layout, "default_height"));
    var bodyTop = _metricNumber(source, "body_top", _contractNumber(layout, "body_top"));
    var bodyBottomMargin = _metricNumber(source, "body_bottom_margin", _contractNumber(layout, "body_bottom_margin"));
    var bodyHeight = _metricNumber(
        source,
        "body_height",
        Math.max(_contractNumber(layout, "body_height"), activeHeight - bodyTop - bodyBottomMargin)
    );
    return {
        "default_width": _metricNumber(source, "default_width", _contractNumber(layout, "default_width")),
        "default_height": _metricNumber(source, "default_height", _contractNumber(layout, "default_height")),
        "min_width": _metricNumber(source, "min_width", _contractNumber(layout, "min_width")),
        "min_height": _metricNumber(source, "min_height", _contractNumber(layout, "min_height")),
        "collapsed_width": _metricNumber(source, "collapsed_width", _contractNumber(_standardContract(), "collapsed_width")),
        "collapsed_height": _metricNumber(
            source,
            "collapsed_height",
            _contractNumber(_standardContract(), "collapsed_height")
        ),
        "header_height": _metricNumber(source, "header_height", 0.0),
        "header_top_margin": _metricNumber(source, "header_top_margin", 0.0),
        "body_top": bodyTop,
        "body_height": bodyHeight,
        "port_top": _metricNumber(source, "port_top", activeHeight - bodyBottomMargin),
        "port_height": _metricNumber(source, "port_height", 0.0),
        "port_center_offset": _metricNumber(source, "port_center_offset", 0.0),
        "port_side_margin": _metricNumber(source, "port_side_margin", _contractNumber(passive, "port_side_margin")),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", _contractNumber(passive, "port_dot_radius")),
        "resize_handle_size": _metricNumber(
            source,
            "resize_handle_size",
            _contractNumber(passive, "resize_handle_size")
        ),
        "title_top": _metricNumber(source, "title_top", _contractNumber(layout, "title_top")),
        "title_height": _metricNumber(source, "title_height", _contractNumber(layout, "title_height")),
        "title_left_margin": _metricNumber(
            source,
            "title_left_margin",
            _contractNumber(layout, "title_left_margin")
        ),
        "title_right_margin": _metricNumber(
            source,
            "title_right_margin",
            _contractNumber(layout, "title_right_margin")
        ),
        "title_centered": _metricBool(source, "title_centered", Boolean(layout.title_centered)),
        "body_left_margin": _metricNumber(
            source,
            "body_left_margin",
            _contractNumber(layout, "body_left_margin")
        ),
        "body_right_margin": _metricNumber(
            source,
            "body_right_margin",
            _contractNumber(layout, "body_right_margin")
        ),
        "body_bottom_margin": bodyBottomMargin,
        "show_header_background": _metricBool(source, "show_header_background", false),
        "show_accent_bar": _metricBool(source, "show_accent_bar", false),
        "use_host_chrome": _metricBool(source, "use_host_chrome", true)
    };
}

function _mediaSurfaceMetrics(node, source) {
    var layout = _mediaVariantLayout(node && node.surface_variant);
    var passive = _passiveContract();
    var activeHeight = _resolvedDimension(node && node.height, _contractNumber(layout, "default_height"));
    var bodyTop = _metricNumber(source, "body_top", _contractNumber(layout, "body_top"));
    var bodyBottomMargin = _metricNumber(source, "body_bottom_margin", _contractNumber(layout, "body_bottom_margin"));
    var bodyHeight = _metricNumber(
        source,
        "body_height",
        Math.max(_contractNumber(layout, "min_body_height"), activeHeight - bodyTop - bodyBottomMargin)
    );
    return {
        "default_width": _metricNumber(source, "default_width", _contractNumber(layout, "default_width")),
        "default_height": _metricNumber(source, "default_height", _contractNumber(layout, "default_height")),
        "min_width": _metricNumber(source, "min_width", _contractNumber(layout, "min_width")),
        "min_height": _metricNumber(source, "min_height", _contractNumber(layout, "min_height")),
        "collapsed_width": _metricNumber(source, "collapsed_width", _contractNumber(_standardContract(), "collapsed_width")),
        "collapsed_height": _metricNumber(
            source,
            "collapsed_height",
            _contractNumber(_standardContract(), "collapsed_height")
        ),
        "header_height": _metricNumber(source, "header_height", 0.0),
        "header_top_margin": _metricNumber(source, "header_top_margin", 0.0),
        "body_top": bodyTop,
        "body_height": bodyHeight,
        "port_top": _metricNumber(source, "port_top", activeHeight - bodyBottomMargin),
        "port_height": _metricNumber(source, "port_height", 0.0),
        "port_center_offset": _metricNumber(source, "port_center_offset", 0.0),
        "port_side_margin": _metricNumber(source, "port_side_margin", _contractNumber(passive, "port_side_margin")),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", _contractNumber(passive, "port_dot_radius")),
        "resize_handle_size": _metricNumber(
            source,
            "resize_handle_size",
            _contractNumber(passive, "resize_handle_size")
        ),
        "title_top": _metricNumber(source, "title_top", _contractNumber(layout, "title_top")),
        "title_height": _metricNumber(source, "title_height", _contractNumber(layout, "title_height")),
        "title_left_margin": _metricNumber(
            source,
            "title_left_margin",
            _contractNumber(layout, "title_left_margin")
        ),
        "title_right_margin": _metricNumber(
            source,
            "title_right_margin",
            _contractNumber(layout, "title_right_margin")
        ),
        "title_centered": _metricBool(source, "title_centered", Boolean(layout.title_centered)),
        "body_left_margin": _metricNumber(
            source,
            "body_left_margin",
            _contractNumber(layout, "body_left_margin")
        ),
        "body_right_margin": _metricNumber(
            source,
            "body_right_margin",
            _contractNumber(layout, "body_right_margin")
        ),
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
    if (family === "media")
        return _mediaSurfaceMetrics(node, source);
    return _standardSurfaceMetrics(node, source);
}

function _normalizedFlowchartVariant(value) {
    return _normalizedVariant(value, _variantLayouts(_flowchartContract()), "process");
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
