from __future__ import annotations

import importlib
import json
import pkgutil
import re
import warnings
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from functools import lru_cache, partial
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from ea_node_editor.common.payload_tools import compact_sequence_metadata
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_HANDLE_KIND,
    DPF_MODEL_DATA_TYPE,
    DPF_OBJECT_HANDLE_KIND,
    DPF_OBJECT_HANDLE_DATA_TYPE,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DPF_WORKFLOW_DATA_TYPE,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    build_field_handle_metadata,
    humanize_dpf_symbol_name,
    normalize_dpf_descriptor_spec,
    normalize_dpf_live_type_name,
    require_dpf_runtime_service,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_OPERATOR_FAMILY_ORDER,
    dpf_category_path,
    operator_family_category_path,
    operator_family_path,
)
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.core_data_types import (
    BOOLEAN_DATA_TYPE_ID,
    DOUBLE_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    JSON_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)
from ea_node_editor.nodes.node_specs import (
    DpfOperatorSourceSpec,
    DpfOperatorSelectorCondition,
    DpfOperatorVariantSpec,
    DpfPinSourceSpec,
    NodeRenderQualitySpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    SettingsGroupItemSpec,
    SettingsGroupSpec,
)
from ea_node_editor.nodes.plugin_contracts import NodePlugin, PluginDescriptor
from ea_node_editor.runtime_contracts import (
    DataTypeCatalogError,
    coerce_runtime_artifact_ref,
    coerce_runtime_handle_ref,
)
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs

_GENERATED_OPERATOR_TYPE_ID_PREFIX = "dpf.op"
_GENERATED_OPERATOR_VARIANT_KEY = "default"
_OPERATOR_ICON = "dpf/ansys.svg"
_SKIPPED_OPERATOR_PACKAGES = frozenset({"specification", "translator"})
_ADVANCED_OPERATOR_FAMILIES = frozenset({"compression", "serialization", "server", "info"})
_PROPERTY_TYPE_BY_DATA_TYPE = {
    BOOLEAN_DATA_TYPE_ID: "bool",
    INTEGER_DATA_TYPE_ID: "int",
    DOUBLE_DATA_TYPE_ID: "float",
    STRING_DATA_TYPE_ID: "str",
    JSON_DATA_TYPE_ID: "json",
}
_FAMILY_ORDER_INDEX = {family: index for index, family in enumerate(DPF_OPERATOR_FAMILY_ORDER)}
_KEY_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")
_USER_NAME_SYMBOL_RE = re.compile(r"[^0-9A-Za-z_\\s]")
_OBJECT_HANDLE_DATA_TYPES = frozenset(
    {
        DPF_DATA_SOURCES_DATA_TYPE,
        DPF_OBJECT_HANDLE_DATA_TYPE,
        DPF_STREAMS_CONTAINER_DATA_TYPE,
        DPF_WORKFLOW_DATA_TYPE,
    }
)
_SINGLE_RUN_OPERATOR_TYPE_IDS = frozenset(
    {
        "dpf.op.mesh.stl_export",
        "dpf.op.result.migrate_to_h5dpf",
        "dpf.op.result.write_cms_rbd_file",
        "dpf.op.result.write_motion_dfmf_file",
        "dpf.op.serialization.data_tree_to_json",
        "dpf.op.serialization.data_tree_to_txt",
        "dpf.op.serialization.export_symbolic_workflow",
        "dpf.op.serialization.hdf5dpf_generate_result_file",
        "dpf.op.serialization.migrate_file_to_vtk",
        "dpf.op.serialization.migrate_to_vtu",
        "dpf.op.serialization.serializer",
        "dpf.op.serialization.vtu_export",
        "dpf.op.serialization.workflow_to_pydpf",
    }
)
_SINGLE_RUN_LIST_INPUTS = {
    "dpf.op.serialization.hdf5dpf_generate_result_file": frozenset({"input_name"}),
    "dpf.op.serialization.migrate_to_vtu": frozenset({"result"}),
    "dpf.op.serialization.serializer": frozenset({"any_input"}),
    "dpf.op.serialization.vtu_export": frozenset({"fields"}),
}
OPERATOR_CATALOG_SCHEMA_VERSION = 1
OPERATOR_CATALOG_PATH = Path(__file__).with_name("operator_catalog.json")
_CATALOG_FALLBACK_WARNED = False


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
        service = require_dpf_runtime_service(
            ctx,
            node_name=self._spec.display_name,
        )
        inputs = ctx.inputs
        if self._spec.type_id in _SINGLE_RUN_OPERATOR_TYPE_IDS:
            inputs = resolve_single_run_inputs(
                inputs,
                node_name=self._spec.display_name,
                list_ports=_SINGLE_RUN_LIST_INPUTS.get(self._spec.type_id, ()),
            )
        invocation = service.invoke_operator(
            self._spec.type_id,
            inputs=inputs,
            properties=ctx.properties,
        )
        outputs = dict(invocation.outputs)
        output_ports = {
            port.key: port
            for port in self._spec.ports
            if port.direction == "out" and port.kind == "data"
        }
        for output_key, output_value in tuple(outputs.items()):
            port = output_ports.get(output_key)
            if port is None:
                continue
            outputs[output_key] = _wrap_generated_dpf_output(
                ctx,
                service=service,
                port=port,
                value=output_value,
            )
        return NodeResult(outputs=outputs)


