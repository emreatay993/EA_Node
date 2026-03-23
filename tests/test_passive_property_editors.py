from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.controllers.workspace_view_nav_ops import WorkspaceViewNavOps
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

    def test_planning_family_long_form_fields_use_textarea(self) -> None:
        task_items = self._property_items_for_type("passive.planning.task_card")
        risk_items = self._property_items_for_type("passive.planning.risk_card")
        decision_items = self._property_items_for_type("passive.planning.decision_card")

        self.assertEqual(task_items["body"]["editor_mode"], "textarea")
        self.assertEqual(risk_items["body"]["editor_mode"], "textarea")
        self.assertEqual(risk_items["mitigation"]["editor_mode"], "textarea")
        self.assertEqual(decision_items["body"]["editor_mode"], "textarea")
        self.assertEqual(decision_items["outcome"]["editor_mode"], "textarea")
        self.assertEqual(task_items["owner"]["editor_mode"], "text")
        self.assertEqual(task_items["status"]["editor_mode"], "enum")

    def test_annotation_family_uses_textarea_only_for_body_fields(self) -> None:
        sticky_items = self._property_items_for_type("passive.annotation.sticky_note")
        callout_items = self._property_items_for_type("passive.annotation.callout")
        section_items = self._property_items_for_type("passive.annotation.section_header")

        self.assertEqual(sticky_items["body"]["editor_mode"], "textarea")
        self.assertEqual(callout_items["body"]["editor_mode"], "textarea")
        self.assertEqual(sticky_items["title"]["editor_mode"], "text")
        self.assertEqual(section_items["title"]["editor_mode"], "text")
        self.assertEqual(section_items["subtitle"]["editor_mode"], "text")

    def test_flowchart_family_exposes_text_title_editor(self) -> None:
        decision_items = self._property_items_for_type("passive.flowchart.decision")
        database_items = self._property_items_for_type("passive.flowchart.database")
        decision_spec = self.registry.get_spec("passive.flowchart.decision")
        decision_body = next(prop for prop in decision_spec.properties if prop.key == "body")

        self.assertEqual(decision_items["title"]["editor_mode"], "text")
        self.assertEqual(decision_items["title"]["value"], "Decision")
        self.assertEqual(decision_items["body"]["editor_mode"], "textarea")
        self.assertEqual(decision_items["body"]["value"], "Decision")
        self.assertEqual(database_items["title"]["editor_mode"], "text")
        self.assertEqual(database_items["title"]["value"], "Database")
        self.assertEqual(database_items["body"]["editor_mode"], "textarea")
        self.assertEqual(database_items["body"]["value"], "Database")
        self.assertTrue(WorkspaceViewNavOps._property_is_content_searchable(decision_body))


if __name__ == "__main__":
    unittest.main()
