from __future__ import annotations

import importlib
import pkgutil
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache, partial
from typing import Any

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    humanize_dpf_symbol_name,
    normalize_dpf_descriptor_spec,
    normalize_dpf_live_type_name,
    require_dpf_runtime_service,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_OPERATOR_FAMILY_ORDER,
    dpf_category_path,
    operator_family_display_name,
)
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import (
    DpfOperatorSourceSpec,
    DpfOperatorVariantSpec,
    DpfPinSourceSpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.plugin_contracts import NodePlugin, PluginDescriptor

_EXEC_IN_PORT = PortSpec("exec_in", "in", "exec", "exec", required=False)
_EXEC_OUT_PORT = PortSpec("exec_out", "out", "exec", "exec", exposed=True)
_GENERATED_OPERATOR_TYPE_ID_PREFIX = "dpf.op"
_GENERATED_OPERATOR_VARIANT_KEY = "default"
_OPERATOR_ICON = "dpf/ansys.svg"
_SKIPPED_OPERATOR_PACKAGES = frozenset({"specification", "translator"})
_ADVANCED_OPERATOR_FAMILIES = frozenset({"compression", "serialization", "server", "info"})
_PRIMITIVE_PROPERTY_TYPES = frozenset({"bool", "int", "float", "str", "json"})
_FAMILY_ORDER_INDEX = {family: index for index, family in enumerate(DPF_OPERATOR_FAMILY_ORDER)}
_KEY_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")


@dataclass(slots=True, frozen=True)
class _GeneratedOperatorDefinition:
    family: str
    module_name: str
    operator_name: str
    display_name: str
    description: str
    source_path: str
    family_path: tuple[str, ...]
    category_path: tuple[str, ...]
    stability: str
    specification: Any


@dataclass(slots=True)
class _GeneratedDpfOperatorNodePlugin:
    _spec: NodeTypeSpec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        invocation = require_dpf_runtime_service(
            ctx,
            node_name=self._spec.display_name,
        ).invoke_operator(
            self._spec.type_id,
            inputs=ctx.inputs,
            properties=ctx.properties,
        )
        outputs = dict(invocation.outputs)
        if any(port.key == "exec_out" for port in self._spec.ports):
            outputs["exec_out"] = True
        return NodeResult(outputs=outputs)


def _operator_family_path(family: str) -> tuple[str, ...]:
    return ("Operators", operator_family_display_name(family))


def _operator_category_path(family: str) -> tuple[str, ...]:
    return dpf_category_path(*_operator_family_path(family))


def _operator_stability(family: str) -> str:
    return "advanced" if family in _ADVANCED_OPERATOR_FAMILIES else "core"


def _load_foundational_operator_plugin_factories() -> tuple[Callable[[], NodePlugin], ...]:
    from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
        DpfFieldOpsNodePlugin,
        DpfResultFieldNodePlugin,
    )

    return (DpfResultFieldNodePlugin, DpfFieldOpsNodePlugin)


_FOUNDATIONAL_DESCRIPTOR_OVERRIDES = {
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "category_path": _operator_category_path("result"),
        "source_path": "ansys.dpf.core.operators.result",
        "family_path": _operator_family_path("result"),
        "stability": _operator_stability("result"),
    },
    DPF_FIELD_OPS_NODE_TYPE_ID: {
        "category_path": _operator_category_path("math"),
        "source_path": "ansys.dpf.core.operators.math",
        "family_path": _operator_family_path("math"),
        "stability": _operator_stability("math"),
    },
}


def _build_foundational_operator_descriptor(factory: Callable[[], NodePlugin]) -> PluginDescriptor:
    normalized_spec = normalize_dpf_descriptor_spec(factory().spec())
    overrides = _FOUNDATIONAL_DESCRIPTOR_OVERRIDES[normalized_spec.type_id]
    node_source = normalized_spec.source_metadata
    if not isinstance(node_source, DpfOperatorSourceSpec):
        raise TypeError(f"Expected DpfOperatorSourceSpec for {normalized_spec.type_id}")

    return PluginDescriptor(
        spec=replace(
            normalized_spec,
            category_path=overrides["category_path"],
            source_metadata=replace(
                node_source,
                source_path=overrides["source_path"],
                family_path=overrides["family_path"],
                stability=overrides["stability"],
            ),
        ),
        factory=factory,
    )


