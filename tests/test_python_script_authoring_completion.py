# Purpose: Verify catalog-derived data-type guidance and incomplete decorator completion.
# Map: subsystems/nodes_registry_builtins.md
# Tests: this file

from __future__ import annotations

import pytest

from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.python_script_declaration import PYTHON_SCRIPT_DECORATOR_FIELDS
from ea_node_editor.runtime_contracts import DataTypeSpec
from ea_node_editor.runtime_contracts.scientific_values import ARRAY_VALUE_TYPE_ID, TABLE_VALUE_TYPE_ID
from ea_node_editor.ui.support.python_script_authoring import completions, decorator_choices, field_choices, type_choices


@pytest.fixture(scope="module")
def catalog():
    return build_builtin_registry().data_types


def test_picker_types_derive_from_catalog_and_explain_scientific_values(catalog) -> None:
    choices = type_choices(catalog)
    assert {item["type_id"] for item in choices} == {item.type_id for item in catalog.all_specs()}
    assert type_choices(catalog, "decimal")[0]["expression"] == "float"
    table = next(item for item in type_choices(catalog, "DataFrame") if item["type_id"] == TABLE_VALUE_TYPE_ID)
    array = next(item for item in type_choices(catalog, "NumPy") if item["type_id"] == ARRAY_VALUE_TYPE_ID)
    assert table["expression"] == repr(TABLE_VALUE_TYPE_ID)
    assert "pd.DataFrame" in table["example"] and "Single value" in table["description"]
    assert "np.array" in array["example"]
    assert {item["expression"] for item in type_choices(catalog, list_items=True)} == {"str", "int", "float", "corex.Color"}


def test_catalog_refresh_addon_and_missing_type(catalog) -> None:
    staged = catalog.fork()
    family = staged.all_specs()[0].family_id
    before = completions('@corex.input("x", value_type=', 28, staged)["catalog_fingerprint"]
    staged.register_many(types=(DataTypeSpec("Example.Types.Custom", "Custom sample", family, lambda _value: True, description="From installed add-on"),), owner_id="example")
    choice = type_choices(staged, "Custom sample")[0]
    assert choice["expression"] == "'Example.Types.Custom'"
    assert choice["owner_id"] == "example"
    assert staged.fingerprint() != before
    missing = type_choices(staged, current_type="Example.Types.Missing")[0]
    assert missing["missing"]


def test_form_fields_cover_validator_contract_and_preserve_omission() -> None:
    for item in decorator_choices():
        descriptors = field_choices(item["kind"], {"label": ""})
        assert {field["name"] for field in descriptors} == PYTHON_SCRIPT_DECORATOR_FIELDS[item["kind"]]
        label = next(field for field in descriptors if field["name"] == "label")
        assert label["present"] and label["value"] == ""
        description = next(field for field in descriptors if field["name"] == "description")
        assert not description["present"]
    dropdown = field_choices("dropdown", {"options": ["A", "B"], "codes": [10, 20]})
    assert next(field for field in dropdown if field["name"] == "default")["choices"] == [{"label": "A", "value": 10}, {"label": "B", "value": 20}]


@pytest.mark.parametrize(("source", "context", "insert"), [
    ("@corex.sl", "decorator", "slider"),
    ('@corex.input("x", value_type=fl', "type", "float"),
    ('@corex.input(\n    "x",\n    value_type=corex.I', "type", "corex.Image"),
    ('@corex.input("x", value_type="COREX.DataTypes.Tab', "type", repr(TABLE_VALUE_TYPE_ID)),
    ('@corex.list("x", item_type=', "type", "corex.Color"),
    ('@corex.slider("x", min', "keyword", "minimum="),
    ('@corex.input("x", structure="tr', "value", "'tree'"),
])
def test_incomplete_code_completion(catalog, source, context, insert) -> None:
    result = completions(source, len(source), catalog)
    assert result["context"] == context
    assert insert in [item["insert_text"] for item in result["items"]]


def test_completion_replaces_existing_expression_suffix(catalog) -> None:
    source = '@corex.input("x", value_type="COREX.DataTypes.TableValue")'
    cursor = source.index("TableValue") + 3
    result = completions(source, cursor, catalog)
    item = next(item for item in result["items"] if item["type_id"] == TABLE_VALUE_TYPE_ID)
    updated = source[:result["start"]] + item["insert_text"] + source[result["end"]:]
    assert updated == '@corex.input("x", value_type=\'COREX.DataTypes.TableValue\')'


@pytest.mark.parametrize("source", ['# @corex.sl', 'message = "@corex.sl"', '@corex.input("x", value_type=float)\nvalue_type=', '@corex.dropdown("x", options=[', 'print("@corex.input(\'x\', value_type=")'])
def test_no_completion_in_comments_strings_or_unrelated_code(catalog, source) -> None:
    result = completions(source, len(source), catalog)
    assert not result["items"]


def test_keyword_completion_excludes_already_supplied_fields(catalog) -> None:
    source = '@corex.slider("x", minimum=0, '
    result = completions(source, len(source), catalog)
    assert "minimum=" not in [item["insert_text"] for item in result["items"]]
    assert "maximum=" in [item["insert_text"] for item in result["items"]]


def test_structure_completion_replaces_existing_suffix_and_closing_quote(catalog) -> None:
    source = '@corex.input("x", structure="tree")'
    result = completions(source, source.index("tree") + 2, catalog)
    assert result["context"] == "value"
    updated = source[:result["start"]] + result["items"][0]["insert_text"] + source[result["end"]:]
    assert updated == '@corex.input("x", structure=\'tree\')'


def test_no_decorator_completion_inside_incomplete_string(catalog) -> None:
    source = 'message = "@corex.sl'
    assert not completions(source, len(source), catalog)["items"]
    complete = source + '"'
    assert not completions(complete, len(source), catalog)["items"]
    multiline = 'description = """\n@corex.sl'
    assert not completions(multiline, len(multiline), catalog)["items"]


def test_completion_ignores_decorator_and_keyword_text_inside_literals(catalog) -> None:
    source = '@corex.input("x", description="Example @corex.input( and minimum=0", value_type=fl'
    result = completions(source, len(source), catalog)
    assert "float" in [item["insert_text"] for item in result["items"]]
    source = '@corex.slider("x", description="minimum=0", min'
    result = completions(source, len(source), catalog)
    assert "minimum=" in [item["insert_text"] for item in result["items"]]
