from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.artifact_refs import (
    format_managed_artifact_ref,
    format_staged_artifact_ref,
)
from ea_node_editor.persistence.project_codec import (
    collect_project_artifact_references,
    rewrite_project_artifact_refs,
)
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.manager import WorkspaceManager


class SerializerRoundTripMixin:
    def test_round_trip_preserves_workspace_view_and_graph(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        view = model.create_view(workspace.workspace_id, name="V2")
        model.set_active_view(workspace.workspace_id, view.view_id)
        node_a = model.add_node(workspace.workspace_id, "core.start", "Start", 10, 20)
        node_b = model.add_node(workspace.workspace_id, "core.end", "End", 80, 120)
        edge = model.add_edge(workspace.workspace_id, node_a.node_id, "exec_out", node_b.node_id, "exec_in")

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        self.assertEqual(loaded.active_workspace_id, workspace.workspace_id)
        loaded_ws = loaded.workspaces[workspace.workspace_id]
        self.assertEqual(loaded_ws.active_view_id, view.view_id)
        self.assertIn(node_a.node_id, loaded_ws.nodes)
        self.assertIn(node_b.node_id, loaded_ws.nodes)
        self.assertIn(edge.edge_id, loaded_ws.edges)

    def test_round_trip_preserves_custom_view_order(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        first_view_id = workspace.active_view_id
        second_view_id = model.create_view(workspace.workspace_id, name="Inspection").view_id
        third_view_id = model.create_view(workspace.workspace_id, name="Review").view_id
        model.move_view(workspace.workspace_id, 2, 0)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_workspace = loaded.workspaces[workspace.workspace_id]
        self.assertEqual(list(loaded_workspace.views), [third_view_id, first_view_id, second_view_id])
        self.assertEqual(loaded_workspace.active_view_id, third_view_id)

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
        state = workspace.capture_persistence_state()
        state.unresolved_node_docs["node_missing"] = {
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
        workspace.restore_persistence_state(state)

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

    def test_round_trip_preserves_node_and_edge_visual_metadata_contracts(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node_a = model.add_node(workspace.workspace_id, "core.start", "Start", 10, 20)
        node_b = model.add_node(workspace.workspace_id, "core.end", "End", 80, 120)
        node_a.visual_style = {"fill": "#102030", "badge": {"shape": "pill"}}
        node_b.visual_style = {"outline": {"width": 2}}
        edge = model.add_edge(workspace.workspace_id, node_a.node_id, "exec_out", node_b.node_id, "exec_in")
        edge.label = "Primary path"
        edge.visual_style = {"stroke": "dashed", "arrow": {"kind": "none"}}

        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        workspace_doc = next(ws for ws in doc["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node_a.node_id)
        edge_doc = next(item for item in workspace_doc["edges"] if item["edge_id"] == edge.edge_id)

        self.assertEqual(doc["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            doc["metadata"]["ui"]["passive_style_presets"],
            {"node_presets": [], "edge_presets": []},
        )
        self.assertEqual(
            doc["metadata"]["artifact_store"],
            {"artifacts": {}, "staged": {}},
        )
        self.assertEqual(node_doc["visual_style"], {"fill": "#102030", "badge": {"shape": "pill"}})
        self.assertEqual(edge_doc["label"], "Primary path")
        self.assertEqual(edge_doc["visual_style"], {"stroke": "dashed", "arrow": {"kind": "none"}})

        loaded = serializer.from_document(doc)
        loaded_ws = loaded.workspaces[workspace.workspace_id]

        self.assertEqual(
            loaded_ws.nodes[node_a.node_id].visual_style,
            {"fill": "#102030", "badge": {"shape": "pill"}},
        )
        self.assertEqual(loaded_ws.nodes[node_b.node_id].visual_style, {"outline": {"width": 2}})
        self.assertEqual(loaded_ws.edges[edge.edge_id].label, "Primary path")
        self.assertEqual(
            loaded_ws.edges[edge.edge_id].visual_style,
            {"stroke": "dashed", "arrow": {"kind": "none"}},
        )

    def test_round_trip_normalizes_project_local_passive_style_presets(self) -> None:
        model = GraphModel()
        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        doc["metadata"]["ui"]["passive_style_presets"] = {
            "node_presets": [
                {
                    "preset_id": "NodePresetBad",
                    "name": " Flow Warm ",
                    "style": {
                        "fill_color": "#112233",
                        "border_width": "2.5",
                        "ignored": True,
                    },
                },
                {
                    "preset_id": "",
                    "name": " ",
                    "style": {
                        "text_color": "#445566",
                        "font_size": "15",
                    },
                },
            ],
            "edge_presets": [
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": " Link ",
                    "style": {
                        "stroke_color": "#abcdef",
                        "stroke_width": "3",
                        "stroke_pattern": "dashed",
                        "arrow_head": "open",
                        "ignored": "value",
                    },
                },
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": "",
                    "style": {
                        "label_text_color": "#010203",
                        "label_background_color": "#AABBCC",
                    },
                },
            ],
        }

        loaded = serializer.from_document(doc)
        presets = loaded.metadata["ui"]["passive_style_presets"]

        self.assertEqual(len(presets["node_presets"]), 2)
        self.assertRegex(presets["node_presets"][0]["preset_id"], r"^node_preset_[0-9a-f]{8}$")
        self.assertRegex(presets["node_presets"][1]["preset_id"], r"^node_preset_[0-9a-f]{8}$")
        self.assertNotEqual(presets["node_presets"][0]["preset_id"], presets["node_presets"][1]["preset_id"])
        self.assertEqual(presets["node_presets"][0]["name"], "Flow Warm")
        self.assertEqual(presets["node_presets"][1]["name"], "Node Preset 2")
        self.assertEqual(
            presets["node_presets"][0]["style"],
            {
                "fill_color": "#112233",
                "border_width": 2.5,
            },
        )
        self.assertEqual(
            presets["node_presets"][1]["style"],
            {
                "text_color": "#445566",
                "font_size": 15,
            },
        )

        self.assertEqual(len(presets["edge_presets"]), 2)
        self.assertEqual(presets["edge_presets"][0]["preset_id"], "edge_preset_deadbeef")
        self.assertRegex(presets["edge_presets"][1]["preset_id"], r"^edge_preset_[0-9a-f]{8}$")
        self.assertNotEqual(presets["edge_presets"][0]["preset_id"], presets["edge_presets"][1]["preset_id"])
        self.assertEqual(presets["edge_presets"][0]["name"], "Link")
        self.assertEqual(presets["edge_presets"][1]["name"], "Edge Preset 2")
        self.assertEqual(
            presets["edge_presets"][0]["style"],
            {
                "stroke_color": "#abcdef",
                "stroke_width": 3.0,
                "stroke_pattern": "dashed",
                "arrow_head": "open",
            },
        )
        self.assertEqual(
            presets["edge_presets"][1]["style"],
            {
                "label_text_color": "#010203",
                "label_background_color": "#AABBCC",
            },
        )

        saved_doc = serializer.to_document(loaded)
        self.assertEqual(saved_doc["metadata"]["ui"]["passive_style_presets"], presets)

    def test_round_trip_preserves_passive_image_panel_properties_and_size(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Image Panel",
            25.0,
            45.0,
            properties={
                "source_path": r"C:\fixtures\diagram.png",
                "caption": "System overview\nRevision 2",
                "fit_mode": "cover",
            },
        )
        model.set_node_size(workspace.workspace_id, node.node_id, 348.0, 258.0)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_node = loaded.workspaces[workspace.workspace_id].nodes[node.node_id]
        self.assertEqual(loaded_node.type_id, "passive.media.image_panel")
        self.assertEqual(
            loaded_node.properties,
            {
                "source_path": r"C:\fixtures\diagram.png",
                "caption": "System overview\nRevision 2",
                "fit_mode": "cover",
            },
        )
        self.assertEqual(loaded_node.custom_width, 348.0)
        self.assertEqual(loaded_node.custom_height, 258.0)

    def test_load_preserves_sparse_passive_image_panel_properties_while_coercing_present_values(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        workspace_doc = next(ws for ws in doc["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        workspace_doc["nodes"].append(
            {
                "node_id": "node_image_panel_sparse",
                "type_id": "passive.media.image_panel",
                "title": "Image Panel",
                "x": 25.0,
                "y": 45.0,
                "collapsed": False,
                "properties": {
                    "source_path": r"C:\fixtures\diagram.png",
                    "fit_mode": "cover",
                    "crop_w": "0.5",
                    "crop_h": None,
                },
                "exposed_ports": {},
                "visual_style": {},
                "parent_node_id": None,
                "custom_width": 348.0,
                "custom_height": 258.0,
            }
        )

        loaded = serializer.from_document(doc)

        loaded_node = loaded.workspaces[workspace.workspace_id].nodes["node_image_panel_sparse"]
        self.assertEqual(
            loaded_node.properties,
            {
                "source_path": r"C:\fixtures\diagram.png",
                "fit_mode": "cover",
                "crop_w": 0.5,
                "crop_h": 1.0,
            },
        )

    def test_round_trip_preserves_passive_pdf_panel_properties_and_size(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "passive.media.pdf_panel",
            "PDF Panel",
            40.0,
            60.0,
            properties={
                "source_path": r"C:\fixtures\manual.pdf",
                "page_number": 4,
                "caption": "Review packet\nSecond pass",
            },
        )
        model.set_node_size(workspace.workspace_id, node.node_id, 312.0, 428.0)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_node = loaded.workspaces[workspace.workspace_id].nodes[node.node_id]
        self.assertEqual(loaded_node.type_id, "passive.media.pdf_panel")
        self.assertEqual(
            loaded_node.properties,
            {
                "source_path": r"C:\fixtures\manual.pdf",
                "page_number": 4,
                "caption": "Review packet\nSecond pass",
            },
        )
        self.assertEqual(loaded_node.custom_width, 312.0)
        self.assertEqual(loaded_node.custom_height, 428.0)

    def test_round_trip_preserves_workspace_order_active_workspace_and_view_cameras(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        manager.move_workspace(1, 0)
        manager.set_active_workspace(second)

        first_ws = model.project.workspaces[first]
        first_v1 = first_ws.views[first_ws.active_view_id]
        first_v1.zoom = 1.1
        first_v1.pan_x = 10.0
        first_v1.pan_y = 20.0
        first_v2 = model.create_view(first, name="V2")
        model.project.workspaces[first].views[first_v2.view_id].zoom = 1.8
        model.project.workspaces[first].views[first_v2.view_id].pan_x = 150.0
        model.project.workspaces[first].views[first_v2.view_id].pan_y = -45.0
        model.set_active_view(first, first_v2.view_id)

        second_ws = model.project.workspaces[second]
        second_v1 = second_ws.views[second_ws.active_view_id]
        second_v1.zoom = 0.85
        second_v1.pan_x = -12.0
        second_v1.pan_y = 34.0
        second_v2 = model.create_view(second, name="V2")
        model.project.workspaces[second].views[second_v2.view_id].zoom = 2.2
        model.project.workspaces[second].views[second_v2.view_id].pan_x = 300.0
        model.project.workspaces[second].views[second_v2.view_id].pan_y = 99.0
        model.set_active_view(second, second_v2.view_id)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        self.assertEqual(loaded.metadata.get("workspace_order"), [second, first])
        self.assertEqual(loaded.active_workspace_id, second)
        self.assertEqual(loaded.workspaces[first].active_view_id, first_v2.view_id)
        self.assertEqual(loaded.workspaces[second].active_view_id, second_v2.view_id)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].zoom, 1.1)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].pan_x, 10.0)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].pan_y, 20.0)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].zoom, 1.8)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].pan_x, 150.0)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].pan_y, -45.0)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].zoom, 0.85)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].pan_x, -12.0)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].pan_y, 34.0)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].zoom, 2.2)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].pan_x, 300.0)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].pan_y, 99.0)


