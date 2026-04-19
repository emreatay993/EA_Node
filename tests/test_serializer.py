from __future__ import annotations

import copy
import unittest
from unittest import mock

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.builtins import ansys_dpf_catalog
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.plugin_contracts import AddOnManifest, AddOnRecord, AddOnState, PluginAvailability
from ea_node_editor.nodes.plugin_loader import discover_addon_records
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.overlay import MISSING_ADDON_PLACEHOLDER_KEY
from ea_node_editor.persistence.project_codec import ProjectPersistenceEnvelope
from ea_node_editor.persistence.serializer import JsonProjectSerializer, ProjectSessionMetadata
from ea_node_editor.settings import SCHEMA_VERSION
from tests.serializer.round_trip_cases import SerializerRoundTripMixin
from tests.serializer.schema_cases import SerializerSchemaMixin
from tests.serializer.workflow_cases import SerializerWorkflowMixin
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


def _test_dpf_addon_record() -> AddOnRecord:
    return AddOnRecord(
        manifest=AddOnManifest(
            addon_id=ANSYS_DPF_ADDON_ID,
            display_name="ANSYS DPF",
            apply_policy="hot_apply",
            version="",
            dependencies=("ansys.dpf.core",),
        ),
        state=AddOnState(enabled=True, pending_restart=False),
        availability=PluginAvailability.available(
            summary="ANSYS DPF is not loaded in this session."
        ),
        provided_node_type_ids=(
            "dpf.result_file",
            "dpf.model",
            "dpf.helper.streams_container.streams_container",
            "dpf.op.result.displacement",
        ),
    )


def _assert_dpf_placeholder_contract(test_case: unittest.TestCase, node_doc: dict[str, object]) -> None:
    placeholder = node_doc[MISSING_ADDON_PLACEHOLDER_KEY]
    test_case.assertEqual(placeholder["addon_id"], ANSYS_DPF_ADDON_ID)
    test_case.assertEqual(placeholder["display_name"], "ANSYS DPF")
    test_case.assertEqual(placeholder["apply_policy"], "hot_apply")
    test_case.assertEqual(placeholder["status"], "installed")
    test_case.assertEqual(
        placeholder["unavailable_reason"],
        "ANSYS DPF is not loaded in this session.",
    )
    test_case.assertEqual(
        placeholder["locked_state"],
        {
            "is_locked": True,
            "reason": "missing_addon",
            "label": "Requires add-on",
            "summary": "ANSYS DPF is not loaded in this session.",
            "focus_addon_id": ANSYS_DPF_ADDON_ID,
        },
    )


def _assert_unavailable_dpf_placeholder_contract(
    test_case: unittest.TestCase,
    node_doc: dict[str, object],
) -> None:
    placeholder = node_doc[MISSING_ADDON_PLACEHOLDER_KEY]
    test_case.assertEqual(placeholder["addon_id"], ANSYS_DPF_ADDON_ID)
    test_case.assertEqual(placeholder["display_name"], "ANSYS DPF")
    test_case.assertEqual(placeholder["apply_policy"], "hot_apply")
    test_case.assertEqual(placeholder["status"], "unavailable")
    test_case.assertEqual(
        placeholder["unavailable_reason"],
        "ansys.dpf.core is not installed; the DPF node family remains unavailable.",
    )
    test_case.assertEqual(
        placeholder["locked_state"],
        {
            "is_locked": True,
            "reason": "missing_addon",
            "label": "Requires add-on",
            "summary": "ansys.dpf.core is not installed; the DPF node family remains unavailable.",
            "focus_addon_id": ANSYS_DPF_ADDON_ID,
        },
    )


def _dpf_placeholder_round_trip_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_dpf_placeholder_round_trip",
        "name": "DPF Placeholder Round Trip",
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
                        "node_id": "node_dpf_model",
                        "type_id": "dpf.model",
                        "title": "Saved DPF Model",
                        "x": 180.0,
                        "y": 60.0,
                        "collapsed": True,
                        "properties": {"path": "C:/tmp/example.rst"},
                        "exposed_ports": {"result_file": True, "model": True},
                        "port_labels": {
                            "result_file": "Saved Result File",
                            "model": "Saved Model",
                        },
                        "visual_style": {"fill": "#334455"},
                        "custom_width": 312.0,
                        "custom_height": 144.0,
                        "parent_node_id": None,
                    }
                ],
                "edges": [],
            }
        ],
        "metadata": {},
    }


