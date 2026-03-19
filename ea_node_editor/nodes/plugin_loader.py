"""Discovers and loads user-authored node plugins from disk and installed packages."""

from __future__ import annotations

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

from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodePlugin, NodeTypeSpec
from ea_node_editor.settings import plugins_dir

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "ea_node_editor.plugins"
_SAFE_MODULE_SEGMENT_RE = re.compile(r"[^0-9A-Za-z_]+")


def _is_node_plugin_class(obj: Any) -> bool:
    """Return True if *obj* looks like a NodePlugin class (not instance)."""
    if not isinstance(obj, type):
        return False
    if obj is NodePlugin:
        return False
    try:
        instance = obj()
        spec = instance.spec()
        return isinstance(spec, NodeTypeSpec) and callable(getattr(instance, "execute", None))
    except Exception:  # noqa: BLE001
        return False


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


def _register_plugin_classes(module: Any, registry: NodeRegistry, source: Path) -> list[str]:
    loaded: list[str] = []
    for attr_name in dir(module):
        obj = getattr(module, attr_name, None)
        if _is_node_plugin_class(obj):
            try:
                registry.register(obj)
                loaded.append(obj().spec().type_id)
            except (ValueError, TypeError, KeyError):
                logger.warning(
                    "Skipping invalid plugin class %s in %s",
                    attr_name,
                    source,
                    exc_info=True,
                )
    return loaded


def _load_plugins_from_directory(directory: Path, registry: NodeRegistry) -> list[str]:
    """Import every .py file in *directory* and register any NodePlugin classes found."""
    loaded: list[str] = []

    for py_file in _public_plugin_files(directory):
        try:
            module = _load_module(_module_name_for_path(py_file, prefix="_ea_plugin"), py_file)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load plugin file %s", py_file, exc_info=True)
            continue

        loaded.extend(_register_plugin_classes(module, registry, py_file))
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


def _load_plugins_from_package_directory(package_dir: Path, registry: NodeRegistry) -> list[str]:
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
            loaded.extend(_register_plugin_classes(package_module, registry, init_file))
    else:
        _create_namespace_package(package_name, package_dir)

    for py_file in _public_plugin_files(package_dir):
        module_name = f"{package_name}.{_safe_module_segment(py_file.stem, fallback='plugin')}"
        try:
            module = _load_module(module_name, py_file)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load plugin file %s", py_file, exc_info=True)
            continue

        loaded.extend(_register_plugin_classes(module, registry, py_file))
    return loaded


def _load_plugins_from_root(root_directory: Path, registry: NodeRegistry) -> list[str]:
    """Load public plugin modules from a plugin root and its package subdirectories."""
    loaded = _load_plugins_from_directory(root_directory, registry)
    for package_dir in _plugin_package_directories(root_directory):
        loaded.extend(_load_plugins_from_package_directory(package_dir, registry))
    return loaded


def _load_plugins_from_entry_points(registry: NodeRegistry) -> list[str]:
    """Load plugins registered via Python package entry points."""
    loaded: list[str] = []
    try:
        if sys.version_info >= (3, 12):
            from importlib.metadata import entry_points
            eps = entry_points(group=ENTRY_POINT_GROUP)
        else:
            from importlib.metadata import entry_points
            all_eps = entry_points()
            eps = all_eps.get(ENTRY_POINT_GROUP, [])
    except Exception:  # noqa: BLE001
        return loaded

    for ep in eps:
        try:
            plugin_class = ep.load()
            if _is_node_plugin_class(plugin_class):
                registry.register(plugin_class)
                loaded.append(plugin_class().spec().type_id)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load entry-point plugin %s", ep.name, exc_info=True)
    return loaded


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
