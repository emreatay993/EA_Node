"""Import and export shareable .eanp node packages.

An .eanp file is a zip archive containing:
  node_package.json   -- manifest with name, version, author, description, node list
  *.py                -- Python source files that expose PluginDescriptor records
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from uuid import uuid4

from ea_node_editor.nodes import plugin_loader
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.plugin_contracts import PluginDescriptor
from ea_node_editor.settings import plugins_dir

logger = logging.getLogger(__name__)

PACKAGE_EXTENSION = ".eanp"
MANIFEST_FILENAME = "node_package.json"
_HIDDEN_PACKAGE_PREFIXES = (".", "_")


@dataclass
class PackageManifest:
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    nodes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PackageExportSource:
    source_path: Path
    archive_name: str | None = None


def _manifest_from_data(raw: object) -> PackageManifest:
    if not isinstance(raw, dict):
        raise ValueError("Manifest must be a JSON object")

    name = raw.get("name")
    if not name:
        raise ValueError("Manifest must contain at least a 'name' field")

    return PackageManifest(
        name=str(name),
        version=str(raw.get("version", "1.0.0")),
        author=str(raw.get("author", "")),
        description=str(raw.get("description", "")),
        nodes=[str(n) for n in raw.get("nodes", [])],
        dependencies=[str(d) for d in raw.get("dependencies", [])],
    )


def _read_manifest(archive: zipfile.ZipFile) -> PackageManifest:
    try:
        raw = json.loads(archive.read(MANIFEST_FILENAME))
    except KeyError as exc:
        raise ValueError(f"Package is missing {MANIFEST_FILENAME}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {MANIFEST_FILENAME}") from exc

    return _manifest_from_data(raw)


def _normalized_manifest_node_ids(
    node_ids: list[str],
    *,
    require_at_least_one: bool,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_node_id in node_ids:
        node_id = str(raw_node_id).strip()
        if not node_id:
            raise ValueError("Package manifest node ids must be non-empty strings")
        if node_id in seen:
            raise ValueError(f"Package manifest node ids must be unique: {node_id}")
        seen.add(node_id)
        normalized.append(node_id)

    if require_at_least_one and not normalized:
        raise ValueError("Package manifest must list at least one exported node type")
    return tuple(normalized)


def _validated_manifest(
    manifest: PackageManifest,
    *,
    require_nodes: bool,
) -> PackageManifest:
    normalized_manifest = _manifest_from_data(asdict(manifest))
    normalized_manifest.name = _validate_package_name(normalized_manifest.name)
    normalized_manifest.nodes = list(
        _normalized_manifest_node_ids(
            normalized_manifest.nodes,
            require_at_least_one=require_nodes,
        )
    )
    return normalized_manifest


def _validate_package_name(package_name: str) -> str:
    candidate = str(package_name).strip()
    if not candidate:
        raise ValueError("Package name must be a non-empty directory name")
    if "/" in candidate or "\\" in candidate:
        raise ValueError("Package name must be a single directory name")
    if PurePosixPath(candidate).parts != (candidate,):
        raise ValueError("Package name must be a single directory name")
    if candidate in {".", ".."}:
        raise ValueError("Package name must be a safe directory name")
    if candidate.startswith(_HIDDEN_PACKAGE_PREFIXES):
        raise ValueError(
            "Package name must not start with '.' or '_' because the loader ignores hidden package directories",
        )
    return candidate


def _validated_archive_member_name(raw_name: str) -> str:
    normalized = raw_name.replace("\\", "/")
    member_path = PurePosixPath(normalized)
    if not normalized or normalized.endswith("/"):
        raise ValueError("Package archive may only contain files at the archive root")
    if member_path.is_absolute() or len(member_path.parts) != 1:
        raise ValueError(f"Unsafe package archive member: {raw_name}")
    if any(part in {"", ".", ".."} for part in member_path.parts):
        raise ValueError(f"Unsafe package archive member: {raw_name}")

    member_name = member_path.name
    if member_name != MANIFEST_FILENAME and not member_name.endswith(".py"):
        raise ValueError(
            f"Unsupported package archive member: {raw_name}. Only {MANIFEST_FILENAME} and top-level .py files are allowed",
        )
    return member_name


def _validate_archive_contents(archive: zipfile.ZipFile) -> tuple[PackageManifest, list[zipfile.ZipInfo]]:
    members: list[zipfile.ZipInfo] = []
    seen_members: set[str] = set()

    for info in archive.infolist():
        member_name = _validated_archive_member_name(info.filename)
        if member_name in seen_members:
            raise ValueError(f"Duplicate package archive member: {member_name}")
        seen_members.add(member_name)
        members.append(info)

    if MANIFEST_FILENAME not in seen_members:
        raise ValueError(f"Package is missing {MANIFEST_FILENAME}")

    manifest = _read_manifest(archive)
    manifest = _validated_manifest(manifest, require_nodes=False)
    return manifest, members


def _validated_manifest_for_export(manifest: PackageManifest) -> PackageManifest:
    return _validated_manifest(manifest, require_nodes=True)


def _normalized_export_source(source: PackageExportSource | Path | str) -> PackageExportSource:
    if isinstance(source, PackageExportSource):
        source_path = Path(source.source_path)
        archive_name = source.archive_name or source_path.name
        return PackageExportSource(source_path=source_path, archive_name=archive_name)

    source_path = Path(source)
    return PackageExportSource(source_path=source_path, archive_name=source_path.name)


def _validated_export_member_name(raw_name: str) -> str:
    member_name = _validated_archive_member_name(raw_name)
    if member_name == MANIFEST_FILENAME:
        raise ValueError(f"{MANIFEST_FILENAME} is reserved for the package manifest")
    return member_name


def _is_discoverable_archive_member(member_name: str) -> bool:
    return member_name == "__init__.py" or not member_name.startswith(_HIDDEN_PACKAGE_PREFIXES)


def _validated_export_sources(
    source_files: list[PackageExportSource | Path | str],
) -> list[PackageExportSource]:
    if not source_files:
        raise ValueError("Package export requires at least one Python source file")

    export_sources: list[PackageExportSource] = []
    seen_members: set[str] = set()
    has_discoverable_source = False

    for source in source_files:
        export_source = _normalized_export_source(source)
        if not export_source.source_path.is_file():
            raise ValueError(f"Package export source does not exist: {export_source.source_path}")
        if export_source.source_path.suffix != ".py":
            raise ValueError(f"Package export source must be a .py file: {export_source.source_path}")

        member_name = _validated_export_member_name(export_source.archive_name or export_source.source_path.name)
        if member_name in seen_members:
            raise ValueError(f"Duplicate package export member: {member_name}")
        seen_members.add(member_name)
        has_discoverable_source = has_discoverable_source or _is_discoverable_archive_member(member_name)
        export_sources.append(
            PackageExportSource(source_path=export_source.source_path, archive_name=member_name),
        )

    if not has_discoverable_source:
        raise ValueError("Package export requires at least one discoverable top-level plugin module")

    return export_sources


def _validated_descriptor_overrides(
    descriptors: list[PluginDescriptor] | tuple[PluginDescriptor, ...] | None,
    export_sources: list[PackageExportSource],
) -> dict[str, tuple[PluginDescriptor, ...]] | None:
    if descriptors is None:
        return None

    source_members = {
        export_source.source_path.resolve(): export_source.archive_name
        for export_source in export_sources
    }
    overrides: dict[str, list[PluginDescriptor]] = {}
    for descriptor in tuple(descriptors):
        if not isinstance(descriptor, PluginDescriptor):
            raise TypeError("Package export descriptors must be PluginDescriptor values")
        provenance = descriptor.provenance
        source_path = provenance.source_path if provenance is not None else None
        if source_path is None:
            raise ValueError("Package export descriptors must include source_path provenance")
        member_name = source_members.get(source_path.resolve())
        if member_name is None:
            raise ValueError(
                f"Package export descriptor source is not included in export sources: {source_path}",
            )
        overrides.setdefault(member_name, []).append(descriptor)

    return {
        member_name: tuple(member_descriptors)
        for member_name, member_descriptors in overrides.items()
    }


def _write_archive_members(
    archive: zipfile.ZipFile,
    members: list[zipfile.ZipInfo],
    destination_dir: Path,
) -> None:
    for member in members:
        member_name = _validated_archive_member_name(member.filename)
        (destination_dir / member_name).write_bytes(archive.read(member))


def _temporary_package_directory(target_dir: Path, package_name: str, *, kind: str) -> Path:
    return target_dir / f".{package_name}.{kind}-{uuid4().hex}"


def _temporary_export_archive_path(output_path: Path) -> Path:
    return output_path.with_name(f".{output_path.stem}.export-{uuid4().hex}{output_path.suffix}")


def _staged_export_validation_directory(output_path: Path, package_name: str) -> Path:
    return output_path.parent / f".{package_name}.export-validation-{uuid4().hex}"


def _activate_staged_install(staged_dir: Path, package_dir: Path) -> None:
    backup_dir: Path | None = None
    try:
        if package_dir.exists():
            if not package_dir.is_dir():
                raise ValueError(f"Installed package target is not a directory: {package_dir}")
            backup_dir = _temporary_package_directory(package_dir.parent, package_dir.name, kind="backup")
            package_dir.replace(backup_dir)
        staged_dir.replace(package_dir)
    except Exception:
        if backup_dir is not None and backup_dir.exists() and not package_dir.exists():
            backup_dir.replace(package_dir)
        raise
    else:
        if backup_dir is not None and backup_dir.exists():
            shutil.rmtree(backup_dir)


def _discovered_package_node_ids(
    package_dir: Path,
    *,
    descriptor_overrides: dict[str, tuple[PluginDescriptor, ...]] | None = None,
) -> tuple[str, ...]:
    registry = NodeRegistry()
    loaded_type_ids = plugin_loader.discover_package_plugins(
        package_dir,
        registry,
        descriptor_overrides=descriptor_overrides,
    )
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_type_id in loaded_type_ids:
        type_id = str(raw_type_id).strip()
        if not type_id or type_id in seen:
            continue
        seen.add(type_id)
        normalized.append(type_id)
    return tuple(normalized)


def _validate_manifest_against_package_directory(
    manifest: PackageManifest,
    package_dir: Path,
    *,
    descriptor_overrides: dict[str, tuple[PluginDescriptor, ...]] | None = None,
) -> None:
    declared_node_ids = tuple(manifest.nodes)
    discovered_node_ids = _discovered_package_node_ids(
        package_dir,
        descriptor_overrides=descriptor_overrides,
    )

    declared_node_id_set = set(declared_node_ids)
    discovered_node_id_set = set(discovered_node_ids)
    if declared_node_id_set == discovered_node_id_set:
        return

    details: list[str] = []
    missing_node_ids = [node_id for node_id in declared_node_ids if node_id not in discovered_node_id_set]
    undeclared_node_ids = [node_id for node_id in discovered_node_ids if node_id not in declared_node_id_set]
    if missing_node_ids:
        details.append(f"missing from package load: {', '.join(missing_node_ids)}")
    if undeclared_node_ids:
        details.append(f"not declared in manifest: {', '.join(undeclared_node_ids)}")
    detail = "; ".join(details) if details else "manifest and discoverable node types differ"
    raise ValueError(f"Package manifest nodes do not match discoverable node types: {detail}")


def _stage_export_sources(
    package_dir: Path,
    export_sources: list[PackageExportSource],
) -> None:
    package_dir.mkdir(parents=True, exist_ok=False)
    for export_source in export_sources:
        shutil.copy2(export_source.source_path, package_dir / export_source.archive_name)


def import_package(package_path: Path, target_dir: Path | None = None) -> PackageManifest:
    """Extract an .eanp package into the plugins directory.

    Returns the manifest so the caller can report what was installed.
    """
    target = target_dir or plugins_dir()
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(package_path, "r") as archive:
        manifest, members = _validate_archive_contents(archive)
        package_dir = target / manifest.name
        staged_dir = _temporary_package_directory(target, manifest.name, kind="incoming")
        staged_dir.mkdir(parents=True, exist_ok=False)
        try:
            _write_archive_members(archive, members, staged_dir)
            _validate_manifest_against_package_directory(manifest, staged_dir)
            _activate_staged_install(staged_dir, package_dir)
        except Exception:
            if staged_dir.exists():
                shutil.rmtree(staged_dir, ignore_errors=True)
            raise

    logger.info("Imported node package '%s' v%s to %s", manifest.name, manifest.version, package_dir)
    return manifest


def export_package(
    source_files: list[PackageExportSource | Path | str],
    manifest: PackageManifest,
    output_path: Path,
    *,
    descriptors: list[PluginDescriptor] | tuple[PluginDescriptor, ...] | None = None,
) -> Path:
    """Bundle explicit Python source files and a manifest into an .eanp archive."""
    normalized_manifest = _validated_manifest_for_export(manifest)
    export_sources = _validated_export_sources(source_files)
    descriptor_overrides = _validated_descriptor_overrides(descriptors, export_sources)
    output_path = output_path.with_suffix(PACKAGE_EXTENSION)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output_path = _temporary_export_archive_path(output_path)
    staged_validation_dir = _staged_export_validation_directory(output_path, normalized_manifest.name)

    try:
        _stage_export_sources(staged_validation_dir, export_sources)
        _validate_manifest_against_package_directory(
            normalized_manifest,
            staged_validation_dir,
            descriptor_overrides=descriptor_overrides,
        )
        with zipfile.ZipFile(temporary_output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_FILENAME, json.dumps(asdict(normalized_manifest), indent=2))
            for export_source in export_sources:
                archive.write(export_source.source_path, export_source.archive_name)

        # Re-validate the produced archive against the import contract before publishing it.
        with zipfile.ZipFile(temporary_output_path, "r") as archive:
            _validate_archive_contents(archive)
        temporary_output_path.replace(output_path)
    except Exception:
        temporary_output_path.unlink(missing_ok=True)
        raise
    finally:
        if staged_validation_dir.exists():
            shutil.rmtree(staged_validation_dir, ignore_errors=True)

    logger.info("Exported node package '%s' to %s", normalized_manifest.name, output_path)
    return output_path


def list_installed_packages(target_dir: Path | None = None) -> list[PackageManifest]:
    """Return manifests of all packages currently installed in the plugins directory."""
    target = target_dir or plugins_dir()
    manifests: list[PackageManifest] = []
    if not target.is_dir():
        return manifests

    for child in sorted(target.iterdir()):
        try:
            _validate_package_name(child.name)
        except ValueError:
            continue
        manifest_path = child / MANIFEST_FILENAME
        if child.is_dir() and manifest_path.exists():
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifests.append(_manifest_from_data(raw))
            except Exception:  # noqa: BLE001
                logger.warning("Could not read manifest in %s", child)
    return manifests


def uninstall_package(package_name: str, target_dir: Path | None = None) -> bool:
    """Remove an installed package by name. Returns True if removed."""
    target = target_dir or plugins_dir()
    package_dir = target / _validate_package_name(package_name)
    if package_dir.is_dir():
        shutil.rmtree(package_dir)
        logger.info("Uninstalled node package '%s'", package_name)
        return True
    return False