def _sanitize_key(value: object, *, default: str) -> str:
    token = _KEY_SANITIZE_RE.sub("_", str(value or "").strip().lower())
    token = re.sub(r"_+", "_", token).strip("_")
    return token or default


def _unique_key(base: str, seen: set[str], *, fallback: str) -> str:
    candidate = _sanitize_key(base, default=fallback)
    if candidate not in seen:
        seen.add(candidate)
        return candidate
    index = 2
    while f"{candidate}_{index}" in seen:
        index += 1
    unique = f"{candidate}_{index}"
    seen.add(unique)
    return unique


def _property_kind_for_live_type(type_name: str) -> str | None:
    normalized = normalize_dpf_live_type_name(type_name)
    if normalized in _PRIMITIVE_PROPERTY_TYPES:
        return normalized
    return None


def _merge_property_kinds(type_names: Sequence[str]) -> str | None:
    kinds = {kind for kind in (_property_kind_for_live_type(type_name) for type_name in type_names) if kind is not None}
    if not kinds:
        return None
    if kinds <= {"bool"}:
        return "bool"
    if kinds <= {"int"}:
        return "int"
    if kinds <= {"float", "int"}:
        return "float"
    if kinds <= {"str"}:
        return "str"
    if kinds <= {"str", "int"}:
        return "str"
    if kinds <= {"json"}:
        return "json"
    return None


