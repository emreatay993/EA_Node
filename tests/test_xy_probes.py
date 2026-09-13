# Purpose: Prove canonical cursor calculations, clipping, paging and bounded scans.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_probes.py
from dataclasses import replace
import tracemalloc

import numpy as np
import pytest

from ea_node_editor.runtime_contracts import ArrayValue, PlotSignal
from ea_node_editor.web_host import xy_probes as probes
from ea_node_editor.web_host.xy_probe_contract import normalized_probe_state
from tests.test_plot_value import plot_value


def plot(x, y, **settings):
    x = np.asarray(x)
    kind = "datetime" if x.dtype.kind == "M" else "numeric"
    base = plot_value()
    signal = PlotSignal("signal-0", ArrayValue.from_numpy(x), ArrayValue.from_numpy(np.asarray(y, dtype=float)), x_kind=kind)
    return replace(base, signals=(signal,), settings=replace(base.settings, **settings))


def request(axis="x", position=1., method="intersections", x=(-10., 10.), y=(-10., 10.), page=0):
    return {"axis": axis, "position": position, "method": method, "ranges": {"x": x, "y": y}, "page": page, "revision": 7}


def test_crossings_vertices_and_source_order():
    value = plot([0, 1, 2], [0, 2, 0])
    result = probes.query_probe(value, request())
    assert result["total"] == 1 and result["rows"][0]["kind"] == "exact"
    assert result["rows"][0]["sample_start"] == 1
    result = probes.query_probe(value, request("y", 1))
    assert [r["x"] for r in result["rows"]] == [.5, 1.5]
    assert all(r["kind"] == "interpolated" for r in result["rows"])
    result = probes.query_probe(plot([0, 2, 0, 2], [0, 1, 2, 3]), request())
    assert [r["y"] for r in result["rows"]] == [.5, 1.5, 2.5]
    assert probes.query_probe(value, request(position=0))["rows"][0]["sample_start"] == 0
    assert probes.query_probe(value, request(position=2))["rows"][0]["sample_start"] == 2


@pytest.mark.parametrize("chunk", [1, 2, 3, 65536])
def test_overlaps_merge_across_chunks_and_absorb_shared_vertices(monkeypatch, chunk):
    monkeypatch.setattr(probes, "PROBE_CHUNK_SIZE", chunk)
    value = plot([0, 1, 1, 1, 2], [0, 1, 2, 0, 1])
    result = probes.query_probe(value, request(y=(.5, 1.5)))
    assert result["total"] == result["overlaps"] == 1
    row = result["rows"][0]
    assert (row["sample_start"], row["sample_end"], row["y"], row["y_end"]) == (1, 3, .5, 1.5)
    result = probes.query_probe(plot(np.arange(7), np.ones(7)), request("y", 1, x=(1.5, 4.5)))
    assert result["total"] == 1
    assert (result["rows"][0]["x"], result["rows"][0]["x_end"]) == (1.5, 4.5)


def test_gaps_nearest_ties_and_viewport_clipping():
    value = plot([0, 1, 2, 3], [0, np.nan, 2, 0])
    assert probes.query_probe(value, request())["total"] == 0
    crossing = probes.query_probe(value, request("y", 1))
    assert [r["x"] for r in crossing["rows"]] == [2.5]
    samples = probes.query_probe(value, request(method="nearest"))
    assert [r["sample_start"] for r in samples["rows"]] == [0, 2]
    assert [r["offset"] for r in samples["rows"]] == [-1, 1]
    assert probes.query_probe(value, request(position=20))["outside_view"]
    through_window = plot([-2, 2], [-2, 2])
    assert probes.query_probe(through_window, request(position=0, x=(-.5, .5), y=(-.5, .5)))["total"] == 1
    assert probes.query_probe(through_window, request(position=0, method="nearest", x=(-.5, .5), y=(-.5, .5)))["total"] == 0


