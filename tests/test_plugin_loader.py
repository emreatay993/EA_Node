from __future__ import annotations

import importlib.metadata
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from ea_node_editor.addons import catalog as addon_catalog
from ea_node_editor.addons.catalog import (
    ANSYS_DPF_ADDON_ID,
    AddOnRegistration,
    registered_addon_registration_by_id,
)
from ea_node_editor.addons.hot_apply import apply_addon_enabled_state
from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    addon_state,
    default_app_preferences_document,
    normalize_app_preferences_document,
    set_addon_state,
)
from ea_node_editor.nodes import plugin_loader
from ea_node_editor.nodes.core_data_types import GRAPH_DATA_TYPE_ID
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec
from ea_node_editor.nodes.plugin_contracts import (
    AddOnManifest,
    ArtifactDescriptor,
    PluginAvailability,
    PluginBackendDescriptor,
    PluginContractManifest,
    PluginDescriptor,
    PluginProvenance,
    RuntimeBackendSpec,
    SurfaceCapabilitySpec,
    ToolchainRequirementSpec,
    ToolchainSpec,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import (
    DataTypeFamilySpec,
    DataTypeSpec,
    RuntimeArtifactRef,
)


def _write_text(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


def _write_plugin(path: Path, *, type_id: str, display_name: str, class_name: str = "PacketPlugin") -> Path:
    return _write_text(
        path,
        f"""
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


PLUGIN_SPEC = NodeTypeSpec(
    type_id={type_id!r},
    display_name={display_name!r},
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class {class_name}:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory={class_name}),
)
""".strip()
        + "\n",
    )


def _packet_descriptor(type_id: str, display_name: str) -> PluginDescriptor:
    class PacketBackendPlugin:
        def spec(self):
            return NodeTypeSpec(
                type_id=type_id,
                display_name=display_name,
                category_path=("Packet Tests",),
                icon="packet",
                ports=(),
                properties=(),
            )

        def execute(self, ctx):
            from ea_node_editor.nodes.types import NodeResult

            return NodeResult()

    return PluginDescriptor(spec=PacketBackendPlugin().spec(), factory=PacketBackendPlugin)


def _typed_packet_descriptor(
    node_type_id: str,
    data_type_id: str,
) -> PluginDescriptor:
    spec = NodeTypeSpec(
        type_id=node_type_id,
        display_name="Typed Packet",
        category_path=("Packet Tests",),
        icon="packet",
        ports=(PortSpec("value", "out", "data", data_type_id),),
        properties=(),
    )

    class TypedPacketPlugin:
        def spec(self):
            return spec

        def execute(self, ctx):
            from ea_node_editor.nodes.types import NodeResult

            return NodeResult()

    return PluginDescriptor(spec=spec, factory=TypedPacketPlugin)


def test_plugin_owner_ids_are_stable_and_path_free_across_install_roots(
    tmp_path: Path,
) -> None:
    root_a = tmp_path / "private_a" / "plugins"
    root_b = tmp_path / "private_b" / "plugins"
    file_a = root_a / "catalog_plugin.py"
    file_b = root_b / "catalog_plugin.py"
    file_owner_a = plugin_loader._plugin_owner_id(  # noqa: SLF001
        file_a,
        PluginProvenance(kind="file", source_path=file_a),
    )
    file_owner_b = plugin_loader._plugin_owner_id(  # noqa: SLF001
        file_b,
        PluginProvenance(kind="file", source_path=file_b),
    )
    package_owner_a = plugin_loader._plugin_owner_id(  # noqa: SLF001
        root_a / "sample" / "nodes.py",
        PluginProvenance(
            kind="package",
            source_path=root_a / "sample" / "nodes.py",
            package_root=root_a / "sample",
            package_name="sample",
        ),
    )
    package_owner_b = plugin_loader._plugin_owner_id(  # noqa: SLF001
        root_b / "sample" / "nodes.py",
        PluginProvenance(
            kind="package",
            source_path=root_b / "sample" / "nodes.py",
            package_root=root_b / "sample",
            package_name="sample",
        ),
    )
    entry_owner = plugin_loader._plugin_owner_id(  # noqa: SLF001
        "catalog-entry",
        PluginProvenance(
            kind="entry_point",
            entry_point_name="catalog-entry",
            distribution_name="catalog-package",
        ),
    )

    assert file_owner_a == file_owner_b == "plugin:file:catalog_plugin"
    assert package_owner_a == package_owner_b == "plugin:package:sample:nodes"
    assert entry_owner == "plugin:entry_point:catalog_package:catalog_entry"
    for owner_id in (file_owner_a, package_owner_a, entry_owner):
        assert str(tmp_path) not in owner_id
        assert "/" not in owner_id
        assert "\\" not in owner_id

    registry = NodeRegistry()
    descriptor = _packet_descriptor("packet.owner.stable", "Stable Owner")
    loaded = plugin_loader._register_plugin_descriptors(  # noqa: SLF001
        (descriptor,),
        registry,
        file_a,
        provenance=PluginProvenance(kind="file", source_path=file_a),
    )

    assert loaded == ["packet.owner.stable"]
    assert registry.plugin_contract_manifest(file_owner_a) == PluginContractManifest()


def test_same_basename_loose_plugins_fail_closed_without_replacing_first_owner(
    tmp_path: Path,
    caplog,
) -> None:
    root_a = tmp_path / "private_a" / "plugins"
    root_b = tmp_path / "private_b" / "plugins"
    file_a = root_a / "shared.py"
    file_b = root_b / "shared.py"
    provenance_a = PluginProvenance(kind="file", source_path=file_a)
    provenance_b = PluginProvenance(kind="file", source_path=file_b)
    first_families, first_types = _packet_data_type_contract(
        family_id="packet_first",
        type_id="Packet.First.Value",
    )
    second_families, second_types = _packet_data_type_contract(
        family_id="packet_second",
        type_id="Packet.Second.Value",
    )
    registry = NodeRegistry()
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)

    first_loaded = plugin_loader._register_plugin_descriptors(  # noqa: SLF001
        (_typed_packet_descriptor("packet.first", "Packet.First.Value"),),
        registry,
        file_a,
        provenance=provenance_a,
        manifest=PluginContractManifest(
            data_type_families=first_families,
            data_types=first_types,
        ),
    )
    before_fingerprint = registry.data_types.fingerprint()
    second_loaded = plugin_loader._register_plugin_descriptors(  # noqa: SLF001
        (_typed_packet_descriptor("packet.second", "Packet.Second.Value"),),
        registry,
        file_b,
        provenance=provenance_b,
        manifest=PluginContractManifest(
            data_type_families=second_families,
            data_types=second_types,
        ),
    )

    assert first_loaded == ["packet.first"]
    assert second_loaded == []
    assert registry.data_types.fingerprint() == before_fingerprint
    assert registry.spec_or_none("packet.first") is not None
    assert registry.spec_or_none("packet.second") is None
    assert registry.data_types.get("Packet.First.Value") is not None
    assert registry.data_types.get("Packet.Second.Value") is None
    assert "plugin:file:shared" in caplog.text
    assert str(root_a) not in caplog.text
    assert str(root_b) not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_same_loose_plugin_source_can_reload_its_owner(tmp_path: Path) -> None:
    plugin_file = tmp_path / "plugins" / "shared.py"
    provenance = PluginProvenance(kind="file", source_path=plugin_file)
    registry = NodeRegistry()

    first_loaded = plugin_loader._register_plugin_descriptors(  # noqa: SLF001
        (_packet_descriptor("packet.first", "First"),),
        registry,
        plugin_file,
        provenance=provenance,
    )
    second_loaded = plugin_loader._register_plugin_descriptors(  # noqa: SLF001
        (_packet_descriptor("packet.second", "Second"),),
        registry,
        plugin_file,
        provenance=provenance,
    )

    assert first_loaded == ["packet.first"]
    assert second_loaded == ["packet.second"]
    assert registry.spec_or_none("packet.first") is None
    assert registry.spec_or_none("packet.second") is not None


def _packet_data_type_contract(
    *,
    family_id: str = "packet_plugin",
    type_id: str = "Packet.Plugin.Value",
) -> tuple[tuple[DataTypeFamilySpec, ...], tuple[DataTypeSpec, ...]]:
    return (
        (DataTypeFamilySpec(family_id, "Packet", "data.packet", "packet"),),
        (
            DataTypeSpec(
                type_id,
                "Packet Value",
                family_id,
                lambda value: True,
                parents=(GRAPH_DATA_TYPE_ID,),
            ),
        ),
    )


def test_discover_and_load_plugins_preserves_root_py_dropins(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_plugin(plugins_root / "root_dropin.py", type_id="packet.root", display_name="Root Drop-In")
    _write_plugin(plugins_root / "_private.py", type_id="packet.private", display_name="Private")

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.root"]
    assert registry.get_spec("packet.root").display_name == "Root Drop-In"
    descriptor = registry.get_descriptor("packet.root")
    assert descriptor.provenance is not None
    assert descriptor.provenance.kind == "file"
    assert descriptor.provenance.source_path == (plugins_root / "root_dropin.py").resolve()
    assert registry.spec_or_none("packet.private") is None


def test_discover_and_load_plugins_discovers_package_directories(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    package_dir = plugins_root / "example_package"
    _write_text(package_dir / "__init__.py", "\n")
    _write_text(package_dir / "helper.py", 'DISPLAY_NAME = "Package Directory Plugin"\n')
    _write_text(
        package_dir / "package_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.package",
    display_name=DISPLAY_NAME,
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class PackagePlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=PackagePlugin),
)
""".strip()
        + "\n",
    )

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.package"]
    assert registry.get_spec("packet.package").display_name == "Package Directory Plugin"
    descriptor = registry.get_descriptor("packet.package")
    assert descriptor.provenance is not None
    assert descriptor.provenance.kind == "package"
    assert descriptor.provenance.package_root == package_dir.resolve()
    assert descriptor.provenance.source_path == (package_dir / "package_plugin.py").resolve()


def test_discover_package_plugins_loads_one_package_directory(tmp_path: Path) -> None:
    package_dir = tmp_path / "plugins" / "example_package"
    _write_text(package_dir / "__init__.py", "\n")
    _write_text(package_dir / "helper.py", 'DISPLAY_NAME = "Package Directory Plugin"\n')
    _write_text(
        package_dir / "package_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.package.single",
    display_name=DISPLAY_NAME,
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class PackagePlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=PackagePlugin),
)
""".strip()
        + "\n",
    )

    registry = NodeRegistry()
    loaded = plugin_loader.discover_package_plugins(package_dir, registry)

    assert loaded == ["packet.package.single"]
    descriptor = registry.get_descriptor("packet.package.single")
    assert descriptor.provenance is not None
    assert descriptor.provenance.kind == "package"
    assert descriptor.provenance.package_root == package_dir.resolve()


def test_discover_package_plugins_requires_real_package_init(
    tmp_path: Path,
    caplog,
) -> None:
    package_dir = tmp_path / "plugins" / "namespace_only_package"
    _write_plugin(package_dir / "package_plugin.py", type_id="packet.namespace", display_name="Namespace Package")
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)

    registry = NodeRegistry()
    loaded = plugin_loader.discover_package_plugins(package_dir, registry)

    assert loaded == []
    assert registry.spec_or_none("packet.namespace") is None
    assert "plugin:package:namespace_only_package:init" in caplog.text
    assert "[missing_init]" in caplog.text
    assert str(tmp_path) not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_discover_and_load_plugins_continues_after_bad_modules(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    plugins_root = tmp_path / "plugins"
    private_detail = f"secret-token at {plugins_root}"
    _write_text(
        plugins_root / "broken_root.py",
        f"raise RuntimeError({private_detail!r})\n",
    )
    _write_plugin(plugins_root / "good_root.py", type_id="packet.root.good", display_name="Good Root")

    package_dir = plugins_root / "installed_package"
    _write_text(package_dir / "__init__.py", "\n")
    _write_text(
        package_dir / "bad_module.py",
        f"raise RuntimeError({private_detail!r})\n",
    )
    _write_plugin(package_dir / "good_package.py", type_id="packet.package.good", display_name="Good Package")

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.root.good", "packet.package.good"]
    assert registry.spec_or_none("packet.root.good") is not None
    assert registry.spec_or_none("packet.package.good") is not None
    assert "plugin:file:broken_root" in caplog.text
    assert "plugin:package:installed_package:bad_module" in caplog.text
    assert "[module_import]" in caplog.text
    assert private_detail not in caplog.text
    assert str(plugins_root) not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_discover_and_load_plugins_loads_descriptor_records_without_constructor_probing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_text(
        plugins_root / "descriptor_plugin.py",
        """
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor


class ShouldNotBeScanned:
    def __init__(self):
        raise RuntimeError("legacy class probing should not run when PLUGIN_DESCRIPTORS is present")


PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.descriptor",
    display_name="Descriptor Plugin",
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class DescriptorPlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=DescriptorPlugin),
)
""".strip()
        + "\n",
    )

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.descriptor"]
    assert registry.get_spec("packet.descriptor").display_name == "Descriptor Plugin"


def test_discover_and_load_plugins_rejects_descriptor_tuple_shorthand(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_text(
        plugins_root / "tuple_shorthand.py",
        """
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class TuplePlugin:
    def spec(self):
        return NodeTypeSpec(
            type_id="packet.tuple",
            display_name="Tuple Plugin",
            category_path=("Packet Tests",),
            icon="packet",
            ports=(),
            properties=(),
        )

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    (TuplePlugin().spec(), TuplePlugin),
)
""".strip()
        + "\n",
    )

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == []
    assert registry.spec_or_none("packet.tuple") is None
    assert "plugin:file:tuple_shorthand" in caplog.text
    assert "[invalid_api]" in caplog.text
    assert str(tmp_path) not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_discover_and_load_plugins_preserves_entry_point_loading(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    class EntryPointPlugin:
        def spec(self):
            from ea_node_editor.nodes.types import NodeTypeSpec

            return NodeTypeSpec(
                type_id="packet.entry-point",
                display_name="Entry Point",
                category_path=("Packet Tests",),
                icon="packet",
                ports=(),
                properties=(),
            )

        def execute(self, ctx):
            from ea_node_editor.nodes.types import NodeResult

            return NodeResult()

    entry_point_descriptor = PluginDescriptor(
        spec=EntryPointPlugin().spec(),
        factory=EntryPointPlugin,
    )

    class FakeEntryPoint:
        def __init__(self, name: str) -> None:
            self.name = name

        def load(self):
            return SimpleNamespace(PLUGIN_DESCRIPTORS=(entry_point_descriptor,))

    def fake_entry_points(*args, **kwargs):
        calls.append(dict(kwargs))
        entry_points = [FakeEntryPoint("packet-entry-point")]
        assert kwargs == {"group": plugin_loader.ENTRY_POINT_GROUP}
        return entry_points

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: tmp_path / "plugins")
    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.entry-point"]
    assert registry.get_spec("packet.entry-point").display_name == "Entry Point"
    descriptor = registry.get_descriptor("packet.entry-point")
    assert descriptor.provenance is not None
    assert descriptor.provenance.kind == "entry_point"
    assert descriptor.provenance.entry_point_name == "packet-entry-point"
    assert calls == [{"group": plugin_loader.ENTRY_POINT_GROUP}]


def test_discover_and_load_plugins_does_not_probe_entry_point_classes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class EntryPointPlugin:
        def spec(self):
            return NodeTypeSpec(
                type_id="packet.entry-point-class",
                display_name="Entry Point Class",
                category_path=("Packet Tests",),
                icon="packet",
                ports=(),
                properties=(),
            )

        def execute(self, ctx):
            from ea_node_editor.nodes.types import NodeResult

            return NodeResult()

    class FakeEntryPoint:
        name = "packet-entry-point-class"

        def load(self):
            return EntryPointPlugin

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: tmp_path / "plugins")
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda *, group: [FakeEntryPoint()] if group == plugin_loader.ENTRY_POINT_GROUP else [],
    )

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == []
    assert registry.spec_or_none("packet.entry-point-class") is None


