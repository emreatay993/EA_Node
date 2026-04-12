from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from ea_node_editor.nodes.category_paths import (
    CategoryPath,
    category_display,
    normalize_category_path,
)

PortDirection = Literal["in", "out", "neutral"]
PortSide = Literal["", "top", "right", "bottom", "left"]
PortKind = Literal["exec", "completed", "failed", "data", "flow"]
PropertyType = Literal["str", "int", "float", "bool", "path", "enum", "json"]
InlineEditorType = Literal["", "text", "number", "toggle", "enum", "path", "textarea", "color"]
InspectorEditorType = Literal["", "text", "textarea", "path", "toggle", "enum", "color"]
RuntimeBehavior = Literal["active", "passive", "compile_only"]
SurfaceFamily = Literal[
    "standard",
    "flowchart",
    "planning",
    "annotation",
    "comment_backdrop",
    "media",
    "viewer",
]
RenderWeightClass = Literal["standard", "heavy"]
MaxPerformanceStrategy = Literal["generic_fallback", "proxy_surface"]
RenderQualityTier = Literal["full", "reduced", "proxy"]
DpfPinDirection = Literal["input", "output"]
DpfPinValueOrigin = Literal["port", "property"]
DpfPinPresence = Literal["required", "optional"]
DpfPinOmissionSemantics = Literal["disallowed", "skip", "operator_default"]

DPF_RESULT_FILE_DATA_TYPE = "dpf_result_file"
DPF_MODEL_DATA_TYPE = "dpf_model"
DPF_MESH_DATA_TYPE = "dpf_mesh"
DPF_FIELD_DATA_TYPE = "dpf_field"
DPF_SCOPING_DATA_TYPE = "dpf_scoping"
DPF_VIEW_SESSION_DATA_TYPE = "dpf_view_session"
DPF_PUBLIC_DATA_TYPES = (
    DPF_MODEL_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_VIEW_SESSION_DATA_TYPE,
)

_SUPPORTED_RENDER_WEIGHT_CLASSES = {"standard", "heavy"}
_SUPPORTED_MAX_PERFORMANCE_STRATEGIES = {"generic_fallback", "proxy_surface"}
_SUPPORTED_RENDER_QUALITY_TIERS = {"full", "reduced", "proxy"}
_SUPPORTED_DPF_PIN_DIRECTIONS = {"input", "output"}
_SUPPORTED_DPF_PIN_VALUE_ORIGINS = {"port", "property"}
_SUPPORTED_DPF_PIN_PRESENCE = {"required", "optional"}
_SUPPORTED_DPF_PIN_OMISSION_SEMANTICS = {"disallowed", "skip", "operator_default"}


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


def _normalize_trimmed_string(
    field_name: str,
    value: object,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if normalized != value:
        raise ValueError(f"{field_name} must be a trimmed string")
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must be a non-empty trimmed string")
    return normalized


def _normalize_string_tuple(
    field_name: str,
    value: object,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_values: Sequence[object] = (value,)
    elif isinstance(value, Sequence):
        raw_values = value
    else:
        raise TypeError(f"{field_name} must be a sequence of strings")

    normalized: list[str] = []
    seen: set[str] = set()
    for index, raw_value in enumerate(raw_values):
        item = _normalize_trimmed_string(
            f"{field_name}[{index}]",
            raw_value,
            allow_empty=False,
        )
        if item in seen:
            raise ValueError(f"{field_name} must not contain duplicates")
        normalized.append(item)
        seen.add(item)

    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must contain at least one value")
    return tuple(normalized)


@dataclass(slots=True, frozen=True)
class DpfOperatorSelectorCondition:
    property_key: str
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "property_key",
            _normalize_trimmed_string("dpf selector property_key", self.property_key),
        )
        object.__setattr__(
            self,
            "values",
            _normalize_string_tuple("dpf selector values", self.values),
        )


@dataclass(slots=True, frozen=True)
class DpfOperatorVariantSpec:
    key: str
    operator_name: str = ""
    operator_name_template: str = ""
    selector_conditions: tuple[DpfOperatorSelectorCondition, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "key",
            _normalize_trimmed_string("dpf operator variant key", self.key),
        )
        operator_name = _normalize_trimmed_string(
            "dpf operator variant operator_name",
            self.operator_name,
            allow_empty=True,
        )
        operator_name_template = _normalize_trimmed_string(
            "dpf operator variant operator_name_template",
            self.operator_name_template,
            allow_empty=True,
        )
        if bool(operator_name) == bool(operator_name_template):
            raise ValueError(
                "dpf operator variants must define exactly one of operator_name or operator_name_template"
            )
        object.__setattr__(self, "operator_name", operator_name)
        object.__setattr__(self, "operator_name_template", operator_name_template)
        if not isinstance(self.selector_conditions, tuple):
            raise TypeError("dpf operator variant selector_conditions must be a tuple")
        for index, condition in enumerate(self.selector_conditions):
            if not isinstance(condition, DpfOperatorSelectorCondition):
                raise TypeError(
                    f"dpf operator variant selector_conditions[{index}] must be DpfOperatorSelectorCondition"
                )


@dataclass(slots=True, frozen=True)
class DpfOperatorSourceSpec:
    backend: str = "ansys.dpf.core"
    variants: tuple[DpfOperatorVariantSpec, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "backend",
            _normalize_trimmed_string("dpf operator backend", self.backend),
        )
        if not isinstance(self.variants, tuple):
            raise TypeError("dpf operator variants must be a tuple")
        if not self.variants:
            raise ValueError("dpf operator variants must contain at least one variant")
        variant_keys: set[str] = set()
        for index, variant in enumerate(self.variants):
            if not isinstance(variant, DpfOperatorVariantSpec):
                raise TypeError(f"dpf operator variants[{index}] must be DpfOperatorVariantSpec")
            if variant.key in variant_keys:
                raise ValueError(f"dpf operator variants must not reuse the key {variant.key!r}")
            variant_keys.add(variant.key)

    @property
    def variant_keys(self) -> tuple[str, ...]:
        return tuple(variant.key for variant in self.variants)


@dataclass(slots=True, frozen=True)
class DpfPinSourceSpec:
    pin_name: str
    pin_direction: DpfPinDirection
    value_origin: DpfPinValueOrigin
    value_key: str
    data_type: str
    presence: DpfPinPresence = "optional"
    omission_semantics: DpfPinOmissionSemantics = "skip"
    exclusive_group: str = ""
    variant_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pin_name",
            _normalize_trimmed_string("dpf pin_name", self.pin_name),
        )
        object.__setattr__(
            self,
            "value_key",
            _normalize_trimmed_string("dpf value_key", self.value_key),
        )
        object.__setattr__(
            self,
            "data_type",
            _normalize_trimmed_string("dpf data_type", self.data_type),
        )
        object.__setattr__(
            self,
            "exclusive_group",
            _normalize_trimmed_string(
                "dpf exclusive_group",
                self.exclusive_group,
                allow_empty=True,
            ),
        )
        if self.pin_direction not in _SUPPORTED_DPF_PIN_DIRECTIONS:
            raise ValueError(f"dpf pin_direction has invalid value: {self.pin_direction}")
        if self.value_origin not in _SUPPORTED_DPF_PIN_VALUE_ORIGINS:
            raise ValueError(f"dpf value_origin has invalid value: {self.value_origin}")
        if self.presence not in _SUPPORTED_DPF_PIN_PRESENCE:
            raise ValueError(f"dpf presence has invalid value: {self.presence}")
        if self.omission_semantics not in _SUPPORTED_DPF_PIN_OMISSION_SEMANTICS:
            raise ValueError(
                f"dpf omission_semantics has invalid value: {self.omission_semantics}"
            )
        if self.presence == "required" and self.omission_semantics != "disallowed":
            raise ValueError(
                "required dpf input bindings must use disallowed omission semantics"
            )
        if self.pin_direction == "output" and self.value_origin != "port":
            raise ValueError("dpf output bindings must originate from a port")
        object.__setattr__(
            self,
            "variant_keys",
            _normalize_string_tuple(
                "dpf variant_keys",
                self.variant_keys,
                allow_empty=True,
            ),
        )


