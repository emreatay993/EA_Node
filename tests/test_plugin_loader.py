from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import stat
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
from ea_node_editor.nodes import bootstrap, plugin_loader
from ea_node_editor.nodes import plugin_generation
from ea_node_editor.nodes.core_data_types import GRAPH_DATA_TYPE_ID
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec
from ea_node_editor.nodes.plugin_contracts import (
    AddOnManifest,
    ArtifactDescriptor,
    PluginAvailability,
    PluginBackendDescriptor,
    PluginContractManifest,
    PluginDescriptor,
    RuntimeBackendSpec,
    SurfaceCapabilitySpec,
    ToolchainRequirementSpec,
    ToolchainSpec,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.plugin_generation import prune_plugin_generations
from ea_node_editor.runtime_contracts import (
    DataTypeFamilySpec,
    DataTypeSpec,
)


def _write_text(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


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


def _function_source(
    type_id: str,
    *,
    description: str = "",
    prelude: str = "",
    import_line: str = "",
) -> str:
    extra_import = f"{import_line}\n" if import_line else ""
    return f'''import corex
{extra_import}{prelude}
@corex.node(
    id={type_id!r},
    name="Static Node",
    category=("Tests",),
    description={description!r},
)
@corex.input("value", value_type=float)
@corex.output("result", value_type=float)
def static_node(ctx, value):
    return {{"result": value}}
'''


def _write_schema2_package(
    root: Path,
    *,
    name: str,
    sources: dict[str, str],
    modules: list[str],
    nodes: list[dict[str, str]],
) -> Path:
    package_dir = root / name
    source_records = []
    for relative_path, source in sources.items():
        source_path = _write_text(package_dir / relative_path, source)
        payload = source_path.read_bytes()
        source_records.append(
            {"path": relative_path, "sha256": hashlib.sha256(payload).hexdigest()}
        )
    manifest = {
        "schema_version": 2,
        "name": name,
        "version": "1.0.0",
        "author": "",
        "description": "",
        "modules": modules,
        "sources": source_records,
        "assets": [],
        "nodes": nodes,
    }
    _write_text(
        package_dir / "node_package.json",
        json.dumps(manifest, indent=2) + "\n",
    )
    return package_dir


def _write_function_package(
    root: Path,
    *,
    name: str,
    type_id: str,
    source: str,
) -> Path:
    return _write_schema2_package(
        root,
        name=name,
        sources={"nodes.py": source},
        modules=["nodes.py"],
        nodes=[{"id": type_id, "module": "nodes.py", "function": "static_node"}],
    )


def test_candidate_registry_statically_overrides_package_and_matches_final(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "installed"
    loose_type_id = "custom.candidate_loose.1234abcd"
    replaced_type_id = "custom.candidate_replaced.1234abcd"
    _write_text(installed_root / "loose.py", _function_source(loose_type_id))
    installed_package = _write_function_package(
        installed_root,
        name="candidate_package",
        type_id=replaced_type_id,
        source=_function_source(replaced_type_id, description="installed"),
    )
    installed_bytes = (installed_package / "nodes.py").read_bytes()
    marker = tmp_path / "executed.txt"
    replacement_source = _function_source(
        replaced_type_id,
        description="replacement",
        prelude=(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')"
        ),
    )
    staged_package = _write_function_package(
        tmp_path / "staged",
        name="candidate_package",
        type_id=replaced_type_id,
        source=replacement_source,
    )
    baseline = bootstrap.build_default_registry(include_public_plugins=False)
    monkeypatch.setattr(bootstrap, "plugins_dir", lambda: installed_root)

    candidate_root = tmp_path / "candidate-generations"
    candidate = bootstrap.build_plugin_candidate_registry(
        generation_root=candidate_root,
        staged_package_root=staged_package,
    )

    assert candidate.get_spec(replaced_type_id).description == "replacement"
    assert candidate.spec_or_none(loose_type_id) is not None
    assert (installed_package / "nodes.py").read_bytes() == installed_bytes
    assert not marker.exists()
    assert {
        Path(bundle.approved_generation_root).parent
        for bundle in candidate.plugin_bundle_refs()
    } == {candidate_root.resolve()}
    assert candidate.data_types.fingerprint() == baseline.data_types.fingerprint()
    assert {
        spec.type_id
        for spec in candidate.all_specs()
        if candidate.python_function_ref_or_none(spec.type_id) is None
    } == {
        spec.type_id
        for spec in baseline.all_specs()
        if baseline.python_function_ref_or_none(spec.type_id) is None
    }

    final_root = tmp_path / "final-installed"
    _write_text(final_root / "loose.py", _function_source(loose_type_id))
    _write_function_package(
        final_root,
        name="candidate_package",
        type_id=replaced_type_id,
        source=replacement_source,
    )
    monkeypatch.setattr(bootstrap, "plugins_dir", lambda: final_root)
    final = bootstrap.build_plugin_candidate_registry(
        generation_root=tmp_path / "canonical-generations",
    )

    assert candidate.plugin_fingerprint() == final.plugin_fingerprint()
    assert {
        bundle.bundle_digest for bundle in candidate.plugin_bundle_refs()
    } == {bundle.bundle_digest for bundle in final.plugin_bundle_refs()}
    assert not marker.exists()


def test_candidate_registry_rejects_conflict_outside_replaced_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "installed"
    replaced_type_id = "custom.replaced.1234abcd"
    retained_type_id = "custom.retained.1234abcd"
    _write_function_package(
        installed_root,
        name="replace_me",
        type_id=replaced_type_id,
        source=_function_source(replaced_type_id),
    )
    _write_function_package(
        installed_root,
        name="retain_me",
        type_id=retained_type_id,
        source=_function_source(retained_type_id),
    )
    staged_package = _write_function_package(
        tmp_path / "staged",
        name="replace_me",
        type_id=retained_type_id,
        source=_function_source(retained_type_id, description="conflict"),
    )
    monkeypatch.setattr(bootstrap, "plugins_dir", lambda: installed_root)

    with pytest.raises(ValueError, match="conflicts with an active node id"):
        bootstrap.build_plugin_candidate_registry(
            generation_root=tmp_path / "generations",
            staged_package_root=staged_package,
        )


def test_candidate_override_requires_exact_installed_package_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "installed"
    _write_function_package(
        installed_root,
        name="same-owner",
        type_id="custom.same_owner_old.1234abcd",
        source=_function_source("custom.same_owner_old.1234abcd"),
    )
    staged_package = _write_function_package(
        tmp_path / "staged",
        name="same_owner",
        type_id="custom.same_owner_new.1234abcd",
        source=_function_source("custom.same_owner_new.1234abcd"),
    )
    monkeypatch.setattr(bootstrap, "plugins_dir", lambda: installed_root)

    with pytest.raises(ValueError, match="owner is already active"):
        bootstrap.build_plugin_candidate_registry(
            generation_root=tmp_path / "generations",
            staged_package_root=staged_package,
        )






def test_loose_function_plugins_are_discovered_without_execution_and_materialized(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    generation_root = tmp_path / "generations"
    marker = tmp_path / "executed.txt"
    source_path = _write_text(
        plugin_root / "safe_node.py",
        _function_source(
            "custom.safe_node.1234abcd",
            prelude=(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')"
            ),
        ),
    )
    source_bytes = source_path.read_bytes()
    registry = NodeRegistry()

    result = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )

    assert result.type_ids == ("custom.safe_node.1234abcd",)
    assert len(result.bundles) == 1
    bundle = result.bundles[0]
    generation = Path(bundle.approved_generation_root)
    assert generation.parent == generation_root.resolve()
    assert (generation / "safe_node.py").read_bytes() == source_bytes
    assert (generation / "node_package.json").is_file()
    assert not marker.exists()
    assert registry.spec_or_none("custom.safe_node.1234abcd") is not None
    assert registry.descriptor_or_none("custom.safe_node.1234abcd") is None
    assert registry.plugin_bundle_refs() == (bundle,)
    assert registry.plugin_fingerprint() == result.plugin_fingerprint
    assert len(result.plugin_fingerprint) == 64
    with pytest.raises(RuntimeError, match="worker resolution"):
        registry.create("custom.safe_node.1234abcd")


def test_generation_reuse_and_source_changes_are_content_addressed(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    generation_root = tmp_path / "generations"
    source_path = _write_text(
        plugin_root / "scale.py",
        _function_source("custom.scale.1234abcd", description="first"),
    )

    first_registry = NodeRegistry()
    first = plugin_loader.discover_static_plugins(
        first_registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )
    first_bundle = first.bundles[0]
    first_generation = Path(first_bundle.approved_generation_root)
    first_bytes = (first_generation / "scale.py").read_bytes()

    second = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(plugin_root,),
        generation_root=generation_root,
    )
    assert second.bundles[0].bundle_digest == first_bundle.bundle_digest
    assert second.bundles[0].approved_generation_root == str(first_generation)
    assert second.plugin_fingerprint == first.plugin_fingerprint

    source_path.write_text(
        _function_source("custom.scale.1234abcd", description="second"),
        encoding="utf-8",
    )
    third_registry = NodeRegistry()
    third = plugin_loader.discover_static_plugins(
        third_registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )
    assert third.bundles[0].bundle_digest != first_bundle.bundle_digest
    assert third.plugin_fingerprint != first.plugin_fingerprint
    assert third_registry.get_spec("custom.scale.1234abcd").description == "second"
    assert (first_generation / "scale.py").read_bytes() == first_bytes

    source_path.write_text("raise RuntimeError('mutable source changed')\n", encoding="utf-8")
    assert third_registry.get_spec("custom.scale.1234abcd").description == "second"
    assert (first_generation / "scale.py").read_bytes() == first_bytes
    assert len(
        [
            path
            for path in generation_root.iterdir()
            if path.is_dir() and len(path.name) == 64
        ]
    ) == 2


def test_missing_import_keeps_node_visible_with_exact_locked_reason(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    missing_module = "codex_missing_dependency_7f31a9"
    _write_text(
        plugin_root / "missing.py",
        _function_source(
            "custom.missing.1234abcd",
            import_line=f"import {missing_module}",
        ),
    )
    registry = NodeRegistry()

    result = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=tmp_path / "generations",
    )

    reason = f"{missing_module} is not included in this COREX bundle."
    assert result.type_ids == ("custom.missing.1234abcd",)
    assert registry.spec_or_none("custom.missing.1234abcd") is not None
    assert registry.unavailable_reason("custom.missing.1234abcd") == reason
    assert result.bundles[0].unavailable_reason == reason
    assert str(tmp_path) not in reason
    with pytest.raises(RuntimeError, match=re.escape(reason)):
        registry.create("custom.missing.1234abcd")


def test_invalid_and_conflicting_loose_bundles_fail_closed_without_side_effects(
    tmp_path: Path,
    caplog,
) -> None:
    plugin_root = tmp_path / "plugins"
    generation_root = tmp_path / "generations"
    marker = tmp_path / "invalid-executed.txt"
    _write_text(
        plugin_root / "a_first.py",
        _function_source("custom.duplicate.1234abcd", description="first"),
    )
    _write_text(
        plugin_root / "b_duplicate.py",
        _function_source("custom.duplicate.1234abcd", description="second"),
    )
    _write_text(
        plugin_root / "c_invalid.py",
        f'''import corex
from pathlib import Path
Path({str(marker)!r}).write_text("executed", encoding="utf-8")
@corex.node(id="custom.invalid.1234abcd", name="Invalid", category=("Tests",))
@corex.number("factor", default=make_default())
def invalid(ctx, settings): return {{}}
''',
    )
    _write_text(
        plugin_root / "d_partial.py",
        '''import corex
@corex.node(id="custom.partial_good.1234abcd", name="Good", category=("Tests",))
def good(ctx): return {}
@corex.node(id="custom.partial_bad.1234abcd", name="Bad", category=("Tests",))
@corex.output("value", value_type="Missing.Type")
def bad(ctx): return {"value": 1}
''',
    )
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)
    registry = NodeRegistry()

    result = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )

    assert result.type_ids == ("custom.duplicate.1234abcd",)
    assert registry.get_spec("custom.duplicate.1234abcd").description == "first"
    assert registry.spec_or_none("custom.invalid.1234abcd") is None
    assert registry.spec_or_none("custom.partial_good.1234abcd") is None
    assert registry.spec_or_none("custom.partial_bad.1234abcd") is None
    assert not marker.exists()
    assert str(tmp_path) not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)
    assert len([path for path in generation_root.iterdir() if len(path.name) == 64]) == 1


