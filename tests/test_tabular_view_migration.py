# Purpose: Prove convert-and-flag at project/fragment boundaries without reviving preview hints.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_view_migration.py
from copy import deepcopy

from ea_node_editor.common.node_property_migrations import migrate_tabular_properties
from ea_node_editor.persistence.project_codec import JsonProjectCodec
from ea_node_editor.graph.fragment_payloads import fragment_node_from_payload, normalize_graph_fragment_payload
from ea_node_editor.nodes.bootstrap import build_default_registry


def old_properties():
    return {"path": "saved://source/data.npz", "selected_object": "temperature", "cache_policy": "source_direct",
            "array_slice_2d": {"row_offset": 0, "row_limit": 50, "column_offset": 0, "column_limit": 50},
            "tabular_selected_columns": ["A", "B"]}


def test_conversion_preserves_source_and_flags_prior_hints_without_applying_them():
    old = old_properties()
    original = deepcopy(old)
    current = migrate_tabular_properties("tabular.input", old)
    assert old == original
    assert current["path"] == old["path"]
    assert current["data_view"] == {"version": 1, "mode": "source", "member": "temperature"}
    assert "output" not in current["data_view"]
    assert current["data_view_migration_notice"]["previous_selection"]["array_slice_2d"]["row_limit"] == 50
    assert "selected_object" not in current and "array_slice_2d" not in current
    assert migrate_tabular_properties("tabular.input", current) == current
    current["data_view_migration_notice"] = {}
    assert migrate_tabular_properties("tabular.input", current)["data_view_migration_notice"] == {}


def test_current_configuration_wins_and_extraction_nodes_are_untouched():
    props = {**old_properties(), "data_view": {"version": 1, "mode": "array", "member": "new"}}
    current = migrate_tabular_properties("tabular.input", props)
    assert current["data_view"] == props["data_view"]
    assert "data_view_migration_notice" not in current
    for kind in ("tabular.table_filter", "tabular.array_slice_2d"):
        assert migrate_tabular_properties(kind, old_properties()) == old_properties()


def test_project_and_direct_fragment_import_convert_before_normalization():
    payload = {"type_id": "tabular.input", "properties": old_properties()}
    project = JsonProjectCodec._normalize_owned_node_mapping(deepcopy(payload))
    fragment = {**payload, "ref_id": "data", "title": "Data", "x": 0, "y": 0}
    node = fragment_node_from_payload(fragment)
    assert project["properties"] == node.properties


def test_new_nodes_start_with_full_output_and_no_notice():
    properties = build_default_registry().default_properties("tabular.input")
    assert properties["data_view"] == {"version": 1, "mode": "source"}
    assert properties["data_view_migration_notice"] == {}
    assert "array_slice_2d" not in properties
