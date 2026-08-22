# Purpose: Discover plugins and atomically register their contracts before node descriptors.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_plugin_loader.py

"""Discovers and loads user-authored node plugins from disk and installed packages."""

from __future__ import annotations

from dataclasses import replace
import importlib
import importlib.util
import hashlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.plugin_contracts import (
    PluginBackendDescriptor,
    PluginContractManifest,
    PluginDescriptor,
    PluginProvenance,
)
from ea_node_editor.settings import plugins_dir

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "ea_node_editor.plugins"
_SAFE_MODULE_SEGMENT_RE = re.compile(r"[^0-9A-Za-z_]+")
_PLUGIN_LOG_LABEL_LENGTH = 256
def _module_plugin_contract_manifest(
    module: Any,
) -> PluginContractManifest | None:
    raw_manifest = getattr(module, "PLUGIN_CONTRACT_MANIFEST", None)
    if raw_manifest is None:
        return None
    if not isinstance(raw_manifest, PluginContractManifest):
        raise TypeError(
            "PLUGIN_CONTRACT_MANIFEST must be a PluginContractManifest"
        )
    return raw_manifest


def _merge_contract_manifests(
    *manifests: PluginContractManifest,
) -> PluginContractManifest:
    return PluginContractManifest(
        runtime_backends=tuple(
            item for manifest in manifests for item in manifest.runtime_backends
        ),
        toolchains=tuple(
            item for manifest in manifests for item in manifest.toolchains
        ),
        artifacts=tuple(
            item for manifest in manifests for item in manifest.artifacts
        ),
        surface_capabilities=tuple(
            item
            for manifest in manifests
            for item in manifest.surface_capabilities
        ),
        data_type_families=tuple(
            item
            for manifest in manifests
            for item in manifest.data_type_families
        ),
        data_types=tuple(
            item for manifest in manifests for item in manifest.data_types
        ),
        data_conversions=tuple(
            item
            for manifest in manifests
            for item in manifest.data_conversions
        ),
    )


def _module_plugin_backends(
    module: Any,
    *,
    collection_attr: str = "PLUGIN_BACKENDS",
) -> tuple[PluginBackendDescriptor, ...] | None:
    raw_backends = getattr(module, collection_attr, None)
    if raw_backends is None:
        return None
    try:
        backends = tuple(raw_backends)
    except TypeError as exc:
        raise TypeError(f"{collection_attr} must be an iterable of PluginBackendDescriptor values") from exc
    if any(not isinstance(backend, PluginBackendDescriptor) for backend in backends):
        raise TypeError(f"{collection_attr} entries must be PluginBackendDescriptor values")
    return backends


def _module_plugin_descriptors(module: Any) -> tuple[PluginDescriptor, ...] | None:
    raw_descriptors = getattr(module, "PLUGIN_DESCRIPTORS", None)
    if raw_descriptors is None:
        return None
    try:
        descriptors = tuple(raw_descriptors)
    except TypeError as exc:
        raise TypeError("PLUGIN_DESCRIPTORS must be an iterable of PluginDescriptor values") from exc
    if any(not isinstance(descriptor, PluginDescriptor) for descriptor in descriptors):
        raise TypeError("PLUGIN_DESCRIPTORS entries must be PluginDescriptor values")
    return descriptors


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

    return tuple(entry_points(group=ENTRY_POINT_GROUP))


def _safe_module_segment(value: str, *, fallback: str) -> str:
    segment = _SAFE_MODULE_SEGMENT_RE.sub("_", value).strip("_")
    if not segment:
        return fallback
    if segment[0].isdigit():
        return f"_{segment}"
    return segment


def _bounded_plugin_log_label(value: object) -> str:
    text = str(value or "")
    if (
        text
        and len(text) <= _PLUGIN_LOG_LABEL_LENGTH
        and not (len(text) >= 2 and text[0].isalpha() and text[1] == ":")
        and all(character.isalnum() or character in "._:@+-" for character in text)
    ):
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"plugin:opaque:{digest}"


