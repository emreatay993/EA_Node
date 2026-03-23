from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.edge_routing import port_scene_pos
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

_REPO_ROOT = Path(__file__).resolve().parents[1]


class FlowchartSurfaceGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def _local_anchor(self, type_id: str, port_key: str) -> tuple[float, float]:
        spec = self.registry.get_spec(type_id)
        node = NodeInstance(
            node_id=f"node_{type_id.rsplit('.', 1)[-1]}",
            type_id=type_id,
            title=spec.display_name,
            x=40.0,
            y=30.0,
        )
        point = port_scene_pos(node, spec, port_key, {node.node_id: node})
        return point.x() - node.x, point.y() - node.y

    def _assert_anchor(self, type_id: str, port_key: str, expected_x: float, expected_y: float) -> None:
        actual_x, actual_y = self._local_anchor(type_id, port_key)
        self.assertAlmostEqual(actual_x, expected_x, places=4)
        self.assertAlmostEqual(actual_y, expected_y, places=4)

    def test_cardinal_anchor_points_cover_rectangular_diamond_curved_and_slanted_shapes(self) -> None:
        self._assert_anchor("passive.flowchart.process", "top", 112.0, 0.5)
        self._assert_anchor("passive.flowchart.process", "right", 223.5, 42.0)
        self._assert_anchor("passive.flowchart.process", "bottom", 112.0, 83.5)
        self._assert_anchor("passive.flowchart.process", "left", 0.5, 42.0)

        self._assert_anchor("passive.flowchart.decision", "top", 118.0, 0.5)
        self._assert_anchor("passive.flowchart.decision", "right", 235.5, 64.0)
        self._assert_anchor("passive.flowchart.decision", "bottom", 118.0, 127.5)
        self._assert_anchor("passive.flowchart.decision", "left", 0.5, 64.0)

        self._assert_anchor("passive.flowchart.start", "top", 114.0, 0.5)
        self._assert_anchor("passive.flowchart.start", "right", 227.5, 39.0)
        self._assert_anchor("passive.flowchart.start", "bottom", 114.0, 77.5)
        self._assert_anchor("passive.flowchart.start", "left", 0.5, 39.0)

        self._assert_anchor("passive.flowchart.input_output", "top", 118.0, 0.5)
        self._assert_anchor("passive.flowchart.input_output", "right", 223.41, 47.0)
        self._assert_anchor("passive.flowchart.input_output", "bottom", 118.0, 93.5)
        self._assert_anchor("passive.flowchart.input_output", "left", 12.59, 47.0)

    def test_database_and_input_output_side_anchors_stay_on_true_visual_midsides(self) -> None:
        self._assert_anchor("passive.flowchart.database", "top", 114.0, 0.5)
        self._assert_anchor("passive.flowchart.database", "right", 227.5, 64.0)
        self._assert_anchor("passive.flowchart.database", "bottom", 114.0, 127.5)
        self._assert_anchor("passive.flowchart.database", "left", 0.5, 64.0)

        self._assert_anchor("passive.flowchart.input_output", "left", 12.59, 47.0)
        self._assert_anchor("passive.flowchart.input_output", "right", 223.41, 47.0)


class FlowchartSurfaceQmlTests(unittest.TestCase):
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

            def flowchart_payload(variant, *, collapsed=False, properties=None):
                resolved_properties = {
                    "title": "Flowchart",
                    "body": "Review request routing and approval outcomes.",
                }
                if properties:
                    resolved_properties.update(properties)
                return {
                    "node_id": "node_flowchart_surface_test",
                    "type_id": "tests.flowchart_surface",
                    "title": "Flowchart",
                    "display_name": "Flowchart",
                    "x": 120.0,
                    "y": 120.0,
                    "width": 236.0,
                    "height": 128.0,
                    "accent": "#2F89FF",
                    "collapsed": collapsed,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "flowchart",
                    "surface_variant": variant,
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "top",
                            "label": "top",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "right",
                            "label": "right",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "bottom",
                            "label": "bottom",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "left",
                            "label": "left",
                            "direction": "neutral",
                            "kind": "flow",
                            "data_type": "flow",
                            "exposed": True,
                            "connected": False,
                        },
                    ],
                    "inline_properties": [],
                    "properties": resolved_properties,
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

    def test_graph_node_host_loads_flowchart_surface_family(self) -> None:
        self._run_qml_probe(
            "flowchart-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision")},
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            title_item = host.findChild(QObject, "graphNodeTitle")
            body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
            assert loader is not None
            assert title_item is not None
            assert body_text is not None
            assert loader.property("loadedSurfaceKey") == "flowchart"
            assert not bool(host.property("_useHostChrome"))
            assert host.findChild(QObject, "graphNodeFlowchartSurface") is not None
            assert not bool(title_item.property("visible"))
            assert bool(body_text.property("visible"))
            assert str(body_text.property("text") or "") == "Review request routing and approval outcomes."
            assert len(named_child_items(host, "graphFlowchartSilhouette")) >= 1
            assert len(named_child_items(host, "graphNodeInputPortMouseArea")) == 2
            assert len(named_child_items(host, "graphNodeOutputPortMouseArea")) == 2
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeOutputPortLabel"))
            """,
        )

    def test_collapsed_flowchart_keeps_compact_header_title_and_hides_body_surface(self) -> None:
        self._run_qml_probe(
            "flowchart-collapsed-header",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision", collapsed=True)},
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            title_item = host.findChild(QObject, "graphNodeTitle")
            body_text = host.findChild(QObject, "graphNodeFlowchartBodyText")
            assert loader is not None
            assert title_item is not None
            assert body_text is None
            assert not bool(loader.property("surfaceLoaded"))
            assert bool(title_item.property("visible"))
            assert str(title_item.property("text") or "") == "Flowchart"
            """,
        )

    def test_graph_canvas_drop_preview_reuses_flowchart_silhouette_component(self) -> None:
        self._run_qml_probe(
            "flowchart-drop-preview",
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
            canvas.setProperty("dropPreviewNodePayload", flowchart_payload("database"))
            canvas.setProperty("dropPreviewScreenX", 180.0)
            canvas.setProperty("dropPreviewScreenY", 220.0)
            app.processEvents()
            drop_preview = canvas.findChild(QObject, "graphCanvasDropPreview")
            assert drop_preview is not None
            assert bool(drop_preview.property("visible"))
            assert float(drop_preview.property("width")) > 0.0
            assert float(drop_preview.property("height")) > 0.0
            assert len(named_child_items(drop_preview, "graphFlowchartSilhouette")) >= 1
            assert len(named_child_items(drop_preview, "graphCanvasDropPreviewInputPortDot")) == 2
            assert len(named_child_items(drop_preview, "graphCanvasDropPreviewOutputPortDot")) == 2
            assert not bool(drop_preview.property("clip"))
            assert not bool(drop_preview.property("previewPortLabelsEnabled"))
            assert not any(item.isVisible() for item in named_child_items(drop_preview, "graphCanvasDropPreviewInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(drop_preview, "graphCanvasDropPreviewOutputPortLabel"))
            """,
        )


if __name__ == "__main__":
    unittest.main()
