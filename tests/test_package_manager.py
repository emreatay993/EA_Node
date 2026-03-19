from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from ea_node_editor.nodes import package_manager, plugin_loader
from ea_node_editor.nodes.registry import NodeRegistry


def _build_package_archive(
    package_path: Path,
    *,
    manifest_name: str = "example_package",
    extra_members: dict[str, str] | None = None,
) -> Path:
    manifest = {
        "name": manifest_name,
        "version": "2.0.0",
        "author": "Packet Tests",
        "description": "P02 package import contract",
        "nodes": ["packet.imported"],
        "dependencies": [],
    }
    members = {
        package_manager.MANIFEST_FILENAME: json.dumps(manifest, indent=2),
        "helper.py": 'DISPLAY_NAME = "Imported Package"\n',
        "package_plugin.py": """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class ImportedPlugin:
    def spec(self):
        return NodeTypeSpec(
            type_id="packet.imported",
            display_name=DISPLAY_NAME,
            category="Packet Tests",
            icon="packet",
            ports=(),
            properties=(),
        )

    def execute(self, ctx):
        return NodeResult()
""".strip()
        + "\n",
    }
    members.update(extra_members or {})

    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for member_name, contents in members.items():
            archive.writestr(member_name, contents)
    return package_path


def test_import_package_installs_package_directory_that_loader_discovers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(tmp_path / "example.eanp")

    manifest = package_manager.import_package(package_path, target_dir=plugins_root)

    installed_package = plugins_root / "example_package"
    assert manifest.name == "example_package"
    assert (installed_package / package_manager.MANIFEST_FILENAME).is_file()
    assert (installed_package / "helper.py").is_file()
    assert (installed_package / "package_plugin.py").is_file()

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.imported"]
    assert registry.get_spec("packet.imported").display_name == "Imported Package"


def test_import_package_requires_manifest(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = tmp_path / "missing_manifest.eanp"
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("plugin.py", "print('missing manifest')\n")

    with pytest.raises(ValueError, match="missing node_package.json"):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


@pytest.mark.parametrize(
    ("member_name", "message"),
    [
        ("notes.txt", "Unsupported package archive member"),
        ("nested/plugin.py", "Unsafe package archive member"),
        ("../escape.py", "Unsafe package archive member"),
    ],
)
def test_import_package_rejects_non_canonical_archive_members(
    tmp_path: Path,
    member_name: str,
    message: str,
) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / f"{member_name.replace('/', '_')}.eanp",
        extra_members={member_name: "# invalid\n"},
    )

    with pytest.raises(ValueError, match=message):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


def test_import_package_rejects_package_names_the_loader_would_skip(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / "hidden.eanp",
        manifest_name="_hidden_package",
    )

    with pytest.raises(ValueError, match="loader ignores hidden package directories"):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


def test_import_package_replaces_existing_install_without_merging_files(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    installed_package = plugins_root / "example_package"
    installed_package.mkdir(parents=True)
    (installed_package / package_manager.MANIFEST_FILENAME).write_text(
        json.dumps({"name": "example_package", "version": "1.0.0"}),
        encoding="utf-8",
    )
    (installed_package / "old_plugin.py").write_text("raise RuntimeError('old file')\n", encoding="utf-8")

    package_path = _build_package_archive(tmp_path / "replacement.eanp")
    package_manager.import_package(package_path, target_dir=plugins_root)

    assert not (installed_package / "old_plugin.py").exists()
    assert (installed_package / "helper.py").is_file()
    assert (installed_package / "package_plugin.py").is_file()
    assert sorted(path.name for path in plugins_root.iterdir()) == ["example_package"]


def test_list_and_uninstall_packages_follow_installed_package_contract(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(tmp_path / "installed.eanp")
    package_manager.import_package(package_path, target_dir=plugins_root)

    hidden_package = plugins_root / ".example_package.incoming-orphan"
    hidden_package.mkdir(parents=True)
    (hidden_package / package_manager.MANIFEST_FILENAME).write_text(
        json.dumps({"name": "example_package", "version": "999.0.0"}),
        encoding="utf-8",
    )
    (plugins_root / "root_dropin.py").write_text("print('drop-in')\n", encoding="utf-8")

    manifests = package_manager.list_installed_packages(target_dir=plugins_root)

    assert [(manifest.name, manifest.version) for manifest in manifests] == [("example_package", "2.0.0")]
    assert package_manager.uninstall_package("example_package", target_dir=plugins_root) is True
    assert package_manager.uninstall_package("example_package", target_dir=plugins_root) is False
    assert not (plugins_root / "example_package").exists()


def test_uninstall_package_rejects_invalid_package_names(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="single directory name"):
        package_manager.uninstall_package("../escape", target_dir=tmp_path / "plugins")
