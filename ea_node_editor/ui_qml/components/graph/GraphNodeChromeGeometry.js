.pragma library

// Purpose: Analytic rounded-card silhouettes with unioned circular port cutouts.
// Map: docs/agent_maps/subsystems/graph_canvas.md
// Tests: tests/test_graph_node_chrome_geometry.py
// Paths retain circular arcs. No flattening, pixel scale, zoom, or paint state is
// involved here; QML bindings rebuild only when the logical geometry changes.
// Settings-group animations rebuild every tick. Cards whose cutouts all sit on
// straight edges take a direct edge walk; other layouts use the general pass.

var TAU = Math.PI * 2;
var PARAM_EPS = 1e-9;

function finite(value, fallback) {
    var number = Number(value);
    return isFinite(number) ? number : fallback;
}

function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

function point(primitive, t) {
    if (primitive.kind === "line")
        return {x: primitive.x + primitive.dx * t, y: primitive.y + primitive.dy * t};
    var angle = primitive.start + primitive.sweep * t;
    return {x: primitive.x + primitive.radius * Math.cos(angle),
            y: primitive.y + primitive.radius * Math.sin(angle)};
}

function line(x, y, endX, endY) {
    return {kind: "line", x: x, y: y, dx: endX - x, dy: endY - y, cuts: [0, 1]};
}

function arc(x, y, radius, start, sweep) {
    return {kind: "arc", x: x, y: y, radius: radius, start: start, sweep: sweep, cuts: [0, 1]};
}

function normalized(width, height, radius, centers, holeRadius, inset) {
    width = finite(width, 0);
    height = finite(height, 0);
    inset = Math.max(0, finite(inset, 0));
    var box = {left: inset, top: inset, right: width - inset, bottom: height - inset};
    box.empty = width <= inset * 2 || height <= inset * 2;
    box.radius = Math.min(Math.max(0, finite(radius, 0) - inset),
                          Math.max(0, (width - inset * 2) / 2),
                          Math.max(0, (height - inset * 2) / 2));
    box.epsilon = Math.max(1, Math.abs(width), Math.abs(height)) * 1e-8;
    box.holes = [];
    var r = Math.max(0, finite(holeRadius, 9)) + inset;
    if (box.empty || r <= 0)
        return box;
    centers = centers || {};
    for (var side = 0; side < 2; ++side) {
        var x = side === 0 ? 0 : width;
        var values = centers[side === 0 ? "left" : "right"] || [];
        for (var i = 0; i < values.length; ++i) {
            var y = Number(values[i]);
            if (!isFinite(y) || y + r <= box.top || y - r >= box.bottom)
                continue;
            var duplicate = false;
            for (var h = 0; h < box.holes.length && !duplicate; ++h) {
                duplicate = Math.abs(box.holes[h].x - x) <= box.epsilon
                    && Math.abs(box.holes[h].y - y) <= box.epsilon;
            }
            if (!duplicate)
                box.holes.push({x: x, y: y, radius: r});
        }
    }
    return box;
}

function insideCard(box, p) {
    if (box.empty || p.x < box.left || p.x > box.right || p.y < box.top || p.y > box.bottom)
        return false;
    var cx = clamp(p.x, box.left + box.radius, box.right - box.radius);
    var cy = clamp(p.y, box.top + box.radius, box.bottom - box.radius);
    return (p.x - cx) * (p.x - cx) + (p.y - cy) * (p.y - cy)
        <= box.radius * box.radius + box.epsilon * box.epsilon;
}

function insideHole(hole, p, epsilon) {
    var dx = p.x - hole.x;
    var dy = p.y - hole.y;
    // Strict containment preserves a boundary at external tangencies.
    return dx * dx + dy * dy < hole.radius * hole.radius - epsilon * epsilon;
}

