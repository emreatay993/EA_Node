# Purpose: Prove Python authoring draft history, identity, assistance and Apply session isolation.
# Map: subsystems/qml_shell_and_bridges.md
# Tests: this file
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PyQt6.QtTest import QSignalSpy, QTest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui.shell.controllers.workspace_edit_controller import WorkspaceEditController
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel


SOURCE = '''# π 🐍 retained comment
@corex.node
@corex.input("payload", value_type=corex.Any)
@corex.output("result", value_type=corex.Any)
@corex.slider("scale", default=0.5, minimum=0.0, maximum=1.0, port=True)
@corex.text("caption", default="Chart")
def run(ctx, payload, scale, caption):
    return {"result": payload}
'''


@pytest.fixture
def authoring():
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace.workspace_id)
    history = RuntimeGraphHistory()
    scene.bind_runtime_history(history)
    node_id = scene.add_node_from_type("code.python_script", 0, 0)
    scene.set_node_property(node_id, "script", SOURCE)
    editor = ScriptEditorModel()
    context = [model.project, workspace, registry]

    def apply(node_id, source, renamed_keys, revision, prepared):
        result = scene.apply_python_script(node_id, source, renamed_keys=renamed_keys,
                                          source_revision=revision, prepared=prepared)
        editor.set_node(workspace.nodes[node_id])
        return result

    editor.configure_authoring(
        context_provider=lambda: tuple(context),
        prepare=lambda node_id, source, renamed_keys, revision: scene.prepare_python_script(
            node_id, source, renamed_keys=renamed_keys, source_revision=revision),
        apply=apply,
    )
    editor.set_node(workspace.nodes[node_id])
    yield SimpleNamespace(editor=editor, scene=scene, model=model, workspace=workspace,
                          registry=registry, history=history, node_id=node_id, context=context)
    editor._analysis_timer.stop()


def rename(editor, old, new):
    review = editor.preview_rename(old, new)
    assert not review["error"]
    assert review["changes"]
    assert editor.confirm_rename()


def test_analysis_is_debounced_and_apply_flushes_pending_source(authoring):
    editor = authoring.editor
    editor.set_script_text(SOURCE + "\n# valid draft\n")
    assert editor.analysis_status == "updating"
    assert editor.apply()
    assert editor.analysis_status == "ready"
    assert not editor.dirty
    editor.set_script_text("@corex.node\ndef run(")
    QTest.qWait(350)
    assert editor.analysis_status == "unavailable"
    assert editor.diagnostics[0]["severity"] == "error"


def test_builder_type_is_explicit_and_model_undo_covers_code_and_builder(authoring):
    editor = authoring.editor
    assert not editor.perform_edit("add", {"kind": "input", "key": "values"})
    assert "type" in editor.operation_error
    assert editor.perform_edit("add", {"kind": "input", "key": "values", "fields": {"value_type": "float"}})
    added = editor.script_text
    editor.set_script_text(added + "\n# typed\n")
    assert editor.undo() and editor.script_text == added
    assert editor.undo() and editor.script_text == SOURCE
    assert editor.redo() and editor.script_text == added


def test_guided_rename_and_undo_after_apply_preserve_identity(authoring):
    editor = authoring.editor
    authoring.scene.set_node_property(authoring.node_id, "scale", 0.75)
    rename(editor, "scale", "gain")
    assert editor.renamed_keys == {"scale": "gain"}
    depth = authoring.history.undo_depth(authoring.workspace.workspace_id)
    assert editor.apply()
    assert authoring.workspace.nodes[authoring.node_id].properties["gain"] == 0.75
    assert authoring.history.undo_depth(authoring.workspace.workspace_id) == depth + 1
    assert editor.renamed_keys == {}
    assert editor.undo()
    assert editor.renamed_keys == {"gain": "scale"}
    assert editor.apply()
    assert authoring.workspace.nodes[authoring.node_id].properties["scale"] == 0.75


