from __future__ import annotations

from pathlib import Path

import pytest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import (
    NodeResult,
    NodeTypeSpec,
    PluginDescriptor,
    PluginProvenance,
    PortSpec,
)
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.node_title_icon_sources import (
    resolve_node_title_icon_source,
    title_icon_source_for_node_payload,
)


class _Plugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


def _spec(
    type_id: str,
    icon: str,
    *,
    runtime_behavior: str = "active",
    show_title_icon: bool = False,
) -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id=type_id,
        display_name=type_id.rsplit(".", 1)[-1].replace("_", " ").title(),
        category_path=("Tests",),
        icon=icon,
        ports=(PortSpec("value", "out", "data", "any"),),
        properties=(),
        runtime_behavior=runtime_behavior,  # type: ignore[arg-type]
        show_title_icon=show_title_icon,
    )


def _factory(spec: NodeTypeSpec):
    return lambda: _Plugin(spec)


def test_title_icon_resolver_accepts_supported_absolute_local_paths(tmp_path: Path) -> None:
    for suffix in (".svg", ".PNG", ".jpg", ".JPEG"):
        icon_path = tmp_path / f"icon{suffix}"
        icon_path.write_bytes(b"icon")

        assert resolve_node_title_icon_source(str(icon_path)) == icon_path.resolve().as_uri()


def test_title_icon_resolver_rejects_invalid_icon_values(tmp_path: Path) -> None:
    unsupported_path = tmp_path / "icon.gif"
    unsupported_path.write_bytes(b"icon")
    missing_path = tmp_path / "missing.svg"

    for value in (
        "",
        "warning",
        "https://example.test/icon.svg",
        "data:image/svg+xml;base64,PHN2Zy8+",
        str(unsupported_path),
        str(missing_path),
    ):
        assert resolve_node_title_icon_source(value) == ""


def test_title_icon_resolver_rejects_unreadable_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    icon_path = tmp_path / "unreadable.svg"
    icon_path.write_bytes(b"icon")
    real_open = Path.open

    def _raise_for_icon(path: Path, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        if path.resolve(strict=False) == icon_path.resolve():
            raise OSError("permission denied")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _raise_for_icon)

    assert resolve_node_title_icon_source(str(icon_path)) == ""


def test_title_icon_resolver_resolves_builtin_relative_paths_from_asset_root(tmp_path: Path) -> None:
    asset_root = tmp_path / "node_title_icons"
    icon_path = asset_root / "core" / "start.svg"
    icon_path.parent.mkdir(parents=True)
    icon_path.write_bytes(b"icon")
    outside_path = tmp_path / "outside.svg"
    outside_path.write_bytes(b"icon")

    assert (
        resolve_node_title_icon_source("core/start.svg", asset_root=asset_root)
        == icon_path.resolve().as_uri()
    )
    assert resolve_node_title_icon_source("../outside.svg", asset_root=asset_root) == ""


