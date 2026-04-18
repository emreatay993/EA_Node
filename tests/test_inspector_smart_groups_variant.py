from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal
from PyQt6.QtQml import QJSEngine, QQmlComponent, QQmlEngine
from PyQt6.QtWidgets import QApplication

from ea_node_editor.ui.icon_registry import UiIconRegistryBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_COMPONENTS_DIR = (
    _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "shell"
)
_INSPECTOR_FILTER_JS_PATH = _SHELL_COMPONENTS_DIR / "InspectorFilter.js"
_SMART_GROUPS_BODY_QML_PATH = _SHELL_COMPONENTS_DIR / "InspectorSmartGroupsBody.qml"


def _load_filter_engine() -> QJSEngine:
    source = _INSPECTOR_FILTER_JS_PATH.read_text(encoding="utf-8")
    stripped = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith(".pragma")
    )
    engine = QJSEngine()
    result = engine.evaluate(stripped)
    if result.isError():
        raise RuntimeError(f"InspectorFilter.js failed to load: {result.toString()}")
    return engine


def _evaluate_helper(engine: QJSEngine, fn_name: str, items: list[dict]) -> object:
    payload = json.dumps(items)
    expression = f"JSON.stringify({fn_name}({payload}))"
    result = engine.evaluate(expression)
    if result.isError():
        raise RuntimeError(f"{fn_name} failed: {result.toString()}")
    return json.loads(result.toString())


class InspectorSmartGroupsJsHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._engine = _load_filter_engine()

    def test_smart_groups_surface_dirty_driven_and_required_sections(self) -> None:
        items = [
            {"key": "a", "label": "A", "dirty": True},
            {"key": "b", "label": "B", "driven_by": "port.in"},
            {"key": "c", "label": "C", "overridden_by_input": True},
            {"key": "d", "label": "D", "required": True},
            {"key": "e", "label": "E"},
        ]

        sections = _evaluate_helper(self._engine, "smartGroups", items)

        kinds = [section["kind"] for section in sections]
        self.assertEqual(kinds, ["modified", "driven", "required"])
        driven_keys = [prop["key"] for prop in sections[1]["items"]]
        self.assertEqual(set(driven_keys), {"b", "c"})
        accents = {section["kind"]: section["accent"] for section in sections}
        self.assertEqual(
            accents,
            {"modified": "edge_warning", "driven": "accent", "required": "run_failed"},
        )

    def test_smart_groups_omits_empty_sections(self) -> None:
        items = [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}]
        sections = _evaluate_helper(self._engine, "smartGroups", items)
        self.assertEqual(sections, [])

    def test_group_property_items_preserves_first_seen_order_and_defaults(self) -> None:
        items = [
            {"key": "a", "group": "Source"},
            {"key": "b", "group": ""},
            {"key": "c", "group": "Source"},
            {"key": "d"},
        ]

        groups = _evaluate_helper(self._engine, "groupPropertyItems", items)

        self.assertEqual([group["name"] for group in groups], ["Source", "Properties"])
        props_by_group = {group["name"]: [prop["key"] for prop in group["items"]] for group in groups}
        self.assertEqual(props_by_group["Source"], ["a", "c"])
        self.assertEqual(props_by_group["Properties"], ["b", "d"])


