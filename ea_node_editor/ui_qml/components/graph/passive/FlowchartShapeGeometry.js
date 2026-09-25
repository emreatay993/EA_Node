.pragma library

// Purpose: Shared flowchart silhouette parameters, the shape-aware body text regions, and the grow-to-fit searches.
// Map: feature_routes/passive_surface_loading_contracts
// Tests: tests/qml_quick/tst_graph_node_host.qml

// Gap between the text and the outline on the edges a shape limits itself.
var TEXT_REGION_PADDING = 6.0;
// Largest rectangle inside a diamond: half of each axis.
var DIAMOND_INSCRIBED_FRACTION = 0.5;
// Largest rectangle inside an ellipse: 1/sqrt(2) of each axis.
var ELLIPSE_INSCRIBED_FRACTION = Math.SQRT1_2;
var BELOW_SHAPE_BAND_FRACTION = 0.28;
var GROW_TO_FIT_MAX_EXTENT = 8000.0;

function _number(value, fallback) {
    var numeric = Number(value);
    return isFinite(numeric) ? numeric : fallback;
}

function outlineBounds(width, height, strokeWidth) {
    var inset = Math.max(0.5, _number(strokeWidth, 1.0) * 0.5);
    var left = inset;
    var top = inset;
    var right = Math.max(left + 1.0, _number(width, 0.0) - inset);
    var bottom = Math.max(top + 1.0, _number(height, 0.0) - inset);
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "widthValue": Math.max(1.0, right - left),
        "heightValue": Math.max(1.0, bottom - top),
        "centerX": (left + right) * 0.5,
        "centerY": (top + bottom) * 0.5
    };
}

function terminatorRadius(bounds) {
    return Math.min(bounds.heightValue * 0.5, bounds.widthValue * 0.5);
}

function documentWaveDepth(bounds, strokeWidth) {
    return Math.min(bounds.heightValue * 0.11, 10.0 + _number(strokeWidth, 1.0) * 1.5);
}

// The wave's upper control points sit on this line, so the curve stays below it.
function documentWaveCrestY(bounds, strokeWidth) {
    return bounds.bottom - documentWaveDepth(bounds, strokeWidth) * 1.08;
}

function inputOutputSlant(bounds) {
    return Math.min(bounds.widthValue * 0.13, bounds.heightValue * 0.26);
}

function databaseCapHeight(bounds, strokeWidth) {
    return Math.min(bounds.heightValue * 0.13, 14.0 + _number(strokeWidth, 1.0));
}

function calloutTailWidth(bounds, strokeWidth) {
    return Math.min(bounds.widthValue * 0.18, 24.0 + _number(strokeWidth, 1.0) * 2.0);
}

function calloutTailHeight(bounds, strokeWidth) {
    return Math.min(bounds.heightValue * 0.3, 30.0 + _number(strokeWidth, 1.0) * 2.0);
}

// The multi-document pages are drawn on an 88 x 60.28 unit grid.
function multiDocumentScaleX(bounds) {
    return bounds.widthValue / 88.0;
}

function multiDocumentScaleY(bounds) {
    return bounds.heightValue / 60.28;
}

function _rect(x, y, width, height) {
    return {
        "x": x,
        "y": y,
        "width": Math.max(0.0, width),
        "height": Math.max(0.0, height)
    };
}

function _edgesRect(left, top, right, bottom) {
    return _rect(left, top, right - left, bottom - top);
}

