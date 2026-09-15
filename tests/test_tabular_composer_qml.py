# Purpose: Exercise and render the production fullscreen composer with a real backend session.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_qml.py
from pathlib import Path
import time

import numpy as np
import pytest
from PyQt6.QtCore import QObject, QPointF, QUrl, Qt, pyqtProperty, pyqtSlot
from PyQt6.QtQuick import QQuickView
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtTest import QTest

from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
from ea_node_editor.ui.tabular_composer_session import TabularComposerSession
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider
from ea_node_editor.ui_qml import register_qml_types


class Bridge(QObject):
    def __init__(self, session):
        super().__init__()
        self.session = session

    @pyqtProperty(QObject, constant=True)
    def tabular_composer(self):
        return self.session

    @pyqtSlot("QVariantMap", result=bool)
    def save_tabular_table_view_state(self, state):
        return True


def wait_for(app, predicate):
    deadline = time.monotonic() + 12
    while not predicate():
        app.processEvents()
        if time.monotonic() > deadline:
            raise AssertionError("QML composer did not settle")
        QTest.qWait(10)


def visual_child(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = visual_child(child, name)
        if found is not None:
            return found
    return None


@pytest.fixture
def rendered(tmp_path, qapp, request):
    register_qml_types()
    previous_font = qapp.font()
    font_id = -1
    windows_font = Path("C:/Windows/Fonts/segoeui.ttf")
    if windows_font.is_file():
        font_id = QFontDatabase.addApplicationFont(str(windows_font))
        qapp.setFont(QFont("Segoe UI", 9))
    source = tmp_path / "example.npz"
    np.savez(source, values=np.arange(60).reshape(20, 3), labels=np.array(["Housing", "Shaft", "Gear"]), time_s=np.arange(20))
    props = {"path": str(source), "data_view_name": "Temperature history", "data_view": {
        "version": 1, "mode": "table", "segments": [{"blocks": [{"member": "values", "labels_member": "labels", "unit": "C"}],
                                                       "coordinate": {"member": "time_s", "name": "time_s", "unit": "s"}}]}}
    if hasattr(request, "param"):
        import csv
        suffix, delimiter = request.param
        source = tmp_path / ("example." + suffix)
        with source.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter=delimiter)
            writer.writerow(["time_s", "Housing", "Shaft", "Gear"])
            writer.writerows([[row, row * 3, row * 3 + 1, row * 3 + 2] for row in range(20)])
        props = {"path": str(source), "data_view": {"version": 1, "mode": "source"}}
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    session = TabularComposerSession(read_properties=lambda: props, apply_properties=lambda values: bool(props.update(values) is None),
                                     project_context=lambda: (None, None),
                                     provider_factory=lambda **kw: TabularPreviewProvider(service_factory=lambda: loader, **kw))
    bridge = Bridge(session)
    view = QQuickView()
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(1200, 1000)
    view.setInitialProperties({"bridgeRef": bridge})
    path = Path(__file__).parents[1] / "ea_node_editor/ui_qml/components/graph/tabular/TabularFullscreenSurface.qml"
    view.setSource(QUrl.fromLocalFile(str(path)))
    assert view.status() == QQuickView.Status.Ready, "\n".join(error.toString() for error in view.errors())
    session.begin(props)
    view.show()
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"], session.state
    QTest.qWait(80)
    yield view, session, props
    session.shutdown()
    view.close()
    view.deleteLater()
    qapp.setFont(previous_font)
    if font_id >= 0:
        QFontDatabase.removeApplicationFont(font_id)
    qapp.processEvents()