def _module_name_for_path(py_file: Path, *, prefix: str) -> str:
    safe_stem = _safe_module_segment(py_file.stem, fallback="plugin")
    digest = hashlib.sha1(str(py_file.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{safe_stem}_{digest}"


def _plugin_owner_id(
    source: Path | str,
    provenance: PluginProvenance | None,
) -> str:
    if provenance is None:
        source_name = Path(str(source)).stem
        return (
            "plugin:module:"
            f"{_safe_module_segment(source_name, fallback='plugin')}"
        )
    if provenance.kind == "entry_point":
        distribution = _safe_module_segment(
            provenance.distribution_name,
            fallback="unknown_distribution",
        )
        entry_point = _safe_module_segment(
            provenance.entry_point_name,
            fallback="plugin",
        )
        return f"plugin:entry_point:{distribution}:{entry_point}"
    if provenance.kind == "package":
        package_name = _safe_module_segment(
            provenance.package_name,
            fallback="package",
        )
        source_path = provenance.source_path
        package_root = provenance.package_root
        relative_path = Path(source_path.name if source_path else "plugin.py")
        if source_path is not None and package_root is not None:
            try:
                relative_path = source_path.relative_to(package_root)
            except ValueError:
                pass
        module_id = ".".join(
            _safe_module_segment(part, fallback="module")
            for part in relative_path.with_suffix("").parts
        )
        return f"plugin:package:{package_name}:{module_id}"
    source_path = provenance.source_path
    source_name = source_path.stem if source_path is not None else str(source)
    return (
        "plugin:file:"
        f"{_safe_module_segment(source_name, fallback='plugin')}"
    )


def _plugin_source_identity(provenance: PluginProvenance | None) -> str:
    if provenance is None or provenance.source_path is None:
        return ""
    return os.path.normcase(str(provenance.source_path.resolve()))


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
    manifest: PluginContractManifest | None = None,
    owner_id: str = "",
    owner_version: str = "",
) -> list[str]:
    normalized_descriptors = tuple(
        _descriptor_with_provenance(descriptor, provenance)
        for descriptor in descriptors
    )
    normalized_owner_id = owner_id or _plugin_owner_id(source, provenance)
    try:
        registry.register_plugin_bundle(
            manifest,
            normalized_descriptors,
            owner_id=normalized_owner_id,
            owner_version=owner_version,
            source_label=str(source),
            source_identity=_plugin_source_identity(provenance),
            replace_owner=True,
        )
    except (ValueError, TypeError, KeyError):
        logger.warning(
            "Plugin %s skipped [invalid_bundle]",
            _bounded_plugin_log_label(normalized_owner_id),
        )
        return []
    return [descriptor.spec.type_id for descriptor in normalized_descriptors]


def _register_plugin_backend(
    backend: PluginBackendDescriptor,
    registry: NodeRegistry,
    source: Path | str,
    *,
    provenance: PluginProvenance | None = None,
    module_manifest: PluginContractManifest | None = None,
) -> list[str]:
    availability = backend.get_availability()
    if not availability.is_available:
        logger.info(
            "Plugin backend %s skipped [unavailable]",
            _bounded_plugin_log_label(backend.plugin_id),
        )
        return []
    owner_version = (
        backend.addon_manifest.version
        if backend.addon_manifest is not None
        else ""
    )
    manifest = _merge_contract_manifests(
        module_manifest or PluginContractManifest(),
        backend.contract_manifest,
    )
    return _register_plugin_descriptors(
        backend.load_descriptors(),
        registry,
        source,
        provenance=backend.provenance if backend.provenance is not None else provenance,
        manifest=manifest,
        owner_id=backend.plugin_id,
        owner_version=owner_version,
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
                "Plugin backend %s failed [backend_load]",
                _bounded_plugin_log_label(backend.plugin_id),
            )
    return loaded


def _register_module_plugins(
    module: Any,
    registry: NodeRegistry,
    source: Path | str,
    *,
    provenance: PluginProvenance | None = None,
    preferred_descriptors: tuple[PluginDescriptor, ...] | None = None,
) -> list[str]:
    manifest = _module_plugin_contract_manifest(module)
    backends = _module_plugin_backends(module)
    if backends is not None:
        if len(backends) == 1:
            try:
                return _register_plugin_backend(
                    backends[0],
                    registry,
                    source,
                    provenance=provenance,
                    module_manifest=manifest,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Plugin backend %s failed [backend_load]",
                    _bounded_plugin_log_label(backends[0].plugin_id),
                )
                return []
        if manifest is not None and manifest != PluginContractManifest():
            raise TypeError(
                "Module-level plugin contracts require exactly one backend; "
                "multi-backend modules must declare contracts on each backend"
            )
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
            manifest=manifest,
        )
    return []


