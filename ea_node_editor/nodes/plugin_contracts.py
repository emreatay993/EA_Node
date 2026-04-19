from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Protocol

from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec

PluginProvenanceKind = Literal["runtime", "file", "package", "entry_point"]
PluginAvailabilityState = Literal["available", "missing_dependency"]
AddOnApplyPolicy = Literal["hot_apply", "restart_required"]
AddOnRecordState = Literal["installed", "disabled", "unavailable", "pending_restart"]


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
class AddOnManifest:
    addon_id: str
    display_name: str
    apply_policy: AddOnApplyPolicy
    vendor: str = ""
    version: str = ""
    summary: str = ""
    details: str = ""
    dependencies: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class AddOnState:
    enabled: bool = True
    pending_restart: bool = False


@dataclass(slots=True, frozen=True)
class AddOnRecord:
    manifest: AddOnManifest
    state: AddOnState = field(default_factory=AddOnState)
    availability: "PluginAvailability" = field(default_factory=lambda: PluginAvailability.available())
    provided_node_type_ids: tuple[str, ...] = ()

    @property
    def addon_id(self) -> str:
        return self.manifest.addon_id

    @property
    def display_name(self) -> str:
        return self.manifest.display_name

    @property
    def apply_policy(self) -> AddOnApplyPolicy:
        return self.manifest.apply_policy

    @property
    def vendor(self) -> str:
        return self.manifest.vendor

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def summary(self) -> str:
        return self.manifest.summary

    @property
    def details(self) -> str:
        return self.manifest.details

    @property
    def status(self) -> AddOnRecordState:
        if not self.availability.is_available:
            return "unavailable"
        if self.state.pending_restart:
            return "pending_restart"
        if not self.state.enabled:
            return "disabled"
        return "installed"


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
    addon_manifest: AddOnManifest | None = None


__all__ = [
    "AddOnApplyPolicy",
    "AddOnManifest",
    "AddOnRecord",
    "AddOnRecordState",
    "AddOnState",
    "PluginAvailability",
    "PluginAvailabilityState",
    "PluginBackendDescriptor",
    "AsyncNodePlugin",
    "NodePlugin",
    "PluginDescriptor",
    "PluginProvenance",
    "PluginProvenanceKind",
]
