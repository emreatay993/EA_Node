from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol

PortDirection = Literal["in", "out", "neutral"]
PortSide = Literal["", "top", "right", "bottom", "left"]
PortKind = Literal["exec", "completed", "failed", "data", "flow"]
PropertyType = Literal["str", "int", "float", "bool", "path", "enum", "json"]
InlineEditorType = Literal["", "text", "number", "toggle", "enum", "path", "textarea"]
InspectorEditorType = Literal["", "text", "textarea", "path", "toggle", "enum"]
RuntimeBehavior = Literal["active", "passive", "compile_only"]
SurfaceFamily = Literal["standard", "flowchart", "planning", "annotation", "media"]
PluginProvenanceKind = Literal["runtime", "file", "package", "entry_point"]
RenderWeightClass = Literal["standard", "heavy"]
MaxPerformanceStrategy = Literal["generic_fallback", "proxy_surface"]
RenderQualityTier = Literal["full", "reduced", "proxy"]

_SUPPORTED_RENDER_WEIGHT_CLASSES = {"standard", "heavy"}
_SUPPORTED_MAX_PERFORMANCE_STRATEGIES = {"generic_fallback", "proxy_surface"}
_SUPPORTED_RENDER_QUALITY_TIERS = {"full", "reduced", "proxy"}


def _normalize_render_quality_token(
    field_name: str,
    value: object,
    *,
    allowed: set[str],
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty trimmed string")
    if normalized not in allowed:
        raise ValueError(f"{field_name} has invalid value: {normalized}")
    return normalized


def _normalize_render_quality_tiers(value: object) -> tuple[RenderQualityTier, ...]:
    if isinstance(value, str):
        raw_tiers: Sequence[object] = (value,)
    elif isinstance(value, Sequence):
        raw_tiers = value
    else:
        raise TypeError("render_quality.supported_quality_tiers must be a sequence of strings")

    normalized: list[RenderQualityTier] = []
    seen: set[str] = set()
    for raw_tier in raw_tiers:
        tier = _normalize_render_quality_token(
            "render_quality.supported_quality_tiers",
            raw_tier,
            allowed=_SUPPORTED_RENDER_QUALITY_TIERS,
        )
        if tier in seen:
            continue
        normalized.append(tier)  # type: ignore[arg-type]
        seen.add(tier)

    if not normalized:
        raise ValueError("render_quality.supported_quality_tiers must contain at least one tier")
    return tuple(normalized)


@dataclass(slots=True, frozen=True)
class PortSpec:
    key: str
    direction: PortDirection
    kind: PortKind
    data_type: str
    label: str = ""
    required: bool = False
    exposed: bool = True
    allow_multiple_connections: bool = False
    side: PortSide = ""


@dataclass(slots=True, frozen=True)
class PropertySpec:
    key: str
    type: PropertyType
    default: Any
    label: str
    expose_port_toggle: bool = False
    enum_values: tuple[str, ...] = ()
    inline_editor: InlineEditorType = ""
    inspector_editor: InspectorEditorType = ""
    inspector_visible: bool = True


@dataclass(slots=True, frozen=True)
class NodeRenderQualitySpec:
    weight_class: RenderWeightClass = "standard"
    max_performance_strategy: MaxPerformanceStrategy = "generic_fallback"
    supported_quality_tiers: tuple[RenderQualityTier, ...] = ("full",)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "weight_class",
            _normalize_render_quality_token(
                "render_quality.weight_class",
                self.weight_class,
                allowed=_SUPPORTED_RENDER_WEIGHT_CLASSES,
            ),
        )
        object.__setattr__(
            self,
            "max_performance_strategy",
            _normalize_render_quality_token(
                "render_quality.max_performance_strategy",
                self.max_performance_strategy,
                allowed=_SUPPORTED_MAX_PERFORMANCE_STRATEGIES,
            ),
        )
        object.__setattr__(
            self,
            "supported_quality_tiers",
            _normalize_render_quality_tiers(self.supported_quality_tiers),
        )

    @classmethod
    def from_value(cls, value: object) -> NodeRenderQualitySpec:
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("render_quality must be a NodeRenderQualitySpec, mapping, or None")
        raw_tiers = value.get("supported_quality_tiers", ("full",))
        return cls(
            weight_class=value.get("weight_class", "standard"),  # type: ignore[arg-type]
            max_performance_strategy=value.get("max_performance_strategy", "generic_fallback"),  # type: ignore[arg-type]
            supported_quality_tiers=raw_tiers,  # type: ignore[arg-type]
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "weight_class": self.weight_class,
            "max_performance_strategy": self.max_performance_strategy,
            "supported_quality_tiers": list(self.supported_quality_tiers),
        }


@dataclass(slots=True, frozen=True)
class NodeTypeSpec:
    type_id: str
    display_name: str
    category: str
    icon: str
    ports: tuple[PortSpec, ...]
    properties: tuple[PropertySpec, ...]
    collapsible: bool = True
    description: str = ""
    is_async: bool = False
    runtime_behavior: RuntimeBehavior = "active"
    surface_family: SurfaceFamily = "standard"
    surface_variant: str = ""
    render_quality: NodeRenderQualitySpec = field(default_factory=NodeRenderQualitySpec)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "render_quality",
            NodeRenderQualitySpec.from_value(self.render_quality),
        )


@dataclass(slots=True)
class ExecutionContext:
    run_id: str
    node_id: str
    workspace_id: str
    inputs: dict[str, Any]
    properties: dict[str, Any]
    emit_log: Callable[[str, str], None]
    trigger: dict[str, Any] = field(default_factory=dict)
    should_stop: Callable[[], bool] = field(default=lambda: False)
    register_cancel: Callable[[Callable[[], None]], None] = field(default=lambda _callback: None)

    def log_info(self, message: str) -> None:
        self.emit_log("info", message)

    def log_warning(self, message: str) -> None:
        self.emit_log("warning", message)

    def log_error(self, message: str) -> None:
        self.emit_log("error", message)


@dataclass(slots=True)
class NodeResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    completed: bool = True
    warnings: tuple[str, ...] = ()


class NodePlugin(Protocol):
    def spec(self) -> NodeTypeSpec:
        ...

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ...


class AsyncNodePlugin(NodePlugin, Protocol):
    """Extended protocol for nodes that support non-blocking execution.

    Set ``is_async=True`` in the NodeTypeSpec and implement ``async_execute``
    instead of (or in addition to) ``execute``.  The worker will run async
    nodes in a thread pool so they don't block the rest of the pipeline.
    """

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


def property_has_inline_editor(property_spec: PropertySpec) -> bool:
    return bool(str(property_spec.inline_editor).strip())


def inline_property_specs(spec: NodeTypeSpec) -> tuple[PropertySpec, ...]:
    return tuple(
        property_spec
        for property_spec in spec.properties
        if property_has_inline_editor(property_spec)
    )


def property_inspector_editor(property_spec: PropertySpec) -> str:
    editor = str(property_spec.inspector_editor).strip()
    if editor:
        return editor
    if property_spec.type == "bool":
        return "toggle"
    if property_spec.type == "enum":
        return "enum"
    if property_spec.type == "path":
        return "path"
    return "text"


def property_visible_in_inspector(property_spec: PropertySpec) -> bool:
    return bool(property_spec.inspector_visible)
