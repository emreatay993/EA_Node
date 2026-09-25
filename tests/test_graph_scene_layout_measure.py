# Purpose: Offscreen scene tests that align and distribute measure nodes as drawn (settings bands, rows a view hides), that a resize commits the size the canvas draws, and that Set Same Height keeps the frame custom sizes are stored in.
# Map: feature_routes/graph_actions_and_context_menus
# Tests: tests/test_graph_scene_layout_measure.py
from __future__ import annotations

import unittest

from ea_node_editor.ui_qml.graph_geometry.standard_metrics import uses_content_sizing
from ea_node_editor.ui_qml.graph_surface_metrics import resolved_node_surface_size
from tests.automation.harness import build_context

PLOT = "plot.signal"
LOGGER = "core.logger"
INTERVAL = "math.construct_interval"
WEB_VIEWER = "web.page_viewer"


class _LayoutMeasureCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene

    def add(self, type_id: str, x: float, y: float) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def select(self, *node_ids: str) -> None:
        self.scene.clear_selection()
        for index, node_id in enumerate(node_ids):
            self.scene.select_node(node_id, index > 0)

    def top(self, node_id: str) -> float:
        return self.scene.node_bounds(node_id).y()

    def bottom(self, node_id: str) -> float:
        return self.scene.node_bounds(node_id).bottom()

    def height(self, node_id: str) -> float:
        return self.scene.node_bounds(node_id).height()

    def drawn_rect(self, node_id: str) -> tuple[float, float, float, float]:
        bounds = self.scene.node_bounds(node_id)
        return (bounds.x(), bounds.y(), bounds.width(), bounds.height())

    def stored_height(self, node_id: str) -> float | None:
        return self.context.active_workspace().nodes[node_id].custom_height

    def settings_band_height(self, node_id: str) -> float:
        row = next(row for row in self.scene.nodes_model if row["node_id"] == node_id)
        return float(row["settings_band"]["height"])

    def surface_measure_height(self, node_id: str) -> float:
        """The plain surface measure, which leaves out the settings band and ignores the rows a view hides."""
        workspace = self.context.active_workspace()
        node = workspace.nodes[node_id]
        return float(resolved_node_surface_size(node, self.context.registry.get_spec(node.type_id), workspace.nodes)[1])


class DrawnSizeAlignAndDistributeTests(_LayoutMeasureCase):
    """Align and distribute place nodes by the rectangle the canvas draws, not the plain surface measure."""

    def test_align_bottom_lines_up_the_drawn_bottom_of_a_plot(self) -> None:
        plot = self.add(PLOT, 0, 0)
        logger = self.add(LOGGER, 400, 300)
        self.assertGreater(self.settings_band_height(plot), 0.0)
        self.select(plot, logger)

        self.assertTrue(self.scene.align_selected_nodes("bottom"))

        self.assertAlmostEqual(self.bottom(plot), self.bottom(logger), places=6)

    def test_align_bottom_counts_every_open_plot_settings_group(self) -> None:
        plot = self.add(PLOT, 0, 0)
        for settings_group in self.context.registry.get_spec(PLOT).settings_groups:
            self.assertTrue(self.scene.set_node_settings_group_expanded(plot, settings_group.group_id, True))
        self.assertGreater(self.height(plot) - self.surface_measure_height(plot), 1000.0)
        logger = self.add(LOGGER, 400, 1600)
        self.select(plot, logger)

        self.assertTrue(self.scene.align_selected_nodes("bottom"))

        self.assertAlmostEqual(self.bottom(plot), self.bottom(logger), places=6)

    def test_align_center_y_centres_a_plot_on_its_drawn_height(self) -> None:
        plot = self.add(PLOT, 0, 0)
        logger = self.add(LOGGER, 400, 300)
        self.select(plot, logger)

        self.assertTrue(self.scene.align_selected_nodes("center_y"))

        self.assertAlmostEqual(
            self.scene.node_bounds(plot).center().y(), self.scene.node_bounds(logger).center().y(), places=6
        )

    def test_vertical_distribute_spaces_a_plot_by_its_drawn_height(self) -> None:
        first = self.add(LOGGER, 0, 0)
        plot = self.add(PLOT, 0, 150)
        last = self.add(LOGGER, 0, 700)
        self.select(first, plot, last)

        self.assertTrue(self.scene.distribute_selected_nodes("vertical"))

        self.assertAlmostEqual(self.top(plot) - self.bottom(first), self.top(last) - self.bottom(plot), places=6)
        self.assertEqual((self.top(first), self.top(last)), (0.0, 700.0))

    def test_align_bottom_in_a_view_that_hides_optional_ports_uses_the_shorter_drawn_height(self) -> None:
        interval = self.add(INTERVAL, 0, 0)
        logger = self.add(LOGGER, 400, 300)
        self.assertTrue(self.scene.set_hide_optional_ports(True))
        self.assertLess(self.height(interval), self.surface_measure_height(interval))
        self.select(interval, logger)

        self.assertTrue(self.scene.align_selected_nodes("bottom"))

        self.assertAlmostEqual(self.bottom(interval), self.bottom(logger), places=6)


