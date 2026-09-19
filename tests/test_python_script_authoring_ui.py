# Purpose: Prove native authoring forms and the isolated production node preview.
# Map: subsystems/qml_shell_and_bridges.md
# Tests: this file
from __future__ import annotations

import copy
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QObject, QPointF, Qt, QUrl, QMetaObject, Q_ARG
from PyQt6.QtGui import QColor, QFont, QFontDatabase
from PyQt6.QtQuick import QQuickView
from PyQt6.QtTest import QSignalSpy, QTest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.syntax_bridge import QmlScriptSyntaxBridge
from ea_node_editor.ui.icon_registry import UiIconRegistryBridge, UiIconImageProvider, UI_ICON_PROVIDER_ID

SOURCE = '''@corex.node
@corex.input("values", value_type=float, structure="list")
@corex.output("result", value_type=float)
@corex.slider("gain", default=1.0, minimum=0.0, maximum=4.0, step=0.1, port=True, section="Display")
@corex.dropdown("mode", default="Mean", options=["Mean", "Maximum"], section="Display")
@corex.text("caption", default="Results")
@corex.text_area("notes", default="A note")
@corex.number("count", default=3)
@corex.switch("legend", default=True)
@corex.color("accent", default="#336699")
@corex.path("source_file", default="")
@corex.interval("bounds", default=(0.0, 1.0))
@corex.list("labels", default=["A", "B"], item_type=str)
def run(ctx, values, gain, mode, caption, notes, count, legend, accent, source_file, bounds, labels):
    raise RuntimeError("Preview must never execute this body")
'''

PRESENTATION_SOURCE = '''@corex.node
@corex.input("samples", value_type=float, structure="list")
@corex.output("result", value_type=float)
@corex.slider("gain", default=1.0, minimum=0.0, maximum=5.0, step=0.1, section="Parameters")
@corex.dropdown("method", default="Mean", options=["Mean", "Maximum"], section="Parameters")
@corex.switch("absolute", default=False, label="Absolute values", section="Parameters")
def run(ctx, samples, gain, method, absolute):
    values = [abs(value) if absolute else value for value in samples]
    summary = max(values) if method == "Maximum" else sum(values) / len(values)
    return {"result": summary * gain}
'''


@pytest.fixture
def session(qapp):
    registry = build_builtin_registry()
    graph = GraphModel()
    scene = GraphSceneBridge()
    scene.set_workspace(graph, registry, graph.active_workspace.workspace_id)
    node_id = scene.add_node_from_type("core.python_script", 0, 0)
    scene.set_node_property(node_id, "script", SOURCE)
    editor = ScriptEditorModel()
    def apply(node_id, source, renamed_keys, revision, prepared):
        value = scene.apply_python_script(node_id, source, renamed_keys=renamed_keys, source_revision=revision, prepared=prepared)
        editor.set_node(graph.active_workspace.nodes[node_id])
        return value
    editor.configure_authoring(
        context_provider=lambda: (graph.project, graph.active_workspace, registry),
        prepare=lambda node_id, source, renamed_keys, revision: scene.prepare_python_script(node_id, source, renamed_keys=renamed_keys, source_revision=revision),
        apply=apply,
    )
    editor.set_node(graph.active_workspace.nodes[node_id])
    yield SimpleNamespace(editor=editor, registry=registry, graph=graph, scene=scene, node_id=node_id)
    editor._analysis_timer.stop()


