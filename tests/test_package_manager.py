from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from ea_node_editor.nodes import package_manager, plugin_loader
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import (
    ArtifactDescriptor,
    NodeTypeSpec,
    PluginDescriptor,
    PluginProvenance,
    RuntimeBackendSpec,
    SurfaceCapabilitySpec,
    ToolchainRequirementSpec,
    ToolchainSpec,
)


def _build_package_archive(
    package_path: Path,
    *,
    manifest_name: str = "example_package",
    manifest_nodes: list[str] | None = None,
    plugin_type_id: str = "packet.imported",
    plugin_display_name: str = "Imported Package",
    manifest_extra: dict[str, object] | None = None,
    extra_members: dict[str, str] | None = None,
) -> Path:
    plugin_module = f"""
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


PLUGIN_SPEC = NodeTypeSpec(
    type_id={plugin_type_id!r},
    display_name=DISPLAY_NAME,
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class ImportedPlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=ImportedPlugin),
)
""".strip() + "\n"
    manifest = {
        "name": manifest_name,
        "version": "2.0.0",
        "author": "Packet Tests",
        "description": "P02 package import contract",
        "nodes": manifest_nodes if manifest_nodes is not None else [plugin_type_id],
        "dependencies": [],
    }
    manifest.update(manifest_extra or {})
    members = {
        package_manager.MANIFEST_FILENAME: json.dumps(manifest, indent=2),
        "__init__.py": "\n",
        "helper.py": f"DISPLAY_NAME = {plugin_display_name!r}\n",
        "package_plugin.py": plugin_module,
    }
    members.update(extra_members or {})

    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for member_name, contents in members.items():
            archive.writestr(member_name, contents)
    return package_path


