from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec

PluginProvenanceKind = Literal["runtime", "file", "package", "entry_point"]
PluginAvailabilityState = Literal["available", "missing_dependency"]


class NodePlugin(Protocol):
    def spec(self) -> NodeTypeSpec:
        ...

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ...


class AsyncNodePlugin(NodePlugin, Protocol):
    """Extended protocol for nodes that support non-blocking execution."""

    async def async_execute(self, ctx: ExecutionContext) -> NodeResult:
        ...


@dataclass(slots=True, frozen=True)
class PluginProvenance:
    kind: PluginProvenanceKind
    source_path: Path | None = None
    package_root: Path | None = None
    package_name: str = ""
    entry_point_name: str = ""
    distribution_name: str = ""


@dataclass(slots=True, frozen=True)
class PluginDescriptor:
    spec: NodeTypeSpec
    factory: Callable[[], NodePlugin]
    provenance: PluginProvenance | None = None


@dataclass(slots=True, frozen=True)
class PluginAvailability:
    state: PluginAvailabilityState
    summary: str = ""
    missing_dependencies: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        return self.state == "available"

    @classmethod
    def available(cls, summary: str = "") -> "PluginAvailability":
        return cls(state="available", summary=summary)

    @classmethod
    def missing_dependency(
        cls,
        *dependencies: str,
        summary: str = "",
    ) -> "PluginAvailability":
        return cls(
            state="missing_dependency",
            summary=summary,
            missing_dependencies=tuple(str(dependency) for dependency in dependencies if str(dependency).strip()),
        )


@dataclass(slots=True, frozen=True)
class PluginBackendDescriptor:
    plugin_id: str
    display_name: str
    get_availability: Callable[[], PluginAvailability]
    load_descriptors: Callable[[], tuple[PluginDescriptor, ...]]
    provenance: PluginProvenance | None = None


__all__ = [
    "PluginAvailability",
    "PluginAvailabilityState",
    "PluginBackendDescriptor",
    "AsyncNodePlugin",
    "NodePlugin",
    "PluginDescriptor",
    "PluginProvenance",
    "PluginProvenanceKind",
]
