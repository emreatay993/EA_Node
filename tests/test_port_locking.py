from __future__ import annotations

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel, NodeInstance, node_instance_from_mapping, node_instance_to_mapping
from ea_node_editor.graph.port_locking import (
    compute_initial_locked_ports,
    is_lockable_data_type,
    is_port_lockable,
    lockable_port_keys,
    property_value_triggers_lock,
)
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