def test_discover_and_load_plugins_supports_neutral_runtime_contract_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_text(
        plugins_root / "runtime_contract_plugin.py",
        """
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PluginDescriptor
from ea_node_editor.runtime_contracts import PATH_DATA_TYPE_ID, RuntimeArtifactRef


PLUGIN_SPEC = NodeTypeSpec(
    type_id="packet.runtime_contracts",
    display_name="Runtime Contracts",
    category_path=("Packet Tests",),
    icon="packet",
    ports=(),
    properties=(),
)


class RuntimeContractPlugin:
    def spec(self):
        return PLUGIN_SPEC

    def execute(self, ctx):
        return NodeResult(
            outputs={
                "artifact": RuntimeArtifactRef.staged(
                    "packet_runtime_contract",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="bin",
                    size_bytes=0,
                    sha256="0" * 64,
                    provenance="corex.test.fixture",
                )
            },
        )


PLUGIN_DESCRIPTORS = (
    PluginDescriptor(spec=PLUGIN_SPEC, factory=RuntimeContractPlugin),
)
""".strip()
        + "\n",
    )

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.runtime_contracts"]
    descriptor = registry.get_descriptor("packet.runtime_contracts")
    result = descriptor.factory().execute(None)

    assert isinstance(result.outputs["artifact"], RuntimeArtifactRef)
    assert result.outputs["artifact"].artifact_id == "packet_runtime_contract"