def test_schema2_package_is_static_and_schema1_directory_is_rejected(
    tmp_path: Path,
    caplog,
) -> None:
    plugin_root = tmp_path / "plugins"
    marker = tmp_path / "package-executed.txt"
    nodes_source = f'''import corex
from pathlib import Path
from .helpers import helper
Path({str(marker)!r}).write_text("executed", encoding="utf-8")
@corex.node(id="custom.package_node.1234abcd", name="Package Node", category=("Tests",))
@corex.input("value", value_type=float)
@corex.output("result", value_type=float)
def package_node(ctx, value): return {{"result": helper(value)}}
'''
    package_dir = _write_schema2_package(
        plugin_root,
        name="static_package",
        sources={"nodes.py": nodes_source, "helpers.py": "def helper(value): return value\n"},
        modules=["nodes.py"],
        nodes=[
            {
                "id": "custom.package_node.1234abcd",
                "module": "nodes.py",
                "function": "package_node",
            }
        ],
    )
    legacy_dir = plugin_root / "legacy_package"
    _write_text(
        legacy_dir / "node_package.json",
        json.dumps({"name": "legacy_package", "version": "1.0.0", "nodes": []}),
    )
    caplog.set_level(logging.WARNING, logger=plugin_loader.__name__)
    registry = NodeRegistry()

    result = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=tmp_path / "generations",
    )

    assert result.type_ids == ("custom.package_node.1234abcd",)
    bundle = result.bundles[0]
    generation = Path(bundle.approved_generation_root)
    assert (generation / "nodes.py").read_text(encoding="utf-8") == nodes_source
    assert (generation / "helpers.py").read_text(encoding="utf-8") == (
        package_dir / "helpers.py"
    ).read_text(encoding="utf-8")
    assert not marker.exists()
    assert registry.spec_or_none("custom.package_node.1234abcd") is not None
    assert "plugin:package:legacy_package" in caplog.text
    assert str(tmp_path) not in caplog.text

    direct_registry = NodeRegistry()
    assert plugin_loader.discover_package_plugins(
        package_dir,
        direct_registry,
        generation_root=tmp_path / "direct-generations",
        descriptor_overrides=None,
    ) == ["custom.package_node.1234abcd"]
    with pytest.raises(TypeError, match="Descriptor overrides"):
        plugin_loader.discover_package_plugins(
            package_dir,
            NodeRegistry(),
            generation_root=tmp_path / "rejected-generations",
            descriptor_overrides={},
        )