def test_logarithmic_intersections_and_masked_gaps():
    value = plot([0, 2], [1, 100], logarithmic_y_axis=True)
    row = probes.query_probe(value, request(y=(1, 100)))["rows"][0]
    assert row["y"] == pytest.approx(10)
    row = probes.query_probe(value, request("y", 10, y=(1, 100)))["rows"][0]
    assert row["x"] == pytest.approx(1)
    gap = plot([0, 1, 2], [1, -1, 100], logarithmic_y_axis=True)
    assert probes.query_probe(gap, request(y=(1, 100)))["total"] == 0
    samples = probes.query_probe(value, request("y", 10, "nearest", y=(1, 100)))["rows"]
    assert len(samples) == 2  # Equidistant in the plotted logarithmic scale.
    for low, midpoint, high in ((2., 4., 8.), (.25, .5, 1.), (1e-200, 1., 1e200)):
        logarithmic = plot([0, 1], [low, high], logarithmic_y_axis=True)
        tied = probes.query_probe(logarithmic, request('y', midpoint, 'nearest', y=(low, high)))
        assert [row['sample_start'] for row in tied['rows']] == [0, 1]


def test_datetime_matches_rendered_fractional_milliseconds_and_sample_text():
    dates = np.array(["2026-01-01T00:00:00.000100", "2026-01-01T00:00:02.000100"], dtype="datetime64[us]")
    from ea_node_editor.common.plot_coordinates import plot_x_coordinates
    origin = float(plot_x_coordinates(dates)[0])
    value = plot(dates, [0, 2])
    result = probes.query_probe(value, request(position=origin + 1000, x=(origin, origin + 2000)))
    assert result["rows"][0]["y"] == 1
    assert result["rows"][0]["x_text"].startswith("2026-01-01T00:00:01.000")
    result = probes.query_probe(value, request(position=origin + 1000, method="nearest", x=(origin, origin + 2000)))
    assert [r["offset"] for r in result["rows"]] == [-1000, 1000]
    assert result["rows"][0]["x_text"].endswith(".000100Z")
    tiny = plot(np.array(['2026-01-01T00:00:00.000100', '2026-01-01T00:00:00.000900'], dtype='datetime64[us]'), [0, 2])
    coordinates = plot_x_coordinates(tiny.signals[0].x.to_numpy())
    midpoint = float((coordinates[0] + coordinates[1]) / 2)
    result = probes.query_probe(tiny, request(position=midpoint, x=(float(coordinates[0] - 1), float(coordinates[1] + 1))))
    assert result['total'] == 1 and result['rows'][0]['kind'] == 'interpolated'
    assert result['rows'][0]['y'] == pytest.approx(1)


def test_interpolation_handles_opposing_extreme_finite_coordinates():
    value = plot([-1e308, 1e308], [-1e308, 1e308])
    result = probes.query_probe(value, request(position=0, x=(-1e308, 1e308), y=(-1e308, 1e308)))
    assert result['rows'][0]['y'] == 0


def test_representation_visibility_and_marker_only_sources():
    value = plot([0, 1, 2], [0, 1, 2])
    hidden_line = probes.query_probe(value, request(), visible_lines=set(), visible_signals={"signal-0"})
    assert hidden_line["counts"] == [{"signal": "signal-0", "count": 0, "status": "no_line"}]
    assert probes.query_probe(value, request(), visible_signals=set())["counts"] == []
    markers = replace(value, settings=replace(value.settings, line_styles=(0,)))
    assert probes.query_probe(markers, request())["total"] == 0
    assert probes.query_probe(markers, request(method="nearest"))["total"] == 1


