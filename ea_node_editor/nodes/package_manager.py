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
from pathlib import Path

from ea_node_editor.settings import plugins_dir

logger = logging.getLogger(__name__)

PACKAGE_EXTENSION = ".eanp"
MANIFEST_FILENAME = "node_package.json"


@dataclass
class PackageManifest:
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    nodes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


def _read_manifest(archive: zipfile.ZipFile) -> PackageManifest:
    try:
        raw = json.loads(archive.read(MANIFEST_FILENAME))
    except KeyError as exc:
        raise ValueError(f"Package is missing {MANIFEST_FILENAME}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {MANIFEST_FILENAME}") from exc

    if not isinstance(raw, dict) or not raw.get("name"):
        raise ValueError("Manifest must contain at least a 'name' field")

    return PackageManifest(
        name=str(raw["name"]),
        version=str(raw.get("version", "1.0.0")),
        author=str(raw.get("author", "")),
        description=str(raw.get("description", "")),
        nodes=[str(n) for n in raw.get("nodes", [])],
        dependencies=[str(d) for d in raw.get("dependencies", [])],
    )


def import_package(package_path: Path, target_dir: Path | None = None) -> PackageManifest:
    """Extract an .eanp package into the plugins directory.

    Returns the manifest so the caller can report what was installed.
    """
    target = target_dir or plugins_dir()
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(package_path, "r") as archive:
        manifest = _read_manifest(archive)

        package_dir = target / manifest.name
        if package_dir.exists():
            shutil.rmtree(package_dir)
        package_dir.mkdir(parents=True, exist_ok=True)

        for member in archive.namelist():
            if member == MANIFEST_FILENAME or member.endswith(".py"):
                archive.extract(member, package_dir)

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
        manifest_path = child / MANIFEST_FILENAME
        if child.is_dir() and manifest_path.exists():
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifests.append(PackageManifest(
                    name=str(raw.get("name", child.name)),
                    version=str(raw.get("version", "0.0.0")),
                    author=str(raw.get("author", "")),
                    description=str(raw.get("description", "")),
                    nodes=[str(n) for n in raw.get("nodes", [])],
                    dependencies=[str(d) for d in raw.get("dependencies", [])],
                ))
            except Exception:  # noqa: BLE001
                logger.warning("Could not read manifest in %s", child)
    return manifests


def uninstall_package(package_name: str, target_dir: Path | None = None) -> bool:
    """Remove an installed package by name. Returns True if removed."""
    target = target_dir or plugins_dir()
    package_dir = target / package_name
    if package_dir.is_dir():
        shutil.rmtree(package_dir)
        logger.info("Uninstalled node package '%s'", package_name)
        return True
    return False
