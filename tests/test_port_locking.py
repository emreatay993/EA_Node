from __future__ import annotations

import pytest

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel, NodeInstance, node_instance_from_mapping, node_instance_to_mapping
from ea_node_editor.graph.normalization import (
    LOCKED_TARGET_PORT_MESSAGE,
    build_graph_fragment_payload,
    normalize_graph_fragment_payload,
)
from ea_node_editor.graph.port_locking import (
    compute_initial_locked_ports,
    is_lockable_data_type,
    is_port_lockable,
    lockable_port_keys,
    property_value_triggers_lock,
)
from ea_node_editor.graph.transform_fragment_ops import build_subtree_fragment_payload_data
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec, PropertySpec


def _make_spec() -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id="tests.lockable",
        display_name="Lockable",
        category_path=("Tests",),
        icon="",
        ports=(
            PortSpec("count", "in", "data", "int"),
            PortSpec("ratio", "in", "data", "float"),
            PortSpec("enabled", "in", "data", "bool"),
            PortSpec("message", "in", "data", "str"),
            PortSpec("missing_prop", "in", "data", "str"),
            PortSpec("payload", "in", "data", "any"),
            PortSpec("result", "out", "data", "str"),
            PortSpec("exec_in", "in", "exec", "exec"),
        ),
        properties=(
            PropertySpec("count", "int", 0, "Count"),
            PropertySpec("ratio", "float", 0.5, "Ratio"),
            PropertySpec("enabled", "bool", False, "Enabled"),
            PropertySpec("message", "str", "", "Message"),
            PropertySpec("result", "str", "", "Result"),
        ),
    )


def _make_node(**overrides) -> NodeInstance:
    defaults = dict(
        node_id="node_locking",
        type_id="tests.lockable",
        title="Lockable",
        x=0.0,
        y=0.0,
    )
    defaults.update(overrides)
    return NodeInstance(**defaults)


def _build_registry():
    registry = build_default_registry()
    registry.register_descriptor(_make_spec(), factory=lambda: object())
    return registry


def test_node_instance_locked_ports_round_trip_preserves_authored_keys() -> None:
    node = _make_node(locked_ports={"message": True, "shadow": False})

    mapping = node_instance_to_mapping(node)
    restored = node_instance_from_mapping(mapping)

    assert mapping["locked_ports"] == {"message": True, "shadow": False}
    assert restored is not None
    assert restored.locked_ports == {"message": True, "shadow": False}


def test_effective_ports_exposes_locked_state_on_resolved_ports() -> None:
    ports = effective_ports(
        node=_make_node(locked_ports={"message": True}),
        spec=_make_spec(),
        workspace_nodes={},
    )
    by_key = {port.key: port for port in ports}

    assert by_key["message"].locked is True
    assert by_key["count"].locked is False


def test_lockable_port_helpers_match_packet_state_contract() -> None:
    spec = _make_spec()

    assert is_lockable_data_type("int") is True
    assert is_lockable_data_type("float") is True
    assert is_lockable_data_type("bool") is True
    assert is_lockable_data_type("str") is True
    assert is_lockable_data_type("any") is False

    assert lockable_port_keys(spec) == ("count", "ratio", "enabled", "message")
    assert is_port_lockable(spec, "count") is True
    assert is_port_lockable(spec, "missing_prop") is False
    assert is_port_lockable(spec, "payload") is False
    assert is_port_lockable(spec, "result") is False
    assert is_port_lockable(spec, "exec_in") is False


def test_property_value_triggers_lock_uses_primitive_rules() -> None:
    assert property_value_triggers_lock("int", 2) is True
    assert property_value_triggers_lock("int", 0) is False
    assert property_value_triggers_lock("float", 0.25) is True
    assert property_value_triggers_lock("float", 0.0) is False
    assert property_value_triggers_lock("bool", True) is True
    assert property_value_triggers_lock("bool", False) is False
    assert property_value_triggers_lock("str", "  hello  ") is True
    assert property_value_triggers_lock("str", "   ") is False


