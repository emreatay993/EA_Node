.pragma library

function clamp(value, minValue, maxValue) {
    return Math.max(minValue, Math.min(maxValue, value));
}

function distanceSegment(px, py, x1, y1, x2, y2) {
    var dx = x2 - x1;
    var dy = y2 - y1;
    var lengthSq = dx * dx + dy * dy;
    if (lengthSq <= 1e-9) {
        var ddx = px - x1;
        var ddy = py - y1;
        return Math.sqrt(ddx * ddx + ddy * ddy);
    }
    var t = ((px - x1) * dx + (py - y1) * dy) / lengthSq;
    t = clamp(t, 0.0, 1.0);
    var closestX = x1 + t * dx;
    var closestY = y1 + t * dy;
    var ddx2 = px - closestX;
    var ddy2 = py - closestY;
    return Math.sqrt(ddx2 * ddx2 + ddy2 * ddy2);
}

function cubicPoint(t, p0, p1, p2, p3) {
    var inv = 1.0 - t;
    var a = inv * inv * inv;
    var b = 3.0 * inv * inv * t;
    var c = 3.0 * inv * t * t;
    var d = t * t * t;
    return a * p0 + b * p1 + c * p2 + d * p3;
}

function distanceBezier(px, py, x0, y0, x1, y1, x2, y2, x3, y3, segments) {
    var sampleCount = Math.max(12, segments || 20);
    var prevX = x0;
    var prevY = y0;
    var minDistance = distanceSegment(px, py, prevX, prevY, prevX, prevY);
    for (var i = 1; i <= sampleCount; i++) {
        var t = i / sampleCount;
        var curX = cubicPoint(t, x0, x1, x2, x3);
        var curY = cubicPoint(t, y0, y1, y2, y3);
        minDistance = Math.min(minDistance, distanceSegment(px, py, prevX, prevY, curX, curY));
        prevX = curX;
        prevY = curY;
    }
    return minDistance;
}

function distancePolyline(px, py, points) {
    if (!points || points.length === 0)
        return Number.POSITIVE_INFINITY;
    if (points.length === 1)
        return distanceSegment(px, py, points[0].x, points[0].y, points[0].x, points[0].y);
    var minDistance = Number.POSITIVE_INFINITY;
    for (var i = 1; i < points.length; i++) {
        var a = points[i - 1];
        var b = points[i];
        minDistance = Math.min(minDistance, distanceSegment(px, py, a.x, a.y, b.x, b.y));
    }
    return minDistance;
}

function _vectorAngleDegrees(dx, dy) {
    return Math.atan2(dy, dx) * 180.0 / Math.PI;
}

function _normalizeVector(dx, dy) {
    var length = Math.sqrt(dx * dx + dy * dy);
    if (length <= 1e-9)
        return {"dx": 1.0, "dy": 0.0};
    return {"dx": dx / length, "dy": dy / length};
}

function cubicDerivative(t, p0, p1, p2, p3) {
    var inv = 1.0 - t;
    return 3.0 * inv * inv * (p1 - p0)
        + 6.0 * inv * t * (p2 - p1)
        + 3.0 * t * t * (p3 - p2);
}

function bezierPointTangent(t, x0, y0, x1, y1, x2, y2, x3, y3) {
    var px = cubicPoint(t, x0, x1, x2, x3);
    var py = cubicPoint(t, y0, y1, y2, y3);
    var dx = cubicDerivative(t, x0, x1, x2, x3);
    var dy = cubicDerivative(t, y0, y1, y2, y3);
    var normalized = _normalizeVector(dx, dy);
    return {
        "x": px,
        "y": py,
        "dx": normalized.dx,
        "dy": normalized.dy,
        "angle": _vectorAngleDegrees(normalized.dx, normalized.dy)
    };
}

function pointTangentAlongBezier(x0, y0, x1, y1, x2, y2, x3, y3, fraction, segments) {
    var sampleCount = Math.max(16, segments || 32);
    var clampedFraction = clamp(fraction, 0.0, 1.0);
    var samples = [];
    var totalLength = 0.0;
    var prev = bezierPointTangent(0.0, x0, y0, x1, y1, x2, y2, x3, y3);
    samples.push({"t": 0.0, "point": prev, "length": 0.0});
    for (var i = 1; i <= sampleCount; i++) {
        var t = i / sampleCount;
        var point = bezierPointTangent(t, x0, y0, x1, y1, x2, y2, x3, y3);
        totalLength += Math.sqrt(Math.pow(point.x - prev.x, 2) + Math.pow(point.y - prev.y, 2));
        samples.push({"t": t, "point": point, "length": totalLength});
        prev = point;
    }
    if (totalLength <= 1e-9)
        return samples[samples.length - 1].point;
    var targetLength = totalLength * clampedFraction;
    for (var index = 1; index < samples.length; index++) {
        var current = samples[index];
        if (current.length + 1e-9 < targetLength)
            continue;
        var previous = samples[index - 1];
        var span = current.length - previous.length;
        if (span <= 1e-9)
            return current.point;
        var localFraction = (targetLength - previous.length) / span;
        var interpolatedT = previous.t + (current.t - previous.t) * localFraction;
        return bezierPointTangent(interpolatedT, x0, y0, x1, y1, x2, y2, x3, y3);
    }
    return samples[samples.length - 1].point;
}

function pointTangentAlongPolyline(points, fraction) {
    if (!points || points.length === 0)
        return null;
    if (points.length === 1)
        return {"x": points[0].x, "y": points[0].y, "dx": 1.0, "dy": 0.0, "angle": 0.0};
    var segments = [];
    var totalLength = 0.0;
    for (var i = 1; i < points.length; i++) {
        var a = points[i - 1];
        var b = points[i];
        var dx = b.x - a.x;
        var dy = b.y - a.y;
        var length = Math.sqrt(dx * dx + dy * dy);
        segments.push({"a": a, "b": b, "dx": dx, "dy": dy, "length": length});
        totalLength += length;
    }
    if (totalLength <= 1e-9) {
        var lastPoint = points[points.length - 1];
        return {"x": lastPoint.x, "y": lastPoint.y, "dx": 1.0, "dy": 0.0, "angle": 0.0};
    }
    var clampedFraction = clamp(fraction, 0.0, 1.0);
    var targetLength = totalLength * clampedFraction;
    var traversed = 0.0;
    for (var index = 0; index < segments.length; index++) {
        var segment = segments[index];
        var nextLength = traversed + segment.length;
        if (segment.length <= 1e-9) {
            traversed = nextLength;
            continue;
        }
        if (targetLength - nextLength > 1e-9) {
            traversed = nextLength;
            continue;
        }
        var segmentFraction = (targetLength - traversed) / segment.length;
        var normalized = _normalizeVector(segment.dx, segment.dy);
        return {
            "x": segment.a.x + segment.dx * segmentFraction,
            "y": segment.a.y + segment.dy * segmentFraction,
            "dx": normalized.dx,
            "dy": normalized.dy,
            "angle": _vectorAngleDegrees(normalized.dx, normalized.dy)
        };
    }
    var tail = segments[segments.length - 1];
    var tailNormalized = _normalizeVector(tail.dx, tail.dy);
    return {
        "x": tail.b.x,
        "y": tail.b.y,
        "dx": tailNormalized.dx,
        "dy": tailNormalized.dy,
        "angle": _vectorAngleDegrees(tailNormalized.dx, tailNormalized.dy)
    };
}
