# Purpose: Prove the exact T15 function cutover and T16 trusted exception boundary.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_remaining_builtin_function_migration.py

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from ea_node_editor.addons.ansys_dpf import catalog as ansys_dpf_catalog
from ea_node_editor.nodes import builtin_catalog
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.function_plugin import INTERNAL_BUILTIN_FUNCTION_OWNER_ID
from ea_node_editor.nodes.plugin_contracts import PluginAvailability
from ea_node_editor.nodes.registry import PythonFunctionEntry, TrustedFactoryEntry
from ea_node_editor.runtime_contracts import TypedInlineValue
from tests.non_dpf_catalog_fixture import load_effective_non_dpf_catalog


_T15_CONVERTED_TYPE_IDS = (
    "ai.create_vector_collection",
    "ai.inspect_vector_collection",
    "ai.large_language_model",
    "ai.sqlite_vector_database",
    "core.constant",
    "core.logger",
    "data.boolean_toggle",
    "data.number_slider",
    "data.panel",
    "data.select",
    "engineering.cad_import",
    "engineering.fe_import",
    "fea.force",
    "fea.load_container",
    "geometry.construct_group",
    "geometry.construct_transform",
    "geometry.cylinder",
    "geometry.deconstruct_transform",
    "math.construct_interval",
    "mesh.deconstruct_mesh_face",
    "model.viewer",
    "optimization.construct_design",
    "optimization.construct_parameters",
    "optimization.construct_responses",
    "reference.plane_container",
    "reporting.markdown_flowchart",
    "reporting.markdown_flowchart_node",
    "security.windows_authentication",
    "utilities.construct_view",
    "utilities.deconstruct_view",
)
_MIGRATION_INVENTORY = (
    Path(__file__).parents[1]
    / "docs"
    / "specs"
    / "requirements"
    / "COREX_NOVICE_PLUGIN_SDK_MIGRATION_INVENTORY.md"
)
_INTERNAL_EXCEPTION_ROW = re.compile(
    r"^\| `(?P<type_id>[^`]+)` \| internal exception \|"
)
_DPF_EXCLUDED_ROW = re.compile(
    r"^\| `(?P<type_id>[^`]+)` \| DPF excluded \|"
)


def test_exact_t15_entries_match_golden_and_leave_exact_exception_set(
    tmp_path: Path,
) -> None:
    registry = build_builtin_registry(generation_root=tmp_path / "generations")
    golden_rows = load_effective_non_dpf_catalog()
    expected = {
        row["spec"]["type_id"]: row["spec"]
        for row in golden_rows
        if row["spec"]["type_id"] in _T15_CONVERTED_TYPE_IDS
    }

    assert len(golden_rows) == 131
    assert len(_T15_CONVERTED_TYPE_IDS) == 30
    assert set(expected) == set(_T15_CONVERTED_TYPE_IDS)
    for type_id in _T15_CONVERTED_TYPE_IDS:
        entry = registry.get_entry(type_id)
        assert isinstance(entry, PythonFunctionEntry)
        assert entry.owner_id == INTERNAL_BUILTIN_FUNCTION_OWNER_ID
        assert registry.descriptor_or_none(type_id) is None
        assert json.loads(json.dumps(asdict(entry.spec))) == expected[type_id]

    bundle = registry.plugin_bundle_refs()
    assert len(bundle) == 1
    assert bundle[0].owner_id == INTERNAL_BUILTIN_FUNCTION_OWNER_ID
    assert len(bundle[0].functions) == 68
    assert set(registry.all_python_function_refs()) == set(bundle[0].functions)

    expected_exceptions = {
        match["type_id"]
        for line in _MIGRATION_INVENTORY.read_text(encoding="utf-8").splitlines()
        if (match := _INTERNAL_EXCEPTION_ROW.match(line)) is not None
    }
    assert len(expected_exceptions) == 53
    actual_exceptions = {
        spec.type_id
        for spec in registry.all_specs()
        if isinstance(registry.get_entry(spec.type_id), TrustedFactoryEntry)
    }
    assert builtin_catalog._TRUSTED_BUILTIN_TYPE_IDS == expected_exceptions
    assert actual_exceptions == expected_exceptions
    assert registry.plugin_contract_manifest("corex.windows_authentication") is None


def test_t16_trusted_descriptor_allowlist_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        builtin_catalog,
        "_TRUSTED_BUILTIN_DESCRIPTORS",
        builtin_catalog._TRUSTED_BUILTIN_DESCRIPTORS[:-1],
    )

    with pytest.raises(
        RuntimeError,
        match="Trusted built-in descriptor allowlist mismatch",
    ):
        build_builtin_registry(generation_root=tmp_path / "generations")


def test_t16_dpf_backend_catalog_matches_exact_excluded_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_type_ids = {
        match["type_id"]
        for line in _MIGRATION_INVENTORY.read_text(encoding="utf-8").splitlines()
        if (match := _DPF_EXCLUDED_ROW.match(line)) is not None
    }
    monkeypatch.setattr(
        ansys_dpf_catalog,
        "get_ansys_dpf_plugin_availability",
        lambda: PluginAvailability.available(),
    )
    monkeypatch.setattr(
        ansys_dpf_catalog,
        "resolve_ansys_dpf_plugin_version",
        lambda: "t16-inventory",
    )
    ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()

    try:
        descriptors = ansys_dpf_catalog.ANSYS_DPF_PLUGIN_BACKEND.load_descriptors()
    finally:
        ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()
    actual_type_ids = tuple(descriptor.spec.type_id for descriptor in descriptors)

    assert len(expected_type_ids) == 805
    assert len(actual_type_ids) == len(set(actual_type_ids)) == 805
    assert set(actual_type_ids) == expected_type_ids


def test_t15_discovery_does_not_load_heavy_or_identity_dependencies(
    tmp_path: Path,
) -> None:
    code = """
import getpass
import json
from pathlib import Path
import sqlite3
import sys

def blocked(*_args, **_kwargs):
    raise RuntimeError("discovery executed a runtime helper")

getpass.getuser = blocked
sqlite3.connect = blocked

from ea_node_editor.nodes.bootstrap import build_builtin_registry

registry = build_builtin_registry(generation_root=Path(sys.argv[1]))
print(json.dumps({
    "count": len(registry.plugin_bundle_refs()[0].functions),
    "heavy": sorted(name for name in (
        "OCP", "numpy", "openpyxl", "paramiko", "pyvista", "vtk", "win32security"
    ) if name in sys.modules),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-E", "-c", code, str(tmp_path / "generations")],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {"count": 68, "heavy": []}


def test_t15_typed_carrier_defaults_are_normalized_values(tmp_path: Path) -> None:
    registry = build_builtin_registry(generation_root=tmp_path / "generations")
    plane_default = registry.get_spec("reference.plane_container").properties[0].default
    view_defaults = {
        prop.key: prop.default
        for prop in registry.get_spec("utilities.construct_view").properties
    }

    assert isinstance(plane_default, TypedInlineValue)
    assert plane_default.data_type_id == "COREX.DataTypes.Plane"
    assert isinstance(view_defaults["camera_position"], TypedInlineValue)
    assert isinstance(view_defaults["camera_target"], TypedInlineValue)
    assert isinstance(view_defaults["camera_up_vector"], TypedInlineValue)
    assert view_defaults["camera_position"].data_type_id == "COREX.DataTypes.Point3D"
    assert view_defaults["camera_target"].data_type_id == "COREX.DataTypes.Point3D"
    assert view_defaults["camera_up_vector"].data_type_id == "COREX.DataTypes.Vector3D"