def test_register_plugin_backends_redacts_availability_and_failure_details(
    tmp_path: Path,
    caplog,
) -> None:
    private_detail = f"secret-token at {tmp_path / 'private' / 'backend.py'}"

    def fail_descriptors() -> tuple[PluginDescriptor, ...]:
        raise RuntimeError(private_detail)

    unavailable = PluginBackendDescriptor(
        plugin_id="packet.unavailable",
        display_name="Unavailable Backend",
        get_availability=lambda: PluginAvailability.missing_dependency(
            private_detail,
            summary=private_detail,
        ),
        load_descriptors=lambda: (),
    )
    failing = PluginBackendDescriptor(
        plugin_id=str(tmp_path / "private" / "failing_backend.py"),
        display_name="Failing Backend",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=fail_descriptors,
    )
    caplog.set_level(logging.INFO, logger=plugin_loader.__name__)

    loaded = plugin_loader.register_plugin_backends(
        (unavailable, failing),
        NodeRegistry(),
        tmp_path / "private" / "backend.py",
    )

    assert loaded == []
    assert "Plugin backend packet.unavailable skipped [unavailable]" in caplog.text
    assert "Plugin backend plugin:opaque:" in caplog.text
    assert "[backend_load]" in caplog.text
    assert private_detail not in caplog.text
    assert str(tmp_path) not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_plugin_failure_logs_omit_hostile_dynamic_exception_class_names(
    tmp_path: Path,
    caplog,
) -> None:
    hostile_name = f"SecretClass\n{tmp_path / 'private' / 'exception.py'}\t"
    hostile_exception = type(hostile_name, (Exception,), {})

    def fail_descriptors() -> tuple[PluginDescriptor, ...]:
        raise hostile_exception("plugin-controlled message")

    backend = PluginBackendDescriptor(
        plugin_id="packet.hostile_exception",
        display_name="Hostile Exception",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=fail_descriptors,
    )
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)

    loaded = plugin_loader.register_plugin_backends(
        (backend,),
        NodeRegistry(),
        tmp_path / "private" / "backend.py",
    )

    assert loaded == []
    assert "Plugin backend packet.hostile_exception failed [backend_load]" in caplog.text
    assert "SecretClass" not in caplog.text
    assert str(tmp_path) not in caplog.text
    assert "plugin-controlled message" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_module_level_types_are_omitted_when_single_backend_is_unavailable() -> None:
    descriptor_loader_called = False
    families, data_types = _packet_data_type_contract(
        family_id="packet_module_optional",
        type_id="Packet.Module.Optional",
    )

    def load_descriptors() -> tuple[PluginDescriptor, ...]:
        nonlocal descriptor_loader_called
        descriptor_loader_called = True
        return (
            _typed_packet_descriptor(
                "packet.module.optional",
                "Packet.Module.Optional",
            ),
        )

    backend = PluginBackendDescriptor(
        plugin_id="packet.module.optional",
        display_name="Module Optional",
        get_availability=lambda: PluginAvailability.missing_dependency(
            "packet.module.optional.dep",
        ),
        load_descriptors=load_descriptors,
    )
    module = SimpleNamespace(
        PLUGIN_CONTRACT_MANIFEST=PluginContractManifest(
            data_type_families=families,
            data_types=data_types,
        ),
        PLUGIN_BACKENDS=(backend,),
    )
    registry = NodeRegistry()

    loaded = plugin_loader._register_module_plugins(
        module,
        registry,
        "packet.module.optional",
    )

    assert loaded == []
    assert descriptor_loader_called is False
    assert registry.spec_or_none("packet.module.optional") is None
    assert registry.data_types.get("Packet.Module.Optional") is None
    assert registry.plugin_contract_manifest("packet.module.optional") is None