def _wrap_generated_dpf_output(ctx, *, service, port: PortSpec, value: Any) -> Any:  # noqa: ANN001
    if value is None:
        return None
    if port.data_access == "list":
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return value
        item_port = replace(port, data_access="item")
        return [
            _wrap_generated_dpf_output(ctx, service=service, port=item_port, value=item)
            for item in value
        ]
    if coerce_runtime_handle_ref(value) is not None or coerce_runtime_artifact_ref(value) is not None:
        return value

    data_type = _classify_generated_dpf_output(service, port=port, value=value)
    if data_type == DPF_FIELDS_CONTAINER_DATA_TYPE:
        return ctx.register_handle(
            value,
            data_type_id=data_type,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            metadata=service._build_fields_container_metadata(value),
        )
    if data_type == DPF_FIELD_DATA_TYPE:
        return ctx.register_handle(
            value,
            data_type_id=data_type,
            kind=DPF_FIELD_HANDLE_KIND,
            metadata=build_field_handle_metadata(value),
        )
    if data_type == DPF_MESH_DATA_TYPE:
        return ctx.register_handle(
            value,
            data_type_id=data_type,
            kind=DPF_MESH_HANDLE_KIND,
            metadata=service._build_mesh_metadata(value),
        )
    if data_type == DPF_MODEL_DATA_TYPE:
        return ctx.register_handle(
            value,
            data_type_id=data_type,
            kind=DPF_MODEL_HANDLE_KIND,
            metadata={},
        )
    if data_type == DPF_RESULT_FILE_DATA_TYPE:
        return ctx.register_handle(
            value,
            data_type_id=data_type,
            kind=DPF_RESULT_FILE_HANDLE_KIND,
            metadata={},
        )
    if data_type == DPF_SCOPING_DATA_TYPE:
        location = str(getattr(value, "location", "") or "").strip()
        metadata: dict[str, Any] = {"location": location}
        ids = getattr(value, "ids", None)
        if ids is not None:
            try:
                metadata.update(
                    compact_sequence_metadata(
                        "ids",
                        (int(item) for item in ids),
                    )
                )
            except TypeError:
                metadata["ids"] = []
        if location.casefold() == "timefreq":
            return ctx.register_handle(
                value,
                data_type_id=data_type,
                kind=DPF_TIME_SCOPING_HANDLE_KIND,
                metadata=metadata,
            )
        if location:
            return ctx.register_handle(
                value,
                data_type_id=data_type,
                kind=DPF_MESH_SCOPING_HANDLE_KIND,
                metadata=metadata,
            )
    if data_type.startswith("COREX.Ansys.DPF."):
        return ctx.register_handle(
            value,
            data_type_id=data_type,
            kind=DPF_OBJECT_HANDLE_KIND,
            metadata={},
        )
    return value


