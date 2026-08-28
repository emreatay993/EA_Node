from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re

from ea_node_editor.addons.ansys_dpf.curated_catalog import (
    load_ansys_dpf_curated_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.helper_catalog import (
    load_ansys_dpf_helper_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.plot_catalog import (
    load_ansys_dpf_plot_plugin_descriptors,
)
from ea_node_editor.addons.mars.function_nodes import SOURCE as MARS_SOURCE
from ea_node_editor.addons.mars.metadata import MARS_ADDON_ID
from ea_node_editor.addons.tabular_data.function_nodes import SOURCE as TABULAR_SOURCE
from ea_node_editor.addons.tabular_data.metadata import TABULAR_DATA_ADDON_ID
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.plugin_declaration import discover_plugin_declarations
from ea_node_editor.nodes.registry import resolve_instance_ports, resolve_instance_spec
from tests.non_dpf_catalog_fixture import (
    FROZEN_CATALOG_PATH,
    FROZEN_CATALOG_SHA256,
    load_effective_non_dpf_catalog,
    load_frozen_non_dpf_catalog,
    load_solution_reuse_scopes,
)


_MIGRATION_INVENTORY = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "specs"
    / "requirements"
    / "COREX_NOVICE_PLUGIN_SDK_MIGRATION_INVENTORY.md"
)
_INVENTORY_ROW = re.compile(
    r"^\| `(?P<type_id>[^`]+)` \| "
    r"(?P<disposition>convert|internal exception|DPF excluded) \| "
    r"`(?P<owner>[^`]+)` \| (?P<ports>.*?) \| (?P<properties>.*?) \| "
    r".* \| `(?P<test>[^`]+)` \|$"
)


def _catalog_value(value: object) -> object:
    if callable(value):
        return True
    if is_dataclass(value):
        return {
            field.name: _catalog_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _catalog_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_catalog_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_catalog_value(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, Enum):
        return _catalog_value(value.value)
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"Unsupported catalog value: {type(value).__qualname__}")


def _current_non_dpf_catalog() -> list[dict[str, object]]:
    tabular_specs = tuple(
        declaration.spec
        for declaration in discover_plugin_declarations(
            TABULAR_SOURCE,
            filename="tabular_data.py",
            allow_reserved_ids=True,
            owner_id=TABULAR_DATA_ADDON_ID,
            allow_internal_metadata=True,
        )
    )
    mars_specs = tuple(
        declaration.spec
        for declaration in discover_plugin_declarations(
            MARS_SOURCE,
            filename="mars_nodes.py",
            allow_reserved_ids=True,
            owner_id=MARS_ADDON_ID,
            allow_internal_metadata=True,
        )
    )
    specs = (
        *build_builtin_registry().all_specs(),
        *tabular_specs,
        *mars_specs,
    )
    type_ids = [spec.type_id for spec in specs]
    assert len(type_ids) == len(set(type_ids))

    catalog: list[dict[str, object]] = []
    for spec in sorted(specs, key=lambda item: item.type_id):
        defaults = {property_spec.key: property_spec.default for property_spec in spec.properties}
        resolved_spec = resolve_instance_spec(spec, defaults)
        catalog.append(
            {
                "spec": _catalog_value(spec),
                "resolved_default_ports": _catalog_value(
                    resolve_instance_ports(resolved_spec, defaults)
                ),
            }
        )
    return catalog


def test_builtin_registry_contains_retained_corex_contract_families() -> None:
    registry = build_builtin_registry()

    assert len(registry.all_specs()) == 121
    for type_id in (
        "plot.signal",
        "geometry.cylinder",
        "reference.construct_point",
        "security.windows_authentication",
        "reporting.markdown_flowchart",
    ):
        assert registry.spec_or_none(type_id) is not None

    for data_type_id in (
        "COREX.DataTypes.Image",
        "COREX.DataTypes.Color",
        "COREX.DataTypes.Point3D",
        "COREX.Geometry.OCPBody",
        "COREX.DataTree.Path",
    ):
        assert registry.data_types.require(data_type_id).type_id == data_type_id


def test_frozen_non_dpf_catalog_plus_documentation_and_structural_overlays_matches_current() -> (
    None
):
    assert (
        hashlib.sha256(FROZEN_CATALOG_PATH.read_bytes()).hexdigest().upper()
        == FROZEN_CATALOG_SHA256
    )
    assert len(load_frozen_non_dpf_catalog()) == 133
    effective = load_effective_non_dpf_catalog()
    assert len(effective) == 131
    assert _current_non_dpf_catalog() == effective


def test_solution_reuse_classification_matches_all_shipped_rows() -> None:
    tabular_specs = tuple(
        declaration.spec
        for declaration in discover_plugin_declarations(
            TABULAR_SOURCE,
            filename="tabular_data.py",
            allow_reserved_ids=True,
            owner_id=TABULAR_DATA_ADDON_ID,
            allow_internal_metadata=True,
        )
    )
    mars_specs = tuple(
        declaration.spec
        for declaration in discover_plugin_declarations(
            MARS_SOURCE,
            filename="mars_nodes.py",
            allow_reserved_ids=True,
            owner_id=MARS_ADDON_ID,
            allow_internal_metadata=True,
        )
    )
    non_dpf = (*build_builtin_registry().all_specs(), *tabular_specs, *mars_specs)
    dpf = tuple(
        descriptor.spec
        for descriptor in (
            *load_ansys_dpf_helper_plugin_descriptors(),
            *load_ansys_dpf_curated_plugin_descriptors(),
            *load_ansys_dpf_plot_plugin_descriptors(),
            *load_ansys_dpf_operator_plugin_descriptors(),
        )
    )
    specs = (*non_dpf, *dpf)
    executable = tuple(spec for spec in specs if spec.runtime_behavior == "active")
    excluded = tuple(spec for spec in specs if spec.runtime_behavior != "active")

    assert len(specs) == 936
    assert len(executable) == 898
    assert Counter(spec.solution_reuse_scope for spec in executable) == {
        "durable": 29,
        "session": 27,
        "never": 842,
    }
    assert Counter(spec.runtime_behavior for spec in excluded) == {
        "passive": 35,
        "compile_only": 3,
    }
    assert len(dpf) == 805
    assert {spec.solution_reuse_scope for spec in dpf} == {"never"}
    assert {
        spec.type_id: spec.solution_reuse_scope for spec in specs
    } == load_solution_reuse_scopes()
    non_dpf_by_id = {spec.type_id: spec for spec in non_dpf}
    assert non_dpf_by_id["engineering.cad_import"].solution_reuse_scope == "session"
    assert non_dpf_by_id["model.viewer"].solution_reuse_scope == "session"


def test_novice_plugin_sdk_migration_inventory_is_exhaustive() -> None:
    rows = {
        match["type_id"]: match.groupdict()
        for line in _MIGRATION_INVENTORY.read_text(encoding="utf-8").splitlines()
        if (match := _INVENTORY_ROW.match(line)) is not None
    }
    tabular_specs = tuple(
        declaration.spec
        for declaration in discover_plugin_declarations(
            TABULAR_SOURCE,
            filename="tabular_data.py",
            allow_reserved_ids=True,
            owner_id=TABULAR_DATA_ADDON_ID,
            allow_internal_metadata=True,
        )
    )
    mars_specs = tuple(
        declaration.spec
        for declaration in discover_plugin_declarations(
            MARS_SOURCE,
            filename="mars_nodes.py",
            allow_reserved_ids=True,
            owner_id=MARS_ADDON_ID,
            allow_internal_metadata=True,
        )
    )
    non_dpf = (
        *build_builtin_registry().all_specs(),
        *tabular_specs,
        *mars_specs,
    )
    dpf = tuple(
        descriptor.spec
        for descriptor in (
            *load_ansys_dpf_helper_plugin_descriptors(),
            *load_ansys_dpf_curated_plugin_descriptors(),
            *load_ansys_dpf_plot_plugin_descriptors(),
            *load_ansys_dpf_operator_plugin_descriptors(),
        )
    )
    specs = (*non_dpf, *dpf)

    assert len(rows) == 936
    assert len(specs) == 936
    current_type_ids = {spec.type_id for spec in specs}
    assert current_type_ids == set(rows)
    assert {
        type_id for type_id, row in rows.items() if row["disposition"] == "DPF excluded"
    } == {spec.type_id for spec in dpf}
    assert [row["disposition"] for row in rows.values()].count("convert") == 78
    assert [row["disposition"] for row in rows.values()].count(
        "internal exception"
    ) == 53

    for spec in specs:
        row = rows[spec.type_id]
        assert row["ports"] == (
            ", ".join(port.key for port in spec.ports) or "—"
        )
        assert row["properties"] == (
            ", ".join(prop.key for prop in spec.properties) or "—"
        )
        assert (Path(__file__).resolve().parents[1] / row["owner"]).is_file()
        assert (Path(__file__).resolve().parents[1] / row["test"]).is_file()
