from __future__ import annotations

import importlib.metadata
import logging
from pathlib import Path

from ea_node_editor.nodes import plugin_loader
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.plugin_contracts import (
    PluginAvailability,
    PluginBackendDescriptor,
    PluginDescriptor,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import RuntimeArtifactRef


def _write_text(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


def _write_plugin(path: Path, *, type_id: str, display_name: str, class_name: str = "PacketPlugin") -> Path:
    return _write_text(
        path,
        f"""
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class {class_name}:
    def spec(self):
        return NodeTypeSpec(
            type_id={type_id!r},
            display_name={display_name!r},
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
    _write_text(package_dir / "helper.py", 'DISPLAY_NAME = "Package Directory Plugin"\n')
    _write_text(
        package_dir / "package_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class PackagePlugin:
    def spec(self):
        return NodeTypeSpec(
            type_id="packet.package",
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
    _write_text(package_dir / "helper.py", 'DISPLAY_NAME = "Package Directory Plugin"\n')
    _write_text(
        package_dir / "package_plugin.py",
        """
from .helper import DISPLAY_NAME
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class PackagePlugin:
    def spec(self):
        return NodeTypeSpec(
            type_id="packet.package.single",
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

    registry = NodeRegistry()
    loaded = plugin_loader.discover_package_plugins(package_dir, registry)

    assert loaded == ["packet.package.single"]
    descriptor = registry.get_descriptor("packet.package.single")
    assert descriptor.provenance is not None
    assert descriptor.provenance.kind == "package"
    assert descriptor.provenance.package_root == package_dir.resolve()


def test_discover_and_load_plugins_continues_after_bad_modules(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_text(plugins_root / "broken_root.py", 'raise RuntimeError("boom")\n')
    _write_plugin(plugins_root / "good_root.py", type_id="packet.root.good", display_name="Good Root")

    package_dir = plugins_root / "installed_package"
    _write_text(package_dir / "bad_module.py", 'raise RuntimeError("broken package module")\n')
    _write_plugin(package_dir / "good_package.py", type_id="packet.package.good", display_name="Good Package")

    monkeypatch.setattr(plugin_loader, "plugins_dir", lambda: plugins_root)
    monkeypatch.setattr(plugin_loader, "_load_plugins_from_entry_points", lambda registry: [])
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)

    registry = NodeRegistry()
    loaded = plugin_loader.discover_and_load_plugins(registry)

    assert loaded == ["packet.root.good", "packet.package.good"]
    assert registry.spec_or_none("packet.root.good") is not None
    assert registry.spec_or_none("packet.package.good") is not None
    assert "Failed to load plugin file" in caplog.text


def test_discover_and_load_plugins_prefers_module_descriptors_without_constructor_probing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_text(
        plugins_root / "descriptor_plugin.py",
        """
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec


class ShouldNotBeScanned:
    def __init__(self):
        raise RuntimeError("legacy class probing should not run when PLUGIN_DESCRIPTORS is present")


class DescriptorPlugin:
    def spec(self):
        return NodeTypeSpec(
            type_id="packet.descriptor",
            display_name="Descriptor Plugin",
            category_path=("Packet Tests",),
            icon="packet",
            ports=(),
            properties=(),
        )

    def execute(self, ctx):
        return NodeResult()


PLUGIN_DESCRIPTORS = (
    (
        NodeTypeSpec(
            type_id="packet.descriptor",
            display_name="Descriptor Plugin",
            category_path=("Packet Tests",),
            icon="packet",
            ports=(),
            properties=(),
        ),
        DescriptorPlugin,
    ),
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

    class FakeEntryPoint:
        def __init__(self, name: str) -> None:
            self.name = name

        def load(self):
            return EntryPointPlugin

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


def test_discover_and_load_plugins_supports_neutral_runtime_contract_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugins_root = tmp_path / "plugins"
    _write_text(
        plugins_root / "runtime_contract_plugin.py",
        """
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec
from ea_node_editor.runtime_contracts import RuntimeArtifactRef


class RuntimeContractPlugin:
    def spec(self):
        return NodeTypeSpec(
            type_id="packet.runtime_contracts",
            display_name="Runtime Contracts",
            category_path=("Packet Tests",),
            icon="packet",
            ports=(),
            properties=(),
        )

    def execute(self, ctx):
        return NodeResult(
            outputs={"artifact": RuntimeArtifactRef.staged("packet_runtime_contract")},
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


def test_register_plugin_backends_skips_missing_dependency_backends_without_loading_descriptors() -> None:
    descriptor_loader_called = False

    def load_descriptors() -> tuple[PluginDescriptor, ...]:
        nonlocal descriptor_loader_called
        descriptor_loader_called = True
        return (_packet_descriptor("packet.optional", "Optional Backend"),)

    backend = PluginBackendDescriptor(
        plugin_id="packet.optional",
        display_name="Optional Backend",
        get_availability=lambda: PluginAvailability.missing_dependency(
            "packet.optional.dep",
            summary="optional dependency missing",
        ),
        load_descriptors=load_descriptors,
    )

    registry = NodeRegistry()
    loaded = plugin_loader.register_plugin_backends((backend,), registry, "packet.optional")

    assert loaded == []
    assert descriptor_loader_called is False
    assert registry.spec_or_none("packet.optional") is None


def test_register_plugin_backends_loads_available_backends() -> None:
    backend = PluginBackendDescriptor(
        plugin_id="packet.available",
        display_name="Available Backend",
        get_availability=lambda: PluginAvailability.available("available"),
        load_descriptors=lambda: (_packet_descriptor("packet.available", "Available Backend"),),
    )

    registry = NodeRegistry()
    loaded = plugin_loader.register_plugin_backends((backend,), registry, "packet.available")

    assert loaded == ["packet.available"]
    assert registry.get_spec("packet.available").display_name == "Available Backend"