def _classify_generated_dpf_output(service, *, port: PortSpec, value: Any) -> str:  # noqa: ANN001
    candidates = tuple(
        dict.fromkeys(
            candidate
            for candidate in (
                str(port.data_type or "").strip(),
                *(str(item).strip() for item in port.accepted_data_types),
            )
            if candidate
        )
    )
    if not candidates:
        raise TypeError(f"Generated DPF output port {port.key!r} has no semantic type.")

    catalog = service._worker_services.data_types
    classified_type = normalize_dpf_live_type_name(type(value).__name__)
    matches: list[str] = []
    reasons: list[str] = []
    for candidate in candidates:
        try:
            spec = catalog.require(candidate)
        except DataTypeCatalogError as exc:
            reasons.append(f"{candidate}: {exc}")
            continue
        if spec.abstract:
            reasons.append(f"{candidate}: abstract type")
            continue
        if classified_type == candidate:
            matches.append(candidate)
            continue
        try:
            catalog.validate_output(candidate, value)
        except DataTypeCatalogError as exc:
            reasons.append(f"{candidate}: {exc}")
        else:
            matches.append(candidate)

    if len(matches) == 1:
        return matches[0]
    concrete_type = f"{type(value).__module__}.{type(value).__qualname__}"
    if not matches:
        raise TypeError(
            f"Generated DPF output port {port.key!r} returned unsupported "
            f"Python type {concrete_type}; live classifier {classified_type!r}; "
            f"declared candidates {candidates!r}; reasons: {'; '.join(reasons)}"
        )
    raise TypeError(
        f"Generated DPF output port {port.key!r} is ambiguous for Python type "
        f"{concrete_type}; live classifier {classified_type!r}; matching "
        f"candidates {tuple(matches)!r}."
    )


def _operator_stability(family: str) -> str:
    # Retained as source-spec metadata only; category routing no longer
    # consults stability (all operator mirrors live under Advanced).
    return "advanced" if family in _ADVANCED_OPERATOR_FAMILIES else "core"


def _load_foundational_operator_plugin_factories() -> tuple[Callable[[], NodePlugin], ...]:
    from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
        DpfFieldOpsNodePlugin,
        DpfResultFieldNodePlugin,
    )

    return (DpfResultFieldNodePlugin, DpfFieldOpsNodePlugin)


