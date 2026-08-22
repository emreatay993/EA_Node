from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.ui_qml.viewer_control_bridge import ViewerControlBridge


class _SceneBridgeStub(QObject):
    workspace_changed = pyqtSignal(str)
    nodes_changed = pyqtSignal()

    def __init__(self, node: SimpleNamespace) -> None:
        super().__init__()
        self.workspace_id = "workspace"
        self._node = node

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        if node_id != "node":
            raise KeyError(node_id)
        self._node.properties[key] = value
        self.nodes_changed.emit()


class _SessionBridgeStub(QObject):
    viewer_query_completed = pyqtSignal(str, dict)
    sessions_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.sync_calls: list[tuple[str, str, Any, dict[str, Any]]] = []
        self.session_id = "session"

    def sync_node_property_option(
        self,
        node_id: str,
        key: str,
        value: Any,
        context: dict[str, Any],
    ) -> bool:
        self.sync_calls.append((node_id, key, value, dict(context)))
        return True

    def session_state(self, node_id: str) -> dict[str, Any]:
        return {
            "workspace_id": "workspace",
            "node_id": node_id,
            "session_id": self.session_id,
            "summary": {"scene_fingerprint": "a" * 64},
        }


class _ViewerHostStub:
    def __init__(self) -> None:
        self.camera_state: dict[str, Any] = {"zoom": 1.0, "parallel_projection": False}
        self.applied: list[tuple[str, dict[str, Any]]] = []
        self.selection_filters: list[tuple[str, str]] = []
        self.selection = {
            "scene_fingerprint": "a" * 64,
            "entities": [
                {
                    "layer_id": "primary",
                    "source_fingerprint": "a" * 64,
                    "entity_kind": "cad_face",
                    "entity_id": f"part:1/face:{value}",
                }
                for value in (8, 2)
            ],
            "isolate_active": False,
            "selection_filter": "cad_face",
        }

    def camera_state_snapshot(self, _node_id: str) -> dict[str, Any]:
        return dict(self.camera_state)

    def apply_overlay_camera_state(self, node_id: str, state: dict[str, Any]) -> bool:
        self.applied.append((node_id, dict(state)))
        return True

    def viewer_selection_snapshot(self, _node_id: str) -> dict[str, Any]:
        return dict(self.selection)

    def activate_viewer_selection(self, _node_id: str, _entities: list[dict[str, str]]) -> bool:
        return True

    def set_viewer_selection_filter(self, _node_id: str, _value: str) -> bool:
        self.selection_filters.append((_node_id, _value))
        return True


class _AppPreferencesControllerStub:
    def __init__(self) -> None:
        self.graphics = {"engineering_viewer": {"tangent_selection_angle_degrees": 5.0}}
        self.updates: list[tuple[dict[str, Any], Any]] = []

    def graphics_settings(self) -> dict[str, Any]:
        return self.graphics

    def update_graphics_settings(self, updates: dict[str, Any], *, host=None) -> None:  # noqa: ANN001
        self.updates.append((updates, host))
        self.graphics["engineering_viewer"] = dict(updates["engineering_viewer"])


class ViewerControlBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.node = SimpleNamespace(properties={}, title="Viewer")
        self.workspace = SimpleNamespace(nodes={"node": self.node})
        manager = SimpleNamespace(active_workspace_id=lambda: "workspace")
        self.host = _ViewerHostStub()
        self.preferences = _AppPreferencesControllerStub()
        shell = SimpleNamespace(
            workspace_manager=manager,
            model=SimpleNamespace(project=SimpleNamespace(workspaces={"workspace": self.workspace})),
            viewer_host_service=self.host,
            app_preferences_controller=self.preferences,
        )
        self.scene = _SceneBridgeStub(self.node)
        self.session = _SessionBridgeStub()
        self.bridge = ViewerControlBridge(
            shell_window=shell,
            scene_bridge=self.scene,
            viewer_session_bridge=self.session,
        )
        self.shell = shell

    def test_node_scoped_options_include_new_render_and_orientation_values(self) -> None:
        self.assertTrue(self.bridge.set_viewer_option("node", "representation", "wireframe_visible_edges"))
        self.assertTrue(self.bridge.set_viewer_option("node", "show_attribute_colors", True))
        self.assertTrue(self.bridge.set_viewer_option("node", "show_orientation_triad", False))
        self.assertTrue(self.bridge.set_viewer_option("node", "show_view_cube", False))
        self.assertTrue(self.bridge.set_viewer_option("node", "show_world_axes", True))
        self.assertFalse(self.bridge.set_viewer_option("node", "unsupported", True))
        self.assertEqual(self.node.properties["representation"], "wireframe_visible_edges")
        self.assertEqual(len(self.session.sync_calls), 5)

    def test_selection_filter_is_runtime_only_and_tangent_angle_is_app_wide(self) -> None:
        self.assertTrue(self.bridge.set_viewer_option("node", "selection_filter", "CAD_FACE"))
        self.assertEqual(self.host.selection_filters, [("node", "cad_face")])
        self.assertNotIn("selection_filter", self.node.properties)
        self.assertEqual(self.session.sync_calls, [])

        changed: list[float] = []
        self.bridge.viewer_tangent_selection_angle_changed.connect(changed.append)
        self.assertEqual(self.bridge.viewer_tangent_selection_angle_degrees(), 5.0)
        self.assertTrue(self.bridge.set_viewer_tangent_selection_angle_degrees(120.0))
        self.assertEqual(changed, [90.0])
        self.assertEqual(
            self.preferences.updates,
            [
                (
                    {"engineering_viewer": {"tangent_selection_angle_degrees": 90.0}},
                    self.shell,
                )
            ],
        )

    def test_saved_views_persist_order_cycle_with_wrap_and_sync_projection(self) -> None:
        front = {
            "position": [1.0, 2.0, 3.0],
            "focal_point": [0.0, 0.0, 0.0],
            "viewup": [0.0, 1.0, 0.0],
            "zoom": 1.25,
            "parallel_scale": 4.5,
            "view_angle": 30.0,
            "parallel_projection": False,
        }
        rear = {
            "position": [-3.0, 2.0, 1.0],
            "focal_point": [1.0, 0.0, 0.0],
            "viewup": [0.0, 0.0, 1.0],
            "zoom": 2.0,
            "parallel_scale": 7.5,
            "view_angle": 24.0,
            "parallel_projection": True,
        }
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), -1)
        self.host.camera_state = front
        self.assertTrue(self.bridge.save_viewer_camera_bookmark("node", "Front"))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 0)
        self.host.camera_state = rear
        self.assertTrue(self.bridge.save_viewer_camera_bookmark("node", "Back"))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 1)
        self.assertTrue(self.bridge.rename_viewer_camera_bookmark("node", 1, "Rear"))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 1)
        self.assertTrue(self.bridge.move_viewer_camera_bookmark("node", 1, -1))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 0)
        self.assertEqual(
            [entry["name"] for entry in self.bridge.viewer_camera_bookmarks("node")],
            ["Rear", "Front"],
        )

        self.assertTrue(self.bridge.cycle_viewer_camera_bookmark("node", -1))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 1)
        expected_front = {
            **front,
            "clip_enabled": False,
            "clip_axis": "x",
            "clip_offset": 0.0,
        }
        expected_rear = {
            **rear,
            "clip_enabled": False,
            "clip_axis": "x",
            "clip_offset": 0.0,
        }
        self.assertEqual(self.host.applied[-1], ("node", expected_front))
        self.assertTrue(self.bridge.apply_viewer_camera_bookmark("node", 0))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 0)
        self.assertEqual(self.host.applied[-1], ("node", expected_rear))
        self.assertIs(self.node.properties["parallel_projection"], True)

        self.session.session_id = "replacement-session"
        self.session.sessions_changed.emit()
        self.assertNotIn(("workspace", "node"), self.bridge._bookmark_indices)
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), -1)
        self.assertTrue(self.bridge.cycle_viewer_camera_bookmark("node", -1))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 1)
        self.assertEqual(self.host.applied[-1], ("node", expected_front))

        self.workspace.nodes.clear()
        self.scene.nodes_changed.emit()
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), -1)
        self.assertEqual(self.bridge._bookmark_indices, {})
        self.assertEqual(self.bridge._bookmark_session_ids, {})

    def test_saved_view_current_index_tracks_removal_without_selecting_an_unapplied_view(self) -> None:
        for name, zoom in (("A", 1.0), ("B", 2.0), ("C", 3.0)):
            self.host.camera_state = {"zoom": zoom}
            self.assertTrue(self.bridge.save_viewer_camera_bookmark("node", name))

        self.assertTrue(self.bridge.apply_viewer_camera_bookmark("node", 1))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 1)
        self.assertTrue(self.bridge.remove_viewer_camera_bookmark("node", 0))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 0)
        self.assertTrue(self.bridge.remove_viewer_camera_bookmark("node", 0))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), -1)
        self.assertTrue(self.bridge.cycle_viewer_camera_bookmark("node", 1))
        self.assertEqual(self.bridge.viewer_camera_bookmark_current_index("node"), 0)

    def test_saved_selections_remain_node_scoped(self) -> None:
        self.assertTrue(self.bridge.save_current_viewer_selection("node", "Faces"))
        saved = self.bridge.viewer_saved_selections("node")
        self.assertEqual(
            [entity["entity_id"] for entity in saved["selections"][0]["entities"]],
            ["part:1/face:2", "part:1/face:8"],
        )
        self.assertTrue(self.bridge.rename_viewer_selection("node", 0, "Critical faces"))
        self.assertTrue(self.bridge.publish_viewer_selection("node", 0))
        self.assertEqual(
            self.bridge.viewer_saved_selections("node")["published_name"],
            "Critical faces",
        )
        self.assertTrue(self.bridge.remove_viewer_selection("node", 0))
        self.assertEqual(self.bridge.viewer_saved_selections("node")["selections"], [])

    def test_stale_saved_selection_schema_cannot_break_viewer_controls(self) -> None:
        self.node.properties["saved_selections"] = {
            "schema": "engineering_selection_set.v1",
            "scene_fingerprint": "",
            "published_name": "",
            "selections": [],
        }

        with patch(
            "ea_node_editor.ui_qml.viewer_control_bridge.normalize_engineering_selection_set",
            side_effect=AssertionError("stale schema must be rejected before normalization"),
        ):
            saved = self.bridge.viewer_saved_selections("node")

        self.assertEqual(saved["schema"], "engineering_selection_set.v2")
        self.assertEqual(saved["scene_fingerprint"], "a" * 64)
        self.assertEqual(saved["published_name"], "")
        self.assertEqual(saved["selections"], [])


if __name__ == "__main__":
    unittest.main()
