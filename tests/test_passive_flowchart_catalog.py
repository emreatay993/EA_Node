from __future__ import annotations

import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry

_EXPECTED_FLOWCHART_SPECS = {
    "passive.flowchart.start": {
        "display_name": "Start",
        "surface_variant": "start",
        "ports": (("flow_out", "out", False),),
    },
    "passive.flowchart.end": {
        "display_name": "End",
        "surface_variant": "end",
        "ports": (("flow_in", "in", True),),
    },
    "passive.flowchart.process": {
        "display_name": "Process",
        "surface_variant": "process",
        "ports": (
            ("flow_in", "in", True),
            ("flow_out", "out", False),
        ),
    },
    "passive.flowchart.decision": {
        "display_name": "Decision",
        "surface_variant": "decision",
        "ports": (
            ("flow_in", "in", False),
            ("branch_a", "out", False),
            ("branch_b", "out", False),
        ),
    },
    "passive.flowchart.document": {
        "display_name": "Document",
        "surface_variant": "document",
        "ports": (
            ("flow_in", "in", True),
            ("flow_out", "out", False),
        ),
    },
    "passive.flowchart.connector": {
        "display_name": "Connector",
        "surface_variant": "connector",
        "ports": (
            ("flow_in", "in", True),
            ("flow_out", "out", False),
        ),
    },
    "passive.flowchart.input_output": {
        "display_name": "Input / Output",
        "surface_variant": "input_output",
        "ports": (
            ("flow_in", "in", True),
            ("flow_out", "out", False),
        ),
    },
    "passive.flowchart.predefined_process": {
        "display_name": "Predefined Process",
        "surface_variant": "predefined_process",
        "ports": (
            ("flow_in", "in", True),
            ("flow_out", "out", False),
        ),
    },
    "passive.flowchart.database": {
        "display_name": "Database",
        "surface_variant": "database",
        "ports": (
            ("flow_in", "in", True),
            ("flow_out", "out", False),
        ),
    },
}


class PassiveFlowchartCatalogTests(unittest.TestCase):
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
                    (port.key, port.direction, port.allow_multiple_connections)
                    for port in spec.ports
                ),
                expected["ports"],
            )
            self.assertTrue(all(port.kind == "flow" for port in spec.ports))
            self.assertTrue(all(port.data_type == "flow" for port in spec.ports))

    def test_decision_branch_ports_remain_neutral_and_edge_label_driven(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("passive.flowchart.decision")

        self.assertEqual(
            [port.key for port in spec.ports if port.direction == "out"],
            ["branch_a", "branch_b"],
        )
        self.assertFalse(any(port.key.lower() in {"yes", "no"} for port in spec.ports))


if __name__ == "__main__":
    unittest.main()
