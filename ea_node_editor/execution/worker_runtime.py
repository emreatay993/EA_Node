from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.execution.compiler import compile_runtime_snapshot
from ea_node_editor.execution.protocol import StartRunCommand
from ea_node_editor.execution.runtime_dto import RuntimeEdge, RuntimeWorkspace
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore

_CONTROL_PORT_KINDS = frozenset({"exec", "completed", "failed"})


def load_runtime_snapshot(
    command: StartRunCommand,
) -> RuntimeSnapshot:
    if command.runtime_snapshot is None:
        raise ValueError("start_run requires runtime_snapshot.")
    return command.runtime_snapshot


def _is_dependency_spec(spec: Any) -> bool:
    return all(getattr(port, "kind", "") == "data" for port in getattr(spec, "ports", ()))


def _is_exec_entry_spec(spec: Any) -> bool:
    has_control_output = any(
        getattr(port, "direction", "") == "out" and getattr(port, "kind", "") in _CONTROL_PORT_KINDS
        for port in getattr(spec, "ports", ())
    )
    has_control_input = any(
        getattr(port, "direction", "") == "in" and getattr(port, "kind", "") in _CONTROL_PORT_KINDS
        for port in getattr(spec, "ports", ())
    )
    return has_control_output and not has_control_input


class ExecutionPlan:
    def __init__(self, workspace: RuntimeWorkspace, registry: Any) -> None:
        self.workspace = workspace
        self.nodes = workspace.nodes_by_id
        self.node_specs = {
            node_id: registry.get_spec(node.type_id)
            for node_id, node in self.nodes.items()
        }
        self._port_kinds = {
            node_id: {port.key: port.kind for port in spec.ports}
            for node_id, spec in self.node_specs.items()
        }
        self.exec_outgoing: dict[str, list[str]] = defaultdict(list)
        self.failed_outgoing: dict[str, list[str]] = defaultdict(list)
        self.data_incoming: dict[str, list[RuntimeEdge]] = defaultdict(list)
        self._dependency_outgoing: dict[str, set[str]] = defaultdict(set)
        self.exec_incoming_remaining: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        self.dependency_nodes: set[str] = {
            node_id for node_id, spec in self.node_specs.items() if _is_dependency_spec(spec)
        }
        self.start_nodes = [
            node_id for node_id, node in self.nodes.items() if node.type_id == "core.start"
        ]

        for edge in workspace.edges:
            source_node_id = edge.source_node_id
            target_node_id = edge.target_node_id
            source_kind = self._port_kinds.get(source_node_id, {}).get(edge.source_port_key, "data")
            if source_kind == "failed":
                self.failed_outgoing[source_node_id].append(target_node_id)
                self.exec_incoming_remaining[target_node_id] += 1
            elif source_kind in {"exec", "completed"}:
                self.exec_outgoing[source_node_id].append(target_node_id)
                self.exec_incoming_remaining[target_node_id] += 1
            elif source_kind == "flow":
                continue
            else:
                self.data_incoming[target_node_id].append(edge)
                if source_node_id in self.dependency_nodes and target_node_id in self.dependency_nodes:
                    self._dependency_outgoing[source_node_id].add(target_node_id)

    def initial_ready(self) -> deque[str]:
        if self.start_nodes:
            return deque(self.start_nodes)
        return deque(
            sorted(
                node_id
                for node_id, spec in self.node_specs.items()
                if self.exec_incoming_remaining.get(node_id, 0) == 0 and _is_exec_entry_spec(spec)
            )
        )

    def dependency_sources_for(self, node_id: str) -> list[str]:
        sources: list[str] = []
        seen: set[str] = set()
        for edge in self.data_incoming.get(node_id, []):
            source_node_id = edge.source_node_id
            if source_node_id not in self.dependency_nodes or source_node_id in seen:
                continue
            seen.add(source_node_id)
            sources.append(source_node_id)
        return sources

    def input_values_for(self, node_id: str, node_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for edge in self.data_incoming.get(node_id, []):
            source_outputs = node_outputs.get(edge.source_node_id, {})
            source_port_key = edge.source_port_key
            if source_port_key in source_outputs:
                inputs[edge.target_port_key] = source_outputs[source_port_key]
        return inputs

    def has_failure_downstream(self, node_id: str) -> bool:
        return bool(self.failed_outgoing.get(node_id))

    def release_downstream(self, node_id: str, status: str) -> list[str]:
        downstream_nodes = (
            self.failed_outgoing.get(node_id, [])
            if status == "failed_handled"
            else self.exec_outgoing.get(node_id, [])
        )
        ready_nodes: list[str] = []
        for downstream in downstream_nodes:
            self.exec_incoming_remaining[downstream] -= 1
            if self.exec_incoming_remaining[downstream] <= 0:
                ready_nodes.append(downstream)
        return ready_nodes

    def has_only_dependency_nodes(self) -> bool:
        return all(node_id in self.dependency_nodes for node_id in self.nodes)

    def dependency_sinks(self) -> list[str]:
        sinks = sorted(
            node_id for node_id in self.dependency_nodes if not self._dependency_outgoing.get(node_id)
        )
        if sinks:
            return sinks
        return sorted(self.dependency_nodes)


@dataclass(slots=True)
class PreparedRuntime:
    registry: Any
    runtime_snapshot: RuntimeSnapshot
    runtime_context: RuntimeSnapshotContext
    workspace: RuntimeWorkspace
    plan: ExecutionPlan


class RuntimeArtifactService:
    def __init__(
        self,
        *,
        runtime_context: RuntimeSnapshotContext,
    ) -> None:
        self._runtime_context = runtime_context
        self._project_path = str(runtime_context.project_path).strip()
        self._resolver = ProjectArtifactResolver(
            project_path=self._project_path or None,
            artifact_store=runtime_context.artifact_store,
        )

    @property
    def project_path(self) -> str:
        return self._project_path

    @property
    def runtime_context(self) -> RuntimeSnapshotContext:
        return self._runtime_context

    @property
    def store(self):
        return self._resolver.store

    def normalize_outputs(self, payload: dict[str, Any]) -> dict[str, Any]:
        from ea_node_editor.nodes.types import deserialize_runtime_value

        normalized = deserialize_runtime_value(payload)
        return dict(normalized) if isinstance(normalized, dict) else {}

    def resolve_path(self, value: Any) -> Any:
        return self._resolver.resolve_to_path(value)


def resolve_runtime_artifact_store(
    *,
    project_path: str = "",
    runtime_snapshot: RuntimeSnapshot | None = None,
    runtime_context: RuntimeSnapshotContext | None = None,
) -> ProjectArtifactStore:
    if runtime_context is not None:
        return runtime_context.artifact_store
    project_metadata = runtime_snapshot.metadata if runtime_snapshot is not None else None
    return ProjectArtifactStore.from_project_metadata(
        project_path=str(project_path).strip() or None,
        project_metadata=project_metadata if isinstance(project_metadata, Mapping) else None,
    )


def prepare_runtime(command: StartRunCommand) -> PreparedRuntime:
    from ea_node_editor.nodes.bootstrap import build_default_registry

    registry = build_default_registry()
    runtime_snapshot = load_runtime_snapshot(command)
    artifact_context_project_path = command.project_path
    runtime_context = RuntimeSnapshotContext.from_snapshot(
        runtime_snapshot,
        project_path=artifact_context_project_path,
    )
    workspace = compile_runtime_snapshot(
        runtime_snapshot,
        workspace_id=command.workspace_id,
        registry=registry,
    )
    return PreparedRuntime(
        registry=registry,
        runtime_snapshot=runtime_snapshot,
        runtime_context=runtime_context,
        workspace=workspace,
        plan=ExecutionPlan(workspace, registry),
    )


__all__ = [
    "ExecutionPlan",
    "PreparedRuntime",
    "RuntimeArtifactService",
    "load_runtime_snapshot",
    "prepare_runtime",
    "resolve_runtime_artifact_store",
]
