from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec

PluginProvenanceKind = Literal["runtime", "file", "package", "entry_point"]


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


__all__ = [
    "AsyncNodePlugin",
    "NodePlugin",
    "PluginDescriptor",
    "PluginProvenance",
    "PluginProvenanceKind",
]
