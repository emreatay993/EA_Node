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
