# Purpose: Prove immutable, bounded data-view recipes and lossless transport.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_data_view_contract.py
from dataclasses import FrozenInstanceError

import pytest

from ea_node_editor.addons.tabular_data.source_backends import TabularLoadOptions
from ea_node_editor.runtime_contracts import TabularDataRef, deserialize_runtime_value, serialize_runtime_value
from ea_node_editor.runtime_contracts.data_view import DataViewDefinition, projection_axes


def recipe():
    return {
        "version": 1, "mode": "table",
        "segments": [{"blocks": [{"id": "values", "member": "temperature", "labels_member": "nodes"}],
                      "coordinate": {"member": "time", "name": "Time", "unit": "s"}}],
        "query": {"filters": [{"column": "Sensor A", "op": "gt", "value": "9007199254740993"}]},
    }


def test_recipe_is_deeply_immutable_and_canonical():
    source = recipe()
    view = DataViewDefinition(source)
    digest = view.digest
    source["segments"][0]["blocks"][0]["member"] = "changed"
    detached = view.to_payload()
    detached["segments"].clear()
    assert view.digest == digest
    assert view.members == ("temperature", "nodes", "time")
    assert DataViewDefinition(view.to_payload()) == view
    with pytest.raises(FrozenInstanceError):
        view.canonical_json = "{}"


def test_new_view_has_full_output_and_no_query():
    view = DataViewDefinition()
    assert view.mode == "source"
    assert view.to_payload()["output"] == {"row_offset": 0, "row_limit": 0, "columns": []}
    assert not view.has_query


def test_recipe_reopens_from_lossless_ref_transport():
    view = DataViewDefinition(recipe())
    options = TabularLoadOptions(data_view=view)
    ref = TabularDataRef(ref_id="view", resolver_id="tabular.cache", object_id="view:" + view.digest,
                         metadata={"load_options": options.to_cache_payload()})
    restored = deserialize_runtime_value(serialize_runtime_value(ref))
    reopened = TabularLoadOptions.from_mapping(restored.metadata["load_options"])
    assert reopened.data_view == view
    assert reopened.data_view.to_payload()["query"]["filters"][0]["value"] == "9007199254740993"


@pytest.mark.parametrize("update", [
    {"version": 2}, {"version": True}, {"mode": "join"}, {"file": "other.npz"},
    {"output": {"row_limit": -1}}, {"output": {"row_limit": True}},
    {"output": {"columns": ["A", "A"]}},
    {"query": {"filters": [{"column": "A", "op": "eval", "value": "x"}]}},
    {"query": {"filters": [{"column": "A", "op": "gt", "value": 9007199254740993}]}},
    {"query": {"sort": [{"column": "A", "descending": "false"}]}},
    {"query": {"sort": [{"column": "A"}, {"column": "A"}]}},
])
def test_invalid_recipe_is_rejected(update):
    with pytest.raises((ValueError, TypeError)):
        DataViewDefinition({**recipe(), **update})


def test_empty_table_and_oversized_recipe_are_rejected():
    with pytest.raises(ValueError, match="segment"):
        DataViewDefinition({"version": 1, "mode": "table"})
    with pytest.raises(ValueError, match="size limit"):
        DataViewDefinition({"version": 1, "member": "a" * 50000})


def test_arrays_reject_table_rules_and_accept_explicit_slices():
    view = DataViewDefinition({"version": 1, "mode": "array", "member": "matrix", "array_slices": [[2, 8], [1, 3]]})
    assert view.to_payload()["array_slices"] == [[2, 8], [1, 3]]
    with pytest.raises(ValueError, match="table mode"):
        DataViewDefinition({"version": 1, "mode": "array", "query": {"sort": [{"column": "A"}]}})


def test_projection_requires_every_hidden_axis_and_valid_bounds():
    assert projection_axes({}, (8,)) == (0, None, {})
    assert projection_axes({"row": 2, "column": 0, "fixed": {"1": 3}}, (4, 5, 6)) == (2, 0, {1: 3})
    with pytest.raises(ValueError, match="every axis"):
        projection_axes({}, (4, 5, 6))
    with pytest.raises(ValueError, match="outside"):
        projection_axes({"fixed": {"2": 6}}, (4, 5, 6))
    with pytest.raises(ValueError, match="different"):
        projection_axes({"row": 0, "column": 0}, (4, 5))


def test_order_and_output_rules_change_identity():
    view = DataViewDefinition(recipe())
    changed = view.to_payload()
    changed["output"]["columns"] = ["Sensor B", "Sensor A"]
    assert DataViewDefinition(changed).digest != view.digest
    changed["output"]["columns"].reverse()
    assert DataViewDefinition(changed).digest != DataViewDefinition({**view.to_payload(), "output": {"columns": ["Sensor B", "Sensor A"]}}).digest
