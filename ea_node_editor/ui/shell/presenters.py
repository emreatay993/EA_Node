from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.app_preferences import normalize_graphics_performance_mode
from ea_node_editor.graph.effective_ports import find_port
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.graph_theme import (
    resolve_graph_theme_id,
    serialize_custom_graph_themes,
)
from ea_node_editor.ui.shell.controllers.app_preferences_controller import normalize_graph_theme_settings
from ea_node_editor.ui.shell.window_library_inspector import (
    build_canvas_quick_insert_items,
    build_combined_library_items,
    build_connection_quick_insert_items,
    build_filtered_library_items,
    build_grouped_library_items,
    build_library_category_options,
    build_library_data_type_options,
    build_library_direction_options,
    build_pin_data_type_options,
    build_registry_library_items,
    build_selected_node_header_data,
    build_selected_node_port_items,
    build_selected_node_property_items,
    library_item_matches_filters,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


_UNSET = object()


@dataclass(slots=True)
class ShellWorkspaceUiState:
    show_grid: bool
    show_minimap: bool
    node_shadow: bool
    shadow_strength: int
    shadow_softness: int
    shadow_offset: int
    graphics_performance_mode: str
    tab_strip_density: str
    active_theme_id: str


def build_default_shell_workspace_ui_state(
    graphics_settings: Any = DEFAULT_GRAPHICS_SETTINGS,
) -> ShellWorkspaceUiState:
    canvas = graphics_settings.get("canvas", {}) if isinstance(graphics_settings, dict) else {}
    shell = graphics_settings.get("shell", {}) if isinstance(graphics_settings, dict) else {}
    performance = graphics_settings.get("performance", {}) if isinstance(graphics_settings, dict) else {}
    theme = graphics_settings.get("theme", {}) if isinstance(graphics_settings, dict) else {}
    return ShellWorkspaceUiState(
        show_grid=bool(canvas.get("show_grid", DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_grid"])),
        show_minimap=bool(canvas.get("show_minimap", DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_minimap"])),
        node_shadow=bool(canvas.get("node_shadow", DEFAULT_GRAPHICS_SETTINGS["canvas"]["node_shadow"])),
        shadow_strength=int(canvas.get("shadow_strength", DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_strength"])),
        shadow_softness=int(canvas.get("shadow_softness", DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_softness"])),
        shadow_offset=int(canvas.get("shadow_offset", DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_offset"])),
        graphics_performance_mode=normalize_graphics_performance_mode(
            performance.get("mode", DEFAULT_GRAPHICS_SETTINGS["performance"]["mode"])
        ),
        tab_strip_density=str(
            shell.get("tab_strip_density", DEFAULT_GRAPHICS_SETTINGS["shell"]["tab_strip_density"])
        ),
        active_theme_id=str(theme.get("theme_id", DEFAULT_GRAPHICS_SETTINGS["theme"]["theme_id"])),
    )


class ShellLibraryPresenter(QObject):
    node_library_changed = pyqtSignal()
    library_pane_reset_requested = pyqtSignal(name="libraryPaneResetRequested")
    graph_search_changed = pyqtSignal()
    connection_quick_insert_changed = pyqtSignal()
    graph_hint_changed = pyqtSignal()

    def __init__(self, host: "ShellWindow") -> None:
        super().__init__(host)
        self._host = host
        host.node_library_changed.connect(self.node_library_changed.emit)
        host.library_pane_reset_requested.connect(self.library_pane_reset_requested.emit)
        host.graph_search_changed.connect(self.graph_search_changed.emit)
        host.connection_quick_insert_changed.connect(self.connection_quick_insert_changed.emit)
        host.graph_hint_changed.connect(self.graph_hint_changed.emit)

    def _registry_library_items(self) -> list[dict[str, Any]]:
        return build_registry_library_items(registry_specs=self._host.registry.all_specs())

    def _combined_library_items(self) -> list[dict[str, Any]]:
        return build_combined_library_items(
            registry_items=self._registry_library_items(),
            custom_workflow_items=self._host.workspace_library_controller.custom_workflow_library_items(),
        )

    @staticmethod
    def _library_item_matches_filters(
        item: dict[str, Any],
        *,
        query: str,
        category: str,
        data_type: str,
        direction: str,
    ) -> bool:
        return library_item_matches_filters(
            item,
            query=query,
            category=category,
            data_type=data_type,
            direction=direction,
        )

    @property
    def filtered_node_library_items(self) -> list[dict[str, Any]]:
        return build_filtered_library_items(
            combined_items=self._combined_library_items(),
            query=self._host.library_filter_state.library_query,
            category=self._host.library_filter_state.library_category,
            data_type=self._host.library_filter_state.library_data_type,
            direction=self._host.library_filter_state.library_direction,
        )

    @property
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        return build_grouped_library_items(filtered_items=self.filtered_node_library_items)

    @property
    def library_category_options(self) -> list[dict[str, str]]:
        return build_library_category_options(
            combined_items=self._combined_library_items(),
            registry_categories=self._host.registry.categories(),
        )

    @property
    def library_direction_options(self) -> list[dict[str, str]]:
        return build_library_direction_options()

    @property
    def library_data_type_options(self) -> list[dict[str, str]]:
        return build_library_data_type_options(
            registry_specs=self._host.registry.all_specs(),
            custom_workflow_items=self._host.workspace_library_controller.custom_workflow_library_items(),
        )

    @property
    def graph_search_open(self) -> bool:
        return bool(self._host.search_scope_state.graph_search.open)

    @property
    def graph_search_query(self) -> str:
        return self._host.search_scope_state.graph_search.query

    @property
    def graph_search_results(self) -> list[dict[str, Any]]:
        return list(self._host.search_scope_state.graph_search.results)

    @property
    def graph_search_highlight_index(self) -> int:
        return int(self._host.search_scope_state.graph_search.highlight_index)

    @property
    def connection_quick_insert_open(self) -> bool:
        return bool(self._host.search_scope_state.connection_quick_insert.open)

    @property
    def connection_quick_insert_query(self) -> str:
        return str(self._host.search_scope_state.connection_quick_insert.query)

    @property
    def connection_quick_insert_results(self) -> list[dict[str, Any]]:
        return list(self._host.search_scope_state.connection_quick_insert.results)

    @property
    def connection_quick_insert_highlight_index(self) -> int:
        return int(self._host.search_scope_state.connection_quick_insert.highlight_index)

    @property
    def connection_quick_insert_overlay_x(self) -> float:
        context = self._host.search_scope_state.connection_quick_insert.context or {}
        return float(context.get("overlay_x", 0.0))

    @property
    def connection_quick_insert_overlay_y(self) -> float:
        context = self._host.search_scope_state.connection_quick_insert.context or {}
        return float(context.get("overlay_y", 0.0))

    @property
    def connection_quick_insert_source_summary(self) -> str:
        context = self._host.search_scope_state.connection_quick_insert.context or {}
        node_title = str(context.get("node_title", "")).strip()
        port_label = str(context.get("port_label", "")).strip()
        data_type = str(context.get("data_type", "")).strip()
        if not node_title and not port_label:
            return ""
        summary = f"{node_title}.{port_label}" if node_title and port_label else (node_title or port_label)
        if data_type:
            summary += f" [{data_type}]"
        return summary

    @property
    def connection_quick_insert_is_canvas_mode(self) -> bool:
        context = self._host.search_scope_state.connection_quick_insert.context or {}
        return str(context.get("mode", "")).strip() == "canvas_insert"

    @property
    def graph_hint_message(self) -> str:
        return str(self._host.search_scope_state.graph_hint_message)

    @property
    def graph_hint_visible(self) -> bool:
        return bool(self._host.search_scope_state.graph_hint_message.strip())

    @property
    def can_publish_custom_workflow_from_scope(self) -> bool:
        return bool(self._host.scene.active_scope_path)

    def set_library_query(self, query: str) -> None:
        normalized = str(query).strip()
        if normalized == self._host.library_filter_state.library_query:
            return
        self._host.library_filter_state.library_query = normalized
        self._host.node_library_changed.emit()

    def set_library_category(self, category: str) -> None:
        normalized = str(category).strip()
        if normalized == self._host.library_filter_state.library_category:
            return
        self._host.library_filter_state.library_category = normalized
        self._host.node_library_changed.emit()

    def set_library_data_type(self, data_type: str) -> None:
        normalized = str(data_type).strip()
        if normalized == self._host.library_filter_state.library_data_type:
            return
        self._host.library_filter_state.library_data_type = normalized
        self._host.node_library_changed.emit()

    def set_library_direction(self, direction: str) -> None:
        normalized = str(direction).strip().lower()
        if normalized not in {"", "in", "out"}:
            normalized = ""
        if normalized == self._host.library_filter_state.library_direction:
            return
        self._host.library_filter_state.library_direction = normalized
        self._host.node_library_changed.emit()

    def _set_graph_search_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
    ) -> None:
        self._host.search_scope_controller.set_graph_search_state(
            open_=open_,
            query=query,
            results=results,
            highlight_index=highlight_index,
        )

    def _refresh_graph_search_results(self, query: str) -> None:
        self._host.search_scope_controller.refresh_graph_search_results(query)

    def _set_connection_quick_insert_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
        context: dict[str, Any] | None | object = _UNSET,
    ) -> None:
        quick_insert = self._host.search_scope_state.connection_quick_insert
        changed = False
        if open_ is not None:
            normalized_open = bool(open_)
            if normalized_open != quick_insert.open:
                quick_insert.open = normalized_open
                changed = True
        if query is not None:
            normalized_query = str(query)
            if normalized_query != quick_insert.query:
                quick_insert.query = normalized_query
                changed = True
        if results is not None:
            normalized_results = list(results)
            if normalized_results != quick_insert.results:
                quick_insert.results = normalized_results
                changed = True
        if highlight_index is not None:
            normalized_index = int(highlight_index)
            if normalized_index != quick_insert.highlight_index:
                quick_insert.highlight_index = normalized_index
                changed = True
        if context is not _UNSET:
            normalized_context = dict(context) if isinstance(context, dict) else None
            if normalized_context != quick_insert.context:
                quick_insert.context = normalized_context
                changed = True
        if changed:
            self._host.connection_quick_insert_changed.emit()

    def _connection_quick_insert_context_for_port(
        self,
        node_id: str,
        port_key: str,
    ) -> dict[str, Any] | None:
        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return None
        normalized_node_id = str(node_id).strip()
        normalized_port_key = str(port_key).strip()
        if not normalized_node_id or not normalized_port_key:
            return None
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return None
        spec = self._host.registry.get_spec(node.type_id)
        port = find_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=normalized_port_key,
        )
        if port is None or not bool(port.exposed):
            return None
        connection_count = 0
        for edge in workspace.edges.values():
            if edge.source_node_id == normalized_node_id and edge.source_port_key == normalized_port_key:
                connection_count += 1
            if edge.target_node_id == normalized_node_id and edge.target_port_key == normalized_port_key:
                connection_count += 1
        return {
            "node_id": normalized_node_id,
            "node_title": str(node.title),
            "type_id": str(node.type_id),
            "port_key": normalized_port_key,
            "port_label": str(port.label or port.key),
            "direction": str(port.direction),
            "kind": str(port.kind),
            "data_type": str(port.data_type),
            "connection_count": int(connection_count),
        }

    def _refresh_connection_quick_insert_results(self, query: str) -> None:
        quick_insert = self._host.search_scope_state.connection_quick_insert
        context = quick_insert.context
        if context is None:
            self._set_connection_quick_insert_state(query=str(query), results=[], highlight_index=-1)
            return
        normalized_query = str(query)
        results: list[dict[str, Any]] = []
        if str(context.get("mode", "")).strip() == "canvas_insert":
            results = build_canvas_quick_insert_items(
                combined_items=self._combined_library_items(),
                query=normalized_query,
                limit=self._host._CONNECTION_QUICK_INSERT_LIMIT,
            )
        elif not (
            str(context.get("direction", "")).strip().lower() == "in"
            and int(context.get("connection_count", 0)) > 0
        ):
            results = build_connection_quick_insert_items(
                combined_items=self._combined_library_items(),
                query=normalized_query,
                source_direction=str(context.get("direction", "")),
                source_kind=str(context.get("kind", "")),
                source_data_type=str(context.get("data_type", "")),
                limit=self._host._CONNECTION_QUICK_INSERT_LIMIT,
            )
        highlight_index = 0 if results else -1
        if 0 <= quick_insert.highlight_index < len(results):
            highlight_index = quick_insert.highlight_index
        self._set_connection_quick_insert_state(
            query=normalized_query,
            results=results,
            highlight_index=highlight_index,
        )

    def request_open_graph_search(self) -> None:
        self._set_connection_quick_insert_state(
            open_=False,
            query="",
            results=[],
            highlight_index=-1,
            context=None,
        )
        self._set_graph_search_state(open_=True, query="", results=[], highlight_index=-1)

    def request_close_graph_search(self) -> None:
        self._set_graph_search_state(open_=False, query="", results=[], highlight_index=-1)

    def set_graph_search_query(self, query: str) -> None:
        if not self.graph_search_open:
            return
        self._refresh_graph_search_results(query)

    def request_graph_search_move(self, delta: int) -> None:
        self._host.search_scope_controller.request_graph_search_move(delta)

    def request_graph_search_highlight(self, index: int) -> None:
        self._host.search_scope_controller.request_graph_search_highlight(index)

    def request_graph_search_accept(self) -> bool:
        return bool(self._host.search_scope_controller.request_graph_search_accept())

    def request_graph_search_jump(self, index: int) -> bool:
        return bool(self._host.search_scope_controller.request_graph_search_jump(index))

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool:
        context = self._connection_quick_insert_context_for_port(node_id, port_key)
        if context is None:
            return False
        context["scene_x"] = float(scene_x)
        context["scene_y"] = float(scene_y)
        context["overlay_x"] = float(overlay_x)
        context["overlay_y"] = float(overlay_y)
        self._set_graph_search_state(open_=False, query="", results=[], highlight_index=-1)
        self._set_connection_quick_insert_state(
            open_=True,
            query="",
            results=[],
            highlight_index=-1,
            context=context,
        )
        self._refresh_connection_quick_insert_results("")
        if self.connection_quick_insert_results:
            return True
        message = (
            "This input is already connected."
            if str(context.get("direction", "")).strip().lower() == "in"
            and int(context.get("connection_count", 0)) > 0
            else "No compatible nodes found for quick insert."
        )
        self.show_graph_hint(message, 2200)
        self.request_close_connection_quick_insert()
        return False

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        context: dict[str, Any] = {
            "mode": "canvas_insert",
            "scene_x": float(scene_x),
            "scene_y": float(scene_y),
            "overlay_x": float(overlay_x),
            "overlay_y": float(overlay_y),
        }
        self._set_graph_search_state(open_=False, query="", results=[], highlight_index=-1)
        self._set_connection_quick_insert_state(
            open_=True,
            query="",
            results=[],
            highlight_index=-1,
            context=context,
        )
        self._refresh_connection_quick_insert_results("")

    def request_close_connection_quick_insert(self) -> None:
        self._set_connection_quick_insert_state(
            open_=False,
            query="",
            results=[],
            highlight_index=-1,
            context=None,
        )

    def set_connection_quick_insert_query(self, query: str) -> None:
        if not self.connection_quick_insert_open:
            return
        self._refresh_connection_quick_insert_results(query)

    def request_connection_quick_insert_move(self, delta: int) -> None:
        quick_insert = self._host.search_scope_state.connection_quick_insert
        if not quick_insert.open or not quick_insert.results:
            return
        current = quick_insert.highlight_index
        if current < 0:
            current = 0
        next_index = max(0, min(len(quick_insert.results) - 1, current + int(delta)))
        self._set_connection_quick_insert_state(highlight_index=next_index)

    def request_connection_quick_insert_highlight(self, index: int) -> None:
        quick_insert = self._host.search_scope_state.connection_quick_insert
        if not quick_insert.open:
            return
        if index < 0 or index >= len(quick_insert.results):
            return
        self._set_connection_quick_insert_state(highlight_index=int(index))

    def request_connection_quick_insert_accept(self) -> bool:
        quick_insert = self._host.search_scope_state.connection_quick_insert
        if not quick_insert.open or not quick_insert.results:
            return False
        index = quick_insert.highlight_index
        if index < 0 or index >= len(quick_insert.results):
            index = 0
        return self.request_connection_quick_insert_choose(index)

    def request_connection_quick_insert_choose(self, index: int) -> bool:
        quick_insert = self._host.search_scope_state.connection_quick_insert
        if index < 0 or index >= len(quick_insert.results):
            return False
        context = quick_insert.context
        if context is None:
            return False
        selected_item = quick_insert.results[index]
        scene_x = float(context.get("scene_x", 0.0))
        scene_y = float(context.get("scene_y", 0.0))
        if str(context.get("mode", "")).strip() == "canvas_insert":
            created = self._host.workspace_library_controller.request_drop_node_from_library(
                str(selected_item.get("type_id", "")),
                scene_x,
                scene_y,
                "",
                "",
                "",
                "",
            ).payload
        else:
            offset = self._host._CONNECTION_QUICK_INSERT_OFFSET
            if str(context.get("direction", "")).strip().lower() == "in":
                scene_x -= offset
            else:
                scene_x += offset
            created = self._host.workspace_library_controller.request_drop_node_from_library(
                str(selected_item.get("type_id", "")),
                scene_x,
                scene_y,
                "port",
                str(context.get("node_id", "")),
                str(context.get("port_key", "")),
                "",
            ).payload
        self.request_close_connection_quick_insert()
        return bool(created)

    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
        self._host.search_scope_controller.show_graph_hint(message, timeout_ms)

    def clear_graph_hint(self) -> None:
        self._host.search_scope_controller.clear_graph_hint()

    def request_add_node_from_library(self, type_id: str) -> None:
        self._host.workspace_library_controller.add_node_from_library(type_id)

    def request_publish_custom_workflow_from_selected(self) -> bool:
        result = self._host.workspace_library_controller.publish_custom_workflow_from_selected_subnode()
        return bool(result.payload)

    def request_publish_custom_workflow_from_scope(self) -> bool:
        result = self._host.workspace_library_controller.publish_custom_workflow_from_current_scope()
        return bool(result.payload)

    def request_publish_custom_workflow_from_node(self, node_id: str) -> bool:
        result = self._host.workspace_library_controller.publish_custom_workflow_from_node(node_id)
        return bool(result.payload)

    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        result = self._host.workspace_library_controller.delete_custom_workflow(workflow_id, workflow_scope)
        return bool(result.payload)

    def request_rename_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        result = self._host.workspace_library_controller.rename_custom_workflow(workflow_id, workflow_scope)
        return bool(result.payload)

    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        result = self._host.workspace_library_controller.set_custom_workflow_scope(workflow_id, workflow_scope)
        return bool(result.payload)


class ShellWorkspacePresenter(QObject):
    project_meta_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    graphics_preferences_changed = pyqtSignal()

    def __init__(self, host: "ShellWindow") -> None:
        super().__init__(host)
        self._host = host
        self._ui_state = host.workspace_ui_state
        host.project_meta_changed.connect(self.project_meta_changed.emit)
        host.workspace_state_changed.connect(self.workspace_state_changed.emit)
        host.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)

    @property
    def project_display_name(self) -> str:
        filename = Path(self._host.project_path).name if self._host.project_path else "untitled.sfe"
        return f"COREX Node Editor - {filename}"

    @property
    def graphics_tab_strip_density(self) -> str:
        return str(self._ui_state.tab_strip_density)

    @property
    def graphics_performance_mode(self) -> str:
        return str(self._ui_state.graphics_performance_mode)

    @property
    def active_theme_id(self) -> str:
        return str(self._ui_state.active_theme_id)

    @property
    def active_workspace_id(self) -> str:
        try:
            return self._host.workspace_manager.active_workspace_id()
        except Exception:  # noqa: BLE001
            return ""

    @property
    def active_workspace_name(self) -> str:
        workspace = self._host.model.project.workspaces.get(self.active_workspace_id)
        return workspace.name if workspace is not None else ""

    @property
    def active_view_name(self) -> str:
        workspace = self._host.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return ""
        workspace.ensure_default_view()
        active_view = workspace.views.get(workspace.active_view_id)
        if active_view is None:
            return ""
        return active_view.name

    @property
    def active_view_items(self) -> list[dict[str, Any]]:
        workspace = self._host.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return []
        workspace.ensure_default_view()
        return [
            {
                "view_id": view.view_id,
                "label": view.name,
                "active": view.view_id == workspace.active_view_id,
            }
            for view in workspace.views.values()
        ]

    @property
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return list(self._host.scene.scope_breadcrumb_model)

    @property
    def can_publish_custom_workflow_from_scope(self) -> bool:
        return bool(self._host.scene.active_scope_path)

    def request_run_workflow(self) -> None:
        self._host.run_controller.run_workflow()

    def request_toggle_run_pause(self) -> None:
        self._host.run_controller.toggle_pause_resume()

    def request_stop_workflow(self) -> None:
        self._host.run_controller.stop_workflow()

    def show_workflow_settings_dialog(self, _checked: bool = False) -> None:
        self._host.project_session_controller.show_workflow_settings_dialog()

    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        self._host.project_session_controller.set_script_editor_panel_visible(checked)

    def set_graphics_performance_mode(self, mode: str) -> None:
        self._host.set_graphics_performance_mode(mode)

    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        return bool(self._host.search_scope_controller.navigate_scope(lambda: self._host.scene.navigate_scope_to(normalized_node_id)))

    def request_switch_view(self, view_id: str) -> None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        target_id = str(view_id).strip()
        if not target_id or target_id not in workspace.views:
            return
        if workspace.active_view_id == target_id:
            return
        self._host.search_scope_controller.remember_scope_camera()
        self._host.workspace_library_controller.switch_view(target_id)
        self._host.scene.sync_scope_with_active_view()
        self._host.search_scope_controller.restore_scope_camera()

    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._host.workspace_library_controller.move_view(from_index, to_index))

    def request_rename_view(self, view_id: str) -> bool:
        return bool(self._host.workspace_library_controller.rename_view(view_id))

    def request_close_view(self, view_id: str) -> bool:
        return bool(self._host.workspace_library_controller.close_view(view_id))

    def request_create_view(self) -> None:
        self._host.workspace_library_controller.create_view()

    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._host.workspace_library_controller.move_workspace(from_index, to_index))

    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._host.workspace_library_controller.rename_workspace_by_id(workspace_id))

    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._host.workspace_library_controller.close_workspace_by_id(workspace_id))

    def request_create_workspace(self) -> None:
        self._host.workspace_library_controller.create_workspace()

    def apply_graphics_preferences(self, graphics: Any) -> dict[str, Any]:
        canvas = graphics.get("canvas", {}) if isinstance(graphics, dict) else {}
        interaction = graphics.get("interaction", {}) if isinstance(graphics, dict) else {}
        performance = graphics.get("performance", {}) if isinstance(graphics, dict) else {}
        shell = graphics.get("shell", {}) if isinstance(graphics, dict) else {}
        theme = graphics.get("theme", {}) if isinstance(graphics, dict) else {}
        graph_theme = graphics.get("graph_theme", {}) if isinstance(graphics, dict) else {}

        changed = False
        show_grid = bool(canvas.get("show_grid", self._ui_state.show_grid))
        show_minimap = bool(canvas.get("show_minimap", self._ui_state.show_minimap))
        minimap_expanded = bool(
            canvas.get("minimap_expanded", self._host.search_scope_state.graphics_minimap_expanded)
        )
        node_shadow = bool(canvas.get("node_shadow", self._ui_state.node_shadow))
        shadow_strength = int(canvas.get("shadow_strength", self._ui_state.shadow_strength))
        shadow_softness = int(canvas.get("shadow_softness", self._ui_state.shadow_softness))
        shadow_offset = int(canvas.get("shadow_offset", self._ui_state.shadow_offset))
        graphics_performance_mode = normalize_graphics_performance_mode(
            performance.get("mode", self._ui_state.graphics_performance_mode),
            self._ui_state.graphics_performance_mode,
        )
        tab_strip_density = str(shell.get("tab_strip_density", self._ui_state.tab_strip_density))
        active_theme_id = self._host.shell_host_presenter.apply_theme(
            theme.get("theme_id", self._ui_state.active_theme_id)
        )
        follow_shell_theme = graph_theme.get("follow_shell_theme")
        if not isinstance(follow_shell_theme, bool):
            follow_shell_theme = bool(DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["follow_shell_theme"])
        custom_graph_themes = serialize_custom_graph_themes(graph_theme.get("custom_themes"))
        selected_graph_theme_id = resolve_graph_theme_id(
            graph_theme.get(
                "selected_theme_id",
                DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["selected_theme_id"],
            ),
            custom_themes=custom_graph_themes,
        )
        normalized_graph_theme = {
            "follow_shell_theme": bool(follow_shell_theme),
            "selected_theme_id": selected_graph_theme_id,
            "custom_themes": custom_graph_themes,
        }
        previous_graph_theme_id = self._host.graph_theme_bridge.theme_id
        self._host.graph_theme_bridge.apply_settings(
            shell_theme_id=active_theme_id,
            graph_theme_settings=normalized_graph_theme,
        )

        if self._ui_state.show_grid != show_grid:
            self._ui_state.show_grid = show_grid
            changed = True
        if self._ui_state.show_minimap != show_minimap:
            self._ui_state.show_minimap = show_minimap
            changed = True
        if self._host.search_scope_state.graphics_minimap_expanded != minimap_expanded:
            self._host.search_scope_state.graphics_minimap_expanded = minimap_expanded
            changed = True
        if self._ui_state.node_shadow != node_shadow:
            self._ui_state.node_shadow = node_shadow
            changed = True
        if self._ui_state.shadow_strength != shadow_strength:
            self._ui_state.shadow_strength = shadow_strength
            changed = True
        if self._ui_state.shadow_softness != shadow_softness:
            self._ui_state.shadow_softness = shadow_softness
            changed = True
        if self._ui_state.shadow_offset != shadow_offset:
            self._ui_state.shadow_offset = shadow_offset
            changed = True
        if self._ui_state.graphics_performance_mode != graphics_performance_mode:
            self._ui_state.graphics_performance_mode = graphics_performance_mode
            changed = True
        if self._ui_state.tab_strip_density != tab_strip_density:
            self._ui_state.tab_strip_density = tab_strip_density
            changed = True
        if self._ui_state.active_theme_id != active_theme_id:
            self._ui_state.active_theme_id = active_theme_id
            changed = True
        if previous_graph_theme_id != self._host.graph_theme_bridge.theme_id:
            changed = True

        self._host.search_scope_controller.set_snap_to_grid_enabled(
            bool(interaction.get("snap_to_grid", self._host.search_scope_state.snap_to_grid_enabled)),
            persist=False,
        )
        if changed:
            self._host.graphics_preferences_changed.emit()

        return {
            "canvas": {
                "show_grid": bool(self._ui_state.show_grid),
                "show_minimap": bool(self._ui_state.show_minimap),
                "minimap_expanded": bool(self._host.search_scope_state.graphics_minimap_expanded),
                "node_shadow": bool(self._ui_state.node_shadow),
                "shadow_strength": int(self._ui_state.shadow_strength),
                "shadow_softness": int(self._ui_state.shadow_softness),
                "shadow_offset": int(self._ui_state.shadow_offset),
            },
            "interaction": {
                "snap_to_grid": bool(self._host.search_scope_state.snap_to_grid_enabled),
            },
            "performance": {
                "mode": str(self._ui_state.graphics_performance_mode),
            },
            "shell": {
                "tab_strip_density": str(self._ui_state.tab_strip_density),
            },
            "theme": {
                "theme_id": str(self._ui_state.active_theme_id),
            },
            "graph_theme": {
                "follow_shell_theme": bool(follow_shell_theme),
                "selected_theme_id": selected_graph_theme_id,
                "custom_themes": custom_graph_themes,
            },
        }


class ShellInspectorPresenter(QObject):
    selected_node_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    inspector_state_changed = pyqtSignal()

    def __init__(self, host: "ShellWindow") -> None:
        super().__init__(host)
        self._host = host
        host.selected_node_changed.connect(self._emit_selected_node_changed)
        host.workspace_state_changed.connect(self._emit_workspace_state_changed)

    def _emit_selected_node_changed(self) -> None:
        self.selected_node_changed.emit()
        self.inspector_state_changed.emit()

    def _emit_workspace_state_changed(self) -> None:
        self.workspace_state_changed.emit()
        self.inspector_state_changed.emit()

    def _selected_node_context(self):
        return self._host.workspace_library_controller.selected_node_context()

    def _selected_node_header_data(self) -> dict[str, Any]:
        selected = self._selected_node_context()
        if selected is None:
            return {}
        node, spec = selected
        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        workflow_nodes = workspace.nodes if workspace is not None else {}
        return build_selected_node_header_data(
            node=node,
            spec=spec,
            workflow_nodes=workflow_nodes,
        )

    @property
    def selected_node_title(self) -> str:
        return str(self._selected_node_header_data().get("title", ""))

    @property
    def selected_node_subtitle(self) -> str:
        return str(self._selected_node_header_data().get("subtitle", ""))

    @property
    def selected_node_header_items(self) -> list[dict[str, str]]:
        header_data = self._selected_node_header_data()
        items = header_data.get("metadata_items", [])
        return list(items) if isinstance(items, list) else []

    @property
    def selected_node_summary(self) -> str:
        header_data = self._selected_node_header_data()
        if not header_data:
            return "No node selected"
        lines = [str(header_data.get("title", "")).strip()]
        for item in self.selected_node_header_items:
            label = str(item.get("label", "")).strip()
            value = str(item.get("value", "")).strip()
            if label and value:
                lines.append(f"{label}: {value}")
        return "\n".join(line for line in lines if line)

    @property
    def has_selected_node(self) -> bool:
        return self._selected_node_context() is not None

    @property
    def selected_node_collapsible(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        _node, spec = selected
        return bool(spec.collapsible)

    @property
    def selected_node_collapsed(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        node, _spec = selected
        return bool(node.collapsed)

    @property
    def selected_node_is_subnode_pin(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        node, _spec = selected
        return node.type_id in self._host._SUBNODE_PIN_TYPE_IDS

    @property
    def selected_node_is_subnode_shell(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        node, _spec = selected
        return node.type_id == SUBNODE_TYPE_ID

    @property
    def selected_node_property_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        return build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=self._host._SUBNODE_PIN_TYPE_IDS,
        )

    @property
    def selected_node_port_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None or self.selected_node_is_subnode_pin:
            return []
        node, spec = selected
        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return []
        return build_selected_node_port_items(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
        )

    @property
    def pin_data_type_options(self) -> list[str]:
        return build_pin_data_type_options(
            registry_specs=self._host.registry.all_specs(),
            workspaces=self._host.model.project.workspaces.values(),
            subnode_pin_type_ids=self._host._SUBNODE_PIN_TYPE_IDS,
            subnode_pin_data_type_property=SUBNODE_PIN_DATA_TYPE_PROPERTY,
        )

    def _node_property_spec(self, node_id: str, key: str):
        normalized_node_id = str(node_id or "").strip()
        normalized_key = str(key).strip()
        if not normalized_node_id or not normalized_key:
            return None
        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return None
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return None
        spec = self._host.registry.get_spec(node.type_id)
        return next((prop for prop in spec.properties if prop.key == normalized_key), None)

    def _selected_node_property_spec(self, key: str):
        selected = self._selected_node_context()
        if selected is None:
            return None
        node, _spec = selected
        return self._node_property_spec(node.node_id, key)

    def _path_dialog_start_path(self, current_path: str) -> str:
        normalized_current = str(current_path or "").strip()
        if normalized_current:
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

    def set_selected_node_property(self, key: str, value: Any) -> None:
        self._host.workspace_library_controller.set_selected_node_property(key, value)

    def browse_selected_node_property_path(self, key: str, current_path: str) -> str:
        property_spec = self._selected_node_property_spec(key)
        if property_spec is None or str(property_spec.type) != "path":
            return ""
        return self._host.shell_host_presenter.browse_property_path_dialog(property_spec.label, current_path)

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        property_spec = self._node_property_spec(node_id, key)
        if property_spec is None or str(property_spec.type) != "path":
            return ""
        return self._host.shell_host_presenter.browse_property_path_dialog(property_spec.label, current_path)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self._host.workspace_library_controller.set_selected_port_exposed(key, exposed)

    def set_selected_port_label(self, key: str, label: str) -> bool:
        return bool(self._host.workspace_library_controller.set_selected_port_label(key, label))

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self._host.workspace_library_controller.set_selected_node_collapsed(collapsed)

    def request_ungroup_selected_nodes(self) -> bool:
        return bool(self._host.workspace_library_controller.ungroup_selected_nodes())

    def request_add_selected_subnode_pin(self, direction: str) -> str:
        result = self._host.workspace_library_controller.request_add_selected_subnode_pin(direction)
        return str(result.payload or "")

    def request_remove_selected_port(self, key: str) -> bool:
        return bool(self._host.workspace_library_controller.request_remove_selected_port(key).payload)


class GraphCanvasPresenter(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()

    def __init__(
        self,
        host: "ShellWindow",
        *,
        workspace_presenter: ShellWorkspacePresenter,
        library_presenter: ShellLibraryPresenter,
        inspector_presenter: ShellInspectorPresenter,
    ) -> None:
        super().__init__(host)
        self._host = host
        self._workspace_presenter = workspace_presenter
        self._library_presenter = library_presenter
        self._inspector_presenter = inspector_presenter
        host.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)
        host.snap_to_grid_changed.connect(self.snap_to_grid_changed.emit)

    @property
    def graphics_minimap_expanded(self) -> bool:
        return bool(self._host.search_scope_state.graphics_minimap_expanded)

    @property
    def graphics_show_grid(self) -> bool:
        return bool(self._host.workspace_ui_state.show_grid)

    @property
    def graphics_show_minimap(self) -> bool:
        return bool(self._host.workspace_ui_state.show_minimap)

    @property
    def graphics_node_shadow(self) -> bool:
        return bool(self._host.workspace_ui_state.node_shadow)

    @property
    def graphics_shadow_strength(self) -> int:
        return int(self._host.workspace_ui_state.shadow_strength)

    @property
    def graphics_shadow_softness(self) -> int:
        return int(self._host.workspace_ui_state.shadow_softness)

    @property
    def graphics_shadow_offset(self) -> int:
        return int(self._host.workspace_ui_state.shadow_offset)

    @property
    def graphics_performance_mode(self) -> str:
        return str(self._host.workspace_ui_state.graphics_performance_mode)

    @property
    def snap_to_grid_enabled(self) -> bool:
        return bool(self._host.search_scope_state.snap_to_grid_enabled)

    @property
    def snap_grid_size(self) -> float:
        return float(self._host._SNAP_GRID_SIZE)

    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        self._host.search_scope_controller.set_snap_to_grid_enabled(enabled)

    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._host.search_scope_controller.set_graphics_minimap_expanded(expanded)

    def set_graphics_performance_mode(self, mode: str) -> None:
        self._host.set_graphics_performance_mode(mode)

    def request_open_subnode_scope(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        return bool(
            self._host.search_scope_controller.navigate_scope(
                lambda: self._host.scene.open_subnode_scope(normalized_node_id)
            )
        )

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return self._inspector_presenter.browse_node_property_path(node_id, key, current_path)

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> bool:
        result = self._host.workspace_library_controller.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )
        return bool(result.payload)

    def request_connect_ports(
        self,
        node_a_id: str,
        port_a: str,
        node_b_id: str,
        port_b: str,
    ) -> bool:
        result = self._host.workspace_library_controller.request_connect_ports(node_a_id, port_a, node_b_id, port_b)
        return bool(result.payload)

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool:
        return bool(
            self._library_presenter.request_open_connection_quick_insert(
                node_id,
                port_key,
                scene_x,
                scene_y,
                overlay_x,
                overlay_y,
            )
        )

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        self._library_presenter.request_open_canvas_quick_insert(scene_x, scene_y, overlay_x, overlay_y)


__all__ = [
    "GraphCanvasPresenter",
    "ShellInspectorPresenter",
    "ShellLibraryPresenter",
    "ShellWorkspacePresenter",
    "ShellWorkspaceUiState",
    "build_default_shell_workspace_ui_state",
    "normalize_graph_theme_settings",
]
