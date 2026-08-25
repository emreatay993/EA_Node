# Purpose: Validate and compose node descriptors with their semantic data-type catalog.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_registry_validation.py
# Landmarks: resolve_instance_ports; TrustedFactoryEntry; PythonFunctionEntry; NodeRegistry; descriptor validation

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any, Callable

from ea_node_editor.runtime_contracts import (
    DataTypeCatalog,
    DataTypeCatalogError,
    INTERVAL_1D_DATA_TYPE,
    RuntimeArtifactRef,
    TypedInlineValue,
    ImageValue,
    coerce_interval_1d,
    deserialize_runtime_value,
)

from .category_paths import (
    CategoryPath,
    category_display,
    category_path_ancestors,
    category_path_matches_prefix,
    normalize_category_path,
)
from .core_data_types import (
    CORE_DATA_CONVERSIONS,
    CORE_DATA_TYPE_FAMILIES,
    CORE_DATA_TYPE_OWNER_ID,
    CORE_DATA_TYPE_OWNER_VERSION,
    CORE_DATA_TYPES,
)
from .function_plugin import PluginBundleRef, PythonFunctionRef
from .node_specs import (
    DpfCallableSourceSpec,
    DpfOperatorSourceSpec,
    DpfPinSourceSpec,
    DynamicPortGroupSpec,
    NodeTypeSpec,
    PortSpec,
    PropertyConditionSpec,
    PropertySpec,
    ReadinessRequirementSpec,
    SettingsGroupItemSpec,
    SettingsGroupSpec,
    property_inspector_editor,
)
from .plugin_contracts import (
    NodePlugin,
    PluginContractManifest,
    PluginDescriptor,
    PluginProvenance,
)

_SUPPORTED_DIRECTIONS = {"in", "out", "neutral"}
_SUPPORTED_PORT_SIDES = {"", "top", "right", "bottom", "left"}
_SUPPORTED_KINDS = {"data", "flow"}
_SUPPORTED_DATA_ACCESS = {"item", "list", "tree"}
def _coerce_property_value(
    prop: PropertySpec,
    value: Any,
    *,
    strict: bool,
    data_types: DataTypeCatalog | None = None,
) -> Any:
    default = copy.deepcopy(prop.default)
    if value is None:
        if prop.nullable:
            return None
        if strict:
            raise ValueError(f"Property {prop.key} default cannot be None")
        return _coerce_property_value(
            prop,
            default,
            strict=True,
            data_types=data_types,
        )

    try:
        if prop.persistence_data_type_id and isinstance(
            value,
            (TypedInlineValue, ImageValue, RuntimeArtifactRef),
        ):
            if data_types is None:
                raise ValueError(
                    "persistence-aware property requires a data-type catalog"
                )
            data_types.validate_carrier(prop.persistence_data_type_id, value)
            actual_spec = data_types.require(value.data_type_id)
            expected_persistence = (
                "inline" if isinstance(value, (TypedInlineValue, ImageValue)) else "saved_artifact"
            )
            if actual_spec.persistence != expected_persistence:
                raise ValueError(
                    f"data type {value.data_type_id!r} does not permit "
                    f"{expected_persistence} persistence"
                )
            if isinstance(value, RuntimeArtifactRef):
                if value.scope == "managed":
                    return value.ref
                return value
            return copy.deepcopy(value)
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
        if prop.type == INTERVAL_1D_DATA_TYPE:
            try:
                return coerce_interval_1d(value)
            except TypeError:
                return coerce_interval_1d(deserialize_runtime_value(value))
        json.dumps(value)
        return copy.deepcopy(value)
    except Exception as exc:  # noqa: BLE001
        if strict:
            raise ValueError(
                f"Invalid default for property {prop.key} ({prop.type}): {value!r}"
            ) from exc
        return _coerce_property_value(
            prop,
            default,
            strict=True,
            data_types=data_types,
        )


def _validate_port(
    spec: NodeTypeSpec,
    port: PortSpec,
    *,
    data_types: DataTypeCatalog | None = None,
) -> None:
    type_id = spec.type_id
    if not isinstance(port, PortSpec):
        raise TypeError(f"Node {type_id} ports must be PortSpec instances")
    if not isinstance(port.key, str) or not port.key or port.key.strip() != port.key:
        raise ValueError(f"Node {type_id} has invalid port key: {port.key!r}")
    if port.direction not in _SUPPORTED_DIRECTIONS:
        raise ValueError(
            f"Node {type_id} port {port.key} has invalid direction: {port.direction}"
        )
    if port.kind not in _SUPPORTED_KINDS:
        raise ValueError(
            f"Node {type_id} port {port.key} has invalid kind: {port.kind}"
        )
    if port.data_access not in _SUPPORTED_DATA_ACCESS:
        raise ValueError(
            f"Node {type_id} port {port.key} has invalid data_access: {port.data_access}"
        )
    if (
        not isinstance(port.data_type, str)
        or not port.data_type
        or port.data_type.strip() != port.data_type
    ):
        raise ValueError(
            f"Node {type_id} port {port.key} has invalid data_type: {port.data_type!r}"
        )
    for accepted_type in port.accepted_data_types:
        if not accepted_type or accepted_type.strip() != accepted_type:
            raise ValueError(
                f"Node {type_id} port {port.key} has invalid accepted_data_type: {accepted_type!r}"
            )
    if port.kind == "data" and data_types is not None:
        try:
            data_types.require(port.data_type)
            for accepted_type in port.accepted_data_types:
                data_types.require(accepted_type)
        except DataTypeCatalogError as exc:
            raise ValueError(f"Node {type_id} port {port.key} declares {exc}") from exc
    elif port.kind != "data" and port.accepted_data_types:
        raise ValueError(
            f"Node {type_id} flow port {port.key} cannot declare accepted_data_types"
        )
    if not isinstance(port.side, str) or port.side.strip() != port.side:
        raise ValueError(
            f"Node {type_id} port {port.key} side must be a trimmed string"
        )
    if port.side not in _SUPPORTED_PORT_SIDES:
        raise ValueError(
            f"Node {type_id} port {port.key} has invalid side: {port.side}"
        )
    if port.required is not None and not isinstance(port.required, bool):
        raise TypeError(f"Node {type_id} port {port.key} required must be bool or None")
    active_data_input = (
        spec.runtime_behavior == "active"
        and port.direction == "in"
        and port.kind == "data"
    )
    if active_data_input and port.required is None:
        raise ValueError(
            f"Node {type_id} active data input {port.key} must explicitly declare required=True or False"
        )
    if port.required is True and not active_data_input:
        raise ValueError(
            f"Node {type_id} port {port.key} required=True is only valid on active data inputs"
        )
    if not isinstance(port.uses_property_default, bool):
        raise TypeError(
            f"Node {type_id} port {port.key} uses_property_default must be bool"
        )
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
            raise ValueError(
                f"Node {type_id} port {port.key} neutral direction requires a cardinal side"
            )
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


def _resolve_dynamic_port_groups(
    spec: NodeTypeSpec,
    properties: Mapping[str, object],
    *,
    data_types: DataTypeCatalog | None = None,
) -> tuple[tuple[PortSpec, ...], ...]:
    if not spec.dynamic_port_groups:
        return ()
    resolved_properties = {
        prop.key: _coerce_property_value(
            prop,
            properties[prop.key] if prop.key in properties else prop.default,
            strict=prop.key not in properties,
            data_types=data_types,
        )
        for prop in spec.properties
    }
    seen_keys = {port.key for port in spec.ports}
    resolved_groups: list[tuple[PortSpec, ...]] = []
    for group in spec.dynamic_port_groups:
        try:
            ports = group.ports_resolver(dict(resolved_properties))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"Node {spec.type_id} dynamic port group {group.group_id} resolver failed"
            ) from exc
        if not isinstance(ports, tuple):
            raise ValueError(
                f"Node {spec.type_id} dynamic port group {group.group_id} resolver must return tuple[PortSpec, ...]"
            )
        if len(ports) < group.minimum:
            raise ValueError(
                f"Node {spec.type_id} dynamic port group {group.group_id} requires at least {group.minimum} ports"
            )
        if group.maximum is not None and len(ports) > group.maximum:
            raise ValueError(
                f"Node {spec.type_id} dynamic port group {group.group_id} allows at most {group.maximum} ports"
            )
        for port in ports:
            if not isinstance(port, PortSpec):
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} must resolve PortSpec instances"
                )
            _validate_port(spec, port, data_types=data_types)
            if port.direction != group.direction:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} port {port.key} direction must be {group.direction}"
                )
            if port.kind != "data":
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} port {port.key} must be a data port"
                )
            if port.uses_property_default:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} port {port.key} cannot use a property default"
                )
            if not port.key or port.key.strip() != port.key:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} has invalid port key: {port.key!r}"
                )
            if port.key in seen_keys:
                raise ValueError(
                    f"Node {spec.type_id} has duplicate port key: {port.key}"
                )
            seen_keys.add(port.key)
        resolved_groups.append(ports)
        resolved_properties[group.property_key] = [port.key for port in ports]
    return tuple(resolved_groups)


