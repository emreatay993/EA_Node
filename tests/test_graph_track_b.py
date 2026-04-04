from __future__ import annotations

import unittest
from unittest.mock import Mock

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from tests.graph_track_b.qml_preference_bindings import (
    GraphCanvasQmlPreferenceBindingTests,
    build_graph_canvas_qml_preference_binding_subprocess_suite,
)
from tests.graph_track_b.runtime_history import RuntimeGraphHistoryTrackBTests
from tests.graph_track_b.scene_and_model import GraphModelTrackBTests, GraphSceneBridgeTrackBTests
from tests.graph_track_b.viewport import ViewportBridgeTrackBTests


def _compat_test_workspace_mutation_service_clamps_pdf_panel_page_numbers_on_property_updates(self) -> None:
    registry = build_default_registry()
    model = GraphModel()
    workspace = model.active_workspace
    service = model.validated_mutations(workspace.workspace_id, registry)
    spec = registry.get_spec("passive.media.pdf_panel")
    node = service.add_node(
        type_id=spec.type_id,
        title=spec.display_name,
        x=40.0,
        y=60.0,
        properties=registry.default_properties(spec.type_id),
        exposed_ports={port.key: port.exposed for port in spec.ports},
    )

    clamp_pdf_page_number = Mock(return_value=2)
    service.boundary_adapters.clamp_pdf_page_number_resolver = clamp_pdf_page_number
    source_path = service.set_node_property(node.node_id, "source_path", "/tmp/clamped.pdf")
    page_updates = service.set_node_properties(node.node_id, {"page_number": 99})

    self.assertEqual(source_path, "/tmp/clamped.pdf")
    self.assertEqual(page_updates, {"page_number": 2})
    self.assertEqual(workspace.nodes[node.node_id].properties["page_number"], 2)
    self.assertEqual(clamp_pdf_page_number.call_args_list[-1].args, ("/tmp/clamped.pdf", 99))


# Keep the shared track-b source untouched and override only the stale patch target here.
GraphModelTrackBTests.test_workspace_mutation_service_clamps_pdf_panel_page_numbers_on_property_updates = (
    _compat_test_workspace_mutation_service_clamps_pdf_panel_page_numbers_on_property_updates
)


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(GraphModelTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphSceneBridgeTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(ViewportBridgeTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(RuntimeGraphHistoryTrackBTests))
    suite.addTests(build_graph_canvas_qml_preference_binding_subprocess_suite(loader))
    return suite


if __name__ == "__main__":
    unittest.main()
