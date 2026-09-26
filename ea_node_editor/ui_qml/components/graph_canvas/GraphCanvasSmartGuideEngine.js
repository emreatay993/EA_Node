.pragma library

// Purpose: Smart-guide snaps, guide lines and gap markers for node drag and resize.
// Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
// Tests: tests/test_graph_canvas_smart_guide_engine.py
// Landmarks: buildIndex; sortedBand; rowAround (skyline sweep); spacingSnap; gapMarkers; resolveMove; resolveResize
// Pure JS with no Qt objects; every rect is in scene coordinates.
// Complexity: buildIndex sorts the candidates once per gesture, O(n log n). Per axis it keeps each
// rect's edges by rect id, the sorted edge values (left+right, top+bottom), the sorted centre values
// and the rects ordered by their low edge. Band queries use per-extent windows: rects grouped by
// extent in powers of two, each sorted by low edge, so one tall Group backdrop only widens its own
// window. A resolve call binary-searches those arrays (O(log n) per window) and then works only on
// the matches and the band beside the moving rect (k rects): at most O(k log k) to order the band,
// plus a sweep over the band's skyline (at most 2k + 1 segments). The sweep finds the segment under
// each band rect's span start by walking a short skyline from its start, or past WALK_SEGMENTS
// segments in a bitmap of the segment starts (a few word reads), and then visits every segment under
// that span, whether the rect raises it or not. That is O(k) visits for rows and columns, whose rects
// raise what they cover, but O(k^2) at worst: thin rows reaching far with full-height slivers inside
// them make every sliver visit every row's segment. So equal spacing is left out on an axis whose band
// holds more than SPACING_BAND_LIMIT rects: that axis gets no spacing snap and no gap markers in that
// call, and alignment is unaffected. Measured in QV4, that comb costs about 5 ms a call at the limit
// (20 ms at 512 band rects, 200 ms at 1600), and grids of nodes about 0.3 ms at the limit. No call
// scans all n candidates.
// Every skyline search and edit step counts against the segments the skyline holds, which no correct
// sweep exceeds. A sweep that runs out anyway (a corrupt skyline or bitmap) stops, reports no spacing
// on its axis and clears the bitmap, so such a bug costs gap markers, never a hung UI thread.
// Equal spacing only counts what can be seen. Two band rects form a gap when they overlap on the
// cross axis and nothing else in the band, the moving rect included, lies between them over that
// overlap. The moving rect's neighbours follow the same rule. A band rect that holds the moving rect
// (a Group backdrop it is dragged inside) is left out of spacing, so it hides none of its members; it
// still gives alignment lines. Both axes snap from the input offset, then lines and gap markers are
// measured again at the final offset. A spacing snap that no guide there shows falls back to the
// axis' alignment snap, or to no snap.

var LINE_TOLERANCE = 0.5;
var MAX_LINES_PER_AXIS = 3;
var MAX_GAPS_PER_AXIS = 6;
// Band windows start one unit early so rounding in the stored extents never drops a rect.
var BAND_SLACK = 1.0;
// Min-size checks forgive float rounding in an aspect-derived edge.
var SIZE_EPSILON = 1e-6;
// Skyline owners that are not band positions.
var NO_OWNER = -1;
var MOVING_OWNER = -2;
// Up to this many skyline segments, a sweep walks the skyline to find the segment under a span start.
var WALK_SEGMENTS = 16;
// An axis whose band holds more rects than this gets no equal spacing (see the header): at the limit,
// the worst band measured 5 ms a call, and the cost grows with the square of the band.
var SPACING_BAND_LIMIT = 256;

var AXIS_X = {name: "x", cross: "y", lo: "left", hi: "right", crossLo: "top", crossHi: "bottom"};
var AXIS_Y = {name: "y", cross: "x", lo: "top", hi: "bottom", crossLo: "left", crossHi: "right"};
var AXES = [AXIS_X, AXIS_Y];

function finite(value) {
    if (value === null || value === undefined || value === "")
        return NaN;
    var number = Number(value);
    return isFinite(number) ? number : NaN;
}

// {node_id, x, y, width, height} -> {node_id, left, top, right, bottom}, or null when not a real rect.
function sceneRect(entry) {
    if (!entry)
        return null;
    var x = finite(entry.x);
    var y = finite(entry.y);
    var width = finite(entry.width);
    var height = finite(entry.height);
    if (!(isFinite(x) && isFinite(y) && width > 0 && height > 0))
        return null;
    var right = x + width;
    var bottom = y + height;
    if (!(isFinite(right) && isFinite(bottom)))
        return null;
    var nodeId = entry.node_id === undefined || entry.node_id === null ? "" : String(entry.node_id);
    return {node_id: nodeId, left: x, top: y, right: right, bottom: bottom};
}

// {left, top, right, bottom} with positive size, or null.
function boxRect(value) {
    if (!value)
        return null;
    var left = finite(value.left);
    var top = finite(value.top);
    var right = finite(value.right);
    var bottom = finite(value.bottom);
    if (!(right > left && bottom > top))
        return null;
    return {left: left, top: top, right: right, bottom: bottom};
}

function translated(rect, dx, dy) {
    return {left: rect.left + dx, top: rect.top + dy, right: rect.right + dx, bottom: rect.bottom + dy};
}

// First index whose value is >= target.
function lowerBound(values, target) {
    var low = 0;
    var high = values.length;
    while (low < high) {
        var mid = (low + high) >> 1;
        if (values[mid] < target)
            low = mid + 1;
        else
            high = mid;
    }
    return low;
}

function compareNumbers(a, b) {
    return a - b;
}

// Entries {value, rect} -> parallel sorted arrays; ties keep rect order.
function sortedEntries(entries) {
    entries.sort(function(a, b) { return a.value - b.value || a.rect - b.rect; });
    var values = new Array(entries.length);
    var rects = new Array(entries.length);
    for (var i = 0; i < entries.length; ++i) {
        values[i] = entries[i].value;
        rects[i] = entries[i].rect;
    }
    return {values: values, rects: rects};
}

