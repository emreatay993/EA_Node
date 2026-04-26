from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import QMessageBox, QWidget

from ea_node_editor.ui.folder_explorer import (
    FolderExplorerClipboard,
    FolderExplorerDirectoryEntry,
    FolderExplorerDirectoryListing,
    FolderExplorerFilesystemService,
    FolderExplorerServiceError,
)
from ea_node_editor.ui.shell.graph_action_contracts import (
    GraphActionId,
    normalize_graph_action_id,
    normalize_graph_action_payload,
)

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


class _GraphCanvasCommandSource(Protocol):
    def set_graphics_minimap_expanded(self, expanded: bool) -> None: ...

    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None: ...

    def set_graphics_performance_mode(self, mode: str) -> None: ...

    def set_graphics_floating_toolbar_style(self, style: str) -> None: ...

    def request_open_subnode_scope(self, node_id: str) -> bool: ...

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str: ...

    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str: ...

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> bool: ...

    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool: ...

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool: ...

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None: ...


class _FolderExplorerConfirmationSource(Protocol):
    def confirm_folder_explorer_operation(
        self,
        operation: str,
        path: str,
        target_path: str = "",
    ) -> bool: ...


class _FolderExplorerClipboardSource(Protocol):
    def setText(self, text: str) -> None: ...  # noqa: N802


class _FolderExplorerOpenSource(Protocol):
    def open_folder_explorer_path(self, path: str) -> bool: ...


class _GraphCanvasHostSource(Protocol):
    def request_delete_selected_graph_items(self, edge_ids: list[object]) -> bool: ...

    def request_navigate_scope_parent(self) -> bool: ...

    def request_navigate_scope_root(self) -> bool: ...

    def set_graph_cursor_shape(self, cursor_shape: int) -> None: ...

    def clear_graph_cursor_shape(self) -> None: ...

    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]: ...


class _GraphCanvasSceneCommandSource(Protocol):
    def select_node(self, node_id: str, additive: bool = False) -> None: ...

    def clear_selection(self) -> None: ...

    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None: ...

    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None: ...

    def set_node_property(self, node_id: str, key: str, value: object) -> None: ...

    def set_pending_surface_action(self, node_id: str) -> None: ...

    def consume_pending_surface_action(self, node_id: str) -> bool: ...

    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool: ...

    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str: ...

    def add_path_pointer_node(self, path: str, mode: str, x: float = 0.0, y: float = 0.0) -> str: ...

    def add_folder_explorer_node(self, current_path: str, x: float = 0.0, y: float = 0.0) -> str: ...

    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool: ...

    def move_node(self, node_id: str, x: float, y: float) -> None: ...

    def resize_node(self, node_id: str, width: float, height: float) -> None: ...

    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None: ...

    def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool: ...


class _GraphCanvasScenePolicySource(Protocol):
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool: ...

    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool: ...


def _invoke(source: object | None, name: str, *args, default: Any = None) -> Any:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return default
    return callback(*args)


def _copy_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


_FOLDER_EXPLORER_ACTION_IDS: frozenset[GraphActionId] = frozenset(
    {
        GraphActionId.FOLDER_EXPLORER_LIST,
        GraphActionId.FOLDER_EXPLORER_NAVIGATE,
        GraphActionId.FOLDER_EXPLORER_REFRESH,
        GraphActionId.FOLDER_EXPLORER_SET_SORT,
        GraphActionId.FOLDER_EXPLORER_SET_SEARCH,
        GraphActionId.FOLDER_EXPLORER_OPEN,
        GraphActionId.FOLDER_EXPLORER_OPEN_IN_NEW_WINDOW,
        GraphActionId.FOLDER_EXPLORER_NEW_FOLDER,
        GraphActionId.FOLDER_EXPLORER_RENAME,
        GraphActionId.FOLDER_EXPLORER_DELETE,
        GraphActionId.FOLDER_EXPLORER_CUT,
        GraphActionId.FOLDER_EXPLORER_COPY,
        GraphActionId.FOLDER_EXPLORER_PASTE,
        GraphActionId.FOLDER_EXPLORER_COPY_PATH,
        GraphActionId.FOLDER_EXPLORER_PROPERTIES,
        GraphActionId.FOLDER_EXPLORER_SEND_TO_COREX_PATH_POINTER,
    }
)