@pytest.fixture
def view(session, qapp):
    # Windows' offscreen platform has no system font database. Load the same
    # installed families the real desktop uses for meaningful visual QA.
    for filename in ("segoeui.ttf", "segoeuib.ttf", "seguisym.ttf", "consola.ttf"):
        font_path = Path("C:/Windows/Fonts") / filename
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    qapp.setFont(QFont("Segoe UI", 10))
    view = QQuickView()
    icons = UiIconRegistryBridge()
    icon_provider = UiIconImageProvider()
    view.engine().addImageProvider(UI_ICON_PROVIDER_ID, icon_provider)
    view.rootContext().setContextProperty("uiIcons", icons)
    theme = ThemeBridge(theme_id="stitch_light")
    graph_theme = GraphThemeBridge(theme_id="graph_stitch_light")
    highlighter = QmlScriptSyntaxBridge()
    view.rootContext().setContextProperty("themeBridge", theme)
    view.setInitialProperties({"scriptEditorBridgeRef": session.editor, "themeBridgeRef": theme, "graphThemeBridgeRef": graph_theme, "scriptHighlighterBridgeRef": highlighter})
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(1600, 900)
    path = Path(__file__).resolve().parents[1] / "ea_node_editor/ui_qml/components/shell/ScriptCodeEditorPane.qml"
    view.setSource(QUrl.fromLocalFile(str(path)))
    assert view.status() == QQuickView.Status.Ready, "\n".join(error.toString() for error in view.errors())
    view.show()
    QTest.qWait(80)
    yield SimpleNamespace(view=view, root=view.rootObject(), editor=session.editor, theme=theme, graph_theme=graph_theme, icon_provider=icon_provider)
    view.close()
    view.setSource(QUrl())
    view.deleteLater()
    qapp.processEvents()


def find(view, name):
    result = next((item for item in objects(view) if item.objectName() == name), None)
    assert result is not None, name
    return result


def objects(view):
    seen = set()
    pending = [view.view.contentItem(), view.root]
    while pending:
        item = pending.pop()
        if item in seen:
            continue
        seen.add(item)
        yield item
        pending.extend(item.children())
        if hasattr(item, "childItems"):
            pending.extend(item.childItems())


def click(view, item):
    if isinstance(item, str):
        item = find(view, item)
    assert item.isVisible(), item.objectName()
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    QTest.mouseClick(view.view, Qt.MouseButton.LeftButton, pos=point)
    QTest.qWait(25)


def visible_find(view, name):
    return next(item for item in objects(view) if item.objectName() == name and item.isVisible())


def capture(view, name):
    output = os.environ.get("COREX_AUTHORING_SCREENSHOTS")
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        QTest.qWait(180)
        assert view.view.grabWindow().save(str(directory / name))


def test_preview_is_detached_and_never_runs_source(session):
    snapshot = copy.deepcopy(session.graph.active_workspace)
    preview = session.editor.preview_bridge
    assert preview.payload["type_id"] == "core.python_script"
    assert preview.set_value("gain", 2.5)
    assert preview.set_value("caption", "Temporary")
    for group in preview.payload.get("settings_groups", []):
        preview.set_group_expanded(group["group_id"], False)
    assert session.graph.active_workspace == snapshot
    assert session.editor.script_text == SOURCE
    assert preview.values["gain"] == 2.5
    assert preview.use_as_default("gain")
    assert "default=2.5" in session.editor.script_text
    assert session.graph.active_workspace == snapshot
    assert session.editor.undo() and session.editor.script_text == SOURCE


def test_preview_uses_explicit_theme_bridge_and_rebinds(view, session):
    preview = session.editor.preview_bridge
    assert preview._theme is view.graph_theme
    node = find(view, "scriptPreviewNode")
    assert node.property("themeSurfaceColor") == QColor(view.graph_theme.node_palette["card_bg"])
    before = node.property("themeSurfaceColor")
    replacement = GraphThemeBridge(theme_id="graph_stitch_dark")
    view.root.setProperty("graphThemeBridgeRef", replacement)
    QTest.qWait(20)
    assert preview._theme is replacement
    assert node.property("themeSurfaceColor") == QColor(replacement.node_palette["card_bg"])
    assert node.property("themeSurfaceColor") != before
    changed = QSignalSpy(preview.changed)
    view.graph_theme.apply_theme("graph_stitch_dark")
    assert len(changed) == 0
    replacement.apply_theme("graph_stitch_light")
    assert len(changed) == 1
    view.root.setProperty("graphThemeBridgeRef", view.graph_theme)


