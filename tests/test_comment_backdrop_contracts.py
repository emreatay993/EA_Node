from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from ea_node_editor.graph.model import GraphModel, NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics
from tests.graph_surface_pointer_regression import run_qml_probe

COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"


class CommentBackdropCatalogTests(unittest.TestCase):
    def test_generated_js_surface_metric_contract_matches_authoritative_json(self) -> None:
        graph_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "ui_qml" / "components" / "graph"
        json_payload = json.loads((graph_dir / "GraphNodeSurfaceMetricContract.json").read_text(encoding="utf-8"))
        js_text = (graph_dir / "GraphNodeSurfaceMetricContract.js").read_text(encoding="utf-8")
        match = re.search(
            r"var SURFACE_METRIC_CONTRACT = (\{.*\});\s*function contract",
            js_text,
            re.DOTALL,
        )

        self.assertIsNotNone(match)
        assert match is not None
        js_payload = json.loads(match.group(1))
        self.assertEqual(js_payload, json_payload)

    def test_default_registry_registers_locked_comment_backdrop_spec(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec(COMMENT_BACKDROP_TYPE_ID)

        self.assertEqual(spec.display_name, "Comment Backdrop")
        self.assertEqual(spec.category, "Annotation")
        self.assertEqual(spec.runtime_behavior, "passive")
        self.assertEqual(spec.surface_family, "comment_backdrop")
        self.assertEqual(spec.surface_variant, "comment_backdrop")
        self.assertTrue(spec.collapsible)
        self.assertEqual(spec.ports, ())
        self.assertEqual(tuple(prop.key for prop in spec.properties), ("title", "body"))

        title = next(prop for prop in spec.properties if prop.key == "title")
        body = next(prop for prop in spec.properties if prop.key == "body")
        self.assertEqual(title.default, "Comment Backdrop")
        self.assertEqual(title.inspector_editor, "")
        self.assertEqual(body.default, "")
        self.assertEqual(body.inspector_editor, "textarea")

    def test_comment_backdrop_surface_metrics_use_locked_defaults(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec(COMMENT_BACKDROP_TYPE_ID)
        node = NodeInstance(
            node_id="node_comment_backdrop",
            type_id=spec.type_id,
            title=spec.display_name,
            x=40.0,
            y=30.0,
        )

        metrics = node_surface_metrics(node, spec, {node.node_id: node})

        self.assertEqual(metrics.default_width, 420.0)
        self.assertEqual(metrics.default_height, 260.0)
        self.assertEqual(metrics.min_width, 260.0)
        self.assertEqual(metrics.min_height, 180.0)
        self.assertEqual(metrics.title_top, 14.0)
        self.assertEqual(metrics.title_height, 24.0)
        self.assertEqual(metrics.body_top, 52.0)
        self.assertEqual(metrics.body_height, 190.0)
        self.assertEqual(metrics.body_left_margin, 18.0)
        self.assertEqual(metrics.body_right_margin, 18.0)
        self.assertEqual(metrics.body_bottom_margin, 18.0)
        self.assertFalse(metrics.show_header_background)
        self.assertFalse(metrics.show_accent_bar)
        self.assertFalse(metrics.use_host_chrome)

    def test_scene_bridge_payload_and_serializer_roundtrip_stay_on_normal_document_path(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        node_id = scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, 40.0, 60.0)
        scene.set_node_property(node_id, "body", "Cluster related nodes here.")

        payload = next(item for item in scene.nodes_model if item["node_id"] == node_id)
        self.assertEqual(payload["runtime_behavior"], "passive")
        self.assertEqual(payload["surface_family"], "comment_backdrop")
        self.assertEqual(payload["surface_variant"], "comment_backdrop")
        self.assertEqual(payload["ports"], [])
        self.assertEqual(payload["width"], 420.0)
        self.assertEqual(payload["height"], 260.0)
        self.assertFalse(payload["surface_metrics"]["use_host_chrome"])

        serializer = JsonProjectSerializer(registry)
        document = serializer.to_document(model.project)
        workspace_doc = next(doc for doc in document["workspaces"] if doc["workspace_id"] == workspace_id)
        node_doc = next(doc for doc in workspace_doc["nodes"] if doc["node_id"] == node_id)

        self.assertEqual(node_doc["type_id"], COMMENT_BACKDROP_TYPE_ID)
        self.assertEqual(node_doc["properties"]["title"], "Comment Backdrop")
        self.assertEqual(node_doc["properties"]["body"], "Cluster related nodes here.")
        for membership_key in (
            "member_ids",
            "member_node_ids",
            "member_backdrop_ids",
            "contained_node_ids",
            "contained_backdrop_ids",
        ):
            self.assertNotIn(membership_key, node_doc)

        round_tripped = serializer.from_document(document)
        round_trip_workspace = round_tripped.workspaces[workspace_id]
        round_trip_node = round_trip_workspace.nodes[node_id]
        self.assertEqual(round_trip_node.type_id, COMMENT_BACKDROP_TYPE_ID)
        self.assertEqual(
            round_trip_node.properties,
            {
                "title": "Comment Backdrop",
                "body": "Cluster related nodes here.",
            },
        )


class CommentBackdropSurfaceQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))

            repo_root = Path.cwd()
            graph_node_host_qml_path = repo_root / "ea_node_editor" / "ui_qml" / "components" / "graph" / "GraphNodeHost.qml"

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

            def comment_backdrop_payload(properties):
                return {
                    "node_id": "node_comment_backdrop_surface_test",
                    "type_id": "passive.annotation.comment_backdrop",
                    "title": "Comment Backdrop",
                    "x": 120.0,
                    "y": 90.0,
                    "width": 420.0,
                    "height": 260.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": "comment_backdrop",
                    "surface_variant": "comment_backdrop",
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
                    "inline_properties": [],
                    "properties": properties,
                }
            """,
            body,
        )

    def test_graph_node_host_loads_comment_backdrop_surface_family(self) -> None:
        self._run_qml_probe(
            "comment-backdrop-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": comment_backdrop_payload(
                        {
                            "title": "Comment Backdrop",
                            "body": "Cluster related nodes here.",
                        }
                    ),
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            surface = host.findChild(QObject, "graphNodeCommentBackdropSurface")
            body_text = host.findChild(QObject, "graphNodeCommentBackdropBodyText")
            assert loader is not None
            assert surface is not None
            assert body_text is not None
            assert loader.property("loadedSurfaceKey") == "comment_backdrop"
            assert float(loader.property("contentHeight")) > 0.0
            assert not bool(host.property("_useHostChrome"))
            assert bool(body_text.property("visible"))
            assert len(named_child_items(host, "graphNodeInputPortMouseArea")) == 0
            assert len(named_child_items(host, "graphNodeOutputPortMouseArea")) == 0
            """,
        )


if __name__ == "__main__":
    unittest.main()
