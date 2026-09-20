# Purpose: Project authored node state onto ports and properties that participate in computation.
# Map: subsystems/execution.md
# Tests: tests/test_dynamic_input_execution.py
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ea_node_editor.graph.effective_ports import EffectivePort
from ea_node_editor.nodes.instance_resolution import resolve_dynamic_port_groups
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec
from ea_node_editor.runtime_contracts import DataTypeCatalog


@dataclass(frozen=True, slots=True)
class NodeComputation:
    properties: Mapping[str, object]
    ports: tuple[EffectivePort | PortSpec, ...]


def project_node_computation(
    *,
    spec: NodeTypeSpec,
    authored_properties: Mapping[str, object],
    execution_properties: Mapping[str, object],
    ports: Sequence[EffectivePort | PortSpec],
    connected_input_keys: frozenset[str],
    data_types: DataTypeCatalog,
) -> NodeComputation:
    """Keep stable connected IDs in authored order without changing runtime state.

    Connectivity must come from enabled, compiled incoming edges. The complete
    authored properties and effective ports remain authoritative for execution,
    persistence and dispatch attestation.
    """
    properties = dict(execution_properties)
    omitted_keys: set[str] = set()
    if any(group.execution_policy == "connected_inputs" for group in spec.dynamic_port_groups):
        resolved_groups = resolve_dynamic_port_groups(
            spec, authored_properties, data_types=data_types
        )
        for group, members in zip(spec.dynamic_port_groups, resolved_groups, strict=True):
            if group.execution_policy != "connected_inputs":
                continue
            properties[group.property_key] = [
                port.key for port in members if port.key in connected_input_keys
            ]
            omitted_keys.update(
                port.key for port in members if port.key not in connected_input_keys
            )
    return NodeComputation(
        properties=properties,
        ports=tuple(port for port in ports if port.key not in omitted_keys),
    )
