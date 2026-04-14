from __future__ import annotations

import copy
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable

from .category_paths import (
    CategoryPath,
    category_display,
    category_path_ancestors,
    category_path_matches_prefix,
    normalize_category_path,
)
from .node_specs import (
    DpfCallableSourceSpec,
    DpfOperatorSourceSpec,
    DpfPinSourceSpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from .plugin_contracts import NodePlugin, PluginDescriptor, PluginProvenance


@dataclass(slots=True)
class NodeRegistryEntry:
    spec: NodeTypeSpec
    factory: Callable[[], NodePlugin]
    provenance: PluginProvenance | None = None

    def descriptor(self) -> PluginDescriptor:
        return PluginDescriptor(
            spec=self.spec,
            factory=self.factory,
            provenance=self.provenance,
        )


class NodeRegistry:
    _TYPE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
    _SUPPORTED_PROPERTY_TYPES = {"str", "int", "float", "bool", "path", "enum", "json"}
    _SUPPORTED_INLINE_EDITORS = {"", "text", "number", "toggle", "enum", "path", "textarea", "color"}
    _SUPPORTED_INSPECTOR_EDITORS = {"", "text", "textarea", "path", "toggle", "enum", "color"}
    _SUPPORTED_DIRECTIONS = {"in", "out", "neutral"}
    _SUPPORTED_PORT_SIDES = {"", "top", "right", "bottom", "left"}
    _SUPPORTED_KINDS = {"exec", "completed", "failed", "data", "flow"}
    _SUPPORTED_RUNTIME_BEHAVIORS = {"active", "passive", "compile_only"}
    _SUPPORTED_SURFACE_FAMILIES = {
        "standard",
        "flowchart",
        "planning",
        "annotation",
        "comment_backdrop",
        "media",
        "viewer",
    }

    def __init__(self) -> None:
        self._entries: dict[str, NodeRegistryEntry] = {}

    def register(
        self,
        factory: Callable[[], NodePlugin],
        *,
        provenance: PluginProvenance | None = None,
    ) -> None:
        plugin = factory()
        spec = plugin.spec()
        self.register_descriptor(spec, factory, provenance=provenance)

    def register_descriptor(
        self,
        spec: NodeTypeSpec | PluginDescriptor,
        factory: Callable[[], NodePlugin] | None = None,
        *,
        provenance: PluginProvenance | None = None,
    ) -> None:
        if isinstance(spec, PluginDescriptor):
            descriptor = spec
            spec = descriptor.spec
            factory = descriptor.factory
            if provenance is None:
                provenance = descriptor.provenance
        if factory is None or not callable(factory):
            raise TypeError("Plugin factory must be callable")
        self._validate_spec(spec)
        if spec.type_id in self._entries:
            raise ValueError(f"Node type already registered: {spec.type_id}")
        self._entries[spec.type_id] = NodeRegistryEntry(
            spec=spec,
            factory=factory,
            provenance=provenance,
        )

    def create(self, type_id: str) -> NodePlugin:
        try:
            entry = self._entries[type_id]
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc
        return entry.factory()

    def get_spec(self, type_id: str) -> NodeTypeSpec:
        try:
            return self._entries[type_id].spec
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc

    def spec_or_none(self, type_id: str) -> NodeTypeSpec | None:
        entry = self._entries.get(type_id)
        if entry is None:
            return None
        return entry.spec

    def get_descriptor(self, type_id: str) -> PluginDescriptor:
        try:
            return self._entries[type_id].descriptor()
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc

    def descriptor_or_none(self, type_id: str) -> PluginDescriptor | None:
        entry = self._entries.get(type_id)
        if entry is None:
            return None
        return entry.descriptor()

    def all_specs(self) -> list[NodeTypeSpec]:
        return [entry.spec for entry in self._entries.values()]

    def all_descriptors(self) -> list[PluginDescriptor]:
        return [entry.descriptor() for entry in self._entries.values()]

    def default_properties(self, type_id: str) -> dict[str, Any]:
        spec = self.get_spec(type_id)
        return {
            prop.key: copy.deepcopy(self._coerce_property_value(prop, prop.default, strict=True))
            for prop in spec.properties
        }

    def normalize_property_value(self, type_id: str, key: str, value: Any) -> Any:
        prop_spec = self._property_spec(type_id, key)
        return self._coerce_property_value(prop_spec, value, strict=False)

    def normalize_properties(
        self,
        type_id: str,
        values: dict[str, Any] | None,
        *,
        include_defaults: bool = True,
    ) -> dict[str, Any]:
        provided = dict(values or {})
        spec = self.get_spec(type_id)
        normalized: dict[str, Any] = {}
        for prop in spec.properties:
            if prop.key in provided:
                normalized[prop.key] = self._coerce_property_value(prop, provided[prop.key], strict=False)
                continue
            if include_defaults:
                normalized[prop.key] = self._coerce_property_value(prop, prop.default, strict=False)
        return normalized

    def filter_nodes(
        self,
        query: str = "",
        category: str = "",
        data_type: str = "",
        direction: str = "",
        *,
        category_path: Sequence[str] | None = None,
    ) -> list[NodeTypeSpec]:
        text = query.strip().lower()
        category_prefix = self._category_filter_prefix(
            category_path=category_path,
            category=category,
        )
        normalized_type = data_type.strip().lower()
        normalized_direction = direction.strip().lower()
        output: list[NodeTypeSpec] = []
        for spec in self.all_specs():
            if category_prefix is not None and not category_path_matches_prefix(
                spec.category_path,
                category_prefix,
            ):
                continue
            if text and not self._matches_text(spec, text):
                continue
            if (normalized_type or normalized_direction) and not self._matches_port_filters(
                spec,
                data_type=normalized_type,
                direction=normalized_direction,
            ):
                continue
            output.append(spec)
        output.sort(
            key=lambda spec: (
                tuple(segment.lower() for segment in spec.category_path),
                spec.display_name.lower(),
                spec.type_id.lower(),
            )
        )
        return output

    def category_paths(self) -> list[CategoryPath]:
        paths: set[CategoryPath] = set()
        for spec in self.all_specs():
            paths.update(category_path_ancestors(spec.category_path))
        return sorted(paths, key=self._category_path_sort_key)

    def categories(self) -> list[str]:
        leaf_paths = {spec.category_path for spec in self.all_specs()}
        return [category_display(path) for path in sorted(leaf_paths, key=self._category_path_sort_key)]

    def _category_filter_prefix(
        self,
        *,
        category_path: Sequence[str] | None,
        category: str,
    ) -> CategoryPath | None:
        if category_path is not None:
            return normalize_category_path(category_path)

        normalized_category = str(category).strip()
        if not normalized_category:
            return None
        return self._category_path_for_compat_category(normalized_category)

    def _category_path_for_compat_category(self, category: str) -> CategoryPath:
        normalized_category = category.casefold()
        for path in self.category_paths():
            if category_display(path).casefold() == normalized_category:
                return path
        return normalize_category_path((category,))

    @staticmethod
    def _category_path_sort_key(path: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        normalized_path = normalize_category_path(path)
        return tuple(segment.casefold() for segment in normalized_path), normalized_path

    @staticmethod
    def _matches_text(spec: NodeTypeSpec, query: str) -> bool:
        haystack = " ".join(
            [
                spec.type_id,
                spec.display_name,
                spec.category,
                spec.description,
                " ".join(port.key for port in spec.ports),
            ]
        ).lower()
        return query in haystack

    @staticmethod
    def _matches_port_filters(spec: NodeTypeSpec, data_type: str, direction: str) -> bool:
        for port in spec.ports:
            if direction and port.direction != direction:
                continue
            if data_type and not NodeRegistry._port_matches_data_type(port, data_type):
                continue
            return True
        return False

    @staticmethod
    def _port_matches_data_type(port: PortSpec, data_type: str) -> bool:
        accepted_types = port.accepted_data_types or (port.data_type,)
        return any(accepted_type.lower() == data_type for accepted_type in accepted_types)

    def _property_spec(self, type_id: str, key: str) -> PropertySpec:
        spec = self.get_spec(type_id)
        for prop in spec.properties:
            if prop.key == key:
                return prop
        raise KeyError(f"Unknown property {key} for node type {type_id}")

    def _validate_spec(self, spec: NodeTypeSpec) -> None:
        if not isinstance(spec, NodeTypeSpec):
            raise TypeError("Plugin spec() must return NodeTypeSpec")

        if not spec.type_id or spec.type_id.strip() != spec.type_id:
            raise ValueError("Node type_id must be a non-empty trimmed string")
        if not self._TYPE_ID_PATTERN.fullmatch(spec.type_id):
            raise ValueError(f"Node type_id has unsupported characters: {spec.type_id}")
        if not spec.display_name.strip():
            raise ValueError(f"Node {spec.type_id} display_name must be non-empty")
        if not spec.category_path:
            raise ValueError(f"Node {spec.type_id} category_path must be non-empty")
        if spec.runtime_behavior not in self._SUPPORTED_RUNTIME_BEHAVIORS:
            raise ValueError(
                f"Node {spec.type_id} runtime_behavior has invalid value: {spec.runtime_behavior}"
            )
        if (
            not isinstance(spec.surface_family, str)
            or not spec.surface_family
            or spec.surface_family.strip() != spec.surface_family
        ):
            raise ValueError(f"Node {spec.type_id} surface_family must be a non-empty trimmed string")
        if spec.surface_family not in self._SUPPORTED_SURFACE_FAMILIES:
            raise ValueError(f"Node {spec.type_id} surface_family has invalid value: {spec.surface_family}")
        if not isinstance(spec.surface_variant, str) or spec.surface_variant.strip() != spec.surface_variant:
            raise ValueError(f"Node {spec.type_id} surface_variant must be a trimmed string")
        if not isinstance(spec.ports, tuple):
            raise TypeError(f"Node {spec.type_id} ports must be a tuple[PortSpec, ...]")
        if not isinstance(spec.properties, tuple):
            raise TypeError(f"Node {spec.type_id} properties must be a tuple[PropertySpec, ...]")

        port_keys: set[str] = set()
        for port in spec.ports:
            self._validate_port(spec, port)
            if port.key in port_keys:
                raise ValueError(f"Node {spec.type_id} has duplicate port key: {port.key}")
            port_keys.add(port.key)

        property_keys: set[str] = set()
        for prop in spec.properties:
            self._validate_property(spec.type_id, prop)
            if prop.key in property_keys:
                raise ValueError(f"Node {spec.type_id} has duplicate property key: {prop.key}")
            property_keys.add(prop.key)
        self._validate_source_metadata(spec)

    def _validate_port(self, spec: NodeTypeSpec, port: PortSpec) -> None:
        type_id = spec.type_id
        if not isinstance(port, PortSpec):
            raise TypeError(f"Node {type_id} ports must be PortSpec instances")
        if not port.key or port.key.strip() != port.key:
            raise ValueError(f"Node {type_id} has invalid port key: {port.key!r}")
        if port.direction not in self._SUPPORTED_DIRECTIONS:
            raise ValueError(f"Node {type_id} port {port.key} has invalid direction: {port.direction}")
        if port.kind not in self._SUPPORTED_KINDS:
            raise ValueError(f"Node {type_id} port {port.key} has invalid kind: {port.kind}")
        if not port.data_type or port.data_type.strip() != port.data_type:
            raise ValueError(f"Node {type_id} port {port.key} has invalid data_type: {port.data_type!r}")
        for accepted_type in port.accepted_data_types:
            if not accepted_type or accepted_type.strip() != accepted_type:
                raise ValueError(
                    f"Node {type_id} port {port.key} has invalid accepted_data_type: {accepted_type!r}"
                )
        if not isinstance(port.side, str) or port.side.strip() != port.side:
            raise ValueError(f"Node {type_id} port {port.key} side must be a trimmed string")
        if port.side not in self._SUPPORTED_PORT_SIDES:
            raise ValueError(f"Node {type_id} port {port.key} has invalid side: {port.side}")
        if not isinstance(port.required, bool):
            raise TypeError(f"Node {type_id} port {port.key} required must be bool")
        if not isinstance(port.exposed, bool):
            raise TypeError(f"Node {type_id} port {port.key} exposed must be bool")
        if not isinstance(port.allow_multiple_connections, bool):
            raise TypeError(
                f"Node {type_id} port {port.key} allow_multiple_connections must be bool"
            )
        if port.direction == "neutral":
            if spec.runtime_behavior != "passive":
                raise ValueError(
                    f"Node {type_id} port {port.key} neutral direction is only supported on passive nodes"
                )
            if port.kind != "flow" or port.data_type != "flow":
                raise ValueError(
                    f"Node {type_id} port {port.key} neutral direction requires flow kind and data_type"
                )
            if not port.side:
                raise ValueError(f"Node {type_id} port {port.key} neutral direction requires a cardinal side")
            if port.key != port.side:
                raise ValueError(
                    f"Node {type_id} port {port.key} neutral direction side must match the stored port key"
                )
            if not port.allow_multiple_connections:
                raise ValueError(
                    f"Node {type_id} port {port.key} neutral passive flow ports must allow multiple connections"
                )
        elif port.side:
            raise ValueError(
                f"Node {type_id} port {port.key} side metadata is only supported on neutral passive flow ports"
            )

    def _validate_property(self, type_id: str, prop: PropertySpec) -> None:
        if not isinstance(prop, PropertySpec):
            raise TypeError(f"Node {type_id} properties must be PropertySpec instances")
        if not prop.key or prop.key.strip() != prop.key:
            raise ValueError(f"Node {type_id} has invalid property key: {prop.key!r}")
        if prop.type not in self._SUPPORTED_PROPERTY_TYPES:
            raise ValueError(f"Node {type_id} property {prop.key} has invalid type: {prop.type}")
        if not prop.label.strip():
            raise ValueError(f"Node {type_id} property {prop.key} label must be non-empty")
        if not isinstance(prop.expose_port_toggle, bool):
            raise TypeError(f"Node {type_id} property {prop.key} expose_port_toggle must be bool")
        inline_editor = str(prop.inline_editor).strip()
        if inline_editor != prop.inline_editor:
            raise ValueError(f"Node {type_id} property {prop.key} inline_editor must be trimmed")
        if inline_editor not in self._SUPPORTED_INLINE_EDITORS:
            raise ValueError(
                f"Node {type_id} property {prop.key} inline_editor has invalid value: {inline_editor}"
            )
        inspector_editor = str(prop.inspector_editor).strip()
        if inspector_editor != prop.inspector_editor:
            raise ValueError(f"Node {type_id} property {prop.key} inspector_editor must be trimmed")
        if inspector_editor not in self._SUPPORTED_INSPECTOR_EDITORS:
            raise ValueError(
                f"Node {type_id} property {prop.key} inspector_editor has invalid value: {inspector_editor}"
            )
        if not isinstance(prop.inspector_visible, bool):
            raise TypeError(f"Node {type_id} property {prop.key} inspector_visible must be bool")
        enum_values = tuple(prop.enum_values)
        if prop.type == "enum":
            if not enum_values:
                raise ValueError(f"Node {type_id} enum property {prop.key} must define enum_values")
            if len(set(enum_values)) != len(enum_values):
                raise ValueError(f"Node {type_id} enum property {prop.key} enum_values must be unique")
        elif enum_values:
            raise ValueError(f"Node {type_id} non-enum property {prop.key} cannot define enum_values")
        self._coerce_property_value(prop, prop.default, strict=True)

    def _validate_source_metadata(self, spec: NodeTypeSpec) -> None:
        node_source = spec.source_metadata
        if node_source is not None and not isinstance(
            node_source,
            (DpfOperatorSourceSpec, DpfCallableSourceSpec),
        ):
            raise TypeError(
                f"Node {spec.type_id} source_metadata must be a DpfOperatorSourceSpec or DpfCallableSourceSpec"
            )

        variant_keys = (
            set(node_source.variant_keys)
            if isinstance(node_source, DpfOperatorSourceSpec)
            else set()
        )

        for port in spec.ports:
            source = port.source_metadata
            if source is None:
                continue
            self._validate_port_source_metadata(
                spec,
                port,
                source,
                node_source=node_source,
                variant_keys=variant_keys,
            )

        for prop in spec.properties:
            source = prop.source_metadata
            if source is None:
                continue
            self._validate_property_source_metadata(
                spec,
                prop,
                source,
                node_source=node_source,
                variant_keys=variant_keys,
            )

    def _validate_port_source_metadata(
        self,
        spec: NodeTypeSpec,
        port: PortSpec,
        source: DpfPinSourceSpec,
        *,
        node_source: DpfOperatorSourceSpec | DpfCallableSourceSpec | None,
        variant_keys: set[str],
    ) -> None:
        if not isinstance(source, DpfPinSourceSpec):
            raise TypeError(f"Node {spec.type_id} port {port.key} source_metadata must be DpfPinSourceSpec")
        if node_source is None:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} source_metadata requires node source_metadata"
            )
        if source.value_origin != "port":
            raise ValueError(
                f"Node {spec.type_id} port {port.key} source_metadata must use a port value_origin"
            )
        if source.value_key != port.key:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} source_metadata value_key must match the port key"
            )
        if source.data_type != port.data_type:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} source_metadata data_type must match the port data_type"
            )
        if source.accepted_data_types != port.accepted_data_types:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} source_metadata accepted_data_types must match the port accepted_data_types"
            )
        if port.direction == "neutral":
            raise ValueError(
                f"Node {spec.type_id} port {port.key} neutral ports cannot publish DPF source metadata"
            )
        expected_pin_direction = "input" if port.direction == "in" else "output"
        if source.pin_direction != expected_pin_direction:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} source_metadata pin_direction must match the port direction"
            )
        if isinstance(node_source, DpfOperatorSourceSpec):
            if source.callable_binding is not None:
                raise ValueError(
                    f"Node {spec.type_id} port {port.key} operator metadata cannot declare callable_binding"
                )
            unknown_variant_keys = set(source.variant_keys) - variant_keys
            if unknown_variant_keys:
                unknown_values = ", ".join(sorted(unknown_variant_keys))
                raise ValueError(
                    f"Node {spec.type_id} port {port.key} references unknown DPF source variants: {unknown_values}"
                )
            return

        if source.variant_keys:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} callable source_metadata cannot declare variant_keys"
            )
        if source.callable_binding is None:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} callable source_metadata requires callable_binding"
            )
        binding_kind = source.callable_binding.binding_kind
        if expected_pin_direction == "output":
            if binding_kind != "return_value":
                raise ValueError(
                    f"Node {spec.type_id} port {port.key} callable output bindings must use return_value"
                )
            return
        if binding_kind not in {"parameter", "receiver"}:
            raise ValueError(
                f"Node {spec.type_id} port {port.key} callable input bindings must use parameter or receiver"
            )

    def _validate_property_source_metadata(
        self,
        spec: NodeTypeSpec,
        prop: PropertySpec,
        source: DpfPinSourceSpec,
        *,
        node_source: DpfOperatorSourceSpec | DpfCallableSourceSpec | None,
        variant_keys: set[str],
    ) -> None:
        if not isinstance(source, DpfPinSourceSpec):
            raise TypeError(
                f"Node {spec.type_id} property {prop.key} source_metadata must be DpfPinSourceSpec"
            )
        if node_source is None:
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} source_metadata requires node source_metadata"
            )
        if source.value_origin != "property":
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} source_metadata must use a property value_origin"
            )
        if source.value_key != prop.key:
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} source_metadata value_key must match the property key"
            )
        if source.pin_direction != "input":
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} source_metadata pin_direction must be input"
            )
        if source.accepted_data_types:
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} source_metadata cannot declare accepted_data_types"
            )
        if isinstance(node_source, DpfOperatorSourceSpec):
            if source.callable_binding is not None:
                raise ValueError(
                    f"Node {spec.type_id} property {prop.key} operator metadata cannot declare callable_binding"
                )
            unknown_variant_keys = set(source.variant_keys) - variant_keys
            if unknown_variant_keys:
                unknown_values = ", ".join(sorted(unknown_variant_keys))
                raise ValueError(
                    f"Node {spec.type_id} property {prop.key} references unknown DPF source variants: {unknown_values}"
                )
            return

        if source.variant_keys:
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} callable source_metadata cannot declare variant_keys"
            )
        if source.callable_binding is None:
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} callable source_metadata requires callable_binding"
            )
        if source.callable_binding.binding_kind != "parameter":
            raise ValueError(
                f"Node {spec.type_id} property {prop.key} callable property bindings must use parameter"
            )

    @staticmethod
    def _coerce_property_value(prop: PropertySpec, value: Any, strict: bool) -> Any:
        default = copy.deepcopy(prop.default)
        if value is None:
            if strict:
                raise ValueError(f"Property {prop.key} default cannot be None")
            return default

        try:
            if prop.type in {"str", "path"}:
                return str(value)
            if prop.type == "int":
                if isinstance(value, bool):
                    raise ValueError("bool is not a valid int default")
                return int(value)
            if prop.type == "float":
                if isinstance(value, bool):
                    raise ValueError("bool is not a valid float default")
                return float(value)
            if prop.type == "bool":
                if not isinstance(value, bool):
                    raise ValueError("bool property requires bool value")
                return value
            if prop.type == "enum":
                normalized = str(value)
                if normalized not in set(prop.enum_values):
                    raise ValueError(
                        f"enum property value must be one of {tuple(prop.enum_values)}"
                    )
                return normalized
            # json type
            json.dumps(value)
            return copy.deepcopy(value)
        except Exception as exc:  # noqa: BLE001
            if strict:
                raise ValueError(
                    f"Invalid default for property {prop.key} ({prop.type}): {value!r}"
                ) from exc
            return default


def default_port(spec: NodeTypeSpec, key: str) -> PortSpec:
    for port in spec.ports:
        if port.key == key:
            return port
    raise KeyError(f"Port {key} not found in {spec.type_id}")