_FOLDER_EXPLORER_CONFIRMATION_OPERATIONS: dict[GraphActionId, str] = {
    GraphActionId.FOLDER_EXPLORER_NEW_FOLDER: "new_folder",
    GraphActionId.FOLDER_EXPLORER_RENAME: "rename",
    GraphActionId.FOLDER_EXPLORER_DELETE: "delete",
    GraphActionId.FOLDER_EXPLORER_CUT: "cut",
    GraphActionId.FOLDER_EXPLORER_COPY: "copy",
    GraphActionId.FOLDER_EXPLORER_PASTE: "paste",
}

_FOLDER_EXPLORER_COMMAND_ALIASES: dict[str, str] = {
    "list": GraphActionId.FOLDER_EXPLORER_LIST.value,
    "navigate": GraphActionId.FOLDER_EXPLORER_NAVIGATE.value,
    "refresh": GraphActionId.FOLDER_EXPLORER_REFRESH.value,
    "setSort": GraphActionId.FOLDER_EXPLORER_SET_SORT.value,
    "setSearch": GraphActionId.FOLDER_EXPLORER_SET_SEARCH.value,
    "open": GraphActionId.FOLDER_EXPLORER_OPEN.value,
    "openInNewWindow": GraphActionId.FOLDER_EXPLORER_OPEN_IN_NEW_WINDOW.value,
    "newFolder": GraphActionId.FOLDER_EXPLORER_NEW_FOLDER.value,
    "rename": GraphActionId.FOLDER_EXPLORER_RENAME.value,
    "delete": GraphActionId.FOLDER_EXPLORER_DELETE.value,
    "cut": GraphActionId.FOLDER_EXPLORER_CUT.value,
    "copy": GraphActionId.FOLDER_EXPLORER_COPY.value,
    "paste": GraphActionId.FOLDER_EXPLORER_PASTE.value,
    "copyPath": GraphActionId.FOLDER_EXPLORER_COPY_PATH.value,
    "properties": GraphActionId.FOLDER_EXPLORER_PROPERTIES.value,
    "sendToCorexPathPointer": GraphActionId.FOLDER_EXPLORER_SEND_TO_COREX_PATH_POINTER.value,
}


def _payload_str(payload: Mapping[str, object], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return str(value if value is not None else "").strip()


def _payload_float(payload: Mapping[str, object], key: str, default: float = 0.0) -> float:
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError):
        return default


def _payload_bool(payload: Mapping[str, object], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on"}
    return bool(value)


def _first_payload_str(payload: Mapping[str, object], *keys: str, default: str = "") -> str:
    for key in keys:
        value = _payload_str(payload, key)
        if value:
            return value
    return default


def _resolve_scene_command_source(scene_bridge: object | None) -> _GraphCanvasSceneCommandSource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasSceneCommandSource,
        getattr(scene_bridge, "command_bridge", scene_bridge),
    )


def _resolve_scene_policy_source(scene_bridge: object | None) -> _GraphCanvasScenePolicySource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasScenePolicySource,
        getattr(scene_bridge, "policy_bridge", scene_bridge),
    )