def _dpf_hidden_edge_placeholder_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_dpf_hidden_edge_placeholder",
        "name": "DPF Hidden Edge Placeholder",
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
                        "title": "Saved Result",
                        "x": 60.0,
                        "y": 40.0,
                        "collapsed": False,
                        "properties": {"path": "C:/tmp/example.rst"},
                        "exposed_ports": {"result_file": True, "exec_out": True},
                        "port_labels": {"result_file": "Saved Result File"},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_model",
                        "type_id": "dpf.model",
                        "title": "Saved Model",
                        "x": 320.0,
                        "y": 40.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"result_file": False, "model": True},
                        "port_labels": {
                            "result_file": "Hidden Saved Result File",
                            "model": "Saved Model",
                        },
                        "parent_node_id": None,
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_hidden_result_file",
                        "source_node_id": "node_result",
                        "source_port_key": "result_file",
                        "target_node_id": "node_model",
                        "target_port_key": "result_file",
                    }
                ],
            }
        ],
        "metadata": {},
    }


def _generated_dpf_placeholder_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_generated_dpf_placeholder",
        "name": "Generated DPF Placeholder",
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
                        "node_id": "node_streams_container",
                        "type_id": "dpf.helper.streams_container.streams_container",
                        "title": "Saved Streams Container",
                        "x": 40.0,
                        "y": 40.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"streams_container": True, "exec_out": True},
                        "port_labels": {"streams_container": "Saved Streams Container"},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_displacement",
                        "type_id": "dpf.op.result.displacement",
                        "title": "Saved Displacement",
                        "x": 340.0,
                        "y": 40.0,
                        "collapsed": True,
                        "properties": {"read_cyclic": 2, "phi": 90.0},
                        "exposed_ports": {"streams_container": False, "fields_container_2": True},
                        "port_labels": {
                            "streams_container": "Hidden Saved Streams Container",
                            "fields_container_2": "Saved Fields",
                        },
                        "parent_node_id": None,
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_generated_streams_container",
                        "source_node_id": "node_streams_container",
                        "source_port_key": "streams_container",
                        "target_node_id": "node_displacement",
                        "target_port_key": "streams_container",
                    }
                ],
            }
        ],
        "metadata": {},
    }


