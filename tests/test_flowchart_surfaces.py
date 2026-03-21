from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec
from ea_node_editor.ui_qml.edge_routing import port_scene_pos
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics

_REPO_ROOT = Path(__file__).resolve().parents[1]


class FlowchartSurfaceGeometryTests(unittest.TestCase):
    def test_terminator_anchor_hugs_the_curved_edge(self) -> None:
        spec = NodeTypeSpec(
            type_id="tests.flowchart_start",
            display_name="Start",
            category="Tests",
            icon="play",
            ports=(
                PortSpec("flow_in", "in", "flow", "any"),
                PortSpec("flow_out", "out", "flow", "any", allow_multiple_connections=True),
            ),
            properties=(),
            runtime_behavior="passive",
            surface_family="flowchart",
            surface_variant="start",
        )
        node = NodeInstance(
            node_id="node_start",
            type_id=spec.type_id,
            title="Start",
            x=40.0,
            y=30.0,
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})
        input_point = port_scene_pos(node, spec, "flow_in", {node.node_id: node})

        self.assertEqual(metrics.default_width, 228.0)
        self.assertGreaterEqual(metrics.min_height, 78.0)
        self.assertGreater(input_point.x() - node.x, 0.0)
        self.assertLess(input_point.x() - node.x, 2.0)


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

            def flowchart_payload(variant):
                return {
                    "node_id": "node_flowchart_surface_test",
                    "type_id": "tests.flowchart_surface",
                    "title": "Flowchart",
                    "display_name": "Flowchart",
                    "x": 120.0,
                    "y": 120.0,
                    "width": 220.0,
                    "height": 124.0,
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
                            "label": "In",
                            "direction": "in",
                            "kind": "flow",
                            "data_type": "any",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "branch_a",
                            "label": "A",
                            "direction": "out",
                            "kind": "flow",
                            "data_type": "any",
                            "exposed": True,
                            "connected": False,
                        },
                        {
                            "key": "branch_b",
                            "label": "B",
                            "direction": "out",
                            "kind": "flow",
                            "data_type": "any",
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

    def test_graph_node_host_loads_flowchart_surface_family(self) -> None:
        self._run_qml_probe(
            "flowchart-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": flowchart_payload("decision")},
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "flowchart"
            assert not bool(host.property("_useHostChrome"))
            assert host.findChild(QObject, "graphNodeFlowchartSurface") is not None
            assert len(named_child_items(host, "graphFlowchartSilhouette")) >= 1
            assert len(named_child_items(host, "graphNodeInputPortMouseArea")) == 1
            assert len(named_child_items(host, "graphNodeOutputPortMouseArea")) == 2
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(host, "graphNodeOutputPortLabel"))
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
            assert not bool(drop_preview.property("clip"))
            assert not bool(drop_preview.property("previewPortLabelsEnabled"))
            assert not any(item.isVisible() for item in named_child_items(drop_preview, "graphCanvasDropPreviewInputPortLabel"))
            assert not any(item.isVisible() for item in named_child_items(drop_preview, "graphCanvasDropPreviewOutputPortLabel"))
            """,
        )


if __name__ == "__main__":
    unittest.main()
