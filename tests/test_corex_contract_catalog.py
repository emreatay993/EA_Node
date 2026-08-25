from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
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
from ea_node_editor.addons.mars.nodes import MARS_NODE_DESCRIPTORS
from ea_node_editor.addons.tabular_data.catalog import (
    load_tabular_data_plugin_descriptors,
)
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.registry import resolve_instance_ports, resolve_instance_spec


_PRE_CUTOVER_CATALOG = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "node_catalog"
    / "pre_cutover_non_dpf_catalog.json"
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
    descriptors = (
        *build_builtin_registry().all_descriptors(),
        *load_tabular_data_plugin_descriptors(),
        *MARS_NODE_DESCRIPTORS,
    )
    type_ids = [descriptor.spec.type_id for descriptor in descriptors]
    assert len(type_ids) == len(set(type_ids))

    catalog: list[dict[str, object]] = []
    for descriptor in sorted(descriptors, key=lambda item: item.spec.type_id):
        spec = descriptor.spec
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

    assert len(registry.all_specs()) == 123
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


def test_pre_cutover_non_dpf_catalog_is_unchanged() -> None:
    expected = json.loads(_PRE_CUTOVER_CATALOG.read_text(encoding="utf-8"))

    assert len(expected) == 133
    assert _current_non_dpf_catalog() == expected


def test_novice_plugin_sdk_migration_inventory_is_exhaustive() -> None:
    rows = {
        match["type_id"]: match.groupdict()
        for line in _MIGRATION_INVENTORY.read_text(encoding="utf-8").splitlines()
        if (match := _INVENTORY_ROW.match(line)) is not None
    }
    non_dpf = (
        *build_builtin_registry().all_descriptors(),
        *load_tabular_data_plugin_descriptors(),
        *MARS_NODE_DESCRIPTORS,
    )
    dpf = (
        *load_ansys_dpf_helper_plugin_descriptors(),
        *load_ansys_dpf_curated_plugin_descriptors(),
        *load_ansys_dpf_plot_plugin_descriptors(),
        *load_ansys_dpf_operator_plugin_descriptors(),
    )
    descriptors = (*non_dpf, *dpf)

    assert len(rows) == len(descriptors) == 938
    assert set(rows) == {descriptor.spec.type_id for descriptor in descriptors}
    assert {type_id for type_id, row in rows.items() if row["disposition"] == "DPF excluded"} == {
        descriptor.spec.type_id for descriptor in dpf
    }
    assert [row["disposition"] for row in rows.values()].count("convert") == 78
    assert [row["disposition"] for row in rows.values()].count("internal exception") == 55

    for descriptor in descriptors:
        row = rows[descriptor.spec.type_id]
        assert row["ports"] == (
            ", ".join(port.key for port in descriptor.spec.ports) or "—"
        )
        assert row["properties"] == (
            ", ".join(prop.key for prop in descriptor.spec.properties) or "—"
        )
        assert (Path(__file__).resolve().parents[1] / row["owner"]).is_file()
        assert (Path(__file__).resolve().parents[1] / row["test"]).is_file()