class SerializerTests(SerializerRoundTripMixin, SerializerWorkflowMixin, SerializerSchemaMixin, unittest.TestCase):
    def test_project_session_metadata_exposes_typed_substructures_and_preserves_extra_namespaces(self) -> None:
        metadata = ProjectSessionMetadata.from_mapping(
            {
                "ui": {
                    "script_editor": {
                        "visible": True,
                    },
                    "panel_state": {
                        "inspector": "expanded",
                    },
                },
                "workflow_settings": {
                    "solver_config": {
                        "thread_count": 16,
                    },
                },
                "artifact_store": {
                    "staged": {
                        "pending_output": {
                            "relative_path": "outputs/run.txt",
                            "slot": "process_run.stdout",
                        }
                    }
                },
            }
        )

        self.assertTrue(metadata.ui.script_editor.visible)
        self.assertFalse(metadata.ui.script_editor.floating)
        self.assertEqual(metadata.ui.extra["panel_state"], {"inspector": "expanded"})
        self.assertEqual(metadata.workflow_settings["solver_config"]["thread_count"], 16)
        self.assertIn("memory_limit_gb", metadata.workflow_settings["solver_config"])
        self.assertEqual(metadata.extra["artifact_store"]["staged"]["pending_output"]["slot"], "process_run.stdout")

        round_tripped = metadata.to_mapping()
        self.assertEqual(
            round_tripped["ui"]["script_editor"],
            {
                "visible": True,
                "floating": False,
            },
        )
        self.assertEqual(round_tripped["ui"]["panel_state"], {"inspector": "expanded"})
        self.assertEqual(
            round_tripped["artifact_store"],
            copy.deepcopy(metadata.extra["artifact_store"]),
        )

    def test_comment_backdrop_load_recomputes_membership_and_drops_persisted_membership_fields(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        backdrop = model.add_node(
            workspace.workspace_id,
            "passive.annotation.comment_backdrop",
            "Comment Backdrop",
            80.0,
            80.0,
        )
        model.set_node_size(workspace.workspace_id, backdrop.node_id, 360.0, 240.0)
        logger = model.add_node(workspace.workspace_id, "core.logger", "Logger", 140.0, 140.0)

        serializer = JsonProjectSerializer(registry)
        document = serializer.to_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        backdrop_doc = next(node for node in workspace_doc["nodes"] if node["node_id"] == backdrop.node_id)
        logger_doc = next(node for node in workspace_doc["nodes"] if node["node_id"] == logger.node_id)
        backdrop_doc.update(
            {
                "owner_backdrop_id": "stale-owner",
                "backdrop_depth": 99,
                "member_node_ids": ["stale-node"],
                "member_backdrop_ids": ["stale-backdrop"],
                "contained_node_ids": ["stale-node"],
                "contained_backdrop_ids": ["stale-backdrop"],
            }
        )
        logger_doc.update(
            {
                "owner_backdrop_id": "wrong-backdrop",
                "backdrop_depth": 42,
            }
        )

        loaded_project = serializer.from_document(document)
        reserialized = serializer.to_document(loaded_project)
        reserialized_workspace_doc = next(
            ws for ws in reserialized["workspaces"] if ws["workspace_id"] == workspace.workspace_id
        )
        serialized_nodes = {
            node["node_id"]: node
            for node in reserialized_workspace_doc["nodes"]
        }
        for node_id in (backdrop.node_id, logger.node_id):
            for key in (
                "owner_backdrop_id",
                "backdrop_depth",
                "member_node_ids",
                "member_backdrop_ids",
                "contained_node_ids",
                "contained_backdrop_ids",
            ):
                self.assertNotIn(key, serialized_nodes[node_id])

        loaded_model = GraphModel(loaded_project)
        scene = GraphSceneBridge()
        scene.set_workspace(loaded_model, registry, workspace.workspace_id)
        payloads = {
            payload["node_id"]: payload
            for payload in [*scene.nodes_model, *scene.backdrop_nodes_model]
        }
        self.assertEqual(payloads[logger.node_id]["owner_backdrop_id"], backdrop.node_id)
        self.assertEqual(payloads[logger.node_id]["backdrop_depth"], 1)
        self.assertEqual(payloads[backdrop.node_id]["member_node_ids"], [logger.node_id])


class SerializerPortLockingTests(unittest.TestCase):
    def test_persistent_document_round_trip_preserves_locked_ports_and_view_filters(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Logger",
            120.0,
            80.0,
            properties={"message": "inline"},
        )
        node.locked_ports = {"message": True, "shadow": False}
        view = workspace.views[workspace.active_view_id]
        view.hide_locked_ports = True
        view.hide_optional_ports = True

        document = serializer.to_persistent_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node.node_id)
        view_doc = next(item for item in workspace_doc["views"] if item["view_id"] == view.view_id)

        self.assertEqual(node_doc["locked_ports"], {"message": True, "shadow": False})
        self.assertTrue(view_doc["hide_locked_ports"])
        self.assertTrue(view_doc["hide_optional_ports"])

        loaded = serializer.from_document(document)
        loaded_workspace = loaded.workspaces[workspace.workspace_id]
        loaded_node = loaded_workspace.nodes[node.node_id]
        loaded_view = loaded_workspace.views[view.view_id]

        self.assertEqual(loaded_node.locked_ports, {"message": True, "shadow": False})
        self.assertTrue(loaded_view.hide_locked_ports)
        self.assertTrue(loaded_view.hide_optional_ports)

    def test_load_defaults_locked_ports_and_view_filters_when_fields_are_missing(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Logger",
            40.0,
            60.0,
        )

        document = serializer.to_persistent_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node.node_id)
        view_doc = next(item for item in workspace_doc["views"] if item["view_id"] == workspace.active_view_id)
        node_doc.pop("locked_ports", None)
        view_doc.pop("hide_locked_ports", None)
        view_doc.pop("hide_optional_ports", None)

        loaded = serializer.from_document(document)
        loaded_workspace = loaded.workspaces[workspace.workspace_id]
        loaded_node = loaded_workspace.nodes[node.node_id]
        loaded_view = loaded_workspace.views[workspace.active_view_id]

        self.assertEqual(loaded_node.locked_ports, {})
        self.assertFalse(loaded_view.hide_locked_ports)
        self.assertFalse(loaded_view.hide_optional_ports)