def test_title_icon_resolver_resolves_plugin_relative_paths_from_file_and_package_roots(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugin_root"
    package_root = tmp_path / "package_root"
    file_icon_path = plugin_root / "icons" / "file.svg"
    package_icon_path = package_root / "icons" / "package.png"
    file_icon_path.parent.mkdir(parents=True)
    package_icon_path.parent.mkdir(parents=True)
    file_icon_path.write_bytes(b"icon")
    package_icon_path.write_bytes(b"icon")

    file_provenance = PluginProvenance(
        kind="file",
        source_path=plugin_root / "file_plugin.py",
    )
    package_provenance = PluginProvenance(
        kind="package",
        source_path=package_root / "package_plugin.py",
        package_root=package_root,
        package_name="package_root",
    )

    assert (
        resolve_node_title_icon_source("icons/file.svg", provenance=file_provenance)
        == file_icon_path.resolve().as_uri()
    )
    assert (
        resolve_node_title_icon_source("icons/package.png", provenance=package_provenance)
        == package_icon_path.resolve().as_uri()
    )


def test_title_icon_resolver_does_not_use_cwd_for_entry_point_relative_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd_icon_path = tmp_path / "icons" / "entry.svg"
    cwd_icon_path.parent.mkdir(parents=True)
    cwd_icon_path.write_bytes(b"icon")
    monkeypatch.chdir(tmp_path)

    assert (
        resolve_node_title_icon_source(
            "icons/entry.svg",
            provenance=PluginProvenance(kind="entry_point", entry_point_name="entry"),
        )
        == ""
    )


def test_title_icon_source_for_node_payload_allows_only_active_and_compile_only_specs(
    tmp_path: Path,
) -> None:
    icon_path = tmp_path / "node.svg"
    icon_path.write_bytes(b"icon")

    active_spec = _spec("tests.title_icon.active", str(icon_path), runtime_behavior="active")
    compile_only_spec = _spec(
        "tests.title_icon.compile_only",
        str(icon_path),
        runtime_behavior="compile_only",
    )
    passive_spec = _spec("tests.title_icon.passive", str(icon_path), runtime_behavior="passive")

    assert title_icon_source_for_node_payload(active_spec) == icon_path.resolve().as_uri()
    assert title_icon_source_for_node_payload(compile_only_spec) == icon_path.resolve().as_uri()
    assert title_icon_source_for_node_payload(passive_spec) == ""


def test_title_icon_source_for_passive_spec_honors_show_title_icon_opt_in(
    tmp_path: Path,
) -> None:
    """Passive specs that set ``show_title_icon=True`` render their icon.

    Default-passive suppression exists for flowchart/planning/annotation/
    media families that draw their own body art; data-source-style passive
    nodes (``io.path_pointer``) opt back in via this flag.
    """
    icon_path = tmp_path / "passive.svg"
    icon_path.write_bytes(b"icon")

    opted_in = _spec(
        "tests.title_icon.passive.opted_in",
        str(icon_path),
        runtime_behavior="passive",
        show_title_icon=True,
    )
    default = _spec(
        "tests.title_icon.passive.default",
        str(icon_path),
        runtime_behavior="passive",
    )

    assert title_icon_source_for_node_payload(opted_in) == icon_path.resolve().as_uri()
    assert title_icon_source_for_node_payload(default) == ""


def test_title_icon_scene_payload_uses_registry_provenance_without_persistence_fields(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugin"
    active_icon_path = plugin_root / "icons" / "active.svg"
    compile_icon_path = plugin_root / "icons" / "compile.svg"
    active_icon_path.parent.mkdir(parents=True)
    active_icon_path.write_bytes(b"active")
    compile_icon_path.write_bytes(b"compile")
    provenance = PluginProvenance(
        kind="file",
        source_path=plugin_root / "plugin.py",
    )
    active_spec = _spec("tests.title_icon.active_payload", "icons/active.svg")
    compile_spec = _spec(
        "tests.title_icon.compile_payload",
        "icons/compile.svg",
        runtime_behavior="compile_only",
    )
    missing_spec = _spec("tests.title_icon.missing_payload", "icons/missing.svg")

    registry = NodeRegistry()
    for spec in (active_spec, compile_spec, missing_spec):
        registry.register_descriptor(
            PluginDescriptor(
                spec=spec,
                factory=_factory(spec),
                provenance=provenance,
            )
        )

    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    for index, spec in enumerate((active_spec, compile_spec, missing_spec)):
        model.add_node(workspace_id, spec.type_id, spec.display_name, 80.0 + index * 160.0, 90.0)

    builder = GraphScenePayloadBuilder()
    nodes_payload, _backdrops, _minimap, _edges = builder.rebuild_partitioned_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=None,
    )
    payload_by_type = {payload["type_id"]: payload for payload in nodes_payload}

    assert payload_by_type[active_spec.type_id]["icon_source"] == active_icon_path.resolve().as_uri()
    assert payload_by_type[compile_spec.type_id]["icon_source"] == compile_icon_path.resolve().as_uri()
    assert payload_by_type[missing_spec.type_id]["icon_source"] == ""
    first_node = model.active_workspace.nodes[next(iter(model.active_workspace.nodes))]
    assert not hasattr(first_node, "icon_source")