class _StubPane(QObject):
    """Minimal stand-in for ShellInspectorPane used purely by the smart groups body.

    Only the attributes read by the body / its nested editors are exposed; calling
    into the real inspector bridge is avoided since this test targets layout only.
    """

    changed = pyqtSignal()

    def __init__(self, palette: dict, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._palette = dict(palette)

    @pyqtProperty("QVariantMap", notify=changed)
    def themePalette(self):  # type: ignore[override]
        return self._palette

    @pyqtProperty(bool, notify=changed)
    def isPinInspector(self) -> bool:
        return False

    @pyqtProperty("QVariantList", notify=changed)
    def pinDataTypeOptions(self):
        return []

    @pyqtProperty(QObject, notify=changed)
    def inspectorBridgeRef(self):
        return None


class InspectorSmartGroupsBodyQmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._app = QApplication.instance() or QApplication([])

    def _walk(self, item):
        yield item
        child_items = getattr(item, "childItems", None)
        if not callable(child_items):
            return
        for child in child_items():
            yield from self._walk(child)

    def _find_by_name(self, root, object_name: str):
        for node in self._walk(root):
            if node.objectName() == object_name:
                return node
        return None

    def _load_component(self, initial_property_items: list[dict]):
        engine = QQmlEngine()
        theme_bridge = ThemeBridge(theme_id="stitch_dark")
        ui_icons = UiIconRegistryBridge()
        engine.rootContext().setContextProperty("themeBridge", theme_bridge)
        engine.rootContext().setContextProperty("uiIcons", ui_icons)
        engine.addImportPath(str(_SHELL_COMPONENTS_DIR.parent))

        pane = _StubPane(palette=theme_bridge.palette)

        component = QQmlComponent(engine, QUrl.fromLocalFile(str(_SMART_GROUPS_BODY_QML_PATH)))
        if component.status() != QQmlComponent.Status.Ready:
            errors = "\n".join(error.toString() for error in component.errors())
            raise AssertionError(f"Failed to load InspectorSmartGroupsBody.qml:\n{errors}")
        initial_properties = {
            "pane": pane,
            "propertyItems": list(initial_property_items),
        }
        obj = component.createWithInitialProperties(initial_properties)
        if obj is None:
            errors = "\n".join(error.toString() for error in component.errors())
            raise AssertionError(f"Failed to instantiate InspectorSmartGroupsBody.qml:\n{errors}")
        self._app.processEvents()
        return obj, engine, pane, theme_bridge, ui_icons

    def test_component_loads_and_exposes_static_groups(self) -> None:
        items = [
            {"key": "source_path", "label": "Source Path", "group": "Source", "editor_mode": "text", "value": ""},
            {"key": "comment", "label": "Comment", "group": "", "editor_mode": "text", "value": ""},
        ]

        body, engine, pane, theme_bridge, ui_icons = self._load_component(items)
        try:
            self.assertIsNotNone(self._find_by_name(body, "inspectorStaticGroupHeader_Source"))
            self.assertIsNotNone(self._find_by_name(body, "inspectorStaticGroupHeader_Properties"))
            self.assertIsNone(self._find_by_name(body, "inspectorSmartGroupHeader_modified"))
            self.assertIsNone(self._find_by_name(body, "inspectorSmartGroupHeader_driven"))
            self.assertIsNone(self._find_by_name(body, "inspectorSmartGroupHeader_required"))
        finally:
            body.deleteLater()
            engine.deleteLater()
            pane.deleteLater()
            theme_bridge.deleteLater()
            ui_icons.deleteLater()
            self._app.processEvents()

    def test_smart_group_headers_appear_when_flagged_items_present(self) -> None:
        items = [
            {"key": "a", "label": "A", "group": "Source", "editor_mode": "text", "value": "", "dirty": True},
            {"key": "b", "label": "B", "group": "Source", "editor_mode": "text", "value": "", "overridden_by_input": True},
            {"key": "c", "label": "C", "group": "Post", "editor_mode": "text", "value": "", "required": True},
        ]

        body, engine, pane, theme_bridge, ui_icons = self._load_component(items)
        try:
            self.assertIsNotNone(self._find_by_name(body, "inspectorSmartGroupHeader_modified"))
            self.assertIsNotNone(self._find_by_name(body, "inspectorSmartGroupHeader_driven"))
            self.assertIsNotNone(self._find_by_name(body, "inspectorSmartGroupHeader_required"))
            self.assertIsNotNone(self._find_by_name(body, "inspectorStaticGroupHeader_Source"))
            self.assertIsNotNone(self._find_by_name(body, "inspectorStaticGroupHeader_Post"))
        finally:
            body.deleteLater()
            engine.deleteLater()
            pane.deleteLater()
            theme_bridge.deleteLater()
            ui_icons.deleteLater()
            self._app.processEvents()

    def test_filter_bar_is_present_at_top_of_body(self) -> None:
        items = [{"key": "a", "label": "A", "group": "Source", "editor_mode": "text", "value": ""}]

        body, engine, pane, theme_bridge, ui_icons = self._load_component(items)
        try:
            self.assertIsNotNone(self._find_by_name(body, "inspectorSmartGroupsFilterBar"))
        finally:
            body.deleteLater()
            engine.deleteLater()
            pane.deleteLater()
            theme_bridge.deleteLater()
            ui_icons.deleteLater()
            self._app.processEvents()


if __name__ == "__main__":
    unittest.main()
