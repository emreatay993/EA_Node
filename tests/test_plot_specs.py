# Purpose: Prove generic Plot metadata imports, isolated defaults, and role policies.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_specs.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ea_node_editor.nodes.builtins.plot import specs


@pytest.mark.parametrize("module", [
    "ea_node_editor.nodes.builtins.plot",
    "ea_node_editor.nodes.builtins.plot.specs",
    "ea_node_editor.nodes.builtins.plot.property_edit_adapter",
])
def test_plot_metadata_imports_do_not_load_execution_or_optional_libraries(module: str) -> None:
    code = """
import importlib, sys
importlib.import_module(sys.argv[1])
for prefix in ('numpy', 'matplotlib', 'pyarrow', 'pyvista', 'pyqtgraph',
               'ea_node_editor.nodes.builtins.plot.generic',
               'ea_node_editor.addons.tabular_data.loader_cache_service',
               'ea_node_editor.execution.plot_backend'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""
    result = subprocess.run([sys.executable, "-c", code, module], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_plot_specs_construct_independent_mutable_defaults() -> None:
    definition = specs.PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"]
    first_spec = specs.plot_node_spec(definition)
    first = specs.plot_property_defaults(first_spec)
    second = specs.plot_property_defaults(first_spec)
    other = specs.plot_property_defaults(specs.plot_node_spec(definition))
    first["axis_limits"]["x"][0] = 12
    first["log_scales"]["y"] = True
    first["tabular_mapping"]["y"] = ["edited"]
    first["plot_options"]["nested"] = []
    assert second == other
    assert second["axis_limits"]["x"] == [None, None]
    assert second["log_scales"]["y"] is False
    assert second["tabular_mapping"] == second["plot_options"] == {}


def test_mapping_metadata_is_immutable_and_keeps_distinct_orders() -> None:
    for kind in ("heatmap", "contour", "surface"):
        assert tuple(role[0] for role in specs.PLOT_TABULAR_EDITOR_ROLES[kind]) == ("z", "values", "columns")
        assert specs.PLOT_TABULAR_VALIDATION_KEYS[kind] == ("values", "z")
    with pytest.raises(TypeError):
        specs.PLOT_TABULAR_EDITOR_ROLES["bar"] = ()
    with pytest.raises(TypeError):
        specs.PLOT_TABULAR_VALIDATION_KEYS["bar"] = ()
    assert "scatter" not in specs.PLOT_TABULAR_EDITOR_ROLES
    assert "line" not in specs.PLOT_TABULAR_EDITOR_ROLES


@pytest.mark.parametrize("kind, expected", [
    ("bar", (("x", "X Column", "single"), ("category", "Category Column", "single"), ("y", "Y Columns", "multi"))),
    ("histogram", (("values", "Value Columns", "multi"),)),
    ("point_cloud", (("x", "X Column", "single"), ("y", "Y Column", "single"), ("z", "Z Column", "single"))),
    ("streamlines", (("x", "X Column", "single"), ("y", "Y Column", "single"), ("z", "Z Column", "single"))),
])
def test_mapping_editor_roles_keep_labels_and_cardinality(kind, expected) -> None:
    assert specs.PLOT_TABULAR_EDITOR_ROLES[kind] == (*expected, ("columns", "Available Columns", "multi"))


@pytest.mark.parametrize("filename, expected_edges", [
    ("corex_plot_live_line.cxproj", 2),
    ("corex_plot_archive_exports.cxproj", 3),
    ("tabular_plot_showcase.cxproj", 18),
    ("tabular_plot_showcase_direct.cxproj", 11),
])
def test_authored_plot_examples_keep_all_edges_after_registry_loading(filename, expected_edges) -> None:
    import json
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.persistence.serializer import JsonProjectSerializer

    path = Path(__file__).resolve().parents[1] / "examples" / filename
    document = json.loads(path.read_text(encoding="utf-8"))
    source_ids = {edge["edge_id"] for workspace in document["workspaces"] for edge in workspace["edges"]}
    assert len(source_ids) == expected_edges
    project = JsonProjectSerializer(build_default_registry()).load(str(path))
    assert {edge_id for workspace in project.workspaces.values() for edge_id in workspace.edges} == source_ids
    assert not any(node.type_id in {"plot.line", "plot.scatter"}
                   for workspace in project.workspaces.values() for node in workspace.nodes.values())