def test_paging_counts_all_million_segments_without_materializing_rows():
    n = 1_000_000
    value = plot(np.arange(n, dtype=float), np.arange(n) % 2)
    tracemalloc.start()
    result = probes.query_probe(value, request("y", .5, x=(0, n)))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result["total"] == n - 1 and len(result["rows"]) == probes.PROBE_PAGE_SIZE
    assert peak < 32 * 1024**2
    last = probes.query_probe(value, request("y", .5, x=(0, n), page=(n - 2) // 50))
    assert len(last["rows"]) == 49 and last["rows"][-1]["x"] == n - 1.5
    small = plot(np.arange(131), np.arange(131) % 2)
    pages = [probes.query_probe(small, request("y", .5, x=(0, 131), page=i)) for i in range(3)]
    assert [row["sample_start"] for page in pages for row in page["rows"]] == list(range(130))


def test_retirement_and_invalid_requests():
    with pytest.raises(probes.ProbeCancelled):
        probes.query_probe(plot([0, 1], [0, 1]), request(), cancelled=lambda: True)
    for patch in ({"axis": "z"}, {"method": []}, {"position": float("nan")}, {"page": -1},
                  {"revision": True}, {"ranges": {"x": [1, 0], "y": [0, 1]}}):
        with pytest.raises(ValueError):
            probes.ProbeQuery.parse({**request(), **patch})
    for state in ({"positions": {"z": 1}}, {"positions": {"x": True}}, {"active": []}, {"method": "bad"}):
        with pytest.raises(ValueError):
            normalized_probe_state(state)
    with pytest.raises(ValueError):
        normalized_probe_state({"positions": {"y": 0}}, logarithmic_y=True)


def test_million_nearest_ties_and_overlap_are_bounded():
    n = 1_000_000
    value = plot(np.arange(n, dtype=float), np.ones(n))
    tracemalloc.start()
    result = probes.query_probe(value, request('y', 1, 'nearest', x=(0, n), page=(n - 1) // 50))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 32 * 1024**2
    assert result['total'] == n and len(result['rows']) == 50
    assert [row['sample_start'] for row in result['rows']] == list(range(n - 50, n))
    overlap = probes.query_probe(value, request('y', 1, x=(0, n)))
    assert overlap['total'] == overlap['overlaps'] == 1
    assert overlap['rows'][0]['sample_end'] == n - 1


def test_pages_follow_logical_signal_then_source_order():
    value = plot(np.arange(41), np.arange(41) % 2)
    second = replace(value.signals[0], signal_id='second')
    value = replace(value, signals=(value.signals[0], second))
    pages = [probes.query_probe(value, request('y', .5, x=(0, 41), page=page)) for page in (0, 1)]
    rows = [row for page in pages for row in page['rows']]
    assert [row['signal'] for row in rows] == ['signal-0'] * 40 + ['second'] * 40
    assert [row['sample_start'] for row in rows] == list(range(40)) * 2


def test_cancellation_is_checked_between_chunks():
    value = plot(np.arange(200000, dtype=float), np.arange(200000) % 2)
    calls = 0
    def cancelled():
        nonlocal calls
        calls += 1
        return calls == 3
    with pytest.raises(probes.ProbeCancelled):
        probes.query_probe(value, request("y", .5, x=(0, 200000)), cancelled=cancelled)
    assert calls == 3


@pytest.mark.parametrize("axis", ["x", "y"])
def test_chunked_results_match_independent_scalar_geometry(monkeypatch, axis):
    monkeypatch.setattr(probes, "PROBE_CHUNK_SIZE", 3)
    for seed in range(25):
        rng = np.random.default_rng(seed)
        x, y = rng.integers(0, 5, size=(2, 31)).astype(float)
        y[rng.choice(31, 3, replace=False)] = np.nan
        a, b = (x, y) if axis == 'x' else (y, x)
        valid = np.isfinite(x) & np.isfinite(y)
        expected, covered = [], set()
        i = 0
        while i < len(x) - 1:
            if valid[i] and valid[i + 1] and a[i] == a[i + 1] == 2:
                start = i
                while i < len(x) - 1 and valid[i] and valid[i + 1] and a[i] == a[i + 1] == 2:
                    i += 1
                covered.update(range(start, i + 1))
                lo, hi = max(.5, min(b[start:i + 1])), min(3.5, max(b[start:i + 1]))
                if lo <= hi:
                    expected.append(('overlap', start, i, lo, hi))
            else:
                i += 1
        vertices = set()
        for i in range(len(x) - 1):
            if not valid[i] or not valid[i + 1] or a[i] == a[i + 1]:
                continue
            t = (2 - a[i]) / (a[i + 1] - a[i])
            opposite = (1 - t) * b[i] + t * b[i + 1]
            if not 0 <= t <= 1 or not .5 <= opposite <= 3.5:
                continue
            if t in (0, 1):
                index = i if t == 0 else i + 1
                if index not in covered and index not in vertices:
                    vertices.add(index); expected.append(('exact', index, index, b[index], b[index]))
            else:
                expected.append(('interpolated', i, i + 1, opposite, opposite))
        expected.sort(key=lambda row: row[1])
        bounds = {'x': (.5, 3.5), 'y': (.5, 3.5)}
        result = probes.query_probe(plot(x, y), request(axis, 2, **bounds))
        other = 'y' if axis == 'x' else 'x'
        actual = [(r['kind'], r['sample_start'], r['sample_end'], r[other], r.get(other + '_end', r[other])) for r in result['rows']]
        assert len(actual) == result['total'] == len(expected), (seed, axis, actual, expected)
        for left, right in zip(actual, expected):
            assert left[:3] == right[:3], (seed, axis, left, right)
            assert left[3:] == pytest.approx(right[3:])
