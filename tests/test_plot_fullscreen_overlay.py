from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.addons.property_edit_adapters import PropertyEditAdapterContext
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.plot.property_edit_adapter import PlotPropertyEditAdapter
from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge
from ea_node_editor.ui_qml.graph_scene_payload import GraphScenePayloadBuilder


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


class _FakeSelectionScene:
    def __init__(self, node_id: str) -> None:
        self._node_id = node_id

    def selected_node_id(self) -> str:
        return self._node_id


class _FakePlotShell:
    project_path = ""

    def __init__(self, *, model: GraphModel, registry, workspace_id: str, node_id: str) -> None:  # noqa: ANN001
        self.model = model
        self.registry = registry
        self.workspace_manager = _FakeWorkspaceManager(workspace_id)
        self.scene = _FakeSelectionScene(node_id)
        self.property_calls: list[tuple[str, object]] = []

    def set_selected_node_property(self, key: str, value: object) -> None:
        self.property_calls.append((key, value))
        workspace = self.model.project.workspaces[self.workspace_manager.active_workspace_id()]
        node = workspace.nodes[self.scene.selected_node_id()]
        spec = self.registry.get_spec(node.type_id)
        rewrite = PlotPropertyEditAdapter().rewrite_property_edit(
            PropertyEditAdapterContext(
                node=node,
                spec=spec,
                workspace_nodes=workspace.nodes,
                workspace_edges=workspace.edges,
            ),
            key=key,
            value=value,
        )
        if rewrite is not None:
            node.properties[rewrite.key] = rewrite.value


def _bridge_with_plot_node(*, render_in_canvas: bool = False) -> tuple[ContentFullscreenBridge, str]:
    model = GraphModel()
    registry = build_default_registry()
    workspace_id = model.active_workspace.workspace_id
    node = model.add_node(
        workspace_id,
        "plot.scatter",
        "Line Plot",
        0.0,
        0.0,
        properties={"render_in_canvas": render_in_canvas},
    )
    scene = _FakeSceneBridge(workspace_id)
    nodes_payload, _minimap_payload, _edges_payload = GraphScenePayloadBuilder().rebuild_models(
        model=model,
        registry=registry,
        workspace_id=workspace_id,
        scope_path=(),
        graph_theme_bridge=None,
    )
    scene.nodes_model = nodes_payload
    shell = _FakePlotShell(model=model, registry=registry, workspace_id=workspace_id, node_id=node.node_id)
    return ContentFullscreenBridge(shell_window=shell, scene_bridge=scene), node.node_id


def test_plot_fullscreen_bridge_opens_plot_payload_even_when_embedded_is_suppressed() -> None:
    bridge, node_id = _bridge_with_plot_node(render_in_canvas=False)

    assert bridge.request_open_node(node_id) is True

    assert bridge.open is True
    assert bridge.content_kind == "plot"
    assert bridge.node_id == node_id
    plot_payload = bridge.plot_payload
    assert plot_payload["content_kind"] == "plot"
    assert plot_payload["surface_family"] == "plot"
    assert plot_payload["surface_variant"] == "line"
    assert plot_payload["surface_spec"]["fullscreen"]["content_kind"] == "plot"
    assert plot_payload["surface_spec"]["native_overlay"]["required"] is True
    assert plot_payload["plot_surface"] == {
        "plot_type": "line",
        "live_backend_id": "pyqtgraph",
        "render_in_canvas": False,
        "lightweight_canvas": False,
        "embedded_rendering_suppressed": True,
        "embedded_rendering_suppressed_by": ["render_in_canvas"],
    }


def test_plot_fullscreen_payload_refreshes_from_scene_node_payload() -> None:
    bridge, node_id = _bridge_with_plot_node(render_in_canvas=True)

    assert bridge.request_open_node(node_id) is True

    assert bridge.content_kind == "plot"
    assert bridge.plot_payload["plot_surface"]["embedded_rendering_suppressed"] is False
    assert bridge.can_open_node(node_id) is True
    bridge.request_close()
    assert bridge.open is False
    assert bridge.plot_payload == {}


def test_plot_fullscreen_bridge_updates_active_plot_options_through_selected_property_path() -> None:
    bridge, node_id = _bridge_with_plot_node(render_in_canvas=True)

    assert bridge.request_open_node(node_id) is True
    assert bridge.set_active_plot_option("crosshair", True) is True
    assert bridge.set_active_plot_option("plot_theme", "dark") is True

    shell = bridge.shell_window
    assert shell is not None
    assert shell.property_calls == [("plot_option_crosshair", True), ("plot_option_plot_theme", "dark")]
    workspace = shell.model.project.workspaces[shell.workspace_manager.active_workspace_id()]
    assert workspace.nodes[node_id].properties["plot_options"]["crosshair"] is True
    assert workspace.nodes[node_id].properties["plot_options"]["plot_theme"] == "dark"
    assert bridge.plot_payload["properties"]["plot_options"]["crosshair"] is True
    assert bridge.plot_payload["properties"]["plot_options"]["plot_theme"] == "dark"


def test_content_fullscreen_overlay_uses_opaque_scrim() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "ea_node_editor"
        / "ui_qml"
        / "ContentFullscreenOverlay.qml"
    ).read_text(encoding="utf-8")

    assert "color: root.themePalette.app_bg" in source
    assert "Qt.alpha(root.themePalette.app_bg, 0.97)" not in source


def test_content_fullscreen_overlay_exposes_plot_investigation_controls() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "ea_node_editor"
        / "ui_qml"
        / "ContentFullscreenOverlay.qml"
    ).read_text(encoding="utf-8")

    assert 'objectName: "contentFullscreenPlotQuickControls"' in source
    assert 'objectName: "contentFullscreenPlotHoverReadoutButton"' in source
    assert 'objectName: "contentFullscreenPlotVerticalGuideButton"' in source
    assert 'objectName: "contentFullscreenPlotCrosshairButton"' in source
    assert 'objectName: "contentFullscreenPlotThemeCombo"' in source
    assert 'root._setPlotOption("hover_readout"' in source
    assert 'root._setPlotOption("vertical_guide"' in source
    assert 'root._setPlotOption("crosshair"' in source
    assert 'root._setPlotOption("plot_theme"' in source