@pytest.mark.parametrize("fullscreen", [False, True])
def test_help_is_available_in_docked_and_fullscreen_editor(view, fullscreen):
    view.root.setProperty("guideButtonVisible", fullscreen)
    requested = QSignalSpy(view.root.guideRequested)
    click(view, "pythonScriptGuideButton")
    assert len(requested) == int(fullscreen)
    assert find(view, "scriptHelpPopup").property("visible") is not fullscreen


def test_preview_headerless_controls_never_acquire_expansion_state(session):
    preview = session.editor.preview_bridge
    group = next(group for group in preview.payload["settings_groups"] if not group["show_header"])
    assert group["expanded"]
    assert group["group_id"] not in preview._node.expanded_settings_group_ids
    before = preview._node.clone()
    preview.set_group_expanded(group["group_id"], False)
    preview.set_group_expanded("unknown", True)
    assert preview._node == before
    assert group["group_id"] not in preview._group_expansion
    assert "unknown" not in preview._group_expansion


@pytest.mark.parametrize("port", [False, True])
def test_unsectioned_preview_controls_keep_order_and_blank_labels(view, session, port):
    source = f'''@corex.node
@corex.input("payload", value_type=corex.Any)
@corex.output("result", value_type=corex.Any)
@corex.switch("enabled", default=False, label="", port={port})
@corex.slider("amount", default=0.5, minimum=0.0, maximum=1.0, port={port})
@corex.dropdown("mode", default="First", options=("First", "Second"), port={port})
def run(ctx, payload, enabled, amount, mode):
    return {{"result": payload}}
'''
    session.scene.set_node_property(session.node_id, "script", source)
    view.editor.set_node(session.graph.active_workspace.nodes[session.node_id])
    baseline = copy.deepcopy(session.graph.active_workspace)
    QTest.qWait(60)
    labels = [
        item for item in objects(view)
        if item.objectName() == "graphNodeInlinePropertyLabel" and item.property("propertyKey") == "enabled"
    ]
    assert len(labels) == 1 and labels[0].property("text") == ""
    assert not any(item.isVisible() for item in objects(view) if item.objectName() == "graphNodeSettingsGroupHeader")
    toggle = next(
        item for item in objects(view)
        if item.objectName() == "graphNodeInlineToggleEditor" and item.property("propertyKey") == "enabled"
    )
    click(view, toggle)
    assert view.editor.preview_bridge.values["enabled"] is True
    assert session.graph.active_workspace == baseline
    capture(view, f"unsectioned_controls_port_{str(port).lower()}.png")


def test_component_compiles_and_responsive_hosts_keep_one_document(view):
    assert len(view.root.findChildren(QObject, "scriptEditorArea")) == 1
    for width, expected in ((1600, (True, False)), (1000, (False, False)), (650, (False, True))):
        view.view.resize(width, 800)
        QTest.qWait(20)
        assert (view.root.property("wide"), view.root.property("narrow")) == expected
        assert find(view, "scriptEditorArea").isVisible()


def test_qml_number_mode_preserves_integral_decimal_and_rejects_fractional_whole(view):
    editor = view.editor
    engine = view.view.engine()
    engine.globalObject().setProperty("editor", engine.newQObject(editor))
    result = engine.evaluate('editor.perform_edit("add", {kind:"slider",key:"scale",numeric_mode:"decimal",fields:{default:1.0,minimum:0.0,maximum:2.0,step:0.1}})')
    assert result.toBool(), editor.operation_error
    assert "default=1.0" in editor.script_text
    before = editor.script_text
    result = engine.evaluate('editor.perform_edit("update", {key:"scale",numeric_mode:"whole",fields:{default:1.5}})')
    assert not result.toBool()
    assert editor.script_text == before
    assert "fractions" in editor.operation_error


