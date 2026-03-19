from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


class GraphSceneBridgeBindRegressionTests(unittest.TestCase):
    def test_set_workspace_does_not_mutate_node_properties_or_exposed_ports(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        node = model.add_node(
            workspace_id,
            "core.logger",
            "Logger",
            0.0,
            0.0,
            properties={"message": 123},
            exposed_ports={},
        )

        original_properties = dict(node.properties)
        original_exposed = dict(node.exposed_ports)

        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace_id)

        workspace_node = model.project.workspaces[workspace_id].nodes[node.node_id]
        self.assertEqual(workspace_node.properties, original_properties)
        self.assertEqual(workspace_node.exposed_ports, original_exposed)


if __name__ == "__main__":
    unittest.main()