def test_module_backend_invalid_descriptor_preserves_active_owner_bundle() -> None:
    registry = NodeRegistry()
    active_families, active_types = _packet_data_type_contract(
        family_id="packet_module_active",
        type_id="Packet.Module.Active",
    )
    active_spec = _typed_packet_descriptor(
        "packet.module.replace",
        "Packet.Module.Active",
    )
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=active_families,
            data_types=active_types,
        ),
        (active_spec,),
        owner_id="packet.module.replace",
    )
    before_fingerprint = registry.data_types.fingerprint()

    replacement_families, replacement_types = _packet_data_type_contract(
        family_id="packet_module_replacement",
        type_id="Packet.Module.Replacement",
    )
    backend = PluginBackendDescriptor(
        plugin_id="packet.module.replace",
        display_name="Module Replacement",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=lambda: (
            _typed_packet_descriptor(
                "packet.module.invalid",
                "Packet.Unknown",
            ),
        ),
    )
    module = SimpleNamespace(
        PLUGIN_CONTRACT_MANIFEST=PluginContractManifest(
            data_type_families=replacement_families,
            data_types=replacement_types,
        ),
        PLUGIN_BACKENDS=(backend,),
    )

    loaded = plugin_loader._register_module_plugins(
        module,
        registry,
        "packet.module.replace",
    )

    assert loaded == []
    assert registry.data_types.fingerprint() == before_fingerprint
    assert registry.data_types.get("Packet.Module.Active") is not None
    assert registry.data_types.get("Packet.Module.Replacement") is None
    assert registry.spec_or_none("packet.module.replace") is not None
    assert registry.spec_or_none("packet.module.invalid") is None


