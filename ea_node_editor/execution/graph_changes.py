# Purpose: Compare authored snapshots by their computational meaning, independently of UI actions.
# Map: subsystems/execution.md
# Tests: tests/test_execution_graph_changes.py, tests/test_run_controller_unit.py
from __future__ import annotations

from dataclasses import dataclass

from ea_node_editor.execution.compiler import compile_runtime_workspace_snapshot
from ea_node_editor.execution.execution_plan import ExecutionPlan
from ea_node_editor.execution.runtime_dto import (
    RuntimeEdge,
    RuntimeNode,
    RuntimeWorkspace,
)
from ea_node_editor.execution.solution_identity import (
    canonical_digest,
    node_contract_digest,
)
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.workspace_state import WorkspaceSnapshot
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.instance_resolution import resolve_instance_ports


@dataclass(frozen=True, slots=True)
class ExecutionGraphChange:
    affects_execution: bool
    changed_root_node_ids: tuple[str, ...] = ()
    removed_node_ids: tuple[str, ...] = ()


def _passive(node: NodeInstance, registry: NodeRegistry) -> bool:
    spec = registry.spec_or_none(node.type_id)
    return spec is not None and spec.runtime_behavior == "passive"


def _authored_node_structure(node: NodeInstance) -> tuple:
    return (
        node.type_id,
        node.parent_node_id,
        node.exposed_ports,
        node.port_modifiers,
        node.principal_input_port_id,
        node.links,
    )


def _authored_edges(snapshot: WorkspaceSnapshot) -> tuple:
    return tuple(
        sorted(
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
                edge.enabled,
                edge.input_order,
            )
            for edge in snapshot.edges.values()
        )
    )


def _authored_property_change(
    before: WorkspaceSnapshot,
    after: WorkspaceSnapshot,
    registry: NodeRegistry,
) -> ExecutionGraphChange | None:
    """Resolve property-only edits without rebuilding unchanged graph structure.

    This also permits moving/formatting an invalid or incomplete node. Raw links
    and hierarchy stay conservative here; compilation resolves their meaning.
    """
    before_nodes = {
        key: node for key, node in before.nodes.items() if not _passive(node, registry)
    }
    after_nodes = {
        key: node for key, node in after.nodes.items() if not _passive(node, registry)
    }
    if before_nodes.keys() != after_nodes.keys() or _authored_edges(
        before
    ) != _authored_edges(after):
        return None
    changed = []
    for node_id, new in after_nodes.items():
        old = before_nodes[node_id]
        if _authored_node_structure(old) != _authored_node_structure(new):
            return None
        if old.properties == new.properties:
            continue
        try:
            old_properties = registry.execution_properties(old.type_id, old.properties)
            new_properties = registry.execution_properties(new.type_id, new.properties)
            properties_changed = canonical_digest(old_properties) != canonical_digest(
                new_properties
            )
            declared = registry.get_spec(old.type_id)
            if (
                declared.runtime_behavior == "active"
                and declared.instance_spec_resolver is None
            ):
                if resolve_instance_ports(
                    declared, old.properties
                ) != resolve_instance_ports(declared, new.properties):
                    return None
                if properties_changed:
                    changed.append(node_id)
                continue
            if properties_changed:
                return None
            # Resolvers are callable declarations: a misclassified property must
            # never hide an actual interface/readiness change behind this shortcut.
            old_spec = registry.resolve_spec(old.type_id, old.properties)
            new_spec = registry.resolve_spec(new.type_id, new.properties)
            if node_contract_digest(
                old_spec, resolve_instance_ports(old_spec, old.properties)
            ) != node_contract_digest(
                new_spec, resolve_instance_ports(new_spec, new.properties)
            ):
                return None
        except (KeyError, TypeError, ValueError):
            return None
    return ExecutionGraphChange(bool(changed), tuple(changed))


def _project_computation(
    workspace_id: str,
    snapshot: WorkspaceSnapshot,
    registry: NodeRegistry,
) -> dict[str, str]:
    # No project conversion or artifact/provenance preparation is needed here.
    workspace = RuntimeWorkspace(
        document_fields={"workspace_id": workspace_id, "name": snapshot.name},
        nodes=tuple(
            RuntimeNode.from_node_instance(node) for node in snapshot.nodes.values()
        ),
        edges=tuple(
            RuntimeEdge.from_edge_instance(edge) for edge in snapshot.edges.values()
        ),
    )
    compiled = compile_runtime_workspace_snapshot(workspace, registry)
    plan = ExecutionPlan.for_invalidation(compiled, registry)
    result = {}
    for node_id in plan.execution_order:
        node = plan.nodes[node_id]
        properties = (
            node.properties
            if node_id in plan.node_preflight_errors
            else registry.execution_properties(node.type_id, node.properties)
        )
        result[node_id] = canonical_digest(
            {
                "type_id": node.type_id,
                "properties": properties,
                "interface": plan.node_solution_interface_digest(node_id),
                "incoming": tuple(
                    (
                        edge.source_node_id,
                        edge.source_port_key,
                        edge.target_port_key,
                        edge.input_order,
                    )
                    for edge in plan.incoming_edges_for(node_id)
                ),
                "hidden_incoming": tuple(
                    sorted(
                        source
                        for source, target in plan.hidden_ordering_pairs
                        if target == node_id
                    )
                ),
            }
        )
    return result


def compare_execution_graphs(
    workspace_id: str,
    *,
    before_snapshot: WorkspaceSnapshot,
    after_snapshot: WorkspaceSnapshot,
    registry: NodeRegistry,
) -> ExecutionGraphChange:
    """Return surviving changed roots and removals, without a second closure policy."""
    if (
        not workspace_id
        or not isinstance(before_snapshot, WorkspaceSnapshot)
        or not isinstance(after_snapshot, WorkspaceSnapshot)
    ):
        raise ValueError(
            "Execution comparison requires a workspace ID and complete snapshots"
        )
    property_change = _authored_property_change(
        before_snapshot, after_snapshot, registry
    )
    if property_change is not None:
        return property_change
    try:
        before = _project_computation(workspace_id, before_snapshot, registry)
    except (KeyError, TypeError, ValueError):
        before = None
    try:
        after = _project_computation(workspace_id, after_snapshot, registry)
    except (KeyError, TypeError, ValueError):
        after = None
    if before is None or after is None:
        # A real authored computational change that cannot be projected must not
        # silently retain current results. Normal runtime admission reports errors.
        def active_ids(snapshot):
            return {
                key
                for key, node in snapshot.nodes.items()
                if (spec := registry.spec_or_none(node.type_id)) is not None
                and spec.runtime_behavior == "active"
            }

        before_ids = set(before) if before is not None else active_ids(before_snapshot)
        after_ids = set(after) if after is not None else active_ids(after_snapshot)
        return ExecutionGraphChange(
            True,
            tuple(key for key in after_snapshot.nodes if key in after_ids),
            tuple(
                key for key in before_snapshot.nodes if key in before_ids - after_ids
            ),
        )
    return ExecutionGraphChange(
        before != after,
        tuple(
            key
            for key in after_snapshot.nodes
            if key in after and before.get(key) != after[key]
        ),
        tuple(
            key for key in before_snapshot.nodes if key in before and key not in after
        ),
    )
