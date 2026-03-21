from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from ea_node_editor.graph.model import GraphModel, NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

_REPO_ROOT = Path(__file__).resolve().parents[1]


class FlowchartVisualPolishMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def _metrics_for(self, type_id: str):
        spec = self.registry.get_spec(type_id)
        node = NodeInstance(
            node_id=f"node_{type_id.rsplit('.', 1)[-1]}",
            type_id=type_id,
            title=spec.display_name,
            x=20.0,
            y=30.0,
        )
        return node_surface_metrics(node, spec, {node.node_id: node})

    def test_polished_flowchart_variants_use_roomier_layout_metrics(self) -> None:
        decision = self._metrics_for("passive.flowchart.decision")
        document = self._metrics_for("passive.flowchart.document")
        connector = self._metrics_for("passive.flowchart.connector")
        input_output = self._metrics_for("passive.flowchart.input_output")
        predefined = self._metrics_for("passive.flowchart.predefined_process")
        database = self._metrics_for("passive.flowchart.database")

        self.assertEqual((decision.default_width, decision.min_width, decision.min_height), (236.0, 192.0, 128.0))
        self.assertEqual((decision.title_left_margin, decision.title_right_margin), (66.0, 66.0))
        self.assertEqual((document.default_width, document.min_height, document.body_bottom_margin), (228.0, 104.0, 24.0))
        self.assertEqual((connector.default_width, connector.min_width, connector.min_height), (108.0, 92.0, 92.0))
        self.assertEqual((input_output.default_width, input_output.title_left_margin), (236.0, 34.0))
        self.assertEqual((predefined.default_width, predefined.title_left_margin), (236.0, 36.0))
        self.assertEqual((database.default_width, database.min_width, database.min_height), (228.0, 180.0, 128.0))


class FlowchartVisualPolishRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace = self.model.active_workspace
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace.workspace_id)

    def test_vertical_flowchart_edges_prefer_pipe_routes(self) -> None:
        source_id = self.scene.add_node_from_type("passive.flowchart.process", 40.0, 40.0)
        target_id = self.scene.add_node_from_type("passive.flowchart.process", 64.0, 250.0)
        edge_id = self.scene.add_edge(source_id, "flow_out", target_id, "flow_in")

        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]

        self.assertEqual(edge_payload["route"], "pipe")
        self.assertEqual(len(edge_payload["pipe_points"]), 6)
        self.assertGreater(edge_payload["pipe_points"][2]["y"], edge_payload["pipe_points"][0]["y"])

    def test_wide_left_to_right_flowchart_edges_keep_bezier_routes(self) -> None:
        source_id = self.scene.add_node_from_type("passive.flowchart.process", 20.0, 40.0)
        target_id = self.scene.add_node_from_type("passive.flowchart.process", 420.0, 72.0)
        edge_id = self.scene.add_edge(source_id, "flow_out", target_id, "flow_in")

        edge_payload = {item["edge_id"]: item for item in self.scene.edges_model}[edge_id]

        self.assertEqual(edge_payload["route"], "bezier")
        self.assertEqual(edge_payload["pipe_points"], [])

    def test_decision_branch_edges_keep_distinct_lane_biases(self) -> None:
        decision_id = self.scene.add_node_from_type("passive.flowchart.decision", 40.0, 40.0)
        branch_a_target = self.scene.add_node_from_type("passive.flowchart.process", 260.0, 210.0)
        branch_b_target = self.scene.add_node_from_type("passive.flowchart.process", 260.0, 320.0)
        edge_a = self.scene.add_edge(decision_id, "branch_a", branch_a_target, "flow_in")
        edge_b = self.scene.add_edge(decision_id, "branch_b", branch_b_target, "flow_in")

        payload = {item["edge_id"]: item for item in self.scene.edges_model}

        self.assertEqual(payload[edge_a]["route"], "pipe")
        self.assertEqual(payload[edge_b]["route"], "pipe")
        self.assertGreaterEqual(abs(payload[edge_a]["lane_bias"] - payload[edge_b]["lane_bias"]), 20.0)


class FlowchartVisualPolishQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))

            repo_root = Path.cwd()
            components_dir = repo_root / "ea_node_editor" / "ui_qml" / "components"
            graph_canvas_qml_path = components_dir / "GraphCanvas.qml"
            graph_node_host_qml_path = components_dir / "graph" / "GraphNodeHost.qml"

            def create_component(path, initial_properties):
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
                if component.status() != QQmlComponent.Status.Ready:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to load {path.name}:\\n{errors}")
                if hasattr(component, "createWithInitialProperties"):
                    obj = component.createWithInitialProperties(initial_properties)
                else:
                    obj = component.create()
                    for key, value in initial_properties.items():
                        obj.setProperty(key, value)
                if obj is None:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to instantiate {path.name}:\\n{errors}")
                app.processEvents()
                return obj

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

            def flowchart_payload(variant):
                return {
                    "node_id": "node_flowchart_visual_polish",
                    "type_id": "tests.flowchart_visual_polish",
                    "title": "Decision",
                    "display_name": "Decision",
                    "x": 120.0,
                    "y": 120.0,
                    "width": 236.0,
                    "height": 128.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "flowchart",
                    "surface_variant": variant,
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "flow_in",
                            "label": "flow_in",
                            "direction": "in",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "branch_a",
                            "label": "branch_a",
                            "direction": "out",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "branch_b",
                            "label": "branch_b",
                            "direction": "out",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                    ],
                    "inline_properties": [],
                }
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

    def test_flowchart_host_hides_raw_port_labels_and_keeps_port_handles(self) -> None:
        self._run_qml_probe(
            "flowchart-host-polish",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision")},
            )
            assert bool(host.property("isFlowchartSurface"))
            assert not bool(host.property("_useHostChrome"))
            assert bool(host.property("_suppressShadow"))
            assert len(named_child_items(host, "graphNodeInputPortDot")) == 1
            assert len(named_child_items(host, "graphNodeOutputPortDot")) == 2
            assert len(named_child_items(host, "graphNodeInputPortMouseArea")) == 1
            assert len(named_child_items(host, "graphNodeOutputPortMouseArea")) == 2
            assert host.findChild(QObject, "graphFlowchartVectorShape") is not None
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeOutputPortLabel"))
            """,
        )

    def test_flowchart_drop_preview_matches_family_and_hides_port_labels(self) -> None:
        self._run_qml_probe(
            "flowchart-drop-preview-polish",
            """
            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            canvas.setProperty("dropPreviewNodePayload", flowchart_payload("document"))
            canvas.setProperty("dropPreviewScreenX", 180.0)
            canvas.setProperty("dropPreviewScreenY", 220.0)
            app.processEvents()
            drop_preview = canvas.findChild(QObject, "graphCanvasDropPreview")
            assert drop_preview is not None
            assert bool(drop_preview.property("previewIsFlowchart"))
            assert not bool(drop_preview.property("previewUsesHostChrome"))
            assert not bool(drop_preview.property("previewPortLabelsEnabled"))
            assert len(named_child_items(drop_preview, "graphFlowchartSilhouette")) >= 1
            assert len(named_child_items(drop_preview, "graphFlowchartVectorShape")) >= 1
            assert len(named_child_items(drop_preview, "graphCanvasDropPreviewInputPortDot")) == 1
            assert len(named_child_items(drop_preview, "graphCanvasDropPreviewOutputPortDot")) == 2
            assert not any(item.isVisible() for item in named_child_items(drop_preview, "graphCanvasDropPreviewInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(drop_preview, "graphCanvasDropPreviewOutputPortLabel"))
            """,
        )


if __name__ == "__main__":
    unittest.main()