def test_compute_initial_locked_ports_preserves_authored_keys_and_default_triggers() -> None:
    lock_map = compute_initial_locked_ports(
        _make_spec(),
        properties={"count": 2, "message": "   "},
        authored_locked_ports={"enabled": True, "shadow": False},
    )

    assert lock_map == {
        "count": True,
        "ratio": True,
        "enabled": True,
        "shadow": False,
    }


def test_workspace_snapshot_restore_preserves_locked_ports_and_view_filters() -> None:
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(
        workspace.workspace_id,
        "core.logger",
        "Logger",
        40.0,
        80.0,
        properties={"message": "locked"},
    )
    node.locked_ports = {"message": True, "shadow": False}
    view = workspace.views[workspace.active_view_id]
    view.hide_locked_ports = True
    view.hide_optional_ports = True

    snapshot = workspace.capture_snapshot()

    node.locked_ports = {}
    view.hide_locked_ports = False
    view.hide_optional_ports = False

    workspace.restore_snapshot(snapshot)

    restored_node = workspace.nodes[node.node_id]
    restored_view = workspace.views[view.view_id]
    assert restored_node.locked_ports == {"message": True, "shadow": False}
    assert restored_view.hide_locked_ports is True
    assert restored_view.hide_optional_ports is True


def test_duplicate_workspace_preserves_locked_ports_and_view_filters() -> None:
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(workspace.workspace_id, "core.logger", "Logger", 10.0, 20.0)
    node.locked_ports = {"message": True}
    source_view = workspace.views[workspace.active_view_id]
    source_view.hide_locked_ports = True
    source_view.hide_optional_ports = True

    duplicate = model.duplicate_workspace(workspace.workspace_id)
    duplicate_view = duplicate.views[duplicate.active_view_id]

    assert duplicate.workspace_id != workspace.workspace_id
    assert duplicate.nodes[node.node_id].locked_ports == {"message": True}
    assert duplicate_view.hide_locked_ports is True
    assert duplicate_view.hide_optional_ports is True


def test_validated_add_node_seeds_locked_ports_from_meaningful_default_properties() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    node = mutations.add_node(type_id="core.logger", title="Logger", x=10.0, y=20.0)

    assert node.locked_ports == {"message": True}


def test_set_node_property_auto_locks_and_prunes_incoming_edges_without_auto_unlock() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    source = mutations.add_node(type_id="core.constant", title="Constant", x=0.0, y=0.0)
    target = mutations.add_node(
        type_id="core.logger",
        title="Logger",
        x=240.0,
        y=20.0,
        properties={"message": ""},
    )
    edge = mutations.add_edge(
        source_node_id=source.node_id,
        source_port_key="as_text",
        target_node_id=target.node_id,
        target_port_key="message",
    )

    assert edge.edge_id in workspace.edges
    assert target.locked_ports == {}

    mutations.set_node_property(target.node_id, "message", "  hello  ")

    assert target.locked_ports == {"message": True}
    assert workspace.edges == {}

    mutations.set_node_property(target.node_id, "message", "")

    assert target.locked_ports == {"message": True}
    assert workspace.edges == {}


def test_set_node_properties_auto_lock_is_one_way_for_triggering_ports() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    node = mutations.add_node(
        type_id="tests.lockable",
        title="Lockable",
        x=20.0,
        y=40.0,
        properties={"count": 0, "ratio": 0.0, "enabled": False, "message": ""},
    )

    assert node.locked_ports == {}

    normalized_updates = mutations.set_node_properties(
        node.node_id,
        {"count": 3, "message": "hi", "enabled": False},
    )

    assert normalized_updates == {"count": 3, "message": "hi"}
    assert node.locked_ports == {"count": True, "message": True}

    cleared_updates = mutations.set_node_properties(node.node_id, {"count": 0, "message": ""})

    assert cleared_updates == {"count": 0, "message": ""}
    assert node.locked_ports == {"count": True, "message": True}