def test_dotted_bundled_source_and_dev_only_imports_are_locked(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    nodes_source = '''import corex
from .helpers.missing import value
@corex.node(id="custom.dotted.1234abcd", name="Dotted", category=("Tests",))
def dotted(ctx): return {}
'''
    _write_schema2_package(
        plugin_root,
        name="dotted_package",
        sources={"nodes.py": nodes_source, "helpers.py": "VALUE = 1\n"},
        modules=["nodes.py"],
        nodes=[
            {
                "id": "custom.dotted.1234abcd",
                "module": "nodes.py",
                "function": "dotted",
            }
        ],
    )
    _write_text(
        plugin_root / "dev_only.py",
        _function_source(
            "custom.dev_only.1234abcd",
            import_line="import pytest",
        ),
    )
    registry = NodeRegistry()

    result = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=tmp_path / "generations",
    )

    assert set(result.type_ids) == {
        "custom.dev_only.1234abcd",
        "custom.dotted.1234abcd",
    }
    assert registry.unavailable_reason("custom.dotted.1234abcd") == (
        "helpers.missing is not included in this COREX bundle."
    )
    assert registry.unavailable_reason("custom.dev_only.1234abcd") == (
        "pytest is not included in this COREX bundle."
    )


def test_symlinked_discovery_roots_and_entries_are_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    linked_root = tmp_path / "linked-root"
    _write_text(
        linked_root / "outside.py",
        _function_source("custom.outside.1234abcd"),
    )
    regular_root = tmp_path / "regular-root"
    linked_file = _write_text(
        regular_root / "linked.py",
        _function_source("custom.linked_entry.1234abcd"),
    )
    simulated_symlinks = {linked_root, linked_file}
    monkeypatch.setattr(
        plugin_loader,
        "_is_reparse_point",
        lambda path: path in simulated_symlinks,
    )

    registry = NodeRegistry()
    result = plugin_loader.discover_static_plugins(
        registry,
        roots=(linked_root, regular_root),
        generation_root=tmp_path / "generations",
    )

    assert result.type_ids == ()
    assert registry.spec_or_none("custom.outside.1234abcd") is None


