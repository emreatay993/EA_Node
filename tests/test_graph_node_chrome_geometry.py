"""Render actual QML JavaScript paths and check their analytic set membership.

Purpose: Prove unioned cutouts, inside borders, and retained hatch geometry.
Map: docs/agent_maps/subsystems/graph_canvas.md
Tests: tests/test_graph_node_chrome_geometry.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random
import unittest

from PyQt6.QtCore import QByteArray, QCoreApplication, QRectF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtQml import QJSEngine
from PyQt6.QtSvg import QSvgRenderer


SOURCE = Path(__file__).resolve().parents[1] / "ea_node_editor/ui_qml/components/graph/GraphNodeChromeGeometry.js"


class GraphNodeChromeGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])
        cls.engine = QJSEngine()
        result = cls.engine.evaluate(SOURCE.read_text(encoding="utf-8").replace(".pragma library", ""), str(SOURCE))
        if result.isError():
            raise AssertionError(result.toString())

    def evaluate(self, expression):
        result = self.engine.evaluate(expression)
        self.assertFalse(result.isError(), result.toString())
        return result.toVariant()

    def geometry(self, width=100, height=80, radius=12, border=2, centers=None):
        args = json.dumps([width, height, radius, border, centers or {}, 9])
        return self.evaluate(f"build.apply(null, {args})")

    @staticmethod
    def render(path, width, height):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
               f'<path d="{path}" fill="white" fill-rule="evenodd"/></svg>')
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        if not renderer.isValid():
            raise AssertionError("Invalid generated SVG")
        image = QImage(math.ceil(width * 2), math.ceil(height * 2), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter, QRectF(0, 0, width * 2, height * 2))
        painter.end()
        return image

    @staticmethod
    def clearance(x, y, width, height, radius, centers, inset=0):
        """Independent signed distance oracle: rounded box minus circle union."""
        if width <= inset * 2 or height <= inset * 2:
            return -math.inf
        radius = max(0, min(radius, width / 2, height / 2) - inset)
        qx = abs(x - width / 2) - (width / 2 - inset - radius)
        qy = abs(y - height / 2) - (height / 2 - inset - radius)
        result = radius - (math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0))
        for side, values in centers.items():
            cx = 0 if side == "left" else width
            for cy in values:
                result = min(result, math.hypot(x - cx, y - cy) - 9 - inset)
        return result

    def assert_membership(self, width, height, radius, border, centers):
        geometry = self.geometry(width, height, radius, border, centers)
        fill = self.render(geometry["fillPath"], width, height)
        outline = self.render(geometry["borderPath"], width, height)
        checked = 0
        for py in range(fill.height()):
            for px in range(fill.width()):
                x, y = (px + 0.5) / 2, (py + 0.5) / 2
                outer = self.clearance(x, y, width, height, radius, centers)
                inner = self.clearance(x, y, width, height, radius, centers, border)
                if abs(outer) < 0.6 or abs(inner) < 0.6:
                    continue  # Antialiasing coverage at boundaries is not binary.
                self.assertEqual(fill.pixelColor(px, py).alpha() > 127, outer > 0,
                                 ("fill", width, height, radius, centers, x, y, geometry))
                self.assertEqual(outline.pixelColor(px, py).alpha() > 127, outer > 0 >= inner,
                                 ("border", width, height, radius, centers, x, y, geometry))
                checked += 1
        self.assertGreater(checked, 10)

    def test_regular_opposite_ports_and_inside_border(self):
        self.assert_membership(100, 80, 12, 2, {"left": [24, 52], "right": [38]})

    def test_overlapping_and_tangent_cutouts_are_union_not_parity(self):
        self.assert_membership(70, 80, 12, 2, {"left": [22, 30, 48, 66], "right": [30, 40]})

    def test_cutouts_intersect_rounded_corners_and_pill_ends(self):
        self.assert_membership(96, 30, 50, 2.4, {"left": [2, 15, 28], "right": [15]})
        self.assert_membership(70, 70, 24, 3, {"left": [5, 20, 65], "right": [8, 54]})

    def test_opposite_cutouts_can_disconnect_the_body(self):
        geometry = self.geometry(14, 70, 6, 1.5, {"left": [35], "right": [35]})
        self.assertGreaterEqual(geometry["fillPath"].count("M"), 2)
        self.assert_membership(14, 70, 6, 1.5, {"left": [35], "right": [35]})

    def test_excessive_border_and_zero_corner(self):
        self.assert_membership(40, 30, 0, 50, {"left": [15]})
        self.assert_membership(40, 30, 0, 0, {"left": [15]})

    def test_duplicates_and_nonfinite_centers_are_ignored(self):
        expected = self.geometry(100, 80, 12, 2, {"left": [24], "right": [30]})
        actual = self.evaluate('build(100,80,12,2,{left:[24,24,NaN,Infinity],right:[30,30,-Infinity]},9)')
        self.assertEqual(actual, expected)

    def test_nonpositive_or_nonfinite_dimensions_have_no_geometry(self):
        for width, height in [(0, 20), (-2, 20), (20, 0), (20, -3)]:
            self.assertEqual(self.geometry(width, height), {"fillPath": "", "borderPath": ""})
        self.assertEqual(self.evaluate('build(NaN,80,12,2,{},9).fillPath'), "")

    def test_external_tangencies_and_containing_holes(self):
        self.assert_membership(30, 30, 0, 2, {"left": [-9, 39], "right": [15]})
        self.assert_membership(8, 8, 4, 1, {"left": [4], "right": [4]})

    def test_randomized_geometry_stays_closed(self):
        rng = random.Random(1337)
        for _ in range(100):
            width, height = rng.uniform(4, 240), rng.uniform(4, 200)
            centers = {side: [rng.uniform(-10, height + 10) for _ in range(rng.randrange(8))]
                       for side in ("left", "right")}
            geometry = self.geometry(width, height, rng.uniform(0, 80), rng.uniform(0.1, 12), centers)
            self.assertNotIn("NaN", geometry["fillPath"])
            self.assertNotIn("Infinity", geometry["borderPath"])

    def test_hatch_segments_stay_within_silhouette(self):
        path = self.evaluate('hatch(100,80,12,{left:[8,30,38,65],right:[20,55]},9,8)')
        self.assertTrue(path)
        centers = {"left": [8, 30, 38, 65], "right": [20, 55]}
        for segment in path.split("M")[1:]:
            start, end = segment.strip().split("L")
            x0, y0 = map(float, start.split())
            x1, y1 = map(float, end.split())
            for fraction in [0.05, 0.25, 0.5, 0.75, 0.95]:
                x, y = x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * fraction
                self.assertGreaterEqual(self.clearance(x, y, 100, 80, 12, centers), -1e-5)


if __name__ == "__main__":
    unittest.main()