def _write_source_file(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


def _typed_package_plugin_source(
    *,
    node_type_id: str = "packet.typed",
    data_type_id: str = "Packet.Package.Value",
) -> str:
    return f"""
from ea_node_editor.nodes.types import (
    DataTypeFamilySpec,
    DataTypeSpec,
    NodeResult,
    NodeTypeSpec,
    PluginContractManifest,
    PluginDescriptor,
    PortSpec,
)

PLUGIN_CONTRACT_MANIFEST = PluginContractManifest(
    data_type_families=(
        DataTypeFamilySpec("packet_package", "Packet", "data.packet", "packet"),
    ),
    data_types=(
        DataTypeSpec(
            {data_type_id!r},
            "Packet Value",
            "packet_package",
            lambda value: True,
            parents=("COREX.DataTypes.Any",),
        ),
    ),
)

PLUGIN_SPEC = NodeTypeSpec(
    type_id={node_type_id!r},
    display_name="Typed Package",
    category_path=("Packet Tests",),
    icon="packet",
    ports=(PortSpec("value", "out", "data", {data_type_id!r}),),
    properties=(),
)


class TypedPackagePlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=TypedPackagePlugin),
)
""".strip() + "\n"


def test_import_package_installs_package_directory_that_loader_discovers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(tmp_path / "example.cxpkg")

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


def test_package_manager_uses_public_package_discovery_surface() -> None:
    source = Path(package_manager.__file__).read_text(encoding="utf-8")

    assert "discover_package_plugins" in source
    assert "_load_plugins_from_package_directory" not in source


def test_import_package_preserves_plugin_toolchain_contract_manifest(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / "manifested.cxpkg",
        manifest_extra={
            "runtime_backends": [
                {
                    "backend_id": "packet.external",
                    "display_name": "Packet External",
                    "kind": "external_process",
                    "adapter_module": "packet.runtime",
                    "adapter_factory": "create_backend",
                    "transport": "json-rpc",
                    "transport_revision": 1,
                    "toolchain_ids": ["packet.rust"],
                    "artifact_ids": ["packet.native"],
                    "surface_capability_ids": ["packet.viewer"],
                }
            ],
            "toolchains": [
                {
                    "toolchain_id": "packet.rust",
                    "display_name": "Packet Rust",
                    "kind": "rust",
                    "language": "rust",
                    "requirements": [
                        {
                            "requirement_id": "rustc",
                            "kind": "compiler",
                            "display_name": "Rust compiler",
                            "command": "rustc",
                            "version_spec": ">=1.75",
                            "optional": False,
                        }
                    ],
                }
            ],
            "artifacts": [
                {
                    "artifact_id": "packet.native",
                    "kind": "shared_library",
                    "path": "target/release/packet_node.dll",
                    "runtime_backend_id": "packet.external",
                    "toolchain_id": "packet.rust",
                    "platform_tags": ["win_amd64"],
                }
            ],
            "surface_capabilities": [
                {
                    "capability_id": "packet.viewer",
                    "surface_family": "viewer",
                    "runtime_backend_id": "packet.external",
                    "fullscreen": True,
                    "input_modes": ["pointer", "keyboard"],
                }
            ],
        },
    )

    manifest = package_manager.import_package(package_path, target_dir=plugins_root)

    assert manifest.runtime_backends[0].backend_id == "packet.external"
    assert manifest.runtime_backends[0].kind == "external_process"
    assert manifest.toolchains[0].requirements[0].command == "rustc"
    assert manifest.artifacts[0].platform_tags == ("win_amd64",)
    assert manifest.surface_capabilities[0].fullscreen is True
    assert manifest.contract_manifest.runtime_backends == manifest.runtime_backends


def test_import_package_requires_manifest(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = tmp_path / "missing_manifest.cxpkg"
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("plugin.py", "print('missing manifest')\n")

    with pytest.raises(ValueError, match="missing node_package.json"):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


def test_import_package_requires_explicit_manifest_name(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = tmp_path / "nameless.cxpkg"
    with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(package_manager.MANIFEST_FILENAME, json.dumps({"nodes": ["packet.imported"]}))
        archive.writestr("__init__.py", "\n")

    with pytest.raises(ValueError, match="at least a 'name' field"):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


def test_import_package_rejects_manifest_node_mismatch_before_install(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / "mismatch.cxpkg",
        manifest_nodes=["packet.declared"],
        plugin_type_id="packet.actual",
    )

    with pytest.raises(ValueError, match="Package manifest nodes do not match discoverable node types"):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


def test_import_package_validates_and_loads_declared_data_type_inventory(
    tmp_path: Path,
) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / "typed.cxpkg",
        manifest_nodes=["packet.typed"],
        manifest_extra={"data_type_ids": [" Packet.Package.Value ", "Packet.Package.Value"]},
        extra_members={"package_plugin.py": _typed_package_plugin_source()},
    )

    manifest = package_manager.import_package(
        package_path,
        target_dir=plugins_root,
    )

    assert manifest.data_type_ids == ["Packet.Package.Value"]
    registry = NodeRegistry()
    loaded = plugin_loader.discover_package_plugins(
        plugins_root / "example_package",
        registry,
    )
    assert loaded == ["packet.typed"]
    assert registry.data_types.require("Packet.Package.Value").family_id == "packet_package"


def test_import_package_rejects_data_type_inventory_mismatch_before_install(
    tmp_path: Path,
) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / "typed_mismatch.cxpkg",
        manifest_nodes=["packet.typed"],
        manifest_extra={"data_type_ids": []},
        extra_members={"package_plugin.py": _typed_package_plugin_source()},
    )

    with pytest.raises(
        ValueError,
        match="Package manifest data_type_ids do not match executable data types",
    ):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


@pytest.mark.parametrize("data_type_ids", ["Packet.Package.Value", [1], [""]])
def test_package_manifest_rejects_invalid_data_type_inventory(
    data_type_ids: object,
) -> None:
    with pytest.raises(ValueError, match="data_type_ids"):
        package_manager._manifest_from_data(
            {
                "name": "invalid_types",
                "nodes": [],
                "data_type_ids": data_type_ids,
            }
        )


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
        tmp_path / f"{member_name.replace('/', '_')}.cxpkg",
        extra_members={member_name: "# invalid\n"},
    )

    with pytest.raises(ValueError, match=message):
        package_manager.import_package(package_path, target_dir=plugins_root)

    assert list(plugins_root.iterdir()) == []