function insideOtherHole(holes, skip, p, epsilon) {
    for (var i = 0; i < holes.length; ++i) {
        // |dy| >= radius already rules out strict containment; skip the product.
        if (i !== skip && Math.abs(p.y - holes[i].y) < holes[i].radius
                && insideHole(holes[i], p, epsilon))
            return true;
    }
    return false;
}

function cardEdges(box) {
    var l = box.left, t = box.top, r = box.right, b = box.bottom, c = box.radius;
    if (c <= box.epsilon)
        return [line(l, t, r, t), line(r, t, r, b), line(r, b, l, b), line(l, b, l, t)];
    return [line(l + c, t, r - c, t), arc(r - c, t + c, c, -Math.PI / 2, Math.PI / 2),
            line(r, t + c, r, b - c), arc(r - c, b - c, c, 0, Math.PI / 2),
            line(r - c, b, l + c, b), arc(l + c, b - c, c, Math.PI / 2, Math.PI / 2),
            line(l, b - c, l, t + c), arc(l + c, t + c, c, Math.PI, Math.PI / 2)];
}

function parameter(primitive, p) {
    if (primitive.kind === "line") {
        var length2 = primitive.dx * primitive.dx + primitive.dy * primitive.dy;
        return length2 > 0 ? ((p.x - primitive.x) * primitive.dx + (p.y - primitive.y) * primitive.dy) / length2 : -1;
    }
    var angle = Math.atan2(p.y - primitive.y, p.x - primitive.x);
    var travel = primitive.sweep > 0 ? angle - primitive.start : primitive.start - angle;
    travel = ((travel % TAU) + TAU) % TAU;
    if (TAU - travel < PARAM_EPS)
        travel = 0;
    return travel / Math.abs(primitive.sweep);
}

function addIntersection(a, b, p) {
    var ta = parameter(a, p), tb = parameter(b, p);
    if (ta >= -PARAM_EPS && ta <= 1 + PARAM_EPS && tb >= -PARAM_EPS && tb <= 1 + PARAM_EPS) {
        a.cuts.push(clamp(ta, 0, 1));
        b.cuts.push(clamp(tb, 0, 1));
    }
}

// Only outer-to-hole and hole-to-hole pairs intersect. Outer edges already
// form a closed rounded rectangle, so line/line intersection is unnecessary.
function intersect(a, b, epsilon) {
    if (a.kind === "line") {
        var dx = a.x - b.x, dy = a.y - b.y;
        var aa = a.dx * a.dx + a.dy * a.dy;
        if (aa <= epsilon * epsilon)
            return;
        var bb = 2 * (dx * a.dx + dy * a.dy);
        var cc = dx * dx + dy * dy - b.radius * b.radius;
        var discriminant = bb * bb - 4 * aa * cc;
        if (discriminant < -epsilon * epsilon * aa)
            return;
        var root = Math.sqrt(Math.max(0, discriminant));
        addIntersection(a, b, point(a, (-bb - root) / (2 * aa)));
        addIntersection(a, b, point(a, (-bb + root) / (2 * aa)));
        return;
    }
    var x = b.x - a.x, y = b.y - a.y;
    var distance = Math.sqrt(x * x + y * y);
    if (distance <= epsilon || distance > a.radius + b.radius + epsilon
            || distance < Math.abs(a.radius - b.radius) - epsilon)
        return;
    var along = (a.radius * a.radius - b.radius * b.radius + distance * distance) / (2 * distance);
    var perpendicular = Math.sqrt(Math.max(0, a.radius * a.radius - along * along));
    var cx = a.x + x * along / distance, cy = a.y + y * along / distance;
    addIntersection(a, b, {x: cx - y * perpendicular / distance, y: cy + x * perpendicular / distance});
    addIntersection(a, b, {x: cx + y * perpendicular / distance, y: cy - x * perpendicular / distance});
}

