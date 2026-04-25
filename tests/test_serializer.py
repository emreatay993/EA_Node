from __future__ import annotations

import copy
import unittest

from ea_node_editor.execution.compiler import compile_workspace_document
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.artifact_refs import (
    format_managed_artifact_ref,
    format_staged_artifact_ref,
)
from ea_node_editor.persistence.project_codec import (
    PERSISTENCE_ENVELOPE_KEY,
    ProjectDocumentFlavor,
    ProjectPersistenceEnvelope,
    collect_project_artifact_references,
    rewrite_project_artifact_refs,
)
from ea_node_editor.persistence.serializer import JsonProjectSerializer, ProjectSessionMetadata
from ea_node_editor.settings import SCHEMA_VERSION
from tests.serializer.base_cases import (
    _current_schema_inconsistent_payload,
    _missing_plugin_parent_payload,
    _missing_plugin_round_trip_payload,
)
from tests.serializer.round_trip_cases import SerializerRoundTripMixin
from tests.serializer.schema_cases import SerializerSchemaMixin, _missing_addon_round_trip_payload, _test_addon_record
from tests.serializer.workflow_cases import SerializerWorkflowMixin
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


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
    def test_round_trip_artifact_ref_helpers_collect_and_rewrite_persistent_document(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Image Panel",
            25.0,
            45.0,
            properties={
                "source_path": format_staged_artifact_ref("pending_output"),
                "fallback": format_managed_artifact_ref("existing_asset"),
                "gallery": [format_staged_artifact_ref("pending_gallery")],
            },
        )
        workspace.unresolved_node_docs = {
            "node_missing": {
                "node_id": "node_missing",
                "type_id": "missing.node",
                "title": "Missing",
                "x": 5.0,
                "y": 7.0,
                "properties": {
                    "source_path": format_staged_artifact_ref("pending_hidden"),
                },
                "exposed_ports": {},
                "visual_style": {},
                "parent_node_id": None,
            }
        }

        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_persistent_document(model.project)
        refs = collect_project_artifact_references(doc)

        self.assertEqual(refs.managed_ids, frozenset({"existing_asset"}))
        self.assertEqual(
            refs.staged_ids,
            frozenset({"pending_output", "pending_gallery", "pending_hidden"}),
        )

        rewritten = rewrite_project_artifact_refs(
            doc,
            {
                format_staged_artifact_ref("pending_output"): format_managed_artifact_ref("pending_output"),
                format_staged_artifact_ref("pending_hidden"): format_managed_artifact_ref("pending_hidden"),
            },
        )
        workspace_doc = next(ws for ws in rewritten["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        resolved_node = next(item for item in workspace_doc["nodes"] if item["node_id"] == node.node_id)
        missing_node = next(item for item in workspace_doc["nodes"] if item["node_id"] == "node_missing")

        self.assertEqual(
            resolved_node["properties"],
            {
                "source_path": format_managed_artifact_ref("pending_output"),
                "fallback": format_managed_artifact_ref("existing_asset"),
                "gallery": [format_staged_artifact_ref("pending_gallery")],
            },
        )
        self.assertEqual(
            missing_node["properties"]["source_path"],
            format_managed_artifact_ref("pending_hidden"),
        )

    def test_collect_and_rewrite_artifact_refs_from_persistent_document(self) -> None:
        self.test_round_trip_artifact_ref_helpers_collect_and_rewrite_persistent_document()

    def test_current_schema_fixture_repairs_invalid_hidden_and_duplicate_edges(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _current_schema_inconsistent_payload()
        project = serializer.from_document(payload)

        workspace = project.workspaces["ws_legacy"]
        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.edges), {"edge_valid"})
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_unknown"})

        round_tripped = serializer.to_persistent_document(project)
        workspace_doc = round_tripped["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        edges_by_id = {edge["edge_id"]: edge for edge in workspace_doc["edges"]}
        self.assertEqual(nodes_by_id["node_unknown"], payload["workspaces"][0]["nodes"][2])
        self.assertEqual(edges_by_id["edge_unknown"], payload["workspaces"][0]["edges"][3])

    def test_round_trip_preserves_missing_plugin_payload_across_normalization(self) -> None:
        registry = build_default_registry()
        serializer = JsonProjectSerializer(registry)
        payload = _missing_plugin_round_trip_payload()

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws_plugin"]

        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(workspace.edges), {"edge_valid"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_unknown_to_known"})

        normalize_project_for_registry(project, registry)
        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.edges), {"edge_valid"})
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_unknown_to_known"})

        runtime_doc = serializer.to_document(project)
        runtime_workspace_doc = runtime_doc["workspaces"][0]
        self.assertEqual(
            [node["node_id"] for node in runtime_workspace_doc["nodes"]],
            ["node_end", "node_start"],
        )
        self.assertEqual([edge["edge_id"] for edge in runtime_workspace_doc["edges"]], ["edge_valid"])
        runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_doc)
        self.assertEqual(runtime_envelope.document_flavor, ProjectDocumentFlavor.RUNTIME)
        self.assertEqual(
            set(runtime_envelope.workspace_envelope("ws_plugin").unresolved_node_docs),
            {"node_unknown"},
        )
        self.assertEqual(
            set(runtime_envelope.workspace_envelope("ws_plugin").unresolved_edge_docs),
            {"edge_unknown_to_known"},
        )

        compiled = compile_workspace_document(runtime_workspace_doc, registry)
        self.assertEqual(
            [node["node_id"] for node in compiled["nodes"]],
            ["node_end", "node_start"],
        )
        self.assertEqual(
            compiled["edges"],
            [
                {
                    "source_node_id": "node_start",
                    "source_port_key": "exec_out",
                    "target_node_id": "node_end",
                    "target_port_key": "exec_in",
                }
            ],
        )

        reloaded_from_runtime_doc = serializer.from_document(runtime_doc)
        reloaded_workspace = reloaded_from_runtime_doc.workspaces["ws_plugin"]
        self.assertEqual(set(reloaded_workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(reloaded_workspace.unresolved_edge_docs), {"edge_unknown_to_known"})

        authored_doc = serializer.to_persistent_document(project)
        workspace_doc = authored_doc["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        edges_by_id = {edge["edge_id"]: edge for edge in workspace_doc["edges"]}
        self.assertEqual(nodes_by_id["node_unknown"], payload["workspaces"][0]["nodes"][1])
        self.assertEqual(edges_by_id["edge_unknown_to_known"], payload["workspaces"][0]["edges"][1])

    def test_round_trip_preserves_missing_addon_placeholder_contract_across_normalization(self) -> None:
        registry = build_default_registry()
        serializer = JsonProjectSerializer(registry)
        payload = _missing_addon_round_trip_payload()

        with unittest.mock.patch(
            "ea_node_editor.persistence.overlay.discover_addon_records",
            return_value=(_test_addon_record(),),
        ):
            project = serializer.from_document(payload)
            workspace = project.workspaces["ws_addon"]

            self.assertNotIn("node_signal_transform", workspace.nodes)
            placeholder_doc = workspace.unresolved_node_docs["node_signal_transform"]
            placeholder = placeholder_doc["_missing_addon_placeholder"]
            self.assertEqual(placeholder["addon_id"], "tests.addons.signal_pack")
            self.assertEqual(placeholder["display_name"], "Signal Pack")

            runtime_doc = serializer.to_document(project)
            runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_doc)
            runtime_placeholder = runtime_envelope.workspace_envelope("ws_addon").unresolved_node_docs[
                "node_signal_transform"
            ]["_missing_addon_placeholder"]
            self.assertEqual(runtime_placeholder["locked_state"]["focus_addon_id"], "tests.addons.signal_pack")

            authored_doc = serializer.to_persistent_document(project)
        workspace_doc = authored_doc["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        edges_by_id = {edge["edge_id"]: edge for edge in workspace_doc["edges"]}
        self.assertEqual(nodes_by_id["node_signal_transform"]["plugin_payload"], {"preset": "band-pass"})
        self.assertIn("_missing_addon_placeholder", nodes_by_id["node_signal_transform"])
        self.assertIn("edge_signal_to_end", edges_by_id)

    def test_from_document_sanitizes_live_parent_links_to_unresolved_nodes(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _missing_plugin_parent_payload()

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws"]

        self.assertEqual(sorted(workspace.nodes), ["known_child"])
        self.assertEqual(sorted(workspace.unresolved_node_docs), ["missing_shell"])
        self.assertIsNone(workspace.nodes["known_child"].parent_node_id)
        self.assertEqual(
            workspace.authored_node_overrides["known_child"],
            {"parent_node_id": "missing_shell"},
        )

        authored_doc = serializer.to_persistent_document(project)
        workspace_doc = authored_doc["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        self.assertEqual(nodes_by_id["known_child"]["parent_node_id"], "missing_shell")
        self.assertIn("missing_shell", nodes_by_id)

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
    def test_unavailable_registered_addon_nodes_are_kept_in_persistence_state_not_live_graph(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _dpf_placeholder_round_trip_payload()

        project = serializer.from_document(copy.deepcopy(payload))
        workspace = project.workspaces["ws_dpf"]
        self.assertEqual(workspace.nodes, {})
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_dpf_model"})

        scene = GraphSceneBridge()
        scene.set_workspace(GraphModel(project), NodeRegistry(), "ws_dpf")
        self.assertEqual(list(scene.nodes_model), [])

    def test_persistent_document_round_trip_preserves_unresolved_dpf_node_payload(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _dpf_placeholder_round_trip_payload()

        project = serializer.from_document(copy.deepcopy(payload))
        workspace = project.workspaces["ws_dpf"]

        self.assertEqual(workspace.nodes, {})

        authored_document = serializer.to_persistent_document(project)
        workspace_doc = authored_document["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        self.assertIn("node_dpf_model", nodes_by_id)

        runtime_document = serializer.to_document(project)
        self.assertIn(PERSISTENCE_ENVELOPE_KEY, runtime_document["metadata"])
        runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_document)
        self.assertEqual(
            set(runtime_envelope.workspace_envelope("ws_dpf").unresolved_node_docs),
            {"node_dpf_model"},
        )

    def test_persistent_document_round_trip_preserves_hidden_port_edges_for_unresolved_dpf_nodes(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _dpf_hidden_edge_placeholder_payload()

        project = serializer.from_document(copy.deepcopy(payload))
        workspace = project.workspaces["ws_dpf"]

        self.assertEqual(workspace.nodes, {})
        self.assertEqual(workspace.edges, {})
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_result", "node_model"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_hidden_result_file"})

        authored_document = serializer.to_persistent_document(project)
        workspace_doc = authored_document["workspaces"][0]
        self.assertEqual(
            {node["node_id"] for node in workspace_doc["nodes"]},
            {"node_result", "node_model"},
        )
        self.assertEqual(
            {edge["edge_id"] for edge in workspace_doc["edges"]},
            {"edge_hidden_result_file"},
        )

    def test_generated_dpf_placeholder_projection_is_deferred_to_persistence_envelope(self) -> None:
        serializer = JsonProjectSerializer(NodeRegistry())
        payload = _generated_dpf_placeholder_payload()

        project = serializer.from_document(copy.deepcopy(payload))
        runtime_document = serializer.to_document(project)
        self.assertIn(PERSISTENCE_ENVELOPE_KEY, runtime_document["metadata"])
        runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_document)
        self.assertEqual(
            set(runtime_envelope.workspace_envelope("ws_dpf").unresolved_node_docs),
            {"node_streams_container", "node_displacement"},
        )

        loaded_model = GraphModel(project)
        scene = GraphSceneBridge()
        scene.set_workspace(loaded_model, NodeRegistry(), "ws_dpf")

        self.assertEqual(list(scene.nodes_model), [])


if __name__ == "__main__":
    unittest.main()
