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
    source_files: list[Path],
    manifest: PackageManifest,
    output_path: Path,
) -> Path:
    """Bundle Python source files and a manifest into an .eanp archive."""
    output_path = output_path.with_suffix(PACKAGE_EXTENSION)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_FILENAME, json.dumps(asdict(manifest), indent=2))
        for source_file in source_files:
            if source_file.is_file() and source_file.suffix == ".py":
                archive.write(source_file, source_file.name)

    logger.info("Exported node package '%s' to %s", manifest.name, output_path)
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
