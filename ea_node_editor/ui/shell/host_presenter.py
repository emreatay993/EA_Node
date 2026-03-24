from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
import weakref

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog

from ea_node_editor.graph.effective_ports import port_kind
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.telemetry.system_metrics import read_system_metrics
from ea_node_editor.ui.media_preview_provider import set_media_preview_project_context_provider
from ea_node_editor.ui.dialogs.passive_style_controls import (
    normalize_flow_edge_style_payload,
    normalize_passive_node_style_payload,
)
from ea_node_editor.ui.pdf_preview_provider import set_pdf_preview_project_context_provider
from ea_node_editor.ui.graph_theme import resolve_graph_theme_id, serialize_custom_graph_themes
from ea_node_editor.ui.passive_style_presets import normalize_passive_style_presets
from ea_node_editor.ui.shell.controllers.app_preferences_controller import normalize_graph_theme_settings
from ea_node_editor.ui.theme import build_theme_stylesheet

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


_UNSET = object()
_PASSIVE_NODE_STYLE_CLIPBOARD_KIND = "passive-node-style"
_FLOW_EDGE_STYLE_CLIPBOARD_KIND = "flow-edge-style"
_STYLE_CLIPBOARD_APP_PROPERTY = "eaNodeEditorStyleClipboard"
_RENDERER_LABELS = {
    QSGRendererInterface.GraphicsApi.Direct3D11Rhi: "Direct3D 11",
    QSGRendererInterface.GraphicsApi.Direct3D12: "Direct3D 12",
    QSGRendererInterface.GraphicsApi.MetalRhi: "Metal",
    QSGRendererInterface.GraphicsApi.NullRhi: "Null",
    QSGRendererInterface.GraphicsApi.OpenGL: "OpenGL",
    QSGRendererInterface.GraphicsApi.OpenVG: "OpenVG",
    QSGRendererInterface.GraphicsApi.Software: "Software",
    QSGRendererInterface.GraphicsApi.VulkanRhi: "Vulkan",
}