function bounds(edge) {
    if (edge.kind === "line")
        return {left: Math.min(edge.x, edge.x + edge.dx), right: Math.max(edge.x, edge.x + edge.dx),
                top: Math.min(edge.y, edge.y + edge.dy), bottom: Math.max(edge.y, edge.y + edge.dy)};
    return {left: edge.x - edge.radius, right: edge.x + edge.radius,
            top: edge.y - edge.radius, bottom: edge.y + edge.radius};
}

function boundsOverlap(a, b, epsilon) {
    return a.left <= b.right + epsilon && b.left <= a.right + epsilon
        && a.top <= b.bottom + epsilon && b.top <= a.bottom + epsilon;
}

// In-place insertion sort; cut and center lists are short and nearly ordered.
function ascending(values) {
    for (var i = 1; i < values.length; ++i) {
        var value = values[i];
        var j = i - 1;
        for (; j >= 0 && values[j] > value; --j)
            values[j + 1] = values[j];
        values[j + 1] = value;
    }
    return values;
}

function uniqueCuts(cuts) {
    ascending(cuts);
    var unique = [];
    for (var k = 0; k < cuts.length; ++k) {
        if (k === 0 || cuts[k] - cuts[k - 1] > PARAM_EPS)
            unique.push(cuts[k]);
    }
    return unique;
}

function retainedSegments(box) {
    if (box.empty)
        return [];
    var outer = cardEdges(box);
    var edges = outer.slice();
    for (var h = 0; h < box.holes.length; ++h)
        edges.push(arc(box.holes[h].x, box.holes[h].y, box.holes[h].radius, 0, -TAU));
    var boxes = [];
    for (var b = 0; b < edges.length; ++b)
        boxes.push(bounds(edges[b]));
    for (var i = 0; i < edges.length; ++i) {
        for (var j = Math.max(i + 1, outer.length); j < edges.length; ++j) {
            if (boundsOverlap(boxes[i], boxes[j], box.epsilon))
                intersect(edges[i], edges[j], box.epsilon);
        }
    }
    var segments = [];
    for (var index = 0; index < edges.length; ++index) {
        var edge = edges[index];
        var ownHole = index - outer.length;
        var cuts = uniqueCuts(edge.cuts);
        for (var cut = 1; cut < cuts.length; ++cut) {
            var from = cuts[cut - 1], to = cuts[cut];
            var middle = point(edge, (from + to) / 2);
            if (ownHole >= 0 && !insideCard(box, middle))
                continue;
            if (insideOtherHole(box.holes, ownHole, middle, box.epsilon))
                continue;
            var start = point(edge, from), end = point(edge, to);
            var length = edge.kind === "arc" ? edge.radius * Math.abs(edge.sweep * (to - from))
                : Math.hypot(end.x - start.x, end.y - start.y);
            if (length > box.epsilon)
                segments.push({edge: edge, from: from, to: to, start: start, end: end});
        }
    }
    return segments;
}

function near(a, b, epsilon) {
    return Math.abs(a.x - b.x) <= epsilon && Math.abs(a.y - b.y) <= epsilon;
}

function number(value) {
    // Six decimal places remain well below a device pixel at supported zooms,
    // while keeping the retained SVG path compact and deterministic.
    return String(Math.round(value * 1e6) / 1e6);
}

function coordinate(p) {
    return number(p.x) + " " + number(p.y);
}

function segmentCommand(segment) {
    var edge = segment.edge;
    if (edge.kind === "line")
        return "L" + coordinate(segment.end);
    var sweep = edge.sweep * (segment.to - segment.from);
    if (Math.abs(sweep) >= TAU - PARAM_EPS) {
        var middle = point(edge, (segment.from + segment.to) / 2);
        var prefix = "A" + number(edge.radius) + " " + number(edge.radius) + " 0 0 " + (sweep > 0 ? "1 " : "0 ");
        return prefix + coordinate(middle) + prefix + coordinate(segment.end);
    }
    return "A" + number(edge.radius) + " " + number(edge.radius) + " 0 "
        + (Math.abs(sweep) > Math.PI ? "1 " : "0 ") + (sweep > 0 ? "1 " : "0 ") + coordinate(segment.end);
}

