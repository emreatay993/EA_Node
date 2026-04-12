from __future__ import annotations
import unittest
from unittest.mock import patch
import pytest
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.builtins.ansys_dpf_catalog import ANSYS_DPF_DEPENDENCY
from ea_node_editor.nodes.plugin_contracts import PluginAvailability
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from tests.graph_surface import (
    GraphSurfaceBoundaryContractTests,
    GraphSurfaceInlineEditorContractTests,
    GraphSurfaceMediaAndScopeContractTests,
)
from tests.graph_surface.environment import GraphSurfaceInputContractTestBase
# GraphSurfaceInputContractTests remains covered in tests.graph_surface; this entrypoint stays packet-focused.
pytestmark = pytest.mark.xdist_group("p03_graph_surface")
def _missing_dpf_surface_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_missing_dpf_surface",
        "name": "Missing DPF Surface",
        "active_workspace_id": "ws_dpf",
        "workspace_order": ["ws_dpf"],
        "workspaces": [
            {
                "workspace_id": "ws_dpf",
                "name": "Workspace DPF",
                "active_view_id": "view_dpf",
                "views": [
                    {
                        "view_id": "view_dpf",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "node_result",
                        "type_id": "dpf.result_file",
                        "title": "Offline Result",
                        "x": 40.0,
                        "y": 90.0,
                        "collapsed": False,
                        "properties": {"path": "C:/tmp/example.rst"},
                        "exposed_ports": {"result_file": True, "exec_out": True},
                        "port_labels": {"result_file": "Saved Result File"},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_model",
                        "type_id": "dpf.model",
                        "title": "Offline Model",
                        "x": 280.0,
                        "y": 90.0,
                        "collapsed": False,
                        "properties": {"path": "C:/tmp/example.rst"},
                        "exposed_ports": {"result_file": False, "model": True},
                        "port_labels": {"result_file": "Hidden Saved Result File", "model": "Saved Model"},
                        "parent_node_id": None,
                    },
                ],
                "edges": [{"edge_id": "edge_hidden_result_file", "source_node_id": "node_result", "source_port_key": "result_file", "target_node_id": "node_model", "target_port_key": "result_file"}],
            }
        ],
        "metadata": {},
    }
