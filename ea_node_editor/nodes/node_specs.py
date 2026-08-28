# Purpose: Define node, port, property, and DPF pin metadata records.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_registry_validation.py

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from ea_node_editor.nodes.solution_provenance import SolutionProvenanceInputSpec
from ea_node_editor.runtime_contracts.data_tree import DataAccess
from ea_node_editor.nodes.category_paths import (
    CategoryPath,
    category_display,
    normalize_category_path,
)

PortDirection = Literal["in", "out", "neutral"]
PortSide = Literal["", "top", "right", "bottom", "left"]
PortKind = Literal["data", "flow"]
PortDisplayTier = Literal["", "simple", "advanced"]
PropertyType = Literal["str", "int", "float", "bool", "path", "enum", "json", "interval_1d"]
InlineEditorType = Literal[
    "",
    "text",
    "number",
    "toggle",
    "enum",
    "path",
    "textarea",
    "color",
    "slider",
    "interval_slider",
    "interval_fields",
    "list",
    "secret",
]
ListItemType = Literal["", "str", "int", "float", "enum", "color"]
InspectorEditorType = Literal[
    "",
    "text",
    "textarea",
    "path",
    "toggle",
    "enum",
    "color",
    "font_family",
    "secret",
]
RuntimeBehavior = Literal["active", "passive", "compile_only"]
SolutionReuseScope = Literal["never", "session", "durable"]
SurfaceFamily = Literal[
    "standard",
    "flowchart",
    "planning",
    "annotation",
    "group_backdrop",
    "media",
    "viewer",
    "web",
    "jupyter",
]
RenderQualityTier = Literal["full", "reduced", "proxy"]
DpfPinDirection = Literal["input", "output"]
DpfPinValueOrigin = Literal["port", "property"]
DpfPinPresence = Literal["required", "optional"]
DpfPinOmissionSemantics = Literal["disallowed", "skip", "operator_default"]
DpfCallableKind = Literal["constructor", "factory", "mutator"]
DpfCallableBindingKind = Literal["parameter", "receiver", "return_value"]
DpfNodeStability = Literal["", "core", "advanced", "raw"]
DynamicPortRenameMode = Literal["none", "label", "key"]

_SUPPORTED_RENDER_QUALITY_TIERS = {"full", "reduced", "proxy"}
_SUPPORTED_DPF_PIN_DIRECTIONS = {"input", "output"}
_SUPPORTED_DPF_PIN_VALUE_ORIGINS = {"port", "property"}
_SUPPORTED_DPF_PIN_PRESENCE = {"required", "optional"}
_SUPPORTED_DPF_PIN_OMISSION_SEMANTICS = {"disallowed", "skip", "operator_default"}
_SUPPORTED_DPF_CALLABLE_KINDS = {"constructor", "factory", "mutator"}
_SUPPORTED_DPF_CALLABLE_BINDING_KINDS = {"parameter", "receiver", "return_value"}
_SUPPORTED_DPF_NODE_STABILITY = {"", "core", "advanced", "raw"}
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


def _normalize_dpf_node_stability(field_name: str, value: object) -> str:
    normalized = _normalize_trimmed_string(field_name, value, allow_empty=True)
    if normalized not in _SUPPORTED_DPF_NODE_STABILITY:
        raise ValueError(f"{field_name} has invalid value: {normalized}")
    return normalized


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
    source_path: str = ""
    family_path: tuple[str, ...] = ()
    stability: DpfNodeStability = ""

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
        object.__setattr__(
            self,
            "source_path",
            _normalize_trimmed_string("dpf operator source_path", self.source_path, allow_empty=True),
        )
        object.__setattr__(
            self,
            "family_path",
            _normalize_string_tuple("dpf operator family_path", self.family_path, allow_empty=True),
        )
        object.__setattr__(
            self,
            "stability",
            _normalize_dpf_node_stability("dpf operator stability", self.stability),
        )

    @property
    def variant_keys(self) -> tuple[str, ...]:
        return tuple(variant.key for variant in self.variants)


@dataclass(slots=True, frozen=True)
class DpfCallableSourceSpec:
    callable_name: str
    callable_kind: DpfCallableKind
    backend: str = "ansys.dpf.core"
    source_path: str = ""
    family_path: tuple[str, ...] = ()
    stability: DpfNodeStability = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "backend",
            _normalize_trimmed_string("dpf callable backend", self.backend),
        )
        object.__setattr__(
            self,
            "callable_name",
            _normalize_trimmed_string("dpf callable callable_name", self.callable_name),
        )
        if self.callable_kind not in _SUPPORTED_DPF_CALLABLE_KINDS:
            raise ValueError(f"dpf callable callable_kind has invalid value: {self.callable_kind}")
        object.__setattr__(
            self,
            "source_path",
            _normalize_trimmed_string("dpf callable source_path", self.source_path, allow_empty=True),
        )
        object.__setattr__(
            self,
            "family_path",
            _normalize_string_tuple("dpf callable family_path", self.family_path, allow_empty=True),
        )
        object.__setattr__(
            self,
            "stability",
            _normalize_dpf_node_stability("dpf callable stability", self.stability),
        )


