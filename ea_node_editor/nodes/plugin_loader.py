"""Discovers and loads user-authored node plugins from disk and installed packages."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodePlugin, NodeTypeSpec
from ea_node_editor.settings import plugins_dir

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "ea_node_editor.plugins"


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


def _load_plugins_from_directory(directory: Path, registry: NodeRegistry) -> list[str]:
    """Import every .py file in *directory* and register any NodePlugin classes found."""
    loaded: list[str] = []
    if not directory.is_dir():
        return loaded

    for py_file in sorted(directory.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"_ea_plugin_{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to load plugin file %s", py_file, exc_info=True)
            continue

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
                        py_file,
                        exc_info=True,
                    )
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

    loaded.extend(_load_plugins_from_directory(plugins_dir(), registry))

    for directory in extra_dirs or []:
        loaded.extend(_load_plugins_from_directory(directory, registry))

    loaded.extend(_load_plugins_from_entry_points(registry))

    if loaded:
        logger.info("Loaded %d plugin node(s): %s", len(loaded), ", ".join(loaded))
    return loaded
