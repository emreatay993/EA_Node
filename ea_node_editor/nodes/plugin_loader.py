"""Discovers and loads user-authored node plugins from disk and installed packages."""

from __future__ import annotations

from dataclasses import replace
import importlib
from importlib.machinery import ModuleSpec
import importlib.util
import hashlib
import logging
import re
import sys
import types
from pathlib import Path
from typing import Any

from ea_node_editor.app_preferences import addon_state, normalize_app_preferences_document
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.plugin_contracts import (
    AddOnManifest,
    AddOnRecord,
    AddOnState,
    NodePlugin,
    PluginBackendDescriptor,
    PluginDescriptor,
    PluginProvenance,
    PluginAvailability,
)
from ea_node_editor.settings import plugins_dir

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "ea_node_editor.plugins"
_SAFE_MODULE_SEGMENT_RE = re.compile(r"[^0-9A-Za-z_]+")


def _legacy_plugin_spec(obj: Any) -> NodeTypeSpec | None:
    """Return a plugin spec when *obj* matches the legacy class contract."""
    if not isinstance(obj, type):
        return None
    if obj is NodePlugin:
        return None
    try:
        instance = obj()
        spec = instance.spec()
        if isinstance(spec, NodeTypeSpec) and callable(getattr(instance, "execute", None)):
            return spec
    except Exception:  # noqa: BLE001
        return None
    return None


def _coerce_plugin_descriptor(raw_descriptor: object) -> PluginDescriptor:
    if isinstance(raw_descriptor, PluginDescriptor):
        return raw_descriptor
    if isinstance(raw_descriptor, (tuple, list)) and len(raw_descriptor) == 2:
        spec, factory = raw_descriptor
        return PluginDescriptor(spec=spec, factory=factory)
    raise TypeError(
        "PLUGIN_DESCRIPTORS entries must be PluginDescriptor values or (spec, factory) pairs",
    )


def _coerce_plugin_backend(raw_backend: object) -> PluginBackendDescriptor:
    if isinstance(raw_backend, PluginBackendDescriptor):
        return raw_backend
    raise TypeError("PLUGIN_BACKENDS entries must be PluginBackendDescriptor values")


def _module_plugin_backends(module: Any) -> tuple[PluginBackendDescriptor, ...] | None:
    raw_backends = getattr(module, "PLUGIN_BACKENDS", None)
    if raw_backends is None:
        return None
    try:
        return tuple(_coerce_plugin_backend(item) for item in raw_backends)
    except TypeError as exc:
        raise TypeError("PLUGIN_BACKENDS must be an iterable of plugin backends") from exc


def _module_plugin_descriptors(module: Any) -> tuple[PluginDescriptor, ...] | None:
    raw_descriptors = getattr(module, "PLUGIN_DESCRIPTORS", None)
    if raw_descriptors is None:
        return None
    try:
        return tuple(_coerce_plugin_descriptor(item) for item in raw_descriptors)
    except TypeError as exc:
        raise TypeError("PLUGIN_DESCRIPTORS must be an iterable of plugin descriptors") from exc


def _descriptor_with_provenance(
    descriptor: PluginDescriptor,
    provenance: PluginProvenance | None,
) -> PluginDescriptor:
    if provenance is None or descriptor.provenance == provenance:
        return descriptor
    return replace(descriptor, provenance=provenance)


def _file_plugin_provenance(py_file: Path) -> PluginProvenance:
    return PluginProvenance(kind="file", source_path=py_file.resolve())


def _package_plugin_provenance(package_dir: Path, source_path: Path) -> PluginProvenance:
    return PluginProvenance(
        kind="package",
        source_path=source_path.resolve(),
        package_root=package_dir.resolve(),
        package_name=package_dir.name,
    )


def _entry_point_plugin_provenance(entry_point: Any) -> PluginProvenance:
    distribution = getattr(entry_point, "dist", None)
    return PluginProvenance(
        kind="entry_point",
        entry_point_name=str(getattr(entry_point, "name", "") or ""),
        distribution_name=str(getattr(distribution, "name", "") or ""),
    )


def _entry_points_for_group() -> tuple[Any, ...]:
    from importlib.metadata import entry_points

    try:
        return tuple(entry_points(group=ENTRY_POINT_GROUP))
    except TypeError:
        all_entry_points = entry_points()
        if hasattr(all_entry_points, "select"):
            return tuple(all_entry_points.select(group=ENTRY_POINT_GROUP))
        return tuple(all_entry_points.get(ENTRY_POINT_GROUP, ()))


def _registered_addon_registrations():
    from ea_node_editor.addons.catalog import registered_addon_registrations

    return registered_addon_registrations()