def test_module_backend_descriptor_loader_exception_leaves_no_contribution() -> None:
    families, data_types = _packet_data_type_contract(
        family_id="packet_module_throwing",
        type_id="Packet.Module.Throwing",
    )

    def load_descriptors() -> tuple[PluginDescriptor, ...]:
        raise RuntimeError("descriptor load failed")

    backend = PluginBackendDescriptor(
        plugin_id="packet.module.throwing",
        display_name="Module Throwing",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=load_descriptors,
    )
    module = SimpleNamespace(
        PLUGIN_CONTRACT_MANIFEST=PluginContractManifest(
            data_type_families=families,
            data_types=data_types,
        ),
        PLUGIN_BACKENDS=(backend,),
    )
    registry = NodeRegistry()

    loaded = plugin_loader._register_module_plugins(
        module,
        registry,
        "packet.module.throwing",
    )

    assert loaded == []
    assert registry.data_types.get("Packet.Module.Throwing") is None
    assert registry.spec_or_none("packet.module.throwing") is None
    assert registry.plugin_contract_manifest("packet.module.throwing") is None


def test_multi_backend_modules_require_backend_owned_type_contracts() -> None:
    module_families, module_types = _packet_data_type_contract(
        family_id="packet_module_ambiguous",
        type_id="Packet.Module.Ambiguous",
    )
    first_families, first_types = _packet_data_type_contract(
        family_id="packet_backend_first",
        type_id="Packet.Backend.First",
    )
    second_families, second_types = _packet_data_type_contract(
        family_id="packet_backend_second",
        type_id="Packet.Backend.Second",
    )
    first_backend = PluginBackendDescriptor(
        plugin_id="packet.backend.first",
        display_name="First Backend",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=lambda: (
            _typed_packet_descriptor(
                "packet.backend.first",
                "Packet.Backend.First",
            ),
        ),
        data_type_families=first_families,
        data_types=first_types,
    )
    second_backend = PluginBackendDescriptor(
        plugin_id="packet.backend.second",
        display_name="Second Backend",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=lambda: (
            _typed_packet_descriptor(
                "packet.backend.second",
                "Packet.Backend.Second",
            ),
        ),
        data_type_families=second_families,
        data_types=second_types,
    )
    registry = NodeRegistry()

    with pytest.raises(TypeError, match="multi-backend modules"):
        plugin_loader._register_module_plugins(
            SimpleNamespace(
                PLUGIN_CONTRACT_MANIFEST=PluginContractManifest(
                    data_type_families=module_families,
                    data_types=module_types,
                ),
                PLUGIN_BACKENDS=(first_backend, second_backend),
            ),
            registry,
            "packet.module.ambiguous",
        )

    assert registry.data_types.get("Packet.Module.Ambiguous") is None
    assert registry.spec_or_none("packet.backend.first") is None
    assert registry.spec_or_none("packet.backend.second") is None

    loaded = plugin_loader._register_module_plugins(
        SimpleNamespace(PLUGIN_BACKENDS=(first_backend, second_backend)),
        registry,
        "packet.module.explicit",
    )

    assert loaded == ["packet.backend.first", "packet.backend.second"]
    assert registry.data_types.get("Packet.Backend.First") is not None
    assert registry.data_types.get("Packet.Backend.Second") is not None




