# Purpose: Verify lossless static builder operations and scope-safe guided renames.
# Map: subsystems/nodes_registry_builtins.md
# Tests: this file

from __future__ import annotations

import ast

import pytest

from ea_node_editor.nodes.python_script_authoring import analyze_source, edit_source
from ea_node_editor.nodes.python_script_declaration import PythonScriptDeclarationError
from ea_node_editor.ui.support.python_script_authoring import decorator_choices


SOURCE = '''# Authored preamble
import math

@corex.node
@corex.input("value", value_type=float, label="İşlem 😀")  # input note
@corex.output("result", value_type=float)
def run(ctx, value: float):
    # Keep this calculation and its whitespace.
    return {"result": math.sin(value)}
'''


def test_analysis_reports_character_ranges_and_preserves_signature_mismatch_inventory() -> None:
    source = SOURCE.replace("value: float", "other: float")
    result = analyze_source(source)
    assert not result.valid
    assert result.can_synchronize
    assert result.parameter_keys == ("value",)
    assert result.signature_keys == ("ctx", "other")
    assert result.diagnostics[0].fix == "synchronize_parameters"
    item = result.items[0]
    assert source[item.source_range.start:item.source_range.end].startswith('@corex.input("value"')
    assert item.fields["label"] == "İşlem 😀"
    assert item.expressions["label"] == '"İşlem 😀"'
    fixed = edit_source(source, "synchronize_parameters").source
    assert analyze_source(fixed).valid
    assert "return {\"result\": math.sin(value)}" in fixed


def test_syntax_errors_and_bounds_do_not_execute_source(tmp_path) -> None:
    target = tmp_path / "must-not-exist"
    source = f"open({str(target)!r}, 'w').write('bad')\n" + SOURCE
    assert analyze_source(source).valid
    assert not target.exists()
    assert not analyze_source(source + "(").valid
    assert not analyze_source("#" * 300_000).valid


@pytest.mark.parametrize("choice", decorator_choices(), ids=lambda item: item["kind"])
def test_every_palette_item_adds_a_valid_decorator_and_parameter(choice) -> None:
    fields = dict(choice["initial_fields"])
    if choice["kind"] in {"input", "output"}:
        fields["value_type"] = "float"
    result = edit_source(SOURCE, "add", key="setting", kind=choice["kind"], fields=fields)
    analysis = analyze_source(result.source)
    assert analysis.valid
    assert "setting" in (analysis.output_keys if choice["kind"] == "output" else analysis.parameter_keys)
    assert SOURCE[SOURCE.index("    # Keep"): ] == result.source[result.source.index("    # Keep"): ]
    assert "value: float" in result.source


def test_input_requires_explicit_type_and_names_do_not_capture_body_locals() -> None:
    with pytest.raises(PythonScriptDeclarationError, match="explicit data type"):
        edit_source(SOURCE, "add", key="new", kind="input")
    with pytest.raises(PythonScriptDeclarationError, match="already used"):
        edit_source(SOURCE, "add", key="math", kind="input", fields={"value_type": "float"})


def test_update_preserves_comments_annotations_unicode_crlf_and_omitted_blank_distinction() -> None:
    source = '''@corex.node
@corex.text(
    "text",  # keep key
    label="İ 😀",  # keep label note
    default="quoted \\" text",  # keep default note
)  # after decorator
def run(ctx, text: tuple[str, int]):
    return {}
'''.replace("\n", "\r\n")
    result = edit_source(source, "update", key="text", fields={"label": "", "section": "Details"}).source
    assert '# keep key\r\n' in result
    assert '# keep label note\r\n' in result
    assert 'text: tuple[str, int]' in result
    assert "label=''" in result
    assert result.count("\r\n") == source.count("\r\n")
    omitted = edit_source(result, "update", key="text", remove_fields=("label",)).source
    item = analyze_source(omitted).items[0]
    assert "label" not in item.fields
    assert item.label == "Text"
    assert "# keep label note" in omitted


def test_none_is_a_literal_and_not_field_removal() -> None:
    source = edit_source(SOURCE, "add", key="bounds", kind="interval", fields={"default": [0, 1]}).source
    result = edit_source(source, "update", key="bounds", fields={"default": None}).source
    item = analyze_source(result).items[-1]
    assert "default" in item.fields and item.fields["default"] is None
    with pytest.raises(PythonScriptDeclarationError, match="set and omitted"):
        edit_source(source, "update", key="bounds", fields={"default": None}, remove_fields=("default",))


def test_duplicate_reorder_and_remove_preserve_unrelated_source() -> None:
    source = edit_source(SOURCE, "duplicate", key="value", new_key="another").source
    assert analyze_source(source).parameter_keys == ("value", "another")
    moved = edit_source(source, "move", key="another", index=0).source
    assert [item.key for item in analyze_source(moved).items] == ["another", "value", "result"]
    assert '# input note' in moved
    removed = edit_source(moved, "remove", key="another").source
    assert analyze_source(removed).parameter_keys == ("value",)
    assert "value: float" in removed
    assert '    return {"result": math.sin(value)}' in removed


