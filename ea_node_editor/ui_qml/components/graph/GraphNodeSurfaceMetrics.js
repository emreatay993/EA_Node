.pragma library

function _metricNumber(source, key, fallback) {
    var value = source ? Number(source[key]) : NaN;
    if (!isFinite(value))
        value = fallback;
    return value;
}

function inlineBodyHeight(node) {
    var inlineProperties = node && node.inline_properties ? node.inline_properties : [];
    var count = inlineProperties.length;
    if (count <= 0)
        return 0.0;
    return 8.0 + count * 26.0 + Math.max(0, count - 1) * 4.0;
}

function surfaceMetrics(node) {
    var source = node && node.surface_metrics ? node.surface_metrics : {};
    var bodyHeight = _metricNumber(source, "body_height", inlineBodyHeight(node));
    return {
        "default_width": _metricNumber(source, "default_width", 210.0),
        "default_height": _metricNumber(source, "default_height", 50.0),
        "min_width": _metricNumber(source, "min_width", 120.0),
        "min_height": _metricNumber(source, "min_height", 50.0),
        "collapsed_width": _metricNumber(source, "collapsed_width", 130.0),
        "collapsed_height": _metricNumber(source, "collapsed_height", 36.0),
        "header_height": _metricNumber(source, "header_height", 24.0),
        "header_top_margin": _metricNumber(source, "header_top_margin", 4.0),
        "body_top": _metricNumber(source, "body_top", 30.0),
        "body_height": bodyHeight,
        "port_top": _metricNumber(source, "port_top", 30.0 + bodyHeight),
        "port_height": _metricNumber(source, "port_height", 18.0),
        "port_center_offset": _metricNumber(source, "port_center_offset", 6.0),
        "port_side_margin": _metricNumber(source, "port_side_margin", 8.0),
        "port_dot_radius": _metricNumber(source, "port_dot_radius", 3.5),
        "resize_handle_size": _metricNumber(source, "resize_handle_size", 16.0)
    };
}

function portScenePoint(node, direction, rowIndex) {
    if (!node)
        return {"x": 0.0, "y": 0.0};
    var metrics = surfaceMetrics(node);
    var widthValue = Number(node.width);
    if (!isFinite(widthValue) || widthValue <= 0.0)
        widthValue = metrics.default_width;
    if (node.collapsed) {
        return {
            "x": direction === "in" ? Number(node.x) : (Number(node.x) + widthValue),
            "y": Number(node.y) + metrics.collapsed_height * 0.5
        };
    }
    return {
        "x": direction === "in"
            ? Number(node.x) + metrics.port_side_margin + metrics.port_dot_radius
            : Number(node.x) + widthValue - metrics.port_side_margin - metrics.port_dot_radius,
        "y": Number(node.y) + metrics.port_top + metrics.port_center_offset + metrics.port_height * Number(rowIndex)
    };
}

function portScenePointForPort(node, port, inputRow, outputRow) {
    if (!node || !port)
        return {"x": 0.0, "y": 0.0};
    return portScenePoint(
        node,
        String(port.direction || ""),
        String(port.direction || "") === "in" ? inputRow : outputRow
    );
}