@dataclass(slots=True, frozen=True)
class DpfCallableBindingSpec:
    binding_kind: DpfCallableBindingKind
    binding_name: str = ""

    def __post_init__(self) -> None:
        if self.binding_kind not in _SUPPORTED_DPF_CALLABLE_BINDING_KINDS:
            raise ValueError(f"dpf callable binding_kind has invalid value: {self.binding_kind}")
        object.__setattr__(
            self,
            "binding_name",
            _normalize_trimmed_string(
                "dpf callable binding_name",
                self.binding_name,
                allow_empty=True,
            ),
        )
        if self.binding_kind == "parameter" and not self.binding_name:
            raise ValueError("dpf callable parameter bindings must declare a binding_name")


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
    accepted_data_types: tuple[str, ...] = ()
    callable_binding: DpfCallableBindingSpec | None = None

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
        object.__setattr__(
            self,
            "accepted_data_types",
            _normalize_string_tuple(
                "dpf accepted_data_types",
                self.accepted_data_types,
                allow_empty=True,
            ),
        )
        if self.callable_binding is not None and not isinstance(
            self.callable_binding,
            DpfCallableBindingSpec,
        ):
            raise TypeError("dpf callable_binding must be DpfCallableBindingSpec or None")


def _coerce_dpf_node_source_metadata(
    value: DpfOperatorSourceSpec | DpfCallableSourceSpec | None,
    *,
    field_name: str,
) -> DpfOperatorSourceSpec | DpfCallableSourceSpec | None:
    if value is None or isinstance(value, (DpfOperatorSourceSpec, DpfCallableSourceSpec)):
        return value
    raise TypeError(f"{field_name} must be a DpfOperatorSourceSpec, DpfCallableSourceSpec, or None")


def _coerce_dpf_pin_source_metadata(
    value: DpfPinSourceSpec | None,
    *,
    field_name: str,
) -> DpfPinSourceSpec | None:
    if value is None or isinstance(value, DpfPinSourceSpec):
        return value
    raise TypeError(f"{field_name} must be a DpfPinSourceSpec or None")


@dataclass(slots=True, frozen=True)
class PropertyConditionSpec:
    property_key: str
    values: tuple[object, ...] = ()


@dataclass(slots=True, frozen=True)
class ReadinessRequirementSpec:
    any_of_ports: tuple[str, ...] = ()
    any_of_properties: tuple[str, ...] = ()
    when_ports_present: tuple[str, ...] = ()
    when_properties: tuple[PropertyConditionSpec, ...] = ()


@dataclass(slots=True, frozen=True)
class PortSpec:
    key: str
    direction: PortDirection
    kind: PortKind
    data_type: str
    label: str = ""
    required: bool | None = None
    uses_property_default: bool = False
    exposed: bool = True
    allow_multiple_connections: bool = False
    side: PortSide = ""
    source_metadata: DpfPinSourceSpec | None = None
    accepted_data_types: tuple[str, ...] = ()
    display_tier: PortDisplayTier = ""
    description: str = ""
    data_access: DataAccess = "item"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "description",
            _normalize_trimmed_string(
                "PortSpec.description",
                self.description,
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "source_metadata",
            _coerce_dpf_pin_source_metadata(
                self.source_metadata,
                field_name="PortSpec.source_metadata",
            ),
        )
        object.__setattr__(
            self,
            "accepted_data_types",
            _normalize_string_tuple(
                "PortSpec.accepted_data_types",
                self.accepted_data_types,
                allow_empty=True,
            ),
        )


@dataclass(slots=True, frozen=True)
class DynamicPortGroupSpec:
    group_id: str
    property_key: str
    direction: Literal["in", "out"]
    ports_resolver: Callable[[Mapping[str, object]], tuple[PortSpec, ...]]
    key_factory: Callable[[Mapping[str, object]], str]
    minimum: int = 0
    maximum: int | None = None
    rename_mode: DynamicPortRenameMode = "none"
    key_renamer: Callable[[Mapping[str, object], str, str], str] | None = None