class SerializerArtifactRoundTripPacketTests(unittest.TestCase):
    def test_round_trip_preserves_project_artifact_store_metadata_and_string_refs(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        artifact_id = "image_panel_source"
        managed_ref = format_managed_artifact_ref(artifact_id)
        node = model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Image Panel",
            25.0,
            45.0,
            properties={
                "source_path": managed_ref,
                "caption": "Managed image",
                "fit_mode": "contain",
            },
        )
        model.project.metadata["artifact_store"] = {
            "artifacts": {
                artifact_id: {
                    "path": r"assets\passive_media\node_image_panel\source.png",
                }
            }
        }

        serializer = JsonProjectSerializer(build_default_registry())
        document = serializer.to_persistent_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node.node_id)

        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(node_doc["properties"]["source_path"], managed_ref)
        self.assertEqual(
            document["metadata"]["artifact_store"],
            {
                "artifacts": {
                    artifact_id: {
                        "relative_path": "assets/passive_media/node_image_panel/source.png",
                    }
                },
                "staged": {},
            },
        )

        loaded = serializer.from_document(document)
        loaded_node = loaded.workspaces[workspace.workspace_id].nodes[node.node_id]
        self.assertEqual(loaded_node.properties["source_path"], managed_ref)
        self.assertEqual(
            loaded.metadata["artifact_store"],
            {
                "artifacts": {
                    artifact_id: {
                        "relative_path": "assets/passive_media/node_image_panel/source.png",
                    }
                },
                "staged": {},
            },
        )

    def test_collect_and_rewrite_artifact_refs_from_persistent_document(self) -> None:
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
        state = workspace.capture_persistence_state()
        state.unresolved_node_docs["node_missing"] = {
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
        workspace.restore_persistence_state(state)

        serializer = JsonProjectSerializer(build_default_registry())
        document = serializer.to_persistent_document(model.project)
        refs = collect_project_artifact_references(document)

        self.assertEqual(refs.managed_ids, frozenset({"existing_asset"}))
        self.assertEqual(
            refs.staged_ids,
            frozenset({"pending_output", "pending_gallery", "pending_hidden"}),
        )

        rewritten = rewrite_project_artifact_refs(
            document,
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