def test_compound_remove_then_rename_and_name_reuse_distinguish_identities(authoring):
    editor = authoring.editor
    assert editor.perform_edit("remove", {"key": "caption"})
    rename(editor, "scale", "caption")
    assert editor.renamed_keys == {"scale": "caption"}
    assert editor.apply()
    assert authoring.workspace.nodes[authoring.node_id].properties["caption"] == 0.5
    rename(editor, "caption", "gain")
    assert editor.perform_edit("add", {"kind": "text", "key": "caption", "fields": {"default": "New"}})
    assert editor.renamed_keys == {"caption": "gain"}
    assert not editor.selected_item["has_saved_value"]
    assert editor.apply()
    node = authoring.workspace.nodes[authoring.node_id]
    assert node.properties["gain"] == 0.5
    assert node.properties["caption"] == "New"


def test_arbitrary_typed_rename_does_not_transfer_saved_values(authoring):
    editor = authoring.editor
    authoring.scene.set_node_property(authoring.node_id, "scale", 0.75)
    editor.set_script_text(SOURCE.replace("scale", "gain"))
    editor.analyze_now()
    assert editor.renamed_keys == {}
    assert editor.apply()
    assert authoring.workspace.nodes[authoring.node_id].properties["gain"] == 0.5


def test_rename_review_is_invalidated_by_edit(authoring):
    editor = authoring.editor
    editor.preview_rename("scale", "gain")
    editor.set_script_text(SOURCE + "\n# changed\n")
    assert not editor.confirm_rename()
    assert "Review" in editor.operation_error


def test_drafts_survive_retarget_and_clear_selection(authoring):
    editor = authoring.editor
    draft = SOURCE + "\n# keep this\n"
    editor.set_script_text(draft)
    second = authoring.scene.add_node_from_type("code.python_script", 300, 0)
    editor.set_node(authoring.workspace.nodes[second])
    editor.set_script_text(editor.script_text + "\n# second\n")
    editor.set_node(None)
    editor.set_node(authoring.workspace.nodes[authoring.node_id])
    assert editor.script_text == draft
    assert editor.dirty and editor.can_undo


def test_drafts_do_not_cross_workspace_or_loaded_project_identity(authoring):
    editor = authoring.editor
    node = authoring.workspace.nodes[authoring.node_id]
    editor.set_script_text(SOURCE + "\n# original\n")
    original = authoring.context[:]
    authoring.context[1] = SimpleNamespace(workspace_id="other")
    editor.set_node(node)
    assert editor.script_text == SOURCE
    authoring.context[:] = original
    editor.set_node(node)
    assert "original" in editor.script_text
    authoring.context[0] = SimpleNamespace(project_id=original[0].project_id)
    editor.set_node(node)
    assert editor.script_text == SOURCE and not editor.dirty


def test_selection_controller_refreshes_saved_values_and_same_id_context(authoring):
    editor = authoring.editor
    editor.set_script_text(SOURCE + "\n# retain draft\n")
    host = SimpleNamespace(script_editor=editor)
    selection = SimpleNamespace(active_workspace=lambda: authoring.context[1])
    controller = WorkspaceEditController(host, selection_context=selection, effects=Mock())
    authoring.scene.set_node_property(authoring.node_id, "scale", 0.75)
    controller.on_scene_node_selected(authoring.node_id)
    editor.analyze_now()
    editor.select_item("scale")
    assert editor.selected_item["saved_value"] == 0.75
    assert editor.script_text.endswith("# retain draft\n") and editor.can_undo
    authoring.context[1] = SimpleNamespace(workspace_id="other", nodes=authoring.workspace.nodes)
    controller.on_scene_node_selected(authoring.node_id)
    assert editor._context_is_current()
    assert editor.script_text == SOURCE and not editor.dirty
    editor.set_script_text(SOURCE + "\n# other workspace draft\n")
    authoring.context[0] = SimpleNamespace(project_id=authoring.context[0].project_id)
    controller.on_scene_node_selected(authoring.node_id)
    assert editor._context_is_current()
    assert editor.script_text == SOURCE and not editor.dirty


