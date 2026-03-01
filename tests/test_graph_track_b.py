from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication, QGraphicsView

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.scene import NodeGraphScene
from ea_node_editor.graph.view import NodeGraphView
from ea_node_editor.nodes.bootstrap import build_default_registry


def _edge_endpoints(scene: NodeGraphScene, edge_id: str) -> tuple[QPointF, QPointF]:
    edge_item = scene.edge_item(edge_id)
    if edge_item is None:
        raise AssertionError(f"Missing edge item: {edge_id}")
    path = edge_item.path()
    start = path.elementAt(0)
    end = path.elementAt(path.elementCount() - 1)
    return QPointF(start.x, start.y), QPointF(end.x, end.y)


class GraphModelTrackBTests(unittest.TestCase):
    def test_add_move_connect_remove_node_operations(self) -> None:
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        source = model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
        target = model.add_node(workspace_id, "core.end", "End", 300.0, 80.0)

        model.set_node_position(workspace_id, source.node_id, 25.0, 45.0)
        moved = model.project.workspaces[workspace_id].nodes[source.node_id]
        self.assertEqual((moved.x, moved.y), (25.0, 45.0))

        edge = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        duplicate = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        self.assertEqual(edge.edge_id, duplicate.edge_id)
        self.assertEqual(len(model.project.workspaces[workspace_id].edges), 1)

        model.remove_node(workspace_id, source.node_id)
        workspace = model.project.workspaces[workspace_id]
        self.assertNotIn(source.node_id, workspace.nodes)
        self.assertEqual(workspace.edges, {})

    def test_add_edge_rejects_unknown_node_ids(self) -> None:
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        node = model.add_node(workspace_id, "core.end", "End", 0.0, 0.0)
        with self.assertRaises(KeyError):
            model.add_edge(workspace_id, "node_missing", "exec_out", node.node_id, "exec_in")
        with self.assertRaises(KeyError):
            model.add_edge(workspace_id, node.node_id, "exec_out", "node_missing", "exec_in")


class GraphSceneTrackBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = NodeGraphScene()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)
        self.view = NodeGraphView()
        self.view.setScene(self.scene)
        self.view.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.view.close()
        self.scene.clear()
        self.app.processEvents()

    def test_selection_signal_reports_select_and_clear(self) -> None:
        node_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        events: list[str] = []
        self.scene.node_selected.connect(events.append)

        self.scene.focus_node(node_id)
        self.app.processEvents()
        self.assertEqual(events[-1], node_id)

        self.scene.clearSelection()
        self.app.processEvents()
        self.assertEqual(events[-1], "")

    def test_connect_move_and_remove_keep_model_and_scene_in_sync(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 40.0)
        edge_id = self.scene.connect_nodes(source_id, target_id)
        self.app.processEvents()

        source_item = self.scene.node_item(source_id)
        target_item = self.scene.node_item(target_id)
        self.assertIsNotNone(source_item)
        self.assertIsNotNone(target_item)
        if source_item is None or target_item is None:
            self.fail("Expected node items to exist")
        before_start, _ = _edge_endpoints(self.scene, edge_id)

        source_item.setPos(120.0, 90.0)
        self.app.processEvents()

        workspace = self.model.project.workspaces[self.workspace_id]
        source_model = workspace.nodes[source_id]
        self.assertAlmostEqual(source_model.x, 120.0, places=4)
        self.assertAlmostEqual(source_model.y, 90.0, places=4)

        moved_start, moved_end = _edge_endpoints(self.scene, edge_id)
        expected_start = source_item.port_scene_pos("exec_out")
        expected_end = target_item.port_scene_pos("exec_in")
        self.assertNotEqual((before_start.x(), before_start.y()), (moved_start.x(), moved_start.y()))
        self.assertAlmostEqual(moved_start.x(), expected_start.x(), places=4)
        self.assertAlmostEqual(moved_start.y(), expected_start.y(), places=4)
        self.assertAlmostEqual(moved_end.x(), expected_end.x(), places=4)
        self.assertAlmostEqual(moved_end.y(), expected_end.y(), places=4)

        self.scene.remove_edge(edge_id)
        self.app.processEvents()
        self.assertNotIn(edge_id, workspace.edges)
        self.assertIsNone(self.scene.edge_item(edge_id))

        new_edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.scene.remove_node(source_id)
        self.app.processEvents()
        self.assertNotIn(source_id, workspace.nodes)
        self.assertNotIn(new_edge_id, workspace.edges)
        self.assertIsNone(self.scene.node_item(source_id))
        self.assertIsNone(self.scene.edge_item(new_edge_id))

    def test_collapse_expand_reroutes_edge_to_current_geometry(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 30.0)
        edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        source_item = self.scene.node_item(source_id)
        target_item = self.scene.node_item(target_id)
        self.assertIsNotNone(source_item)
        self.assertIsNotNone(target_item)
        if source_item is None or target_item is None:
            self.fail("Expected node items to exist")

        expanded_start = source_item.port_scene_pos("exec_out")
        self.scene.set_node_collapsed(source_id, True)
        self.app.processEvents()

        self.assertTrue(source_item.node.collapsed)
        self.assertLess(source_item.boundingRect().width(), 150.0)
        collapsed_start, collapsed_end = _edge_endpoints(self.scene, edge_id)
        expected_collapsed_start = source_item.port_scene_pos("exec_out")
        expected_collapsed_end = target_item.port_scene_pos("exec_in")
        self.assertNotEqual((expanded_start.x(), expanded_start.y()), (collapsed_start.x(), collapsed_start.y()))
        self.assertAlmostEqual(collapsed_start.x(), expected_collapsed_start.x(), places=4)
        self.assertAlmostEqual(collapsed_start.y(), expected_collapsed_start.y(), places=4)
        self.assertAlmostEqual(collapsed_end.x(), expected_collapsed_end.x(), places=4)
        self.assertAlmostEqual(collapsed_end.y(), expected_collapsed_end.y(), places=4)

        self.scene.set_node_collapsed(source_id, False)
        self.app.processEvents()
        expanded_again_start, expanded_again_end = _edge_endpoints(self.scene, edge_id)
        self.assertFalse(source_item.node.collapsed)
        self.assertAlmostEqual(expanded_again_start.x(), source_item.port_scene_pos("exec_out").x(), places=4)
        self.assertAlmostEqual(expanded_again_start.y(), source_item.port_scene_pos("exec_out").y(), places=4)
        self.assertAlmostEqual(expanded_again_end.x(), target_item.port_scene_pos("exec_in").x(), places=4)
        self.assertAlmostEqual(expanded_again_end.y(), target_item.port_scene_pos("exec_in").y(), places=4)

    def test_exposed_port_changes_refresh_geometry_and_edge_path_immediately(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.python_script", 320.0, 30.0)
        edge_id = self.scene.add_edge(source_id, "trigger", target_id, "payload")
        source_item = self.scene.node_item(source_id)
        self.assertIsNotNone(source_item)
        if source_item is None:
            self.fail("Expected source node item to exist")

        self.app.processEvents()
        before_height = source_item.boundingRect().height()
        before_start, _ = _edge_endpoints(self.scene, edge_id)

        self.scene.set_exposed_port(source_id, "exec_out", False)
        self.app.processEvents()

        after_height = source_item.boundingRect().height()
        after_start, _ = _edge_endpoints(self.scene, edge_id)
        expected_after_start = source_item.port_scene_pos("trigger")
        self.assertLess(after_height, before_height)
        self.assertNotEqual((before_start.x(), before_start.y()), (after_start.x(), after_start.y()))
        self.assertAlmostEqual(after_start.x(), expected_after_start.x(), places=4)
        self.assertAlmostEqual(after_start.y(), expected_after_start.y(), places=4)

    def test_hiding_connected_port_removes_edges_immediately(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.python_script", 320.0, 30.0)
        edge_id = self.scene.add_edge(source_id, "trigger", target_id, "payload")
        self.app.processEvents()

        self.scene.set_exposed_port(source_id, "trigger", False)
        self.app.processEvents()

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertNotIn(edge_id, workspace.edges)
        self.assertIsNone(self.scene.edge_item(edge_id))

    def test_connect_nodes_uses_only_currently_exposed_ports(self) -> None:
        source_id = self.scene.add_node_from_type("core.constant", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.logger", 320.0, 30.0)
        self.scene.set_exposed_port(source_id, "value", False)
        self.scene.set_exposed_port(source_id, "as_text", False)
        self.app.processEvents()

        source_item = self.scene.node_item(source_id)
        self.assertIsNotNone(source_item)
        if source_item is None:
            self.fail("Expected source node item to exist")
        _in_ports, out_ports = source_item.visible_ports()
        self.assertEqual(out_ports, [])

        with self.assertRaises(ValueError):
            self.scene.connect_nodes(source_id, target_id)


class GraphViewPerformanceTrackBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_view_and_scene_apply_perf_related_defaults(self) -> None:
        scene = NodeGraphScene()
        view = NodeGraphView()
        view.setScene(scene)
        self.app.processEvents()

        self.assertEqual(
            view.viewportUpdateMode(),
            QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate,
        )
        flags = view.optimizationFlags()
        self.assertTrue(bool(flags & QGraphicsView.OptimizationFlag.DontSavePainterState))
        self.assertTrue(bool(flags & QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing))
        rect = scene.sceneRect()
        self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), (-5000.0, -5000.0, 10000.0, 10000.0))


if __name__ == "__main__":
    unittest.main()
