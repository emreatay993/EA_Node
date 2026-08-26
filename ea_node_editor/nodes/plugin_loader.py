# Purpose: Discover function plugins statically and register trusted add-on backends.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_plugin_loader.py

from __future__ import annotations

import ast
import hashlib
import importlib.machinery
import importlib.util
import json
import logging
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any

from ea_node_editor.nodes.function_plugin import (
    INTERNAL_BUILTIN_FUNCTION_OWNER_ID,
    PluginBundleRef,
    PythonFunctionRef,
    plugin_fingerprint as _function_plugin_fingerprint,
)
from ea_node_editor.nodes.plugin_contracts import (
    PluginBackendDescriptor,
    PluginContractManifest,
    PluginDescriptor,
    PluginProvenance,
)
from ea_node_editor.nodes.plugin_declaration import (
    PluginDeclarationError,
    PythonFunctionDeclaration,
    discover_plugin_declarations,
)
from ea_node_editor.nodes.plugin_generation import (
    MANIFEST_FILENAME,
    PLUGIN_ASSET_LIMIT,
    PLUGIN_ASSET_SUFFIXES,
    PLUGIN_MANIFEST_LIMIT,
    PLUGIN_MEMBER_LIMIT,
    PLUGIN_SOURCE_LIMIT,
    PLUGIN_TOTAL_LIMIT,
    SCHEMA_1_UNSUPPORTED_MESSAGE,
    _is_reparse_point,
    canonical_bundle_digest,
    canonical_manifest_bytes,
    materialize_plugin_generation,
    validate_plugin_regular_file,
    validated_plugin_member_path,
)
from ea_node_editor.nodes.registry import NodeRegistry, PythonFunctionEntry
from ea_node_editor.settings import plugin_generations_dir, plugins_dir

logger = logging.getLogger(__name__)

_SAFE_SEGMENT = re.compile(r"[^0-9A-Za-z_]+")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PLUGIN_LOG_LABEL_LENGTH = 256
_ROOT_ENTRY_LIMIT = 512
_PACKAGE_PATH_ENTRY_LIMIT = 256
_REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "name",
    "version",
    "modules",
    "sources",
    "assets",
    "nodes",
}
_ALLOWED_MANIFEST_FIELDS = _REQUIRED_MANIFEST_FIELDS | {"author", "description"}
_BUNDLED_MODULE_ROOTS = frozenset(
    {
        "OCP",
        "PyQt6",
        "ansys",
        "corex",
        "duckdb",
        "ea_node_editor",
        "h5py",
        "imageio_ffmpeg",
        "llvmlite",
        "matplotlib",
        "numba",
        "numpy",
        "openpyxl",
        "pandas",
        "paramiko",
        "polars",
        "psutil",
        "pyarrow",
        "pyqtgraph",
        "pyvista",
        "pyvistaqt",
        "qtpy",
        "scipy",
        "tables",
        "vtkmodules",
        "xy",
    }
)


@dataclass(frozen=True, slots=True)
class PluginDiscoveryResult:
    type_ids: tuple[str, ...]
    bundles: tuple[PluginBundleRef, ...]
    plugin_fingerprint: str


@dataclass(frozen=True, slots=True)
class _PreparedBundle:
    owner_id: str
    version: str
    manifest: dict[str, object]
    members: dict[str, bytes]
    declarations: tuple[tuple[str, PythonFunctionDeclaration], ...]
    unavailable_reason: str
    log_label: str
    source_root: Path
    package_name: str = ""


def _safe_segment(value: object, *, fallback: str) -> str:
    segment = _SAFE_SEGMENT.sub("_", str(value)).strip("_")
    if not segment:
        return fallback
    return f"_{segment}" if segment[0].isdigit() else segment


def _bounded_plugin_log_label(value: object) -> str:
    text = str(value or "")
    if (
        text
        and len(text) <= _PLUGIN_LOG_LABEL_LENGTH
        and all(character.isalnum() or character in "._:@+-" for character in text)
    ):
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"plugin:opaque:{digest}"