def test_composer_loads_real_mapping_and_apply_action(rendered, qapp, tmp_path):
    view, session, props = rendered
    root = view.rootObject()
    apply = root.findChild(QObject, "tabularComposerApply")
    assert apply is not None and apply.property("enabled")
    assert root.findChild(QObject, "tabularComposerCatalogue") is not None
    assert visual_child(root, "tabularComposerValues") is not None
    assert root.findChild(QObject, "contentFullscreenTabularGrid").property("rowCount") == 20
    assert not view.grabWindow().isNull()
    view.grabWindow().save(str(tmp_path / "composer-dark.png"))
    session.edit_property("data_view_name", "Renamed history")
    position = apply.mapToScene(QPointF(apply.property("width") / 2, apply.property("height") / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, position)
    qapp.processEvents()
    assert props["data_view_name"] == "Renamed history"


@pytest.mark.parametrize("rendered", [("csv", ","), ("tsv", "\t"), ("txt", ";")], indirect=True)
def test_delimited_file_configure_apply_reopen_and_export(rendered, qapp, tmp_path):
    import csv
    import json
    from ea_node_editor.addons.tabular_data.input_node import tabular_load_options_from_node_properties
    from ea_node_editor.ui.tabular_composer_export import export_composer_data

    view, session, props = rendered
    root = view.rootObject()
    original_source = Path(props["path"]).read_bytes()
    assert session.catalogue.total == 1
    assert session.state["preview"]["metadata"]["row_count"] == 20
    assert session.state["preview"]["window"]["columns"] == ["time_s", "Housing", "Shaft", "Gear"]
    assert not root.findChild(QObject, "tabularComposerArrayMode").property("enabled")
    click(view, root.findChild(QObject, "tabularComposerTableMode"))
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"], session.state["error"]
    click(view, root.findChild(QObject, "tabularComposerRulesTab"))
    qapp.processEvents()
    click(view, root.findChild(QObject, "tabularComposerAddCondition"))
    wait_for(qapp, lambda: not session.state["busy"])
    value = visual_child(root, "tabularComposerFilterValue")
    click(view, value)
    QTest.keyClick(view, Qt.Key.Key_5)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_for(qapp, lambda: not session.state["busy"])
    count = root.findChild(QObject, "tabularComposerOutputCount")
    # A condition adds a form row; scroll the editor before using its range control.
    editor = root.findChild(QObject, "tabularComposerEditor").property("contentItem")
    editor.setProperty("contentY", max(0, editor.property("contentHeight") - editor.height()))
    qapp.processEvents()
    QTest.qWait(40)
    click(view, count)
    QTest.keyClick(view, Qt.Key.Key_3)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"], session.state["error"]
    assert session.state["draft"]["data_view"]["output"]["row_limit"] == 3
    click(view, root.findChild(QObject, "tabularComposerApply"))
    qapp.processEvents()
    assert not session.state["dirty"]
    restored = json.loads(json.dumps(props))
    fresh = TabularLoaderCacheService(cache_dir=tmp_path / "fresh-cache")
    source_path = Path(restored["path"])
    ref = fresh.open_source(source_path, tabular_load_options_from_node_properties(restored))
    assert fresh.schema(ref).row_count == 3  # Cold refs may defer their exact count until read.
    values = fresh.column_arrays(ref, columns=["time_s", "Housing"])
    assert values["time_s"].tolist() == [6, 7, 8]
    assert values["Housing"].tolist() == [18, 21, 24]
    target = tmp_path / "configured.csv"
    export_composer_data(properties=restored, project_context=(None, None), preview={}, scope="output",
                         selection={}, output_path=target, service=fresh)
    with target.open(newline="", encoding="utf-8") as stream:
        exported = list(csv.DictReader(stream))
    assert [int(row["time_s"]) for row in exported] == [6, 7, 8]
    assert source_path.read_bytes() == original_source


def test_mapping_validation_hides_old_rows_and_recovers(rendered, qapp):
    view, session, _ = rendered
    definition = session.state["draft"]["data_view"]
    definition["segments"][0]["blocks"][0]["labels_member"] = "time_s"
    session.update_definition(definition)
    wait_for(qapp, lambda: not session.state["busy"])
    assert not session.state["valid"]
    assert not view.rootObject().findChild(QObject, "tabularComposerApply").property("enabled")
    assert not view.rootObject().findChild(QObject, "contentFullscreenTabularGrid").property("visible")
    definition["segments"][0]["blocks"][0]["labels_member"] = "labels"
    session.update_definition(definition)
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"]


def test_narrow_fullscreen_and_dirty_close(rendered, qapp, tmp_path):
    view, session, _ = rendered
    view.resize(800, 1100)
    QTest.qWait(50)
    assert not view.grabWindow().isNull()
    view.grabWindow().save(str(tmp_path / "composer-narrow.png"))
    session.edit_property("data_view_name", "Unapplied")
    session.request_close()
    qapp.processEvents()
    assert session.state["close_pending"]
    session.keep_editing()
    assert not session.state["close_pending"]


def click(view, control):
    position = control.mapToScene(QPointF(control.property("width") / 2, control.property("height") / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, position)


def test_saved_condition_is_authored_with_real_controls(rendered, qapp):
    view, session, _ = rendered
    root = view.rootObject()
    click(view, root.findChild(QObject, "tabularComposerRulesTab"))
    qapp.processEvents()
    click(view, root.findChild(QObject, "tabularComposerAddCondition"))
    wait_for(qapp, lambda: not session.state["busy"])
    value = visual_child(root, "tabularComposerFilterValue")
    assert value is not None
    click(view, value)
    QTest.keyClick(view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(view, Qt.Key.Key_5)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"], session.state
    assert session.state["draft"]["data_view"]["query"]["filters"][0]["value"] == "5"
    assert session.state["preview"]["metadata"]["row_count"] == 14


def test_light_theme_uses_light_surfaces_and_readable_controls(rendered, qapp, tmp_path):
    view, session, _ = rendered
    view.rootObject().setProperty("themePalette", {"panel_bg": "#ffffff", "panel_alt_bg": "#f1f3f7", "panel_fg": "#232c3c",
                                                   "input_bg": "#ffffff", "input_fg": "#232c3c", "muted_fg": "#637085",
                                                   "border": "#dce1e9", "input_border": "#dce1e9", "accent": "#126bb0",
                                                   "toolbar_bg": "#f1f3f7", "hover": "#edf3fa"})
    QTest.qWait(50)
    image = view.grabWindow()
    assert image.pixelColor(5, 5).lightness() > 220
    assert image.save(str(tmp_path / "composer-light.png"))


def test_output_range_is_authored_from_real_controls(rendered, qapp):
    view, session, _ = rendered
    root = view.rootObject()
    click(view, root.findChild(QObject, "tabularComposerRulesTab"))
    qapp.processEvents()
    count = root.findChild(QObject, "tabularComposerOutputCount")
    click(view, count)
    QTest.keyClick(view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(view, Qt.Key.Key_3)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"], session.state
    assert session.state["draft"]["data_view"]["output"]["row_limit"] == 3
    assert session.state["preview"]["metadata"]["row_count"] == 3


def test_core_mapping_fits_without_expanding_advanced_fields(rendered, qapp, tmp_path):
    view, session, _ = rendered
    root = view.rootObject()
    editor = root.findChild(QObject, "tabularComposerEditor")
    coordinate = visual_child(root, "tabularComposerCoordinate")
    assert coordinate.isVisible()
    assert coordinate.mapToScene(QPointF(0, coordinate.height())).y() <= editor.mapToScene(QPointF(0, editor.height())).y()
    source_columns = visual_child(root, "tabularComposerBlockColumns")
    assert not source_columns.isVisible()
    before = session.state["draft"]
    click(view, visual_child(root, "tabularComposerAdvanced"))
    qapp.processEvents()
    assert source_columns.isVisible()
    assert session.state["draft"] == before
    view.grabWindow().save(str(tmp_path / "composer-advanced.png"))


def test_member_popup_uses_archive_roles_and_keyboard_selection(rendered, qapp):
    view, session, _ = rendered
    values = visual_child(view.rootObject(), "tabularComposerValues")
    assert values.property("count") == 3
    click(view, values)
    qapp.processEvents()
    QTest.keyClick(view, Qt.Key.Key_End)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["draft"]["data_view"]["segments"][0]["blocks"][0]["member"] == "time_s"


@pytest.mark.parametrize("width,height", [(1480, 820), (1100, 780), (760, 1024)])
def test_footer_and_preview_do_not_overlap_at_common_window_sizes(rendered, qapp, width, height):
    view, _, _ = rendered
    view.resize(width, height)
    QTest.qWait(60)
    root = view.rootObject()
    footer = root.findChild(QObject, "tabularComposerFooter")
    preview = root.findChild(QObject, "tabularComposerPreviewCard")
    apply = root.findChild(QObject, "tabularComposerApply")
    cancel = root.findChild(QObject, "tabularComposerCancel")
    assert footer.mapToScene(QPointF(0, footer.height())).y() <= height
    assert preview.mapToScene(QPointF(0, preview.height())).y() < footer.mapToScene(QPointF(0, 0)).y()
    assert cancel.mapToScene(QPointF(cancel.width(), 0)).x() < apply.mapToScene(QPointF(0, 0)).x()
    assert apply.mapToScene(QPointF(apply.width(), 0)).x() <= width


def test_no_source_shows_onboarding_instead_of_empty_mapping_form(rendered, qapp, tmp_path):
    view, session, _ = rendered
    session.set_source("", False)
    wait_for(qapp, lambda: not session.state["busy"])
    root = view.rootObject()
    assert root.findChild(QObject, "tabularComposerEmptyState").isVisible()
    assert not root.findChild(QObject, "tabularComposerEditor").isVisible()
    assert not root.findChild(QObject, "tabularComposerApply").property("enabled")
    assert root.findChild(QObject, "tabularComposerChooseSource").property("enabled")
    assert view.grabWindow().save(str(tmp_path / "composer-empty-dark.png"))
    root.setProperty("themePalette", {"panel_bg": "#f5f7fb", "input_bg": "#ffffff", "panel_alt_bg": "#eef2f8",
                                     "panel_fg": "#24324b", "input_fg": "#24324b", "border": "#dce3ee",
                                     "muted_fg": "#68778d", "accent": "#2563eb"})
    QTest.qWait(60)
    assert view.grabWindow().save(str(tmp_path / "composer-empty-light.png"))


def test_advanced_axis_entry_and_raw_mode_keep_existing_data_contract(rendered, qapp, tmp_path):
    view, session, _ = rendered
    root = view.rootObject()
    original = session.state["draft"]["data_view"]
    click(view, root.findChild(QObject, "tabularComposerArrayMode"))
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["valid"]
    assert session.state["preview"]["preview_kind"] == "array"
    assert not root.findChild(QObject, "tabularComposerRulesTab").property("enabled")
    assert view.grabWindow().save(str(tmp_path / "composer-array.png"))
    click(view, root.findChild(QObject, "tabularComposerTableMode"))
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["draft"]["data_view"] == original
    click(view, root.findChild(QObject, "tabularComposerRulesTab"))
    qapp.processEvents()
    assert view.grabWindow().save(str(tmp_path / "composer-rules.png"))
    # Exercise the custom editable spin control, not just its Python property.
    click(view, root.findChild(QObject, "tabularComposerMappingTab"))
    qapp.processEvents()
    click(view, visual_child(root, "tabularComposerAdvanced"))
    qapp.processEvents()
    QTest.qWait(40)
    axis = visual_child(root, "tabularComposerRowAxis")
    click(view, axis)
    QTest.keyClick(view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(view, Qt.Key.Key_1)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_for(qapp, lambda: not session.state["busy"])
    assert session.state["draft"]["data_view"]["segments"][0]["blocks"][0].get("axes", {}).get("row") == 1, (axis.property("value"), axis.property("activeFocus"), axis.isVisible())