def test_code_tab_and_history_are_local(view):
    code = find(view, "scriptEditorArea")
    code.setProperty("text", "pass")
    code.setProperty("cursorPosition", 4)
    code.forceActiveFocus()
    QTest.keyClick(view.view, Qt.Key.Key_Tab)
    assert code.property("text") == "pass    "
    QTest.keyClick(view.view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert code.property("text") == "pass"
    QTest.keyClick(view.view, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert code.property("text") == "pass    "


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_add_type_picker_rename_and_apply_buttons(view, session, theme):
    view.theme.apply_theme("stitch_" + theme)
    view.graph_theme.apply_theme("graph_stitch_" + theme)
    view.view.setColor(QColor(view.theme.palette["panel_bg"]))
    click(view, "scriptAddButton")
    capture(view, f"add_palette_{theme}.png")
    find(view, "scriptAddSearch").setProperty("text", "Input")
    QTest.qWait(20)
    click(view, "scriptAddChoice_input")
    assert not find(view, "scriptAddConfirm").isEnabled()
    find(view, "scriptAddName").setProperty("text", "temperature")
    click(view, visible_find(view, "scriptTypePickerButton"))
    capture(view, f"type_picker_{theme}.png")
    visible_find(view, "scriptTypeSearch").setProperty("text", "decimal")
    QTest.qWait(20)
    click(view, visible_find(view, "scriptTypeChoice_COREX.DataTypes.Double"))
    click(view, "scriptAddConfirm")
    assert "value_type=float" in view.editor.script_text
    assert "temperature" in view.editor.script_text
    click(view, "scriptRenameButton")
    find(view, "scriptRenameName").setProperty("text", "ambient")
    click(view, "scriptRenameReviewButton")
    assert view.editor.rename_review["changes"]
    capture(view, f"rename_review_{theme}.png")
    click(view, "scriptRenameConfirm")
    assert "ambient" in view.editor.script_text
    click(view, "scriptApplyButton")
    assert not view.editor.dirty
    assert session.graph.active_workspace.nodes[session.node_id].properties["script"] == view.editor.script_text


def test_completion_closes_when_caret_context_changes(view):
    code = find(view, "scriptEditorArea")
    source = "@corex.in\ndef run(ctx):\n    pass\n"
    code.setProperty("text", source)
    code.setProperty("cursorPosition", 9)
    code.forceActiveFocus()
    QTest.keyClick(view.view, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier)
    QTest.qWait(20)
    assert find(view, "scriptCompletionPopup").property("visible")
    code.setProperty("cursorPosition", len(source) - 1)
    assert not find(view, "scriptCompletionPopup").property("visible")
    QTest.keyClick(view.view, Qt.Key.Key_Tab)
    assert code.property("text") == source[:-1] + "    \n"


def test_preview_title_refreshes_without_source_change(session):
    node = session.graph.active_workspace.nodes[session.node_id]
    node.title = "Custom Script"
    session.editor.refresh_node(node)
    assert session.editor.preview_bridge.payload["title"] == "Custom Script"


def test_native_preview_control_and_section_toggle_do_not_mutate_graph(view, session):
    baseline = copy.deepcopy(session.graph.active_workspace)
    view.editor.select_item("legend")
    QTest.qWait(40)
    toggle = next(item for item in objects(view) if item.objectName() == "graphNodeInlineToggleEditor" and item.property("propertyKey") == "legend")
    click(view, toggle)
    assert view.editor.preview_bridge.values["legend"] is False
    assert view.editor.selected_key == "legend"
    assert session.graph.active_workspace == baseline
    view.editor.select_item("gain")
    QTest.qWait(30)
    header = visible_find(view, "graphNodeSettingsGroupHeader")
    click(view, header)
    assert not next(
        group for group in view.editor.preview_bridge.payload["settings_groups"]
        if group["group_id"] == "display"
    )["expanded"]
    assert session.graph.active_workspace == baseline
    assert view.editor.script_text == SOURCE


def test_representative_preview_dropdown_is_interactive(view, session):
    session.scene.set_node_property(session.node_id, "script", PRESENTATION_SOURCE)
    view.editor.set_node(session.graph.active_workspace.nodes[session.node_id])
    baseline = copy.deepcopy(session.graph.active_workspace)
    combo = next(item for item in objects(view) if item.objectName() == "graphNodeInlineEnumEditor" and item.property("propertyKey") == "method")
    assert combo.isEnabled()
    click(view, combo)
    maximum = next(item for item in objects(view) if item.property("text") == "Maximum" and hasattr(item, "isVisible") and item.isVisible())
    click(view, maximum)
    QTest.qWait(25)
    assert view.editor.preview_bridge.values["method"] == "Maximum"
    assert session.graph.active_workspace == baseline


def test_native_form_commits_integral_decimal_and_only_changed_fields(view):
    view.editor.select_item("gain")
    field = visible_find(view, "scriptField_default")
    field.forceActiveFocus()
    field.setProperty("text", "1.0")
    QMetaObject.invokeMethod(field, "editingFinished")
    click(view, "scriptUpdateDeclaration")
    assert "default=1.0" in view.editor.script_text
    label = visible_find(view, "scriptField_label")
    label.setProperty("text", "Gain scale")
    QMetaObject.invokeMethod(label, "editingFinished")
    form = find(view, "scriptSelectedForm")
    changed = form.property("changes").toVariant()
    assert changed == {"label": "Gain scale"}
    click(view, "scriptUpdateDeclaration")
    assert "default=1.0" in view.editor.script_text


def test_form_errors_block_apply_and_selection_until_corrected(view, session):
    editor = view.editor
    editor.select_item("gain")
    default = visible_find(view, "scriptField_default")
    default.setProperty("text", "banana")
    QMetaObject.invokeMethod(default, "editingFinished")
    maximum = visible_find(view, "scriptField_maximum")
    maximum.setProperty("text", "10")
    QMetaObject.invokeMethod(maximum, "editingFinished")
    QTest.qWait(10)
    assert find(view, "scriptSelectedForm").property("error")
    baseline = session.graph.active_workspace.nodes[session.node_id].properties["script"]
    QMetaObject.invokeMethod(view.root, "requestApply")
    assert session.graph.active_workspace.nodes[session.node_id].properties["script"] == baseline
    editor.select_item("caption")
    assert editor.selected_key == "gain"
    assert default.property("text") == "banana"
    default.setProperty("text", "1.5")
    QMetaObject.invokeMethod(default, "editingFinished")
    QTest.qWait(10)
    assert not find(view, "scriptSelectedForm").property("error")
    assert "default=1.5" in editor.script_text and "maximum=10.0" in editor.script_text
    editor.select_item("caption")
    assert editor.selected_key == "caption"


def test_focused_field_is_flushed_by_global_apply(view, session):
    view.editor.select_item("gain")
    default = visible_find(view, "scriptField_default")
    default.forceActiveFocus()
    QTest.keyClick(view.view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    for key in (Qt.Key.Key_2, Qt.Key.Key_Period, Qt.Key.Key_0):
        QTest.keyClick(view.view, key)
    # A pending text field is part of the draft even before it loses focus.
    assert find(view, "scriptApplyButton").isEnabled()
    click(view, "scriptApplyButton")
    assert not view.editor.dirty
    source = session.graph.active_workspace.nodes[session.node_id].properties["script"]
    assert "default=2.0" in source


def test_run_and_dynamic_port_guards_include_focused_native_fields(view, session):
    from ea_node_editor.ui.shell.controllers.run_controller import RunController
    from ea_node_editor.ui.shell.controllers.workspace_edit_controller import WorkspaceEditController
    host = SimpleNamespace(script_editor=view.editor, console_panel=Mock())
    run = SimpleNamespace(_host=host, _suppress_auto_run_for_script_apply=False)
    workspace = SimpleNamespace(_host=host)
    view.editor.select_item("gain")
    field = visible_find(view, "scriptField_default")
    field.forceActiveFocus()
    QTest.keyClick(view.view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    for key in (Qt.Key.Key_2, Qt.Key.Key_Period, Qt.Key.Key_0): QTest.keyClick(view.view, key)
    assert not view.editor.dirty and view.editor.has_unapplied_edits
    assert WorkspaceEditController.dynamic_port_edit_error(workspace, session.node_id)
    assert RunController._apply_dirty_script_draft(run)
    assert "default=2.0" in session.graph.active_workspace.nodes[session.node_id].properties["script"]
    field = visible_find(view, "scriptField_default")
    field.forceActiveFocus()
    QTest.keyClick(view.view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(view.view, Qt.Key.Key_X)
    assert not RunController._apply_dirty_script_draft(run)
    assert view.editor.has_unapplied_edits


def test_invalid_native_form_transfers_between_editor_views(view, session, qapp):
    view.editor.select_item("gain")
    field = visible_find(view, "scriptField_default")
    field.setProperty("text", "banana")
    QMetaObject.invokeMethod(field, "editingFinished")
    view.view.hide()
    second_generator = globals()["view"].__wrapped__(session, qapp)
    second = next(second_generator)
    try:
        assert visible_find(second, "scriptField_default").property("text") == "banana"
        assert find(second, "scriptSelectedForm").property("error")
        assert not session.editor.apply()
        field = visible_find(second, "scriptField_default")
        field.setProperty("text", "2.0")
        QMetaObject.invokeMethod(field, "editingFinished")
        QTest.qWait(10)
        assert session.editor.apply()
    finally:
        try: next(second_generator)
        except StopIteration: pass


def test_invalid_native_form_restores_after_node_switch(view, session):
    editor = view.editor
    editor.select_item("gain")
    field = visible_find(view, "scriptField_default")
    field.setProperty("text", "banana")
    QMetaObject.invokeMethod(field, "editingFinished")
    other = session.scene.add_node_from_type("core.python_script", 0, 0)
    editor.set_node(session.graph.active_workspace.nodes[other])
    assert not editor.has_unapplied_edits
    editor.set_node(session.graph.active_workspace.nodes[session.node_id])
    assert editor.selected_key == "gain"
    assert visible_find(view, "scriptField_default").property("text") == "banana"
    assert editor.has_unapplied_edits
    editor.revert()
    assert not editor.has_unapplied_edits


def test_section_operations_are_atomic_and_preserve_authored_order(session):
    editor = session.editor
    original = editor.script_text
    order = [item.key for item in editor.analysis.items]
    assert editor.perform_edit("section", {"name": "Acquisition", "keys": ["values", "gain"]})
    grouped = editor.script_text
    assert [item.key for item in editor.analysis.items] == order
    assert next(item for item in editor.sections if item["name"] == "Acquisition")["keys"] == ["values", "gain"]
    assert editor.undo() and editor.script_text == original
    assert editor.redo() and editor.script_text == grouped
    assert editor.perform_edit("section", {"name": "Processing", "old_name": "Acquisition", "keys": ["values", "gain"]})
    assert not any(item["name"] == "Acquisition" for item in editor.sections)
    assert editor.perform_edit("update", {"key": "gain", "remove_fields": ["section"]})
    assert next(item for item in editor.sections if item["name"] == "Processing")["keys"] == ["values"]
    before = editor.script_text
    assert not editor.perform_edit("section", {"name": "Invalid", "keys": ["result"]})
    assert not editor.perform_edit("section", {"name": "Empty", "keys": []})
    assert editor.script_text == before


def test_add_section_and_rename_existing_section_dialog(view):
    editor = view.editor
    editor.select_item("gain")
    click(view, "scriptAddButton")
    find(view, "scriptAddSearch").setProperty("text", "section")
    QTest.qWait(20)
    click(view, "scriptAddChoice_section")
    capture(view, "section_dialog_light.png")
    find(view, "scriptAddName").setProperty("text", "Tuning")
    assert find(view, "scriptAddConfirm").isEnabled()
    click(view, "scriptAddConfirm")
    assert next(item for item in editor.sections if item["name"] == "Tuning")["keys"] == ["gain"]
    QMetaObject.invokeMethod(view.root, "openSectionEditor", Q_ARG("QVariant", "Tuning"))
    find(view, "scriptAddName").setProperty("text", "Controls")
    click(view, "scriptAddConfirm")
    assert next(item for item in editor.sections if item["name"] == "Controls")["keys"] == ["gain"]


def test_list_row_typing_retains_focus_and_updates_draft(view):
    view.editor.select_item("labels")
    QTest.qWait(30)
    field = visible_find(view, "scriptListRow_0")
    field.forceActiveFocus()
    QTest.keyClick(view.view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    for key in (Qt.Key.Key_H, Qt.Key.Key_E, Qt.Key.Key_L, Qt.Key.Key_L, Qt.Key.Key_O):
        QTest.keyClick(view.view, key)
    assert field.property("text") == "hello"
    assert field.property("activeFocus")
    QMetaObject.invokeMethod(view.root, "requestApply")
    assert not view.editor.dirty
    assert "hello" in view.editor.script_text


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width,height", [(1600, 900), (1000, 800), (650, 800)])
def test_render_authoring_layouts(view, session, width, height, theme):
    session.scene.set_node_property(session.node_id, "script", PRESENTATION_SOURCE)
    session.graph.active_workspace.nodes[session.node_id].title = "Signal summary"
    view.editor.set_node(session.graph.active_workspace.nodes[session.node_id])
    view.theme.apply_theme("stitch_" + theme)
    view.graph_theme.apply_theme("graph_stitch_" + theme)
    view.view.setColor(QColor(view.theme.palette["panel_bg"]))
    view.editor.select_item("gain")
    view.view.resize(width, height)
    QTest.qWait(180)
    find(view, "scriptEditorArea").setProperty("cursorPosition", 0)
    find(view, "scriptEditorArea").deselect()
    assert find(view, "scriptApplyButton").mapToScene(QPointF()).x() >= 0
    if width == 1600:
        sources = [item.property("source") for item in objects(view)
                   if item.property("source") is not None and str(item.property("source")).startswith("PyQt6.QtCore.QUrl('image://ui-icons/")]
        assert sources, "The native icon provider must be present in visual QA"
        icon = next(item for item in objects(view) if isinstance(item.property("source"), QUrl)
                    and item.property("source").toString().startswith("image://ui-icons/script-input?") and item.isVisible())
        point = icon.mapToScene(QPointF()).toPoint()
        window_image = view.view.grabWindow()
        scale = window_image.width() / view.view.width()
        crop = window_image.copy(round(point.x() * scale), round(point.y() * scale), round(icon.width() * scale), round(icon.height() * scale))
        assert len({crop.pixel(x, y) for x in range(crop.width()) for y in range(crop.height())}) > 5, "Native icons must actually render in the window"
    output = os.environ.get("COREX_AUTHORING_SCREENSHOTS")
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        image = view.view.grabWindow()
        assert not image.isNull()
        assert image.save(str(directory / f"authoring_{theme}_{width}.png"))
        if width < 800:
            for index, suffix in ((0, "interface"), (2, "preview")):
                find(view, "scriptWorkspaceTabs").setProperty("currentIndex", index)
                QTest.qWait(40)
                assert view.view.grabWindow().save(str(directory / f"authoring_{theme}_{width}_{suffix}.png"))
        if width == 1600:
            assert view.editor.perform_edit("update", {"key": "gain", "fields": {"default": 1.5}})
            find(view, "scriptEditorArea").deselect()
            QTest.qWait(180)
            assert view.view.grabWindow().save(str(directory / f"authoring_{theme}_{width}_dirty.png"))