class ShellHostPresenter(QObject):
    def __init__(self, host: "ShellWindow") -> None:
        super().__init__(host)
        self._host = host
        host_ref = weakref.ref(host)

        def _preview_context():
            current_host = host_ref()
            if current_host is None:
                return None
            metadata = current_host.model.project.metadata
            return (
                str(current_host.project_path or "").strip() or None,
                dict(metadata) if isinstance(metadata, dict) else None,
            )

        self._preview_context_provider = _preview_context
        set_media_preview_project_context_provider(self._preview_context_provider)
        set_pdf_preview_project_context_provider(self._preview_context_provider)

    def _project_artifact_resolver(self) -> ProjectArtifactResolver:
        metadata = self._host.model.project.metadata
        return ProjectArtifactResolver(
            project_path=str(self._host.project_path or "").strip() or None,
            project_metadata=dict(metadata) if isinstance(metadata, dict) else None,
        )

    def _path_dialog_start_path(self, current_path: str) -> str:
        normalized_current = str(current_path or "").strip()
        if normalized_current:
            candidate = self._project_artifact_resolver().resolve_to_path(normalized_current)
            if candidate is None:
                candidate = Path(normalized_current).expanduser()
            if candidate.exists():
                return str(candidate)
            parent = candidate.parent
            if str(parent).strip() and parent.exists():
                return str(parent)
        normalized_project_path = str(self._host.project_path or "").strip()
        if normalized_project_path:
            project_path = Path(normalized_project_path).expanduser()
            parent = project_path.parent
            if str(parent).strip() and parent.exists():
                return str(parent)
        return str(Path.cwd())

    def browse_property_path_dialog(self, property_label: str, current_path: str) -> str:
        selected_path, _selected_filter = QFileDialog.getOpenFileName(
            self._host,
            f"Choose {property_label}",
            self._path_dialog_start_path(current_path),
        )
        return str(selected_path or "")

    def apply_graph_cursor(self, cursor_shape: Qt.CursorShape) -> None:
        if getattr(self._host, "quick_widget", None) is None:
            return
        cursor = QCursor(cursor_shape)
        self._host.quick_widget.setCursor(cursor)
        quick_window = self._host.quick_widget.quickWindow()
        if quick_window is not None:
            quick_window.setCursor(cursor)

    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        try:
            resolved_cursor = Qt.CursorShape(int(cursor_shape))
        except ValueError:
            resolved_cursor = Qt.CursorShape.ArrowCursor
        self.apply_graph_cursor(resolved_cursor)

    def clear_graph_cursor_shape(self) -> None:
        if getattr(self._host, "quick_widget", None) is None:
            return
        self._host.quick_widget.unsetCursor()
        quick_window = self._host.quick_widget.quickWindow()
        if quick_window is not None:
            quick_window.unsetCursor()

    def apply_theme(self, theme_id: Any) -> str:
        resolved_theme_id = self._host.theme_bridge.apply_theme(theme_id)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_theme_stylesheet(resolved_theme_id))
        return resolved_theme_id

    def preview_graph_theme_settings(self, graph_theme_settings: Any) -> str:
        normalized = normalize_graph_theme_settings(graph_theme_settings)
        return self._host.graph_theme_bridge.apply_settings(
            shell_theme_id=self._host.active_theme_id,
            graph_theme_settings=normalized,
        )

    def active_renderer_label(self) -> str:
        api = QSGRendererInterface.GraphicsApi.Unknown
        quick_widget = getattr(self._host, "quick_widget", None)
        if quick_widget is not None:
            quick_window = quick_widget.quickWindow()
            if quick_window is not None:
                renderer_interface = quick_window.rendererInterface()
                if renderer_interface is not None:
                    api = renderer_interface.graphicsApi()
        if api == QSGRendererInterface.GraphicsApi.Unknown:
            api = QQuickWindow.graphicsApi()
        return _RENDERER_LABELS.get(api, "Unavailable")

    def show_graphics_settings_dialog(self, _checked: bool = False) -> None:
        from ea_node_editor.ui.dialogs import GraphicsSettingsDialog

        dialog = GraphicsSettingsDialog(
            initial_settings=self._host.app_preferences_controller.graphics_settings(),
            available_graph_themes=self._host.app_preferences_controller.graph_theme_choices(),
            manage_graph_themes_callback=self.edit_graph_theme_settings,
            active_renderer_label=self.active_renderer_label(),
            parent=self._host,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self._host.app_preferences_controller.set_graphics_settings(dialog.values(), host=self._host)

    def edit_graph_theme_settings(
        self,
        graph_theme_settings: Any,
        *,
        enable_live_apply: bool = False,
    ) -> dict[str, Any] | None:
        from ea_node_editor.ui.dialogs import GraphThemeEditorDialog

        dialog = GraphThemeEditorDialog(
            initial_settings=graph_theme_settings,
            parent=self._host,
            live_apply_callback=self.preview_graph_theme_settings if enable_live_apply else None,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog.graph_theme_settings()

    def show_graph_theme_editor_dialog(self, _checked: bool = False) -> None:
        graph_theme_settings = self.edit_graph_theme_settings(
            self._host.app_preferences_controller.graph_theme_settings(),
            enable_live_apply=True,
        )
        if graph_theme_settings is None:
            return
        graphics = self._host.app_preferences_controller.graphics_settings()
        graphics["graph_theme"] = graph_theme_settings
        self._host.app_preferences_controller.set_graphics_settings(graphics, host=self._host)

    def _active_workspace_data(self):
        workspace_id = self._host.workspace_manager.active_workspace_id()
        return self._host.model.project.workspaces.get(workspace_id)

    def _passive_node_context(self, node_id: str):
        workspace = self._active_workspace_data()
        if workspace is None:
            return None
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return None
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return None
        spec = self._host.registry.get_spec(node.type_id)
        if str(spec.runtime_behavior or "").strip().lower() != "passive":
            return None
        return node, spec, workspace

    def _flow_edge_context(self, edge_id: str):
        workspace = self._active_workspace_data()
        if workspace is None:
            return None
        normalized_edge_id = str(edge_id).strip()
        if not normalized_edge_id:
            return None
        edge = workspace.edges.get(normalized_edge_id)
        if edge is None:
            return None
        source_node = workspace.nodes.get(edge.source_node_id)
        target_node = workspace.nodes.get(edge.target_node_id)
        if source_node is None or target_node is None:
            return None
        source_spec = self._host.registry.get_spec(source_node.type_id)
        target_spec = self._host.registry.get_spec(target_node.type_id)
        try:
            source_kind = port_kind(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace.nodes,
                port_key=edge.source_port_key,
            )
            target_kind = port_kind(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace.nodes,
                port_key=edge.target_port_key,
            )
        except KeyError:
            return None
        if source_kind != "flow" or target_kind != "flow":
            return None
        return edge, workspace

    def _project_passive_style_presets(self) -> dict[str, list[dict[str, Any]]]:
        self._host.project_session_controller.ensure_project_metadata_defaults()
        metadata = self._host.model.project.metadata if isinstance(self._host.model.project.metadata, dict) else {}
        ui = metadata.get("ui", {}) if isinstance(metadata.get("ui"), dict) else {}
        normalized = normalize_passive_style_presets(ui.get("passive_style_presets"))
        if ui.get("passive_style_presets") != normalized:
            updated_ui = dict(ui)
            updated_ui["passive_style_presets"] = normalized
            updated_metadata = dict(metadata)
            updated_metadata["ui"] = updated_ui
            self._host.model.project.metadata = updated_metadata
        return normalize_passive_style_presets(normalized)

    def _set_project_passive_style_presets(
        self,
        *,
        node_presets: Any = _UNSET,
        edge_presets: Any = _UNSET,
    ) -> None:
        current = self._project_passive_style_presets()
        updated = {
            "node_presets": current["node_presets"],
            "edge_presets": current["edge_presets"],
        }
        if node_presets is not _UNSET:
            updated["node_presets"] = normalize_passive_style_presets(
                {"node_presets": node_presets, "edge_presets": current["edge_presets"]}
            )["node_presets"]
        if edge_presets is not _UNSET:
            updated["edge_presets"] = normalize_passive_style_presets(
                {"node_presets": updated["node_presets"], "edge_presets": edge_presets}
            )["edge_presets"]
        if updated == current:
            return
        metadata = self._host.model.project.metadata if isinstance(self._host.model.project.metadata, dict) else {}
        ui = metadata.get("ui", {}) if isinstance(metadata.get("ui"), dict) else {}
        updated_ui = dict(ui)
        updated_ui["passive_style_presets"] = updated
        updated_metadata = dict(metadata)
        updated_metadata["ui"] = updated_ui
        self._host.model.project.metadata = updated_metadata
        self._host.project_session_controller.persist_session()
        self._host.project_meta_changed.emit()

    def edit_passive_node_style(self, node_id: str) -> dict[str, Any] | None:
        context = self._passive_node_context(node_id)
        if context is None:
            return None
        node, _spec, _workspace = context
        from ea_node_editor.ui.dialogs import PassiveNodeStyleDialog

        user_presets = self._project_passive_style_presets()["node_presets"]
        dialog = PassiveNodeStyleDialog(
            initial_style=node.visual_style,
            parent=self._host,
            user_presets=user_presets,
        )
        result = dialog.exec()
        updated_user_presets = dialog.user_presets()
        if updated_user_presets != user_presets:
            self._set_project_passive_style_presets(node_presets=updated_user_presets)
        if result != dialog.DialogCode.Accepted:
            return None
        return dialog.node_style()

    def edit_flow_edge_style(self, edge_id: str) -> dict[str, Any] | None:
        context = self._flow_edge_context(edge_id)
        if context is None:
            return None
        edge, _workspace = context
        from ea_node_editor.ui.dialogs import FlowEdgeStyleDialog

        user_presets = self._project_passive_style_presets()["edge_presets"]
        dialog = FlowEdgeStyleDialog(
            initial_style=edge.visual_style,
            parent=self._host,
            user_presets=user_presets,
        )
        result = dialog.exec()
        updated_user_presets = dialog.user_presets()
        if updated_user_presets != user_presets:
            self._set_project_passive_style_presets(edge_presets=updated_user_presets)
        if result != dialog.DialogCode.Accepted:
            return None
        return dialog.edge_style()

    def _write_style_clipboard(self, *, kind: str, style: dict[str, Any]) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setProperty(
            f"{_STYLE_CLIPBOARD_APP_PROPERTY}:{str(kind).strip()}",
            json.dumps(
                {
                    "kind": str(kind),
                    "version": 1,
                    "style": copy.deepcopy(style),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )

    def _read_style_clipboard(self, *, kind: str) -> dict[str, Any] | None:
        app = QApplication.instance()
        if app is None:
            return None
        return self._normalize_style_clipboard_payload(
            app.property(f"{_STYLE_CLIPBOARD_APP_PROPERTY}:{str(kind).strip()}"),
            kind=kind,
        )

    def _normalize_style_clipboard_payload(self, payload: Any, *, kind: str) -> dict[str, Any] | None:
        if isinstance(payload, str):
            raw_text = payload.strip()
            if not raw_text:
                return None
            try:
                payload = json.loads(raw_text)
            except ValueError:
                return None
        if not isinstance(payload, dict) or str(payload.get("kind", "")).strip() != str(kind):
            return None
        style = payload.get("style")
        if kind == _PASSIVE_NODE_STYLE_CLIPBOARD_KIND:
            return normalize_passive_node_style_payload(style)
        if kind == _FLOW_EDGE_STYLE_CLIPBOARD_KIND:
            return normalize_flow_edge_style_payload(style)
        return None

    def request_edit_passive_node_style(self, node_id: str) -> bool:
        style = self._host.edit_passive_node_style(node_id)
        if style is None:
            return False
        self._host.scene.set_node_visual_style(node_id, style)
        return True

    def request_reset_passive_node_style(self, node_id: str) -> bool:
        if self._passive_node_context(node_id) is None:
            return False
        self._host.scene.clear_node_visual_style(node_id)
        return True

    def request_copy_passive_node_style(self, node_id: str) -> bool:
        context = self._passive_node_context(node_id)
        if context is None:
            return False
        node, _spec, _workspace = context
        self._write_style_clipboard(
            kind=_PASSIVE_NODE_STYLE_CLIPBOARD_KIND,
            style=normalize_passive_node_style_payload(node.visual_style),
        )
        return True

    def request_paste_passive_node_style(self, node_id: str) -> bool:
        if self._passive_node_context(node_id) is None:
            return False
        style = self._read_style_clipboard(kind=_PASSIVE_NODE_STYLE_CLIPBOARD_KIND)
        if style is None:
            return False
        self._host.scene.set_node_visual_style(node_id, style)
        return True

    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        style = self._host.edit_flow_edge_style(edge_id)
        if style is None:
            return False
        self._host.scene.set_edge_visual_style(edge_id, style)
        return True

    def request_edit_flow_edge_label(self, edge_id: str) -> bool:
        context = self._flow_edge_context(edge_id)
        if context is None:
            return False
        edge, _workspace = context
        label, accepted = QInputDialog.getText(
            self._host,
            "Edit Flow Edge Label",
            "Label:",
            text=str(edge.label or ""),
        )
        if not accepted:
            return False
        self._host.scene.set_edge_label(edge_id, label)
        return True

    def request_reset_flow_edge_style(self, edge_id: str) -> bool:
        if self._flow_edge_context(edge_id) is None:
            return False
        self._host.scene.clear_edge_visual_style(edge_id)
        return True

    def request_copy_flow_edge_style(self, edge_id: str) -> bool:
        context = self._flow_edge_context(edge_id)
        if context is None:
            return False
        edge, _workspace = context
        self._write_style_clipboard(
            kind=_FLOW_EDGE_STYLE_CLIPBOARD_KIND,
            style=normalize_flow_edge_style_payload(edge.visual_style),
        )
        return True

    def request_paste_flow_edge_style(self, edge_id: str) -> bool:
        if self._flow_edge_context(edge_id) is None:
            return False
        style = self._read_style_clipboard(kind=_FLOW_EDGE_STYLE_CLIPBOARD_KIND)
        if style is None:
            return False
        self._host.scene.set_edge_visual_style(edge_id, style)
        return True

    def update_metrics(self) -> None:
        metrics = read_system_metrics()
        self.update_system_metrics(metrics.cpu_percent, metrics.ram_used_gb, metrics.ram_total_gb)

    def update_engine_status(
        self,
        state: Literal["ready", "running", "paused", "error"],
        details: str = "",
    ) -> None:
        text = state.capitalize()
        if details:
            text = f"{text} ({details})"
        icon_map = {
            "ready": "R",
            "running": "Run",
            "paused": "P",
            "error": "!",
        }
        self._host.status_engine.set_icon(icon_map.get(state, "E"))
        self._host.status_engine.set_text(text)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self._host.status_jobs.set_text(f"R:{running} Q:{queued} D:{done} F:{failed}")

    def update_system_metrics(
        self,
        cpu_percent: float,
        ram_used_gb: float,
        ram_total_gb: float,
        fps: float | None = None,
    ) -> None:
        fps_value = max(0.0, float(fps)) if fps is not None else self._host._frame_rate_sampler.snapshot().fps
        self._host.status_metrics.set_text(
            f"FPS:{fps_value:.0f} CPU:{cpu_percent:.0f}% RAM:{ram_used_gb:.1f}/{ram_total_gb:.1f} GB"
        )

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self._host.status_notifications.set_text(f"W:{warnings} E:{errors}")