def test_plugin_backend_failure_does_not_leave_partial_type_contribution() -> None:
    families, data_types = _packet_data_type_contract(
        family_id="packet_invalid",
        type_id="Packet.Invalid.Value",
    )
    invalid_descriptor = _typed_packet_descriptor(
        "packet.invalid",
        "Packet.Unknown",
    )
    backend = PluginBackendDescriptor(
        plugin_id="packet.invalid",
        display_name="Invalid Backend",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=lambda: (invalid_descriptor,),
        data_type_families=families,
        data_types=data_types,
    )

    registry = NodeRegistry()
    loaded = plugin_loader.register_plugin_backends(
        (backend,),
        registry,
        "packet.invalid",
    )

    assert loaded == []
    assert registry.spec_or_none("packet.invalid") is None
    assert registry.data_types.get("Packet.Invalid.Value") is None
    assert registry.plugin_contract_manifest("packet.invalid") is None


def test_plugin_backend_type_conflict_does_not_leave_partial_descriptor() -> None:
    registry = NodeRegistry()
    owner_families, owner_types = _packet_data_type_contract(
        family_id="packet_owner",
        type_id="Packet.Shared.Value",
    )
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=owner_families,
            data_types=owner_types,
        ),
        (),
        owner_id="packet.owner",
    )
    conflict_families, conflict_types = _packet_data_type_contract(
        family_id="packet_conflict",
        type_id="Packet.Shared.Value",
    )
    backend = PluginBackendDescriptor(
        plugin_id="packet.conflict",
        display_name="Conflicting Backend",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=lambda: (
            _typed_packet_descriptor("packet.conflict", "Packet.Shared.Value"),
        ),
        data_type_families=conflict_families,
        data_types=conflict_types,
    )

    loaded = plugin_loader.register_plugin_backends(
        (backend,),
        registry,
        "packet.conflict",
    )

    assert loaded == []
    assert registry.spec_or_none("packet.conflict") is None
    assert registry.data_types.owner_of("Packet.Shared.Value") == "packet.owner"
    assert not any(
        record.get("family_id") == "packet_conflict"
        for record in registry.data_types.snapshot()
    )


def test_plugin_backend_descriptor_publishes_toolchain_runtime_artifact_and_surface_contracts() -> None:
    toolchain = ToolchainSpec(
        toolchain_id="packet.python",
        display_name="Packet Python",
        kind="python",
        language="python",
        requirements=(
            ToolchainRequirementSpec(
                requirement_id="packet.optional.lib",
                kind="python_module",
                import_name="packet_optional",
                version_spec=">=1.0",
                optional=True,
            ),
        ),
    )
    artifact = ArtifactDescriptor(
        artifact_id="packet.compiled.extension",
        kind="shared_library",
        path="build/packet_node.pyd",
        runtime_backend_id="packet.external",
        toolchain_id=toolchain.toolchain_id,
        platform_tags=("win_amd64",),
    )
    surface = SurfaceCapabilitySpec(
        capability_id="packet.viewer_surface",
        surface_family="viewer",
        runtime_backend_id="packet.external",
        fullscreen=True,
        input_modes=("pointer", "keyboard"),
    )
    runtime_backend = RuntimeBackendSpec(
        backend_id="packet.external",
        display_name="Packet External Runtime",
        kind="external_process",
        adapter_module="packet_runtime.adapter",
        adapter_factory="create_backend",
        transport="json-rpc",
        transport_revision=1,
        toolchain_ids=(toolchain.toolchain_id,),
        artifact_ids=(artifact.artifact_id,),
        surface_capability_ids=(surface.capability_id,),
    )
    backend = PluginBackendDescriptor(
        plugin_id="packet.contracts",
        display_name="Packet Contracts",
        get_availability=lambda: PluginAvailability.available("ready"),
        load_descriptors=lambda: (_packet_descriptor("packet.contracts", "Packet Contracts"),),
        runtime_backends=(runtime_backend,),
        toolchains=(toolchain,),
        artifacts=(artifact,),
        surface_capabilities=(surface,),
    )

    registry = NodeRegistry()
    loaded = plugin_loader.register_plugin_backends((backend,), registry, "packet.contracts")

    assert loaded == ["packet.contracts"]
    assert backend.contract_manifest == PluginContractManifest(
        runtime_backends=(runtime_backend,),
        toolchains=(toolchain,),
        artifacts=(artifact,),
        surface_capabilities=(surface,),
    )