def _trimmed(field_name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError(f"{field_name} must be a trimmed string")
    if not value and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _sha256(field_name: str, value: object) -> str:
    text = _trimmed(field_name, value)
    if _SHA256.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _source_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bounded(path: Path, *, limit: int, label: str) -> bytes:
    try:
        if path.stat().st_size > limit:
            raise ValueError(f"{label} is too large")
        with path.open("rb") as stream:
            payload = stream.read(limit + 1)
    except OSError as exc:
        raise ValueError(f"{label} cannot be read") from exc
    if len(payload) > limit:
        raise ValueError(f"{label} is too large")
    return payload


def _manifest_records(
    manifest: Mapping[str, object],
    field_name: str,
    *,
    asset: bool,
) -> tuple[tuple[str, str], ...]:
    raw_records = manifest.get(field_name)
    if not isinstance(raw_records, list):
        raise ValueError(f"Manifest {field_name} must be a list")
    records: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_record in raw_records:
        if not isinstance(raw_record, dict) or set(raw_record) != {"path", "sha256"}:
            raise ValueError(f"Manifest {field_name} entries require path and sha256")
        path = validated_plugin_member_path(
            raw_record["path"],
            root_python=not asset,
        )
        if asset and PurePosixPath(path).suffix.lower() not in PLUGIN_ASSET_SUFFIXES:
            raise ValueError(f"Unsupported plugin asset: {path}")
        folded = path.casefold()
        if folded in seen:
            raise ValueError(f"Manifest {field_name} paths must be unique")
        seen.add(folded)
        records.append((path, _sha256(f"{field_name} sha256", raw_record["sha256"])))
    return tuple(records)


def _read_package_member(package_dir: Path, relative_path: str, *, limit: int) -> bytes:
    target = package_dir / relative_path
    cursor = package_dir
    for part in PurePosixPath(relative_path).parts:
        cursor /= part
        if _is_reparse_point(cursor):
            raise ValueError("Plugin package may not contain path aliases")
    if not target.is_file():
        raise ValueError(f"Declared package member is unavailable: {relative_path}")
    validate_plugin_regular_file(target)
    try:
        target.resolve().relative_to(package_dir.resolve())
    except ValueError as exc:
        raise ValueError("Declared package member escapes the package root") from exc
    return _read_bounded(
        target,
        limit=limit,
        label=f"Declared package member {relative_path}",
    )


def _package_manifest(package_dir: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    manifest_path = package_dir / MANIFEST_FILENAME
    if not manifest_path.is_file() or _is_reparse_point(manifest_path):
        raise ValueError(f"Installed plugin package requires {MANIFEST_FILENAME}")
    validate_plugin_regular_file(manifest_path)
    raw_manifest = _read_bounded(
        manifest_path,
        limit=PLUGIN_MANIFEST_LIMIT,
        label="Plugin package manifest",
    )
    try:
        manifest = json.loads(raw_manifest)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Plugin package manifest is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Plugin package manifest must be a JSON object")
    schema_version = manifest.get("schema_version")
    if schema_version is None or (
        type(schema_version) is int and schema_version == 1
    ):
        raise ValueError(SCHEMA_1_UNSUPPORTED_MESSAGE)
    if type(schema_version) is not int or schema_version != 2:
        raise ValueError("Only node package schema 2 is supported")
    if set(manifest) - _ALLOWED_MANIFEST_FIELDS:
        raise ValueError("Plugin package manifest contains unknown fields")
    if _REQUIRED_MANIFEST_FIELDS - set(manifest):
        raise ValueError("Plugin package manifest is missing required fields")
    name = validated_plugin_member_path(_trimmed("Manifest name", manifest["name"]))
    if len(PurePosixPath(name).parts) != 1 or name.startswith((".", "_")):
        raise ValueError("Manifest name must be a safe directory name")
    if package_dir.name != name:
        raise ValueError("Installed package directory must match manifest name")
    _trimmed("Manifest version", manifest["version"])
    for optional_field in ("author", "description"):
        if optional_field in manifest:
            _trimmed(optional_field, manifest[optional_field], allow_empty=True)

    raw_modules = manifest["modules"]
    if not isinstance(raw_modules, list) or not raw_modules:
        raise ValueError("Manifest modules must be a non-empty list")
    modules = tuple(
        validated_plugin_member_path(value, root_python=True)
        for value in raw_modules
    )
    if len({module.casefold() for module in modules}) != len(modules):
        raise ValueError("Manifest modules must be unique")
    sources = _manifest_records(manifest, "sources", asset=False)
    assets = _manifest_records(manifest, "assets", asset=True)
    source_paths = {path for path, _digest_value in sources}
    if not set(modules) <= source_paths:
        raise ValueError("Manifest modules must be declared sources")
    if len(sources) + len(assets) + 1 > PLUGIN_MEMBER_LIMIT:
        raise ValueError("Plugin package contains too many members")

    members: dict[str, bytes] = {}
    asset_paths = {item[0] for item in assets}
    expanded_size = len(raw_manifest)
    if expanded_size > PLUGIN_TOTAL_LIMIT:
        raise ValueError("Plugin package expanded size is too large")
    for path, expected_digest in (*sources, *assets):
        try:
            declared_size = (package_dir / path).stat().st_size
        except OSError as exc:
            raise ValueError(f"Declared package member is unavailable: {path}") from exc
        if expanded_size + declared_size > PLUGIN_TOTAL_LIMIT:
            raise ValueError("Plugin package expanded size is too large")
        payload = _read_package_member(
            package_dir,
            path,
            limit=PLUGIN_ASSET_LIMIT if path in asset_paths else PLUGIN_SOURCE_LIMIT,
        )
        if expanded_size + len(payload) > PLUGIN_TOTAL_LIMIT:
            raise ValueError("Plugin package expanded size is too large")
        if _source_digest(payload) != expected_digest:
            raise ValueError(f"Plugin package hash mismatch: {path}")
        members[path] = payload
        expanded_size += len(payload)

    declared_files = {MANIFEST_FILENAME, *members}
    actual_files: set[str] = set()
    for index, path in enumerate(package_dir.rglob("*")):
        if index >= _PACKAGE_PATH_ENTRY_LIMIT:
            raise ValueError("Plugin package contains too many path entries")
        if _is_reparse_point(path):
            raise ValueError("Plugin package may not contain symlinks")
        if path.is_file():
            actual_files.add(path.relative_to(package_dir).as_posix())
    if actual_files != declared_files:
        raise ValueError("Plugin package contains undeclared members")
    return dict(manifest), members


def _module_declarations(
    manifest: Mapping[str, object],
    members: Mapping[str, bytes],
    *,
    filename_prefix: str,
    owner_id: str = "",
    allow_internal_metadata: bool = False,
) -> tuple[tuple[str, PythonFunctionDeclaration], ...]:
    declarations: list[tuple[str, PythonFunctionDeclaration]] = []
    for module_path in manifest["modules"]:  # type: ignore[union-attr]
        path = str(module_path)
        try:
            source = members[path].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Plugin source is not UTF-8: {path}") from exc
        declarations.extend(
            (path, declaration)
            for declaration in discover_plugin_declarations(
                source,
                filename=f"{filename_prefix}:{path}",
                allow_reserved_ids=(
                    owner_id == INTERNAL_BUILTIN_FUNCTION_OWNER_ID
                    or allow_internal_metadata
                ),
                owner_id=owner_id,
                allow_internal_metadata=allow_internal_metadata,
            )
        )
    return tuple(declarations)


def _node_inventory(
    declarations: Sequence[tuple[str, PythonFunctionDeclaration]],
) -> list[dict[str, str]]:
    return [
        {
            "id": declaration.spec.type_id,
            "module": module_path,
            "function": declaration.function_name,
        }
        for module_path, declaration in declarations
    ]


def _validated_manifest_nodes(
    manifest: Mapping[str, object],
) -> tuple[tuple[str, str, str], ...]:
    raw_nodes = manifest.get("nodes")
    if not isinstance(raw_nodes, list):
        raise ValueError("Manifest nodes must be a list")
    nodes: list[tuple[str, str, str]] = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict) or set(raw_node) != {
            "id",
            "module",
            "function",
        }:
            raise ValueError("Manifest node entries require id, module, and function")
        nodes.append(
            (
                _trimmed("node id", raw_node["id"]),
                validated_plugin_member_path(raw_node["module"], root_python=True),
                _trimmed("node function", raw_node["function"]),
            )
        )
    if len(nodes) != len(set(nodes)):
        raise ValueError("Manifest node entries must be unique")
    return tuple(nodes)


def validated_generation_declarations(
    manifest: Mapping[str, object],
    members: Mapping[str, bytes],
    *,
    filename_prefix: str,
    owner_id: str = "",
    allow_internal_metadata: bool = False,
) -> tuple[tuple[str, PythonFunctionDeclaration], ...]:
    declarations = _module_declarations(
        manifest,
        members,
        filename_prefix=filename_prefix,
        owner_id=owner_id,
        allow_internal_metadata=bool(allow_internal_metadata),
    )
    type_ids = [declaration.spec.type_id for _path, declaration in declarations]
    if len(type_ids) != len(set(type_ids)):
        raise ValueError("Plugin bundle contains duplicate node ids")
    discovered = {
        (item["id"], item["module"], item["function"])
        for item in _node_inventory(declarations)
    }
    if discovered != set(_validated_manifest_nodes(manifest)):
        raise ValueError("Manifest nodes do not match static declarations")
    return declarations


def _pathfinder_module_available(module_name: str) -> bool:
    parts = module_name.split(".")
    try:
        spec = importlib.machinery.PathFinder.find_spec(parts[0])
        qualified_name = parts[0]
        for part in parts[1:]:
            if spec is None or spec.submodule_search_locations is None:
                return False
            qualified_name = f"{qualified_name}.{part}"
            spec = importlib.machinery.PathFinder.find_spec(
                qualified_name,
                spec.submodule_search_locations,
            )
        return spec is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _bundled_module_available(module_name: str) -> bool:
    if module_name in {"corex", "__future__"}:
        return True
    root = module_name.partition(".")[0]
    if root in sys.builtin_module_names:
        return module_name == root
    if root in getattr(sys, "stdlib_module_names", ()):
        return module_name == root or _pathfinder_module_available(module_name)
    if root not in _BUNDLED_MODULE_ROOTS:
        return False
    if getattr(sys, "frozen", False):
        try:
            return importlib.util.find_spec(module_name) is not None
        except (ImportError, AttributeError, ValueError):
            return False
    return _pathfinder_module_available(module_name)


def _missing_imports(
    members: Mapping[str, bytes],
    source_paths: set[str],
) -> tuple[str, ...]:
    source_stems = {PurePosixPath(path).stem for path in source_paths}
    missing: set[str] = set()
    for source_path in sorted(source_paths):
        try:
            tree = ast.parse(members[source_path].decode("utf-8"), filename=source_path)
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise ValueError(f"Plugin source cannot be parsed: {source_path}") from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.partition(".")[0]
                    bundled_source = alias.name == root and root in source_stems
                    if not bundled_source and not _bundled_module_available(alias.name):
                        missing.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if node.level != 1:
                        missing.add(node.module or node.names[0].name)
                        continue
                    if node.module:
                        relative_source = f"{node.module.replace('.', '/')}.py"
                        if relative_source not in source_paths:
                            missing.add(node.module)
                    else:
                        for alias in node.names:
                            relative_source = f"{alias.name}.py"
                            if relative_source not in source_paths:
                                missing.add(alias.name)
                    continue
                root = (node.module or "").partition(".")[0]
                module_name = node.module or ""
                bundled_source = module_name == root and root in source_stems
                if (
                    module_name
                    and not bundled_source
                    and not _bundled_module_available(module_name)
                ):
                    missing.add(module_name)
    return tuple(sorted(missing))


def _prepare_loose_file(source_path: Path) -> _PreparedBundle | None:
    if _is_reparse_point(source_path) or not source_path.is_file():
        raise ValueError("Loose plugin source must be a regular file")
    payload = _read_bounded(
        source_path,
        limit=PLUGIN_SOURCE_LIMIT,
        label="Loose plugin source",
    )
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Loose plugin source must be UTF-8") from exc
    declarations = discover_plugin_declarations(source, filename=source_path.name)
    if not declarations:
        return None
    if any(declaration.spec.icon for declaration in declarations):
        raise ValueError("Loose plugins cannot declare custom icons; export a package")
    name = _safe_segment(source_path.stem, fallback="plugin")
    owner_id = f"plugin:file:{name}"
    module_path = source_path.name
    inventory = _node_inventory(tuple((module_path, item) for item in declarations))
    manifest: dict[str, object] = {
        "schema_version": 2,
        "name": name,
        "version": "0.0.0",
        "author": "",
        "description": "",
        "modules": [module_path],
        "sources": [{"path": module_path, "sha256": _source_digest(payload)}],
        "assets": [],
        "nodes": inventory,
    }
    members = {module_path: payload}
    missing = _missing_imports(members, {module_path})
    unavailable_reason = (
        f"{missing[0]} is not included in this COREX bundle." if missing else ""
    )
    return _PreparedBundle(
        owner_id=owner_id,
        version="0.0.0",
        manifest=manifest,
        members=members,
        declarations=tuple((module_path, item) for item in declarations),
        unavailable_reason=unavailable_reason,
        log_label=_bounded_plugin_log_label(owner_id),
        source_root=source_path.parent.resolve(),
    )


def _prepare_package(package_dir: Path) -> _PreparedBundle:
    if _is_reparse_point(package_dir) or not package_dir.is_dir():
        raise ValueError("Installed plugin package must be a regular directory")
    manifest, members = _package_manifest(package_dir)
    owner_id = f"plugin:package:{_safe_segment(manifest['name'], fallback='package')}"
    declarations = validated_generation_declarations(
        manifest,
        members,
        filename_prefix=str(manifest["name"]),
        owner_id=owner_id,
    )
    asset_paths = {
        str(record["path"])
        for record in manifest["assets"]  # type: ignore[union-attr]
    }
    for _module_path, declaration in declarations:
        icon = declaration.spec.icon
        if not icon:
            continue
        try:
            icon_path = validated_plugin_member_path(icon)
        except ValueError as exc:
            raise ValueError(f"Plugin node icon path is invalid: {icon}") from exc
        if icon_path not in asset_paths:
            raise ValueError(f"Plugin node icon is not a declared asset: {icon_path}")
    source_paths = {str(record["path"]) for record in manifest["sources"]}  # type: ignore[index]
    missing = _missing_imports(members, source_paths)
    unavailable_reason = (
        f"{missing[0]} is not included in this COREX bundle." if missing else ""
    )
    return _PreparedBundle(
        owner_id=owner_id,
        version=str(manifest["version"]),
        manifest=manifest,
        members=members,
        declarations=declarations,
        unavailable_reason=unavailable_reason,
        log_label=_bounded_plugin_log_label(owner_id),
        source_root=package_dir.resolve(),
        package_name=str(manifest["name"]),
    )


def _prepare_backend_function_bundle(
    backend: PluginBackendDescriptor,
) -> _PreparedBundle:
    load_sources = backend.load_function_sources
    if load_sources is None:
        raise ValueError("Plugin backend does not declare function sources")
    raw_sources = load_sources()
    if not isinstance(raw_sources, tuple) or not raw_sources:
        raise TypeError("Plugin backend function sources must be a non-empty tuple")
    if len(raw_sources) + 1 > PLUGIN_MEMBER_LIMIT:
        raise ValueError("Plugin backend function bundle contains too many members")

    members: dict[str, bytes] = {}
    seen_paths: set[str] = set()
    module_names: list[str] = []
    for index, raw_item in enumerate(raw_sources):
        if not isinstance(raw_item, tuple) or len(raw_item) != 2:
            raise TypeError(
                f"Plugin backend function source {index} must be a path/source tuple"
            )
        raw_path, source = raw_item
        path = validated_plugin_member_path(raw_path, root_python=True)
        folded_path = path.casefold()
        if folded_path in seen_paths:
            raise ValueError("Plugin backend function source paths must be unique")
        if not isinstance(source, str):
            raise TypeError("Plugin backend function source must be a string")
        payload = source.encode("utf-8")
        if len(payload) > PLUGIN_SOURCE_LIMIT:
            raise ValueError("Plugin backend function source is too large")
        seen_paths.add(folded_path)
        module_names.append(path)
        members[path] = payload

    package_name = _safe_segment(backend.plugin_id, fallback="addon")
    version = backend.addon_manifest.version if backend.addon_manifest else "0.0.0"
    manifest: dict[str, object] = {
        "schema_version": 2,
        "name": package_name,
        "version": version,
        "author": "",
        "description": "",
        "modules": module_names,
        "sources": [
            {"path": path, "sha256": _source_digest(members[path])}
            for path in module_names
        ],
        "assets": [],
        "nodes": [],
    }
    declarations = _module_declarations(
        manifest,
        members,
        filename_prefix=backend.plugin_id,
        owner_id=backend.plugin_id,
        allow_internal_metadata=True,
    )
    parsed_type_ids = tuple(
        declaration.spec.type_id for _path, declaration in declarations
    )
    if parsed_type_ids != backend.function_type_ids:
        raise ValueError(
            "Plugin backend function type ids do not match static declarations"
        )
    manifest["nodes"] = _node_inventory(declarations)
    manifest_size = len(canonical_manifest_bytes(manifest))
    if manifest_size > PLUGIN_MANIFEST_LIMIT:
        raise ValueError("Plugin backend function manifest is too large")
    if manifest_size + sum(map(len, members.values())) > PLUGIN_TOTAL_LIMIT:
        raise ValueError("Plugin backend function bundle is too large")
    missing = _missing_imports(members, set(module_names))
    return _PreparedBundle(
        owner_id=backend.plugin_id,
        version=version,
        manifest=manifest,
        members=members,
        declarations=declarations,
        unavailable_reason=(
            f"{missing[0]} is not included in this COREX bundle." if missing else ""
        ),
        log_label=_bounded_plugin_log_label(backend.plugin_id),
        source_root=Path(__file__).parent,
        package_name=package_name,
    )


def _function_refs(
    prepared: _PreparedBundle,
    bundle_digest: str,
) -> tuple[PythonFunctionRef, ...]:
    return tuple(
        PythonFunctionRef(
            bundle_id=prepared.owner_id,
            bundle_digest=bundle_digest,
            module_relative_path=module_path,
            function_name=declaration.function_name,
            source_digest=_source_digest(prepared.members[module_path]),
            is_async=declaration.is_async,
        )
        for module_path, declaration in prepared.declarations
    )


def _validate_registration(prepared: _PreparedBundle, registry: NodeRegistry) -> None:
    type_ids = [declaration.spec.type_id for _path, declaration in prepared.declarations]
    if len(type_ids) != len(set(type_ids)):
        raise ValueError("Plugin bundle contains duplicate node ids")
    if any(registry.spec_or_none(type_id) is not None for type_id in type_ids):
        raise ValueError("Plugin bundle conflicts with an active node id")
    if any(
        bundle.owner_id == prepared.owner_id
        for bundle in registry.plugin_bundle_refs()
    ):
        raise ValueError("Plugin bundle owner is already active")
    if any(
        entry.owner_id == prepared.owner_id
        for entry in (registry.entry_or_none(spec.type_id) for spec in registry.all_specs())
        if entry is not None
    ):
        raise ValueError("Plugin bundle owner is already active")
    for _module_path, declaration in prepared.declarations:
        registry.validate_spec(declaration.spec)


def _register_prepared_bundle(
    prepared: _PreparedBundle,
    registry: NodeRegistry,
    generation_root: Path,
) -> tuple[PluginBundleRef, tuple[str, ...]]:
    _validate_registration(prepared, registry)
    bundle_ref, function_entries = _materialize_prepared_bundle(
        prepared,
        generation_root,
    )
    for entry in function_entries:
        registry.register_python_function(
            entry.spec,
            entry.function_ref,
            provenance=entry.provenance,
            owner_id=entry.owner_id,
            unavailable_reason=entry.unavailable_reason,
        )
    return bundle_ref, tuple(entry.spec.type_id for entry in function_entries)


def _materialize_prepared_bundle(
    prepared: _PreparedBundle,
    generation_root: Path,
    *,
    provenance_override: PluginProvenance | None = None,
) -> tuple[PluginBundleRef, tuple[PythonFunctionEntry, ...]]:
    bundle_digest = canonical_bundle_digest(prepared.manifest, prepared.members)
    function_refs = _function_refs(prepared, bundle_digest)
    generation = materialize_plugin_generation(
        generation_root,
        bundle_digest=bundle_digest,
        manifest=prepared.manifest,
        members=prepared.members,
    )
    bundle_ref = PluginBundleRef(
        owner_id=prepared.owner_id,
        version=prepared.version,
        generation_id=bundle_digest,
        bundle_digest=bundle_digest,
        approved_generation_root=str(generation),
        functions=function_refs,
        unavailable_reason=prepared.unavailable_reason,
    )
    entries: list[PythonFunctionEntry] = []
    for (_module_path, declaration), function_ref in zip(
        prepared.declarations, function_refs, strict=True
    ):
        if provenance_override is not None:
            provenance = provenance_override
        elif prepared.owner_id == INTERNAL_BUILTIN_FUNCTION_OWNER_ID:
            provenance = None
        elif prepared.package_name:
            provenance = PluginProvenance(
                kind="package",
                source_path=generation / function_ref.module_relative_path,
                package_root=generation,
                package_name=prepared.package_name,
            )
        else:
            provenance = PluginProvenance(
                kind="file",
                source_path=prepared.source_root / function_ref.module_relative_path,
            )
        entries.append(
            PythonFunctionEntry(
                spec=declaration.spec,
                function_ref=function_ref,
                provenance=provenance,
                owner_id=prepared.owner_id,
                unavailable_reason=prepared.unavailable_reason,
            )
        )
    return bundle_ref, tuple(entries)


def plugin_fingerprint(
    registry: NodeRegistry,
    bundles: Sequence[PluginBundleRef],
) -> str:
    entries = tuple(
        (spec, function_ref)
        for spec in registry.all_specs()
        if (function_ref := registry.python_function_ref_or_none(spec.type_id))
        is not None
    )
    return _function_plugin_fingerprint(entries, bundles)


def register_internal_builtin_functions(
    registry: NodeRegistry,
    *,
    generation_root: Path,
) -> PluginDiscoveryResult:
    """Register packaged inert source as one reserved function bundle."""

    from ea_node_editor.nodes.builtin_functions import source_modules

    source_items = source_modules()
    module_names = [name for name, _source in source_items]
    if len(module_names) != len({name.casefold() for name in module_names}):
        raise ValueError("Internal built-in source module names must be unique")
    members: dict[str, bytes] = {}
    for raw_path, source in source_items:
        path = validated_plugin_member_path(raw_path, root_python=True)
        if not isinstance(source, str):
            raise TypeError("Internal built-in function source must be a string")
        payload = source.encode("utf-8")
        if len(payload) > PLUGIN_SOURCE_LIMIT:
            raise ValueError("Internal built-in function source is too large")
        members[path] = payload
    manifest: dict[str, object] = {
        "schema_version": 2,
        "name": "corex_builtin_functions",
        "version": "1.0.0",
        "author": "COREX",
        "description": "Ordinary built-in nodes implemented with the function SDK.",
        "modules": module_names,
        "sources": [
            {"path": path, "sha256": _source_digest(members[path])}
            for path in module_names
        ],
        "assets": [],
        "nodes": [],
    }
    declarations = _module_declarations(
        manifest,
        members,
        filename_prefix=INTERNAL_BUILTIN_FUNCTION_OWNER_ID,
        owner_id=INTERNAL_BUILTIN_FUNCTION_OWNER_ID,
    )
    manifest["nodes"] = _node_inventory(declarations)
    missing = _missing_imports(members, set(module_names))
    prepared = _PreparedBundle(
        owner_id=INTERNAL_BUILTIN_FUNCTION_OWNER_ID,
        version="1.0.0",
        manifest=manifest,
        members=members,
        declarations=declarations,
        unavailable_reason=(
            f"{missing[0]} is not included in this COREX bundle." if missing else ""
        ),
        log_label=INTERNAL_BUILTIN_FUNCTION_OWNER_ID,
        source_root=Path(__file__).parent / "builtin_functions",
    )
    bundle, type_ids = _register_prepared_bundle(
        prepared,
        registry,
        Path(generation_root),
    )
    bundles = (*registry.plugin_bundle_refs(), bundle)
    fingerprint = plugin_fingerprint(registry, bundles)
    registry.set_python_plugin_catalog(bundles, plugin_fingerprint=fingerprint)
    return PluginDiscoveryResult(type_ids, bundles, fingerprint)


def _root_entries(root: Path) -> tuple[Path, ...]:
    entries: list[Path] = []
    for index, entry in enumerate(root.iterdir()):
        if index >= _ROOT_ENTRY_LIMIT:
            raise ValueError("Plugin root contains too many entries")
        entries.append(entry)
    return tuple(sorted(entries, key=lambda path: path.name.casefold()))


def _prepared_static_bundles(
    roots: Sequence[Path],
    *,
    strict: bool,
    staged_package_root: Path | None,
) -> tuple[_PreparedBundle, ...]:
    staged = (
        _prepare_package(Path(staged_package_root))
        if staged_package_root is not None
        else None
    )
    replacement_name = staged.package_name if staged is not None else ""
    replacement_root = (
        Path(roots[0]).resolve() if replacement_name and roots else None
    )
    candidates: list[_PreparedBundle] = []
    seen_roots: set[Path] = set()
    for raw_root in roots:
        configured_root = Path(raw_root)
        if _is_reparse_point(configured_root):
            if strict:
                raise ValueError("Plugin root must not be a path alias")
            logger.warning("Plugin root skipped [symlink_root]")
            continue
        root = configured_root.resolve()
        if root in seen_roots:
            continue
        seen_roots.add(root)
        if not root.is_dir():
            continue
        try:
            entries = _root_entries(root)
        except (OSError, ValueError):
            if strict:
                raise ValueError("Plugin root is invalid") from None
            logger.warning("Plugin root skipped [invalid_root]")
            continue
        for source_path in entries:
            if (
                source_path.suffix != ".py"
                or source_path.name.startswith("_")
                or _is_reparse_point(source_path)
                or not source_path.is_file()
            ):
                continue
            try:
                prepared = _prepare_loose_file(source_path)
                if prepared is not None:
                    candidates.append(prepared)
            except OSError:
                if strict:
                    raise ValueError("Loose plugin source cannot be read") from None
                logger.warning(
                    "Plugin %s skipped [invalid_bundle]",
                    _bounded_plugin_log_label(f"plugin:file:{source_path.stem}"),
                )
            except (ValueError, PluginDeclarationError):
                if strict:
                    raise
                logger.warning(
                    "Plugin %s skipped [invalid_bundle]",
                    _bounded_plugin_log_label(f"plugin:file:{source_path.stem}"),
                )
        for package_dir in entries:
            if (
                not package_dir.is_dir()
                or _is_reparse_point(package_dir)
                or package_dir.name.startswith((".", "_"))
                or not (package_dir / MANIFEST_FILENAME).exists()
            ):
                continue
            if (
                root == replacement_root
                and replacement_name
                and package_dir.name == replacement_name
            ):
                continue
            try:
                candidates.append(_prepare_package(package_dir))
            except OSError:
                if strict:
                    raise ValueError("Plugin package cannot be read") from None
                logger.warning(
                    "Plugin %s skipped [invalid_bundle]",
                    _bounded_plugin_log_label(f"plugin:package:{package_dir.name}"),
                )
            except (ValueError, PluginDeclarationError) as exc:
                if strict:
                    raise
                label = _bounded_plugin_log_label(
                    f"plugin:package:{package_dir.name}"
                )
                if str(exc) == SCHEMA_1_UNSUPPORTED_MESSAGE:
                    logger.warning(
                        "Plugin %s skipped [schema_1]: %s",
                        label,
                        SCHEMA_1_UNSUPPORTED_MESSAGE,
                    )
                else:
                    logger.warning("Plugin %s skipped [invalid_bundle]", label)
    if staged is not None:
        candidates.append(staged)
    return tuple(candidates)


def _discover_static_plugins(
    registry: NodeRegistry,
    *,
    roots: Sequence[Path],
    generation_root: Path,
    strict: bool,
    staged_package_root: Path | None = None,
) -> PluginDiscoveryResult:
    loaded: list[str] = []
    new_bundles: list[PluginBundleRef] = []
    candidates = _prepared_static_bundles(
        roots,
        strict=strict,
        staged_package_root=staged_package_root,
    )
    for prepared in candidates:
        try:
            bundle, type_ids = _register_prepared_bundle(
                prepared,
                registry,
                Path(generation_root),
            )
        except (OSError, TypeError, ValueError):
            if strict:
                raise
            logger.warning(
                "Plugin %s skipped [invalid_bundle]",
                prepared.log_label,
            )
            continue
        new_bundles.append(bundle)
        loaded.extend(type_ids)

    bundles = (*registry.plugin_bundle_refs(), *new_bundles)
    fingerprint = plugin_fingerprint(registry, bundles)
    registry.set_python_plugin_catalog(tuple(bundles), plugin_fingerprint=fingerprint)
    return PluginDiscoveryResult(tuple(loaded), tuple(bundles), fingerprint)


def discover_static_plugins(
    registry: NodeRegistry,
    *,
    roots: Sequence[Path],
    generation_root: Path,
) -> PluginDiscoveryResult:
    return _discover_static_plugins(
        registry,
        roots=roots,
        generation_root=generation_root,
        strict=False,
    )


def discover_static_plugin_candidate(
    registry: NodeRegistry,
    *,
    roots: Sequence[Path],
    generation_root: Path,
    staged_package_root: Path | None = None,
) -> PluginDiscoveryResult:
    """Build one fail-closed public-plugin candidate without executing source."""

    return _discover_static_plugins(
        registry,
        roots=roots,
        generation_root=generation_root,
        strict=True,
        staged_package_root=staged_package_root,
    )


def _discover_configured_static_plugins(
    registry: NodeRegistry,
    extra_dirs: list[Path] | None = None,
    *,
    generation_root: Path | None = None,
) -> list[str]:
    result = discover_static_plugins(
        registry,
        roots=(plugins_dir(), *(extra_dirs or ())),
        generation_root=generation_root or plugin_generations_dir(),
    )
    if result.type_ids:
        logger.info(
            "Loaded %d plugin node(s): %s",
            len(result.type_ids),
            ", ".join(result.type_ids),
        )
    return list(result.type_ids)


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
            item for manifest in manifests for item in manifest.surface_capabilities
        ),
        data_type_families=tuple(
            item for manifest in manifests for item in manifest.data_type_families
        ),
        data_types=tuple(
            item for manifest in manifests for item in manifest.data_types
        ),
        data_conversions=tuple(
            item for manifest in manifests for item in manifest.data_conversions
        ),
    )