// Band-query windows: rects grouped by extent in powers of two, each sorted by low edge and carrying
// its largest extent, so a query windows each group by that group's own extent.
function extentWindows(lo, hi) {
    var groups = {};
    var keys = [];
    for (var i = 0; i < lo.length; ++i) {
        var extent = hi[i] - lo[i];
        var key = Math.floor(Math.log(extent) / Math.LN2);
        if (groups[key] === undefined) {
            groups[key] = {entries: [], maxExtent: 0};
            keys.push(key);
        }
        groups[key].entries.push({value: lo[i], rect: i});
        groups[key].maxExtent = Math.max(groups[key].maxExtent, extent);
    }
    keys.sort(compareNumbers);
    var windows = [];
    for (var k = 0; k < keys.length; ++k) {
        var sorted = sortedEntries(groups[keys[k]].entries);
        windows.push({values: sorted.values, rects: sorted.rects, maxExtent: groups[keys[k]].maxExtent});
    }
    return windows;
}

// Per-axis arrays by rect id (lo, hi, their slots, rank in the low-edge ordering), the sorted orderings,
// and the band-query windows over this axis.
function axisIndex(rects, axis) {
    var count = rects.length;
    var lo = new Array(count);
    var hi = new Array(count);
    var edgeEntries = [];
    var centres = [];
    var lowEntries = [];
    for (var i = 0; i < count; ++i) {
        lo[i] = rects[i][axis.lo];
        hi[i] = rects[i][axis.hi];
        edgeEntries.push({value: lo[i], rect: i});
        edgeEntries.push({value: hi[i], rect: i});
        centres.push({value: (lo[i] + hi[i]) / 2, rect: i});
        lowEntries.push({value: lo[i], rect: i});
    }
    var edges = sortedEntries(edgeEntries);
    // An edge's slot is 1 + the index of the first sorted edge of its value, so slots order edges like
    // their values and equal values share one. Slots 0 and 2 * count + 1 stay free for the two ends of a
    // sweep's interval, which every edge swept inside it lies between.
    var loSlot = new Array(count);
    var hiSlot = new Array(count);
    for (var s = 0; s < count; ++s) {
        loSlot[s] = lowerBound(edges.values, lo[s]) + 1;
        hiSlot[s] = lowerBound(edges.values, hi[s]) + 1;
    }
    var lows = sortedEntries(lowEntries);
    var rank = new Array(count);
    for (var r = 0; r < count; ++r)
        rank[lows.rects[r]] = r;
    return {
        lo: lo,
        hi: hi,
        loSlot: loSlot,
        hiSlot: hiSlot,
        rank: rank,
        edges: edges,
        centres: sortedEntries(centres),
        lows: lows,
        windows: extentWindows(lo, hi)
    };
}

function zeroes(count) {
    var values = new Array(count);
    for (var i = 0; i < count; ++i)
        values[i] = 0;
    return values;
}

// Marks over `slots` slots in levels of 32-bit words: level 0 marks slots, and each level above marks
// the words of the level below that hold a mark. There are at least two levels; the top one is a word.
function slotMarks(slots) {
    var levels = [];
    var size = slots;
    do {
        size = (size + 31) >> 5;
        levels.push(zeroes(size));
    } while (size > 1 || levels.length < 2);
    return levels;
}

// Marks `position` of `level` (a slot at level 0, a word of the level below above it) and, when its
// word held no mark yet, that word in the levels above.
function mark(levels, level, position) {
    for (; level < levels.length; ++level) {
        var words = levels[level];
        var at = position >> 5;
        var bits = words[at];
        words[at] = bits | (1 << (position & 31));
        if (bits !== 0)
            return;
        position = at;
    }
}

// Clears `position` of `level` and, when its word holds no mark any more, that word in the levels above.
function unmark(levels, level, position) {
    for (; level < levels.length; ++level) {
        var words = levels[level];
        var at = position >> 5;
        var bits = words[at] & ~(1 << (position & 31));
        words[at] = bits;
        if (bits !== 0)
            return;
        position = at;
    }
}

function clearMarks(levels) {
    for (var level = 0; level < levels.length; ++level) {
        var words = levels[level];
        for (var i = 0; i < words.length; ++i)
            words[i] = 0;
    }
}

// The highest marked slot at or below `position` of `level`, or -1: climb until a word holds a mark at or
// below the position, then descend through the highest mark of each word.
function markAtOrBelow(levels, level, position) {
    for (;;) {
        if (position < 0 || level === levels.length)
            return -1;
        var bits = levels[level][position >> 5] & (-1 >>> (31 - (position & 31)));
        if (bits !== 0) {
            position = (position & ~31) + 31 - Math.clz32(bits);
            break;
        }
        position = (position >> 5) - 1;
        ++level;
    }
    while (level > 0) {
        --level;
        position = (position << 5) + 31 - Math.clz32(levels[level][position]);
    }
    return position;
}

// Candidate rects {node_id, x, y, width, height} -> opaque index; entries with non-finite values or
// no area are ignored. Geometry lives in per-axis arrays, and each resolve call reuses the scratch
// rows and skyline buffers, so a drag frame allocates little for the garbage collector to chase.
function buildIndex(rects) {
    var items = [];
    var source = rects || [];
    for (var i = 0; i < source.length; ++i) {
        var rect = sceneRect(source[i]);
        if (rect !== null)
            items.push(rect);
    }
    var count = items.length;
    var nodeIds = new Array(count);
    for (var j = 0; j < count; ++j)
        nodeIds[j] = items[j].node_id;
    // A skyline segment is keyed by the slot of its start (see axisIndex).
    var slots = 2 * count + 2;
    // A sweep of k band rects records at most 3k gaps: each gap is an empty rectangle between the two
    // rects it joins and no two of them overlap, so the gaps form a planar graph on the rects. Only
    // bands of up to SPACING_BAND_LIMIT rects are swept (a caller that lifts the limit may grow these).
    var gaps = 3 * Math.min(count, SPACING_BAND_LIMIT);
    return {
        count: count,
        nodeIds: nodeIds,
        x: axisIndex(items, AXIS_X),
        y: axisIndex(items, AXIS_Y),
        scratch: {
            rankMarks: zeroes(count),
            bandIds: {x: zeroes(count), y: zeroes(count)},
            ids: zeroes(count),
            lows: zeroes(count),
            highs: zeroes(count),
            spanLows: zeroes(count),
            spanHighs: zeroes(count),
            gapFirst: zeroes(gaps),
            gapSecond: zeroes(gaps),
            segmentStarts: zeroes(slots),
            segmentOwners: zeroes(slots),
            segmentReaches: zeroes(slots),
            segmentNext: zeroes(slots),
            marks: slotMarks(slots)
        }
    };
}

