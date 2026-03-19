from __future__ import annotations

import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.passive_annotation import (
    PASSIVE_ANNOTATION_CALLOUT_TYPE_ID,
    PASSIVE_ANNOTATION_NODE_PLUGINS,
    PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID,
    PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID,
)
from ea_node_editor.nodes.builtins.passive_flowchart import (
    PASSIVE_FLOWCHART_CONNECTOR_TYPE_ID,
    PASSIVE_FLOWCHART_DATABASE_TYPE_ID,
    PASSIVE_FLOWCHART_DECISION_TYPE_ID,
    PASSIVE_FLOWCHART_DOCUMENT_TYPE_ID,
    PASSIVE_FLOWCHART_END_TYPE_ID,
    PASSIVE_FLOWCHART_INPUT_OUTPUT_TYPE_ID,
    PASSIVE_FLOWCHART_NODE_PLUGINS,
    PASSIVE_FLOWCHART_PREDEFINED_PROCESS_TYPE_ID,
    PASSIVE_FLOWCHART_PROCESS_TYPE_ID,
    PASSIVE_FLOWCHART_START_TYPE_ID,
)
from ea_node_editor.nodes.builtins.passive_media import (
    PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    PASSIVE_MEDIA_NODE_PLUGINS,
    PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
)
from ea_node_editor.nodes.builtins.passive_planning import (
    PASSIVE_PLANNING_DECISION_CARD_TYPE_ID,
    PASSIVE_PLANNING_MILESTONE_CARD_TYPE_ID,
    PASSIVE_PLANNING_NODE_PLUGINS,
    PASSIVE_PLANNING_RISK_CARD_TYPE_ID,
    PASSIVE_PLANNING_TASK_CARD_TYPE_ID,
)
from ea_node_editor.nodes.types import ExecutionContext


def _context() -> ExecutionContext:
    return ExecutionContext(
        run_id="run",
        node_id="node",
        workspace_id="ws",
        inputs={},
        properties={},
        emit_log=lambda _level, _message: None,
    )


class PassiveNodeContractsTests(unittest.TestCase):
    def test_passive_plugins_publish_passive_surface_contracts_and_noop_execution(self) -> None:
        for plugin_cls in (
            *PASSIVE_FLOWCHART_NODE_PLUGINS,
            *PASSIVE_PLANNING_NODE_PLUGINS,
            *PASSIVE_ANNOTATION_NODE_PLUGINS,
            *PASSIVE_MEDIA_NODE_PLUGINS,
        ):
            plugin = plugin_cls()
            spec = plugin.spec()

            self.assertEqual(spec.runtime_behavior, "passive")
            self.assertFalse(spec.collapsible)
            self.assertTrue(spec.surface_family)
            self.assertEqual(plugin.execute(_context()).outputs, {})

    def test_flowchart_passive_nodes_use_flow_only_ports_and_branch_contracts(self) -> None:
        registry = build_default_registry()
        flowchart_type_ids = (
            PASSIVE_FLOWCHART_START_TYPE_ID,
            PASSIVE_FLOWCHART_END_TYPE_ID,
            PASSIVE_FLOWCHART_PROCESS_TYPE_ID,
            PASSIVE_FLOWCHART_DECISION_TYPE_ID,
            PASSIVE_FLOWCHART_DOCUMENT_TYPE_ID,
            PASSIVE_FLOWCHART_CONNECTOR_TYPE_ID,
            PASSIVE_FLOWCHART_INPUT_OUTPUT_TYPE_ID,
            PASSIVE_FLOWCHART_PREDEFINED_PROCESS_TYPE_ID,
            PASSIVE_FLOWCHART_DATABASE_TYPE_ID,
        )

        for type_id in flowchart_type_ids:
            spec = registry.get_spec(type_id)
            self.assertEqual(spec.surface_family, "flowchart")
            self.assertTrue(spec.ports)
            self.assertTrue(all(port.kind == "flow" and port.data_type == "flow" for port in spec.ports))

        start_spec = registry.get_spec(PASSIVE_FLOWCHART_START_TYPE_ID)
        self.assertEqual([port.key for port in start_spec.ports], ["flow_out"])

        end_spec = registry.get_spec(PASSIVE_FLOWCHART_END_TYPE_ID)
        self.assertEqual([port.key for port in end_spec.ports], ["flow_in"])
        self.assertTrue(end_spec.ports[0].allow_multiple_connections)

        decision_spec = registry.get_spec(PASSIVE_FLOWCHART_DECISION_TYPE_ID)
        self.assertEqual([port.key for port in decision_spec.ports], ["flow_in", "branch_a", "branch_b"])

    def test_non_flow_passive_nodes_do_not_expose_ports(self) -> None:
        registry = build_default_registry()
        portless_type_ids = (
            PASSIVE_PLANNING_TASK_CARD_TYPE_ID,
            PASSIVE_PLANNING_MILESTONE_CARD_TYPE_ID,
            PASSIVE_PLANNING_RISK_CARD_TYPE_ID,
            PASSIVE_PLANNING_DECISION_CARD_TYPE_ID,
            PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID,
            PASSIVE_ANNOTATION_CALLOUT_TYPE_ID,
            PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID,
            PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
            PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
        )

        for type_id in portless_type_ids:
            spec = registry.get_spec(type_id)
            self.assertEqual(spec.ports, ())

    def test_registry_default_properties_cover_media_and_planning_defaults(self) -> None:
        registry = build_default_registry()

        task_defaults = registry.default_properties(PASSIVE_PLANNING_TASK_CARD_TYPE_ID)
        risk_defaults = registry.default_properties(PASSIVE_PLANNING_RISK_CARD_TYPE_ID)
        image_defaults = registry.default_properties(PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID)
        pdf_defaults = registry.default_properties(PASSIVE_MEDIA_PDF_PANEL_TYPE_ID)

        self.assertEqual(task_defaults["title"], "Task")
        self.assertEqual(task_defaults["status"], "todo")
        self.assertEqual(risk_defaults["severity"], "medium")
        self.assertEqual(image_defaults["fit_mode"], "contain")
        self.assertEqual(image_defaults["crop_w"], 1.0)
        self.assertEqual(pdf_defaults["page_number"], 1)


if __name__ == "__main__":
    unittest.main()