def _coerce_dpf_operator_source_metadata(
    value: DpfOperatorSourceSpec | None,
    *,
    field_name: str,
) -> DpfOperatorSourceSpec | None:
    if value is None or isinstance(value, DpfOperatorSourceSpec):
        return value
    raise TypeError(f"{field_name} must be a DpfOperatorSourceSpec or None")


def _coerce_dpf_pin_source_metadata(
    value: DpfPinSourceSpec | None,
    *,
    field_name: str,
) -> DpfPinSourceSpec | None:
    if value is None or isinstance(value, DpfPinSourceSpec):
        return value
    raise TypeError(f"{field_name} must be a DpfPinSourceSpec or None")


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
    source_metadata: DpfPinSourceSpec | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_metadata",
            _coerce_dpf_pin_source_metadata(
                self.source_metadata,
                field_name="PortSpec.source_metadata",
            ),
        )


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
    source_metadata: DpfPinSourceSpec | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_metadata",
            _coerce_dpf_pin_source_metadata(
                self.source_metadata,
                field_name="PropertySpec.source_metadata",
            ),
        )


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
    category_path: CategoryPath
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
    source_metadata: DpfOperatorSourceSpec | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "category_path",
            normalize_category_path(self.category_path),
        )
        object.__setattr__(
            self,
            "render_quality",
            NodeRenderQualitySpec.from_value(self.render_quality),
        )
        object.__setattr__(
            self,
            "source_metadata",
            _coerce_dpf_operator_source_metadata(
                self.source_metadata,
                field_name="NodeTypeSpec.source_metadata",
            ),
        )

    @property
    def category(self) -> str:
        return category_display(self.category_path)


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


__all__ = [
    "DPF_FIELD_DATA_TYPE",
    "DPF_MESH_DATA_TYPE",
    "DPF_MODEL_DATA_TYPE",
    "DPF_PUBLIC_DATA_TYPES",
    "DPF_RESULT_FILE_DATA_TYPE",
    "DPF_SCOPING_DATA_TYPE",
    "DPF_VIEW_SESSION_DATA_TYPE",
    "CategoryPath",
    "DpfOperatorSelectorCondition",
    "DpfOperatorSourceSpec",
    "DpfOperatorVariantSpec",
    "DpfPinDirection",
    "DpfPinOmissionSemantics",
    "DpfPinPresence",
    "DpfPinSourceSpec",
    "DpfPinValueOrigin",
    "InlineEditorType",
    "InspectorEditorType",
    "MaxPerformanceStrategy",
    "NodeRenderQualitySpec",
    "NodeTypeSpec",
    "PortDirection",
    "PortKind",
    "PortSide",
    "PortSpec",
    "PropertySpec",
    "PropertyType",
    "RenderQualityTier",
    "RenderWeightClass",
    "RuntimeBehavior",
    "SurfaceFamily",
    "inline_property_specs",
    "property_has_inline_editor",
    "property_inspector_editor",
    "property_visible_in_inspector",
]