_FOUNDATIONAL_DESCRIPTOR_OVERRIDES = {
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "category_path": operator_family_category_path("result"),
        "source_path": "ansys.dpf.core.operators.result",
        "family_path": operator_family_path("result"),
        "stability": _operator_stability("result"),
    },
    DPF_FIELD_OPS_NODE_TYPE_ID: {
        "category_path": operator_family_category_path("math"),
        "source_path": "ansys.dpf.core.operators.math",
        "family_path": operator_family_path("math"),
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
    return _PROPERTY_TYPE_BY_DATA_TYPE.get(normalized)


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
    return tuple(ordered or (GRAPH_DATA_TYPE_ID,))


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
    ellipsis = bool(getattr(pin, "ellipsis", False))
    if getattr(pin, "optional", False) and not ellipsis:
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
        data_access="list" if ellipsis else "item",
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
        required=False,
        exposed=True,
        data_access="list" if bool(getattr(pin, "ellipsis", False)) else "item",
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
    if user_name and any(ch.isalnum() for ch in user_name) and not _USER_NAME_SYMBOL_RE.search(user_name):
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

    family_path = operator_family_path(discovered_family)
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
    seen_port_keys: set[str] = set()
    seen_property_keys: set[str] = set()
    ports: list[PortSpec] = []
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

    type_id = _stable_operator_type_id(definition.family, definition.module_name)
    if type_id in _SINGLE_RUN_OPERATOR_TYPE_IDS:
        ports = [
            replace(port, data_access="tree")
            if port.direction == "in" and port.kind == "data"
            else port
            for port in ports
        ]

    return NodeTypeSpec(
        type_id=type_id,
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


def _installed_dpf_version() -> str:
    try:
        return version("ansys-dpf-core")
    except PackageNotFoundError:
        return ""


def _warn_catalog_fallback(reason: str) -> None:
    global _CATALOG_FALLBACK_WARNED
    if _CATALOG_FALLBACK_WARNED:
        return
    warnings.warn(
        f"Ansys DPF operator catalog fallback: {reason}.",
        RuntimeWarning,
        stacklevel=2,
    )
    _CATALOG_FALLBACK_WARNED = True


def _pin_source_from_payload(payload: object) -> DpfPinSourceSpec | None:
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise TypeError("DPF pin source metadata must be an object")
    return DpfPinSourceSpec(
        pin_name=str(payload.get("pin_name", "")),
        pin_direction=str(payload.get("pin_direction", "")),  # type: ignore[arg-type]
        value_origin=str(payload.get("value_origin", "")),  # type: ignore[arg-type]
        value_key=str(payload.get("value_key", "")),
        data_type=str(payload.get("data_type", "")),
        presence=str(payload.get("presence", "optional")),  # type: ignore[arg-type]
        omission_semantics=str(payload.get("omission_semantics", "skip")),  # type: ignore[arg-type]
        exclusive_group=str(payload.get("exclusive_group", "")),
        variant_keys=tuple(str(item) for item in payload.get("variant_keys", ())),
        accepted_data_types=tuple(str(item) for item in payload.get("accepted_data_types", ())),
    )


def _operator_source_from_payload(payload: object) -> DpfOperatorSourceSpec:
    if not isinstance(payload, Mapping):
        raise TypeError("DPF operator source metadata must be an object")
    variants: list[DpfOperatorVariantSpec] = []
    for raw_variant in payload.get("variants", ()):
        if not isinstance(raw_variant, Mapping):
            raise TypeError("DPF operator variants must be objects")
        conditions = tuple(
            DpfOperatorSelectorCondition(
                property_key=str(condition.get("property_key", "")),
                values=tuple(str(item) for item in condition.get("values", ())),
            )
            for condition in raw_variant.get("selector_conditions", ())
            if isinstance(condition, Mapping)
        )
        variants.append(
            DpfOperatorVariantSpec(
                key=str(raw_variant.get("key", "")),
                operator_name=str(raw_variant.get("operator_name", "")),
                operator_name_template=str(raw_variant.get("operator_name_template", "")),
                selector_conditions=conditions,
            )
        )
    return DpfOperatorSourceSpec(
        backend=str(payload.get("backend", "ansys.dpf.core")),
        variants=tuple(variants),
        source_path=str(payload.get("source_path", "")),
        family_path=tuple(str(item) for item in payload.get("family_path", ())),
        stability=str(payload.get("stability", "")),  # type: ignore[arg-type]
    )


def _port_spec_from_payload(payload: Mapping[str, object]) -> PortSpec:
    key = str(payload["key"])
    direction = str(payload["direction"])
    kind = str(payload["kind"])
    is_data_input = direction == "in" and kind == "data"
    if is_data_input and "required" not in payload:
        raise ValueError(f"DPF operator input port {key!r} must declare required explicitly")
    required = payload.get("required")
    if is_data_input and not isinstance(required, bool):
        raise TypeError(f"DPF operator input port {key!r} required must be bool")
    if not is_data_input and required is not None and not isinstance(required, bool):
        raise TypeError(f"DPF operator port {key!r} required must be bool or None")
    source_metadata = _pin_source_from_payload(payload.get("source_metadata"))
    if is_data_input and source_metadata is not None:
        if (
            source_metadata.pin_direction != "input"
            or source_metadata.value_origin != "port"
            or source_metadata.value_key != key
        ):
            raise ValueError(f"DPF source metadata does not align with input port {key!r}")
        expected_required = source_metadata.presence == "required" and not source_metadata.variant_keys
        if required is not expected_required:
            raise ValueError(f"DPF required flag does not align with source metadata for port {key!r}")
    return PortSpec(
        key=key,
        direction=direction,  # type: ignore[arg-type]
        kind=kind,  # type: ignore[arg-type]
        data_type=str(payload["data_type"]),
        label=str(payload.get("label", "")),
        required=required,
        exposed=bool(payload.get("exposed", True)),
        allow_multiple_connections=bool(payload.get("allow_multiple_connections", False)),
        side=str(payload.get("side", "")),  # type: ignore[arg-type]
        source_metadata=source_metadata,
        accepted_data_types=tuple(str(item) for item in payload.get("accepted_data_types", ())),
        display_tier=str(payload.get("display_tier", "")),  # type: ignore[arg-type]
        data_access=str(payload.get("data_access", "item")),  # type: ignore[arg-type]
    )


def _spec_from_payload(payload: object) -> NodeTypeSpec:
    if not isinstance(payload, Mapping):
        raise TypeError("DPF operator descriptor must be an object")
    ports = tuple(
        _port_spec_from_payload(port)
        for port in payload.get("ports", ())
        if isinstance(port, Mapping)
    )
    properties = tuple(
        PropertySpec(
            key=str(prop["key"]),
            type=str(prop["type"]),  # type: ignore[arg-type]
            default=prop.get("default"),
            label=str(prop.get("label", "")),
            expose_port_toggle=bool(prop.get("expose_port_toggle", False)),
            enum_values=tuple(str(item) for item in prop.get("enum_values", ())),
            inline_editor=str(prop.get("inline_editor", "")),  # type: ignore[arg-type]
            inspector_editor=str(prop.get("inspector_editor", "")),  # type: ignore[arg-type]
            inspector_visible=bool(prop.get("inspector_visible", True)),
            source_metadata=_pin_source_from_payload(prop.get("source_metadata")),
            group=str(prop.get("group", "")),
            file_filter=str(prop.get("file_filter", "")),
        )
        for prop in payload.get("properties", ())
        if isinstance(prop, Mapping)
    )
    settings_groups = tuple(
        SettingsGroupSpec(
            group_id=str(group.get("group_id", "")),
            label=str(group.get("label", "")),
            items=tuple(
                SettingsGroupItemSpec(
                    port_key=str(item.get("port_key", "")),
                    property_key=str(item.get("property_key", "")),
                )
                for item in group.get("items", ())
                if isinstance(item, Mapping)
            ),
        )
        for group in payload.get("settings_groups", ())
        if isinstance(group, Mapping)
    )
    source_metadata = _operator_source_from_payload(payload.get("source_metadata"))
    return NodeTypeSpec(
        type_id=str(payload["type_id"]),
        display_name=str(payload["display_name"]),
        category_path=tuple(str(item) for item in payload.get("category_path", ())),
        icon=str(payload.get("icon", "")),
        ports=ports,
        properties=properties,
        collapsible=bool(payload.get("collapsible", True)),
        description=str(payload.get("description", "")),
        is_async=bool(payload.get("is_async", False)),
        runtime_behavior=str(payload.get("runtime_behavior", "active")),  # type: ignore[arg-type]
        surface_family=str(payload.get("surface_family", "standard")),  # type: ignore[arg-type]
        surface_variant=str(payload.get("surface_variant", "")),
        render_quality=NodeRenderQualitySpec.from_value(payload.get("render_quality")),
        source_metadata=source_metadata,
        show_title_icon=bool(payload.get("show_title_icon", False)),
        settings_groups=settings_groups,
    )


def _descriptors_from_catalog_document(document: object) -> tuple[PluginDescriptor, ...]:
    if not isinstance(document, Mapping):
        raise TypeError("operator catalog root must be an object")
    if document.get("schema_version") != OPERATOR_CATALOG_SCHEMA_VERSION:
        raise ValueError("unsupported operator catalog schema")
    raw_descriptors = document.get("descriptors")
    if not isinstance(raw_descriptors, list):
        raise TypeError("operator catalog descriptors must be a list")
    specs = tuple(_spec_from_payload(payload) for payload in raw_descriptors)
    type_ids = tuple(spec.type_id for spec in specs)
    if len(type_ids) != len(set(type_ids)) or any(
        not type_id.startswith(f"{_GENERATED_OPERATOR_TYPE_ID_PREFIX}.") for type_id in type_ids
    ):
        raise ValueError("operator catalog contains invalid generated type ids")
    return tuple(PluginDescriptor(spec=spec, factory=_generated_operator_factory(spec)) for spec in specs)


def build_ansys_dpf_operator_catalog_document() -> dict[str, object]:
    runtime_version = _installed_dpf_version()
    if not runtime_version:
        raise RuntimeError("ansys-dpf-core is required to generate the operator catalog")
    descriptors: list[dict[str, object]] = []
    for descriptor in _generated_operator_plugin_descriptors():
        payload = asdict(descriptor.spec)
        if not descriptor.spec.keywords:
            payload.pop("keywords")
        if not descriptor.spec.settings_groups:
            payload.pop("settings_groups")
        if not descriptor.spec.readiness_requirements:
            payload.pop("readiness_requirements")
        if not descriptor.spec.dynamic_port_groups:
            payload.pop("dynamic_port_groups")
        if descriptor.spec.instance_spec_resolver is None:
            payload.pop("instance_spec_resolver")
        for port in payload["ports"]:
            if port["direction"] != "in" and port["required"] is None:
                port["required"] = False
            if not port["description"]:
                port.pop("description")
        for prop in payload["properties"]:
            prop.pop("minimum")
            prop.pop("maximum")
            prop.pop("step")
            if not prop["description"]:
                prop.pop("description")
            if not prop["sensitive"]:
                prop.pop("sensitive")
            if not prop["sensitive_scope_key"]:
                prop.pop("sensitive_scope_key")
        payload["category"] = descriptor.spec.category
        descriptors.append(payload)
    return {
        "schema_version": OPERATOR_CATALOG_SCHEMA_VERSION,
        "ansys_dpf_core_version": runtime_version,
        "descriptors": descriptors,
    }


def render_ansys_dpf_operator_catalog() -> str:
    document = build_ansys_dpf_operator_catalog_document()
    descriptor_lines = [
        "    " + json.dumps(descriptor, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        for descriptor in document["descriptors"]
    ]
    descriptors = ",\n".join(descriptor_lines)
    return (
        "{\n"
        f'  "schema_version": {document["schema_version"]},\n'
        f'  "ansys_dpf_core_version": {json.dumps(document["ansys_dpf_core_version"])},\n'
        '  "descriptors": [\n'
        f"{descriptors}\n"
        "  ]\n"
        "}\n"
    )


def _packaged_generated_operator_descriptors(runtime_version: str) -> tuple[PluginDescriptor, ...] | None:
    try:
        document = json.loads(OPERATOR_CATALOG_PATH.read_text(encoding="utf-8"))
        if not isinstance(document, Mapping):
            raise TypeError("operator catalog root must be an object")
        catalog_version = str(document.get("ansys_dpf_core_version", ""))
        if catalog_version != runtime_version:
            _warn_catalog_fallback(
                f"catalog version {catalog_version or 'unknown'} does not match runtime {runtime_version or 'unknown'}"
            )
            return None
        return _descriptors_from_catalog_document(document)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        _warn_catalog_fallback(str(exc))
        return None


@lru_cache(maxsize=1)
def load_ansys_dpf_operator_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    foundational = tuple(
        _build_foundational_operator_descriptor(factory)
        for factory in _load_foundational_operator_plugin_factories()
    )
    generated = _packaged_generated_operator_descriptors(_installed_dpf_version())
    if generated is None:
        try:
            generated = _generated_operator_plugin_descriptors()
        except Exception as exc:
            _warn_catalog_fallback(f"live discovery failed: {exc}")
            generated = ()
    return foundational + generated


__all__ = [
    "_discovered_generated_operator_definitions",
    "OPERATOR_CATALOG_PATH",
    "OPERATOR_CATALOG_SCHEMA_VERSION",
    "build_ansys_dpf_operator_catalog_document",
    "load_ansys_dpf_operator_plugin_descriptors",
    "render_ansys_dpf_operator_catalog",
]
