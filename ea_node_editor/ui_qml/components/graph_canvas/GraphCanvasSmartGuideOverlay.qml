// Purpose: Draw the smart-guide lines and equal-spacing gap markers of a node drag or resize in screen space, above the nodes and outside the canvas export content.
// Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
// Tests: tests/test_graph_canvas_smart_guides.py
import QtQuick 2.15
import QtQuick.Window 2.15
import "../common/contrast_utils.js" as ContrastUtils
import "GraphCanvasSmartGuideEngine.js" as SmartGuideEngine

// Guides arrive in scene coordinates from GraphCanvasSmartGuides and map to screen pixels here
// (screen = size / 2 + (scene - centre) * zoom). Every guide line, gap line and gap tick is a run of cells
// on one grid of hairline-sized cells, so lines keep one device-pixel-aligned width at every zoom and the
// pieces can be kept from sharing a pixel: the colours are translucent, and a pixel painted twice reads
// darker (where a gap line met its ticks, or where two guides cross or run together). A fixed delegate
// pool keeps drag frames free of delegate churn, and the layout is built once per publish: the
// controller bumps guideRevision after it has set both its lines and its gaps.
Item {
    id: root
    objectName: "graphCanvasSmartGuideOverlay"

    property var guides: null
    property var viewBridge: null
    property color backgroundFillColor: "#1d1f24"
    readonly property bool darkCanvasFill: (0.2126 * root.backgroundFillColor.r
        + 0.7152 * root.backgroundFillColor.g
        + 0.0722 * root.backgroundFillColor.b) <= 0.5
    // Style knobs stay plain properties so a render script can compare options with setProperty.
    // A faint orange picked by the canvas fill, not the shell theme (the canvas colour is its own
    // preference): #E8590C at 60% on light canvases, the same hue lighter at 45% on dark ones, both
    // clear of the amber warning colours.
    property color guideColor: root.darkCanvasFill ? "#73ff7a3d" : "#99e8590c"
    // Gap labels are off for now. When shown, a label pill takes the opaque guide hue and its text
    // whichever of dark or white reads better on the pill.
    property bool showGapLabels: false
    property color pillFillColor: Qt.rgba(root.guideColor.r, root.guideColor.g, root.guideColor.b, 1.0)
    property color labelTextColor: root.readableTextColor(root.pillFillColor)
    property real lineOvershootPx: 4.0
    property real gapTickLengthPx: 7.0
    property int gapLabelPixelSize: 10
    // Horizontal-gap markers run this many scene units below the top of the cross span their two rects
    // share, so they stay in the node header band at every zoom, and never past the span's middle; zero
    // or less puts them at the middle. Vertical-gap markers always run down the middle.
    property real horizontalGapHeaderOffset: 16.0
    // The screen's device pixel ratio, a plain property so a test or render script can set another.
    property real devicePixelRatio: Screen.devicePixelRatio

    readonly property int lineCapacity: SmartGuideEngine.MAX_LINES_PER_AXIS * 2
    readonly property int gapCapacity: SmartGuideEngine.MAX_GAPS_PER_AXIS * 2
    // Every guide line and every gap marker's three pieces, twice over for the splits at crossings.
    readonly property int pieceCapacity: (root.lineCapacity + root.gapCapacity * 3) * 2
    // The controller's lines and gaps, taken together once per publish (see _readGuides).
    property var _published: ({"lines": [], "gaps": []})
    readonly property var lines: root._published.lines
    readonly property var gaps: root._published.gaps
    readonly property int visibleLineCount: Math.min(root.lines.length, root.lineCapacity)
    readonly property int visibleGapCount: Math.min(root.gaps.length, root.gapCapacity)
    readonly property real _zoom: {
        var zoom = root.viewBridge ? Number(root.viewBridge.zoom_value) : 1.0;
        return isFinite(zoom) && zoom > 0.0001 ? zoom : 1.0;
    }
    readonly property real _centerX: root.viewBridge ? Number(root.viewBridge.center_x) || 0.0 : 0.0
    readonly property real _centerY: root.viewBridge ? Number(root.viewBridge.center_y) || 0.0 : 0.0
    readonly property real _pixelRatio: Math.max(1.0, Number(root.devicePixelRatio) || 1.0)
    // round(device pixel ratio) device pixels, never fewer than one: 1 device pixel at 100% and 125%
    // scaling (0.8 logical px at 125%), 2 at 150% and 200%. Every piece covers whole device pixels.
    readonly property real hairline: Math.max(1, Math.round(root._pixelRatio)) / root._pixelRatio
    // Built once per publish, view change or style change. It reads the guides only through
    // _published: reading lines and gaps as well would build it once for each of them.
    readonly property var _layout: root._buildLayout(root._published)
    // One marker per visible gap, in cells: {horizontal, across, start, end, size}, or null for a gap
    // without finite coordinates. The gap covers cells [start, end) along its axis; the marker runs
    // along cell `across`.
    readonly property var markers: root._layout.markers
    // What the pool paints: {x, y, width, height, part} in logical px, part "line", "gapLine" or
    // "gapTick" (the most important piece a merged run holds). Never more than the pool holds, and no
    // two pieces share a pixel unless splitting their crossing would overflow the pool (see _pieces).
    readonly property var pieces: root._layout.pieces
    readonly property color _darkLabelTextColor: "#1b1d22"

    anchors.fill: parent
    z: 33
    enabled: false
    visible: root.visibleLineCount > 0 || root.visibleGapCount > 0

    onGuidesChanged: root._readGuides()
    Component.onCompleted: root._readGuides()

    Connections {
        target: root.guides

        function onGuideRevisionChanged() {
            root._readGuides();
        }
    }

    // One assignment for both arrays, so the layout is built once however many of them changed.
    function _readGuides() {
        var guides = root.guides;
        root._published = {
            "lines": guides && guides.lines ? guides.lines : [],
            "gaps": guides && guides.gaps ? guides.gaps : []
        };
    }

    function screenX(sceneX) {
        return root.width * 0.5 + (Number(sceneX) - root._centerX) * root._zoom;
    }

    function screenY(sceneY) {
        return root.height * 0.5 + (Number(sceneY) - root._centerY) * root._zoom;
    }

    function _pixel(value) {
        return Math.round(Number(value) * root._pixelRatio) / root._pixelRatio;
    }

    // Dark or white text, whichever has the higher WCAG contrast on `fill` as it shows over the canvas
    // (dark on a tie).
    function readableTextColor(fill) {
        var alpha = fill.a;
        var under = root.backgroundFillColor;
        var shown = String(Qt.rgba(fill.r * alpha + under.r * (1.0 - alpha),
                                   fill.g * alpha + under.g * (1.0 - alpha),
                                   fill.b * alpha + under.b * (1.0 - alpha),
                                   1.0));
        var white = Qt.rgba(1.0, 1.0, 1.0, 1.0);
        return ContrastUtils.contrastRatio(root._darkLabelTextColor, shown) >= ContrastUtils.contrastRatio(white, shown)
            ? root._darkLabelTextColor
            : white;
    }

    // Cell i covers [i, i + 1) hairlines. The cell boundary nearest `position` (logical px).
    function _cellAt(position) {
        return Math.round(Number(position) / root.hairline);
    }

    // The cell a hairline centred on `position` covers (the later one when it is centred on a boundary).
    function _cellAround(position) {
        return Math.round(Number(position) / root.hairline - 0.5);
    }

    // The scene coordinate a gap marker runs along: horizontal gaps sit in the header band.
    function markerCross(gap) {
        var middle = Number(gap.cross);
        var spanStart = gap.crossStart === undefined || gap.crossStart === null ? NaN : Number(gap.crossStart);
        if (gap.axis === "x" && root.horizontalGapHeaderOffset > 0 && isFinite(spanStart))
            return Math.min(spanStart + root.horizontalGapHeaderOffset, middle);
        return middle;
    }

    function _buildLayout(published) {
        var markers = root._markers(published.gaps);
        return {"markers": markers, "pieces": root._pieces(published.lines, markers)};
    }

    function _markers(gaps) {
        var markers = [];
        var count = Math.min(gaps.length, root.gapCapacity);
        for (var i = 0; i < count; ++i) {
            var gap = gaps[i];
            if (!gap) {
                markers.push(null);
                continue;
            }
            var horizontal = gap.axis === "x";
            var cross = root.markerCross(gap);
            var across = root._cellAround(horizontal ? root.screenY(cross) : root.screenX(cross));
            var start = root._cellAt(horizontal ? root.screenX(gap.start) : root.screenY(gap.start));
            var end = root._cellAt(horizontal ? root.screenX(gap.end) : root.screenY(gap.end));
            if (!(isFinite(across) && isFinite(start) && isFinite(end))) {
                markers.push(null);
                continue;
            }
            markers.push({
                "horizontal": horizontal,
                "across": across,
                "start": start,
                "end": Math.max(end, start + 1),
                "size": Number(gap.size)
            });
        }
        return markers;
    }

    // Guide lines and gap-marker pieces as cell runs: a vertical run covers column `across`, rows
    // [lo, hi); a horizontal one row `across`, columns [lo, hi). A gap marker puts a tick on the first and
    // the last cell of its gap and its line only between them. Rank orders who gives a shared cell up.
    function _rawRuns(lines, markers) {
        var runs = [];
        var lineCount = Math.min(lines.length, root.lineCapacity);
        for (var i = 0; i < lineCount; ++i) {
            var guide = lines[i];
            if (!guide)
                continue;
            // axis "x" is a vertical line at x = value from y = start to y = end.
            var vertical = guide.axis === "x";
            var across = root._cellAround(vertical ? root.screenX(guide.value) : root.screenY(guide.value));
            var lo = root._cellAt((vertical ? root.screenY(guide.start) : root.screenX(guide.start))
                - root.lineOvershootPx);
            var hi = root._cellAt((vertical ? root.screenY(guide.end) : root.screenX(guide.end))
                + root.lineOvershootPx);
            if (isFinite(across) && isFinite(lo) && isFinite(hi))
                runs.push({"vertical": vertical, "across": across, "lo": lo, "hi": Math.max(hi, lo + 1),
                           "rank": 0, "part": "line"});
        }
        var half = Math.max(0, Math.round((Number(root.gapTickLengthPx) / root.hairline - 1.0) * 0.5));
        for (var j = 0; j < markers.length; ++j) {
            var marker = markers[j];
            if (!marker)
                continue;
            // axis "x" gaps are horizontal markers: vertical ticks and a horizontal line.
            var first = marker.start;
            var last = marker.end - 1;
            runs.push({"vertical": marker.horizontal, "across": first, "lo": marker.across - half,
                       "hi": marker.across + half + 1, "rank": 2, "part": "gapTick"});
            if (last > first)
                runs.push({"vertical": marker.horizontal, "across": last, "lo": marker.across - half,
                           "hi": marker.across + half + 1, "rank": 2, "part": "gapTick"});
            if (last - first > 1)
                runs.push({"vertical": !marker.horizontal, "across": marker.across, "lo": first + 1, "hi": last,
                           "rank": 1, "part": "gapLine"});
        }
        return runs;
    }

    // The runs of one orientation, collinear ones merged where they share or touch cells.
    function _mergedRuns(runs, vertical) {
        var sorted = [];
        for (var i = 0; i < runs.length; ++i) {
            if (runs[i].vertical === vertical)
                sorted.push(runs[i]);
        }
        sorted.sort(function(a, b) { return a.across - b.across || a.lo - b.lo; });
        var merged = [];
        for (var k = 0; k < sorted.length; ++k) {
            var run = sorted[k];
            var previous = merged.length ? merged[merged.length - 1] : null;
            if (previous !== null && previous.across === run.across && run.lo <= previous.hi) {
                previous.hi = Math.max(previous.hi, run.hi);
                if (run.rank < previous.rank) {
                    previous.rank = run.rank;
                    previous.part = run.part;
                }
                continue;
            }
            merged.push({"vertical": vertical, "across": run.across, "lo": run.lo, "hi": run.hi,
                         "rank": run.rank, "part": run.part, "cuts": [], "applied": []});
        }
        return merged;
    }

    // A run's cut cells, sorted, as blocks of adjacent cells {lo, hi, rank}: cells [lo, hi), and the
    // rank of the most important run that took one of them.
    function _cutBlocks(run) {
        var cuts = run.cuts.slice().sort(function(a, b) { return a.cell - b.cell; });
        var blocks = [];
        for (var i = 0; i < cuts.length; ++i) {
            var block = blocks.length ? blocks[blocks.length - 1] : null;
            if (block !== null && cuts[i].cell <= block.hi) {
                block.hi = Math.max(block.hi, cuts[i].cell + 1);
                block.rank = Math.min(block.rank, cuts[i].rank);
                continue;
            }
            blocks.push({"lo": cuts[i].cell, "hi": cuts[i].cell + 1, "rank": cuts[i].rank});
        }
        return blocks;
    }

    function _appendRect(output, run, lo, hi) {
        var cell = root.hairline;
        output.push(run.vertical
            ? {"x": run.across * cell, "y": lo * cell, "width": cell, "height": (hi - lo) * cell, "part": run.part}
            : {"x": lo * cell, "y": run.across * cell, "width": (hi - lo) * cell, "height": cell, "part": run.part});
    }

    // A run minus the cut blocks applied to it.
    function _appendSplit(output, run) {
        var blocks = run.applied.slice().sort(function(a, b) { return a.lo - b.lo; });
        var from = run.lo;
        for (var i = 0; i < blocks.length; ++i) {
            if (blocks[i].lo > from)
                root._appendRect(output, run, from, blocks[i].lo);
            from = Math.max(from, blocks[i].hi);
        }
        if (run.hi > from)
            root._appendRect(output, run, from, run.hi);
    }

    // Merges collinear runs, then leaves every cell a vertical and a horizontal run share to one of them:
    // the lesser piece (higher rank) gives it up, the horizontal run on a tie. A run's given-up cells form
    // blocks of adjacent cells. A block at either end of the run only shortens it (a block covering it
    // removes it), so it costs no piece and is always cut out. A block inside the run splits it in two,
    // one piece more: those are cut out while the pool has room, the blocks with the most crossings first,
    // then the most important. A crossing whose block did not fit stays painted by both runs.
    function _pieces(lines, markers) {
        var runs = root._rawRuns(lines, markers);
        var columns = root._mergedRuns(runs, true);
        var rows = root._mergedRuns(runs, false);
        for (var c = 0; c < columns.length; ++c) {
            var column = columns[c];
            for (var r = 0; r < rows.length; ++r) {
                var row = rows[r];
                if (row.lo <= column.across && column.across < row.hi
                        && column.lo <= row.across && row.across < column.hi) {
                    var rank = Math.min(column.rank, row.rank);
                    if (column.rank > row.rank)
                        column.cuts.push({"cell": row.across, "rank": rank});
                    else
                        row.cuts.push({"cell": column.across, "rank": rank});
                }
            }
        }
        var merged = columns.concat(rows);
        var count = 0;
        var inner = [];
        for (var i = 0; i < merged.length; ++i) {
            var run = merged[i];
            var blocks = root._cutBlocks(run);
            for (var b = 0; b < blocks.length; ++b) {
                if (blocks[b].lo === run.lo || blocks[b].hi === run.hi)
                    run.applied.push(blocks[b]);
                else
                    inner.push({"run": run, "block": blocks[b], "order": i});
            }
            var removed = run.applied.length === 1 && run.applied[0].lo === run.lo && run.applied[0].hi === run.hi;
            if (!removed)
                count += 1;
        }
        inner.sort(function(a, b) {
            return (b.block.hi - b.block.lo) - (a.block.hi - a.block.lo)
                || a.block.rank - b.block.rank
                || a.order - b.order
                || a.block.lo - b.block.lo;
        });
        for (var k = 0; k < inner.length && count < root.pieceCapacity; ++k) {
            inner[k].run.applied.push(inner[k].block);
            count += 1;
        }
        var output = [];
        for (var m = 0; m < merged.length; ++m)
            root._appendSplit(output, merged[m]);
        return output;
    }

    Repeater {
        model: root.pieceCapacity

        delegate: Rectangle {
            objectName: "graphCanvasSmartGuidePiece"
            readonly property var piece: index < root.pieces.length ? root.pieces[index] : null
            readonly property string part: piece === null ? "" : piece.part

            visible: piece !== null
            antialiasing: false
            color: root.guideColor
            x: piece === null ? 0.0 : piece.x
            y: piece === null ? 0.0 : piece.y
            width: piece === null ? 0.0 : piece.width
            height: piece === null ? 0.0 : piece.height
        }
    }

    // No label delegate exists while the labels are off, so a drag frame does no label work.
    Repeater {
        model: root.showGapLabels ? root.gapCapacity : 0

        delegate: Rectangle {
            id: gapLabel
            objectName: "graphCanvasSmartGuideGapLabel"
            readonly property var marker: index < root.markers.length ? root.markers[index] : null
            readonly property bool horizontal: marker !== null && marker.horizontal
            readonly property real lengthPx: marker === null ? 0.0 : (marker.end - marker.start) * root.hairline
            readonly property real centerAlong: marker === null
                ? 0.0
                : (marker.start + marker.end) * 0.5 * root.hairline
            readonly property real centerAcross: marker === null ? 0.0 : (marker.across + 0.5) * root.hairline

            visible: marker !== null && lengthPx >= (horizontal ? width : height) + root.gapTickLengthPx * 2.0
            width: Math.ceil(gapLabelText.implicitWidth) + 8
            height: Math.ceil(gapLabelText.implicitHeight) + 2
            radius: height * 0.5
            color: root.pillFillColor
            x: root._pixel((horizontal ? centerAlong : centerAcross) - width * 0.5)
            y: root._pixel((horizontal ? centerAcross : centerAlong) - height * 0.5)

            Text {
                id: gapLabelText
                objectName: "graphCanvasSmartGuideGapLabelText"
                anchors.centerIn: parent
                text: gapLabel.marker === null ? "" : String(Math.round(gapLabel.marker.size))
                color: root.labelTextColor
                font.pixelSize: root.gapLabelPixelSize
                font.bold: true
            }
        }
    }
}