def _mapped_data_types(type_names: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for type_name in type_names:
        normalized = normalize_dpf_live_type_name(type_name)
        if normalized not in ordered:
            ordered.append(normalized)
    return tuple(ordered or ("any",))


def _property_spec_defaults(property_kind: str) -> tuple[str, object, str, str]:
    if property_kind == "bool":
        return "bool", False, "toggle", "toggle"
    if property_kind == "int":
        return "int", 0, "number", "text"
    if property_kind == "float":
        return "float", 0.0, "number", "text"
    if property_kind == "json":
        return "json", [], "textarea", "textarea"
    return "str", "", "text", "text"


def _input_binding_for_pin(pin: Any, *, seen_port_keys: set[str], seen_property_keys: set[str]) -> tuple[PortSpec | None, PropertySpec | None]:
    type_names = tuple(str(type_name) for type_name in getattr(pin, "type_names", ()) or ())
    if getattr(pin, "optional", False):
        property_kind = _merge_property_kinds(type_names)
        if property_kind is not None and all(_property_kind_for_live_type(type_name) is not None for type_name in type_names):
            property_key = _unique_key(str(getattr(pin, "name", "property")), seen_property_keys, fallback="property")
            property_type, default, inline_editor, inspector_editor = _property_spec_defaults(property_kind)
            return None, PropertySpec(
                key=property_key,
                type=property_type,  # type: ignore[arg-type]
                default=default,
                label=humanize_dpf_symbol_name(getattr(pin, "name", property_key)),
                expose_port_toggle=True,
                inline_editor=inline_editor,  # type: ignore[arg-type]
                inspector_editor=inspector_editor,  # type: ignore[arg-type]
                source_metadata=DpfPinSourceSpec(
                    pin_name=str(getattr(pin, "name", property_key)),
                    pin_direction="input",
                    value_origin="property",
                    value_key=property_key,
                    data_type=property_kind,
                    presence="optional",
                    omission_semantics="skip",
                ),
            )

    port_key = _unique_key(str(getattr(pin, "name", "input")), seen_port_keys, fallback="input")
    mapped_data_types = _mapped_data_types(type_names)
    primary_data_type = mapped_data_types[0]
    accepted_data_types = mapped_data_types if len(mapped_data_types) > 1 else ()
    required = not bool(getattr(pin, "optional", False))
    return PortSpec(
        key=port_key,
        direction="in",
        kind="data",
        data_type=primary_data_type,
        label=humanize_dpf_symbol_name(getattr(pin, "name", port_key)),
        required=required,
        exposed=required,
        allow_multiple_connections=bool(getattr(pin, "ellipsis", False)),
        source_metadata=DpfPinSourceSpec(
            pin_name=str(getattr(pin, "name", port_key)),
            pin_direction="input",
            value_origin="port",
            value_key=port_key,
            data_type=primary_data_type,
            presence="required" if required else "optional",
            omission_semantics="disallowed" if required else "skip",
            accepted_data_types=accepted_data_types,
        ),
        accepted_data_types=accepted_data_types,
    ), None


def _output_port_for_pin(pin: Any, *, seen_port_keys: set[str]) -> PortSpec:
    port_key = _unique_key(str(getattr(pin, "name", "output")), seen_port_keys, fallback="output")
    mapped_data_types = _mapped_data_types(tuple(str(type_name) for type_name in getattr(pin, "type_names", ()) or ()))
    primary_data_type = mapped_data_types[0]
    accepted_data_types = mapped_data_types if len(mapped_data_types) > 1 else ()
    return PortSpec(
        key=port_key,
        direction="out",
        kind="data",
        data_type=primary_data_type,
        label=humanize_dpf_symbol_name(getattr(pin, "name", port_key)),
        exposed=True,
        allow_multiple_connections=bool(getattr(pin, "ellipsis", False)),
        source_metadata=DpfPinSourceSpec(
            pin_name=str(getattr(pin, "name", port_key)),
            pin_direction="output",
            value_origin="port",
            value_key=port_key,
            data_type=primary_data_type,
            accepted_data_types=accepted_data_types,
        ),
        accepted_data_types=accepted_data_types,
    )


def _stable_operator_type_id(family: str, module_name: str) -> str:
    return ".".join(
        (
            _GENERATED_OPERATOR_TYPE_ID_PREFIX,
            _sanitize_key(family, default="operator"),
            _sanitize_key(module_name, default="operator"),
        )
    )


def _operator_display_name(properties: Mapping[str, Any], module_name: str) -> str:
    scripting_name = str(properties.get("scripting_name", "") or "").strip()
    if scripting_name:
        return humanize_dpf_symbol_name(scripting_name)
    user_name = str(properties.get("user_name", "") or "").strip()
    if user_name and any(ch.isalnum() for ch in user_name):
        return humanize_dpf_symbol_name(user_name)
    return humanize_dpf_symbol_name(module_name)


def _iter_operator_module_names(package_name: str) -> Iterable[str]:
    package = importlib.import_module(package_name)
    module_names = [
        module_info.name
        for module_info in pkgutil.iter_modules(package.__path__)
        if not module_info.ispkg and not module_info.name.startswith("_")
    ]
    return sorted(module_names)


def _build_generated_operator_definition(family: str, module_name: str) -> _GeneratedOperatorDefinition | None:
    module_path = f"ansys.dpf.core.operators.{family}.{module_name}"
    operator_module = importlib.import_module(module_path)
    operator_class = getattr(operator_module, module_name, None)
    if operator_class is None:
        return None

    try:
        operator = operator_class()
    except Exception:
        return None

    specification = operator.specification
    properties = getattr(specification, "properties", {}) or {}
    exposure = str(properties.get("exposure", "") or "").strip().casefold()
    discovered_family = str(properties.get("category", family) or "").strip().casefold()
    operator_name = str(getattr(operator, "name", "") or "").strip()
    outputs = getattr(specification, "outputs", {}) or {}
    if exposure != "public" or not discovered_family or not operator_name or not outputs:
        return None

    family_path = _operator_family_path(discovered_family)
    description = str(getattr(specification, "description", "") or "").strip()
    if not description:
        description = f"Generated wrapper for ansys.dpf.core.operators.{discovered_family}.{module_name}."

    return _GeneratedOperatorDefinition(
        family=discovered_family,
        module_name=module_name,
        operator_name=operator_name,
        display_name=_operator_display_name(properties, module_name),
        description=description,
        source_path=module_path,
        family_path=family_path,
        category_path=dpf_category_path(*family_path),
        stability=_operator_stability(discovered_family),
        specification=specification,
    )


def _generated_operator_sort_key(definition: _GeneratedOperatorDefinition) -> tuple[int, str, str]:
    return (
        _FAMILY_ORDER_INDEX.get(definition.family, len(_FAMILY_ORDER_INDEX)),
        definition.family,
        definition.module_name,
    )


@lru_cache(maxsize=1)
def _discovered_generated_operator_definitions() -> tuple[_GeneratedOperatorDefinition, ...]:
    import ansys.dpf.core.operators as dpf_operators

    discovered_families = {
        module_info.name
        for module_info in pkgutil.iter_modules(dpf_operators.__path__)
        if module_info.ispkg and module_info.name not in _SKIPPED_OPERATOR_PACKAGES
    }
    ordered_families = [
        family
        for family in DPF_OPERATOR_FAMILY_ORDER
        if family in discovered_families
    ] + sorted(discovered_families - set(DPF_OPERATOR_FAMILY_ORDER))

    definitions: list[_GeneratedOperatorDefinition] = []
    for family in ordered_families:
        package_name = f"ansys.dpf.core.operators.{family}"
        for module_name in _iter_operator_module_names(package_name):
            definition = _build_generated_operator_definition(family, module_name)
            if definition is not None:
                definitions.append(definition)
    definitions.sort(key=_generated_operator_sort_key)
    return tuple(definitions)


def _sorted_pin_items(pin_map: Mapping[Any, Any]) -> list[tuple[Any, Any]]:
    try:
        return sorted(pin_map.items(), key=lambda item: int(item[0]))
    except Exception:
        return list(pin_map.items())


def _build_generated_operator_spec(definition: _GeneratedOperatorDefinition) -> NodeTypeSpec:
    seen_port_keys = {"exec_in", "exec_out"}
    seen_property_keys: set[str] = set()
    ports = [_EXEC_IN_PORT]
    properties: list[PropertySpec] = []

    for _, pin in _sorted_pin_items(getattr(definition.specification, "inputs", {}) or {}):
        port_spec, property_spec = _input_binding_for_pin(
            pin,
            seen_port_keys=seen_port_keys,
            seen_property_keys=seen_property_keys,
        )
        if port_spec is not None:
            ports.append(port_spec)
        if property_spec is not None:
            properties.append(property_spec)

    for _, pin in _sorted_pin_items(getattr(definition.specification, "outputs", {}) or {}):
        ports.append(_output_port_for_pin(pin, seen_port_keys=seen_port_keys))

    ports.append(_EXEC_OUT_PORT)
    return NodeTypeSpec(
        type_id=_stable_operator_type_id(definition.family, definition.module_name),
        display_name=definition.display_name,
        category_path=definition.category_path,
        icon=_OPERATOR_ICON,
        ports=tuple(ports),
        properties=tuple(properties),
        description=definition.description,
        source_metadata=DpfOperatorSourceSpec(
            variants=(
                DpfOperatorVariantSpec(
                    key=_GENERATED_OPERATOR_VARIANT_KEY,
                    operator_name=definition.operator_name,
                ),
            ),
            source_path=definition.source_path,
            family_path=definition.family_path,
            stability=definition.stability,
        ),
    )


def _generated_operator_factory(spec: NodeTypeSpec) -> Callable[[], NodePlugin]:
    return partial(_GeneratedDpfOperatorNodePlugin, spec)


@lru_cache(maxsize=1)
def _generated_operator_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    descriptors: list[PluginDescriptor] = []
    for definition in _discovered_generated_operator_definitions():
        spec = _build_generated_operator_spec(definition)
        descriptors.append(
            PluginDescriptor(
                spec=spec,
                factory=_generated_operator_factory(spec),
            )
        )
    return tuple(descriptors)


@lru_cache(maxsize=1)
def load_ansys_dpf_operator_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    foundational = tuple(
        _build_foundational_operator_descriptor(factory)
        for factory in _load_foundational_operator_plugin_factories()
    )
    return foundational + _generated_operator_plugin_descriptors()


__all__ = [
    "load_ansys_dpf_operator_plugin_descriptors",
]