def _load_plugins_from_directory(directory: Path, registry: NodeRegistry) -> list[str]:
    """Import every descriptor-bearing .py file in *directory*."""
    loaded: list[str] = []

    for py_file in _public_plugin_files(directory):
        provenance = _file_plugin_provenance(py_file)
        log_label = _bounded_plugin_log_label(_plugin_owner_id(py_file, provenance))
        try:
            module = _load_module(_module_name_for_path(py_file, prefix="_ea_plugin"), py_file)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Plugin %s failed [module_import]",
                log_label,
            )
            continue

        try:
            loaded.extend(
                _register_module_plugins(
                    module,
                    registry,
                    py_file,
                    provenance=provenance,
                )
            )
        except TypeError:
            logger.warning(
                "Plugin %s skipped [invalid_api]",
                log_label,
            )
    return loaded


def _load_plugins_from_package_directory(
    package_dir: Path,
    registry: NodeRegistry,
    *,
    descriptor_overrides: dict[str, tuple[PluginDescriptor, ...]] | None = None,
) -> list[str]:
    """Import public descriptor modules from a package directory beneath the plugins root."""
    loaded: list[str] = []
    if not package_dir.is_dir():
        return loaded

    package_name = _module_name_for_path(package_dir / "__init__.py", prefix="_ea_plugin_pkg")
    init_file = package_dir / "__init__.py"
    init_provenance = _package_plugin_provenance(package_dir, init_file)
    init_log_label = _bounded_plugin_log_label(
        _plugin_owner_id(init_file, init_provenance)
    )

    if not init_file.is_file():
        logger.warning(
            "Plugin %s skipped [missing_init]",
            init_log_label,
        )
        return loaded

    try:
        package_module = _load_module(
            package_name,
            init_file,
            search_locations=[str(package_dir)],
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "Plugin %s failed [package_init]",
            init_log_label,
        )
        return loaded

    try:
        loaded.extend(
            _register_module_plugins(
                package_module,
                registry,
                init_file,
                provenance=init_provenance,
                preferred_descriptors=(descriptor_overrides or {}).get(init_file.name),
            )
        )
    except TypeError:
        logger.warning(
            "Plugin %s skipped [invalid_api]",
            init_log_label,
        )

    for py_file in _public_plugin_files(package_dir):
        module_name = f"{package_name}.{_safe_module_segment(py_file.stem, fallback='plugin')}"
        provenance = _package_plugin_provenance(package_dir, py_file)
        log_label = _bounded_plugin_log_label(_plugin_owner_id(py_file, provenance))
        try:
            module = _load_module(module_name, py_file)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Plugin %s failed [module_import]",
                log_label,
            )
            continue

        try:
            loaded.extend(
                _register_module_plugins(
                    module,
                    registry,
                    py_file,
                    provenance=provenance,
                    preferred_descriptors=(descriptor_overrides or {}).get(py_file.name),
                )
            )
        except TypeError:
            logger.warning(
                "Plugin %s skipped [invalid_api]",
                log_label,
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
        log_label = _bounded_plugin_log_label(_plugin_owner_id(ep.name, provenance))
        try:
            plugin_target = ep.load()
            loaded.extend(
                _register_module_plugins(
                    plugin_target,
                    registry,
                    ep.name,
                    provenance=provenance,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Plugin %s failed [entry_point_load]",
                log_label,
            )
    return loaded


def discover_addon_records(*, preferences_document: Any = None):
    """Compatibility shim; add-on record discovery is owned by ``ea_node_editor.addons``."""
    from ea_node_editor.addons.catalog import discover_addon_records as _discover_addon_records

    return _discover_addon_records(preferences_document=preferences_document)


def addon_record_by_id(addon_id: str, *, preferences_document: Any = None):
    """Compatibility shim; add-on record lookup is owned by ``ea_node_editor.addons``."""
    from ea_node_editor.addons.catalog import addon_record_by_id as _addon_record_by_id

    return _addon_record_by_id(addon_id, preferences_document=preferences_document)


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