// Walks one vertical edge between its corner arcs: down the right edge or up the
// left one, with the card interior toward `interior` (+1 right, -1 left) of the
// hole centers. Cutouts whose chords on the edge overlap or touch leave the edge
// and meet at their interior intersection instead.
function edgeWalk(centers, edgeX, holeX, interior, radius, chord, inset, downward, bandStart, bandEnd, epsilon) {
    var path = "";
    var arcPrefix = "A" + number(radius) + " " + number(radius) + " 0 0 0 ";
    var current = bandStart;
    var joined = false;
    var count = centers.length;
    for (var n = 0; n < count; ++n) {
        var y = centers[downward ? n : count - 1 - n];
        if (!joined) {
            var entry = downward ? y - chord : y + chord;
            if (Math.abs(entry - current) > epsilon)
                path += "L" + number(edgeX) + " " + number(entry);
        }
        var gap = n + 1 < count ? Math.abs(centers[downward ? n + 1 : count - 2 - n] - y) : Infinity;
        joined = gap <= chord * 2;
        if (joined) {
            // Equal circles centered on one vertical line meet on their bisector.
            var reach = Math.max(inset, Math.sqrt(Math.max(0, radius * radius - gap * gap / 4)));
            current = downward ? y + gap / 2 : y - gap / 2;
            path += arcPrefix + number(holeX + interior * reach) + " " + number(current);
        } else {
            current = downward ? y + chord : y - chord;
            path += arcPrefix + number(edgeX) + " " + number(current);
        }
    }
    if (Math.abs(bandEnd - current) > epsilon)
        path += "L" + number(edgeX) + " " + number(bandEnd);
    return path;
}

// Most cards keep every cutout on the straight part of a vertical edge, with left
// and right cutouts too far apart to meet. Such a silhouette is one clockwise walk:
// no pairwise intersections, containment tests, or segment chaining. Returns null
// for every other layout, which the general pass below handles.
function edgeWalkSilhouette(box) {
    if (box.empty)
        return "";
    var epsilon = box.epsilon;
    var c = box.radius > epsilon ? box.radius : 0;
    var bandTop = box.top + c, bandBottom = box.bottom - c;
    var inset = box.left;
    var width = box.right + inset;
    var left = [], right = [];
    var radius = box.holes.length ? box.holes[0].radius : 0;
    for (var i = 0; i < box.holes.length; ++i) {
        var hole = box.holes[i];
        // A cutout reaching a corner arc or a horizontal edge needs the general pass.
        if (hole.y - radius <= bandTop + epsilon || hole.y + radius >= bandBottom - epsilon)
            return null;
        (hole.x === 0 ? left : right).push(hole.y);
    }
    // Also general: tangent (chordless) cutouts, cutouts reaching the opposite
    // edge, and left/right cutouts that can meet inside the card.
    var chord = Math.sqrt(Math.max(0, radius * radius - inset * inset));
    if (box.holes.length && (chord <= epsilon || radius >= box.right - epsilon
            || (left.length && right.length && radius * 2 >= width - epsilon)))
        return null;
    ascending(left);
    ascending(right);
    var path = "M" + number(box.left + c) + " " + number(box.top);
    if (box.right - box.left - 2 * c > epsilon)
        path += "L" + number(box.right - c) + " " + number(box.top);
    var corner = "A" + number(c) + " " + number(c) + " 0 0 1 ";
    if (c)
        path += corner + number(box.right) + " " + number(bandTop);
    path += edgeWalk(right, box.right, width, -1, radius, chord, inset, true, bandTop, bandBottom, epsilon);
    if (c)
        path += corner + number(box.right - c) + " " + number(box.bottom);
    if (box.right - box.left - 2 * c > epsilon)
        path += "L" + number(box.left + c) + " " + number(box.bottom);
    if (c)
        path += corner + number(box.left) + " " + number(bandBottom);
    path += edgeWalk(left, box.left, 0, 1, radius, chord, inset, false, bandBottom, bandTop, epsilon);
    if (c)
        path += corner + number(box.left + c) + " " + number(box.top);
    return path + "Z";
}