def test_path_alias_detector_recognizes_posix_symlink_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        plugin_generation.os,
        "lstat",
        lambda _path: SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0),
    )

    assert plugin_generation._is_reparse_point(Path("alias"))  # noqa: SLF001


def test_oversized_sources_and_unbounded_roots_fail_before_full_discovery(
    tmp_path: Path,
) -> None:
    oversized_root = tmp_path / "oversized"
    oversized_root.mkdir()
    (oversized_root / "huge.py").write_bytes(b"#" * (256 * 1024 + 1))
    oversized = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(oversized_root,),
        generation_root=tmp_path / "oversized-generations",
    )
    assert oversized.type_ids == ()

    crowded_root = tmp_path / "crowded"
    crowded_root.mkdir()
    for index in range(513):
        (crowded_root / f"empty-{index}.txt").touch()
    crowded = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(crowded_root,),
        generation_root=tmp_path / "crowded-generations",
    )
    assert crowded.type_ids == ()


def test_package_aggregate_limit_rejects_before_reading_excess_member(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_dir = tmp_path / "plugins" / "aggregate_package"
    source_path = _write_text(package_dir / "nodes.py", "import corex\n")
    zero_digest = hashlib.sha256(b"\0" * (4 * 1024 * 1024)).hexdigest()
    assets = []
    for index in range(4):
        asset_path = package_dir / f"asset-{index}.png"
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        with asset_path.open("wb") as stream:
            stream.seek(4 * 1024 * 1024 - 1)
            stream.write(b"\0")
        assets.append({"path": asset_path.name, "sha256": zero_digest})
    manifest = {
        "schema_version": 2,
        "name": "aggregate_package",
        "version": "1.0.0",
        "modules": ["nodes.py"],
        "sources": [
            {
                "path": "nodes.py",
                "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            }
        ],
        "assets": assets,
        "nodes": [],
    }
    _write_text(package_dir / "node_package.json", json.dumps(manifest))
    calls: list[str] = []
    read_member = plugin_loader._read_package_member  # noqa: SLF001

    def recording_read_member(package_root, relative_path, *, limit):  # noqa: ANN001
        calls.append(relative_path)
        return read_member(package_root, relative_path, limit=limit)

    monkeypatch.setattr(plugin_loader, "_read_package_member", recording_read_member)

    with pytest.raises(ValueError, match="expanded size"):
        plugin_loader._package_manifest(package_dir)  # noqa: SLF001
    assert calls == ["nodes.py", "asset-0.png", "asset-1.png", "asset-2.png"]


def test_frozen_import_availability_uses_the_actual_bundle_importer(monkeypatch) -> None:
    monkeypatch.setattr(plugin_loader.sys, "frozen", True, raising=False)
    monkeypatch.setattr(plugin_loader.importlib.util, "find_spec", lambda _name: None)

    assert not plugin_loader._bundled_module_available("ansys")  # noqa: SLF001


def test_plugin_fingerprint_is_independent_of_install_and_generation_roots(
    tmp_path: Path,
) -> None:
    source = _function_source("custom.portable.1234abcd")
    root_a = tmp_path / "install-a" / "plugins"
    root_b = tmp_path / "install-b" / "plugins"
    _write_text(root_a / "portable.py", source)
    _write_text(root_b / "portable.py", source)

    first = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(root_a,),
        generation_root=tmp_path / "generations-a",
    )
    second = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(root_b,),
        generation_root=tmp_path / "generations-b",
    )

    assert first.plugin_fingerprint == second.plugin_fingerprint
    assert first.bundles[0].bundle_digest == second.bundles[0].bundle_digest
    assert (
        first.bundles[0].approved_generation_root
        != second.bundles[0].approved_generation_root
    )