def test_generic_addon_state_normalization_preserves_enabled_and_pending_restart() -> None:
    document = normalize_app_preferences_document(
        {
            "kind": "ea-node-editor/app-preferences",
            "version": 5,
            "addons": {
                "states": {
                    "packet.restart": {
                        "enabled": False,
                        "pending_restart": True,
                    }
                }
            },
        }
    )

    assert addon_state(document, "packet.restart") == {
        "enabled": False,
        "pending_restart": True,
    }


def test_set_addon_state_updates_the_generic_addon_state_store() -> None:
    document = set_addon_state(
        default_app_preferences_document(),
        "packet.toggle",
        enabled=False,
        pending_restart=True,
    )

    assert addon_state(document, "packet.toggle") == {
        "enabled": False,
        "pending_restart": True,
    }


def test_addon_registration_lookup_requires_canonical_addon_id() -> None:
    assert registered_addon_registration_by_id(ANSYS_DPF_ADDON_ID) is not None
    assert registered_addon_registration_by_id("ansys.dpf") is None
    assert registered_addon_registration_by_id("ansys_dpf") is None


def test_discover_addon_records_reports_generic_manifest_and_state(monkeypatch) -> None:
    restart_runtime_backend = RuntimeBackendSpec(
        backend_id="packet.restart.runtime",
        display_name="Packet Restart Runtime",
        kind="python",
        adapter_module="packet.restart.runtime",
        adapter_factory="create_runtime",
    )
    available_backend = PluginBackendDescriptor(
        plugin_id="packet.restart",
        display_name="Packet Restart Add-On",
        get_availability=lambda: PluginAvailability.available("ready"),
        load_descriptors=lambda: (_packet_descriptor("packet.restart.node", "Restart Node"),),
    )
    unavailable_backend = PluginBackendDescriptor(
        plugin_id="packet.unavailable",
        display_name="Packet Unavailable Add-On",
        get_availability=lambda: PluginAvailability.missing_dependency(
            "packet.unavailable.dep",
            summary="dependency missing",
        ),
        load_descriptors=lambda: (_packet_descriptor("packet.unavailable.node", "Unavailable Node"),),
    )
    registrations = (
        AddOnRegistration(
            manifest=AddOnManifest(
                addon_id="packet.restart",
                display_name="Packet Restart Add-On",
                apply_policy="restart_required",
                vendor="Packet Vendor",
                summary="Restart managed add-on",
                details="Requires a restart to finish applying.",
                dependencies=("packet.restart.dep",),
                runtime_backends=(restart_runtime_backend,),
            ),
            backend_module="packet.restart.module",
            backend_id="packet.restart",
            version_resolver_attr="resolve_version",
        ),
        AddOnRegistration(
            manifest=AddOnManifest(
                addon_id="packet.unavailable",
                display_name="Packet Unavailable Add-On",
                apply_policy="hot_apply",
                vendor="Packet Vendor",
                summary="Unavailable add-on",
                details="Stays unavailable until its dependency is installed.",
                dependencies=("packet.unavailable.dep",),
            ),
            backend_module="packet.unavailable.module",
            backend_id="packet.unavailable",
        ),
    )
    fake_modules = {
        "packet.restart.module": SimpleNamespace(
            PLUGIN_BACKENDS=(available_backend,),
            resolve_version=lambda: "9.9.9",
        ),
        "packet.unavailable.module": SimpleNamespace(
            PLUGIN_BACKENDS=(unavailable_backend,),
        ),
    }
    preferences = set_addon_state(
        default_app_preferences_document(),
        "packet.restart",
        enabled=False,
        pending_restart=True,
    )

    monkeypatch.setattr(addon_catalog, "REGISTERED_ADDON_REGISTRATIONS", registrations)
    monkeypatch.setattr(
        addon_catalog.importlib,
        "import_module",
        lambda module_name: fake_modules[module_name],
    )

    records = addon_catalog.discover_addon_records(preferences_document=preferences)
    records_by_id = {record.addon_id: record for record in records}

    restart_record = records_by_id["packet.restart"]
    assert restart_record.status == "pending_restart"
    assert restart_record.apply_policy == "restart_required"
    assert restart_record.vendor == "Packet Vendor"
    assert restart_record.version == "9.9.9"
    assert restart_record.summary == "Restart managed add-on"
    assert restart_record.details == "Requires a restart to finish applying."
    assert restart_record.provided_node_type_ids == ("packet.restart.node",)
    assert restart_record.runtime_backends == (restart_runtime_backend,)
    assert restart_record.manifest.contract_manifest.runtime_backends == (restart_runtime_backend,)

    unavailable_record = records_by_id["packet.unavailable"]
    assert unavailable_record.status == "unavailable"
    assert unavailable_record.apply_policy == "hot_apply"
    assert unavailable_record.version == ""
    assert unavailable_record.availability.missing_dependencies == ("packet.unavailable.dep",)
    assert unavailable_record.provided_node_type_ids == ()


def test_plugin_loader_addon_record_discovery_delegates_to_addon_catalog(monkeypatch) -> None:
    sentinel_records = (object(),)
    seen_documents: list[object] = []

    def fake_discover_addon_records(*, preferences_document=None):
        seen_documents.append(preferences_document)
        return sentinel_records

    preferences = default_app_preferences_document()
    monkeypatch.setattr(addon_catalog, "discover_addon_records", fake_discover_addon_records)

    assert plugin_loader.discover_addon_records(preferences_document=preferences) is sentinel_records
    assert seen_documents == [preferences]


