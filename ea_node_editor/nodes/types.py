from __future__ import annotations

import asyncio
import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol

from ea_node_editor.persistence.artifact_refs import (
    ManagedArtifactRef,
    StagedArtifactRef,
    format_managed_artifact_ref,
    format_staged_artifact_ref,
    parse_artifact_ref,
)

if TYPE_CHECKING:
    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot

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
RuntimeArtifactScope = Literal["managed", "staged"]

_SUPPORTED_RENDER_WEIGHT_CLASSES = {"standard", "heavy"}
_SUPPORTED_MAX_PERFORMANCE_STRATEGIES = {"generic_fallback", "proxy_surface"}
_SUPPORTED_RENDER_QUALITY_TIERS = {"full", "reduced", "proxy"}
_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"
_RUNTIME_ARTIFACT_MARKER_VALUE = "artifact_ref"
_RUNTIME_HANDLE_MARKER_VALUE = "handle_ref"


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


def _copy_metadata_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): copy.deepcopy(item)
        for key, item in value.items()
    }


def _normalize_required_runtime_string(field_name: str, value: object) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_worker_generation(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("worker_generation must be an integer")
    try:
        generation = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("worker_generation must be an integer") from exc
    if generation < 0:
        raise ValueError("worker_generation must be >= 0")
    return generation


@dataclass(slots=True, frozen=True)
class RuntimeArtifactRef:
    ref: str
    artifact_id: str
    scope: RuntimeArtifactScope
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parsed = parse_artifact_ref(self.ref)
        if self.scope == "managed":
            if not isinstance(parsed, ManagedArtifactRef):
                raise ValueError(f"Runtime artifact ref is not managed: {self.ref!r}")
            normalized_ref = parsed.as_string()
        elif self.scope == "staged":
            if not isinstance(parsed, StagedArtifactRef):
                raise ValueError(f"Runtime artifact ref is not staged: {self.ref!r}")
            normalized_ref = parsed.as_string()
        else:
            raise ValueError(f"Unsupported runtime artifact scope: {self.scope!r}")

        if self.artifact_id != parsed.artifact_id:
            raise ValueError(
                "Runtime artifact ref artifact_id does not match the ref payload: "
                f"{self.artifact_id!r} != {parsed.artifact_id!r}"
            )

        object.__setattr__(self, "ref", normalized_ref)
        object.__setattr__(self, "metadata", _copy_metadata_mapping(self.metadata))

    @classmethod
    def managed(
        cls,
        artifact_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        return cls(
            ref=format_managed_artifact_ref(artifact_id),
            artifact_id=str(artifact_id).strip(),
            scope="managed",
            metadata=_copy_metadata_mapping(metadata),
        )

    @classmethod
    def staged(
        cls,
        artifact_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        return cls(
            ref=format_staged_artifact_ref(artifact_id),
            artifact_id=str(artifact_id).strip(),
            scope="staged",
            metadata=_copy_metadata_mapping(metadata),
        )

    @classmethod
    def from_artifact_ref(
        cls,
        value: object,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        parsed = parse_artifact_ref(value)
        if isinstance(parsed, ManagedArtifactRef):
            return cls.managed(parsed.artifact_id, metadata=metadata)
        if isinstance(parsed, StagedArtifactRef):
            return cls.staged(parsed.artifact_id, metadata=metadata)
        raise ValueError(f"Unsupported runtime artifact ref value: {value!r}")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RuntimeArtifactRef | None:
        if str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip() != _RUNTIME_ARTIFACT_MARKER_VALUE:
            return None
        metadata = payload.get("metadata")
        ref_value = str(payload.get("ref", "")).strip()
        if not ref_value:
            return None
        runtime_ref = cls.from_artifact_ref(
            ref_value,
            metadata=metadata if isinstance(metadata, Mapping) else None,
        )
        payload_scope = str(payload.get("scope", "")).strip()
        payload_artifact_id = str(payload.get("artifact_id", "")).strip()
        if payload_scope and payload_scope != runtime_ref.scope:
            raise ValueError(
                "Runtime artifact ref payload scope does not match the ref value: "
                f"{payload_scope!r} != {runtime_ref.scope!r}"
            )
        if payload_artifact_id and payload_artifact_id != runtime_ref.artifact_id:
            raise ValueError(
                "Runtime artifact ref payload artifact_id does not match the ref value: "
                f"{payload_artifact_id!r} != {runtime_ref.artifact_id!r}"
            )
        return runtime_ref

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_ARTIFACT_MARKER_VALUE,
            "ref": self.ref,
            "artifact_id": self.artifact_id,
            "scope": self.scope,
        }
        if self.metadata:
            payload["metadata"] = _copy_metadata_mapping(self.metadata)
        return payload

    def __str__(self) -> str:
        return self.ref


@dataclass(slots=True, frozen=True)
class RuntimeHandleRef:
    handle_id: str
    kind: str
    owner_scope: str
    worker_generation: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "handle_id",
            _normalize_required_runtime_string("handle_id", self.handle_id),
        )
        object.__setattr__(self, "kind", _normalize_required_runtime_string("kind", self.kind))
        object.__setattr__(
            self,
            "owner_scope",
            _normalize_required_runtime_string("owner_scope", self.owner_scope),
        )
        object.__setattr__(
            self,
            "worker_generation",
            _normalize_worker_generation(self.worker_generation),
        )
        object.__setattr__(self, "metadata", _copy_metadata_mapping(self.metadata))

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RuntimeHandleRef | None:
        if str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip() != _RUNTIME_HANDLE_MARKER_VALUE:
            return None
        if "worker_generation" not in payload:
            raise ValueError("Runtime handle ref payload is missing worker_generation")
        return cls(
            handle_id=payload.get("handle_id", ""),
            kind=payload.get("kind", ""),
            owner_scope=payload.get("owner_scope", ""),
            worker_generation=payload.get("worker_generation", 0),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else None,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_HANDLE_MARKER_VALUE,
            "handle_id": self.handle_id,
            "kind": self.kind,
            "owner_scope": self.owner_scope,
            "worker_generation": self.worker_generation,
        }
        if self.metadata:
            payload["metadata"] = _copy_metadata_mapping(self.metadata)
        return payload


def coerce_runtime_artifact_ref(value: object) -> RuntimeArtifactRef | None:
    if isinstance(value, RuntimeArtifactRef):
        return value
    if isinstance(value, Mapping):
        payload_ref = RuntimeArtifactRef.from_payload(value)
        if payload_ref is not None:
            return payload_ref
    parsed = parse_artifact_ref(value)
    if isinstance(parsed, ManagedArtifactRef):
        return RuntimeArtifactRef.managed(parsed.artifact_id)
    if isinstance(parsed, StagedArtifactRef):
        return RuntimeArtifactRef.staged(parsed.artifact_id)
    return None


def coerce_runtime_handle_ref(value: object) -> RuntimeHandleRef | None:
    if isinstance(value, RuntimeHandleRef):
        return value
    if isinstance(value, Mapping):
        return RuntimeHandleRef.from_payload(value)
    return None


def serialize_runtime_value(value: Any) -> Any:
    from ea_node_editor.execution.runtime_value_codec import serialize_runtime_value as _serialize_runtime_value

    return _serialize_runtime_value(value)


def deserialize_runtime_value(value: Any) -> Any:
    from ea_node_editor.execution.runtime_value_codec import deserialize_runtime_value as _deserialize_runtime_value

    return _deserialize_runtime_value(value)


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
    project_path: str = ""
    runtime_snapshot: RuntimeSnapshot | None = None
    path_resolver: Callable[[Any], Path | None] = field(default=lambda _value: None)
    worker_services: Any = None

    def log_info(self, message: str) -> None:
        self.emit_log("info", message)

    def log_warning(self, message: str) -> None:
        self.emit_log("warning", message)

    def log_error(self, message: str) -> None:
        self.emit_log("error", message)

    def runtime_artifact_ref(self, value: Any) -> RuntimeArtifactRef | None:
        return coerce_runtime_artifact_ref(value)

    def runtime_handle_ref(self, value: Any) -> RuntimeHandleRef | None:
        return coerce_runtime_handle_ref(value)

    def _require_worker_services(self) -> Any:
        if self.worker_services is None:
            raise RuntimeError("ExecutionContext does not have worker services.")
        return self.worker_services

    def register_handle(
        self,
        value: Any,
        *,
        kind: str,
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        return self._require_worker_services().register_handle(
            value,
            kind=kind,
            run_id=self.run_id,
            owner_scope=owner_scope,
            metadata=metadata,
        )

    def resolve_handle(self, value: Any, *, expected_kind: str = "") -> Any:
        runtime_ref = self.runtime_handle_ref(value)
        if runtime_ref is None:
            raise TypeError("ExecutionContext.resolve_handle requires a RuntimeHandleRef payload.")
        return self._require_worker_services().resolve_handle(runtime_ref, expected_kind=expected_kind)

    def release_handle(self, value: Any) -> bool:
        runtime_ref = self.runtime_handle_ref(value)
        if runtime_ref is None:
            raise TypeError("ExecutionContext.release_handle requires a RuntimeHandleRef payload.")
        return self._require_worker_services().release_handle(runtime_ref)

    def handle_ref(
        self,
        value: Any,
        *,
        kind: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        return self._require_worker_services().handle_ref(
            value,
            kind=kind,
            run_id=self.run_id,
            owner_scope=owner_scope,
            metadata=metadata,
        )

    def resolve_path_value(self, value: Any) -> Path | None:
        runtime_ref = self.runtime_artifact_ref(value)
        candidate = runtime_ref.ref if runtime_ref is not None else value
        return self.path_resolver(candidate)

    def resolve_input_path(self, input_key: str, *, property_key: str = "") -> Path | None:
        candidates = [self.inputs.get(input_key)]
        if property_key:
            candidates.append(self.properties.get(property_key))
        for candidate in candidates:
            path = self.resolve_path_value(candidate)
            if path is not None:
                return path
        return None


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
