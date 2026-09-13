# Purpose: Verify canonical selections and bounded live transport in the XY demo.
# Map: docs/agent_maps/feature_routes/plotter_nodes.md
# Tests: tests/test_xy_interactive_showcase.py
from __future__ import annotations

import base64
import unittest

import numpy as np

from scripts import showcase_xy_interactive as demo


class XYInteractiveShowcaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        demo.load_dependencies()

    def test_selection_uses_canonical_coordinates_and_bounded_preview(self):
        state = demo.ShowcaseState()
        state.initialize("selections", 0)
        x, y = demo.scatter_data(6000)
        expected = np.flatnonzero((x >= -1) & (x <= 1) & (y >= -1) & (y <= 1))
        events = state.message("selections", 0, {
            "type": "select", "seq": 71, "x0": -1, "x1": 1, "y0": -1, "y1": 1})
        summary = events[0]["value"]
        self.assertEqual(summary["count"], len(expected))
        self.assertEqual(len(summary["rows"]), demo.PREVIEW_LIMIT)
        self.assertAlmostEqual(summary["traces"][0]["x_mean"], x[expected].mean())
        self.assertAlmostEqual(summary["traces"][0]["y_mean"], y[expected].mean())
        for row, index in zip(summary["rows"], expected):
            self.assertEqual((row["index"], row["x"], row["y"]), (index, x[index], y[index]))
        reply = events[-1]
        self.assertEqual(reply["message"]["seq"], 71)
        mask = np.frombuffer(base64.b64decode(reply["buffers"][0]), dtype=np.uint32)
        np.testing.assert_array_equal(mask, expected)

    def test_lasso_and_empty_selection(self):
        state = demo.ShowcaseState()
        state.initialize("selections", 0)
        x, y = demo.scatter_data(6000)
        # Axis-aligned polygon has an independently calculable membership predicate.
        events = state.message("selections", 0, {"type": "select_polygon", "seq": 5,
                               "points": [[-1, -1], [1, -1], [1, 1], [-1, 1]]})
        self.assertEqual(events[0]["value"]["count"],
                         np.count_nonzero((x > -1) & (x < 1) & (y > -1) & (y < 1)))
        self.assertIsNotNone(state.figures["selections"].view_state()["selection"])
        cleared = state.message("selections", 0, {"type": "select_clear", "seq": 7})
        self.assertEqual(cleared[0]["value"]["count"], 0)
        self.assertEqual(cleared[0]["value"]["rows"], [])
        self.assertEqual(cleared[-1]["message"]["seq"], 7)
        self.assertEqual(cleared[-1]["message"]["traces"], [])
        self.assertIsNone(state.figures["selections"].view_state()["selection"])
        events = state.message("selections", 0, {"type": "select", "seq": 6,
                               "x0": 100, "x1": 101, "y0": 100, "y1": 101})
        self.assertEqual(events[0]["value"], {
            "count": 0, "traces": [], "rows": [], "preview_limit": demo.PREVIEW_LIMIT})
        self.assertEqual(events[-1]["message"]["total"], 0)

    def test_density_selects_full_million_rows_and_keeps_reply_sequence(self):
        state = demo.ShowcaseState()
        mount = state.initialize("large", 0)[0]
        self.assertEqual(mount["spec"]["traces"][0]["tier"], "density")
        self.assertEqual(mount["spec"]["traces"][0]["n_points"], 1_000_000)
        events = state.message("large", 0, {"type": "select", "seq": 42,
                               "x0": -100, "x1": 100, "y0": -100, "y1": 100})
        self.assertEqual(events[0]["value"]["count"], 1_000_000)
        self.assertEqual(len(events[0]["value"]["rows"]), demo.PREVIEW_LIMIT)
        self.assertEqual(events[-1]["message"]["seq"], 42)
        drill = state.message("large", 0, {"type": "density_view", "seq": 91,
                              "trace": 0, "x0": 0.1, "x1": 0.2, "y0": 1.5,
                              "y1": 1.6, "w": 512, "h": 384})
        self.assertEqual(drill[-1]["message"]["type"], "density_update")
        self.assertEqual(drill[-1]["message"]["seq"], 91)

    def test_stream_append_order_cap_reset_and_stale_generation(self):
        state = demo.ShowcaseState(1000)
        state.initialize("streaming", 0)
        state.activate("streaming")
        state.control_stream("start", 0)
        sequences = []
        while state.running:
            update, status = state.tick()
            sequences.append(update["spec"]["append"]["seq"])
            self.assertTrue(update["spec"]["interaction"]["_transport_view_change"])
        self.assertEqual(len(sequences), 199)
        self.assertEqual(sequences, sorted(set(sequences)))
        self.assertEqual(status["count"], demo.STREAM_LIMIT)
        self.assertFalse(status["running"])
        self.assertEqual(state.tick(), [])
        trace = state.figures["stream"].traces[0]
        x, y = demo.signal_data(0, demo.STREAM_LIMIT)
        np.testing.assert_array_equal(trace.x.values, x)
        np.testing.assert_array_equal(trace.y.values, y)
        self.assertFalse(state.control_stream("start", 0)[0]["running"])
        state.initialize("streaming", 1)
        self.assertEqual(state.stream_count, demo.STREAM_BLOCK)
        self.assertFalse(state.running)
        self.assertEqual(state.initialize("streaming", 0), [])
        self.assertEqual(state.control_stream("start", 0), [])
        self.assertEqual(state.message("stream", 0, {"type": "select_clear"}), [])

    def test_lazy_loading_and_pause_on_tab_change(self):
        state = demo.ShowcaseState(23)
        self.assertEqual(state.figures, {})
        state.initialize("signals", 0)
        self.assertEqual(set(state.figures), {"signals"})
        linked = state.initialize("linked", 0)
        for event in linked:
            self.assertEqual(event["spec"]["interaction"]["link_group"], "showcase-time")
            self.assertEqual(event["spec"]["interaction"]["link_axes"], ["x"])
        state.initialize("streaming", 0)
        self.assertFalse(state.control_stream("start", 0)[0]["running"])
        state.activate("streaming")
        self.assertTrue(state.control_stream("start", 0)[0]["running"])
        self.assertFalse(state.activate("signals")[0]["running"])
        self.assertEqual(state.tick(), [])


if __name__ == "__main__":
    unittest.main()
