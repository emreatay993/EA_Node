from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry

_REPO_ROOT = Path(__file__).resolve().parents[1]

_EXPECTED_PLANNING_SPECS = {
    "passive.planning.task_card": {
        "display_name": "Task Card",
        "surface_variant": "task_card",
        "properties": ("title", "body", "owner", "due_date", "status"),
        "enum_property": ("status", ("todo", "in_progress", "blocked", "done")),
    },
    "passive.planning.milestone_card": {
        "display_name": "Milestone Card",
        "surface_variant": "milestone_card",
        "properties": ("title", "body", "target_date", "status"),
        "enum_property": ("status", ("planned", "at_risk", "done")),
    },
    "passive.planning.risk_card": {
        "display_name": "Risk Card",
        "surface_variant": "risk_card",
        "properties": ("title", "body", "severity", "mitigation"),
        "enum_property": ("severity", ("low", "medium", "high", "critical")),
    },
    "passive.planning.decision_card": {
        "display_name": "Decision Card",
        "surface_variant": "decision_card",
        "properties": ("title", "body", "state", "outcome"),
        "enum_property": ("state", ("open", "decided", "deferred")),
    },
}

_EXPECTED_ANNOTATION_SPECS = {
    "passive.annotation.sticky_note": {
        "display_name": "Sticky Note",
        "surface_variant": "sticky_note",
        "properties": ("title", "body"),
    },
    "passive.annotation.callout": {
        "display_name": "Callout",
        "surface_variant": "callout",
        "properties": ("title", "body"),
    },
    "passive.annotation.section_header": {
        "display_name": "Section Header",
        "surface_variant": "section_header",
        "properties": ("title", "subtitle"),
    },
}


class PlanningAnnotationCatalogTests(unittest.TestCase):
    def test_default_registry_registers_locked_planning_catalog_specs(self) -> None:
        registry = build_default_registry()

        for type_id, expected in _EXPECTED_PLANNING_SPECS.items():
            spec = registry.get_spec(type_id)

            self.assertEqual(spec.display_name, expected["display_name"])
            self.assertEqual(spec.category, "Planning")
            self.assertEqual(spec.runtime_behavior, "passive")
            self.assertEqual(spec.surface_family, "planning")
            self.assertEqual(spec.surface_variant, expected["surface_variant"])
            self.assertFalse(spec.collapsible)
            self.assertEqual(spec.ports, ())
            self.assertEqual(tuple(prop.key for prop in spec.properties), expected["properties"])
            enum_key, enum_values = expected["enum_property"]
            enum_spec = next(prop for prop in spec.properties if prop.key == enum_key)
            self.assertEqual(enum_spec.enum_values, enum_values)

    def test_default_registry_registers_locked_annotation_catalog_specs(self) -> None:
        registry = build_default_registry()

        for type_id, expected in _EXPECTED_ANNOTATION_SPECS.items():
            spec = registry.get_spec(type_id)

            self.assertEqual(spec.display_name, expected["display_name"])
            self.assertEqual(spec.category, "Annotation")
            self.assertEqual(spec.runtime_behavior, "passive")
            self.assertEqual(spec.surface_family, "annotation")
            self.assertEqual(spec.surface_variant, expected["surface_variant"])
            self.assertFalse(spec.collapsible)
            self.assertEqual(spec.ports, ())
            self.assertEqual(tuple(prop.key for prop in spec.properties), expected["properties"])


class PlanningAnnotationSurfaceQmlTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
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

            def node_payload(surface_family, surface_variant, title, properties, width, height):
                return {
                    "node_id": "node_planning_annotation_surface_test",
                    "type_id": "tests.passive_surface",
                    "title": title,
                    "properties": properties,
                    "x": 80.0,
                    "y": 90.0,
                    "width": width,
                    "height": height,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "passive",
                    "surface_family": surface_family,
                    "surface_variant": surface_variant,
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [],
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

    def test_graph_node_host_loads_shared_planning_card_surface(self) -> None:
        self._run_qml_probe(
            "planning-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(
                        "planning",
                        "task_card",
                        "Ship parser",
                        {
                            "title": "Ship parser",
                            "body": "Finalize validation and release notes.",
                            "owner": "Platform",
                            "due_date": "2026-03-31",
                            "status": "in_progress",
                        },
                        248.0,
                        168.0,
                    ),
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "planning"
            assert host.findChild(QObject, "graphNodePlanningSurface") is not None
            assert float(loader.property("contentHeight")) > 0.0
            """,
        )

    def test_graph_node_host_loads_shared_annotation_note_surface(self) -> None:
        self._run_qml_probe(
            "annotation-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {
                    "nodeData": node_payload(
                        "annotation",
                        "sticky_note",
                        "Release note",
                        {
                            "title": "Release note",
                            "body": "Track follow-up messaging for the rollout.",
                        },
                        228.0,
                        152.0,
                    ),
                },
            )
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "annotation"
            assert host.findChild(QObject, "graphNodeAnnotationSurface") is not None
            assert float(loader.property("contentHeight")) > 0.0
            """,
        )


if __name__ == "__main__":
    unittest.main()
