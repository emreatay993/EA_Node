"""Tests for user-editable port labels feature."""

from __future__ import annotations

import pytest

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import (
    GraphModel,
    NodeInstance,
    node_instance_from_mapping,
    node_instance_to_mapping,
)
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec


def _make_spec(*, label: str = "") -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id="test.node",
        display_name="Test",
        category_path=("Test",),
        icon="bug_report",
        ports=(
            PortSpec("exec_in", "in", "exec", "exec"),
            PortSpec("data_in", "in", "data", "str", label=label),
            PortSpec("data_out", "out", "data", "str", label=label),
        ),
        properties=(),
    )


def _make_node(**overrides) -> NodeInstance:
    defaults = dict(
        node_id="n1",
        type_id="test.node",
        title="Test",
        x=0.0,
        y=0.0,
    )
    defaults.update(overrides)
    return NodeInstance(**defaults)


# -- PortSpec.label field --


class TestPortSpecLabel:
    def test_default_empty(self):
        spec = PortSpec("key", "in", "data", "str")
        assert spec.label == ""

    def test_custom_label(self):
        spec = PortSpec("key", "in", "data", "str", label="Custom")
        assert spec.label == "Custom"


# -- Serialization round-trip --


class TestPortLabelsSerialization:
    def test_round_trip(self):
        node = _make_node(port_labels={"data_in": "My Input"})
        mapping = node_instance_to_mapping(node)
        assert mapping["port_labels"] == {"data_in": "My Input"}
        restored = node_instance_from_mapping(mapping)
        assert restored is not None
        assert restored.port_labels == {"data_in": "My Input"}

    def test_current_schema_includes_empty_port_labels(self):
        mapping = node_instance_to_mapping(_make_node())
        assert mapping["port_labels"] == {}

    def test_empty_labels_stripped(self):
        mapping = {
            "node_id": "n1",
            "type_id": "test.node",
            "title": "Test",
            "x": 0.0,
            "y": 0.0,
            "port_labels": {"data_in": "", "data_out": "  "},
        }
        node = node_instance_from_mapping(mapping)
        assert node is not None
        assert node.port_labels == {}


# -- EffectivePort label resolution --


class TestEffectivePortLabelResolution:
    def test_fallback_to_key(self):
        spec = _make_spec()
        node = _make_node()
        ports = effective_ports(node=node, spec=spec, workspace_nodes={})
        data_in = next(p for p in ports if p.key == "data_in")
        assert data_in.label == "data_in"

    def test_spec_label_overrides_key(self):
        spec = _make_spec(label="Friendly Name")
        node = _make_node()
        ports = effective_ports(node=node, spec=spec, workspace_nodes={})
        data_in = next(p for p in ports if p.key == "data_in")
        assert data_in.label == "Friendly Name"

    def test_instance_override_wins(self):
        spec = _make_spec(label="Spec Label")
        node = _make_node(port_labels={"data_in": "User Label"})
        ports = effective_ports(node=node, spec=spec, workspace_nodes={})
        data_in = next(p for p in ports if p.key == "data_in")
        assert data_in.label == "User Label"

    def test_empty_instance_override_falls_through(self):
        spec = _make_spec(label="Spec Label")
        node = _make_node(port_labels={"data_in": ""})
        ports = effective_ports(node=node, spec=spec, workspace_nodes={})
        data_in = next(p for p in ports if p.key == "data_in")
        assert data_in.label == "Spec Label"

    def test_exec_port_label_still_key(self):
        spec = _make_spec()
        node = _make_node()
        ports = effective_ports(node=node, spec=spec, workspace_nodes={})
        exec_in = next(p for p in ports if p.key == "exec_in")
        assert exec_in.label == "exec_in"


# -- GraphModel.set_port_label --


class TestGraphModelSetPortLabel:
    def test_set_and_clear(self):
        model = GraphModel()
        ws = model.active_workspace
        node = _make_node()
        ws.nodes[node.node_id] = node

        model.set_port_label(ws.workspace_id, node.node_id, "data_in", "Custom")
        assert node.port_labels["data_in"] == "Custom"
        assert ws.dirty

        ws.dirty = False
        model.set_port_label(ws.workspace_id, node.node_id, "data_in", "")
        assert "data_in" not in node.port_labels
        assert ws.dirty


class TestWorkspaceMutationServiceSetPortLabel:
    def test_uses_bound_workspace_id(self):
        model = GraphModel()
        ws = model.active_workspace
        node = _make_node()
        ws.nodes[node.node_id] = node

        mutation_service = model.mutation_service(ws.workspace_id)
        mutation_service.set_port_label(node.node_id, "data_in", "Inline Rename")

        assert node.port_labels == {"data_in": "Inline Rename"}
        assert ws.dirty