def _safe_module_segment(value: str, *, fallback: str) -> str:
    segment = _SAFE_MODULE_SEGMENT_RE.sub("_", value).strip("_")
    if not segment:
        return fallback
    if segment[0].isdigit():
        return f"_{segment}"
    return segment


def _module_name_for_path(py_file: Path, *, prefix: str) -> str:
    safe_stem = _safe_module_segment(py_file.stem, fallback="plugin")
    digest = hashlib.sha1(str(py_file.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{safe_stem}_{digest}"


def _public_plugin_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return [py_file for py_file in sorted(directory.glob("*.py")) if not py_file.name.startswith("_")]


def _plugin_package_directories(root_directory: Path) -> list[Path]:
    if not root_directory.is_dir():
        return []
    return [
        child
        for child in sorted(root_directory.iterdir())
        if child.is_dir() and not child.name.startswith((".", "_"))
    ]


def _load_module(
    module_name: str,
    module_path: Path,
    *,
    search_locations: list[str] | None = None,
):
    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
        submodule_search_locations=search_locations,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001
        sys.modules.pop(module_name, None)
        raise
    return module


def _register_plugin_descriptors(
    descriptors: tuple[PluginDescriptor, ...],
    registry: NodeRegistry,
    source: Path | str,
    *,
    provenance: PluginProvenance | None = None,
) -> list[str]:
    loaded: list[str] = []
    for index, descriptor in enumerate(descriptors):
        descriptor = _descriptor_with_provenance(descriptor, provenance)
        descriptor_label = getattr(descriptor.spec, "type_id", f"descriptor[{index}]")
        try:
            registry.register_descriptor(descriptor)
            loaded.append(descriptor.spec.type_id)
        except (ValueError, TypeError, KeyError):
            logger.warning(
                "Skipping invalid plugin descriptor %s in %s",
                descriptor_label,
                source,
                exc_info=True,
            )
    return loaded


def _register_plugin_backend(
    backend: PluginBackendDescriptor,
    registry: NodeRegistry,
    source: Path | str,
    *,
    provenance: PluginProvenance | None = None,
) -> list[str]:
    availability = backend.get_availability()
    if not availability.is_available:
        logger.info(
            "Skipping unavailable plugin backend %s from %s: %s",
            backend.plugin_id,
            source,
            availability.summary or ", ".join(availability.missing_dependencies),
        )
        return []
    return _register_plugin_descriptors(
        backend.load_descriptors(),
        registry,
        source,
        provenance=backend.provenance if backend.provenance is not None else provenance,
    )


def register_plugin_backends(
    backends: tuple[PluginBackendDescriptor, ...] | list[PluginBackendDescriptor],
    registry: NodeRegistry,
    source: Path | str,
    *,
    provenance: PluginProvenance | None = None,
) -> list[str]:
    loaded: list[str] = []
    for backend in backends:
        try:
            loaded.extend(
                _register_plugin_backend(
                    backend,
                    registry,
                    source,
                    provenance=provenance,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to load plugin backend %s from %s",
                backend.plugin_id,
                source,
                exc_info=True,
            )
    return loaded


def _register_plugin_classes(
    module: Any,
    registry: NodeRegistry,
    source: Path,
    *,
    provenance: PluginProvenance | None = None,
) -> list[str]:
    loaded: list[str] = []
    for attr_name in dir(module):
        obj = getattr(module, attr_name, None)
        spec = _legacy_plugin_spec(obj)
        if spec is None:
            continue
        try:
            registry.register_descriptor(spec, obj, provenance=provenance)
            loaded.append(spec.type_id)
        except (ValueError, TypeError, KeyError):
            logger.warning(
                "Skipping invalid plugin class %s in %s",
                attr_name,
                source,
                exc_info=True,
            )
    return loaded


def _register_module_plugins(
    module: Any,
    registry: NodeRegistry,
    source: Path,
    *,
    provenance: PluginProvenance | None = None,
    preferred_descriptors: tuple[PluginDescriptor, ...] | None = None,
) -> list[str]:
    backends = _module_plugin_backends(module)
    if backends is not None:
        return register_plugin_backends(
            backends,
            registry,
            source,
            provenance=provenance,
        )
    descriptors = preferred_descriptors
    if descriptors is None:
        descriptors = _module_plugin_descriptors(module)
    if descriptors is not None:
        return _register_plugin_descriptors(
            descriptors,
            registry,
            source,
            provenance=provenance,
        )
    return _register_plugin_classes(
        module,
        registry,
        source,
        provenance=provenance,
    )


def _load_plugins_from_directory(directory: Path, registry: NodeRegistry) -> list[str]:
    """Import every .py file in *directory* and register any NodePlugin classes found."""
    loaded: list[str] = []

    for py_file in _public_plugin_files(directory):
        try:
            module = _load_module(_module_name_for_path(py_file, prefix="_ea_plugin"), py_file)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load plugin file %s", py_file, exc_info=True)
            continue

        loaded.extend(
            _register_module_plugins(
                module,
                registry,
                py_file,
                provenance=_file_plugin_provenance(py_file),
            )
        )
    return loaded


def _create_namespace_package(package_name: str, package_dir: Path) -> None:
    module = types.ModuleType(package_name)
    module.__file__ = str(package_dir)
    module.__package__ = package_name
    module.__path__ = [str(package_dir)]
    spec = ModuleSpec(package_name, loader=None, is_package=True)
    spec.submodule_search_locations = [str(package_dir)]
    module.__spec__ = spec
    sys.modules[package_name] = module


def _load_plugins_from_package_directory(
    package_dir: Path,
    registry: NodeRegistry,
    *,
    descriptor_overrides: dict[str, tuple[PluginDescriptor, ...]] | None = None,
) -> list[str]:
    """Import public plugin modules from a package directory beneath the plugins root."""
    loaded: list[str] = []
    if not package_dir.is_dir():
        return loaded

    package_name = _module_name_for_path(package_dir / "__init__.py", prefix="_ea_plugin_pkg")
    init_file = package_dir / "__init__.py"

    if init_file.is_file():
        try:
            package_module = _load_module(
                package_name,
                init_file,
                search_locations=[str(package_dir)],
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to initialize plugin package %s", package_dir, exc_info=True)
            _create_namespace_package(package_name, package_dir)
        else:
            loaded.extend(
                _register_module_plugins(
                    package_module,
                    registry,
                    init_file,
                    provenance=_package_plugin_provenance(package_dir, init_file),
                    preferred_descriptors=(descriptor_overrides or {}).get(init_file.name),
                )
            )
    else:
        _create_namespace_package(package_name, package_dir)

    for py_file in _public_plugin_files(package_dir):
        module_name = f"{package_name}.{_safe_module_segment(py_file.stem, fallback='plugin')}"
        try:
            module = _load_module(module_name, py_file)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load plugin file %s", py_file, exc_info=True)
            continue

        loaded.extend(
            _register_module_plugins(
                module,
                registry,
                py_file,
                provenance=_package_plugin_provenance(package_dir, py_file),
                preferred_descriptors=(descriptor_overrides or {}).get(py_file.name),
            )
        )
    return loaded


def discover_package_plugins(
    package_dir: Path,
    registry: NodeRegistry,
    *,
    descriptor_overrides: dict[str, tuple[PluginDescriptor, ...]] | None = None,
) -> list[str]:
    """Load discoverable plugin modules from one installed package directory."""
    return _load_plugins_from_package_directory(
        package_dir,
        registry,
        descriptor_overrides=descriptor_overrides,
    )


def _load_plugins_from_root(root_directory: Path, registry: NodeRegistry) -> list[str]:
    """Load public plugin modules from a plugin root and its package subdirectories."""
    loaded = _load_plugins_from_directory(root_directory, registry)
    for package_dir in _plugin_package_directories(root_directory):
        loaded.extend(discover_package_plugins(package_dir, registry))
    return loaded


def _load_plugins_from_entry_points(registry: NodeRegistry) -> list[str]:
    """Load plugins registered via Python package entry points."""
    loaded: list[str] = []
    try:
        eps = _entry_points_for_group()
    except Exception:  # noqa: BLE001
        return loaded

    for ep in eps:
        provenance = _entry_point_plugin_provenance(ep)
        try:
            plugin_target = ep.load()
            backends = _module_plugin_backends(plugin_target)
            if backends is not None:
                loaded.extend(
                    register_plugin_backends(
                        backends,
                        registry,
                        ep.name,
                        provenance=provenance,
                    )
                )
                continue
            descriptors = _module_plugin_descriptors(plugin_target)
            if descriptors is not None:
                loaded.extend(
                    _register_plugin_descriptors(
                        descriptors,
                        registry,
                        ep.name,
                        provenance=provenance,
                    )
                )
                continue

            spec = _legacy_plugin_spec(plugin_target)
            if spec is None:
                continue
            registry.register_descriptor(spec, plugin_target, provenance=provenance)
            loaded.append(spec.type_id)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load entry-point plugin %s", ep.name, exc_info=True)
    return loaded


def _load_addon_backend_from_registration(registration: Any) -> tuple[PluginBackendDescriptor | None, Any | None]:
    try:
        module = importlib.import_module(registration.backend_module)
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to import add-on backend module %s",
            registration.backend_module,
            exc_info=True,
        )
        return None, None

    raw_backends = getattr(module, registration.backend_collection_attr, ())
    try:
        backends = tuple(_coerce_plugin_backend(item) for item in raw_backends)
    except TypeError:
        logger.warning(
            "Ignoring invalid add-on backend registration from %s",
            registration.backend_module,
            exc_info=True,
        )
        return None, module

    for backend in backends:
        if backend.plugin_id == registration.backend_id:
            return backend, module

    logger.warning(
        "Add-on backend %s was not found in %s",
        registration.backend_id,
        registration.backend_module,
    )
    return None, module


def _resolve_addon_version(manifest: AddOnManifest, *, module: Any, registration: Any) -> str:
    version = manifest.version
    version_resolver_attr = str(getattr(registration, "version_resolver_attr", "") or "").strip()
    if module is None or not version_resolver_attr:
        return version
    version_resolver = getattr(module, version_resolver_attr, None)
    if not callable(version_resolver):
        return version
    try:
        resolved_version = version_resolver()
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to resolve add-on version for %s",
            manifest.addon_id,
            exc_info=True,
        )
        return version
    return str(resolved_version or version)


def _unavailable_addon_availability(manifest: AddOnManifest, *, reason: str = "") -> PluginAvailability:
    summary = reason.strip()
    if not summary:
        summary = (
            f"{manifest.display_name} could not initialize its backend metadata; "
            "the add-on remains unavailable."
        )
    return PluginAvailability.missing_dependency(*manifest.dependencies, summary=summary)


def discover_addon_records(*, preferences_document: Any = None) -> tuple[AddOnRecord, ...]:
    normalized_preferences = normalize_app_preferences_document(preferences_document)
    records: list[AddOnRecord] = []

    for registration in _registered_addon_registrations():
        manifest = registration.manifest
        backend, module = _load_addon_backend_from_registration(registration)

        if backend is None:
            availability = _unavailable_addon_availability(manifest)
        else:
            manifest = backend.addon_manifest or manifest
            try:
                availability = backend.get_availability()
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to resolve add-on availability for %s",
                    manifest.addon_id,
                    exc_info=True,
                )
                availability = _unavailable_addon_availability(
                    manifest,
                    reason=f"{manifest.display_name} failed to resolve add-on availability.",
                )

        state_payload = addon_state(normalized_preferences, manifest.addon_id)
        state = AddOnState(
            enabled=state_payload["enabled"],
            pending_restart=state_payload["pending_restart"],
        )

        provided_node_type_ids: tuple[str, ...] = ()
        if backend is not None and availability.is_available:
            try:
                descriptors = backend.load_descriptors()
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to resolve provided node types for add-on %s",
                    manifest.addon_id,
                    exc_info=True,
                )
            else:
                provided_node_type_ids = tuple(
                    dict.fromkeys(descriptor.spec.type_id for descriptor in descriptors)
                )

        manifest = replace(
            manifest,
            version=_resolve_addon_version(manifest, module=module, registration=registration),
        )
        records.append(
            AddOnRecord(
                manifest=manifest,
                state=state,
                availability=availability,
                provided_node_type_ids=provided_node_type_ids,
            )
        )

    return tuple(records)


def addon_record_by_id(addon_id: str, *, preferences_document: Any = None) -> AddOnRecord | None:
    normalized_addon_id = str(addon_id).strip()
    if not normalized_addon_id:
        return None
    for record in discover_addon_records(preferences_document=preferences_document):
        if record.addon_id == normalized_addon_id:
            return record
    return None


def discover_and_load_plugins(
    registry: NodeRegistry,
    extra_dirs: list[Path] | None = None,
) -> list[str]:
    """Load plugins from all sources and return the list of registered type_ids."""
    loaded: list[str] = []

    loaded.extend(_load_plugins_from_root(plugins_dir(), registry))

    for directory in extra_dirs or []:
        loaded.extend(_load_plugins_from_root(directory, registry))

    loaded.extend(_load_plugins_from_entry_points(registry))

    if loaded:
        logger.info("Loaded %d plugin node(s): %s", len(loaded), ", ".join(loaded))
    return loaded


__all__ = [
    "ENTRY_POINT_GROUP",
    "addon_record_by_id",
    "discover_addon_records",
    "discover_and_load_plugins",
    "discover_package_plugins",
    "register_plugin_backends",
]
