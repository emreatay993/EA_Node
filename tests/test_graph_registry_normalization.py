# Purpose: Verify load-time canonicalization and registry memo reuse.
# Map: subsystems/graph_domain.md
# Tests: this file
from __future__ import annotations

import unittest
from unittest.mock import patch

import pytest

import ea_node_editor.graph.invariant_kernel as invariant_kernel
from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.node_port_state import normalize_node_port_state
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.registry_normalization import normalize_project_for_registry
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.registry import NodeRegistry
from tests.graph_mutation_fixtures import _Plugin
from tests.graph_mutation_fixtures import dynamic_registry as _registry


def test_registry_normalization_keeps_only_permitted_dynamic_port_labels() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    dynamic = mutations.add_node(
        type_id="tests.dynamic_inputs",
        title="Dynamic",
        x=0,
        y=0,
    )
    gate = mutations.add_node(
        type_id="core.stream_gate",
        title="Gate",
        x=0,
        y=100,
    )
    no_rename = mutations.add_node(
        type_id="tests.dynamic_no_rename",
        title="No Rename",
        x=0,
        y=200,
    )
    with pytest.raises(ValueError, match="does not allow label rename"):
        mutations.set_port_label(dynamic.node_id, "alpha", "Rejected")
    with pytest.raises(ValueError, match="does not allow label rename"):
        mutations.set_port_label(no_rename.node_id, "alpha", "Rejected")
    assert dynamic.port_labels == {}
    assert no_rename.port_labels == {}
    dynamic.port_labels["alpha"] = "Not permitted"
    no_rename.port_labels["alpha"] = "Also not permitted"
    gate.port_labels["output_0"] = "Permitted"

    normalize_project_for_registry(model.project, registry)

    assert dynamic.port_labels == {}
    assert no_rename.port_labels == {}
    assert gate.port_labels == {"output_0": "Permitted"}


def test_dynamic_port_registry_normalization_resolves_defaults_before_edges() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    gate = mutations.add_node(type_id="core.stream_gate", title="Gate", x=0, y=0)
    sink = mutations.add_node(type_id="tests.sink", title="Sink", x=200, y=0)
    edge = mutations.add_edge(
        source_node_id=gate.node_id,
        source_port_key="output_0",
        target_node_id=sink.node_id,
        target_port_key="value",
    )

    gate.properties["output_port_ids"] = {"wrong": "shape"}
    normalize_project_for_registry(model.project, registry)
    assert gate.properties["output_port_ids"] == ["output_0", "output_1"]
    assert edge.edge_id in workspace.edges

    gate.properties.pop("output_port_ids")
    normalize_project_for_registry(model.project, registry)
    assert "output_port_ids" not in gate.properties
    assert edge.edge_id in workspace.edges
    assert [
        port.key
        for port in effective_ports(
            node=gate,
            spec=registry.get_spec(gate.type_id),
            workspace_nodes=workspace.nodes,
        )
        if port.direction == "out"
    ] == ["output_0", "output_1"]


def _factory(spec):
    return lambda: _Plugin(spec)


def test_loaded_port_projection_canonicalizes_sparse_state_without_mutation() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutation = model.validated_mutations(workspace.workspace_id, registry)
    node = mutation.add_node(type_id="tests.dynamic_inputs", title="Dynamic", x=0, y=0)
    node.port_labels = {"alpha": "Forbidden dynamic label", "missing": "Gone"}
    node.port_modifiers = {"alpha": (" CLEAN ", "graft", "clean", "invalid"), "beta": (), "missing": ("graft",)}
    node.principal_input_port_id = "alpha"
    node.exposed_ports = {"alpha": False, "missing": True}
    node.expanded_settings_group_ids = ("unchanged",)
    before = node.clone()
    spec = registry.resolve_spec(node.type_id, node.properties)
    ports = effective_ports(node=node, spec=spec, workspace_nodes=workspace.nodes)
    state = normalize_node_port_state(node, spec, ports)
    assert node == before
    assert state.exposed_ports == {"alpha": False, "beta": True}
    assert state.port_labels == {}
    assert state.port_modifiers == {"alpha": ("graft", "clean")}
    assert state.principal_input_port_id == "alpha"
    state.exposed_ports.clear()
    state.port_labels["alpha"] = "New"
    state.port_modifiers.clear()
    assert node == before


def test_registry_normalization_reuses_effective_ports_for_projection_and_pruning() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutation = model.validated_mutations(workspace.workspace_id, registry)
    source = mutation.add_node(type_id="tests.source", title="Source", x=0, y=0)
    target = mutation.add_node(type_id="tests.sink", title="Sink", x=200, y=0)
    edge = mutation.add_edge(source_node_id=source.node_id, source_port_key="value", target_node_id=target.node_id, target_port_key="value")
    target.exposed_ports["value"] = False
    with patch.object(invariant_kernel, "effective_ports", wraps=invariant_kernel.effective_ports) as effective_spy:
        normalize_project_for_registry(model.project, registry)
    assert effective_spy.call_count == len(workspace.nodes)
    assert target.exposed_ports["value"] is True
    assert edge.edge_id in workspace.edges