class DrawnSizeResizeTests(_LayoutMeasureCase):
    """A resize commits the size the canvas draws, although custom heights are stored counting the rows a view hides."""

    def test_resize_in_a_view_that_hides_optional_ports_draws_the_node_at_the_committed_size(self) -> None:
        viewer = self.add(WEB_VIEWER, 0, 0)
        self.assertTrue(self.scene.set_hide_optional_ports(True))

        self.scene.set_node_geometry(viewer, 10.0, 20.0, 420.0, 400.0)

        self.assertEqual(self.drawn_rect(viewer), (10.0, 20.0, 420.0, 400.0))
        stored = self.stored_height(viewer)
        self.assertGreater(stored, 400.0)  # stored counting the hidden rows...
        self.assertTrue(self.scene.set_hide_optional_ports(False))
        self.assertAlmostEqual(self.height(viewer), stored, places=6)  # ...which a view showing them draws

    def test_resize_node_in_a_view_that_hides_optional_ports_draws_the_node_at_the_committed_size(self) -> None:
        viewer = self.add(WEB_VIEWER, 0, 0)
        self.assertTrue(self.scene.set_hide_optional_ports(True))

        self.scene.resize_node(viewer, 420.0, 400.0)

        self.assertEqual(self.drawn_rect(viewer), (0.0, 0.0, 420.0, 400.0))

    def test_every_type_that_keeps_a_custom_height_draws_at_the_committed_size_in_a_view_that_hides_optional_ports(
        self,
    ) -> None:
        # Content-sized types ignore custom sizes; of the rest, only types that keep a committed height are checked.
        type_ids = sorted(spec.type_id for spec in self.context.registry.all_specs() if not uses_content_sizing(spec))
        sized: dict[str, str] = {}
        for index, type_id in enumerate(type_ids):
            node_id = self.add(type_id, (index % 8) * 900.0, (index // 8) * 1200.0)
            x, y, width, height = self.drawn_rect(node_id)
            self.scene.set_node_geometry(node_id, x, y, width + 40.0, height + 300.0)
            if abs(self.height(node_id) - (height + 300.0)) < 1e-6:
                sized[type_id] = node_id
        shown_heights = {type_id: self.height(node_id) for type_id, node_id in sized.items()}
        self.assertTrue(self.scene.set_hide_optional_ports(True))
        rows_hidden = {type_id for type_id, node_id in sized.items() if self.height(node_id) < shown_heights[type_id]}
        self.assertIn(WEB_VIEWER, rows_hidden)

        missed: dict[str, tuple[float, float]] = {}
        for type_id, node_id in sized.items():
            x, y, width, height = self.drawn_rect(node_id)
            target_width, target_height = width + 20.0, height + 100.0
            self.scene.set_node_geometry(node_id, x, y, target_width, target_height)
            _x, _y, drawn_width, drawn_height = self.drawn_rect(node_id)
            if abs(drawn_width - target_width) > 1e-6 or abs(drawn_height - target_height) > 1e-6:
                missed[type_id] = (drawn_width - target_width, drawn_height - target_height)

        self.assertEqual(missed, {})


class SameSizeStoredFrameTests(_LayoutMeasureCase):
    """Set Same Height writes custom sizes, which count the rows a view hides, so it must not use the drawn size."""

    def test_same_height_in_a_view_that_hides_optional_ports_draws_both_nodes_at_the_reference_height(self) -> None:
        reference = self.add(WEB_VIEWER, 0, 0)
        other = self.add(WEB_VIEWER, 600, 0)
        self.scene.set_node_geometry(reference, 0.0, 0.0, self.scene.node_bounds(reference).width(), 400.0)
        self.assertTrue(self.scene.set_hide_optional_ports(True))
        self.assertLess(self.height(reference), 400.0)  # the view draws the sized node shorter by the rows it hides

        self.assertTrue(self.scene.set_selected_same_type_size([reference, other], "height"))

        self.assertAlmostEqual(self.height(other), self.height(reference), places=6)


if __name__ == "__main__":
    unittest.main()
