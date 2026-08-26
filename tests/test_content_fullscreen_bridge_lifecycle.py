from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.project_state import ProjectData
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.nodes.builtins.web_viewer import WEB_PAGE_VIEWER_TYPE_ID
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.plugin_contracts import NodePlugin
from ea_node_editor.ui_qml import content_fullscreen_bridge as bridge_module
from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge


class _FakeSceneBridge(QObject):
    workspace_changed = pyqtSignal(str)
    nodes_changed = pyqtSignal()

    def __init__(self, workspace_id: str) -> None:
        super().__init__()
        self.workspace_id = workspace_id
        self.nodes_model: list[dict[str, object]] = []


class _FakeWorkspaceManager:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id

    def active_workspace_id(self) -> str:
        return self._workspace_id


def _unused_factory() -> NodePlugin:
    raise AssertionError("Lifecycle bridge tests should not instantiate node plugins.")


class ContentFullscreenBridgeLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = WorkspaceData(workspace_id="ws-lifecycle", name="Lifecycle")
        self.project = ProjectData(
            project_id="proj-lifecycle",
            name="Lifecycle",
            active_workspace_id=self.workspace.workspace_id,
            workspaces={self.workspace.workspace_id: self.workspace},
        )
        self.model = GraphModel(self.project)
        self.registry = NodeRegistry()
        self.registry.register_descriptor(
            NodeTypeSpec(
                type_id=WEB_PAGE_VIEWER_TYPE_ID,
                display_name="Web Page Viewer",
                category_path=("Web",),
                icon="globe",
                ports=(),
                properties=(),
                runtime_behavior="passive",
                surface_family="web",
                surface_variant="page_viewer",
            ),
            _unused_factory,
        )
        self.scene = _FakeSceneBridge(self.workspace.workspace_id)
        self.shell = SimpleNamespace(
            model=self.model,
            registry=self.registry,
            workspace_manager=_FakeWorkspaceManager(self.workspace.workspace_id),
        )
        self.bridge = ContentFullscreenBridge(shell_window=self.shell, scene_bridge=self.scene)

    def _add_open_web_node(self) -> str:
        node = self.model.add_node(
            self.workspace.workspace_id,
            WEB_PAGE_VIEWER_TYPE_ID,
            "Web Page Viewer",
            0.0,
            0.0,
            properties={"start_location": "https://example.com"},
        )
        self.assertTrue(self.bridge.request_open_node(node.node_id))
        self.assertTrue(self.bridge.open)
        self.assertEqual(self.bridge.node_id, node.node_id)
        return node.node_id

    def test_workspace_changed_closes_without_error(self) -> None:
        self._add_open_web_node()

        self.scene.workspace_changed.emit("ws-other")

        self.assertFalse(self.bridge.open)
        self.assertEqual(self.bridge.node_id, "")
        self.assertEqual(self.bridge.last_error, "")

    def test_nodes_changed_closes_when_active_node_disappears(self) -> None:
        node_id = self._add_open_web_node()

        self.workspace.nodes.pop(node_id)
        self.scene.nodes_changed.emit()

        self.assertFalse(self.bridge.open)
        self.assertEqual(self.bridge.node_id, "")
        self.assertEqual(self.bridge.last_error, "")

    def test_tabular_provider_and_worker_pool_are_lazy_reused_and_shutdown_safely(self) -> None:
        fake_provider = Mock()
        fake_pool = Mock()
        fake_pool.job_finished = Mock()
        bridge = ContentFullscreenBridge(shell_window=self.shell, scene_bridge=self.scene)

        with (
            patch.object(bridge_module, "TabularPreviewProvider", return_value=fake_provider) as provider_factory,
            patch(
                "ea_node_editor.ui.tabular_preview_async.TabularPreviewWorkerPool",
                return_value=fake_pool,
            ) as pool_factory,
        ):
            self.assertIsNone(bridge._tabular_preview_provider)  # noqa: SLF001
            self.assertIsNone(bridge._tabular_preview_worker_pool)  # noqa: SLF001
            provider_factory.assert_not_called()
            pool_factory.assert_not_called()

            self.assertIs(bridge._ensure_tabular_preview_provider(), fake_provider)  # noqa: SLF001
            self.assertIs(bridge._ensure_tabular_preview_provider(), fake_provider)  # noqa: SLF001
            self.assertIs(bridge._ensure_tabular_preview_worker_pool(), fake_pool)  # noqa: SLF001
            self.assertIs(bridge._ensure_tabular_preview_worker_pool(), fake_pool)  # noqa: SLF001

            provider_factory.assert_called_once_with(project_context_provider=bridge._project_context)  # noqa: SLF001
            pool_factory.assert_called_once_with(bridge)
            fake_pool.job_finished.connect.assert_called_once_with(bridge._on_tabular_preview_job_finished)  # noqa: SLF001
            bridge.shutdown()
            fake_pool.shutdown.assert_called_once_with()

        unopened = ContentFullscreenBridge(shell_window=self.shell, scene_bridge=self.scene)
        unopened.shutdown()
        self.assertIsNone(unopened._tabular_preview_provider)  # noqa: SLF001
        self.assertIsNone(unopened._tabular_preview_worker_pool)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
