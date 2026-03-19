from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _source_attr(source: object | None, name: str, default: Any) -> Any:
    if source is None:
        return default
    return getattr(source, name, default)


def _invoke(source: object | None, name: str, *args, default: Any = None) -> Any:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return default
    return callback(*args)


def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
    signal = getattr(source, name, None) if source is not None else None
    if signal is not None and hasattr(signal, "connect"):
        signal.connect(slot)


def _has_signal(source: object | None, name: str) -> bool:
    signal = getattr(source, name, None) if source is not None else None
    return bool(signal is not None and hasattr(signal, "connect"))


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
        self._inspector_source = getattr(shell_window, "shell_inspector_presenter", shell_window)

        _connect_signal(self._inspector_source, "selected_node_changed", self._on_selected_node_changed)
        _connect_signal(self._inspector_source, "workspace_state_changed", self._on_workspace_state_changed)
        if _has_signal(self._inspector_source, "inspector_state_changed"):
            _connect_signal(self._inspector_source, "inspector_state_changed", self.inspector_state_changed.emit)

    def _on_selected_node_changed(self) -> None:
        self.selected_node_changed.emit()
        if not _has_signal(self._inspector_source, "inspector_state_changed"):
            self.inspector_state_changed.emit()

    def _on_workspace_state_changed(self) -> None:
        self.workspace_state_changed.emit()
        if not _has_signal(self._inspector_source, "inspector_state_changed"):
            self.inspector_state_changed.emit()

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_title(self) -> str:
        return str(_source_attr(self._inspector_source, "selected_node_title", ""))

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_subtitle(self) -> str:
        return str(_source_attr(self._inspector_source, "selected_node_subtitle", ""))

    @pyqtProperty(str, notify=inspector_state_changed)
    def selected_node_summary(self) -> str:
        return str(_source_attr(self._inspector_source, "selected_node_summary", ""))

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_header_items(self) -> list[dict[str, str]]:
        return _copy_list(_source_attr(self._inspector_source, "selected_node_header_items", []))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def has_selected_node(self) -> bool:
        return bool(_source_attr(self._inspector_source, "has_selected_node", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_collapsible(self) -> bool:
        return bool(_source_attr(self._inspector_source, "selected_node_collapsible", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_collapsed(self) -> bool:
        return bool(_source_attr(self._inspector_source, "selected_node_collapsed", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_is_subnode_pin(self) -> bool:
        return bool(_source_attr(self._inspector_source, "selected_node_is_subnode_pin", False))

    @pyqtProperty(bool, notify=inspector_state_changed)
    def selected_node_is_subnode_shell(self) -> bool:
        return bool(_source_attr(self._inspector_source, "selected_node_is_subnode_shell", False))

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_property_items(self) -> list[dict]:
        return _copy_list(_source_attr(self._inspector_source, "selected_node_property_items", []))

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def selected_node_port_items(self) -> list[dict]:
        return _copy_list(_source_attr(self._inspector_source, "selected_node_port_items", []))

    @pyqtProperty("QVariantList", notify=inspector_state_changed)
    def pin_data_type_options(self) -> list[str]:
        return _copy_list(_source_attr(self._inspector_source, "pin_data_type_options", []))

    @pyqtSlot(str, "QVariant")
    def set_selected_node_property(self, key: str, value) -> None:
        _invoke(self._inspector_source, "set_selected_node_property", key, value)

    @pyqtSlot(str, str, result=str)
    def browse_selected_node_property_path(self, key: str, current_path: str) -> str:
        return str(
            _invoke(
                self._inspector_source,
                "browse_selected_node_property_path",
                key,
                current_path,
                default="",
            )
            or ""
        )

    @pyqtSlot(str, bool)
    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        _invoke(self._inspector_source, "set_selected_port_exposed", key, exposed)

    @pyqtSlot(str, str, result=bool)
    def set_selected_port_label(self, key: str, label: str) -> bool:
        return bool(_invoke(self._inspector_source, "set_selected_port_label", key, label, default=False))

    @pyqtSlot(bool)
    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        _invoke(self._inspector_source, "set_selected_node_collapsed", collapsed)

    @pyqtSlot(result=bool)
    def request_ungroup_selected_nodes(self) -> bool:
        return bool(_invoke(self._inspector_source, "request_ungroup_selected_nodes", default=False))

    @pyqtSlot(str, result=str)
    def request_add_selected_subnode_pin(self, direction: str) -> str:
        return str(
            _invoke(self._inspector_source, "request_add_selected_subnode_pin", direction, default="") or ""
        )

    @pyqtSlot(str, result=bool)
    def request_remove_selected_port(self, key: str) -> bool:
        return bool(_invoke(self._inspector_source, "request_remove_selected_port", key, default=False))


__all__ = ["ShellInspectorBridge"]