def test_import_package_rejects_package_names_the_loader_would_skip(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(
        tmp_path / "hidden.cxpkg",
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

    package_path = _build_package_archive(tmp_path / "replacement.cxpkg")
    package_manager.import_package(package_path, target_dir=plugins_root)

    assert not (installed_package / "old_plugin.py").exists()
    assert (installed_package / "helper.py").is_file()
    assert (installed_package / "package_plugin.py").is_file()
    assert sorted(path.name for path in plugins_root.iterdir()) == ["example_package"]


def test_list_and_uninstall_packages_follow_installed_package_contract(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    package_path = _build_package_archive(tmp_path / "installed.cxpkg")
    package_manager.import_package(package_path, target_dir=plugins_root)

    hidden_package = plugins_root / ".example_package.incoming-orphan"
    hidden_package.mkdir(parents=True)
    (hidden_package / package_manager.MANIFEST_FILENAME).write_text(
        json.dumps({"name": "example_package", "version": "999.0.0"}),
        encoding="utf-8",
    )
    nameless_package = plugins_root / "nameless_package"
    nameless_package.mkdir(parents=True)
    (nameless_package / package_manager.MANIFEST_FILENAME).write_text(
        json.dumps({"version": "999.0.0"}),
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


def test_export_package_requires_explicit_discoverable_source_files(tmp_path: Path) -> None:
    output_path = tmp_path / "exports" / "hidden_only.cxpkg"
    hidden_source = _write_source_file(tmp_path / "sources" / "_helper.py", 'VALUE = "hidden"\n')
    manifest = package_manager.PackageManifest(
        name="hidden_only",
        version="1.0.0",
        author="Packet Tests",
        description="P03 hidden export rejection",
        nodes=["packet.hidden"],
    )

    with pytest.raises(ValueError, match="discoverable top-level plugin module"):
        package_manager.export_package(
            [package_manager.PackageExportSource(hidden_source, "_helper.py")],
            manifest,
            output_path,
        )

    with pytest.raises(ValueError, match="at least one Python source file"):
        package_manager.export_package([], manifest, tmp_path / "exports" / "empty.cxpkg")

    assert not output_path.exists()


def test_export_package_writes_plugin_toolchain_contract_manifest(tmp_path: Path) -> None:
    init_source = _write_source_file(tmp_path / "sources" / "__init__.py", "\n")
    plugin_source = _write_source_file(
        tmp_path / "sources" / "package_plugin.py",
        """
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor

PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.contract_export",
    display_name="Contract Export",
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)

class ContractExportPlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()

PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=ContractExportPlugin),
)
""".strip()
        + "\n",
    )
    runtime_backend = RuntimeBackendSpec(
        backend_id="packet.python",
        display_name="Packet Python Runtime",
        kind="python",
        adapter_module="packet.runtime",
        adapter_factory="create_backend",
        toolchain_ids=("packet.python",),
        artifact_ids=("packet.source",),
        surface_capability_ids=("packet.standard_surface",),
    )
    toolchain = ToolchainSpec(
        toolchain_id="packet.python",
        display_name="Packet Python",
        kind="python",
        language="python",
        requirements=(
            ToolchainRequirementSpec(
                requirement_id="python",
                kind="executable",
                command="python",
                version_spec=">=3.10",
            ),
        ),
    )
    artifact = ArtifactDescriptor(
        artifact_id="packet.source",
        kind="python_module",
        path="package_plugin.py",
        runtime_backend_id="packet.python",
        toolchain_id="packet.python",
    )
    surface = SurfaceCapabilitySpec(
        capability_id="packet.standard_surface",
        surface_family="standard",
        input_modes=("pointer",),
    )
    manifest = package_manager.PackageManifest(
        name="contract_export",
        version="1.0.0",
        nodes=["packet.contract_export"],
        runtime_backends=(runtime_backend,),
        toolchains=(toolchain,),
        artifacts=(artifact,),
        surface_capabilities=(surface,),
    )

    package_path = package_manager.export_package(
        [
            package_manager.PackageExportSource(init_source, "__init__.py"),
            package_manager.PackageExportSource(plugin_source, "package_plugin.py"),
        ],
        manifest,
        tmp_path / "exports" / "contract_export.cxpkg",
    )

    with zipfile.ZipFile(package_path, "r") as archive:
        exported_manifest = json.loads(archive.read(package_manager.MANIFEST_FILENAME))

    assert exported_manifest["runtime_backends"][0]["backend_id"] == "packet.python"
    assert exported_manifest["toolchains"][0]["requirements"][0]["version_spec"] == ">=3.10"
    assert exported_manifest["artifacts"][0]["kind"] == "python_module"
    assert exported_manifest["surface_capabilities"][0]["surface_family"] == "standard"


def test_export_package_rejects_placeholder_manifest_without_nodes(tmp_path: Path) -> None:
    plugin_source = _write_source_file(tmp_path / "sources" / "package_plugin.py", 'VALUE = "plugin"\n')
    manifest = package_manager.PackageManifest(
        name="placeholder_package",
        version="1.0.0",
        author="Packet Tests",
        description="P03 placeholder manifest rejection",
        nodes=[],
    )

    with pytest.raises(ValueError, match="at least one exported node type"):
        package_manager.export_package([plugin_source], manifest, tmp_path / "exports" / "placeholder.cxpkg")


def test_export_package_rejects_manifest_node_mismatch_before_publish(tmp_path: Path) -> None:
    init_source = _write_source_file(tmp_path / "sources" / "__init__.py", "\n")
    helper_source = _write_source_file(
        tmp_path / "sources" / "helper.py",
        'DISPLAY_NAME = "Exported Package"\n',
    )
    plugin_source = _write_source_file(
        tmp_path / "sources" / "package_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.actual",
    display_name=DISPLAY_NAME,
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class ExportedPlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=ExportedPlugin),
)
""".strip()
        + "\n",
    )
    manifest = package_manager.PackageManifest(
        name="roundtrip_package",
        version="3.0.0",
        author="Packet Tests",
        description="P10 export mismatch rejection",
        nodes=["packet.declared"],
    )

    with pytest.raises(ValueError, match="Package manifest nodes do not match discoverable node types"):
        package_manager.export_package(
            [
                package_manager.PackageExportSource(init_source, "__init__.py"),
                package_manager.PackageExportSource(helper_source, "helper.py"),
                package_manager.PackageExportSource(plugin_source, "package_plugin.py"),
            ],
            manifest,
            tmp_path / "exports" / "roundtrip.cxpkg",
        )

    assert not (tmp_path / "exports" / "roundtrip.cxpkg").exists()


def test_export_package_uses_descriptor_provenance_for_descriptor_only_validation(
    tmp_path: Path,
) -> None:
    init_source = _write_source_file(tmp_path / "sources" / "__init__.py", "\n")
    helper_source = _write_source_file(
        tmp_path / "sources" / "helper.py",
        'DISPLAY_NAME = "Exported Package"\n',
    )
    plugin_source = _write_source_file(
        tmp_path / "sources" / "package_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class ExportedPlugin:
    def __init__(self):
        raise RuntimeError("descriptor override validation must not instantiate source classes")

    def spec(self):
        return NodeTypeSpec(
            type_id="packet.exported",
            display_name=DISPLAY_NAME,
            category_path=("Packet Tests",),
            icon="packet",
            ports=(),
            properties=(),
        )

    def execute(self, ctx):
        return NodeResult()
""".strip()
        + "\n",
    )
    manifest = package_manager.PackageManifest(
        name="roundtrip_package",
        version="3.0.0",
        author="Packet Tests",
        description="P10 descriptor-backed export validation",
        nodes=["packet.exported"],
    )
    descriptor = PluginDescriptor(
        spec=NodeTypeSpec(
            type_id="packet.exported",
            display_name="Exported Package",
            category_path=("Packet Tests",),
            icon="packet",
            ports=(),
            properties=(),
        ),
        factory=type("ExportedPlugin", (), {}),
        provenance=PluginProvenance(
            kind="package",
            source_path=plugin_source.resolve(),
            package_root=plugin_source.parent.resolve(),
            package_name="roundtrip_package",
        ),
    )

    package_path = package_manager.export_package(
        [
            package_manager.PackageExportSource(init_source, "__init__.py"),
            package_manager.PackageExportSource(helper_source, "helper.py"),
            package_manager.PackageExportSource(plugin_source, "package_plugin.py"),
        ],
        manifest,
        tmp_path / "exports" / "roundtrip.cxpkg",
        descriptors=(descriptor,),
    )

    assert package_path == tmp_path / "exports" / "roundtrip.cxpkg"
    assert package_path.is_file()


def test_export_package_round_trips_through_import_and_loader_discovery(
    tmp_path: Path,
    monkeypatch,
) -> None:
    init_source = _write_source_file(tmp_path / "sources" / "__init__.py", "\n")
    helper_source = _write_source_file(
        tmp_path / "sources" / "source_helper.py",
        'DISPLAY_NAME = "Exported Package"\n',
    )
    plugin_source = _write_source_file(
        tmp_path / "sources" / "source_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.exported",
    display_name=DISPLAY_NAME,
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class ExportedPlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=ExportedPlugin),
)
""".strip()
        + "\n",
    )
    manifest = package_manager.PackageManifest(
        name="roundtrip_package",
        version="3.0.0",
        author="Packet Tests",
        description="P03 export round trip",
        nodes=["packet.exported"],
    )

    package_path = package_manager.export_package(
        [
            package_manager.PackageExportSource(init_source, "__init__.py"),
            package_manager.PackageExportSource(helper_source, "helper.py"),
            package_manager.PackageExportSource(plugin_source, "package_plugin.py"),
        ],
        manifest,
        tmp_path / "exports" / "roundtrip.zip",
    )

    assert package_path == tmp_path / "exports" / "roundtrip.cxpkg"
    with zipfile.ZipFile(package_path, "r") as archive:
        assert archive.namelist() == [
            package_manager.MANIFEST_FILENAME,
            "__init__.py",
            "helper.py",
            "package_plugin.py",
        ]
        exported_manifest = json.loads(archive.read(package_manager.MANIFEST_FILENAME))
        assert exported_manifest["name"] == "roundtrip_package"
        assert exported_manifest["nodes"] == ["packet.exported"]

    plugins_root = tmp_path / "plugins"
    installed_manifest = package_manager.import_package(package_path, target_dir=plugins_root)
    assert installed_manifest.name == "roundtrip_package"

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.exported"]
    assert registry.get_spec("packet.exported").display_name == "Exported Package"


def test_export_package_writes_validated_data_type_inventory(tmp_path: Path) -> None:
    init_source = _write_source_file(tmp_path / "sources" / "__init__.py", "\n")
    plugin_source = _write_source_file(
        tmp_path / "sources" / "package_plugin.py",
        _typed_package_plugin_source(),
    )
    manifest = package_manager.PackageManifest(
        name="typed_export",
        nodes=["packet.typed"],
        data_type_ids=["Packet.Package.Value"],
    )

    package_path = package_manager.export_package(
        [
            package_manager.PackageExportSource(init_source, "__init__.py"),
            package_manager.PackageExportSource(plugin_source, "package_plugin.py"),
        ],
        manifest,
        tmp_path / "exports" / "typed_export.cxpkg",
    )

    with zipfile.ZipFile(package_path, "r") as archive:
        exported_manifest = json.loads(
            archive.read(package_manager.MANIFEST_FILENAME)
        )
    assert exported_manifest["data_type_ids"] == ["Packet.Package.Value"]