def _trusted_owner_id(source: Path | str, provenance: PluginProvenance | None) -> str:
    if provenance is not None and provenance.kind == "package":
        return f"plugin:package:{_safe_segment(provenance.package_name, fallback='package')}"
    source_path = provenance.source_path if provenance is not None else None
    source_name = source_path.stem if source_path is not None else Path(str(source)).stem
    return f"plugin:file:{_safe_segment(source_name, fallback='plugin')}"


def _plugin_source_identity(provenance: PluginProvenance | None) -> str:
    if provenance is None or provenance.source_path is None:
        return ""
    return os.path.normcase(str(provenance.source_path.resolve()))


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
        descriptor
        if provenance is None or descriptor.provenance == provenance
        else replace(descriptor, provenance=provenance)
        for descriptor in descriptors
    )
    normalized_owner_id = owner_id or _trusted_owner_id(source, provenance)
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
    except (KeyError, TypeError, ValueError):
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
    generation_root: Path,
) -> list[str]:
    availability = backend.get_availability()
    if not availability.is_available:
        logger.info(
            "Plugin backend %s skipped [unavailable]",
            _bounded_plugin_log_label(backend.plugin_id),
        )
        return []
    owner_version = backend.addon_manifest.version if backend.addon_manifest else ""
    manifest = _merge_contract_manifests(backend.contract_manifest)
    descriptors = backend.load_descriptors()
    if backend.load_function_sources is not None:
        prepared = _prepare_backend_function_bundle(backend)
        effective_provenance = backend.provenance or provenance
        bundle, function_entries = _materialize_prepared_bundle(
            prepared,
            generation_root,
            provenance_override=effective_provenance,
        )
        normalized_descriptors = tuple(
            descriptor
            if effective_provenance is None
            or descriptor.provenance == effective_provenance
            else replace(descriptor, provenance=effective_provenance)
            for descriptor in descriptors
        )
        registry.register_plugin_bundle(
            manifest,
            normalized_descriptors,
            owner_id=backend.plugin_id,
            owner_version=owner_version,
            source_label=str(source),
            source_identity=_plugin_source_identity(effective_provenance),
            replace_owner=True,
            python_function_entries=function_entries,
            plugin_bundle=bundle,
        )
        return [
            *(descriptor.spec.type_id for descriptor in normalized_descriptors),
            *(entry.spec.type_id for entry in function_entries),
        ]
    return _register_plugin_descriptors(
        descriptors,
        registry,
        source,
        provenance=backend.provenance or provenance,
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
    generation_root: Path | None = None,
) -> list[str]:
    loaded: list[str] = []
    resolved_generation_root = generation_root or plugin_generations_dir()
    for backend in backends:
        try:
            loaded.extend(
                _register_plugin_backend(
                    backend,
                    registry,
                    source,
                    provenance=provenance,
                    generation_root=resolved_generation_root,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Plugin backend %s failed [backend_load]",
                _bounded_plugin_log_label(backend.plugin_id),
            )
    return loaded


def discover_addon_records(*, preferences_document: Any = None):
    from ea_node_editor.addons.catalog import discover_addon_records as discover

    return discover(preferences_document=preferences_document)


def addon_record_by_id(addon_id: str, *, preferences_document: Any = None):
    from ea_node_editor.addons.catalog import addon_record_by_id as find_record

    return find_record(addon_id, preferences_document=preferences_document)