class SerializerDpfPlaceholderTests(unittest.TestCase):
    def test_unavailable_registered_addon_still_projects_first_load_placeholder_metadata(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _dpf_placeholder_round_trip_payload()

        with mock.patch.object(ansys_dpf_catalog, "_find_spec", return_value=None):
            records = discover_addon_records()
            dpf_record = next(record for record in records if record.addon_id == ANSYS_DPF_ADDON_ID)
            self.assertEqual(dpf_record.status, "unavailable")
            self.assertEqual(dpf_record.provided_node_type_ids, ())

            project = serializer.from_document(copy.deepcopy(payload))
            workspace = project.workspaces["ws_dpf"]
            self.assertEqual(set(workspace.unresolved_node_docs), {"node_dpf_model"})
            _assert_unavailable_dpf_placeholder_contract(
                self,
                workspace.unresolved_node_docs["node_dpf_model"],
            )

            scene = GraphSceneBridge()
            scene.set_workspace(GraphModel(project), NodeRegistry(), "ws_dpf")
            payloads = {node_payload["node_id"]: node_payload for node_payload in scene.nodes_model}
            node_payload = payloads["node_dpf_model"]

            self.assertTrue(node_payload["unresolved"])
            self.assertTrue(node_payload["read_only"])
            self.assertEqual(node_payload["addon_id"], ANSYS_DPF_ADDON_ID)
            self.assertEqual(node_payload["addon_status"], "unavailable")
            self.assertEqual(
                node_payload["unavailable_reason"],
                "ansys.dpf.core is not installed; the DPF node family remains unavailable.",
            )
            self.assertEqual(
                node_payload["locked_state"],
                {
                    "is_locked": True,
                    "reason": "missing_addon",
                    "label": "Requires add-on",
                    "summary": "ansys.dpf.core is not installed; the DPF node family remains unavailable.",
                    "focus_addon_id": ANSYS_DPF_ADDON_ID,
                },
            )

    def test_persistent_document_round_trip_preserves_unresolved_dpf_node_payload(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _dpf_placeholder_round_trip_payload()

        with mock.patch(
            "ea_node_editor.persistence.overlay.discover_addon_records",
            return_value=(_test_dpf_addon_record(),),
        ):
            project = serializer.from_document(copy.deepcopy(payload))
            workspace = project.workspaces["ws_dpf"]

            self.assertEqual(workspace.nodes, {})
            self.assertEqual(set(workspace.unresolved_node_docs), {"node_dpf_model"})
            _assert_dpf_placeholder_contract(self, workspace.unresolved_node_docs["node_dpf_model"])

            authored_document = serializer.to_persistent_document(project)
            workspace_doc = authored_document["workspaces"][0]
            node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == "node_dpf_model")
            for key, value in payload["workspaces"][0]["nodes"][0].items():
                self.assertEqual(node_doc[key], value)
            _assert_dpf_placeholder_contract(self, node_doc)

            runtime_document = serializer.to_document(project)
            runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_document)
            self.assertEqual(
                set(runtime_envelope.workspace_envelope("ws_dpf").unresolved_node_docs),
                {"node_dpf_model"},
            )
            _assert_dpf_placeholder_contract(
                self,
                runtime_envelope.workspace_envelope("ws_dpf").unresolved_node_docs["node_dpf_model"],
            )

    def test_persistent_document_round_trip_preserves_hidden_port_edges_for_unresolved_dpf_nodes(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _dpf_hidden_edge_placeholder_payload()

        with mock.patch(
            "ea_node_editor.persistence.overlay.discover_addon_records",
            return_value=(_test_dpf_addon_record(),),
        ):
            project = serializer.from_document(copy.deepcopy(payload))
            workspace = project.workspaces["ws_dpf"]

            self.assertEqual(workspace.nodes, {})
            self.assertEqual(set(workspace.unresolved_node_docs), {"node_model", "node_result"})
            self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_hidden_result_file"})
            self.assertFalse(workspace.unresolved_node_docs["node_model"]["exposed_ports"]["result_file"])
            _assert_dpf_placeholder_contract(self, workspace.unresolved_node_docs["node_model"])
            _assert_dpf_placeholder_contract(self, workspace.unresolved_node_docs["node_result"])

            authored_document = serializer.to_persistent_document(project)
            workspace_doc = authored_document["workspaces"][0]
            node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == "node_model")
            edge_doc = next(item for item in workspace_doc["edges"] if item["edge_id"] == "edge_hidden_result_file")
            self.assertFalse(node_doc["exposed_ports"]["result_file"])
            self.assertEqual(edge_doc, payload["workspaces"][0]["edges"][0])
            _assert_dpf_placeholder_contract(self, node_doc)

            runtime_document = serializer.to_document(project)
            runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_document)
            self.assertEqual(
                set(runtime_envelope.workspace_envelope("ws_dpf").unresolved_edge_docs),
                {"edge_hidden_result_file"},
            )
            _assert_dpf_placeholder_contract(
                self,
                runtime_envelope.workspace_envelope("ws_dpf").unresolved_node_docs["node_model"],
            )

    def test_generated_dpf_placeholder_projection_preserves_saved_properties_and_labels(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _generated_dpf_placeholder_payload()

        with mock.patch(
            "ea_node_editor.persistence.overlay.discover_addon_records",
            return_value=(_test_dpf_addon_record(),),
        ):
            project = serializer.from_document(copy.deepcopy(payload))
            runtime_document = serializer.to_document(project)
            runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_document)
            self.assertEqual(
                set(runtime_envelope.workspace_envelope("ws_dpf").unresolved_edge_docs),
                {"edge_generated_streams_container"},
            )

            loaded_model = GraphModel(project)
            scene = GraphSceneBridge()
            scene.set_workspace(loaded_model, NodeRegistry(), "ws_dpf")

            payloads = {payload["node_id"]: payload for payload in scene.nodes_model}
            displacement = payloads["node_displacement"]
            streams_container = payloads["node_streams_container"]

            self.assertTrue(displacement["unresolved"])
            self.assertTrue(displacement["read_only"])
            self.assertEqual(displacement["addon_id"], ANSYS_DPF_ADDON_ID)
            self.assertEqual(displacement["addon_display_name"], "ANSYS DPF")
            self.assertEqual(displacement["addon_apply_policy"], "hot_apply")
            self.assertEqual(displacement["addon_status"], "installed")
            self.assertEqual(displacement["unavailable_reason"], "ANSYS DPF is not loaded in this session.")
            self.assertEqual(
                displacement["locked_state"],
                {
                    "is_locked": True,
                    "reason": "missing_addon",
                    "label": "Requires add-on",
                    "summary": "ANSYS DPF is not loaded in this session.",
                    "focus_addon_id": ANSYS_DPF_ADDON_ID,
                },
            )
            self.assertEqual(displacement["properties"], {"read_cyclic": 2, "phi": 90.0})
            self.assertEqual(
                {port["key"]: port["label"] for port in streams_container["ports"]}["streams_container"],
                "Saved Streams Container",
            )
            self.assertEqual(
                {port["key"]: port["label"] for port in displacement["ports"]}["fields_container_2"],
                "Saved Fields",
            )
            self.assertNotIn(
                "streams_container",
                {port["key"] for port in displacement["ports"]},
            )


if __name__ == "__main__":
    unittest.main()