function silhouette(box) {
    var walked = edgeWalkSilhouette(box);
    if (walked !== null)
        return walked;
    var segments = retainedSegments(box);
    var used = [];
    var paths = [];
    // Each contour starts at the first unused segment and always continues with
    // the first unused segment, in retained order, that starts at its end.
    for (var first = 0; first < segments.length; ++first) {
        if (used[first])
            continue;
        used[first] = true;
        var segment = segments[first];
        var start = segment.start;
        var path = "M" + coordinate(start) + segmentCommand(segment);
        var end = segment.end;
        while (!near(end, start, box.epsilon)) {
            // Every segment before `first` is already part of an earlier contour.
            var next = first + 1;
            while (next < segments.length && (used[next] || !near(segments[next].start, end, box.epsilon)))
                ++next;
            // Every retained boundary has a successor. Do not silently close a
            // broken chain with a straight edge through the card.
            if (next >= segments.length)
                throw new Error("Unclosed node silhouette at " + coordinate(end));
            used[next] = true;
            segment = segments[next];
            path += segmentCommand(segment);
            end = segment.end;
        }
        paths.push(path + "Z");
    }
    return paths.join(" ");
}

function build(width, height, radius, borderWidth, centers, holeRadius) {
    var outer = normalized(width, height, radius, centers, holeRadius, 0);
    var fill = silhouette(outer);
    var border = Math.max(0, finite(borderWidth, 0));
    var inner = border > 0 ? silhouette(normalized(width, height, radius, centers, holeRadius, border)) : fill;
    return {fillPath: fill, borderPath: border > 0 && fill ? fill + (inner ? " " + inner : "") : ""};
}

// Clip each diagonal analytically against the same silhouette. A retained
// stroked path replaces the former Canvas texture and masked hatch layer.
function hatch(width, height, radius, centers, holeRadius, spacing) {
    // Erode by half the one-pixel stroke so its coverage, including the flat
    // endpoints, stays inside the silhouette rather than bleeding into holes.
    var box = normalized(width, height, radius, centers, holeRadius, 0.5);
    if (box.empty)
        return "";
    spacing = Math.max(1, finite(spacing, 8)) * Math.SQRT2;
    var boundaries = cardEdges(box).concat(box.holes.map(function(hole) {
        return arc(hole.x, hole.y, hole.radius, 0, -TAU);
    }));
    var paths = [];
    // Lines x+y=constant slope down-left, matching the old 45-degree hatch.
    for (var sum = spacing / 2; sum < width + height; sum += spacing) {
        var diagonal = line(0, sum, width, sum - width);
        // Line/line crossings with straight rounded-card edges.
        boundaries.forEach(function(edge) {
            if (edge.kind === "arc") {
                intersect(diagonal, edge, box.epsilon);
            } else {
                var denominator = edge.dx + edge.dy;
                if (Math.abs(denominator) > box.epsilon) {
                    var t = (sum - edge.x - edge.y) / denominator;
                    if (t >= 0 && t <= 1)
                        diagonal.cuts.push(clamp((edge.x + edge.dx * t) / width, 0, 1));
                }
            }
        });
        var cuts = uniqueCuts(diagonal.cuts);
        for (var i = 1; i < cuts.length; ++i) {
            var middle = point(diagonal, (cuts[i - 1] + cuts[i]) / 2);
            if (insideCard(box, middle) && !box.holes.some(function(hole) { return insideHole(hole, middle, box.epsilon); }))
                paths.push("M" + coordinate(point(diagonal, cuts[i - 1])) + "L" + coordinate(point(diagonal, cuts[i])));
        }
    }
    return paths.join(" ");
}