@dataclass(slots=True, frozen=True)
class PropertySpec:
    key: str
    type: PropertyType
    default: Any
    label: str
    expose_port_toggle: bool = False
    enum_values: tuple[str, ...] = ()
    enum_codes: tuple[Any, ...] = ()
    # Numeric domain for scalar and Interval 1D slider editors.
    minimum: float | None = None
    maximum: float | None = None
    step: float = 0.0
    inline_editor: InlineEditorType = ""
    inspector_editor: InspectorEditorType = ""
    inspector_visible: bool = True
    source_metadata: DpfPinSourceSpec | None = None
    group: str = ""
    file_filter: str = ""
    enabled_when: PropertyConditionSpec | None = None
    searchable: bool = False
    interval_direction: Literal["", "increasing", "decreasing"] = ""
    description: str = ""
    sensitive: bool = False
    sensitive_scope_key: str = ""
    persistence_data_type_id: str = ""
    nullable: bool = False
    list_item_type: ListItemType = ""
    list_item_enum_values: tuple[str, ...] = ()
    list_item_enum_codes: tuple[Any, ...] = ()
    list_item_minimum: float | None = None
    list_item_maximum: float | None = None
    list_item_step: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "description",
            _normalize_trimmed_string(
                "PropertySpec.description",
                self.description,
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "source_metadata",
            _coerce_dpf_pin_source_metadata(
                self.source_metadata,
                field_name="PropertySpec.source_metadata",
            ),
        )
        object.__setattr__(
            self,
            "file_filter",
            _normalize_trimmed_string("PropertySpec.file_filter", self.file_filter, allow_empty=True),
        )
        object.__setattr__(
            self,
            "sensitive_scope_key",
            _normalize_trimmed_string(
                "PropertySpec.sensitive_scope_key",
                self.sensitive_scope_key,
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "persistence_data_type_id",
            _normalize_trimmed_string(
                "PropertySpec.persistence_data_type_id",
                self.persistence_data_type_id,
                allow_empty=True,
            ),
        )


@dataclass(slots=True, frozen=True)
class SettingsGroupItemSpec:
    port_key: str = ""
    property_key: str = ""


@dataclass(slots=True, frozen=True)
class SettingsGroupSpec:
    group_id: str
    label: str
    items: tuple[SettingsGroupItemSpec, ...]


@dataclass(slots=True, frozen=True)
class NodeRenderQualitySpec:
    supported_quality_tiers: tuple[RenderQualityTier, ...] = ("full",)

    def __post_init__(self) -> None:
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
            supported_quality_tiers=raw_tiers,  # type: ignore[arg-type]
        )

    def to_payload(self) -> dict[str, Any]:
        return {
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
    solution_reuse_scope: SolutionReuseScope = "never"
    solution_provenance_inputs: tuple[SolutionProvenanceInputSpec, ...] = ()
    surface_family: SurfaceFamily = "standard"
    surface_variant: str = ""
    render_quality: NodeRenderQualitySpec = field(default_factory=NodeRenderQualitySpec)
    source_metadata: DpfOperatorSourceSpec | DpfCallableSourceSpec | None = None
    # Opt-in title-icon override for passive nodes.
    #
    # By default, passive nodes suppress the header icon (see
    # ``title_icon_source_for_node_payload``) because the passive flowchart,
    # planning, annotation, and media families draw their own body art and a
    # title-bar icon would clash. Data-source-style passive nodes (e.g.
    # ``io.path_pointer``) have no such body art and benefit from the icon,
    # so they set this flag to opt back in. Active and compile_only nodes
    # show their icon regardless; this flag is a no-op for them.
    show_title_icon: bool = False
    keywords: tuple[str, ...] = ()
    settings_groups: tuple[SettingsGroupSpec, ...] = ()
    readiness_requirements: tuple[ReadinessRequirementSpec, ...] = ()
    dynamic_port_groups: tuple[DynamicPortGroupSpec, ...] = ()
    instance_spec_resolver: Callable[
        ["NodeTypeSpec", Mapping[str, object]], "NodeTypeSpec"
    ] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.solution_provenance_inputs, tuple) or any(
            not isinstance(item, SolutionProvenanceInputSpec)
            for item in self.solution_provenance_inputs
        ):
            raise TypeError(
                "NodeTypeSpec.solution_provenance_inputs must be a tuple of "
                "SolutionProvenanceInputSpec values"
            )
        provenance_keys = tuple(
            item.property_key for item in self.solution_provenance_inputs
        )
        if len(provenance_keys) != len(set(provenance_keys)):
            raise ValueError("solution provenance property keys must be unique")
        object.__setattr__(
            self,
            "keywords",
            _normalize_string_tuple(
                "NodeTypeSpec.keywords",
                self.keywords,
                allow_empty=True,
            ),
        )
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
            _coerce_dpf_node_source_metadata(
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
    "CategoryPath",
    "DataAccess",
    "DynamicPortGroupSpec",
    "DynamicPortRenameMode",
    "DpfCallableBindingKind",
    "DpfCallableBindingSpec",
    "DpfCallableKind",
    "DpfCallableSourceSpec",
    "DpfNodeStability",
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
    "NodeRenderQualitySpec",
    "NodeTypeSpec",
    "PortDirection",
    "PortDisplayTier",
    "PortKind",
    "PortSide",
    "PortSpec",
    "PropertySpec",
    "PropertyType",
    "PropertyConditionSpec",
    "ReadinessRequirementSpec",
    "RenderQualityTier",
    "RuntimeBehavior",
    "SolutionReuseScope",
    "SettingsGroupItemSpec",
    "SettingsGroupSpec",
    "SurfaceFamily",
    "inline_property_specs",
    "property_has_inline_editor",
    "property_inspector_editor",
    "property_visible_in_inspector",
]