class GraphSurfaceLockedPortContractTests(GraphSurfaceInputContractTestBase):
    def test_graph_node_host_emits_locked_input_port_double_click_contract(self) -> None:
        self._run_qml_probe(
            "locked-port-double-click-contract",
            """
            payload = node_payload()
            payload["ports"] = [
                {"key": "message", "label": "Message", "direction": "in", "kind": "data", "data_type": "str", "connected": False, "locked": True, "lockable": True},
                {"key": "details", "label": "Details", "direction": "in", "kind": "data", "data_type": "json", "connected": False, "locked": True, "lockable": False},
            ]
            payload["inline_properties"] = [
                {"key": "message", "label": "Message", "inline_editor": "text", "value": "locked text", "overridden_by_input": False, "input_port_label": "message"},
                {"key": "details", "label": "Details", "inline_editor": "text", "value": "{\\"note\\": \\"raw\\"}", "overridden_by_input": False, "input_port_label": "details"},
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            locked_row = named_item(host, "graphNodeInputPortRow", "message")
            unsupported_row = named_item(host, "graphNodeInputPortRow", "details")
            locked_dot = named_item(host, "graphNodeInputPortDot", "message")
            locked_padlock = named_item(host, "graphNodeInputPortPadlock", "message")
            lock_toggle = named_item(host, "graphNodeInputPortLockToggleMouseArea", "message")
            unsupported_toggle = named_item(host, "graphNodeInputPortLockToggleMouseArea", "details")

            assert bool(locked_row.property("lockableState")) is True
            assert bool(locked_row.property("lockedState")) is True
            assert bool(unsupported_row.property("lockableState")) is False
            assert bool(unsupported_row.property("lockedState")) is False
            assert abs(item_scene_point(locked_dot).x() - item_scene_point(locked_padlock).x()) < 1.0
            assert abs(item_scene_point(locked_dot).y() - item_scene_point(locked_padlock).y()) < 1.0
            assert bool(lock_toggle.property("visible")) is True
            assert bool(unsupported_toggle.property("visible")) is False

            events = []
            host.portDoubleClicked.connect(
                lambda node_id, port_key, direction, locked: events.append((node_id, port_key, direction, locked))
            )
            window = attach_host_to_window(host, 480, 360)
            mouse_click(window, item_scene_point(lock_toggle))
            settle_events(4)
            assert events == [], events

            mouse_double_click(window, item_scene_point(lock_toggle))
            settle_events(4)

            assert events == [("node_surface_contract_test", "message", "in", True)], events

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )
    def test_graph_node_host_emits_unlocked_lockable_input_double_click_contract(self) -> None:
        self._run_qml_probe(
            "unlocked-lockable-port-double-click-contract",
            """
            payload = node_payload()
            payload["ports"] = [
                {"key": "message", "label": "Message", "direction": "in", "kind": "data", "data_type": "str", "lockable": True, "locked": False},
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            unlocked_row = named_item(host, "graphNodeInputPortRow", "message")
            unlocked_mouse = named_item(host, "graphNodeInputPortMouseArea", "message")

            assert bool(unlocked_row.property("lockableState")) is True
            assert bool(unlocked_row.property("lockedState")) is False

            events = []
            host.portDoubleClicked.connect(
                lambda node_id, port_key, direction, locked: events.append((node_id, port_key, direction, locked))
            )
            window = attach_host_to_window(host, 480, 360)
            mouse_double_click(window, item_scene_point(unlocked_mouse))
            settle_events(4)

            assert events == [("node_surface_contract_test", "message", "in", False)], events

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )
class GraphSurfaceMissingDpfPlaceholderContractTests(unittest.TestCase):
    def test_payload_builder_marks_missing_dpf_projection_as_read_only_and_keeps_saved_ports(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        project = serializer.from_document(_missing_dpf_surface_payload())
        builder = GraphScenePayloadBuilder()
        with patch(
            "ea_node_editor.ui_qml.graph_scene_payload_builder.get_ansys_dpf_plugin_availability",
            return_value=PluginAvailability.missing_dependency(
                ANSYS_DPF_DEPENDENCY,
                summary="ansys.dpf.core is not installed; the DPF node family remains unavailable.",
            ),
        ):
            nodes_payload, _backdrops, _minimap, edges_payload = builder.rebuild_partitioned_models(
                model=GraphModel(project),
                registry=NodeRegistry(),
                workspace_id="ws_dpf",
                scope_path=(),
                graph_theme_bridge=None,
            )
        nodes_by_id = {payload["node_id"]: payload for payload in nodes_payload}
        model_ports = {port["key"]: port for port in nodes_by_id["node_model"]["ports"]}
        self.assertEqual({edge["edge_id"] for edge in edges_payload}, {"edge_hidden_result_file"})
        self.assertTrue(nodes_by_id["node_model"]["unresolved"])
        self.assertTrue(nodes_by_id["node_model"]["read_only"])
        self.assertEqual(nodes_by_id["node_model"]["inline_properties"], [])
        self.assertEqual(nodes_by_id["node_model"]["unavailable_reason"], "ansys.dpf.core is not installed; the DPF node family remains unavailable.")
        self.assertNotIn("result_file", model_ports)
        self.assertEqual(model_ports["model"]["label"], "Saved Model")
        self.assertTrue(model_ports["model"]["exposed"])
__all__ = ["GraphSurfaceBoundaryContractTests", "GraphSurfaceInlineEditorContractTests", "GraphSurfaceLockedPortContractTests", "GraphSurfaceMediaAndScopeContractTests"]
if __name__ == "__main__":
    unittest.main()
