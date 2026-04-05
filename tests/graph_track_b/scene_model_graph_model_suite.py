from __future__ import annotations

import unittest
from unittest.mock import Mock

from ea_node_editor.graph.boundary_adapters import build_graph_boundary_adapters
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.mutation_service import WorkspaceMutationService
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder


class GraphModelTrackBTests(unittest.TestCase):
    def test_add_move_connect_remove_node_operations(self) -> None:
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        source = model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
        target = model.add_node(workspace_id, "core.end", "End", 300.0, 80.0)

        model.set_node_position(workspace_id, source.node_id, 25.0, 45.0)
        moved = model.project.workspaces[workspace_id].nodes[source.node_id]
        self.assertEqual((moved.x, moved.y), (25.0, 45.0))

        edge = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        duplicate = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        self.assertEqual(edge.edge_id, duplicate.edge_id)
        self.assertEqual(len(model.project.workspaces[workspace_id].edges), 1)

        model.remove_node(workspace_id, source.node_id)
        workspace = model.project.workspaces[workspace_id]
        self.assertNotIn(source.node_id, workspace.nodes)
        self.assertEqual(workspace.edges, {})

    def test_validated_mutation_boundary_prunes_subnode_edges_when_pin_kind_changes(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        mutations = model.validated_mutations(workspace.workspace_id, registry)
        self.assertIsInstance(mutations, WorkspaceMutationService)

        def _add_node(
            type_id: str,
            title: str,
            x: float,
            y: float,
            *,
            parent_node_id: str | None = None,
        ):
            spec = registry.get_spec(type_id)
            return mutations.add_node(
                type_id=type_id,
                title=title,
                x=x,
                y=y,
                properties=registry.default_properties(type_id),
                exposed_ports={port.key: port.exposed for port in spec.ports},
                parent_node_id=parent_node_id,
            )

        source = _add_node("core.start", "Start", 0.0, 0.0)
        shell = _add_node("core.subnode", "Shell", 240.0, 40.0)
        pin_in = _add_node("core.subnode_input", "Input", 40.0, 80.0, parent_node_id=shell.node_id)
        inner = _add_node("core.logger", "Inner", 320.0, 140.0, parent_node_id=shell.node_id)

        mutations.set_node_property(pin_in.node_id, "kind", "exec")
        mutations.set_exposed_port(shell.node_id, pin_in.node_id, True)

        shell_edge = mutations.add_edge(
            source_node_id=source.node_id,
            source_port_key="exec_out",
            target_node_id=shell.node_id,
            target_port_key=pin_in.node_id,
        )
        inner_edge = mutations.add_edge(
            source_node_id=pin_in.node_id,
            source_port_key="pin",
            target_node_id=inner.node_id,
            target_port_key="exec_in",
        )

        self.assertIn(shell_edge.edge_id, workspace.edges)
        self.assertIn(inner_edge.edge_id, workspace.edges)

        mutations.set_node_property(pin_in.node_id, "kind", "data")

        self.assertNotIn(shell_edge.edge_id, workspace.edges)
        self.assertNotIn(inner_edge.edge_id, workspace.edges)
        self.assertEqual(workspace.nodes[pin_in.node_id].properties["kind"], "data")

    def test_workspace_mutation_service_manages_view_state_without_registry(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        service = model.mutation_service(workspace.workspace_id)

        changed = service.save_active_view_state(
            zoom=1.25,
            pan_x=125.0,
            pan_y=220.0,
        )

        self.assertTrue(changed)
        active_view = service.active_view_state()
        self.assertAlmostEqual(active_view.zoom, 1.25, places=6)
        self.assertAlmostEqual(active_view.pan_x, 125.0, places=6)
        self.assertAlmostEqual(active_view.pan_y, 220.0, places=6)

        created_view = service.create_view(
            name="Review",
            source_view_id=active_view.view_id,
        )
        self.assertEqual(workspace.active_view_id, created_view.view_id)
        self.assertEqual(created_view.name, "Review")
        self.assertAlmostEqual(created_view.zoom, 1.25, places=6)
        self.assertAlmostEqual(created_view.pan_x, 125.0, places=6)
        self.assertAlmostEqual(created_view.pan_y, 220.0, places=6)

        service.set_active_view(active_view.view_id)
        self.assertEqual(workspace.active_view_id, active_view.view_id)

def test_workspace_mutation_service_clamps_pdf_panel_page_numbers_on_property_updates(self) -> None:
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

    def test_graph_scene_payload_builder_normalization_path_is_read_only_while_payload_clamps_pdf_pages(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        spec = registry.get_spec("passive.media.pdf_panel")
        node = model.add_node(
            workspace.workspace_id,
            spec.type_id,
            spec.display_name,
            40.0,
            60.0,
            properties={
                **registry.default_properties(spec.type_id),
                "source_path": "/tmp/clamped.pdf",
                "page_number": 99,
            },
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )
        clamp_pdf_page_number = Mock(return_value=2)
        builder = GraphScenePayloadBuilder(
            boundary_adapters=build_graph_boundary_adapters(
                clamp_pdf_page_number_resolver=clamp_pdf_page_number,
            )
        )

        builder.normalize_pdf_panel_pages(
            model=model,
            registry=registry,
            workspace=workspace,
        )
        self.assertEqual(workspace.nodes[node.node_id].properties["page_number"], 99)
        nodes_payload, _minimap_payload, _edges_payload = builder.rebuild_models(
            model=model,
            registry=registry,
            workspace_id=workspace.workspace_id,
            scope_path=(),
            graph_theme_bridge=None,
        )

        payload = next(item for item in nodes_payload if item["node_id"] == node.node_id)
        self.assertEqual(workspace.nodes[node.node_id].properties["page_number"], 99)
        self.assertEqual(payload["properties"]["page_number"], 2)
        clamp_pdf_page_number.assert_called_once_with("/tmp/clamped.pdf", 99)

__all__ = ['GraphModelTrackBTests']