def resolve_instance_ports(
    spec: NodeTypeSpec,
    properties: Mapping[str, object],
    *,
    data_types: DataTypeCatalog | None = None,
) -> tuple[PortSpec, ...]:
    spec = resolve_instance_spec(spec, properties)
    dynamic_ports = tuple(
        port
        for group_ports in _resolve_dynamic_port_groups(
            spec,
            properties,
            data_types=data_types,
        )
        for port in group_ports
    )
    return spec.ports + dynamic_ports


def resolve_instance_spec(
    spec: NodeTypeSpec,
    properties: Mapping[str, object],
) -> NodeTypeSpec:
    resolver = spec.instance_spec_resolver
    if resolver is None:
        return spec
    resolved_properties = {
        prop.key: copy.deepcopy(prop.default)
        for prop in spec.properties
    }
    resolved_properties.update(dict(properties))
    resolved = resolver(spec, resolved_properties)
    if not isinstance(resolved, NodeTypeSpec):
        raise TypeError(
            f"Node {spec.type_id} instance_spec_resolver must return NodeTypeSpec"
        )
    if resolved.type_id != spec.type_id:
        raise ValueError(
            f"Node {spec.type_id} instance_spec_resolver changed the node type ID"
        )
    if resolved.instance_spec_resolver is not None:
        raise ValueError(
            f"Node {spec.type_id} resolved instance spec must clear instance_spec_resolver"
        )
    return resolved


@dataclass(slots=True, frozen=True)
class TrustedFactoryEntry:
    spec: NodeTypeSpec
    factory: Callable[[], NodePlugin]
    provenance: PluginProvenance | None = None
    owner_id: str = ""

    def descriptor(self) -> PluginDescriptor:
        return PluginDescriptor(
            spec=self.spec,
            factory=self.factory,
            provenance=self.provenance,
        )


@dataclass(slots=True, frozen=True)
class PythonFunctionEntry:
    spec: NodeTypeSpec
    function_ref: PythonFunctionRef
    owner_id: str = ""
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        if self.spec.is_async != self.function_ref.is_async:
            raise ValueError(
                "Python function reference async state must match NodeTypeSpec.is_async"
            )
        if self.owner_id != self.function_ref.bundle_id:
            raise ValueError("Python function entry owner_id must match function bundle_id")
        if not isinstance(self.unavailable_reason, str):
            raise TypeError("Python function entry unavailable_reason must be a string")
        if self.unavailable_reason != self.unavailable_reason.strip():
            raise ValueError("Python function entry unavailable_reason must be trimmed")


RegistryEntry = TrustedFactoryEntry | PythonFunctionEntry


