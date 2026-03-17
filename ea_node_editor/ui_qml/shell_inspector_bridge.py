from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


class ShellInspectorBridge(QObject):
    selected_node_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    inspector_state_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        scene_bridge: "GraphSceneBridge | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge

        self._selected_node_title: Callable[[], str] = lambda: ""
        self._selected_node_subtitle: Callable[[], str] = lambda: ""
        self._selected_node_summary: Callable[[], str] = lambda: ""
        self._selected_node_header_items: Callable[[], list[dict[str, str]]] = lambda: []
        self._has_selected_node: Callable[[], bool] = lambda: False
        self._selected_node_collapsible: Callable[[], bool] = lambda: False
        self._selected_node_collapsed: Callable[[], bool] = lambda: False
        self._selected_node_is_subnode_pin: Callable[[], bool] = lambda: False
        self._selected_node_is_subnode_shell: Callable[[], bool] = lambda: False
        self._selected_node_property_items: Callable[[], list[dict[str, Any]]] = lambda: []
        self._selected_node_port_items: Callable[[], list[dict[str, Any]]] = lambda: []
        self._pin_data_type_options: Callable[[], list[str]] = lambda: []

        self._set_selected_node_property: Callable[[str, object], None] = lambda _key, _value: None
        self._browse_selected_node_property_path: Callable[[str, str], str] = (
            lambda _key, _current_path: ""
        )
        self._set_selected_port_exposed: Callable[[str, bool], None] = (
            lambda _key, _exposed: None
        )
        self._set_selected_port_label: Callable[[str, str], bool] = lambda _key, _label: False
        self._set_selected_node_collapsed: Callable[[bool], None] = lambda _collapsed: None
        self._request_ungroup_selected_nodes: Callable[[], bool] = lambda: False
        self._request_add_selected_subnode_pin: Callable[[str], str] = lambda _direction: ""
        self._request_remove_selected_port: Callable[[str], bool] = lambda _key: False

        if shell_window is not None:
            self._selected_node_title = lambda: str(shell_window.selected_node_title)
            self._selected_node_subtitle = lambda: str(shell_window.selected_node_subtitle)
            self._selected_node_summary = lambda: str(shell_window.selected_node_summary)
            self._selected_node_header_items = lambda: _copy_list(shell_window.selected_node_header_items)
            self._has_selected_node = lambda: bool(shell_window.has_selected_node)
            self._selected_node_collapsible = lambda: bool(shell_window.selected_node_collapsible)
            self._selected_node_collapsed = lambda: bool(shell_window.selected_node_collapsed)
            self._selected_node_is_subnode_pin = lambda: bool(shell_window.selected_node_is_subnode_pin)
            self._selected_node_is_subnode_shell = lambda: bool(shell_window.selected_node_is_subnode_shell)
            self._selected_node_property_items = lambda: _copy_list(shell_window.selected_node_property_items)
            self._selected_node_port_items = lambda: _copy_list(shell_window.selected_node_port_items)
            self._pin_data_type_options = lambda: _copy_list(shell_window.pin_data_type_options)

            self._set_selected_node_property = shell_window.set_selected_node_property
            self._browse_selected_node_property_path = shell_window.browse_selected_node_property_path
            self._set_selected_port_exposed = shell_window.set_selected_port_exposed
            self._set_selected_port_label = shell_window.set_selected_port_label
            self._set_selected_node_collapsed = shell_window.set_selected_node_collapsed
            self._request_ungroup_selected_nodes = shell_window.request_ungroup_selected_nodes
            self._request_add_selected_subnode_pin = shell_window.request_add_selected_subnode_pin
            self._request_remove_selected_port = shell_window.request_remove_selected_port

            shell_window.selected_node_changed.connect(self._on_selected_node_changed)
            shell_window.workspace_state_changed.connect(self._on_workspace_state_changed)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    def _on_selected_node_changed(self) -> None:
        self.selected_node_changed.emit()
        self.inspector_state_changed.emit()

    def _on_workspace_state_changed(self) -> None:
        self.workspace_state_changed.emit()
        self.inspector_state_changed.emit()

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_title(self) -> str:
        return self._selected_node_title()

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_subtitle(self) -> str:
        return self._selected_node_subtitle()

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_summary(self) -> str:
        return self._selected_node_summary()

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_header_items(self) -> list[dict[str, str]]:
        return self._selected_node_header_items()

    @pyqtProperty(bool, notify=inspector_state_changed)
    def has_selected_node(self) -> bool:
        return self._has_selected_node()

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_collapsible(self) -> bool:
        return self._selected_node_collapsible()

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_collapsed(self) -> bool:
        return self._selected_node_collapsed()

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_is_subnode_pin(self) -> bool:
        return self._selected_node_is_subnode_pin()

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_is_subnode_shell(self) -> bool:
        return self._selected_node_is_subnode_shell()

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_property_items(self) -> list[dict]:
        return self._selected_node_property_items()

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_port_items(self) -> list[dict]:
        return self._selected_node_port_items()

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def pin_data_type_options(self) -> list[str]:
        return self._pin_data_type_options()

    @pyqtSlot(str, "QVariant")
    def set_selected_node_property(self, key: str, value) -> None:
        self._set_selected_node_property(key, value)

    @pyqtSlot(str, str, result=str)
    def browse_selected_node_property_path(self, key: str, current_path: str) -> str:
        return str(self._browse_selected_node_property_path(key, current_path) or "")

    @pyqtSlot(str, bool)
    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self._set_selected_port_exposed(key, exposed)

    @pyqtSlot(str, str, result=bool)
    def set_selected_port_label(self, key: str, label: str) -> bool:
        return bool(self._set_selected_port_label(key, label))

    @pyqtSlot(bool)
    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self._set_selected_node_collapsed(collapsed)

    @pyqtSlot(result=bool)
    def request_ungroup_selected_nodes(self) -> bool:
        return bool(self._request_ungroup_selected_nodes())

    @pyqtSlot(str, result=str)
    def request_add_selected_subnode_pin(self, direction: str) -> str:
        return str(self._request_add_selected_subnode_pin(direction) or "")

    @pyqtSlot(str, result=bool)
    def request_remove_selected_port(self, key: str) -> bool:
        return bool(self._request_remove_selected_port(key))


__all__ = ["ShellInspectorBridge"]