// Body text rectangle in surface coordinates for a contract `body_text_placement`.
// `margins` carries the variant's contract insets ({left, right, vertical}); the
// shape-aware placements replace them on the axes the outline itself limits.
function bodyTextRegion(variant, placement, width, height, strokeWidth, margins) {
    var w = Math.max(0.0, _number(width, 0.0));
    var h = Math.max(0.0, _number(height, 0.0));
    var source = margins || {};
    var marginLeft = _number(source.left, 18.0);
    var marginRight = _number(source.right, 18.0);
    var inset = _number(source.vertical, 16.0);
    var padding = TEXT_REGION_PADDING;
    var key = String(placement || "center").trim().toLowerCase();
    var b = outlineBounds(w, h, strokeWidth);

    if (key === "inscribed_diamond" || key === "inscribed_ellipse") {
        var fraction = key === "inscribed_diamond" ? DIAMOND_INSCRIBED_FRACTION : ELLIPSE_INSCRIBED_FRACTION;
        var innerWidth = b.widthValue * fraction;
        var innerHeight = b.heightValue * fraction;
        return _rect(
            b.centerX - innerWidth * 0.5 + padding,
            b.centerY - innerHeight * 0.5 + padding,
            innerWidth - 2.0 * padding,
            innerHeight - 2.0 * padding
        );
    }
    if (key === "between_slants") {
        var slant = inputOutputSlant(b);
        return _edgesRect(b.left + slant + padding, inset, b.right - slant - padding, h - inset);
    }
    if (key === "above_wave")
        return _edgesRect(marginLeft, b.top + padding, w - marginRight, documentWaveCrestY(b, strokeWidth) - padding);
    if (key === "between_caps") {
        // Below the lid ellipse and above where the side walls meet the bottom arc.
        var cap = databaseCapHeight(b, strokeWidth);
        return _edgesRect(marginLeft, b.top + 2.0 * cap + padding, w - marginRight, b.bottom - cap - padding);
    }
    if (key === "above_tail")
        return _edgesRect(marginLeft, b.top + padding, w - marginRight, b.bottom - calloutTailHeight(b, strokeWidth) - padding);
    if (key === "between_end_caps") {
        // Pull the sides in until the text band's corners clear the round end caps.
        var radius = terminatorRadius(b);
        var halfBand = Math.min(radius, Math.max(0.0, h * 0.5 - inset));
        var capInset = b.left + radius - Math.sqrt(Math.max(0.0, radius * radius - halfBand * halfBand)) + padding;
        return _edgesRect(Math.max(marginLeft, capInset), inset, w - Math.max(marginRight, capInset), h - inset);
    }
    if (key === "front_page") {
        // Front sheet only: left of the stacked sheets, below their top edges, above its wave.
        var pageScaleX = multiDocumentScaleX(b);
        var pageScaleY = multiDocumentScaleY(b);
        var waveRise = 50.0 - Math.sqrt(50.0 * 50.0 - 19.5 * 19.5);
        return _edgesRect(
            b.left + padding,
            b.top + 10.0 * pageScaleY + padding,
            b.left + 78.0 * pageScaleX - padding,
            b.top + (55.0 - waveRise) * pageScaleY - padding
        );
    }

    var tickBelowShape = key === "below_shape" && String(variant || "").trim().toLowerCase() === "tick";
    var shiftX = tickBelowShape ? -w * 0.08 : 0.0;
    var shiftY = tickBelowShape ? h * 0.05 : 0.0;
    if (key === "below_shape") {
        return _rect(
            marginLeft + shiftX,
            h * (1.0 - BELOW_SHAPE_BAND_FRACTION) + shiftY,
            w - marginLeft - marginRight,
            h * BELOW_SHAPE_BAND_FRACTION - inset
        );
    }
    if (key === "front_face") {
        var isometricCubeOffset = Math.min(w * 0.24, h * 0.5);
        var frontFaceHeight = Math.max(16.0, Math.min(h * 0.32, h - 2.0 * isometricCubeOffset - 2.0 * inset));
        return _rect(
            w * 0.05,
            Math.max(0.0, (h + isometricCubeOffset) * 0.5 - frontFaceHeight * 0.5),
            w * 0.4,
            frontFaceHeight
        );
    }
    if (key === "cube_front_face") {
        var cubeDepth = Math.min(w * 0.2, h * 0.2);
        var cubeFaceWidth = Math.max(0.0, w - cubeDepth - marginLeft - marginRight);
        var cubeFaceHeight = Math.max(16.0, Math.min(h * 0.5, h - cubeDepth - 2.0 * inset));
        return _rect(
            Math.max(marginLeft, (w - cubeDepth) * 0.5 - cubeFaceWidth * 0.5),
            Math.max(inset, (h + cubeDepth) * 0.5 - cubeFaceHeight * 0.5),
            cubeFaceWidth,
            cubeFaceHeight
        );
    }
    return _rect(marginLeft, inset, w - marginLeft - marginRight, h - 2.0 * inset);
}

// Smallest height >= baseHeight at which fitsAt(width, height) holds; null when
// the base size already fits or nothing up to maxExtent does.
function growHeightToFit(fitsAt, baseWidth, baseHeight, maxExtent) {
    var width = Math.max(1.0, _number(baseWidth, 1.0));
    var low = Math.max(1.0, _number(baseHeight, 1.0));
    var cap = Math.max(low, _number(maxExtent, GROW_TO_FIT_MAX_EXTENT));
    if (fitsAt(width, low))
        return null;
    var high = low;
    while (high < cap) {
        high = Math.min(cap, Math.max(high * 2.0, high + 16.0));
        if (fitsAt(width, high))
            break;
        low = high;
    }
    if (!fitsAt(width, high))
        return null;
    while (high - low > 0.5) {
        var middle = (low + high) * 0.5;
        if (fitsAt(width, middle))
            high = middle;
        else
            low = middle;
    }
    return {"width": width, "height": Math.ceil(high)};
}

// Smallest uniform scale >= 1 at which the node fits, keeping its aspect ratio;
// null when the base size already fits or nothing up to maxExtent does.
function growScaleToFit(fitsAt, baseWidth, baseHeight, maxExtent) {
    var width = Math.max(1.0, _number(baseWidth, 1.0));
    var height = Math.max(1.0, _number(baseHeight, 1.0));
    var cap = Math.max(1.0, _number(maxExtent, GROW_TO_FIT_MAX_EXTENT) / Math.max(width, height));
    if (fitsAt(width, height))
        return null;
    var low = 1.0;
    var high = 1.0;
    while (high < cap) {
        high = Math.min(cap, high * 2.0);
        if (fitsAt(width * high, height * high))
            break;
        low = high;
    }
    if (!fitsAt(width * high, height * high))
        return null;
    var tolerance = 0.5 / Math.max(width, height);
    while (high - low > tolerance) {
        var middle = (low + high) * 0.5;
        if (fitsAt(width * middle, height * middle))
            high = middle;
        else
            low = middle;
    }
    return {"width": Math.ceil(width * high), "height": Math.ceil(height * high)};
}