def test_manual_unlock_does_not_rewrite_property_value_and_allows_reconnect() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    source = mutations.add_node(type_id="core.constant", title="Constant", x=0.0, y=0.0)
    target = mutations.add_node(
        type_id="tests.lockable",
        title="Lockable",
        x=260.0,
        y=20.0,
        properties={"count": 1, "ratio": 0.0, "enabled": False, "message": ""},
    )

    assert target.locked_ports == {"count": True}
    assert mutations.set_locked_port(target.node_id, "count", False) is True
    assert target.properties["count"] == 1
    assert target.locked_ports == {"count": False}

    edge = mutations.add_edge(
        source_node_id=source.node_id,
        source_port_key="value",
        target_node_id=target.node_id,
        target_port_key="count",
    )

    assert edge.edge_id in workspace.edges


def test_set_locked_port_rejects_non_lockable_ports_and_prunes_existing_incoming_edges() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    source = mutations.add_node(type_id="core.constant", title="Constant", x=0.0, y=0.0)
    target = mutations.add_node(
        type_id="tests.lockable",
        title="Lockable",
        x=260.0,
        y=20.0,
        properties={"count": 0, "ratio": 0.0, "enabled": False, "message": ""},
    )
    edge = mutations.add_edge(
        source_node_id=source.node_id,
        source_port_key="value",
        target_node_id=target.node_id,
        target_port_key="count",
    )

    assert edge.edge_id in workspace.edges
    assert mutations.set_locked_port(target.node_id, "count", True) is True
    assert target.locked_ports == {"count": True}
    assert workspace.edges == {}

    with pytest.raises(ValueError, match="Port is not lockable"):
        mutations.set_locked_port(target.node_id, "payload", True)


def test_add_edge_rejects_locked_target_ports() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    source = mutations.add_node(type_id="core.constant", title="Constant", x=0.0, y=0.0)
    target = mutations.add_node(type_id="core.logger", title="Logger", x=260.0, y=20.0)

    with pytest.raises(ValueError) as excinfo:
        mutations.add_edge(
            source_node_id=source.node_id,
            source_port_key="as_text",
            target_node_id=target.node_id,
            target_port_key="message",
        )

    assert str(excinfo.value) == LOCKED_TARGET_PORT_MESSAGE


def test_graph_fragment_serialization_and_insert_preserve_locked_ports() -> None:
    registry = _build_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)

    node = mutations.add_node(
        type_id="tests.lockable",
        title="Lockable",
        x=20.0,
        y=30.0,
        properties={"count": 1, "ratio": 0.0, "enabled": False, "message": "hello"},
    )

    assert node.locked_ports == {"count": True, "message": True}
    assert mutations.set_locked_port(node.node_id, "message", False) is True
    assert node.properties["message"] == "hello"

    fragment_data = build_subtree_fragment_payload_data(workspace=workspace, selected_node_ids=[node.node_id])

    assert fragment_data is not None
    fragment_payload = build_graph_fragment_payload(
        nodes=fragment_data["nodes"],
        edges=fragment_data["edges"],
    )
    normalized_fragment = normalize_graph_fragment_payload(fragment_payload)

    assert normalized_fragment is not None
    assert normalized_fragment["nodes"][0]["locked_ports"] == {"count": True, "message": False}

    inserted_node_ids = mutations.insert_graph_fragment(
        fragment_payload=normalized_fragment,
        delta_x=40.0,
        delta_y=60.0,
    )

    assert len(inserted_node_ids) == 1
    inserted = workspace.nodes[inserted_node_ids[0]]
    assert inserted.node_id != node.node_id
    assert inserted.properties == node.properties
    assert inserted.locked_ports == node.locked_ports
