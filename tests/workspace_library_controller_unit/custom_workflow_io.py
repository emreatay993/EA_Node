from __future__ import annotations

from tests.workspace_library_controller_unit.support import *  # noqa: F401,F403


class WorkspaceLibraryControllerCustomWorkflowIOTests(WorkspaceLibraryControllerUnitTestBase):
    def test_publish_custom_workflow_from_selected_subnode_persists_snapshot(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()

        shell = host.model.add_node(
            workspace_id,
            type_id="core.subnode",
            title="Reusable Shell",
            x=120.0,
            y=80.0,
            properties=host.registry.default_properties("core.subnode"),
            exposed_ports={},
        )
        pin = host.model.add_node(
            workspace_id,
            type_id="core.subnode_output",
            title="Subnode Output",
            x=260.0,
            y=120.0,
            properties=host.registry.default_properties("core.subnode_output"),
            exposed_ports={"pin": True},
        )
        pin.parent_node_id = shell.node_id
        pin.properties["label"] = "Exec Out"
        pin.properties["kind"] = "exec"
        pin.properties["data_type"] = "any"
        shell.exposed_ports[pin.node_id] = True
        host.scene._selected_node_id = shell.node_id

        published = controller.publish_custom_workflow_from_selected_subnode()

        self.assertTrue(published.ok)
        self.assertTrue(published.payload)
        definitions = host.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        definition = definitions[0]
        self.assertEqual(definition["name"], "Reusable Shell")
        self.assertEqual(definition["revision"], 1)
        self.assertEqual(definition["ports"][0]["direction"], "out")
        self.assertEqual(definition["ports"][0]["kind"], "exec")
        self.assertEqual(definition["fragment"]["kind"], "ea-node-editor/graph-fragment")
        self.assertEqual(host.project_meta_changed.calls, 1)
        self.assertEqual(host.node_library_changed.calls, 1)
        library_items = controller.custom_workflow_library_items()
        self.assertEqual(len(library_items), 1)
        self.assertTrue(str(library_items[0]["type_id"]).startswith("custom_workflow:"))

    def test_publish_custom_workflow_from_current_scope_updates_revision(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()

        shell = host.model.add_node(
            workspace_id,
            type_id="core.subnode",
            title="Scoped Shell",
            x=80.0,
            y=40.0,
            properties=host.registry.default_properties("core.subnode"),
            exposed_ports={},
        )
        pin = host.model.add_node(
            workspace_id,
            type_id="core.subnode_input",
            title="Subnode Input",
            x=30.0,
            y=100.0,
            properties=host.registry.default_properties("core.subnode_input"),
            exposed_ports={"pin": True},
        )
        pin.parent_node_id = shell.node_id
        pin.properties["label"] = "Payload A"
        shell.exposed_ports[pin.node_id] = True
        host.scene.active_scope_path = [shell.node_id]

        first_publish = controller.publish_custom_workflow_from_current_scope()
        self.assertTrue(first_publish.ok)

        pin.properties["label"] = "Payload B"
        second_publish = controller.publish_custom_workflow_from_current_scope()
        self.assertTrue(second_publish.ok)

        definitions = host.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        definition = definitions[0]
        self.assertEqual(definition["name"], "Scoped Shell")
        self.assertEqual(definition["revision"], 2)
        self.assertEqual(definition["ports"][0]["label"], "Payload B")

    def test_export_custom_workflow_writes_eawf_payload(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        definitions = [
            {
                "workflow_id": "wf_export",
                "name": "Workflow Export",
                "description": "Export test",
                "revision": 3,
                "ports": [
                    {
                        "key": "exec_out",
                        "label": "Exec Out",
                        "direction": "out",
                        "kind": "exec",
                        "data_type": "any",
                    }
                ],
                "fragment": {
                    "kind": "ea-node-editor/graph-fragment",
                    "version": 1,
                    "nodes": [],
                    "edges": [],
                },
            }
        ]
        host.model.project.metadata["custom_workflows"] = definitions
        controller._prompt_custom_workflow_export_definition = lambda items: items[0]  # type: ignore[method-assign]

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "workflow_export"
            with (
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_path), "Custom Workflow (*.eawf)"),
                ),
                patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
                patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
            ):
                controller.export_custom_workflow()

            saved_path = target_path.with_suffix(".eawf")
            self.assertTrue(saved_path.exists())
            imported = import_custom_workflow_file(saved_path)

        self.assertEqual(imported["workflow_id"], "wf_export")
        self.assertEqual(imported["name"], "Workflow Export")
        self.assertEqual(imported["revision"], 3)
        self.assertEqual(imported["ports"][0]["label"], "Exec Out")
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)

    def test_custom_workflow_export_label_hides_internal_workflow_id(self) -> None:
        label = WorkspaceLibraryController._custom_workflow_export_label(
            {
                "workflow_id": "wf_export",
                "name": "Workflow Export",
                "revision": 3,
            }
        )
        self.assertEqual(label, "Workflow Export (rev 3)")
        self.assertNotIn("wf_export", label)

    def test_import_custom_workflow_replaces_existing_definition_and_emits_signals(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        host.model.project.metadata["custom_workflows"] = [
            {
                "workflow_id": "wf_sync",
                "name": "Old Name",
                "description": "old",
                "revision": 1,
                "ports": [
                    {
                        "key": "exec_out",
                        "label": "Old",
                        "direction": "out",
                        "kind": "exec",
                        "data_type": "any",
                    }
                ],
                "fragment": {"kind": "ea-node-editor/graph-fragment", "version": 1, "nodes": [], "edges": []},
            }
        ]
        imported_definition = {
            "workflow_id": "wf_sync",
            "name": "Imported Name",
            "description": "new",
            "revision": 7,
            "ports": [
                {
                    "key": "payload",
                    "label": "Payload",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "json",
                }
            ],
            "fragment": {"kind": "ea-node-editor/graph-fragment", "version": 1, "nodes": [], "edges": []},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            import_path = export_custom_workflow_file(imported_definition, Path(temp_dir) / "import_target")
            with (
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                    return_value=(str(import_path), "Custom Workflow (*.eawf)"),
                ),
                patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
                patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
            ):
                controller.import_custom_workflow()

        definitions = host.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0], imported_definition)
        self.assertEqual(host.project_meta_changed.calls, 1)
        self.assertEqual(host.node_library_changed.calls, 1)
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)

