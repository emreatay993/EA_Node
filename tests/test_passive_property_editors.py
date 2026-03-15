from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.window_library_inspector import build_selected_node_property_items
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from tests.passive_property_editor_fixtures import (
    PASSIVE_EDITOR_FIXTURE_TYPE_ID,
    register_passive_editor_fixture,
)


class PassivePropertyEditorModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()
        register_passive_editor_fixture(self.registry)
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)

    def _property_items_for_type(self, type_id: str) -> dict[str, dict[str, object]]:
        node_id = self.scene.add_node_from_type(type_id, 0.0, 0.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        node = workspace.nodes[node_id]
        spec = self.registry.get_spec(type_id)
        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        return {str(item["key"]): item for item in items}

    def test_sdk_driven_editor_modes_follow_property_metadata_not_property_keys(self) -> None:
        items = self._property_items_for_type(PASSIVE_EDITOR_FIXTURE_TYPE_ID)

        self.assertEqual(items["notes_blob"]["editor_mode"], "textarea")
        self.assertEqual(items["media_ref"]["editor_mode"], "path")
        self.assertEqual(items["caption"]["editor_mode"], "text")

    def test_existing_logger_property_editor_modes_remain_text_and_enum(self) -> None:
        items = self._property_items_for_type("core.logger")

        self.assertEqual(items["message"]["editor_mode"], "text")
        self.assertEqual(items["level"]["editor_mode"], "enum")


if __name__ == "__main__":
    unittest.main()
