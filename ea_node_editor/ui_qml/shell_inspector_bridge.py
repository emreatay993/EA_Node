from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


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
        self._connect_shell_signal("selected_node_changed", self._on_selected_node_changed)
        self._connect_shell_signal("workspace_state_changed", self._on_workspace_state_changed)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    def _connect_shell_signal(self, signal_name: str, callback) -> None:  # noqa: ANN001
        shell_window = self._shell_window
        if shell_window is None:
            return
        signal = getattr(shell_window, signal_name, None)
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(callback)

    def _shell_value(self, name: str, default):
        shell_window = self._shell_window
        if shell_window is None:
            return default
        return getattr(shell_window, name, default)

    def _call_shell(self, name: str, *args):
        shell_window = self._shell_window
        if shell_window is None:
            return None
        method = getattr(shell_window, name, None)
        if method is None:
            return None
        return method(*args)

    def _on_selected_node_changed(self) -> None:
        self.selected_node_changed.emit()
        self.inspector_state_changed.emit()

    def _on_workspace_state_changed(self) -> None:
        self.workspace_state_changed.emit()
        self.inspector_state_changed.emit()

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_title(self) -> str:
        return str(self._shell_value("selected_node_title", ""))

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_subtitle(self) -> str:
        return str(self._shell_value("selected_node_subtitle", ""))

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_summary(self) -> str:
        return str(self._shell_value("selected_node_summary", ""))

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_header_items(self) -> list[dict[str, str]]:
        items = self._shell_value("selected_node_header_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty(bool, notify=inspector_state_changed)
    def has_selected_node(self) -> bool:
        return bool(self._shell_value("has_selected_node", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_collapsible(self) -> bool:
        return bool(self._shell_value("selected_node_collapsible", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_collapsed(self) -> bool:
        return bool(self._shell_value("selected_node_collapsed", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_is_subnode_pin(self) -> bool:
        return bool(self._shell_value("selected_node_is_subnode_pin", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_is_subnode_shell(self) -> bool:
        return bool(self._shell_value("selected_node_is_subnode_shell", False))

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_property_items(self) -> list[dict]:
        items = self._shell_value("selected_node_property_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_port_items(self) -> list[dict]:
        items = self._shell_value("selected_node_port_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def pin_data_type_options(self) -> list[str]:
        items = self._shell_value("pin_data_type_options", [])
        return list(items) if isinstance(items, list) else []

    @pyqtSlot(str, "QVariant")
    def set_selected_node_property(self, key: str, value) -> None:
        self._call_shell("set_selected_node_property", key, value)

    @pyqtSlot(str, str, result=str)
    def browse_selected_node_property_path(self, key: str, current_path: str) -> str:
        result = self._call_shell("browse_selected_node_property_path", key, current_path)
        return str(result or "")

    @pyqtSlot(str, bool)
    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self._call_shell("set_selected_port_exposed", key, exposed)

    @pyqtSlot(str, str, result=bool)
    def set_selected_port_label(self, key: str, label: str) -> bool:
        return bool(self._call_shell("set_selected_port_label", key, label))

    @pyqtSlot(bool)
    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self._call_shell("set_selected_node_collapsed", collapsed)

    @pyqtSlot(result=bool)
    def request_ungroup_selected_nodes(self) -> bool:
        return bool(self._call_shell("request_ungroup_selected_nodes"))

    @pyqtSlot(str, result=str)
    def request_add_selected_subnode_pin(self, direction: str) -> str:
        result = self._call_shell("request_add_selected_subnode_pin", direction)
        return str(result or "")

    @pyqtSlot(str, result=bool)
    def request_remove_selected_port(self, key: str) -> bool:
        return bool(self._call_shell("request_remove_selected_port", key))


__all__ = ["ShellInspectorBridge"]
