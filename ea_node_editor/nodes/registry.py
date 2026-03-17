from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from .types import NodePlugin, NodeTypeSpec, PortSpec, PropertySpec


@dataclass(slots=True)
class NodeRegistryEntry:
    spec: NodeTypeSpec
    factory: Callable[[], NodePlugin]


class NodeRegistry:
    _TYPE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
    _SUPPORTED_PROPERTY_TYPES = {"str", "int", "float", "bool", "path", "enum", "json"}
    _SUPPORTED_INSPECTOR_EDITORS = {"", "text", "textarea", "path", "toggle", "enum"}
    _SUPPORTED_DIRECTIONS = {"in", "out"}
    _SUPPORTED_KINDS = {"exec", "completed", "failed", "data", "flow"}
    _SUPPORTED_RUNTIME_BEHAVIORS = {"active", "passive", "compile_only"}
    _SUPPORTED_SURFACE_FAMILIES = {
        "standard",
        "flowchart",
        "planning",
        "annotation",
        "media",
    }

    def __init__(self) -> None:
        self._entries: dict[str, NodeRegistryEntry] = {}

    def register(self, factory: Callable[[], NodePlugin]) -> None:
        plugin = factory()
        spec = plugin.spec()
        self._validate_spec(spec)
        if spec.type_id in self._entries:
            raise ValueError(f"Node type already registered: {spec.type_id}")
        self._entries[spec.type_id] = NodeRegistryEntry(spec=spec, factory=factory)

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

    def all_specs(self) -> list[NodeTypeSpec]:
        return [entry.spec for entry in self._entries.values()]

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
    ) -> list[NodeTypeSpec]:
        text = query.strip().lower()
        normalized_category = category.strip().lower()
        normalized_type = data_type.strip().lower()
        normalized_direction = direction.strip().lower()
        output: list[NodeTypeSpec] = []
        for spec in self.all_specs():
            if normalized_category and spec.category.lower() != normalized_category:
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
                spec.category.lower(),
                spec.display_name.lower(),
                spec.type_id.lower(),
            )
        )
        return output

    def categories(self) -> list[str]:
        categories = sorted({spec.category for spec in self.all_specs()})
        return categories

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
            if data_type and port.data_type.lower() != data_type:
                continue
            return True
        return False

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
        if not spec.category.strip():
            raise ValueError(f"Node {spec.type_id} category must be non-empty")
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
            self._validate_port(spec.type_id, port)
            if port.key in port_keys:
                raise ValueError(f"Node {spec.type_id} has duplicate port key: {port.key}")
            port_keys.add(port.key)

        property_keys: set[str] = set()
        for prop in spec.properties:
            self._validate_property(spec.type_id, prop)
            if prop.key in property_keys:
                raise ValueError(f"Node {spec.type_id} has duplicate property key: {prop.key}")
            property_keys.add(prop.key)

    def _validate_port(self, type_id: str, port: PortSpec) -> None:
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
        if not isinstance(port.required, bool):
            raise TypeError(f"Node {type_id} port {port.key} required must be bool")
        if not isinstance(port.exposed, bool):
            raise TypeError(f"Node {type_id} port {port.key} exposed must be bool")
        if not isinstance(port.allow_multiple_connections, bool):
            raise TypeError(
                f"Node {type_id} port {port.key} allow_multiple_connections must be bool"
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