// {left, top, right, bottom} around {x, y, width, height} rects, or null when none is a real rect.
function unionRect(rects) {
    var union = null;
    var source = rects || [];
    for (var i = 0; i < source.length; ++i) {
        var rect = sceneRect(source[i]);
        if (rect === null)
            continue;
        if (union === null) {
            union = {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
            continue;
        }
        union.left = Math.min(union.left, rect.left);
        union.top = Math.min(union.top, rect.top);
        union.right = Math.max(union.right, rect.right);
        union.bottom = Math.max(union.bottom, rect.bottom);
    }
    return union;
}

function indexHasRects(index) {
    return Boolean(index && index.count > 0 && index.scratch);
}

// The sorted value nearest `feature` within threshold as {delta, value}; ties keep the lower value.
function nearestValue(values, feature, threshold) {
    var at = lowerBound(values, feature);
    var best = null;
    if (at > 0 && feature - values[at - 1] <= threshold)
        best = {delta: values[at - 1] - feature, value: values[at - 1]};
    if (at < values.length && values[at] - feature <= threshold
            && (best === null || values[at] - feature < -best.delta))
        best = {delta: values[at] - feature, value: values[at]};
    return best;
}

// The value nearest `feature` within threshold that `accept` takes, as {delta, value}, or null. Values
// are tried nearest first, and ties try the lower value first.
function nearestAccepted(values, feature, threshold, accept) {
    var above = lowerBound(values, feature);
    var below = above - 1;
    for (;;) {
        var belowOk = below >= 0 && feature - values[below] <= threshold;
        var aboveOk = above < values.length && values[above] - feature <= threshold;
        if (!belowOk && !aboveOk)
            return null;
        var takeBelow = belowOk && (!aboveOk || feature - values[below] <= values[above] - feature);
        var value = takeBelow ? values[below] : values[above];
        if (accept(value))
            return {delta: value - feature, value: value};
        if (takeBelow)
            --below;
        else
            ++above;
    }
}

// The snap with the smaller |delta|; ties keep `best`.
function closer(best, candidate) {
    if (candidate === null)
        return best;
    if (best === null || Math.abs(candidate.delta) < Math.abs(best.delta))
        return candidate;
    return best;
}

// Moving edges pair with candidate edges, the moving centre with candidate centres.
function alignmentSnap(axisIdx, lo, hi, threshold) {
    var best = nearestValue(axisIdx.edges.values, lo, threshold);
    best = closer(best, nearestValue(axisIdx.edges.values, hi, threshold));
    return closer(best, nearestValue(axisIdx.centres.values, (lo + hi) / 2, threshold));
}

// Writes the ids of the candidates overlapping (crossLo, crossHi) on the cross axis by a positive
// length to index.scratch.bandIds[axis.name], in the axis' low-edge order, and returns their count. They
// are found through their ranks in that order. Ranks that lie close together (a band spanning most of
// the layout) are read back in order from marks, in time linear in their range; others are sorted,
// where every comparison calls back into JS. Valid until the next sortedBand on the same axis.
function sortedBand(index, axis, crossLo, crossHi) {
    var crossIdx = index[axis.cross];
    var axisIdx = index[axis.name];
    var crossHighs = crossIdx.hi;
    var rank = axisIdx.rank;
    var windows = crossIdx.windows;
    var ranks = index.scratch.bandIds[axis.name];
    var count = 0;
    var lowest = Infinity;
    var highest = -Infinity;
    for (var w = 0; w < windows.length; ++w) {
        var window = windows[w];
        var start = lowerBound(window.values, crossLo - window.maxExtent - BAND_SLACK);
        var end = lowerBound(window.values, crossHi);
        for (var i = start; i < end; ++i) {
            var id = window.rects[i];
            if (crossHighs[id] > crossLo) {
                var value = rank[id];
                ranks[count++] = value;
                if (value < lowest)
                    lowest = value;
                if (value > highest)
                    highest = value;
            }
        }
    }
    var byRank = axisIdx.lows.rects;
    if (highest - lowest < 8 * count) {
        var marked = index.scratch.rankMarks;
        for (var m = 0; m < count; ++m)
            marked[ranks[m]] = 1;
        var at = 0;
        for (var r = lowest; r <= highest; ++r) {
            if (marked[r] === 1) {
                marked[r] = 0;
                ranks[at++] = byRank[r];
            }
        }
        return count;
    }
    // Entries past `count` belong to an earlier band: cut them off, as sort takes the whole array.
    ranks.length = count;
    ranks.sort(compareNumbers);
    for (var j = 0; j < count; ++j)
        ranks[j] = byRank[ranks[j]];
    return count;
}

// Writes the ids of the candidates `rect` overlaps on the cross axis, in order along `axis`, to
// scratch.ids and returns their count. A resolve call sorts one band per axis, widened by `reach`, so a
// later position within reach only filters it.
function bandAround(index, axis, rect, reach, cache) {
    var crossLo = rect[axis.crossLo];
    var crossHi = rect[axis.crossHi];
    var wide = cache[axis.name];
    if (!wide || crossLo < wide.crossLo || crossHi > wide.crossHi) {
        wide = {crossLo: crossLo - reach, crossHi: crossHi + reach, count: 0};
        wide.count = sortedBand(index, axis, wide.crossLo, wide.crossHi);
        cache[axis.name] = wide;
    }
    var crossIdx = index[axis.cross];
    var crossLows = crossIdx.lo;
    var crossHighs = crossIdx.hi;
    var source = index.scratch.bandIds[axis.name];
    var ids = index.scratch.ids;
    var count = 0;
    for (var i = 0; i < wide.count; ++i) {
        var id = source[i];
        if (crossHighs[id] > crossLo && crossLows[id] < crossHi)
            ids[count++] = id;
    }
    return count;
}

// The band beside `rect` along `axis` (the candidates overlapping its cross interval), swept in order
// along the axis over a skyline of that interval: at each cross position, the rect reaching furthest
// so far. Each item (a band rect, or the moving rect before the first band rect starting at or after
// it) first looks back at the skyline owners over its cross span, clipped to the rect's. It sees an
// owner only where the owner holds all of the span they share, so nothing lies between them there.
// Then it raises the skyline to its far edge wherever it reaches further. The moving rect also wins
// ties, so a band rect ending exactly where it ends never hides it. Band rects that hold
// cache.inside (the rect a resolve call starts from), or `rect` without it, edges included, are left
// out: a Group backdrop the moving rect is dragged inside would hide all of its members.
// Fills index.scratch by position in the band left: ids, lows, highs, and spanLows/spanHighs (the
// clipped cross spans). Returns {before, after, gapCount}: the band positions of the nearest
// neighbours (allowing `slack` of overlap) or -1, and the number of gaps wider than `tolerance` in
// scratch.gapFirst and gapSecond. Valid until the next rowAround on the same index. A band of more
// than SPACING_BAND_LIMIT rects, or a sweep that finds its skyline corrupt, gives no neighbours and no
// gaps. This is the drag's innermost loop, so the sweep keeps its state in locals and edits the
// skyline in place, visiting only the segments under each item's span.
function rowAround(index, axis, rect, slack, tolerance, cache) {
    var count = bandAround(index, axis, rect, slack, cache);
    if (count > SPACING_BAND_LIMIT)
        return {before: -1, after: -1, gapCount: 0};
    var scratch = index.scratch;
    var ids = scratch.ids;
    var lows = scratch.lows;
    var highs = scratch.highs;
    var spanLows = scratch.spanLows;
    var spanHighs = scratch.spanHighs;
    var gapFirst = scratch.gapFirst;
    var gapSecond = scratch.gapSecond;
    var axisIdx = index[axis.name];
    var crossIdx = index[axis.cross];
    var axisLows = axisIdx.lo;
    var axisHighs = axisIdx.hi;
    var crossLows = crossIdx.lo;
    var crossHighs = crossIdx.hi;
    var crossLowSlots = crossIdx.loSlot;
    var crossHighSlots = crossIdx.hiSlot;
    var crossLo = rect[axis.crossLo];
    var crossHi = rect[axis.crossHi];
    var movingLo = rect[axis.lo];
    var movingHi = rect[axis.hi];
    var inside = cache.inside || rect;
    var insideLo = inside[axis.lo];
    var insideHi = inside[axis.hi];
    var insideCrossLo = inside[axis.crossLo];
    var insideCrossHi = inside[axis.crossHi];
    var kept = 0;
    for (var i = 0; i < count; ++i) {
        var id = ids[i];
        var low = axisLows[id];
        var high = axisHighs[id];
        var crossLow = crossLows[id];
        var crossHigh = crossHighs[id];
        if (low <= insideLo && high >= insideHi && crossLow <= insideCrossLo && crossHigh >= insideCrossHi)
            continue;
        ids[kept] = id;
        lows[kept] = low;
        highs[kept] = high;
        spanLows[kept] = crossLow > crossLo ? crossLow : crossLo;
        spanHighs[kept] = crossHigh < crossHi ? crossHigh : crossHi;
        ++kept;
    }
    count = kept;
    var before = -1;
    var beforeReach = -Infinity;
    var after = -1;
    var gapCount = 0;
    // An interval that rounding closed holds no span, so nothing in it sees anything.
    if (!(crossLo < crossHi))
        return {before: before, after: after, gapCount: gapCount};
    // The skyline, as segments keyed by the slot of their start: segment c covers
    // [starts[c], starts[next[c]]) and belongs to owners[c], reaching reaches[c]. The first starts at
    // slot 0 (crossLo) and slotHi (crossHi) closes the last; a span edge inside the interval is keyed by
    // its edge slot. `marks` holds the start slots, so the segment under a value starts at the highest
    // mark at or below the value's slot. Adjacent segments never share an owner.
    var starts = scratch.segmentStarts;
    var owners = scratch.segmentOwners;
    var reaches = scratch.segmentReaches;
    var next = scratch.segmentNext;
    var slotHi = starts.length - 1;
    var marks = scratch.marks;
    var level0 = marks[0];
    var level1 = marks[1];
    starts[0] = crossLo;
    owners[0] = NO_OWNER;
    reaches[0] = -Infinity;
    next[0] = slotHi;
    starts[slotHi] = crossHi;
    // A short skyline is searched by walking it. Once it grows past WALK_SEGMENTS segments, the sweep
    // marks every segment start and then searches and updates the marks instead. Every sweep leaves the
    // marks clear.
    var segments = 1;
    var marked = false;
    // False once the skyline or its marks prove corrupt (an engine bug): see the end of the sweep.
    var intact = true;
    var nextPosition = 0;
    var nextLo = count > 0 ? lows[0] : Infinity;
    var movingSwept = false;
    sweep:
    for (var step = 0; step <= count; ++step) {
        var moving = !movingSwept && nextLo >= movingLo;
        var item;
        var itemLo;
        var itemHi;
        var spanLo;
        var spanHi;
        if (moving) {
            item = MOVING_OWNER;
            itemLo = movingLo;
            itemHi = movingHi;
            spanLo = crossLo;
            spanHi = crossHi;
            movingSwept = true;
        } else {
            item = nextPosition++;
            itemLo = nextLo;
            nextLo = nextPosition < count ? lows[nextPosition] : Infinity;
            itemHi = highs[item];
            spanLo = spanLows[item];
            spanHi = spanHighs[item];
            // A span with no length touches nothing; the searches below rely on spans inside the interval.
            if (!(spanLo < spanHi))
                continue;
        }
        // The segment under spanLo: the first one when the span starts with the interval, else the last
        // one starting at or before spanLo. With marks, that one starts at the highest mark at or below
        // the slot of spanLo, in that slot's word or in the nearest word below that holds a mark. This
        // and the mark updates below inline the two lowest levels: they run for every band rect.
        var word;
        var bits;
        var upper;
        var slot = 0;
        var spanLoSlot = 0;
        // Walking to that segment and editing from it visit each segment at most once, so an item that
        // takes more steps than the skyline holds segments has met a corrupt skyline.
        var steps = segments;
        if (spanLo !== crossLo) {
            spanLoSlot = crossLowSlots[ids[item]];
            if (!marked) {
                while (starts[next[slot]] <= spanLo) {
                    slot = next[slot];
                    if (--steps < 0) {
                        intact = false;
                        break sweep;
                    }
                }
            } else {
                word = spanLoSlot >> 5;
                bits = level0[word] & (-1 >>> (31 - (spanLoSlot & 31)));
                if (bits !== 0) {
                    slot = (word << 5) + 31 - Math.clz32(bits);
                } else {
                    word -= 1;
                    bits = word >= 0 ? level1[word >> 5] & (-1 >>> (31 - (word & 31))) : 0;
                    if (bits !== 0) {
                        word = (word & ~31) + 31 - Math.clz32(bits);
                        slot = (word << 5) + 31 - Math.clz32(level0[word]);
                    } else {
                        slot = markAtOrBelow(marks, 2, (word >> 5) - 1);
                    }
                }
                // The slot found is marked and starts at or before spanLo, unless the marks are corrupt.
                if ((level0[slot >> 5] & (1 << (slot & 31))) === 0 || !(starts[slot] <= spanLo)) {
                    intact = false;
                    break sweep;
                }
            }
        }
        // Edit the segments under the span in place. A segment the item does not raise stays; a raised one
        // becomes the item's, merged with the item's segment just before it. Only the first segment can
        // start before the span and only the last can end after it; each keeps that part as its own
        // segment. The item is a new owner and adjacent segments never share one, so the skyline stays
        // canonical without merging anything else.
        var start = starts[slot];
        var tail = -1;  // the item's segment so far, or -1 when the last one written is not the item's
        while (start < spanHi) {
            if (--steps < 0) {
                intact = false;
                break sweep;
            }
            var endSlot = next[slot];
            var end = starts[endSlot];
            var owner = owners[slot];
            var reach = reaches[slot];
            var from = start > spanLo ? start : spanLo;
            var to = end < spanHi ? end : spanHi;
            var raise = false;
            if (from < to) {
                // The owner holds all of the span it shares with the item when this segment starts at the
                // owner's span start or at or before the item's, and ends at the owner's span end or at or
                // after the item's: an owner's segments lie inside its own span.
                if (owner !== NO_OWNER
                        && (start <= spanLo || start === (owner === MOVING_OWNER ? crossLo : spanLows[owner]))
                        && (end >= spanHi || end === (owner === MOVING_OWNER ? crossHi : spanHighs[owner]))) {
                    if (moving) {
                        // A band rect behind the moving rect: the nearest neighbour before reaches furthest.
                        if (reach <= movingLo + slack && (reach > beforeReach || (reach === beforeReach && owner < before))) {
                            before = owner;
                            beforeReach = reach;
                        }
                    } else if (owner === MOVING_OWNER) {
                        // The first band rect the moving rect sees ahead is its neighbour after.
                        if (after < 0 && itemLo >= movingHi - slack && itemHi > movingHi)
                            after = item;
                    } else if (itemLo - reach > tolerance) {
                        gapFirst[gapCount] = owner;
                        gapSecond[gapCount] = item;
                        ++gapCount;
                    }
                }
                raise = itemHi > reach || (moving && itemHi === reach);
            }
            if (!raise) {
                tail = -1;
            } else {
                if (tail >= 0) {
                    // The item's segment grows over this one.
                    --segments;
                    if (marked) {
                        word = slot >> 5;
                        bits = level0[word] & ~(1 << (slot & 31));
                        level0[word] = bits;
                        if (bits === 0) {
                            upper = word >> 5;
                            bits = level1[upper] & ~(1 << (word & 31));
                            level1[upper] = bits;
                            if (bits === 0)
                                unmark(marks, 2, upper);
                        }
                    }
                } else if (start < from) {
                    // The first segment keeps [start, spanLo); the item's segment starts at spanLo.
                    tail = spanLoSlot;
                    starts[tail] = from;
                    owners[tail] = item;
                    reaches[tail] = itemHi;
                    next[slot] = tail;
                    ++segments;
                    if (marked) {
                        word = tail >> 5;
                        bits = level0[word];
                        level0[word] = bits | (1 << (tail & 31));
                        if (bits === 0) {
                            upper = word >> 5;
                            bits = level1[upper];
                            level1[upper] = bits | (1 << (word & 31));
                            if (bits === 0)
                                mark(marks, 2, upper);
                        }
                    }
                } else {
                    tail = slot;
                    owners[tail] = item;
                    reaches[tail] = itemHi;
                }
                if (to < end) {
                    // The last segment keeps [spanHi, end). (The moving rect spans the whole interval.)
                    var split = crossHighSlots[ids[item]];
                    starts[split] = to;
                    owners[split] = owner;
                    reaches[split] = reach;
                    next[split] = endSlot;
                    next[tail] = split;
                    ++segments;
                    if (marked) {
                        word = split >> 5;
                        bits = level0[word];
                        level0[word] = bits | (1 << (split & 31));
                        if (bits === 0) {
                            upper = word >> 5;
                            bits = level1[upper];
                            level1[upper] = bits | (1 << (word & 31));
                            if (bits === 0)
                                mark(marks, 2, upper);
                        }
                    }
                } else {
                    next[tail] = endSlot;
                }
            }
            slot = endSlot;
            start = end;
        }
        if (!marked && segments > WALK_SEGMENTS) {
            // Mark the start of each segment; the skyline ends after exactly `segments` of them.
            marked = true;
            var starting = 0;
            for (var marking = 0; marking < segments; ++marking) {
                mark(marks, 0, starting);
                starting = next[starting];
            }
            if (starting !== slotHi) {
                intact = false;
                break sweep;
            }
        }
    }
    if (marked && intact) {
        // Every mark is a segment start, so zeroing each start's word at every level clears them all; a
        // word already zeroed was zeroed with the words above it.
        var segment = 0;
        for (var clearing = 0; clearing < segments; ++clearing) {
            var position = segment;
            for (var level = 0; level < marks.length; ++level) {
                position >>= 5;
                if (marks[level][position] === 0)
                    break;
                marks[level][position] = 0;
            }
            segment = next[segment];
        }
        intact = segment === slotHi;
    }
    if (!intact) {
        // A corrupt skyline or mark set: this axis gets no spacing, and the next sweep starts from clear
        // marks.
        clearMarks(marks);
        return {before: -1, after: -1, gapCount: 0};
    }
    return {before: before, after: after, gapCount: gapCount};
}

// Centred between the neighbours, or one existing gap away from either neighbour. Gaps no wider than
// the line tolerance are never drawn, so they never attract. The per-gap loop is the hot path of a
// drag frame, so it tracks the best delta in locals instead of snap objects.
function spacingSnap(index, axis, rect, threshold, tolerance, cache) {
    var row = rowAround(index, axis, rect, threshold, tolerance, cache);
    var scratch = index.scratch;
    var lows = scratch.lows;
    var highs = scratch.highs;
    var gapFirst = scratch.gapFirst;
    var gapSecond = scratch.gapSecond;
    var lo = rect[axis.lo];
    var size = rect[axis.hi] - lo;
    var hasBefore = row.before >= 0;
    var hasAfter = row.after >= 0;
    // Deltas that move `lo` to a target: one existing gap after the neighbour before, or before the
    // neighbour after.
    var fromBefore = hasBefore ? highs[row.before] - lo : 0;
    var fromAfter = hasAfter ? lows[row.after] - size - lo : 0;
    var bestDelta = 0;
    var bestDistance = Infinity;
    if (hasBefore && hasAfter) {
        var free = lows[row.after] - highs[row.before] - size;
        if (free / 2 > tolerance) {
            bestDelta = fromBefore + free / 2;
            bestDistance = bestDelta < 0 ? -bestDelta : bestDelta;
        }
    }
    for (var i = 0; i < row.gapCount; ++i) {
        var gap = lows[gapSecond[i]] - highs[gapFirst[i]];
        if (hasBefore) {
            var afterGap = fromBefore + gap;
            var afterDistance = afterGap < 0 ? -afterGap : afterGap;
            if (afterDistance < bestDistance) {
                bestDelta = afterGap;
                bestDistance = afterDistance;
            }
        }
        if (hasAfter) {
            var beforeGap = fromAfter - gap;
            var beforeDistance = beforeGap < 0 ? -beforeGap : beforeGap;
            if (beforeDistance < bestDistance) {
                bestDelta = beforeGap;
                bestDistance = beforeDistance;
            }
        }
    }
    return bestDistance <= threshold ? {delta: bestDelta, value: lo + bestDelta, spaced: true} : null;
}

// Alignment unless equal spacing is strictly closer, which an exact alignment rules out.
function axisSnap(index, axis, rect, threshold, tolerance, spacing, cache) {
    var aligned = alignmentSnap(index[axis.name], rect[axis.lo], rect[axis.hi], threshold);
    if (aligned !== null && aligned.delta === 0)
        return aligned;
    var spaced = spacing ? spacingSnap(index, axis, rect, threshold, tolerance, cache) : null;
    if (spaced !== null && (aligned === null || Math.abs(spaced.delta) < Math.abs(aligned.delta)))
        return spaced;
    return aligned;
}

function intervalGap(lo, hi, otherLo, otherHi) {
    return Math.max(0, otherLo - hi, lo - otherHi);
}

// The guide through every sorted candidate feature within tolerance of `feature`, or null. Its value
// is the matched coordinate nearest the feature; it spans `rect` and every matched candidate.
function lineAt(index, axis, rect, sorted, feature, tolerance) {
    var crossIdx = index[axis.cross];
    var crossLows = crossIdx.lo;
    var crossHighs = crossIdx.hi;
    var rectLo = rect[axis.crossLo];
    var rectHi = rect[axis.crossHi];
    var line = null;
    for (var i = lowerBound(sorted.values, feature - tolerance);
         i < sorted.values.length && sorted.values[i] <= feature + tolerance; ++i) {
        var id = sorted.rects[i];
        var value = sorted.values[i];
        if (line === null)
            line = {axis: axis.name, value: value, start: rectLo, end: rectHi, distance: Infinity};
        else if (Math.abs(value - feature) < Math.abs(line.value - feature))
            line.value = value;
        line.start = Math.min(line.start, crossLows[id]);
        line.end = Math.max(line.end, crossHighs[id]);
        line.distance = Math.min(line.distance, intervalGap(crossLows[id], crossHighs[id], rectLo, rectHi));
    }
    return line;
}

// Lines merge per (axis, value).
function addLine(lines, line) {
    if (line === null)
        return;
    for (var i = 0; i < lines.length; ++i) {
        if (lines[i].value !== line.value)
            continue;
        lines[i].start = Math.min(lines[i].start, line.start);
        lines[i].end = Math.max(lines[i].end, line.end);
        lines[i].distance = Math.min(lines[i].distance, line.distance);
        return;
    }
    lines.push(line);
}

function compareLines(a, b) {
    return a.distance - b.distance || a.value - b.value;
}

function publicLine(line) {
    return {axis: line.axis, value: line.value, start: line.start, end: line.end};
}

function compareGaps(a, b) {
    return a.distance - b.distance || a.start - b.start || a.cross - b.cross || a.end - b.end;
}

function publicGap(gap) {
    return {axis: gap.axis, start: gap.start, end: gap.end, cross: gap.cross, crossStart: gap.crossStart,
            crossEnd: gap.crossEnd, size: gap.size};
}

// Appends the `cap` closest items of one axis, closest first.
function appendClosest(target, items, cap, compare, publish) {
    items.sort(compare);
    for (var i = 0; i < items.length && i < cap; ++i)
        target.push(publish(items[i]));
}

function moveLines(index, rect, tolerance) {
    var lines = [];
    for (var a = 0; a < AXES.length; ++a) {
        var axis = AXES[a];
        var axisIdx = index[axis.name];
        var lo = rect[axis.lo];
        var hi = rect[axis.hi];
        var axisLines = [];
        addLine(axisLines, lineAt(index, axis, rect, axisIdx.edges, lo, tolerance));
        addLine(axisLines, lineAt(index, axis, rect, axisIdx.edges, hi, tolerance));
        addLine(axisLines, lineAt(index, axis, rect, axisIdx.centres, (lo + hi) / 2, tolerance));
        appendClosest(lines, axisLines, MAX_LINES_PER_AXIS, compareLines, publicLine);
    }
    return lines;
}

// Marker for the gap [start, end] along `axis`. [crossStart, crossEnd] is the cross span its two rects
// share inside the moving rect's band, and `cross` its middle.
function gapMarker(axis, start, end, crossStart, crossEnd, distance) {
    return {axis: axis.name, start: start, end: end, cross: (crossStart + crossEnd) / 2, crossStart: crossStart,
            crossEnd: crossEnd, size: end - start, distance: distance};
}

function matchesSize(sizes, size, tolerance) {
    for (var i = 0; i < sizes.length; ++i) {
        if (Math.abs(sizes[i] - size) <= tolerance)
            return true;
    }
    return false;
}

function matchesBandGap(scratch, gapCount, size, tolerance) {
    var lows = scratch.lows;
    var highs = scratch.highs;
    var gapFirst = scratch.gapFirst;
    var gapSecond = scratch.gapSecond;
    for (var i = 0; i < gapCount; ++i) {
        var difference = lows[gapSecond[i]] - highs[gapFirst[i]] - size;
        if (difference <= tolerance && difference >= -tolerance)
            return true;
    }
    return false;
}

// Equal-spacing markers: the moving rect's gap to a neighbour counts when it equals the gap on its
// other side or an existing band gap; every existing band gap of a counted size is marked too.
function gapMarkers(index, rect, tolerance, cache) {
    var markers = [];
    var scratch = index.scratch;
    for (var a = 0; a < AXES.length; ++a) {
        var axis = AXES[a];
        var row = rowAround(index, axis, rect, tolerance, tolerance, cache);
        var lo = rect[axis.lo];
        var hi = rect[axis.hi];
        var beforeSize = row.before >= 0 ? lo - scratch.highs[row.before] : NaN;
        var afterSize = row.after >= 0 ? scratch.lows[row.after] - hi : NaN;
        var beforeValid = beforeSize > tolerance;
        var afterValid = afterSize > tolerance;
        var centred = beforeValid && afterValid && Math.abs(beforeSize - afterSize) <= tolerance;
        var countBefore = beforeValid && (centred || matchesBandGap(scratch, row.gapCount, beforeSize, tolerance));
        var countAfter = afterValid && (centred || matchesBandGap(scratch, row.gapCount, afterSize, tolerance));
        if (!countBefore && !countAfter)
            continue;
        var sizes = [];
        var axisMarkers = [];
        if (countBefore) {
            axisMarkers.push(gapMarker(axis, scratch.highs[row.before], lo,
                                       scratch.spanLows[row.before], scratch.spanHighs[row.before], 0));
            sizes.push(beforeSize);
        }
        if (countAfter) {
            axisMarkers.push(gapMarker(axis, hi, scratch.lows[row.after],
                                       scratch.spanLows[row.after], scratch.spanHighs[row.after], 0));
            sizes.push(afterSize);
        }
        for (var i = 0; i < row.gapCount; ++i) {
            var first = scratch.gapFirst[i];
            var second = scratch.gapSecond[i];
            var start = scratch.highs[first];
            var end = scratch.lows[second];
            if (!matchesSize(sizes, end - start, tolerance))
                continue;
            axisMarkers.push(gapMarker(axis, start, end,
                                       Math.max(scratch.spanLows[first], scratch.spanLows[second]),
                                       Math.min(scratch.spanHighs[first], scratch.spanHighs[second]),
                                       intervalGap(start, end, lo, hi)));
        }
        appendClosest(markers, axisMarkers, MAX_GAPS_PER_AXIS, compareGaps, publicGap);
    }
    return markers;
}

function hasGuide(lines, gaps, axisName) {
    for (var i = 0; i < lines.length; ++i) {
        if (lines[i].axis === axisName)
            return true;
    }
    for (var j = 0; j < gaps.length; ++j) {
        if (gaps[j].axis === axisName)
            return true;
    }
    return false;
}

// Snaps the moving union `base` {left, top, right, bottom} (at zero offset) dragged by (dx, dy).
// options: {threshold > 0, axisLock: "" | "horizontal" | "vertical", spacing: true}. "horizontal" moves
// X only, so Y never snaps and keeps dy; "vertical" is the mirror. An axis reports snapped only when a
// line or gap marker on it holds at the returned offset. Returns {dx, dy, snappedX, snappedY,
// lines: [{axis, value, start, end}], gaps: [{axis, start, end, cross, crossStart, crossEnd, size}]}; a gap's
// [crossStart, crossEnd] is the cross span its two rects share inside the moving rect's band (the moving
// rect is one of them for its own gaps) and `cross` the middle of it.
function resolveMove(index, base, dx, dy, options) {
    var inputDx = finite(dx);
    var inputDy = finite(dy);
    var result = {
        dx: isFinite(inputDx) ? inputDx : 0.0,
        dy: isFinite(inputDy) ? inputDy : 0.0,
        snappedX: false,
        snappedY: false,
        lines: [],
        gaps: []
    };
    var moving = boxRect(base);
    var settings = options || {};
    var threshold = finite(settings.threshold);
    if (moving === null || !(threshold > 0) || !indexHasRects(index))
        return result;
    var axisLock = String(settings.axisLock || "");
    var spacing = settings.spacing === undefined || settings.spacing === null ? true : Boolean(settings.spacing);
    var tolerance = Math.min(LINE_TOLERANCE, threshold);
    // One sorted band per axis; the markers filter it at the final position. Which band rects hold the
    // moving rect is decided once, at the input offset, so snap and markers leave out the same ones.
    var start = translated(moving, result.dx, result.dy);
    var bands = {inside: start};
    var snapX = axisLock !== "vertical" ? axisSnap(index, AXIS_X, start, threshold, tolerance, spacing, bands) : null;
    var snapY = axisLock !== "horizontal" ? axisSnap(index, AXIS_Y, start, threshold, tolerance, spacing, bands) : null;
    // A spacing snap is chosen from the band at the start offset, and the other axis' snap can move the
    // rect out of that band. A spacing snap that no guide at the final offset shows falls back to the
    // axis' alignment snap, whose line always shows, or to no snap. Each pass settles an axis for good,
    // so this re-measures at most twice.
    var settled;
    var lines;
    var gaps;
    for (;;) {
        settled = translated(moving,
                             result.dx + (snapX !== null ? snapX.delta : 0),
                             result.dy + (snapY !== null ? snapY.delta : 0));
        lines = moveLines(index, settled, tolerance);
        gaps = spacing ? gapMarkers(index, settled, tolerance, bands) : [];
        var dropX = snapX !== null && snapX.spaced === true && !hasGuide(lines, gaps, "x");
        var dropY = snapY !== null && snapY.spaced === true && !hasGuide(lines, gaps, "y");
        if (!dropX && !dropY)
            break;
        if (dropX)
            snapX = alignmentSnap(index.x, start.left, start.right, threshold);
        if (dropY)
            snapY = alignmentSnap(index.y, start.top, start.bottom, threshold);
    }
    if (snapX !== null) {
        result.dx += snapX.delta;
        result.snappedX = true;
    }
    if (snapY !== null) {
        result.dy += snapY.delta;
        result.snappedY = true;
    }
    result.lines = lines;
    result.gaps = gaps;
    return result;
}

function fitsMinimum(rect, minWidth, minHeight) {
    var width = rect.right - rect.left;
    var height = rect.bottom - rect.top;
    return width > 0 && height > 0
        && width >= minWidth - SIZE_EPSILON && height >= minHeight - SIZE_EPSILON;
}

function edgeLines(index, rect, axis, edge, tolerance) {
    var lines = [];
    addLine(lines, lineAt(index, axis, rect, index[axis.name].edges, rect[edge], tolerance));
    return lines;
}

// Snaps the moving edges of `rect` {left, top, right, bottom}, given after the handle's own min clamp and
// aspect lock. spec: {movingLeft, movingTop, horizontalOnly, aspectRatio, minWidth, minHeight, threshold};
// movingLeft false moves the right edge, movingTop false the bottom, aspectRatio 0 is free. Moving edges
// snap to the nearest candidate edge within threshold that keeps the minimum size; with an aspect ratio
// the closer valid edge drives and the other moving edge follows. Returns {rect, snappedX, snappedY,
// lines} with lines for snapped edges.
function resolveResize(index, rect, spec) {
    var input = boxRect(rect);
    var result = {rect: input !== null ? translated(input, 0, 0) : rect, snappedX: false, snappedY: false, lines: []};
    var settings = spec || {};
    var threshold = finite(settings.threshold);
    if (input === null || !(threshold > 0) || !indexHasRects(index))
        return result;
    var movingLeft = Boolean(settings.movingLeft);
    var movingTop = Boolean(settings.movingTop);
    var horizontalOnly = Boolean(settings.horizontalOnly);
    var ratio = finite(settings.aspectRatio);
    var minWidth = Math.max(0, finite(settings.minWidth) || 0);
    var minHeight = Math.max(0, finite(settings.minHeight) || 0);
    var xEdge = movingLeft ? "left" : "right";
    var yEdge = movingTop ? "top" : "bottom";
    var output = translated(input, 0, 0);
    if (ratio > 0 && !horizontalOnly) {
        // The moving X edge at `value`, with the moving Y edge following the ratio from the fixed corner.
        var byX = function(value) {
            var sized = translated(input, 0, 0);
            sized[xEdge] = value;
            var height = (sized.right - sized.left) / ratio;
            if (movingTop)
                sized.top = sized.bottom - height;
            else
                sized.bottom = sized.top + height;
            return sized;
        };
        var byY = function(value) {
            var sized = translated(input, 0, 0);
            sized[yEdge] = value;
            var width = (sized.bottom - sized.top) * ratio;
            if (movingLeft)
                sized.left = sized.right - width;
            else
                sized.right = sized.left + width;
            return sized;
        };
        var aspectX = nearestAccepted(index.x.edges.values, input[xEdge], threshold,
                                      function(value) { return fitsMinimum(byX(value), minWidth, minHeight); });
        var aspectY = nearestAccepted(index.y.edges.values, input[yEdge], threshold,
                                      function(value) { return fitsMinimum(byY(value), minWidth, minHeight); });
        if (aspectX === null && aspectY === null)
            return result;
        var useX = aspectX !== null && (aspectY === null || Math.abs(aspectX.delta) <= Math.abs(aspectY.delta));
        output = useX ? byX(aspectX.value) : byY(aspectY.value);
        result.snappedX = useX;
        result.snappedY = !useX;
    } else {
        var snapX = nearestAccepted(index.x.edges.values, input[xEdge], threshold, function(value) {
            var width = movingLeft ? input.right - value : value - input.left;
            return width > 0 && width >= minWidth - SIZE_EPSILON;
        });
        var snapY = horizontalOnly ? null : nearestAccepted(index.y.edges.values, input[yEdge], threshold, function(value) {
            var height = movingTop ? input.bottom - value : value - input.top;
            return height > 0 && height >= minHeight - SIZE_EPSILON;
        });
        if (snapX !== null) {
            output[xEdge] = snapX.value;
            result.snappedX = true;
        }
        if (snapY !== null) {
            output[yEdge] = snapY.value;
            result.snappedY = true;
        }
    }
    result.rect = output;
    var tolerance = Math.min(LINE_TOLERANCE, threshold);
    if (result.snappedX)
        appendClosest(result.lines, edgeLines(index, output, AXIS_X, xEdge, tolerance),
                      MAX_LINES_PER_AXIS, compareLines, publicLine);
    if (result.snappedY)
        appendClosest(result.lines, edgeLines(index, output, AXIS_Y, yEdge, tolerance),
                      MAX_LINES_PER_AXIS, compareLines, publicLine);
    return result;
}