class RegistryNormalizationTests(unittest.TestCase):
    def test_normalize_project_for_registry_marks_same_count_workspace_changes(
        self,
    ) -> None:
        registry = NodeRegistry()
        spec = NodeTypeSpec(
            type_id="tests.normalize_epoch",
            display_name="Normalize Epoch",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "value", "out", "data", "COREX.DataTypes.Any"
                ),
            ),
            properties=(PropertySpec("count", "int", 7, "Count"),),
        )
        registry.register(_factory(spec))
        model = GraphModel()
        workspace = model.active_workspace
        node = NodeInstance(
            node_id="node_normalize_epoch",
            type_id="tests.normalize_epoch",
            title="Normalize Epoch",
            x=0.0,
            y=0.0,
            properties={"count": "15", "stale": "drop"},
            exposed_ports={"stale_port": True},
        )
        workspace.nodes[node.node_id] = node
        revision_before = workspace.mutation_revision
        epoch_before = model.project.document_epoch()

        normalize_project_for_registry(model.project, registry)

        self.assertEqual(node.properties, {"count": 15})
        self.assertEqual(node.exposed_ports, {"value": True})
        self.assertTrue(workspace.dirty)
        self.assertGreater(workspace.mutation_revision, revision_before)
        self.assertNotEqual(model.project.document_epoch(), epoch_before)

        revision_after = workspace.mutation_revision
        epoch_after = model.project.document_epoch()
        normalize_project_for_registry(model.project, registry)

        self.assertEqual(workspace.mutation_revision, revision_after)
        self.assertEqual(model.project.document_epoch(), epoch_after)


    def test_normalize_project_for_registry_prunes_unknown_nodes_without_sidecars(
        self,
    ) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace

        known_source = model.add_node(
            workspace.workspace_id, "core.constant", "Source", 0.0, 0.0
        )
        known_target = model.add_node(
            workspace.workspace_id, "core.logger", "Target", 320.0, 0.0
        )
        unknown_node = NodeInstance(
            node_id="node_unknown",
            type_id="plugin.missing_step",
            title="Missing Step",
            x=160.0,
            y=0.0,
            collapsed=True,
            properties={"threshold": 0.5},
            exposed_ports={"plugin_in": True},
            visual_style={"fill": "#556677"},
        )
        workspace.nodes[unknown_node.node_id] = unknown_node
        child_node = model.add_node(
            workspace.workspace_id, "core.logger", "Child", 200.0, 80.0
        )
        child_node.parent_node_id = unknown_node.node_id

        valid_edge = model.add_edge(
            workspace.workspace_id,
            known_source.node_id,
            "as_text",
            known_target.node_id,
            "message",
        )
        mixed_edge = model.add_edge(
            workspace.workspace_id,
            unknown_node.node_id,
            "plugin_out",
            known_target.node_id,
            "message",
        )

        normalize_project_for_registry(model.project, registry)

        self.assertNotIn(unknown_node.node_id, workspace.nodes)
        self.assertIsNone(workspace.nodes[child_node.node_id].parent_node_id)
        self.assertEqual(set(workspace.edges), {valid_edge.edge_id})
        self.assertNotIn(mixed_edge.edge_id, workspace.edges)


    def test_normalize_project_for_registry_prunes_missing_addon(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        addon_node = NodeInstance(
            node_id="node_signal_transform",
            type_id="addons.signal.transform",
            title="Signal Transform",
            x=120.0,
            y=40.0,
            collapsed=True,
            properties={"gain": 2.0},
            exposed_ports={"signal_in": True, "signal_out": True},
            visual_style={"fill": "#225588"},
        )
        workspace.nodes[addon_node.node_id] = addon_node

        normalize_project_for_registry(model.project, registry)

        self.assertNotIn(addon_node.node_id, workspace.nodes)


    def test_normalize_project_for_registry_keeps_directed_neutral_flowchart_edges(
        self,
    ) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        source = model.add_node(
            workspace.workspace_id, "passive.flowchart.process", "Process", 20.0, 30.0
        )
        target = model.add_node(
            workspace.workspace_id, "passive.flowchart.process", "Process", 320.0, 30.0
        )
        edge = model.add_edge(
            workspace.workspace_id,
            source.node_id,
            "right",
            target.node_id,
            "left",
        )

        normalize_project_for_registry(model.project, registry)

        self.assertIn(edge.edge_id, workspace.edges)
        kept_edge = workspace.edges[edge.edge_id]
        self.assertEqual(kept_edge.source_port_key, "right")
        self.assertEqual(kept_edge.target_port_key, "left")