def test_tampered_existing_generation_is_never_reused(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    generation_root = tmp_path / "generations"
    _write_text(
        plugin_root / "tamper.py",
        _function_source("custom.tamper.1234abcd"),
    )
    first = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(plugin_root,),
        generation_root=generation_root,
    )
    generation = Path(first.bundles[0].approved_generation_root)
    (generation / "tamper.py").write_text("tampered\n", encoding="utf-8")
    registry = NodeRegistry()

    second = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )

    assert second.type_ids == ()
    assert registry.spec_or_none("custom.tamper.1234abcd") is None


def test_symlinked_generation_member_is_never_accepted_as_immutable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plugin_root = tmp_path / "plugins"
    generation_root = tmp_path / "generations"
    _write_text(
        plugin_root / "alias.py",
        _function_source("custom.alias_generation.1234abcd"),
    )
    first = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(plugin_root,),
        generation_root=generation_root,
    )
    generation_source = Path(first.bundles[0].approved_generation_root) / "alias.py"
    monkeypatch.setattr(
        plugin_generation,
        "_is_reparse_point",
        lambda path: path == generation_source,
    )

    registry = NodeRegistry()
    second = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )

    assert second.type_ids == ()
    assert registry.spec_or_none("custom.alias_generation.1234abcd") is None


