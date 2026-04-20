from __future__ import annotations

import time
import unittest
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtQuick import QQuickItem, QQuickWindow
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge

COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"
LOGGER_TYPE_ID = "core.logger"
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _walk_items(root: QObject) -> list[QQuickItem]:
    items: list[QQuickItem] = []

    def _visit(item: QObject) -> None:
        if not isinstance(item, QQuickItem):
            return
        items.append(item)
        for child in item.childItems():
            _visit(child)

    _visit(root)
    return items


def _named_child_items(root: QObject, object_name: str) -> list[QQuickItem]:
    return [item for item in _walk_items(root) if item.objectName() == object_name]


def _variant_value(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


def _node_host(canvas: QObject, node_id: str, *, object_name: str = "graphNodeCard") -> QQuickItem:
    normalized = str(node_id)
    for item in _named_child_items(canvas, object_name):
        payload = _variant_value(item.property("nodeData"))
        if isinstance(payload, dict) and str(payload.get("node_id", "")) == normalized:
            return item
    raise AssertionError(f"Could not find {object_name} for node {node_id!r}.")


def _wait_for(predicate, *, timeout_ms: int = 1000, app: QApplication, message: str) -> None:
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    app.processEvents()
    if predicate():
        return
    raise AssertionError(message)


class _ViewportBridgeStub(QObject):
    view_state_changed = pyqtSignal()

    @pyqtProperty(float, constant=True)
    def center_x(self) -> float:
        return 0.0

    @pyqtProperty(float, constant=True)
    def center_y(self) -> float:
        return 0.0

    @pyqtProperty(float, constant=True)
    def zoom_value(self) -> float:
        return 1.0

    @pyqtProperty("QVariantMap", constant=True)
    def visible_scene_rect_payload(self) -> dict[str, float]:
        return {
            "x": -640.0,
            "y": -480.0,
            "width": 1280.0,
            "height": 960.0,
        }

    @pyqtProperty("QVariantMap", constant=True)
    def visible_scene_rect_payload_cached(self) -> dict[str, float]:
        return self.visible_scene_rect_payload


class CommentBackdropInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)
        self.history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(self.history)
        self.view = _ViewportBridgeStub()
        self._canvas_refs: list[object] = []

    def _workspace(self):
        return self.model.project.workspaces[self.workspace_id]

    def _workspace_node(self, node_id: str):
        return self._workspace().nodes[node_id]

    def _scene_payload(self, node_id: str) -> dict[str, object]:
        for payload in [*self.scene.nodes_model, *self.scene.backdrop_nodes_model]:
            if str(payload["node_id"]) == str(node_id):
                return payload
        raise AssertionError(f"Node payload {node_id!r} was not found.")

    def _add_backdrop(self, x: float, y: float, width: float, height: float) -> str:
        node_id = self.scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, x, y)
        self.scene.set_node_geometry(node_id, x, y, width, height)
        return node_id

    def _create_canvas(self) -> tuple[QObject, QQuickWindow]:
        state_bridge = GraphCanvasStateBridge(scene_bridge=self.scene, view_bridge=self.view)
        command_bridge = GraphCanvasCommandBridge(scene_bridge=self.scene, view_bridge=self.view)
        compat_bridge = GraphCanvasBridge(
            scene_bridge=self.scene,
            view_bridge=self.view,
            state_bridge=state_bridge,
            command_bridge=command_bridge,
        )

        engine = QQmlEngine()
        engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
        engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))
        engine.rootContext().setContextProperty("graphCanvasBridge", compat_bridge)
        self.addCleanup(engine.deleteLater)
        self._canvas_refs.extend([state_bridge, command_bridge, compat_bridge, engine])

        component = QQmlComponent(
            engine,
            QUrl.fromLocalFile(str(_REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml")),
        )
        if component.status() != QQmlComponent.Status.Ready:
            errors = "\n".join(error.toString() for error in component.errors())
            self.fail(f"Failed to load GraphCanvas.qml:\n{errors}")

        initial_properties = {
            "canvasStateBridge": state_bridge,
            "canvasCommandBridge": command_bridge,
            "width": 1280.0,
            "height": 960.0,
        }
        if hasattr(component, "createWithInitialProperties"):
            canvas = component.createWithInitialProperties(initial_properties)
        else:
            canvas = component.create()
            for key, value in initial_properties.items():
                canvas.setProperty(key, value)
        self.addCleanup(lambda: canvas.deleteLater() if canvas is not None else None)
        if canvas is None:
            errors = "\n".join(error.toString() for error in component.errors())
            self.fail(f"Failed to instantiate GraphCanvas.qml:\n{errors}")

        window = QQuickWindow()
        window.resize(1280, 960)
        canvas.setParentItem(window.contentItem())
        window.show()
        self.addCleanup(window.close)
        self.addCleanup(window.deleteLater)
        return canvas, window

    def test_graph_canvas_scene_state_skips_edge_redraw_for_comment_backdrop_live_resize(self) -> None:
        class _EdgeLayerCounter(QObject):
            def __init__(self) -> None:
                super().__init__()
                self.request_count = 0

            @pyqtSlot()
            def requestRedraw(self) -> None:
                self.request_count += 1

        class _SceneStateBridgeStub(QObject):
            def __init__(self, nodes_model: list[dict], backdrop_nodes_model: list[dict]) -> None:
                super().__init__()
                self._nodes_model = list(nodes_model)
                self._backdrop_nodes_model = list(backdrop_nodes_model)

            @pyqtProperty("QVariantList", constant=True)
            def nodes_model(self) -> list[dict]:
                return self._nodes_model

            @pyqtProperty("QVariantList", constant=True)
            def backdrop_nodes_model(self) -> list[dict]:
                return self._backdrop_nodes_model

        class _CanvasItemStub(QObject):
            def __init__(self, scene_state_bridge: QObject) -> None:
                super().__init__()
                self._scene_state_bridge = scene_state_bridge

            @pyqtProperty(QObject, constant=True)
            def _canvasSceneStateBridgeRef(self) -> QObject:
                return self._scene_state_bridge

            @pyqtProperty("QVariantList", constant=True)
            def edgePayload(self) -> list[dict]:
                return []

        graph_canvas_scene_state_qml = (
            _REPO_ROOT
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph_canvas"
            / "GraphCanvasSceneState.qml"
        )
        standard_payload = {
            "node_id": "standard_resize_node",
            "surface_family": "standard",
            "ports": [
                {
                    "key": "exec_in",
                    "direction": "in",
                    "kind": "exec",
                    "data_type": "exec",
                    "connected": False,
                },
                {
                    "key": "exec_out",
                    "direction": "out",
                    "kind": "exec",
                    "data_type": "exec",
                    "connected": False,
                },
            ],
        }
        comment_backdrop_payload = {
            "node_id": "comment_backdrop_resize_node",
            "surface_family": "comment_backdrop",
            "surface_variant": "comment_backdrop",
            "ports": [],
        }

        scene_state_bridge = _SceneStateBridgeStub([standard_payload], [comment_backdrop_payload])
        canvas_item = _CanvasItemStub(scene_state_bridge)
        edge_counter = _EdgeLayerCounter()

        engine = QQmlEngine()
        self.addCleanup(engine.deleteLater)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(graph_canvas_scene_state_qml)))
        if component.status() != QQmlComponent.Status.Ready:
            errors = "\n".join(error.toString() for error in component.errors())
            self.fail(f"Failed to load GraphCanvasSceneState.qml:\n{errors}")
        state = component.createWithInitialProperties(
            {
                "canvasItem": canvas_item,
                "edgeLayerItem": edge_counter,
            }
        )
        self.addCleanup(lambda: state.deleteLater() if state is not None else None)
        if state is None:
            errors = "\n".join(error.toString() for error in component.errors())
            self.fail(f"Failed to instantiate GraphCanvasSceneState.qml:\n{errors}")

        state.setLiveNodeGeometry("comment_backdrop_resize_node", 18.0, 26.0, 320.0, 180.0, True)
        self.app.processEvents()
        self.assertEqual(
            _variant_value(state.property("liveNodeGeometry"))["comment_backdrop_resize_node"],
            {
                "x": 18.0,
                "y": 26.0,
                "width": 320.0,
                "height": 180.0,
            },
        )
        self.assertEqual(edge_counter.request_count, 0)

        state.setLiveNodeGeometry("comment_backdrop_resize_node", 18.0, 26.0, 320.0, 180.0, False)
        self.app.processEvents()
        self.assertEqual(_variant_value(state.property("liveNodeGeometry")), {})
        self.assertEqual(edge_counter.request_count, 0)

        state.setLiveNodeGeometry("standard_resize_node", 42.0, 64.0, 260.0, 120.0, True)
        self.app.processEvents()
        self.assertEqual(
            _variant_value(state.property("liveNodeGeometry"))["standard_resize_node"],
            {
                "x": 42.0,
                "y": 64.0,
                "width": 260.0,
                "height": 120.0,
            },
        )
        self.assertEqual(edge_counter.request_count, 1)

        state.setLiveNodeGeometry("standard_resize_node", 42.0, 64.0, 260.0, 120.0, False)
        self.app.processEvents()
        self.assertEqual(_variant_value(state.property("liveNodeGeometry")), {})
        self.assertEqual(edge_counter.request_count, 2)

    def test_graph_canvas_dragging_backdrop_moves_nested_descendants_once_and_preserves_selection(self) -> None:
        outer_id = self._add_backdrop(40.0, 40.0, 760.0, 520.0)
        inner_id = self._add_backdrop(140.0, 130.0, 320.0, 240.0)
        inner_logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 190.0, 180.0)
        outer_logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 520.0, 260.0)
        outside_logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 880.0, 220.0)

        self.assertEqual(self._scene_payload(inner_id)["owner_backdrop_id"], outer_id)
        self.assertEqual(self._scene_payload(inner_logger_id)["owner_backdrop_id"], inner_id)
        self.assertEqual(self._scene_payload(outer_logger_id)["owner_backdrop_id"], outer_id)
        self.assertEqual(self._scene_payload(outside_logger_id)["owner_backdrop_id"], "")

        self.scene.select_node(outer_id, False)
        self.history.clear_workspace(self.workspace_id)
        workspace = self._workspace()
        canvas, _window = self._create_canvas()

        _wait_for(
            lambda: len(_named_child_items(canvas, "graphCommentBackdropInputCard")) == 2,
            timeout_ms=1500,
            app=self.app,
            message="Timed out waiting for comment backdrop input hosts to appear.",
        )
        outer_input_host = _node_host(canvas, outer_id, object_name="graphCommentBackdropInputCard")
        drag_node_ids = list(_variant_value(canvas.dragNodeIdsForAnchor(outer_id)) or [])
        self.assertEqual(drag_node_ids[0], outer_id)
        self.assertEqual(set(drag_node_ids), {outer_id, inner_id, inner_logger_id, outer_logger_id})

        outer_input_host.dragFinished.emit(outer_id, 120.0, 90.0, True)

        _wait_for(
            lambda: abs(float(workspace.nodes[outer_id].x) - 120.0) < 0.01,
            timeout_ms=1500,
            app=self.app,
            message="Timed out waiting for backdrop drag to commit.",
        )

        self.assertAlmostEqual(float(workspace.nodes[outer_id].x), 120.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].y), 90.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), 180.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 270.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].y), 230.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].x), 600.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].y), 310.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].x), 880.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].y), 220.0, places=6)
        self.assertEqual(self.scene.selected_node_lookup, {outer_id: True})
        self.assertEqual(self._scene_payload(inner_id)["owner_backdrop_id"], outer_id)
        self.assertEqual(self._scene_payload(inner_logger_id)["owner_backdrop_id"], inner_id)
        self.assertEqual(self.history.undo_depth(self.workspace_id), 1)

        self.assertIsNotNone(self.history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].x), 40.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].y), 40.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 140.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), 130.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 190.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].y), 180.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].x), 520.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].y), 260.0, places=6)

        self.assertIsNotNone(self.history.redo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].x), 120.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].y), 90.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), 180.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 270.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].y), 230.0, places=6)

    def test_graph_canvas_live_resize_keeps_wrapped_text_preview_and_mirrors_geometry(self) -> None:
        backdrop_id = self._add_backdrop(160.0, 120.0, 380.0, 260.0)
        self.scene.set_node_property(backdrop_id, "body", "Backdrop note body")
        self.scene.select_node(backdrop_id, False)
        workspace = self._workspace()
        canvas, _window = self._create_canvas()

        _wait_for(
            lambda: len(_named_child_items(canvas, "graphCommentBackdropInputCard")) == 1,
            timeout_ms=1500,
            app=self.app,
            message="Timed out waiting for the selected comment backdrop input host to appear.",
        )

        backdrop_host = _node_host(canvas, backdrop_id)
        backdrop_input_host = _node_host(canvas, backdrop_id, object_name="graphCommentBackdropInputCard")
        body_editor = backdrop_input_host.findChild(QObject, "graphCommentBackdropBodyEditor")
        body_text = backdrop_input_host.findChild(QObject, "graphNodeCommentBackdropBodyText")
        surface = backdrop_input_host.findChild(QObject, "graphNodeCommentBackdropSurface")
        self.assertIsNotNone(body_editor)
        self.assertIsNotNone(body_text)
        self.assertIsNotNone(surface)

        _wait_for(
            lambda: bool(body_editor.property("visible")),
            timeout_ms=1000,
            app=self.app,
            message="Timed out waiting for the selected comment backdrop editor to become visible.",
        )

        backdrop_input_host.resizePreviewChanged.emit(backdrop_id, 190.0, 140.0, 420.0, 310.0, True)

        _wait_for(
            lambda: (
                bool(backdrop_host.property("_liveGeometryActive"))
                and bool(backdrop_input_host.property("_liveGeometryActive"))
                and bool(surface.property("livePreviewActive"))
            ),
            timeout_ms=1000,
            app=self.app,
            message="Timed out waiting for comment backdrop live-resize preview to activate.",
        )

        live_geometry = _variant_value(canvas.property("liveNodeGeometry"))
        self.assertEqual(
            live_geometry[backdrop_id],
            {
                "x": 190.0,
                "y": 140.0,
                "width": 420.0,
                "height": 310.0,
            },
        )
        self.assertAlmostEqual(float(backdrop_host.property("_liveX")), 190.0, places=6)
        self.assertAlmostEqual(float(backdrop_host.property("_liveY")), 140.0, places=6)
        self.assertAlmostEqual(float(backdrop_host.property("_liveWidth")), 420.0, places=6)
        self.assertAlmostEqual(float(backdrop_host.property("_liveHeight")), 310.0, places=6)
        self.assertAlmostEqual(float(backdrop_input_host.property("_liveWidth")), 420.0, places=6)
        self.assertAlmostEqual(float(backdrop_input_host.property("_liveHeight")), 310.0, places=6)
        self.assertFalse(bool(body_editor.property("visible")))
        self.assertTrue(bool(body_text.property("visible")))

        backdrop_input_host.resizeFinished.emit(backdrop_id, 190.0, 140.0, 420.0, 310.0)

        _wait_for(
            lambda: (
                _variant_value(canvas.property("liveNodeGeometry")) == {}
                and abs(float(workspace.nodes[backdrop_id].x) - 190.0) < 0.01
                and abs(float(workspace.nodes[backdrop_id].y) - 140.0) < 0.01
            ),
            timeout_ms=1500,
            app=self.app,
            message="Timed out waiting for comment backdrop live-resize preview to settle.",
        )

        refreshed_backdrop_host = _node_host(canvas, backdrop_id)
        refreshed_backdrop_input_host = _node_host(canvas, backdrop_id, object_name="graphCommentBackdropInputCard")
        refreshed_body_editor = refreshed_backdrop_input_host.findChild(QObject, "graphCommentBackdropBodyEditor")
        refreshed_body_text = refreshed_backdrop_input_host.findChild(QObject, "graphNodeCommentBackdropBodyText")
        self.assertIsNotNone(refreshed_body_editor)
        self.assertIsNotNone(refreshed_body_text)

        self.assertFalse(bool(refreshed_backdrop_host.property("_liveGeometryActive")))
        self.assertFalse(bool(refreshed_backdrop_input_host.property("_liveGeometryActive")))
        self.assertTrue(bool(refreshed_body_editor.property("visible")))
        self.assertFalse(bool(refreshed_body_text.property("visible")))
        self.assertAlmostEqual(float(workspace.nodes[backdrop_id].x), 190.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[backdrop_id].y), 140.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[backdrop_id].custom_width or 0.0), 420.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[backdrop_id].custom_height or 0.0), 310.0, places=6)

    def test_scene_resize_backdrop_recomputes_nested_membership_without_moving_other_nodes(self) -> None:
        outer_id = self._add_backdrop(100.0, 100.0, 760.0, 520.0)
        inner_id = self._add_backdrop(220.0, 170.0, 320.0, 240.0)
        inner_logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 260.0, 220.0)
        outside_logger_id = self.scene.add_node_from_type(LOGGER_TYPE_ID, 980.0, 220.0)

        self.assertEqual(self._scene_payload(inner_id)["owner_backdrop_id"], outer_id)
        self.assertEqual(self._scene_payload(inner_logger_id)["owner_backdrop_id"], inner_id)
        self.assertEqual(self._scene_payload(outside_logger_id)["owner_backdrop_id"], "")

        workspace = self._workspace()
        self.history.clear_workspace(self.workspace_id)
        self.scene.set_node_geometry(outer_id, 100.0, 100.0, 240.0, 160.0)

        outer_payload = self._scene_payload(outer_id)
        inner_payload = self._scene_payload(inner_id)
        inner_logger_payload = self._scene_payload(inner_logger_id)
        outside_logger_payload = self._scene_payload(outside_logger_id)

        self.assertAlmostEqual(float(workspace.nodes[outer_id].x), 100.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].y), 100.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_width or 0.0), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_height or 0.0), 180.0, places=6)
        self.assertEqual(outer_payload["member_backdrop_ids"], [])
        self.assertEqual(outer_payload["contained_backdrop_ids"], [])
        self.assertEqual(inner_payload["owner_backdrop_id"], "")
        self.assertEqual(inner_logger_payload["owner_backdrop_id"], inner_id)
        self.assertEqual(outside_logger_payload["owner_backdrop_id"], "")
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), 170.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].y), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].x), 980.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].y), 220.0, places=6)
        self.assertEqual(self.history.undo_depth(self.workspace_id), 1)

        self.assertIsNotNone(self.history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertEqual(self._scene_payload(inner_id)["owner_backdrop_id"], outer_id)
        self.assertEqual(self._scene_payload(inner_logger_id)["owner_backdrop_id"], inner_id)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_width or 0.0), 760.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_height or 0.0), 520.0, places=6)

        self.assertIsNotNone(self.history.redo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertEqual(self._scene_payload(inner_id)["owner_backdrop_id"], "")
        self.assertEqual(self._scene_payload(inner_logger_id)["owner_backdrop_id"], inner_id)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_width or 0.0), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_height or 0.0), 180.0, places=6)


if __name__ == "__main__":
    unittest.main()