def test_guided_rename_updates_only_parameter_bindings_and_output_forwarding() -> None:
    source = '''@corex.node
@corex.input("value", value_type=corex.Any)
@corex.output("result", value_type=corex.Any, type_from_input="value")
def run(ctx, value: float):
    literal = "value"
    attr = ctx.value
    def capture(offset=value):
        return value + offset
    def shadow(value):
        return value
    def assigned():
        value = 4
        return value
    def nested():
        nonlocal value
        value += 1
        return value
    class Wrapper:
        initial = value
        def get(self):
            return value
    a = [value for value in value]
    b = [value + x for x in value]
    c = lambda value: value
    d = lambda x=value: value + x
    return {"result": value}
'''
    result = edit_source(source, "rename", key="value", new_key="payload")
    assert [(item.old_key, item.new_key, item.kind) for item in result.renames] == [("value", "payload", "input")]
    assert "type_from_input='payload'" in result.source
    for text in ('literal = "value"', "attr = ctx.value", "def shadow(value):\n        return value",
                 "value = 4\n        return value", "a = [value for value in payload]", "c = lambda value: value"):
        assert text in result.source
    for text in ("payload: float", "offset=payload", "return payload + offset", "nonlocal payload", "payload += 1",
                 "initial = payload", "return payload", "b = [payload + x for x in payload]", "lambda x=payload: payload + x"):
        assert text in result.source
    assert len(result.changes) > 5
    assert analyze_source(result.source).valid


def test_rename_preserves_globals_and_multi_generator_comprehension_scope() -> None:
    source = '''@corex.node
@corex.input("value", value_type=float)
def run(ctx, value):
    def f():
        global value
        return value
    return {"unused": [(value, x) for x in value for value in x]}
'''
    result = edit_source(source, "rename", key="value", new_key="payload").source
    assert "global value\n        return value" in result
    assert "[(value, x) for x in payload for value in x]" in result


@pytest.mark.parametrize("body", ["return locals()['value']", "return eval('value')", "lookup = vars\n    return lookup()", "return ctx.f_locals['value']", "payload = 1\n    return value", "def f(payload):\n        return value\n    return f(1)"])
def test_rename_blocks_dynamic_lookup_and_name_capture(body) -> None:
    source = '@corex.node\n@corex.input("value", value_type=float)\ndef run(ctx, value):\n    ' + body + "\n"
    with pytest.raises(PythonScriptDeclarationError):
        edit_source(source, "rename", key="value", new_key="payload")


def test_output_key_rename_updates_only_run_return_dicts() -> None:
    source = SOURCE.replace('    # Keep this calculation and its whitespace.', '    def nested():\n        return {"result": 8}')
    result = edit_source(source, "rename", key="result", new_key="answer").source
    assert '        return {"result": 8}' in result
    assert "return {'answer': math.sin(value)}" in result
    dynamic = SOURCE.replace('return {"result": math.sin(value)}', 'return dict(result=value)')
    with pytest.raises(PythonScriptDeclarationError, match="literal returned dictionaries"):
        edit_source(dynamic, "rename", key="result", new_key="answer")


def test_add_and_remove_multiple_parameters_keep_existing_annotations_and_comments() -> None:
    source = '''@corex.node
@corex.text("new")
def run(
    ctx,  # context
    gone: tuple[int, str],  # first
    other,  # second
):
    return {}
'''
    result = edit_source(source, "synchronize_parameters").source
    assert analyze_source(result).signature_keys == ("ctx", "new")
    assert all(comment in result for comment in ("# context", "# first", "# second"))
    ast.parse(result)


def test_parenthesized_multiline_decorator_moves_as_complete_source_block() -> None:
    source = SOURCE.replace('@corex.input("value", value_type=float, label="İşlem 😀")',
                            '@(\n    corex.input("value", value_type=float, label="İşlem 😀")\n)')
    result = edit_source(source, "move", key="value", index=1).source
    assert [item.key for item in analyze_source(result).items] == ["result", "value"]
    assert '@(\n    corex.input("value", value_type=float, label="İşlem 😀")\n)  # input note' in result


def test_rename_import_alias_does_not_rename_imported_module() -> None:
    source = SOURCE.replace('    return {"result": math.sin(value)}',
                            '    import value as value\n    return {"result": value}')
    result = edit_source(source, "rename", key="value", new_key="payload").source
    assert "import value as payload" in result


def test_unicode_line_separator_inside_literal_does_not_change_ast_rows() -> None:
    source = SOURCE.replace('label="İşlem 😀"', 'label="a\u2028b\u0085c"')
    result = edit_source(source, "update", key="result", fields={"label": "Output"}).source
    assert 'label="a\u2028b\u0085c"' in result
    assert analyze_source(result).valid


@pytest.mark.parametrize("binding", [
    "def payload():\n        return 2", "class payload:\n        pass", "import math as payload",
    "try:\n        pass\n    except Exception as payload:\n        pass",
    "match value:\n        case {'x': payload}:\n            pass",
])
def test_add_rejects_string_backed_bindings_for_parameters(binding) -> None:
    source = SOURCE.replace('    return {"result": math.sin(value)}', '    ' + binding + '\n    return {}')
    with pytest.raises(PythonScriptDeclarationError, match="already used"):
        edit_source(source, "add", key="payload", kind="input", fields={"value_type": "float"})
    result = edit_source(source, "add", key="payload", kind="output", fields={"value_type": "float"})
    assert analyze_source(result.source).valid


@pytest.mark.parametrize(("preamble", "expression"), [
    ("import builtins", 'builtins.locals()["value"]'),
    ("from builtins import locals as local_values", 'local_values()["value"]'),
    ("import builtins as b\nread_values = b.locals", 'read_values()["value"]'),
])
def test_rename_blocks_qualified_and_module_aliased_dynamic_lookup(preamble, expression) -> None:
    source = preamble + "\n" + SOURCE.replace('math.sin(value)', expression)
    with pytest.raises(PythonScriptDeclarationError, match="dynamic name lookup"):
        edit_source(source, "rename", key="value", new_key="payload")


def test_diagnostic_column_counts_unicode_characters() -> None:
    source = '@corex.node\n@corex.text("text", label="İşlem 😀", invalid=True)\ndef run(ctx, text):\n    return {}\n'
    result = analyze_source(source)
    assert result.diagnostics[0].line == 2
    assert result.diagnostics[0].column == source.split("\n")[1].index("True") + 1