def test_hard_linked_generation_member_is_never_accepted_as_immutable(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    generation_root = tmp_path / "generations"
    source_path = _write_text(
        plugin_root / "hardlink.py",
        _function_source("custom.hardlink_generation.1234abcd"),
    )
    first = plugin_loader.discover_static_plugins(
        NodeRegistry(),
        roots=(plugin_root,),
        generation_root=generation_root,
    )
    generation_source = Path(first.bundles[0].approved_generation_root) / "hardlink.py"
    generation_source.unlink()
    os.link(source_path, generation_source)
    assert generation_source.stat().st_nlink > 1

    registry = NodeRegistry()
    second = plugin_loader.discover_static_plugins(
        registry,
        roots=(plugin_root,),
        generation_root=generation_root,
    )

    assert second.type_ids == ()
    assert registry.spec_or_none("custom.hardlink_generation.1234abcd") is None


def test_generation_pruning_preserves_active_referenced_and_unknown_directories(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generation_root = tmp_path / "generations"
    active = "a" * 64
    referenced = "b" * 64
    inactive = "c" * 64
    aliased = "d" * 64
    for name in (active, referenced, inactive, aliased, "manual-not-a-generation"):
        _write_text(generation_root / name / "marker.txt", name)
    monkeypatch.setattr(
        plugin_generation,
        "_is_reparse_point",
        lambda path: path == generation_root / aliased,
    )

    removed = prune_plugin_generations(
        generation_root,
        active_digests=(active,),
        referenced_digests=(referenced,),
    )

    assert removed == (inactive,)
    assert (generation_root / active).is_dir()
    assert (generation_root / referenced).is_dir()
    assert not (generation_root / inactive).exists()
    assert (generation_root / aliased).is_dir()
    assert (generation_root / "manual-not-a-generation").is_dir()


def test_public_loader_has_no_entry_point_or_import_execution_surface() -> None:
    source = Path(plugin_loader.__file__).read_text(encoding="utf-8")
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    assert "ENTRY_POINT_GROUP" not in source
    assert ".load()" not in source
    assert "exec_module" not in source
    assert "ea_node_editor.plugins" not in pyproject


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
    replacement_registry.set_addon_runtime_config(((ANSYS_DPF_ADDON_ID, False),))
    active_serializer = object()
    consumers = SimpleNamespace(
        registry=active_registry,
        serializer=active_serializer,
    )

    class FailingScene:
        def __init__(self) -> None:
            self.registry = active_registry

        def replace_registry(self, registry) -> None:  # noqa: ANN001
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
    replacement_registry.set_addon_runtime_config(((ANSYS_DPF_ADDON_ID, False),))

    class RecordingScene:
        registry = None

        def replace_registry(self, registry) -> None:  # noqa: ANN001
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
