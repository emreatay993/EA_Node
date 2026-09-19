# Purpose: Project caller-specific node port state without resolving or mutating graphs.
# Map: subsystems/graph_domain.md
# Tests: tests/test_graph_node_reconciliation.py, tests/test_graph_registry_normalization.py
from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass

from ea_node_editor.graph.effective_ports import EffectivePort
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec
from ea_node_editor.runtime_contracts import DATA_TREE_MODIFIER_ORDER


@dataclass(frozen=True, slots=True)
class NodePortState:
    exposed_ports: dict[str, bool]
    port_labels: dict[str, str]
    port_modifiers: dict[str, tuple[str, ...]]
    principal_input_port_id: str | None


def _exposed_ports(
    node: NodeInstance,
    ports: Mapping[str, EffectivePort | PortSpec],
    changed: Set[str] = frozenset(),
) -> dict[str, bool]:
    return {
        key: bool(
            port.required
            or (port.exposed if key in changed else node.exposed_ports.get(key, port.exposed))
        )
        for key, port in ports.items()
    }


def normalize_node_port_state(
    node: NodeInstance,
    spec: NodeTypeSpec,
    ports: Sequence[EffectivePort],
) -> NodePortState:
    """Canonicalize loaded state, including dynamic-label and modifier policy."""
    ports_by_key = {port.key: port for port in ports}
    non_label_directions = {
        group.direction for group in spec.dynamic_port_groups if group.rename_mode != "label"
    }
    non_label_keys = {
        port.key for port in ports[len(spec.ports) :] if port.direction in non_label_directions
    }
    labels = {
        key: str(value)
        for key, value in node.port_labels.items()
        if key in ports_by_key and key not in non_label_keys and str(value).strip()
    }
    modifiers = {}
    for key, value in node.port_modifiers.items():
        if key not in ports_by_key or str(ports_by_key[key].kind) != "data":
            continue
        requested = (
            {str(item).strip().lower() for item in value}
            if isinstance(value, (list, tuple, set, frozenset)) else set()
        )
        normalized = tuple(item for item in DATA_TREE_MODIFIER_ORDER if item in requested)
        if normalized:
            modifiers[key] = normalized
    principal = ports_by_key.get(str(node.principal_input_port_id or ""))
    principal_key = (
        node.principal_input_port_id
        if principal is not None
        and str(principal.kind) == "data"
        and str(principal.direction) == "in"
        and str(principal.data_access) != "tree"
        else None
    )
    return NodePortState(_exposed_ports(node, ports_by_key), labels, modifiers, principal_key)


def reconcile_script_port_state(
    node: NodeInstance,
    ports: Mapping[str, PortSpec],
    *,
    semantic_changed_keys: Set[str],
) -> NodePortState:
    """Preserve unchanged authored state during Apply; reset semantic changes.

    Apply already indexes candidate ports to compare their semantics. Reuse that
    mapping rather than resolving ports or allocating another index here.
    """
    labels = {
        key: str(value)
        for key, value in node.port_labels.items()
        if key in ports and key not in semantic_changed_keys and str(value).strip()
    }
    modifiers = {
        key: tuple(value)
        for key, value in node.port_modifiers.items()
        if key in ports and key not in semantic_changed_keys and ports[key].kind == "data"
    }
    principal_key = str(node.principal_input_port_id or "")
    principal = ports.get(principal_key)
    principal_key = (
        principal_key
        if principal is not None
        and principal_key not in semantic_changed_keys
        and principal.direction == "in"
        and principal.kind == "data"
        and principal.data_access != "tree"
        else None
    )
    return NodePortState(
        _exposed_ports(node, ports, semantic_changed_keys), labels, modifiers, principal_key,
    )