class GraphCanvasCommandBridge(QObject):
    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: object | None = None,
        canvas_source: _GraphCanvasCommandSource | None = None,
        host_source: _GraphCanvasHostSource | None = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
        folder_explorer_service: FolderExplorerFilesystemService | None = None,
        folder_explorer_confirmation_source: _FolderExplorerConfirmationSource | None = None,
        folder_explorer_clipboard_source: _FolderExplorerClipboardSource | None = None,
        folder_explorer_open_source: _FolderExplorerOpenSource | None = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._canvas_source = canvas_source
        self._host_source = host_source
        self._scene_command_source = _resolve_scene_command_source(scene_bridge)
        self._scene_policy_source = _resolve_scene_policy_source(scene_bridge)
        self._folder_explorer_service = folder_explorer_service or FolderExplorerFilesystemService()
        self._folder_explorer_confirmation_source = folder_explorer_confirmation_source
        self._folder_explorer_clipboard_source = folder_explorer_clipboard_source
        self._folder_explorer_open_source = folder_explorer_open_source

    @property
    def shell_window(self) -> object | None:
        return None

    @property
    def canvas_source(self) -> _GraphCanvasCommandSource | None:
        return self._canvas_source

    @property
    def host_source(self) -> _GraphCanvasHostSource | None:
        return self._host_source

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def scene_command_source(self) -> _GraphCanvasSceneCommandSource | None:
        return self._scene_command_source

    @property
    def scene_policy_source(self) -> _GraphCanvasScenePolicySource | None:
        return self._scene_policy_source

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtProperty(QObject, constant=True)
    def viewport_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        _invoke(self._canvas_source, "set_graphics_minimap_expanded", bool(expanded))

    @pyqtSlot(bool)
    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        _invoke(self._canvas_source, "set_graphics_show_port_labels", bool(show_port_labels))

    @pyqtSlot(str)
    def set_graphics_performance_mode(self, mode: str) -> None:
        _invoke(self._canvas_source, "set_graphics_performance_mode", mode)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_style(self, style: str) -> None:
        _invoke(self._canvas_source, "set_graphics_floating_toolbar_style", style)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_size(self, size: str) -> None:
        _invoke(self._canvas_source, "set_graphics_floating_toolbar_size", size)

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        _invoke(self._view_bridge, "adjust_zoom", float(factor))

    @pyqtSlot(float, float, float, result=bool)
    def adjust_zoom_at_viewport_point(self, factor: float, viewport_x: float, viewport_y: float) -> bool:
        return bool(
            _invoke(
                self._view_bridge,
                "adjust_zoom_at_viewport_point",
                float(factor),
                float(viewport_x),
                float(viewport_y),
                default=False,
            )
        )

    @pyqtSlot(str, bool, float, float, result="QVariantMap")
    def request_create_path_pointer_node(
        self,
        path_or_url: str,
        is_folder: bool,
        scene_x: float,
        scene_y: float,
    ) -> dict[str, Any]:
        path = self._path_from_url_or_path(path_or_url)
        if not path:
            return {
                "success": False,
                "path": "",
                "created_node_id": "",
                "created_type_id": "",
                "mode": "folder" if bool(is_folder) else "file",
                "error": {
                    "code": "missing_path",
                    "message": "A file or folder path is required.",
                },
            }
        path_obj = Path(path)
        mode = "folder" if path_obj.is_dir() or bool(is_folder) else "file"
        node_id = self._add_path_pointer_node(path, mode, float(scene_x), float(scene_y))
        if not node_id:
            return {
                "success": False,
                "path": path,
                "created_node_id": "",
                "created_type_id": "io.path_pointer",
                "mode": mode,
                "error": {
                    "code": "mutation_unavailable",
                    "message": "Graph scene command bridge cannot create an io.path_pointer node.",
                },
            }
        return {
            "success": True,
            "path": path,
            "created_node_id": node_id,
            "created_type_id": "io.path_pointer",
            "mode": mode,
            "error": {},
        }

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        _invoke(self._view_bridge, "pan_by", float(delta_x), float(delta_y))

    @pyqtSlot(float, float, float, result=bool)
    def set_view_state(self, zoom: float, center_x: float, center_y: float) -> bool:
        return bool(
            _invoke(
                self._view_bridge,
                "set_view_state",
                float(zoom),
                float(center_x),
                float(center_y),
                default=False,
            )
        )

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        _invoke(self._view_bridge, "set_viewport_size", float(width), float(height))

    @pyqtSlot(float, float)
    def center_on_scene_point(self, x: float, y: float) -> None:
        _invoke(self._view_bridge, "center_on_scene_point", float(x), float(y))

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(
            _invoke(
                self._canvas_source,
                "request_open_subnode_scope",
                node_id,
                default=False,
            )
        )

    @pyqtSlot(str, result=bool)
    def can_open_comment_peek(self, node_id: str) -> bool:
        return bool(_invoke(self._scene_bridge, "can_open_comment_peek", node_id, default=False))

    @pyqtSlot(result=bool)
    def request_close_comment_peek(self) -> bool:
        return bool(_invoke(self._scene_bridge, "close_comment_peek", default=False))

    @pyqtSlot(result=str)
    def active_comment_peek_node_id(self) -> str:
        return str(getattr(self._scene_bridge, "active_comment_peek_node_id", "") or "")

    @pyqtSlot(str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return str(
            _invoke(
                self._canvas_source,
                "browse_node_property_path",
                node_id,
                key,
                current_path,
                default="",
            )
            or ""
        )

    @pyqtSlot(str, str, str, result=str)
    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str:
        return str(
            _invoke(
                self._canvas_source,
                "pick_node_property_color",
                node_id,
                key,
                current_value,
                default="",
            )
            or ""
        )

    @pyqtSlot(
        str,
        float,
        float,
        str,
        str,
        str,
        str,
        result=bool,
    )
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
        return bool(
            _invoke(
                self._canvas_source,
                "request_drop_node_from_library",
                type_id,
                float(scene_x),
                float(scene_y),
                target_mode,
                target_node_id,
                target_port_key,
                target_edge_id,
                default=False,
            )
        )

    @pyqtSlot(str, str, str, str, result=bool)
    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return bool(
            _invoke(
                self._canvas_source,
                "request_connect_ports",
                source_node_id,
                source_port_key,
                target_node_id,
                target_port_key,
                default=False,
            )
        )

    @pyqtSlot(str, str, float, float, float, float, result=bool)
    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool:
        return bool(
            _invoke(
                self._canvas_source,
                "request_open_connection_quick_insert",
                node_id,
                port_key,
                float(cursor_scene_x),
                float(cursor_scene_y),
                float(overlay_x),
                float(overlay_y),
                default=False,
            )
        )

    @pyqtSlot(float, float, float, float)
    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        _invoke(
            self._canvas_source,
            "request_open_canvas_quick_insert",
            float(scene_x),
            float(scene_y),
            float(overlay_x),
            float(overlay_y),
        )

    @pyqtSlot("QVariantList", result=bool)
    def request_delete_selected_graph_items(self, edge_ids: list) -> bool:
        return bool(
            _invoke(
                self._host_source,
                "request_delete_selected_graph_items",
                edge_ids,
                default=False,
            )
        )

    @pyqtSlot(result=bool)
    def request_navigate_scope_parent(self) -> bool:
        return bool(
            _invoke(
                self._host_source,
                "request_navigate_scope_parent",
                default=False,
            )
        )

    @pyqtSlot(result=bool)
    def request_navigate_scope_root(self) -> bool:
        return bool(
            _invoke(
                self._host_source,
                "request_navigate_scope_root",
                default=False,
            )
        )

    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        _invoke(self._scene_command_source, "select_node", node_id, bool(additive))

    @pyqtSlot()
    def clear_selection(self) -> None:
        _invoke(self._scene_command_source, "clear_selection")

    @pyqtSlot(float, float, float, float)
    @pyqtSlot(float, float, float, float, bool)
    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None:
        _invoke(
            self._scene_command_source,
            "select_nodes_in_rect",
            float(x1),
            float(y1),
            float(x2),
            float(y2),
            bool(additive),
        )

    @pyqtSlot(str, str, str)
    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        _invoke(self._scene_command_source, "set_node_port_label", node_id, port_key, label)

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        _invoke(self._scene_command_source, "set_node_property", node_id, key, value)

    @pyqtSlot(str)
    def set_pending_surface_action(self, node_id: str) -> None:
        _invoke(self._scene_command_source, "set_pending_surface_action", node_id)

    @pyqtSlot(str, result=bool)
    def consume_pending_surface_action(self, node_id: str) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "consume_pending_surface_action",
                node_id,
                default=False,
            )
        )

    @pyqtSlot(str, "QVariantMap", result=bool)
    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "set_node_properties",
                node_id,
                dict(values or {}),
                default=False,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return bool(
            _invoke(
                self._scene_policy_source,
                "are_port_kinds_compatible",
                source_kind,
                target_kind,
                default=False,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return bool(
            _invoke(
                self._scene_policy_source,
                "are_data_types_compatible",
                source_type,
                target_type,
                default=False,
            )
        )

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list, delta_x: float, delta_y: float) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "move_nodes_by_delta",
                node_ids,
                float(delta_x),
                float(delta_y),
                default=False,
            )
        )

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        _invoke(self._scene_command_source, "move_node", node_id, float(x), float(y))

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        _invoke(self._scene_command_source, "resize_node", node_id, float(width), float(height))

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        _invoke(
            self._scene_command_source,
            "set_node_geometry",
            node_id,
            float(x),
            float(y),
            float(width),
            float(height),
        )

    @pyqtSlot(str, str, bool, result=bool)
    def set_port_locked(self, node_id: str, port_key: str, locked: bool) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "set_port_locked",
                node_id,
                port_key,
                bool(locked),
                default=False,
            )
        )

    @pyqtSlot(int)
    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        _invoke(self._host_source, "set_graph_cursor_shape", int(cursor_shape))

    @pyqtSlot()
    def clear_graph_cursor_shape(self) -> None:
        _invoke(self._host_source, "clear_graph_cursor_shape")

    @pyqtSlot(str, "QVariant", result="QVariantMap")
    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return _copy_dict(
            _invoke(
                self._host_source,
                "describe_pdf_preview",
                source,
                page_number,
                default={},
            )
        )

    @pyqtSlot(str, "QVariantMap", result="QVariantMap")
    def request_folder_explorer_action(self, action_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            return self._folder_explorer_error_payload(
                action_id=str(action_id or ""),
                code="invalid_payload",
                message="Folder explorer action payload must be an object.",
            )
        action_literal = str(action_id or "").strip()
        normalized_action_id = normalize_graph_action_id(
            _FOLDER_EXPLORER_COMMAND_ALIASES.get(action_literal, action_literal)
        )
        if normalized_action_id not in _FOLDER_EXPLORER_ACTION_IDS:
            return self._folder_explorer_error_payload(
                action_id=str(action_id or ""),
                payload=payload,
                code="unknown_action",
                message=f"Unsupported folder explorer action: {action_id!r}",
            )
        normalized_payload = normalize_graph_action_payload(normalized_action_id, payload)
        if normalized_payload is None:
            return self._folder_explorer_error_payload(
                action_id=normalized_action_id.value,
                payload=payload,
                code="invalid_payload",
                message=f"Invalid payload for folder explorer action: {normalized_action_id.value}",
            )
        try:
            return self._dispatch_folder_explorer_action(normalized_action_id, normalized_payload)
        except FolderExplorerServiceError as exc:
            return self._folder_explorer_service_error_payload(normalized_action_id, normalized_payload, exc)

    def _dispatch_folder_explorer_action(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        if action_id in {
            GraphActionId.FOLDER_EXPLORER_LIST,
            GraphActionId.FOLDER_EXPLORER_REFRESH,
            GraphActionId.FOLDER_EXPLORER_SET_SORT,
            GraphActionId.FOLDER_EXPLORER_SET_SEARCH,
        }:
            return self._folder_explorer_listing_payload(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_NAVIGATE:
            return self._folder_explorer_navigate(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_OPEN:
            return self._folder_explorer_open(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_OPEN_IN_NEW_WINDOW:
            return self._folder_explorer_open_in_new_window(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_NEW_FOLDER:
            return self._folder_explorer_new_folder(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_RENAME:
            return self._folder_explorer_rename(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_DELETE:
            return self._folder_explorer_delete(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_CUT:
            return self._folder_explorer_clipboard_action(action_id, payload, mode="cut")
        if action_id is GraphActionId.FOLDER_EXPLORER_COPY:
            return self._folder_explorer_clipboard_action(action_id, payload, mode="copy")
        if action_id is GraphActionId.FOLDER_EXPLORER_PASTE:
            return self._folder_explorer_paste(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_COPY_PATH:
            return self._folder_explorer_copy_path(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_PROPERTIES:
            return self._folder_explorer_properties(action_id, payload)
        if action_id is GraphActionId.FOLDER_EXPLORER_SEND_TO_COREX_PATH_POINTER:
            return self._folder_explorer_send_to_corex_path_pointer(action_id, payload)
        return self._folder_explorer_error_payload(
            action_id=action_id.value,
            payload=payload,
            code="unknown_action",
            message=f"Unsupported folder explorer action: {action_id.value}",
        )

    def _folder_explorer_listing_payload(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
        *,
        path: str | None = None,
    ) -> dict[str, Any]:
        listing = self._folder_explorer_service.list_directory(
            path or _payload_str(payload, "path"),
            sort_key=cast(Any, _first_payload_str(payload, "sort_key", "sortKey", default="name")),
            reverse=_payload_bool(payload, "reverse", False),
            filter_text=str(payload.get("filter_text", payload.get("filterText", "")) or ""),
        )
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=listing.directory_path,
            listing=self._folder_explorer_listing_to_payload(listing),
        )

    def _folder_explorer_navigate(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        listing_result = self._folder_explorer_listing_payload(action_id, payload)
        if not listing_result.get("success"):
            return listing_result
        directory_path = _payload_str(cast(Mapping[str, object], listing_result), "path")
        if not self._set_folder_explorer_current_path(_payload_str(payload, "node_id"), directory_path):
            return self._folder_explorer_error_payload(
                action_id=action_id.value,
                payload=payload,
                path=directory_path,
                code="mutation_unavailable",
                message="Graph scene command bridge cannot update folder explorer current_path.",
            )
        return listing_result

    def _folder_explorer_open(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        path = self._folder_explorer_service.copy_path(_payload_str(payload, "path"))
        if not self._open_folder_explorer_path(path):
            return self._folder_explorer_error_payload(
                action_id=action_id.value,
                payload=payload,
                path=path,
                code="open_failed",
                message=f"Could not open path: {path}",
            )
        return self._folder_explorer_success_payload(action_id, payload, path=path)

    def _folder_explorer_open_in_new_window(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        listing = self._folder_explorer_service.list_directory(_payload_str(payload, "path"))
        node_id = self._add_folder_explorer_node(
            listing.directory_path,
            _payload_float(payload, "scene_x"),
            _payload_float(payload, "scene_y"),
        )
        if not node_id:
            return self._folder_explorer_error_payload(
                action_id=action_id.value,
                payload=payload,
                path=listing.directory_path,
                code="mutation_unavailable",
                message="Graph scene command bridge cannot create an io.folder_explorer node.",
            )
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=listing.directory_path,
            created_node_id=node_id,
            created_type_id="io.folder_explorer",
        )

    def _folder_explorer_new_folder(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        parent_path = _payload_str(payload, "path")
        name = _payload_str(payload, "name")
        target_path = str(Path(parent_path) / name) if name else ""
        cancelled = self._cancelled_confirmation_payload(action_id, payload, target_path=target_path)
        if cancelled is not None:
            return cancelled
        entry = self._folder_explorer_service.new_folder(parent_path, name, confirmed=True)
        return self._folder_explorer_entry_mutation_payload(action_id, payload, entry, listing_path=parent_path)

    def _folder_explorer_rename(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        path = _payload_str(payload, "path")
        new_name = _payload_str(payload, "new_name")
        parent_path = self._folder_explorer_refresh_path(payload, fallback_path=path)
        target_path = str(Path(path).parent / new_name) if new_name else ""
        cancelled = self._cancelled_confirmation_payload(action_id, payload, target_path=target_path)
        if cancelled is not None:
            return cancelled
        entry = self._folder_explorer_service.rename(path, new_name, confirmed=True)
        return self._folder_explorer_entry_mutation_payload(action_id, payload, entry, listing_path=parent_path)

    def _folder_explorer_delete(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        path = _payload_str(payload, "path")
        listing_path = self._folder_explorer_refresh_path(payload, fallback_path=path)
        cancelled = self._cancelled_confirmation_payload(action_id, payload)
        if cancelled is not None:
            return cancelled
        self._folder_explorer_service.delete(path, confirmed=True)
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=path,
            listing=self._folder_explorer_listing_to_payload(
                self._folder_explorer_service.list_directory(listing_path)
            ),
        )

    def _folder_explorer_clipboard_action(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
        *,
        mode: str,
    ) -> dict[str, Any]:
        cancelled = self._cancelled_confirmation_payload(action_id, payload)
        if cancelled is not None:
            return cancelled
        path = _payload_str(payload, "path")
        clipboard = (
            self._folder_explorer_service.cut(path, confirmed=True)
            if mode == "cut"
            else self._folder_explorer_service.copy(path, confirmed=True)
        )
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=clipboard.source_path,
            clipboard=self._folder_explorer_clipboard_to_payload(clipboard),
        )

    def _folder_explorer_paste(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        destination = _payload_str(payload, "path")
        cancelled = self._cancelled_confirmation_payload(action_id, payload)
        if cancelled is not None:
            return cancelled
        entry = self._folder_explorer_service.paste(destination, confirmed=True)
        return self._folder_explorer_entry_mutation_payload(action_id, payload, entry, listing_path=destination)

    def _folder_explorer_copy_path(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        copied_path = self._folder_explorer_service.copy_path(
            _payload_str(payload, "path"),
            quote=_payload_bool(payload, "quote", False),
        )
        if not self._copy_to_system_clipboard(copied_path):
            return self._folder_explorer_error_payload(
                action_id=action_id.value,
                payload=payload,
                path=copied_path,
                code="clipboard_unavailable",
                message="System clipboard is not available.",
            )
        return self._folder_explorer_success_payload(action_id, payload, path=copied_path, copied_path=copied_path)

    def _folder_explorer_properties(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        path = self._folder_explorer_service.copy_path(_payload_str(payload, "path"))
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=path,
            entry=self._folder_explorer_entry_properties_payload(path),
        )

    def _folder_explorer_send_to_corex_path_pointer(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        path = self._folder_explorer_service.copy_path(_payload_str(payload, "path"))
        mode = "folder" if Path(path).is_dir() else "file"
        node_id = self._add_path_pointer_node(
            path,
            mode,
            _payload_float(payload, "scene_x"),
            _payload_float(payload, "scene_y"),
        )
        if not node_id:
            return self._folder_explorer_error_payload(
                action_id=action_id.value,
                payload=payload,
                path=path,
                code="mutation_unavailable",
                message="Graph scene command bridge cannot create an io.path_pointer node.",
            )
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=path,
            created_node_id=node_id,
            created_type_id="io.path_pointer",
            mode=mode,
        )

    def _folder_explorer_entry_mutation_payload(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
        entry: FolderExplorerDirectoryEntry,
        *,
        listing_path: str,
    ) -> dict[str, Any]:
        return self._folder_explorer_success_payload(
            action_id,
            payload,
            path=entry.absolute_path,
            entry=self._folder_explorer_entry_to_payload(entry),
            listing=self._folder_explorer_listing_to_payload(
                self._folder_explorer_service.list_directory(listing_path)
            ),
        )

    def _set_folder_explorer_current_path(self, node_id: str, current_path: str) -> bool:
        command_source = self._scene_command_source
        if command_source is None:
            return False
        callback = getattr(command_source, "set_node_property", None)
        if not callable(callback):
            return False
        callback(node_id, "current_path", current_path)
        return True

    def _add_path_pointer_node(self, path: str, mode: str, x: float, y: float) -> str:
        command_source = self._scene_command_source
        if command_source is None:
            return ""
        add_path_pointer = getattr(command_source, "add_path_pointer_node", None)
        if callable(add_path_pointer):
            return str(add_path_pointer(path, mode, x, y) or "")
        if not self._can_set_node_properties():
            return ""
        node_id = self._add_node_from_type("io.path_pointer", x, y)
        if not node_id:
            return ""
        self._set_node_properties(node_id, {"path": path, "mode": mode})
        return node_id

    def _add_folder_explorer_node(self, current_path: str, x: float, y: float) -> str:
        command_source = self._scene_command_source
        if command_source is None:
            return ""
        add_folder_explorer = getattr(command_source, "add_folder_explorer_node", None)
        if callable(add_folder_explorer):
            return str(add_folder_explorer(current_path, x, y) or "")
        if not self._can_set_node_properties():
            return ""
        node_id = self._add_node_from_type("io.folder_explorer", x, y)
        if not node_id:
            return ""
        self._set_node_properties(node_id, {"current_path": current_path})
        return node_id

    def _add_node_from_type(self, type_id: str, x: float, y: float) -> str:
        command_source = self._scene_command_source
        callback = getattr(command_source, "add_node_from_type", None) if command_source is not None else None
        if not callable(callback):
            return ""
        return str(callback(type_id, float(x), float(y)) or "")

    def _can_set_node_properties(self) -> bool:
        command_source = self._scene_command_source
        if command_source is None:
            return False
        return callable(getattr(command_source, "set_node_properties", None)) or callable(
            getattr(command_source, "set_node_property", None)
        )

    def _set_node_properties(self, node_id: str, properties: Mapping[str, object]) -> None:
        command_source = self._scene_command_source
        if command_source is None:
            return
        bulk = getattr(command_source, "set_node_properties", None)
        if callable(bulk) and bool(bulk(node_id, dict(properties))):
            return
        setter = getattr(command_source, "set_node_property", None)
        if not callable(setter):
            return
        for key, value in properties.items():
            setter(node_id, key, value)

    def _cancelled_confirmation_payload(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
        *,
        target_path: str = "",
    ) -> dict[str, Any] | None:
        operation = _FOLDER_EXPLORER_CONFIRMATION_OPERATIONS[action_id]
        path = _payload_str(payload, "path")
        if self._confirm_folder_explorer_operation(operation, path, target_path=target_path):
            return None
        return self._folder_explorer_error_payload(
            action_id=action_id.value,
            payload=payload,
            path=path,
            target_path=target_path,
            code="cancelled",
            message=f"Folder explorer operation was cancelled: {operation}",
            cancelled=True,
        )

    def _confirm_folder_explorer_operation(self, operation: str, path: str, *, target_path: str = "") -> bool:
        source = self._folder_explorer_confirmation_source
        callback = getattr(source, "confirm_folder_explorer_operation", None) if source is not None else None
        if callable(callback):
            return bool(callback(operation, path, target_path))

        message = f"Apply folder explorer operation '{operation}' to:\n{path}"
        if target_path:
            message += f"\n\nTarget:\n{target_path}"
        choice = QMessageBox.question(
            self._shell_window if isinstance(self._shell_window, QWidget) else None,
            "Confirm Folder Explorer Operation",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return choice == QMessageBox.StandardButton.Yes

    def _copy_to_system_clipboard(self, text: str) -> bool:
        source = self._folder_explorer_clipboard_source
        setter = getattr(source, "setText", None) if source is not None else None
        if callable(setter):
            setter(text)
            return True
        app = QGuiApplication.instance()
        if app is None:
            return False
        clipboard = app.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(text)
        return True

    def _open_folder_explorer_path(self, path: str) -> bool:
        source = self._folder_explorer_open_source
        opener = getattr(source, "open_folder_explorer_path", None) if source is not None else None
        if callable(opener):
            return bool(opener(path))
        return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(path)))

    @staticmethod
    def _path_from_url_or_path(path_or_url: str) -> str:
        text = str(path_or_url or "").strip()
        if not text:
            return ""
        url = QUrl(text)
        if url.isLocalFile():
            return str(Path(url.toLocalFile()).resolve(strict=False))
        return str(Path(text).expanduser().resolve(strict=False))

    def _folder_explorer_refresh_path(self, payload: Mapping[str, object], *, fallback_path: str) -> str:
        explicit = _first_payload_str(payload, "current_path", "directory_path", "currentPath", "directoryPath")
        if explicit:
            return explicit
        parent = self._folder_explorer_service.parent_path(fallback_path)
        return parent or fallback_path

    def _folder_explorer_success_payload(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
        *,
        path: str = "",
        **values: Any,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": True,
            "cancelled": False,
            "action_id": action_id.value,
            "node_id": _payload_str(payload, "node_id"),
            "path": path or _payload_str(payload, "path"),
            "error": {},
        }
        result.update(values)
        return result

    def _folder_explorer_service_error_payload(
        self,
        action_id: GraphActionId,
        payload: Mapping[str, object],
        exc: FolderExplorerServiceError,
    ) -> dict[str, Any]:
        return self._folder_explorer_error_payload(
            action_id=action_id.value,
            payload=payload,
            path=exc.path,
            target_path=exc.target_path,
            code=exc.code,
            message=exc.message,
            error=exc.to_dict(),
        )

    def _folder_explorer_error_payload(
        self,
        *,
        action_id: str,
        payload: Mapping[str, object] | None = None,
        path: str = "",
        target_path: str = "",
        code: str,
        message: str,
        cancelled: bool = False,
        error: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        normalized_payload = payload or {}
        return {
            "success": False,
            "cancelled": bool(cancelled),
            "action_id": action_id,
            "node_id": _payload_str(normalized_payload, "node_id"),
            "path": path or _payload_str(normalized_payload, "path"),
            "error": dict(
                error
                or {
                    "code": code,
                    "message": message,
                    "operation": action_id,
                    "path": path or _payload_str(normalized_payload, "path"),
                    "target_path": target_path,
                }
            ),
        }

    @staticmethod
    def _folder_explorer_listing_to_payload(listing: FolderExplorerDirectoryListing) -> dict[str, Any]:
        return {
            "directory_path": listing.directory_path,
            "parent_path": listing.parent_path or "",
            "breadcrumbs": [
                {
                    "name": breadcrumb.name,
                    "absolute_path": breadcrumb.absolute_path,
                }
                for breadcrumb in listing.breadcrumbs
            ],
            "entries": [
                GraphCanvasCommandBridge._folder_explorer_entry_to_payload(entry)
                for entry in listing.entries
            ],
            "sort_key": listing.sort_key,
            "reverse": listing.reverse,
            "filter_text": listing.filter_text,
        }

    @staticmethod
    def _folder_explorer_entry_to_payload(entry: FolderExplorerDirectoryEntry) -> dict[str, Any]:
        return {
            "name": entry.name,
            "absolute_path": entry.absolute_path,
            "kind": entry.kind,
            "is_folder": entry.is_folder,
            "modified_timestamp": entry.modified_timestamp,
            "extension": entry.extension,
            "type_label": entry.type_label,
            "size_bytes": entry.size_bytes if entry.size_bytes is not None else -1,
            "display_size": entry.display_size,
        }

    @staticmethod
    def _folder_explorer_clipboard_to_payload(clipboard: FolderExplorerClipboard) -> dict[str, str]:
        return {
            "source_path": clipboard.source_path,
            "mode": clipboard.mode,
        }

    @staticmethod
    def _folder_explorer_entry_properties_payload(path: str) -> dict[str, Any]:
        target = Path(path)
        stats = target.stat()
        is_folder = target.is_dir()
        return {
            "name": target.name or path,
            "absolute_path": path,
            "kind": "folder" if is_folder else "file",
            "is_folder": is_folder,
            "modified_timestamp": float(stats.st_mtime),
            "extension": "" if is_folder else target.suffix.lower(),
            "size_bytes": -1 if is_folder else int(stats.st_size),
        }


__all__ = ["GraphCanvasCommandBridge"]
