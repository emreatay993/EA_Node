from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.decorators import in_port, node_type, out_port
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import ExecutionContext, NodeResult
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_REPO_ROOT = Path(__file__).resolve().parents[1]


@node_type(
    type_id="tests.flow_edge_label_node",
    display_name="Flow Edge Label Node",
    category="Tests",
    icon="branch",
    ports=(
        in_port("flow_in", kind="flow"),
        out_port("flow_out", kind="flow"),
    ),
    properties=(),
    runtime_behavior="passive",
    surface_family="annotation",
    surface_variant="sticky_note",
)
class _FlowEdgeLabelNode:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


def _build_registry() -> NodeRegistry:
    registry = build_default_registry()
    registry.register(_FlowEdgeLabelNode)
    return registry


class FlowEdgeLabelPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = _build_registry()
        self.model = GraphModel()
        self.workspace = self.model.active_workspace
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace.workspace_id)

    def test_flow_edge_payload_normalizes_render_metadata(self) -> None:
        source_id = self.scene.add_node_from_type("tests.flow_edge_label_node", 20.0, 20.0)
        target_id = self.scene.add_node_from_type("tests.flow_edge_label_node", 340.0, 110.0)
        edge_id = self.scene.add_edge(source_id, "flow_out", target_id, "flow_in")
        self.workspace.edges[edge_id].label = "Primary path"
        self.workspace.edges[edge_id].visual_style = {
            "stroke": "dashed",
            "stroke_color": "#335577",
            "stroke_width": "3.5",
            "arrow": {"kind": "open"},
            "label_text_color": "#f0f4fb",
            "label_background_color": "#223344",
        }

        self.scene.refresh_workspace_from_model(self.workspace.workspace_id)

        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]
        self.assertEqual(edge_payload["edge_family"], "flow")
        self.assertEqual(edge_payload["label"], "Primary path")
        self.assertEqual(
            edge_payload["flow_style"],
            {
                "stroke_color": "#335577",
                "stroke_width": 3.5,
                "stroke_pattern": "dashed",
                "arrow_head": "open",
                "label_text_color": "#f0f4fb",
                "label_background_color": "#223344",
            },
        )

    def test_non_flow_edges_keep_standard_family_and_empty_flow_style(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 260.0, 0.0)
        edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")

        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]
        self.assertEqual(edge_payload["edge_family"], "standard")
        self.assertEqual(edge_payload["flow_style"], {})
        self.assertEqual(edge_payload["source_port_kind"], "exec")
        self.assertEqual(edge_payload["target_port_kind"], "exec")


class FlowEdgeLabelQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.nodes.decorators import in_port, node_type, out_port
            from ea_node_editor.nodes.types import ExecutionContext, NodeResult
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            @node_type(
                type_id="tests.flow_edge_label_probe_node",
                display_name="Flow Edge Label Probe",
                category="Tests",
                icon="branch",
                ports=(in_port("flow_in", kind="flow"), out_port("flow_out", kind="flow")),
                properties=(),
                runtime_behavior="passive",
                surface_family="annotation",
                surface_variant="sticky_note",
            )
            class _FlowEdgeLabelProbeNode:
                def execute(self, _ctx: ExecutionContext) -> NodeResult:
                    return NodeResult(outputs={})

            def build_registry():
                registry = build_default_registry()
                registry.register(_FlowEdgeLabelProbeNode)
                return registry

            def named_child_items(root, object_name):
                matches = []

                def visit(item):
                    if not isinstance(item, QQuickItem):
                        return
                    if item.objectName() == object_name:
                        matches.append(item)
                    for child in item.childItems():
                        visit(child)

                visit(root)
                return matches

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))

            graph_canvas_qml_path = Path.cwd() / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml"

            component = QQmlComponent(engine, QUrl.fromLocalFile(str(graph_canvas_qml_path)))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError(f"Failed to load GraphCanvas.qml:\\n{errors}")

            model = GraphModel()
            scene = GraphSceneBridge()
            scene.set_workspace(model, build_registry(), model.active_workspace.workspace_id)
            source_id = scene.add_node_from_type("tests.flow_edge_label_probe_node", 40.0, 30.0)
            target_id = scene.add_node_from_type("tests.flow_edge_label_probe_node", 380.0, 130.0)
            edge_id = scene.add_edge(source_id, "flow_out", target_id, "flow_in")
            scene.set_edge_label(edge_id, "Primary path")
            scene.set_edge_visual_style(
                edge_id,
                {
                    "stroke_pattern": "dashed",
                    "arrow_head": "open",
                    "stroke_width": 3,
                    "stroke_color": "#335577",
                    "label_text_color": "#f0f4fb",
                    "label_background_color": "#223344",
                },
            )

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)
            view.centerOn(240.0, 90.0)

            canvas = component.createWithInitialProperties(
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                }
            ) if hasattr(component, "createWithInitialProperties") else component.create()
            if canvas is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError(f"Failed to instantiate GraphCanvas.qml:\\n{errors}")
            if not hasattr(component, "createWithInitialProperties"):
                canvas.setProperty("sceneBridge", scene)
                canvas.setProperty("viewBridge", view)
                canvas.setProperty("width", 1280.0)
                canvas.setProperty("height", 720.0)
            app.processEvents()
            edge_layer = canvas.findChild(QObject, "graphCanvasEdgeLayer")
            if edge_layer is None:
                raise AssertionError("graphCanvasEdgeLayer not found")
            """
        ) + "\n" + textwrap.dedent(body)
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            details = "\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            self.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")

    def test_graph_canvas_flow_edge_labels_render_and_reduce_at_low_zoom(self) -> None:
        self._run_qml_probe(
            "flow-edge-label-zoom",
            """
            labels = named_child_items(edge_layer, "graphEdgeFlowLabelItem")
            assert len(labels) == 1
            label_item = labels[0]
            assert label_item.isVisible()
            assert label_item.property("labelMode") == "pill"
            label_text = label_item.findChild(QObject, "graphEdgeFlowLabelText")
            label_pill = label_item.findChild(QObject, "graphEdgeFlowLabelPill")
            assert label_text is not None
            assert label_pill is not None
            assert label_text.property("text") == "Primary path"
            assert bool(label_pill.property("visible"))
            assert bool(label_item.property("hitTestMatches"))

            view.set_zoom(0.7)
            app.processEvents()
            assert label_item.isVisible()
            assert label_item.property("labelMode") == "text"
            assert not bool(label_pill.property("visible"))

            view.set_zoom(0.5)
            app.processEvents()
            assert label_item.property("labelMode") == "hidden"
            assert not label_item.isVisible()

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_flow_edge_labels_cull_offscreen_edges_until_viewport_moves(self) -> None:
        self._run_qml_probe(
            "flow-edge-label-viewport-cull",
            """
            off_source_id = scene.add_node_from_type("tests.flow_edge_label_probe_node", 4200.0, 3300.0)
            off_target_id = scene.add_node_from_type("tests.flow_edge_label_probe_node", 4680.0, 3420.0)
            off_edge_id = scene.add_edge(off_source_id, "flow_out", off_target_id, "flow_in")
            scene.set_edge_label(off_edge_id, "Offscreen path")
            scene.set_edge_visual_style(
                off_edge_id,
                {
                    "stroke_pattern": "dashed",
                    "arrow_head": "open",
                    "stroke_width": 3,
                    "stroke_color": "#335577",
                    "label_text_color": "#f0f4fb",
                    "label_background_color": "#223344",
                },
            )
            app.processEvents()

            labels = named_child_items(edge_layer, "graphEdgeFlowLabelItem")
            assert len(labels) == 2
            labels_by_text = {item.property("labelText"): item for item in labels}
            assert set(labels_by_text) == {"Primary path", "Offscreen path"}

            visible_label = labels_by_text["Primary path"]
            culled_label = labels_by_text["Offscreen path"]
            assert visible_label.isVisible()
            assert not culled_label.isVisible()
            assert bool(culled_label.property("culledByViewport"))
            assert culled_label.property("geometry") is None
            assert culled_label.property("labelAnchor") is None
            assert not bool(culled_label.property("hitTestMatches"))

            view.centerOn(4440.0, 3360.0)
            app.processEvents()

            assert culled_label.isVisible()
            assert not bool(culled_label.property("culledByViewport"))
            assert culled_label.property("geometry") is not None
            assert culled_label.property("labelAnchor") is not None
            assert not visible_label.isVisible()

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_flow_edge_labels_hide_during_max_performance_interaction_and_recover(self) -> None:
        self._run_qml_probe(
            "flow-edge-label-max-performance",
            """
            from tests.qt_wait import wait_for_condition_or_raise

            canvas.setProperty(
                "mainWindowBridge",
                {
                    "graphics_show_grid": True,
                    "graphics_show_minimap": True,
                    "graphics_minimap_expanded": True,
                    "graphics_node_shadow": True,
                    "graphics_shadow_strength": 70,
                    "graphics_shadow_softness": 50,
                    "graphics_shadow_offset": 4,
                    "graphics_performance_mode": "max_performance",
                    "snap_to_grid_enabled": False,
                    "snap_grid_size": 20.0,
                },
            )
            app.processEvents()

            labels = named_child_items(edge_layer, "graphEdgeFlowLabelItem")
            assert len(labels) == 1
            label_item = labels[0]
            assert canvas.property("resolvedGraphicsPerformanceMode") == "max_performance"
            assert label_item.isVisible()
            assert label_item.property("labelMode") == "pill"

            canvas.beginViewportInteraction()
            canvas.finishViewportInteractionSoon()
            app.processEvents()

            assert bool(canvas.property("transientDegradedWindowActive"))
            assert bool(canvas.property("edgeLabelSimplificationActive"))
            assert label_item.property("labelMode") == "hidden"
            assert not label_item.isVisible()
            assert not bool(label_item.property("hitTestMatches"))

            wait_for_condition_or_raise(
                lambda: not bool(canvas.property("transientDegradedWindowActive")),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for max-performance flow label recovery.",
            )
            assert not bool(canvas.property("edgeLabelSimplificationActive"))
            assert label_item.isVisible()
            assert label_item.property("labelMode") == "pill"
            assert bool(label_item.property("hitTestMatches"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )


if __name__ == "__main__":
    unittest.main()
