"""Import and export shareable .eanp node packages.

An .eanp file is a zip archive containing:
  node_package.json   -- manifest with name, version, author, description, node list
  *.py                -- Python source files that define NodePlugin classes
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from uuid import uuid4

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


def _manifest_from_data(raw: object, *, fallback_name: str | None = None) -> PackageManifest:
    if not isinstance(raw, dict):
        raise ValueError("Manifest must be a JSON object")

    name = raw.get("name", fallback_name)
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
    manifest.name = _validate_package_name(manifest.name)
    return manifest, members


def _validated_manifest_for_export(manifest: PackageManifest) -> PackageManifest:
    normalized_manifest = _manifest_from_data(asdict(manifest))
    normalized_manifest.name = _validate_package_name(normalized_manifest.name)
    if not normalized_manifest.nodes:
        raise ValueError("Package manifest must list at least one exported node type")
    if any(not node_type_id.strip() for node_type_id in normalized_manifest.nodes):
        raise ValueError("Package manifest node ids must be non-empty strings")
    return normalized_manifest


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
) -> Path:
    """Bundle explicit Python source files and a manifest into an .eanp archive."""
    normalized_manifest = _validated_manifest_for_export(manifest)
    export_sources = _validated_export_sources(source_files)
    output_path = output_path.with_suffix(PACKAGE_EXTENSION)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output_path = _temporary_export_archive_path(output_path)

    try:
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
                manifests.append(_manifest_from_data(raw, fallback_name=child.name))
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
