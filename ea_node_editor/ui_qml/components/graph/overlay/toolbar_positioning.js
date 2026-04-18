.pragma library

function _number(value, fallback) {
    var numeric = Number(value);
    if (isFinite(numeric))
        return numeric;
    return Number(fallback) || 0;
}

function _rect(value) {
    var source = value || {};
    return {
        x: _number(source.x, 0),
        y: _number(source.y, 0),
        width: Math.max(0, _number(source.width, 0)),
        height: Math.max(0, _number(source.height, 0))
    };
}

function _size(value) {
    var source = value || {};
    return {
        width: Math.max(0, _number(source.width, 0)),
        height: Math.max(0, _number(source.height, 0))
    };
}

function computeAnchor(nodeRect, toolbarSize, viewportRect, metrics, previousFlipped) {
    var node = _rect(nodeRect);
    var size = _size(toolbarSize);
    var viewport = _rect(viewportRect);
    var options = metrics || {};
    var gap = Math.max(0, _number(options.gap_from_node, 6));
    var safety = Math.max(0, _number(options.safety_margin, 8));
    var hysteresis = Math.max(0, _number(options.hysteresis, 8));

    var topY = node.y - size.height - gap;
    var bottomY = node.y + node.height + gap;

    var viewportValid = viewport.width > 0 && viewport.height > 0;
    var flipped = false;
    if (viewportValid) {
        var minTop = viewport.y + safety;
        if (previousFlipped) {
            flipped = topY < minTop + hysteresis;
        } else {
            flipped = topY < minTop;
        }
    }

    var anchorY = flipped ? bottomY : topY;
    var centerX = node.x + node.width / 2 - size.width / 2;

    var anchorX = centerX;
    if (viewportValid) {
        var minX = viewport.x + safety;
        var maxX = viewport.x + viewport.width - safety - size.width;
        if (maxX < minX)
            maxX = minX;
        anchorX = Math.max(minX, Math.min(maxX, centerX));
    }

    return {
        x: anchorX,
        y: anchorY,
        flipped: flipped
    };
}
