from __future__ import annotations

import unittest

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry

_EXPECTED_CARDINAL_PORTS = (
    ("top", "neutral", True, "top"),
    ("right", "neutral", True, "right"),
    ("bottom", "neutral", True, "bottom"),
    ("left", "neutral", True, "left"),
)

_EXPECTED_FLOWCHART_SPECS = {
    "passive.flowchart.start": {
        "display_name": "Start",
        "surface_variant": "start",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.end": {
        "display_name": "End",
        "surface_variant": "end",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.process": {
        "display_name": "Process",
        "surface_variant": "process",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.decision": {
        "display_name": "Decision",
        "surface_variant": "decision",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.document": {
        "display_name": "Document",
        "surface_variant": "document",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.connector": {
        "display_name": "Connector",
        "surface_variant": "connector",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.input_output": {
        "display_name": "Input / Output",
        "surface_variant": "input_output",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.predefined_process": {
        "display_name": "Predefined Process",
        "surface_variant": "predefined_process",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
    "passive.flowchart.database": {
        "display_name": "Database",
        "surface_variant": "database",
        "ports": _EXPECTED_CARDINAL_PORTS,
        "properties": ("title", "body"),
    },
}


class PassiveFlowchartCatalogTests(unittest.TestCase):
    def test_locked_flowchart_type_ids_remain_stable(self) -> None:
        registry = build_default_registry()

        self.assertEqual(
            set(_EXPECTED_FLOWCHART_SPECS),
            {
                "passive.flowchart.start",
                "passive.flowchart.end",
                "passive.flowchart.process",
                "passive.flowchart.decision",
                "passive.flowchart.document",
                "passive.flowchart.connector",
                "passive.flowchart.input_output",
                "passive.flowchart.predefined_process",
                "passive.flowchart.database",
            },
        )
        for type_id in _EXPECTED_FLOWCHART_SPECS:
            self.assertIsNotNone(registry.get_spec(type_id))

    def test_default_registry_registers_locked_flowchart_catalog_specs(self) -> None:
        registry = build_default_registry()

        for type_id, expected in _EXPECTED_FLOWCHART_SPECS.items():
            spec = registry.get_spec(type_id)

            self.assertEqual(spec.display_name, expected["display_name"])
            self.assertEqual(spec.category, "Flowchart")
            self.assertEqual(spec.runtime_behavior, "passive")
            self.assertEqual(spec.surface_family, "flowchart")
            self.assertEqual(spec.surface_variant, expected["surface_variant"])
            self.assertFalse(spec.collapsible)
            self.assertEqual(
                tuple(
                    (port.key, port.direction, port.allow_multiple_connections, port.side)
                    for port in spec.ports
                ),
                expected["ports"],
            )
            self.assertEqual(tuple(prop.key for prop in spec.properties), expected["properties"])
            self.assertEqual(spec.properties[0].default, expected["display_name"])
            self.assertEqual(spec.properties[1].default, expected["display_name"])
            self.assertEqual(spec.properties[1].inspector_editor, "textarea")
            self.assertTrue(all(port.kind == "flow" for port in spec.ports))
            self.assertTrue(all(port.data_type == "flow" for port in spec.ports))

    def test_effective_flowchart_ports_publish_cardinal_side_metadata(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "passive.flowchart.decision",
            "Decision",
            40.0,
            60.0,
        )
        spec = registry.get_spec("passive.flowchart.decision")
        ports = effective_ports(node=node, spec=spec, workspace_nodes=workspace.nodes)

        self.assertEqual(
            tuple((port.key, port.direction, port.side) for port in ports),
            (
                ("top", "neutral", "top"),
                ("right", "neutral", "right"),
                ("bottom", "neutral", "bottom"),
                ("left", "neutral", "left"),
            ),
        )

    def test_flowchart_decision_ports_are_cardinal_and_edge_label_driven(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.flowchart.decision")

        self.assertEqual(
            [port.key for port in spec.ports],
            ["top", "right", "bottom", "left"],
        )
        self.assertFalse(any(port.key in {"branch_a", "branch_b"} for port in spec.ports))
        self.assertFalse(any(port.key.lower() in {"yes", "no"} for port in spec.ports))


if __name__ == "__main__":
    unittest.main()