def test_hot_apply_uses_runtime_coordinator_boundary_for_runtime_rebuild() -> None:
    class RecordingRuntimeCoordinator:
        def __init__(self) -> None:
            self.registry = NodeRegistry()
            self.calls: list[dict[str, object]] = []

        def rebuild_after_addon_apply(
            self,
            *,
            addon_id: str,
            preferences_document,
            app_preferences_store=None,
            extra_plugin_dirs=None,
        ):
            self.calls.append(
                {
                    "addon_id": addon_id,
                    "preferences_document": preferences_document,
                    "app_preferences_store": app_preferences_store,
                    "extra_plugin_dirs": extra_plugin_dirs,
                }
            )
            return self.registry

    coordinator = RecordingRuntimeCoordinator()

    result = apply_addon_enabled_state(
        ANSYS_DPF_ADDON_ID,
        enabled=False,
        preferences_document=default_app_preferences_document(),
        runtime_coordinator=coordinator,
    )

    assert result.registry is coordinator.registry
    assert coordinator.calls == [
        {
            "addon_id": ANSYS_DPF_ADDON_ID,
            "preferences_document": result.preferences_document,
            "app_preferences_store": None,
            "extra_plugin_dirs": None,
        }
    ]
    assert addon_state(result.preferences_document, ANSYS_DPF_ADDON_ID)["enabled"] is False


def test_hot_apply_failure_keeps_consumers_and_persisted_preference_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    preferences_path = tmp_path / "app_preferences.json"
    preferences_store = AppPreferencesStore(path_provider=lambda: preferences_path)
    original_document = set_addon_state(
        default_app_preferences_document(),
        ANSYS_DPF_ADDON_ID,
        enabled=True,
        pending_restart=False,
    )
    preferences_store.persist_document(original_document)

    active_registry = NodeRegistry()
    replacement_registry = NodeRegistry()
    active_serializer = object()
    consumers = SimpleNamespace(
        registry=active_registry,
        serializer=active_serializer,
    )

    class FailingScene:
        def __init__(self) -> None:
            self.registry = active_registry

        def rebuild_registry(self, registry) -> None:  # noqa: ANN001
            assert registry is replacement_registry
            raise RuntimeError("scene rebuild failed")

    def publish_registry(registry) -> None:  # noqa: ANN001
        consumers.registry = registry
        consumers.serializer = object()

    monkeypatch.setattr(
        "ea_node_editor.nodes.bootstrap.build_default_registry",
        lambda **_kwargs: replacement_registry,
    )

    scene = FailingScene()
    with pytest.raises(RuntimeError, match="scene rebuild failed"):
        apply_addon_enabled_state(
            ANSYS_DPF_ADDON_ID,
            enabled=False,
            app_preferences_store=preferences_store,
            preferences_document=original_document,
            graph_scene_bridge=scene,
            on_registry_rebuilt=publish_registry,
        )

    assert scene.registry is active_registry
    assert consumers.registry is active_registry
    assert consumers.serializer is active_serializer
    assert addon_state(
        preferences_store.load_document(),
        ANSYS_DPF_ADDON_ID,
    )["enabled"] is True


def test_hot_apply_publishes_consumers_then_persists_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    preferences_path = tmp_path / "app_preferences.json"
    calls: list[str] = []

    class RecordingPreferencesStore(AppPreferencesStore):
        def persist_document(self, document):  # noqa: ANN001
            persisted = super().persist_document(document)
            calls.append("persist")
            return persisted

    preferences_store = RecordingPreferencesStore(
        path_provider=lambda: preferences_path,
    )
    original_document = set_addon_state(
        default_app_preferences_document(),
        ANSYS_DPF_ADDON_ID,
        enabled=True,
        pending_restart=False,
    )
    preferences_store.persist_document(original_document)
    calls.clear()

    replacement_registry = NodeRegistry()

    class RecordingScene:
        registry = None

        def rebuild_registry(self, registry) -> None:  # noqa: ANN001
            self.registry = registry
            calls.append("scene")

    scene = RecordingScene()
    consumers = SimpleNamespace(registry=None, serializer=None)

    def publish_registry(registry) -> None:  # noqa: ANN001
        consumers.registry = registry
        consumers.serializer = object()
        calls.append("consumers")

    monkeypatch.setattr(
        "ea_node_editor.nodes.bootstrap.build_default_registry",
        lambda **_kwargs: replacement_registry,
    )

    result = apply_addon_enabled_state(
        ANSYS_DPF_ADDON_ID,
        enabled=False,
        app_preferences_store=preferences_store,
        preferences_document=original_document,
        graph_scene_bridge=scene,
        on_registry_rebuilt=publish_registry,
    )

    assert calls == ["scene", "consumers", "persist"]
    assert result.registry is replacement_registry
    assert scene.registry is replacement_registry
    assert consumers.registry is replacement_registry
    assert consumers.serializer is not None
    assert addon_state(
        preferences_store.load_document(),
        ANSYS_DPF_ADDON_ID,
    )["enabled"] is False