def test_context_change_before_retarget_cannot_apply_other_same_id_node(authoring):
    editor = authoring.editor
    editor.set_script_text(SOURCE + "\n# draft\n")
    authoring.context[1] = SimpleNamespace(workspace_id="other")
    assert not editor.apply()
    assert "workspace changed" in editor.operation_error
    assert authoring.workspace.nodes[authoring.node_id].properties["script"] == SOURCE


def test_dirty_history_refresh_changes_revert_baseline_only(authoring):
    editor = authoring.editor
    editor.set_script_text(SOURCE + "\n# draft\n")
    updated = SOURCE + "\n# applied outside editor\n"
    authoring.scene.set_node_property(authoring.node_id, "script", updated)
    editor.set_node(authoring.workspace.nodes[authoring.node_id])
    assert editor.script_text.endswith("# draft\n")
    editor.revert()
    assert editor.script_text == updated and not editor.dirty
    assert editor.undo() and editor.script_text.endswith("# draft\n")


def test_selection_and_completion_translate_non_bmp_to_utf16(authoring):
    editor = authoring.editor
    spy = QSignalSpy(editor.selection_range_requested)
    editor.select_item("scale")
    expected = SOURCE.index('@corex.slider')
    assert spy[-1][0] == len(SOURCE[:expected].encode("utf-16-le")) // 2
    editor.select_source_position(spy[-1][0])
    assert editor.selected_key == "scale"
    source = '# 🐍\n@corex.input("value", value_type=)'
    editor.set_script_text(source)
    cursor = len(source[:-1].encode("utf-16-le")) // 2
    choices = editor.query_completions(cursor)
    assert choices["context"] == "type" and choices["start"] == cursor
    index = next(i for i, item in enumerate(choices["items"]) if item["expression"] == "float")
    assert editor.accept_completion(index)
    assert editor.script_text.endswith("value_type=float)")


def test_type_help_forms_and_saved_values_are_variant_safe(authoring):
    editor = authoring.editor
    assert any("float" == item["expression"] for item in editor.query_types("decimal", False, ""))
    assert len(editor.query_types("", True, "")) == 4
    assert len(editor.query_decorators("")) == 13
    assert editor.query_decorators("section")[0]["kind"] == "section"
    editor.select_item("scale")
    assert editor.selected_item["saved_value"] == 0.5
    assert any(field["name"] == "port" for field in editor.selected_item["form_fields"])
    editor.perform_edit("add", {"kind": "interval", "key": "bounds", "fields": {"default": [0.0, 1.0]}})
    assert isinstance(editor.selected_item["fields"]["default"], list)


def test_invalid_apply_is_atomic_and_stale_impact_requires_new_apply(authoring):
    editor = authoring.editor
    before = authoring.workspace.capture_snapshot()
    editor.set_script_text(SOURCE.replace("def run(ctx, payload, scale, caption):", "def run(ctx):"))
    assert editor.can_synchronize is False  # analysis is pending
    assert not editor.apply()
    assert editor.can_synchronize
    assert authoring.workspace.capture_snapshot() == before
    assert editor.perform_edit("synchronize_parameters", {})
    editor.set_script_text(editor.script_text + "\n# draft\n")
    impact = editor.prepare_apply()
    assert not impact["error"]
    authoring.scene.add_node_from_type("code.python_script", 300, 0)
    assert not editor.apply()
    assert "Review the updated" in editor.operation_error
    assert editor.dirty
    assert editor.apply()


def test_bare_model_retains_request_signal_contract(qapp):
    editor = ScriptEditorModel()
    editor.set_node(SimpleNamespace(node_id="node", type_id="code.python_script", title="Script",
                                   properties={"script": SOURCE}))
    editor.set_script_text(SOURCE + "\n# changed\n")
    spy = QSignalSpy(editor.script_apply_requested)
    assert not editor.apply()
    assert list(spy[-1]) == ["node", "script", editor.script_text]
    assert editor.dirty