class NodeRegistry:
    _TYPE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
    _SETTINGS_GROUP_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
    _SUPPORTED_PROPERTY_TYPES = {
        "str",
        "int",
        "float",
        "bool",
        "path",
        "enum",
        "json",
        INTERVAL_1D_DATA_TYPE,
    }
    _SUPPORTED_INLINE_EDITORS = {
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
    }
    _SUPPORTED_INSPECTOR_EDITORS = {
        "",
        "text",
        "textarea",
        "path",
        "toggle",
        "enum",
        "color",
        "font_family",
        "secret",
    }
    _SUPPORTED_RUNTIME_BEHAVIORS = {"active", "passive", "compile_only"}
    _SUPPORTED_SURFACE_FAMILIES = {
        "standard",
        "flowchart",
        "planning",
        "annotation",
        "group_backdrop",
        "media",
        "viewer",
        "dpf_workflow",
        "web",
        "jupyter",
    }

    def __init__(self, *, data_types: DataTypeCatalog | None = None) -> None:
        if data_types is None:
            data_types = DataTypeCatalog()
            data_types.register_many(
                families=CORE_DATA_TYPE_FAMILIES,
                types=CORE_DATA_TYPES,
                conversions=CORE_DATA_CONVERSIONS,
                owner_id=CORE_DATA_TYPE_OWNER_ID,
                owner_version=CORE_DATA_TYPE_OWNER_VERSION,
                source_label="ea_node_editor.nodes.core_data_types",
            )
        elif not isinstance(data_types, DataTypeCatalog):
            raise TypeError("data_types must be a DataTypeCatalog")
        self._data_types = data_types
        self._entries: dict[str, RegistryEntry] = {}
        self._contract_manifests: dict[str, PluginContractManifest] = {}
        self._contract_manifest_versions: dict[str, str] = {}
        self._owner_source_identities: dict[str, str] = {}
        self._plugin_bundle_refs: dict[str, PluginBundleRef] = {}
        self._plugin_fingerprint = hashlib.sha256(b"[]").hexdigest()

    @property
    def data_types(self) -> DataTypeCatalog:
        return self._data_types

    def freeze(self) -> None:
        self._data_types.freeze()

    def plugin_contract_manifest(self, owner_id: str) -> PluginContractManifest | None:
        return self._contract_manifests.get(str(owner_id).strip())

    def register_plugin_bundle(
        self,
        manifest: PluginContractManifest | None,
        descriptors: Iterable[PluginDescriptor],
        *,
        owner_id: str,
        owner_version: str = "",
        source_label: str = "",
        source_identity: str = "",
        replace_owner: bool = False,
    ) -> None:
        normalized_owner_id = str(owner_id).strip()
        if not normalized_owner_id:
            raise ValueError(
                "Plugin bundle owner_id must be a non-empty trimmed string"
            )
        normalized_source_identity = str(source_identity).strip()
        owner_is_active = (
            normalized_owner_id in self._contract_manifests
            or normalized_owner_id in self._contract_manifest_versions
            or normalized_owner_id in self._owner_source_identities
            or any(
                entry.owner_id == normalized_owner_id
                for entry in self._entries.values()
            )
            or any(
                record.get("owner_id") == normalized_owner_id
                for record in self._data_types.snapshot()
            )
        )
        if owner_is_active and not replace_owner:
            raise ValueError(
                f"Plugin bundle owner {normalized_owner_id!r} is already active; "
                "pass replace_owner=True to replace it"
            )
        existing_source_identity = self._owner_source_identities.get(
            normalized_owner_id,
            "",
        )
        if (
            existing_source_identity
            and normalized_source_identity
            and existing_source_identity != normalized_source_identity
        ):
            raise ValueError(
                f"Plugin bundle owner {normalized_owner_id!r} is already "
                "registered from a different source"
            )
        if manifest is None:
            normalized_manifest = PluginContractManifest()
        elif isinstance(manifest, PluginContractManifest):
            normalized_manifest = manifest
        else:
            raise TypeError(
                "Plugin bundle manifest must be a PluginContractManifest or None"
            )
        normalized_owner_version = str(owner_version)
        was_frozen = self._data_types.is_frozen
        staged_catalog = self._data_types.fork(
            excluding_owner_id=normalized_owner_id if replace_owner else "",
        )
        staged = NodeRegistry(data_types=staged_catalog)
        staged._entries = {
            type_id: entry
            for type_id, entry in self._entries.items()
            if not replace_owner or entry.owner_id != normalized_owner_id
        }
        staged._contract_manifests = {
            existing_owner: existing_manifest
            for existing_owner, existing_manifest in self._contract_manifests.items()
            if not replace_owner or existing_owner != normalized_owner_id
        }
        staged._contract_manifest_versions = {
            existing_owner: version
            for existing_owner, version in self._contract_manifest_versions.items()
            if not replace_owner or existing_owner != normalized_owner_id
        }
        staged._owner_source_identities = {
            existing_owner: identity
            for existing_owner, identity in self._owner_source_identities.items()
            if not replace_owner or existing_owner != normalized_owner_id
        }
        staged._plugin_bundle_refs = dict(self._plugin_bundle_refs)
        staged._plugin_fingerprint = self._plugin_fingerprint
        staged_catalog.register_many(
            families=normalized_manifest.data_type_families,
            types=normalized_manifest.data_types,
            conversions=normalized_manifest.data_conversions,
            owner_id=normalized_owner_id,
            owner_version=normalized_owner_version,
            source_label=str(source_label),
        )
        staged.register_descriptors(descriptors, owner_id=normalized_owner_id)
        for entry in staged._entries.values():
            staged._validate_spec(entry.spec)
        staged._contract_manifests[normalized_owner_id] = normalized_manifest
        staged._contract_manifest_versions[normalized_owner_id] = (
            normalized_owner_version
        )
        committed_source_identity = (
            normalized_source_identity or existing_source_identity
        )
        if committed_source_identity:
            staged._owner_source_identities[normalized_owner_id] = (
                committed_source_identity
            )
        if was_frozen:
            staged.freeze()
        self._data_types = staged._data_types
        self._entries = staged._entries
        self._contract_manifests = staged._contract_manifests
        self._contract_manifest_versions = staged._contract_manifest_versions
        self._owner_source_identities = staged._owner_source_identities
        self._plugin_bundle_refs = staged._plugin_bundle_refs
        self._plugin_fingerprint = staged._plugin_fingerprint

    def register(
        self,
        factory: Callable[[], NodePlugin],
        *,
        provenance: PluginProvenance | None = None,
        owner_id: str = "",
    ) -> None:
        plugin = factory()
        spec = plugin.spec()
        self.register_descriptor(
            spec,
            factory,
            provenance=provenance,
            owner_id=owner_id,
        )

    def register_descriptor(
        self,
        spec: NodeTypeSpec | PluginDescriptor,
        factory: Callable[[], NodePlugin] | None = None,
        *,
        provenance: PluginProvenance | None = None,
        owner_id: str = "",
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
        self._entries[spec.type_id] = TrustedFactoryEntry(
            spec=spec,
            factory=factory,
            provenance=provenance,
            owner_id=str(owner_id).strip(),
        )

    def register_descriptors(
        self,
        descriptors: Iterable[PluginDescriptor],
        *,
        owner_id: str = "",
    ) -> None:
        descriptor_items = tuple(descriptors)
        staged_entries = dict(self._entries)
        normalized_owner_id = str(owner_id).strip()
        for descriptor in descriptor_items:
            if not isinstance(descriptor, PluginDescriptor):
                raise TypeError(
                    "register_descriptors entries must be PluginDescriptor values"
                )
            if not callable(descriptor.factory):
                raise TypeError("Plugin factory must be callable")
            self._validate_spec(descriptor.spec)
            type_id = descriptor.spec.type_id
            if type_id in staged_entries:
                raise ValueError(f"Node type already registered: {type_id}")
            staged_entries[type_id] = TrustedFactoryEntry(
                spec=descriptor.spec,
                factory=descriptor.factory,
                provenance=descriptor.provenance,
                owner_id=normalized_owner_id,
            )
        self._entries = staged_entries

    def register_python_function(
        self,
        spec: NodeTypeSpec,
        function_ref: PythonFunctionRef,
        *,
        owner_id: str = "",
        unavailable_reason: str = "",
    ) -> None:
        if not isinstance(function_ref, PythonFunctionRef):
            raise TypeError("function_ref must be a PythonFunctionRef")
        normalized_owner_id = str(owner_id).strip() or function_ref.bundle_id
        if normalized_owner_id != function_ref.bundle_id:
            raise ValueError("owner_id must match function_ref.bundle_id")
        self._validate_spec(spec)
        if spec.type_id in self._entries:
            raise ValueError(f"Node type already registered: {spec.type_id}")
        self._entries[spec.type_id] = PythonFunctionEntry(
            spec=spec,
            function_ref=function_ref,
            owner_id=normalized_owner_id,
            unavailable_reason=unavailable_reason,
        )
        self._plugin_fingerprint = ""

    def create(self, type_id: str) -> NodePlugin:
        try:
            entry = self._entries[type_id]
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc
        if isinstance(entry, PythonFunctionEntry):
            if entry.unavailable_reason:
                raise RuntimeError(entry.unavailable_reason)
            raise RuntimeError(
                f"Public function node {type_id!r} requires process-worker resolution"
            )
        return entry.factory()

    def entry_or_none(self, type_id: str) -> RegistryEntry | None:
        return self._entries.get(type_id)

    def get_entry(self, type_id: str) -> RegistryEntry:
        try:
            return self._entries[type_id]
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc

    def python_function_ref_or_none(self, type_id: str) -> PythonFunctionRef | None:
        entry = self._entries.get(type_id)
        return entry.function_ref if isinstance(entry, PythonFunctionEntry) else None

    def unavailable_reason(self, type_id: str) -> str:
        entry = self._entries.get(type_id)
        return (
            entry.unavailable_reason
            if isinstance(entry, PythonFunctionEntry)
            else ""
        )

    def get_spec(self, type_id: str) -> NodeTypeSpec:
        try:
            return self._entries[type_id].spec
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc

    def validate_spec(self, spec: NodeTypeSpec) -> None:
        self._validate_spec(spec)

    def resolve_spec(
        self,
        type_id: str,
        properties: Mapping[str, object],
    ) -> NodeTypeSpec:
        base_spec = self.get_spec(type_id)
        resolved = resolve_instance_spec(base_spec, properties)
        if resolved is not base_spec:
            self._validate_spec(resolved)
        return resolved

    def spec_or_none(self, type_id: str) -> NodeTypeSpec | None:
        entry = self._entries.get(type_id)
        if entry is None:
            return None
        return entry.spec

    def get_descriptor(self, type_id: str) -> PluginDescriptor:
        try:
            entry = self._entries[type_id]
        except KeyError as exc:
            raise KeyError(f"Unknown node type: {type_id}") from exc
        if isinstance(entry, PythonFunctionEntry):
            raise TypeError(f"Node type {type_id!r} does not use a trusted descriptor")
        return entry.descriptor()

    def descriptor_or_none(self, type_id: str) -> PluginDescriptor | None:
        entry = self._entries.get(type_id)
        if entry is None:
            return None
        return entry.descriptor() if isinstance(entry, TrustedFactoryEntry) else None

    def all_specs(self) -> list[NodeTypeSpec]:
        return [entry.spec for entry in self._entries.values()]

    def all_descriptors(self) -> list[PluginDescriptor]:
        return [
            entry.descriptor()
            for entry in self._entries.values()
            if isinstance(entry, TrustedFactoryEntry)
        ]

    def all_python_function_refs(self) -> tuple[PythonFunctionRef, ...]:
        return tuple(
            entry.function_ref
            for entry in self._entries.values()
            if isinstance(entry, PythonFunctionEntry)
        )

    def set_python_plugin_catalog(
        self,
        bundles: tuple[PluginBundleRef, ...],
        *,
        plugin_fingerprint: str,
    ) -> None:
        if not isinstance(bundles, tuple) or not all(
            isinstance(bundle, PluginBundleRef) for bundle in bundles
        ):
            raise TypeError("bundles must be a tuple of PluginBundleRef values")
        owners = [bundle.owner_id for bundle in bundles]
        if len(owners) != len(set(owners)):
            raise ValueError("Plugin bundle owner ids must be unique")
        bundled_functions = {
            function for bundle in bundles for function in bundle.functions
        }
        if bundled_functions != set(self.all_python_function_refs()):
            raise ValueError("Plugin bundles must match registered Python function refs")
        fingerprint = str(plugin_fingerprint)
        if len(fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in fingerprint
        ):
            raise ValueError("plugin_fingerprint must be a lowercase SHA-256 digest")
        self._plugin_bundle_refs = {bundle.owner_id: bundle for bundle in bundles}
        self._plugin_fingerprint = fingerprint

    def plugin_bundle_refs(self) -> tuple[PluginBundleRef, ...]:
        return tuple(
            self._plugin_bundle_refs[owner_id]
            for owner_id in sorted(self._plugin_bundle_refs)
        )

    def plugin_fingerprint(self) -> str:
        return self._plugin_fingerprint

    def default_properties(self, type_id: str) -> dict[str, Any]:
        return self.normalize_properties(type_id, {}, include_defaults=True)

    def normalize_property_value(
        self,
        type_id: str,
        key: str,
        value: Any,
        *,
        properties: Mapping[str, object] | None = None,
    ) -> Any:
        prop_spec = self._property_spec(type_id, key, properties=properties)
        return self._normalize_special_property_value(
            type_id,
            key,
            _coerce_property_value(
                prop_spec,
                value,
                strict=False,
                data_types=self._data_types,
            ),
        )

    def normalize_properties(
        self,
        type_id: str,
        values: dict[str, Any] | None,
        *,
        include_defaults: bool = True,
    ) -> dict[str, Any]:
        provided = dict(values or {})
        ambiguous_legacy_dpf_time_scope = self._has_ambiguous_legacy_dpf_time_scope(
            type_id,
            provided,
        )
        provided = self._normalize_legacy_dpf_time_scope_properties(
            type_id,
            provided,
        )
        base_spec = self.get_spec(type_id)
        resolution_properties = {
            prop.key: copy.deepcopy(prop.default)
            for prop in base_spec.properties
        }
        resolution_properties.update(provided)
        spec = self.resolve_spec(type_id, resolution_properties)
        normalized: dict[str, Any] = {}
        for prop in spec.properties:
            if prop.key in provided:
                normalized[prop.key] = self._normalize_special_property_value(
                    type_id,
                    prop.key,
                    _coerce_property_value(
                        prop,
                        provided[prop.key],
                        strict=False,
                        data_types=self._data_types,
                    ),
                )
                continue
            if include_defaults:
                normalized[prop.key] = self._normalize_special_property_value(
                    type_id,
                    prop.key,
                    _coerce_property_value(
                        prop,
                        prop.default,
                        strict=False,
                        data_types=self._data_types,
                    ),
                )
        if ambiguous_legacy_dpf_time_scope:
            normalized.pop("time_scope_mode", None)
        normalized = self._normalize_special_properties(type_id, normalized)
        resolved_groups = _resolve_dynamic_port_groups(
            spec,
            normalized,
            data_types=self._data_types,
        )
        for group, ports in zip(spec.dynamic_port_groups, resolved_groups, strict=True):
            if include_defaults or group.property_key in provided:
                normalized[group.property_key] = [port.key for port in ports]
        return normalized

    @staticmethod
    def _has_ambiguous_legacy_dpf_time_scope(
        type_id: str, values: Mapping[str, Any]
    ) -> bool:
        if not type_id.startswith("dpf.workflow."):
            return False
        if str(values.get("time_scope_mode", "") or "").strip():
            return False
        return bool(str(values.get("set_ids", "") or "").strip()) and bool(
            str(values.get("time_values", "") or "").strip()
        )

    @staticmethod
    def _normalize_legacy_dpf_time_scope_properties(
        type_id: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        from ea_node_editor.nodes.builtins.ansys_dpf_common import (
            DPF_TIME_SCOPE_SET_IDS,
            DPF_TIME_SCOPE_TIME_VALUES,
            DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
            DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
            DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
        )

        supported = {
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
            DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
            DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
            DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
        }
        if (
            type_id not in supported
            or str(values.get("time_scope_mode", "") or "").strip()
        ):
            return values
        normalized = dict(values)
        normalized.pop("time_scope_mode", None)
        has_set_ids = bool(str(normalized.get("set_ids", "") or "").strip())
        has_time_values = bool(str(normalized.get("time_values", "") or "").strip())
        if has_set_ids and has_time_values:
            return normalized
        if has_set_ids:
            normalized["time_scope_mode"] = DPF_TIME_SCOPE_SET_IDS
        elif has_time_values:
            normalized["time_scope_mode"] = DPF_TIME_SCOPE_TIME_VALUES
        return normalized

    @staticmethod
    def _normalize_special_property_value(type_id: str, key: str, value: Any) -> Any:
        if type_id == "data.number_slider":
            from ea_node_editor.nodes.builtins.data_control import (
                normalize_number_slider_property_value,
            )

            return normalize_number_slider_property_value(key, value)
        if type_id != "web.page_viewer" or key != "browser_state":
            return value
        from ea_node_editor.nodes.builtins.web_viewer import (
            normalize_web_page_viewer_browser_state,
        )

        return normalize_web_page_viewer_browser_state(
            value if isinstance(value, Mapping) else {}
        )

    @staticmethod
    def _normalize_special_properties(
        type_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        if type_id == "data.select":
            from ea_node_editor.nodes.builtins.data_control import (
                normalize_select_properties,
            )

            return normalize_select_properties(values)
        if type_id == "data.number_slider":
            from ea_node_editor.nodes.builtins.data_control import (
                normalize_number_slider_properties,
            )

            return normalize_number_slider_properties(values)
        if type_id != "web.page_viewer":
            return values
        from ea_node_editor.nodes.builtins.web_viewer import (
            normalize_web_page_viewer_properties,
        )

        return normalize_web_page_viewer_properties(values)

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
        category_prefix = (
            normalize_category_path(category_path)
            if category_path is not None
            else None
        )
        category_display_filter = str(category).strip().casefold()
        normalized_type = data_type.strip().lower()
        normalized_direction = direction.strip().lower()
        output: list[NodeTypeSpec] = []
        for spec in self.all_specs():
            if category_prefix is not None:
                if not category_path_matches_prefix(
                    spec.category_path, category_prefix
                ):
                    continue
            elif category_display_filter:
                if (
                    category_display(spec.category_path).casefold()
                    != category_display_filter
                ):
                    continue
            if text and not self._matches_text(spec, text):
                continue
            if (
                normalized_type or normalized_direction
            ) and not self._matches_port_filters(
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
        return [
            category_display(path)
            for path in sorted(leaf_paths, key=self._category_path_sort_key)
        ]

    @staticmethod
    def _category_path_sort_key(
        path: Sequence[str],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        normalized_path = normalize_category_path(path)
        return tuple(segment.casefold() for segment in normalized_path), normalized_path

    @staticmethod
    def _matches_text(spec: NodeTypeSpec, query: str) -> bool:
        ports = resolve_instance_ports(spec, {})
        haystack = " ".join(
            [
                spec.type_id,
                spec.display_name,
                spec.category,
                spec.description,
                " ".join(port.key for port in ports),
            ]
        ).lower()
        return query in haystack

    @staticmethod
    def _matches_port_filters(
        spec: NodeTypeSpec, data_type: str, direction: str
    ) -> bool:
        for port in resolve_instance_ports(spec, {}):
            if direction and port.direction != direction:
                continue
            if data_type and not NodeRegistry._port_matches_data_type(port, data_type):
                continue
            return True
        return False

    @staticmethod
    def _port_matches_data_type(port: PortSpec, data_type: str) -> bool:
        accepted_types = (port.data_type, *port.accepted_data_types)
        return any(
            accepted_type.lower() == data_type for accepted_type in accepted_types
        )

    def _property_spec(
        self,
        type_id: str,
        key: str,
        *,
        properties: Mapping[str, object] | None = None,
    ) -> PropertySpec:
        spec = (
            self.resolve_spec(type_id, properties)
            if properties is not None
            else self.get_spec(type_id)
        )
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
            raise ValueError(
                f"Node {spec.type_id} surface_family must be a non-empty trimmed string"
            )
        if spec.surface_family not in self._SUPPORTED_SURFACE_FAMILIES:
            raise ValueError(
                f"Node {spec.type_id} surface_family has invalid value: {spec.surface_family}"
            )
        if (
            not isinstance(spec.surface_variant, str)
            or spec.surface_variant.strip() != spec.surface_variant
        ):
            raise ValueError(
                f"Node {spec.type_id} surface_variant must be a trimmed string"
            )
        if not isinstance(spec.ports, tuple):
            raise TypeError(f"Node {spec.type_id} ports must be a tuple[PortSpec, ...]")
        if not isinstance(spec.properties, tuple):
            raise TypeError(
                f"Node {spec.type_id} properties must be a tuple[PropertySpec, ...]"
            )
        if not isinstance(spec.dynamic_port_groups, tuple):
            raise TypeError(
                f"Node {spec.type_id} dynamic_port_groups must be a tuple[DynamicPortGroupSpec, ...]"
            )
        if not isinstance(spec.settings_groups, tuple):
            raise TypeError(
                f"Node {spec.type_id} settings_groups must be a tuple[SettingsGroupSpec, ...]"
            )
        if not isinstance(spec.readiness_requirements, tuple):
            raise TypeError(
                f"Node {spec.type_id} readiness_requirements must be a tuple[ReadinessRequirementSpec, ...]"
            )
        if spec.instance_spec_resolver is not None and not callable(
            spec.instance_spec_resolver
        ):
            raise TypeError(
                f"Node {spec.type_id} instance_spec_resolver must be callable or None"
            )

        port_keys: set[str] = set()
        for port in spec.ports:
            _validate_port(spec, port, data_types=self._data_types)
            if port.key in port_keys:
                raise ValueError(
                    f"Node {spec.type_id} has duplicate port key: {port.key}"
                )
            port_keys.add(port.key)

        property_keys: set[str] = set()
        properties_by_key: dict[str, PropertySpec] = {}
        for prop in spec.properties:
            self._validate_property(spec.type_id, prop)
            if prop.key in property_keys:
                raise ValueError(
                    f"Node {spec.type_id} has duplicate property key: {prop.key}"
                )
            property_keys.add(prop.key)
            properties_by_key[prop.key] = prop
        self._validate_sensitive_properties(spec, properties_by_key)
        resolved_ports = self._validate_dynamic_port_groups(spec, properties_by_key)
        self._validate_property_conditions(spec, properties_by_key)
        self._validate_property_default_ports(spec, properties_by_key)
        self._validate_readiness_requirements(spec, properties_by_key)
        self._validate_settings_groups(spec)
        self._validate_source_metadata(spec, ports=resolved_ports)
        if spec.instance_spec_resolver is not None:
            self._validate_spec(resolve_instance_spec(spec, {}))

    @staticmethod
    def _validate_sensitive_properties(
        spec: NodeTypeSpec,
        properties_by_key: Mapping[str, PropertySpec],
    ) -> None:
        for prop in spec.properties:
            secret_editor = (
                str(prop.inline_editor) == "secret"
                or str(prop.inspector_editor) == "secret"
            )
            if not isinstance(prop.sensitive, bool):
                raise TypeError(
                    f"Node {spec.type_id} property {prop.key} sensitive must be bool"
                )
            if secret_editor and not prop.sensitive:
                raise ValueError(
                    f"Node {spec.type_id} property {prop.key} secret editor requires sensitive=True"
                )
            if not prop.sensitive:
                if prop.sensitive_scope_key:
                    raise ValueError(
                        f"Node {spec.type_id} property {prop.key} sensitive_scope_key requires sensitive=True"
                    )
                continue
            if prop.type != "json":
                raise ValueError(
                    f"Node {spec.type_id} sensitive property {prop.key} requires a json property"
                )
            if not secret_editor:
                raise ValueError(
                    f"Node {spec.type_id} sensitive property {prop.key} requires a secret editor"
                )
            if not prop.sensitive_scope_key:
                continue
            scope_property = properties_by_key.get(prop.sensitive_scope_key)
            if scope_property is None or scope_property.type != "enum":
                raise ValueError(
                    f"Node {spec.type_id} sensitive property {prop.key} scope key "
                    f"{prop.sensitive_scope_key} must reference an enum property"
                )

    def _validate_dynamic_port_groups(
        self,
        spec: NodeTypeSpec,
        properties_by_key: Mapping[str, PropertySpec],
    ) -> tuple[PortSpec, ...]:
        group_ids: set[str] = set()
        property_keys: set[str] = set()
        directions: set[str] = set()
        for group in spec.dynamic_port_groups:
            if not isinstance(group, DynamicPortGroupSpec):
                raise TypeError(
                    f"Node {spec.type_id} dynamic_port_groups must contain DynamicPortGroupSpec instances"
                )
            if (
                not isinstance(group.group_id, str)
                or not group.group_id
                or group.group_id.strip() != group.group_id
            ):
                raise ValueError(
                    f"Node {spec.type_id} has invalid dynamic port group id: {group.group_id!r}"
                )
            if group.group_id in group_ids:
                raise ValueError(
                    f"Node {spec.type_id} has duplicate dynamic port group id: {group.group_id}"
                )
            group_ids.add(group.group_id)
            if (
                not isinstance(group.property_key, str)
                or not group.property_key
                or group.property_key.strip() != group.property_key
            ):
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} has invalid property key: "
                    f"{group.property_key!r}"
                )
            if group.property_key in property_keys:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port groups duplicate property key: {group.property_key}"
                )
            property_keys.add(group.property_key)
            backing_property = properties_by_key.get(group.property_key)
            if (
                backing_property is None
                or backing_property.type != "json"
                or backing_property.inspector_visible
            ):
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} requires hidden JSON property "
                    f"{group.property_key}"
                )
            if group.direction not in {"in", "out"}:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} has invalid direction: "
                    f"{group.direction}"
                )
            if group.direction in directions:
                raise ValueError(
                    f"Node {spec.type_id} has more than one dynamic port group for direction {group.direction}"
                )
            directions.add(group.direction)
            if (
                not isinstance(group.minimum, int)
                or isinstance(group.minimum, bool)
                or group.minimum < 0
            ):
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} minimum must be a non-negative int"
                )
            if group.maximum is not None and (
                not isinstance(group.maximum, int)
                or isinstance(group.maximum, bool)
                or group.maximum < group.minimum
            ):
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} maximum must be None or >= minimum"
                )
            if not callable(group.ports_resolver):
                raise TypeError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} ports_resolver must be callable"
                )
            if not callable(group.key_factory):
                raise TypeError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} key_factory must be callable"
                )
            if group.rename_mode not in {"none", "label", "key"}:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} has invalid rename_mode: "
                    f"{group.rename_mode}"
                )
            if group.rename_mode == "key":
                if not callable(group.key_renamer):
                    raise TypeError(
                        f"Node {spec.type_id} dynamic port group {group.group_id} key rename requires key_renamer"
                    )
            elif group.key_renamer is not None:
                raise ValueError(
                    f"Node {spec.type_id} dynamic port group {group.group_id} key_renamer requires key rename mode"
                )

        resolved_ports = resolve_instance_ports(
            spec,
            {},
            data_types=self._data_types,
        )
        for port in resolved_ports[len(spec.ports) :]:
            _validate_port(spec, port, data_types=self._data_types)
        return resolved_ports

    def _validate_readiness_requirements(
        self,
        spec: NodeTypeSpec,
        properties_by_key: Mapping[str, PropertySpec],
    ) -> None:
        if spec.readiness_requirements and spec.runtime_behavior != "active":
            raise ValueError(
                f"Node {spec.type_id} readiness_requirements are only supported on active nodes"
            )

        ports_by_key = {port.key: port for port in spec.ports}
        validated: list[ReadinessRequirementSpec] = []
        for index, requirement in enumerate(spec.readiness_requirements):
            field_name = f"Node {spec.type_id} readiness requirement {index}"
            if not isinstance(requirement, ReadinessRequirementSpec):
                raise TypeError(
                    f"Node {spec.type_id} readiness_requirements must contain ReadinessRequirementSpec instances"
                )
            self._validate_readiness_keys(
                field_name, "any_of_ports", requirement.any_of_ports
            )
            self._validate_readiness_keys(
                field_name,
                "any_of_properties",
                requirement.any_of_properties,
            )
            self._validate_readiness_keys(
                field_name,
                "when_ports_present",
                requirement.when_ports_present,
            )
            if not requirement.any_of_ports and not requirement.any_of_properties:
                raise ValueError(f"{field_name} must declare at least one target")
            if not isinstance(requirement.when_properties, tuple):
                raise TypeError(f"{field_name} when_properties must be a tuple")
            if set(requirement.any_of_ports) & set(requirement.when_ports_present):
                raise ValueError(
                    f"{field_name} cannot require and condition on the same port"
                )

            for key in requirement.any_of_ports + requirement.when_ports_present:
                port = ports_by_key.get(key)
                if port is None:
                    raise ValueError(f"{field_name} references unknown port: {key}")
                if port.direction != "in" or port.kind != "data":
                    raise ValueError(
                        f"{field_name} port {key} must be an active data input"
                    )
                if key in requirement.any_of_ports and port.required is True:
                    raise ValueError(
                        f"{field_name} port {key} duplicates its unconditional required input rule"
                    )
            for key in requirement.any_of_properties:
                if key not in properties_by_key:
                    raise ValueError(f"{field_name} references unknown property: {key}")
            if set(requirement.any_of_ports) & set(requirement.any_of_properties):
                raise ValueError(f"{field_name} target keys must be unambiguous")

            condition_keys: set[str] = set()
            for condition in requirement.when_properties:
                if not isinstance(condition, PropertyConditionSpec):
                    raise TypeError(
                        f"{field_name} when_properties must contain PropertyConditionSpec instances"
                    )
                key = condition.property_key
                if not isinstance(key, str) or not key or key.strip() != key:
                    raise ValueError(
                        f"{field_name} has an invalid condition property key: {key!r}"
                    )
                if key in condition_keys:
                    raise ValueError(
                        f"{field_name} has contradictory conditions for property: {key}"
                    )
                condition_keys.add(key)
                prop = properties_by_key.get(key)
                if prop is None:
                    raise ValueError(
                        f"{field_name} condition references unknown property: {key}"
                    )
                if not isinstance(condition.values, tuple):
                    raise TypeError(
                        f"{field_name} condition {key} values must be a tuple"
                    )
                seen_values: list[object] = []
                for value in condition.values:
                    self._validate_readiness_condition_value(field_name, prop, value)
                    if any(value == existing for existing in seen_values):
                        raise ValueError(
                            f"{field_name} condition {key} values must be unique"
                        )
                    seen_values.append(value)
            if set(requirement.any_of_properties) & condition_keys:
                raise ValueError(
                    f"{field_name} cannot require and condition on the same property"
                )
            if any(requirement == previous for previous in validated):
                raise ValueError(
                    f"Node {spec.type_id} has duplicate readiness requirements"
                )
            validated.append(requirement)

    def _validate_property_conditions(
        self,
        spec: NodeTypeSpec,
        properties_by_key: Mapping[str, PropertySpec],
    ) -> None:
        scalar_types = {"str", "path", "enum", "bool", "int", "float"}
        for prop in spec.properties:
            condition = prop.enabled_when
            if condition is None:
                continue
            field_name = f"Node {spec.type_id} property {prop.key} enabled_when"
            if not isinstance(condition, PropertyConditionSpec):
                raise TypeError(f"{field_name} must be a PropertyConditionSpec")
            key = condition.property_key
            if not isinstance(key, str) or not key or key.strip() != key:
                raise ValueError(f"{field_name} has an invalid property key: {key!r}")
            if key == prop.key:
                raise ValueError(f"{field_name} cannot reference itself")
            source = properties_by_key.get(key)
            if source is None:
                raise ValueError(f"{field_name} references unknown property: {key}")
            if source.type not in scalar_types:
                raise ValueError(f"{field_name} source {key} must be a scalar property")
            if not isinstance(condition.values, tuple):
                raise TypeError(f"{field_name} values must be a tuple")
            if not condition.values:
                raise ValueError(f"{field_name} values must not be empty")
            for value in condition.values:
                self._validate_enabled_condition_value(field_name, source, value)

    @staticmethod
    def _validate_enabled_condition_value(
        field_name: str,
        source: PropertySpec,
        value: object,
    ) -> None:
        if source.type in {"str", "path", "enum"}:
            valid = isinstance(value, str)
        elif source.type == "bool":
            valid = isinstance(value, bool)
        elif source.type == "int":
            valid = isinstance(value, int) and not isinstance(value, bool)
        else:
            valid = isinstance(value, float)
        if not valid:
            raise ValueError(
                f"{field_name} value is invalid for {source.type}: {value!r}"
            )
        if source.type == "enum" and value not in source.enum_values:
            raise ValueError(
                f"{field_name} value must be one of {source.enum_values}: {value!r}"
            )

    @staticmethod
    def _validate_readiness_keys(field_name: str, name: str, keys: object) -> None:
        if not isinstance(keys, tuple):
            raise TypeError(f"{field_name} {name} must be a tuple")
        seen: set[str] = set()
        for key in keys:
            if not isinstance(key, str) or not key or key.strip() != key:
                raise ValueError(
                    f"{field_name} {name} contains an invalid key: {key!r}"
                )
            if key in seen:
                raise ValueError(f"{field_name} {name} must not contain duplicates")
            seen.add(key)

    @staticmethod
    def _validate_readiness_condition_value(
        field_name: str,
        prop: PropertySpec,
        value: object,
    ) -> None:
        valid = False
        if prop.type in {"str", "path", "enum"}:
            valid = isinstance(value, str)
        elif prop.type == "bool":
            valid = isinstance(value, bool)
        elif prop.type == "int":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif prop.type == "float":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                valid = False
            else:
                valid = True
        if not valid:
            raise ValueError(
                f"{field_name} condition {prop.key} value is invalid for {prop.type}: {value!r}"
            )
        if prop.type == "enum" and value not in prop.enum_values:
            raise ValueError(
                f"{field_name} condition {prop.key} value must be one of {prop.enum_values}: {value!r}"
            )

    def _validate_property_default_ports(
        self,
        spec: NodeTypeSpec,
        properties_by_key: Mapping[str, PropertySpec],
    ) -> None:
        for port in spec.ports:
            if not port.uses_property_default:
                continue
            if (
                spec.runtime_behavior != "active"
                or port.direction != "in"
                or port.kind != "data"
            ):
                raise ValueError(
                    f"Node {spec.type_id} port {port.key} property defaults require an active data input"
                )
            prop = properties_by_key.get(port.key)
            if prop is None:
                raise ValueError(
                    f"Node {spec.type_id} port {port.key} property default requires a same-key property"
                )
            self._validate_property_default_value(spec.type_id, port, prop)

    def _validate_property_default_value(
        self,
        type_id: str,
        port: PortSpec,
        prop: PropertySpec,
    ) -> None:
        from ea_node_editor.runtime_contracts import DataTree

        normalized_default = _coerce_property_value(
            prop,
            prop.default,
            strict=True,
            data_types=self._data_types,
        )
        if (
            prop.type == INTERVAL_1D_DATA_TYPE
            or type(normalized_default) is TypedInlineValue
        ):
            value = normalized_default
        else:
            value = deserialize_runtime_value(normalized_default)
        if isinstance(value, DataTree):
            if port.data_access != "tree":
                raise ValueError(
                    f"Node {type_id} port {port.key} serialized DataTree default requires tree access"
                )
            tree = value
        elif port.data_access == "list":
            if isinstance(value, (str, bytes, bytearray)) or not isinstance(
                value, Sequence
            ):
                raise ValueError(
                    f"Node {type_id} port {port.key} list property default must be a non-string sequence"
                )
            tree = DataTree.from_list(value)
        else:
            tree = DataTree.from_item(value)

        accepted_types = (port.data_type, *port.accepted_data_types)
        incompatible = [
            item
            for _path, items in tree.branches
            for item in items
            if not any(
                self._property_default_item_matches_type(item, data_type)
                for data_type in accepted_types
            )
        ]
        if incompatible:
            raise ValueError(
                f"Node {type_id} port {port.key} property default is incompatible with {port.data_type}"
            )

    def _property_default_item_matches_type(
        self,
        value: object,
        data_type: str,
    ) -> bool:
        try:
            if type(value) is TypedInlineValue:
                self._data_types.validate_carrier(data_type, value)
            else:
                self._data_types.prepare_untyped_input(data_type, value)
        except DataTypeCatalogError:
            return False
        return True

    def _validate_settings_groups(self, spec: NodeTypeSpec) -> None:
        if not spec.settings_groups:
            return
        if spec.runtime_behavior != "active":
            raise ValueError(
                f"Node {spec.type_id} settings_groups are only supported on active nodes"
            )

        ports_by_key = {port.key: port for port in spec.ports}
        properties_by_key = {prop.key: prop for prop in spec.properties}
        group_ids: set[str] = set()
        grouped_port_keys: set[str] = set()
        grouped_property_keys: set[str] = set()
        for group in spec.settings_groups:
            if not isinstance(group, SettingsGroupSpec):
                raise TypeError(
                    f"Node {spec.type_id} settings_groups must contain SettingsGroupSpec instances"
                )
            if not isinstance(
                group.group_id, str
            ) or not self._SETTINGS_GROUP_ID_PATTERN.fullmatch(group.group_id):
                raise ValueError(
                    f"Node {spec.type_id} has invalid settings group id: {group.group_id!r}"
                )
            if group.group_id in group_ids:
                raise ValueError(
                    f"Node {spec.type_id} has duplicate settings group id: {group.group_id}"
                )
            group_ids.add(group.group_id)
            if (
                not isinstance(group.label, str)
                or not group.label
                or group.label.strip() != group.label
            ):
                raise ValueError(
                    f"Node {spec.type_id} settings group {group.group_id} label must be non-empty and trimmed"
                )
            if not isinstance(group.items, tuple) or not group.items:
                raise ValueError(
                    f"Node {spec.type_id} settings group {group.group_id} items must be a non-empty tuple"
                )

            for item in group.items:
                if not isinstance(item, SettingsGroupItemSpec):
                    raise TypeError(
                        f"Node {spec.type_id} settings group {group.group_id} items must be SettingsGroupItemSpec instances"
                    )
                if not isinstance(item.port_key, str) or not isinstance(
                    item.property_key, str
                ):
                    raise TypeError(
                        f"Node {spec.type_id} settings group {group.group_id} item keys must be strings"
                    )
                port_key = item.port_key
                property_key = item.property_key
                if port_key.strip() != port_key or property_key.strip() != property_key:
                    raise ValueError(
                        f"Node {spec.type_id} settings group {group.group_id} item keys must be trimmed"
                    )
                if not port_key and not property_key:
                    raise ValueError(
                        f"Node {spec.type_id} settings group {group.group_id} items require a port_key or property_key"
                    )
                if port_key:
                    port = ports_by_key.get(port_key)
                    if port is None:
                        raise ValueError(
                            f"Node {spec.type_id} settings group {group.group_id} references unknown port: {port_key}"
                        )
                    if port.direction != "in":
                        raise ValueError(
                            f"Node {spec.type_id} settings group {group.group_id} port {port_key} must be an input"
                        )
                    if port_key in grouped_port_keys:
                        raise ValueError(
                            f"Node {spec.type_id} settings groups duplicate port membership: {port_key}"
                        )
                    grouped_port_keys.add(port_key)
                if property_key:
                    prop = properties_by_key.get(property_key)
                    if prop is None:
                        raise ValueError(
                            f"Node {spec.type_id} settings group {group.group_id} references unknown property: {property_key}"
                        )
                    if not str(prop.inline_editor).strip():
                        raise ValueError(
                            f"Node {spec.type_id} settings group {group.group_id} property {property_key} requires an inline editor"
                        )
                    if property_key in grouped_property_keys:
                        raise ValueError(
                            f"Node {spec.type_id} settings groups duplicate property membership: {property_key}"
                        )
                    grouped_property_keys.add(property_key)
                if port_key and property_key:
                    from ea_node_editor.graph.input_semantics import (
                        property_override_input_port_keys,
                    )

                    if port_key not in property_override_input_port_keys(
                        spec.type_id, property_key
                    ):
                        raise ValueError(
                            f"Node {spec.type_id} settings group {group.group_id} pairs unrelated port/property keys: "
                            f"{port_key}/{property_key}"
                        )

    def _validate_property(self, type_id: str, prop: PropertySpec) -> None:
        if not isinstance(prop, PropertySpec):
            raise TypeError(f"Node {type_id} properties must be PropertySpec instances")
        if not prop.key or prop.key.strip() != prop.key:
            raise ValueError(f"Node {type_id} has invalid property key: {prop.key!r}")
        if prop.type not in self._SUPPORTED_PROPERTY_TYPES:
            raise ValueError(
                f"Node {type_id} property {prop.key} has invalid type: {prop.type}"
            )
        if not prop.label.strip():
            raise ValueError(
                f"Node {type_id} property {prop.key} label must be non-empty"
            )
        if not isinstance(prop.expose_port_toggle, bool):
            raise TypeError(
                f"Node {type_id} property {prop.key} expose_port_toggle must be bool"
            )
        inline_editor = str(prop.inline_editor).strip()
        if inline_editor != prop.inline_editor:
            raise ValueError(
                f"Node {type_id} property {prop.key} inline_editor must be trimmed"
            )
        if inline_editor not in self._SUPPORTED_INLINE_EDITORS:
            raise ValueError(
                f"Node {type_id} property {prop.key} inline_editor has invalid value: {inline_editor}"
            )
        if not isinstance(prop.searchable, bool):
            raise TypeError(
                f"Node {type_id} property {prop.key} searchable must be bool"
            )
        if prop.searchable and (prop.type != "enum" or inline_editor != "enum"):
            raise ValueError(
                f"Node {type_id} property {prop.key} searchable requires an enum property using the enum inline editor"
            )
        interval_direction = str(prop.interval_direction).strip()
        if interval_direction != prop.interval_direction:
            raise ValueError(
                f"Node {type_id} property {prop.key} interval_direction must be trimmed"
            )
        if interval_direction not in {"", "increasing", "decreasing"}:
            raise ValueError(
                f"Node {type_id} property {prop.key} interval_direction has invalid value: {interval_direction}"
            )
        if prop.type != INTERVAL_1D_DATA_TYPE and interval_direction:
            raise ValueError(
                f"Node {type_id} property {prop.key} interval_direction requires an interval_1d property"
            )
        if prop.type == INTERVAL_1D_DATA_TYPE and inline_editor not in {
            "",
            "interval_fields",
            "interval_slider",
        }:
            raise ValueError(
                f"Node {type_id} property {prop.key} interval_1d properties require the interval_slider inline editor"
            )
        if inline_editor == "slider":
            if prop.type not in {"int", "float"}:
                raise ValueError(
                    f"Node {type_id} property {prop.key} slider inline_editor requires an int or float property"
                )
            if prop.minimum is None or prop.maximum is None:
                raise ValueError(
                    f"Node {type_id} property {prop.key} slider inline_editor requires minimum and maximum"
                )
            if not float(prop.minimum) < float(prop.maximum):
                raise ValueError(
                    f"Node {type_id} property {prop.key} slider inline_editor requires minimum < maximum"
                )
            if float(prop.step) < 0.0:
                raise ValueError(
                    f"Node {type_id} property {prop.key} slider inline_editor step must be >= 0"
                )
        if inline_editor == "interval_slider":
            if prop.type != INTERVAL_1D_DATA_TYPE:
                raise ValueError(
                    f"Node {type_id} property {prop.key} interval_slider inline_editor requires an interval_1d property"
                )
            if not interval_direction:
                raise ValueError(
                    f"Node {type_id} property {prop.key} interval_slider inline_editor requires an interval direction"
                )
            numeric_metadata = {
                "minimum": prop.minimum,
                "maximum": prop.maximum,
                "step": prop.step,
            }
            for name, value in numeric_metadata.items():
                if isinstance(value, bool) or not isinstance(value, Real):
                    raise ValueError(
                        f"Node {type_id} property {prop.key} interval_slider {name} must be a finite number"
                    )
                if not math.isfinite(float(value)):
                    raise ValueError(
                        f"Node {type_id} property {prop.key} interval_slider {name} must be finite"
                    )
            minimum = float(prop.minimum)
            maximum = float(prop.maximum)
            step = float(prop.step)
            if minimum >= maximum:
                raise ValueError(
                    f"Node {type_id} property {prop.key} interval_slider requires minimum < maximum"
                )
            if step < 0.0:
                raise ValueError(
                    f"Node {type_id} property {prop.key} interval_slider step must be >= 0"
                )
        if inline_editor == "interval_fields" and prop.type != INTERVAL_1D_DATA_TYPE:
            raise ValueError(
                f"Node {type_id} property {prop.key} interval_fields requires an interval_1d property"
            )
        if inline_editor != "interval_slider" and prop.type == INTERVAL_1D_DATA_TYPE and (
            prop.minimum is not None
            or prop.maximum is not None
            or prop.step != 0.0
            or interval_direction
        ):
            raise ValueError(
                f"Node {type_id} property {prop.key} interval editor metadata requires interval_slider"
            )
        inspector_editor = str(prop.inspector_editor).strip()
        if inspector_editor != prop.inspector_editor:
            raise ValueError(
                f"Node {type_id} property {prop.key} inspector_editor must be trimmed"
            )
        if inspector_editor not in self._SUPPORTED_INSPECTOR_EDITORS:
            raise ValueError(
                f"Node {type_id} property {prop.key} inspector_editor has invalid value: {inspector_editor}"
            )
        file_filter = str(prop.file_filter).strip()
        if file_filter != prop.file_filter:
            raise ValueError(
                f"Node {type_id} property {prop.key} file_filter must be trimmed"
            )
        if (
            file_filter
            and prop.type != "path"
            and inline_editor != "path"
            and property_inspector_editor(prop) != "path"
        ):
            raise ValueError(
                f"Node {type_id} property {prop.key} file_filter requires a path property/editor"
            )
        if not isinstance(prop.inspector_visible, bool):
            raise TypeError(
                f"Node {type_id} property {prop.key} inspector_visible must be bool"
            )
        persistence_data_type_id = prop.persistence_data_type_id
        if persistence_data_type_id:
            try:
                persistence_spec = self._data_types.require(persistence_data_type_id)
            except DataTypeCatalogError as exc:
                raise ValueError(
                    f"Node {type_id} property {prop.key} declares {exc}"
                ) from exc
            if persistence_spec.persistence == "never":
                raise ValueError(
                    f"Node {type_id} property {prop.key} data type "
                    f"{persistence_data_type_id!r} does not permit persistence"
                )
        enum_values = tuple(prop.enum_values)
        enum_codes = tuple(prop.enum_codes)
        if prop.type == "enum":
            if not enum_values:
                raise ValueError(
                    f"Node {type_id} enum property {prop.key} must define enum_values"
                )
            if len(set(enum_values)) != len(enum_values):
                raise ValueError(
                    f"Node {type_id} enum property {prop.key} enum_values must be unique"
                )
        elif enum_values and not (inline_editor == "enum" and enum_codes):
            raise ValueError(
                f"Node {type_id} non-enum property {prop.key} cannot define enum_values"
            )
        if enum_codes:
            if inline_editor != "enum" or len(enum_codes) != len(enum_values):
                raise ValueError(
                    f"Node {type_id} property {prop.key} enum_codes must match enum_values"
                )
            if len(set(enum_codes)) != len(enum_codes):
                raise ValueError(
                    f"Node {type_id} property {prop.key} enum_codes must be unique"
                )
        if prop.nullable and prop.type != INTERVAL_1D_DATA_TYPE:
            raise ValueError(
                f"Node {type_id} property {prop.key} nullable is supported only for interval_1d"
            )
        if inline_editor == "list":
            if prop.type != "json" or prop.list_item_type not in {"str", "int", "float", "enum", "color"}:
                raise ValueError(
                    f"Node {type_id} property {prop.key} list editor requires a json property and list_item_type"
                )
            if not isinstance(prop.default, list):
                raise ValueError(
                    f"Node {type_id} property {prop.key} list editor default must be a list"
                )
            if prop.list_item_type == "enum":
                if (
                    not prop.list_item_enum_values
                    or len(prop.list_item_enum_values) != len(prop.list_item_enum_codes)
                    or len(set(prop.list_item_enum_codes)) != len(prop.list_item_enum_codes)
                ):
                    raise ValueError(
                        f"Node {type_id} property {prop.key} enum list metadata is invalid"
                    )
                if any(item not in prop.list_item_enum_codes for item in prop.default):
                    raise ValueError(
                        f"Node {type_id} property {prop.key} enum list default contains an invalid code"
                    )
            elif prop.list_item_enum_values or prop.list_item_enum_codes:
                raise ValueError(
                    f"Node {type_id} property {prop.key} non-enum list cannot define enum metadata"
                )
            bounded_list = prop.list_item_minimum is not None or prop.list_item_maximum is not None
            if bounded_list:
                if (
                    prop.list_item_type not in {"int", "float"}
                    or prop.list_item_minimum is None
                    or prop.list_item_maximum is None
                    or not math.isfinite(float(prop.list_item_minimum))
                    or not math.isfinite(float(prop.list_item_maximum))
                    or float(prop.list_item_minimum) >= float(prop.list_item_maximum)
                    or float(prop.list_item_step) < 0.0
                ):
                    raise ValueError(
                        f"Node {type_id} property {prop.key} bounded list metadata is invalid"
                    )
                if any(
                    isinstance(item, bool)
                    or not isinstance(item, Real)
                    or not float(prop.list_item_minimum) <= float(item) <= float(prop.list_item_maximum)
                    for item in prop.default
                ):
                    raise ValueError(
                        f"Node {type_id} property {prop.key} list default is outside its bounds"
                    )
            elif prop.list_item_step != 0.0:
                raise ValueError(
                    f"Node {type_id} property {prop.key} list_item_step requires bounds"
                )
        elif (
            prop.list_item_type
            or prop.list_item_enum_values
            or prop.list_item_enum_codes
            or prop.list_item_minimum is not None
            or prop.list_item_maximum is not None
            or prop.list_item_step != 0.0
        ):
            raise ValueError(
                f"Node {type_id} property {prop.key} list metadata requires the list inline editor"
            )
        normalized_default = _coerce_property_value(
            prop,
            prop.default,
            strict=True,
            data_types=self._data_types,
        )
        if inline_editor == "interval_slider":
            if (
                not float(prop.minimum)
                <= normalized_default.start
                <= float(prop.maximum)
            ):
                raise ValueError(
                    f"Node {type_id} property {prop.key} interval start is outside the slider domain"
                )
            if not float(prop.minimum) <= normalized_default.end <= float(prop.maximum):
                raise ValueError(
                    f"Node {type_id} property {prop.key} interval end is outside the slider domain"
                )
            if (
                interval_direction == "increasing"
                and normalized_default.start > normalized_default.end
            ):
                raise ValueError(
                    f"Node {type_id} property {prop.key} default must be increasing"
                )
            if (
                interval_direction == "decreasing"
                and normalized_default.start < normalized_default.end
            ):
                raise ValueError(
                    f"Node {type_id} property {prop.key} default must be decreasing"
                )

    def _validate_source_metadata(
        self,
        spec: NodeTypeSpec,
        *,
        ports: tuple[PortSpec, ...] | None = None,
    ) -> None:
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

        for port in spec.ports if ports is None else ports:
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
            raise TypeError(
                f"Node {spec.type_id} port {port.key} source_metadata must be DpfPinSourceSpec"
            )
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


def default_port(spec: NodeTypeSpec, key: str) -> PortSpec:
    for port in spec.ports:
        if port.key == key:
            return port
    raise KeyError(f"Port {key} not found in {spec.type_id}")
