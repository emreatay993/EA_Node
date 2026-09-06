from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
from pathlib import Path
import re

import pytest

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
from ea_node_editor.nodes.instance_resolution import (
    resolve_instance_ports,
    resolve_instance_spec,
)
from ea_node_editor.nodes.solution_provenance import trusted_solution_provenance_inputs
from tests.non_dpf_catalog_fixture import (
    CURRENT_CONTRACT_OVERLAY_PATH,
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
    r"(?P<disposition>convert|native function|internal exception|DPF excluded) \| "
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
        replace(
            declaration.spec,
            solution_provenance_inputs=trusted_solution_provenance_inputs(
                TABULAR_DATA_ADDON_ID,
                declaration.spec.type_id,
            ),
        )
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

    assert len(registry.all_specs()) == 129
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
    frozen = load_frozen_non_dpf_catalog()
    assert len(frozen) == 133
    effective = load_effective_non_dpf_catalog()
    assert len(effective) == 139
    current = _current_non_dpf_catalog()
    assert current == effective

    def representation_default(catalog: list[dict[str, object]]) -> object:
        viewer = next(row for row in catalog if row["spec"]["type_id"] == "model.viewer")
        return next(
            item["default"]
            for item in viewer["spec"]["properties"]
            if item["key"] == "representation"
        )

    assert representation_default(frozen) == "surface"
    assert representation_default(effective) == "surface_with_edges"
    assert representation_default(current) == "surface_with_edges"


def _any_port_endpoints(catalog: list[dict[str, object]]) -> set[str]:
    return {
        f"{row['spec']['type_id']}.{port['key']}"
        for row in catalog
        for port in row["resolved_default_ports"]
        if port["kind"] == "data"
        and "COREX.DataTypes.Any" in (port["data_type"], *port["accepted_data_types"])
    }


def test_default_resolved_non_dpf_any_ports_are_only_intentional_generic_ports() -> None:
    actual = _any_port_endpoints(_current_non_dpf_catalog())
    assert actual == {
        "core.if.true_value", "core.if.false_value", "core.if.result",
        "io.process_run.stdout", "io.process_run.stderr",
        "data.panel.input", "data.panel.output",
        "core.trigger.input", "core.trigger.output",
        "core.stream_gate.stream", "core.stream_gate.output_0", "core.stream_gate.output_1",
        "core.python_script.payload", "core.python_script.result",
        "core.subnode_input.pin", "core.subnode_output.pin",
        "media.panel._surface_source",
        "mars.batch_solve.files", "mars.run_job.files", "mars.time_history.files",
    }


def test_non_dpf_any_inventory_detects_an_accepted_type_leak() -> None:
    catalog = _current_non_dpf_catalog()
    baseline = _any_port_endpoints(catalog)
    file_write = next(row for row in catalog if row["spec"]["type_id"] == "io.file_write")
    data_port = next(port for port in file_write["resolved_default_ports"] if port["key"] == "data")
    data_port["accepted_data_types"].append("COREX.DataTypes.Any")
    assert _any_port_endpoints(catalog) - baseline == {"io.file_write.data"}


def test_default_resolved_non_dpf_accepted_types_never_repeat_the_primary() -> None:
    repeated = {
        f"{row['spec']['type_id']}.{port['key']}"
        for row in _current_non_dpf_catalog()
        for port in row["resolved_default_ports"]
        if port["data_type"] in port["accepted_data_types"]
    }
    assert repeated == set()


def test_current_contract_overlay_rejects_extra_drift_duplicate_unknown_and_enum_invalid(
    tmp_path: Path,
) -> None:
    base = json.loads(CURRENT_CONTRACT_OVERLAY_PATH.read_text(encoding="utf-8"))
    invalid_payloads = {
        "extra": {**base, "extra": True},
        "drift": {
            **base,
            "property_default_patches": {
                "model.viewer": {
                    "representation": {
                        "expected_default": "wireframe",
                        "replacement_default": "surface_with_edges",
                    }
                }
            },
        },
        "unknown": {
            **base,
            "property_default_patches": {
                "model.unknown": base["property_default_patches"]["model.viewer"]
            },
        },
        "enum_invalid": {
            **base,
            "property_default_patches": {
                "model.viewer": {
                    "representation": {
                        "expected_default": "surface",
                        "replacement_default": "invalid",
                    }
                }
            },
        },
        "port_drift": {
            **base,
            "port_contract_patches": {
                "core.constant": {
                    "value": {
                        **base["port_contract_patches"]["core.constant"]["value"],
                        "expected_data_type": "COREX.DataTypes.String",
                    }
                }
            },
        },
        "port_unknown": {
            **base,
            "port_contract_patches": {"unknown.node": {}},
        },
        "port_repeated_primary": {
            **base,
            "port_contract_patches": {
                "core.constant": {
                    "value": {
                        **base["port_contract_patches"]["core.constant"]["value"],
                        "replacement_accepted_data_types": ["COREX.DataTypes.JsonValue"],
                    }
                }
            },
        },
    }
    invalid_texts = {
        name: json.dumps(payload) for name, payload in invalid_payloads.items()
    }
    invalid_texts["duplicate"] = CURRENT_CONTRACT_OVERLAY_PATH.read_text(
        encoding="utf-8"
    ).replace(
        '"schema_version": 1,',
        '"schema_version": 1,\n  "schema_version": 1,',
        1,
    )

    for name, text in invalid_texts.items():
        overlay_path = tmp_path / f"{name}.json"
        overlay_path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError):
            load_effective_non_dpf_catalog(
                current_contract_overlay_path=overlay_path
            )


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

    assert len(specs) == 944
    assert len(executable) == 906
    assert Counter(spec.solution_reuse_scope for spec in executable) == {
        "durable": 29,
        "session": 27,
        "never": 850,
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

    assert len(rows) == 944
    assert len(specs) == 944
    current_type_ids = {spec.type_id for spec in specs}
    assert current_type_ids == set(rows)
    assert {
        type_id for type_id, row in rows.items() if row["disposition"] == "DPF excluded"
    } == {spec.type_id for spec in dpf}
    assert [row["disposition"] for row in rows.values()].count("convert") == 78
    assert [row["disposition"] for row in rows.values()].count("native function") == 8
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
