from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtQml import qmlRegisterType

from ea_node_editor.ui.shell.presenters.addon_manager_presenter import AddOnManagerPresenter

_QML_IMPORT_NAME = "EA.NodeEditor"
_QML_IMPORT_MAJOR_VERSION = 1
_QML_IMPORT_MINOR_VERSION = 0
_QML_TYPE_NAME = "ShellAddOnManagerBridge"
_QML_REGISTERED = False


class ShellAddOnManagerBridge(QObject):
    request_bridge_changed = pyqtSignal()
    workspace_bridge_changed = pyqtSignal()
    viewer_host_service_changed = pyqtSignal()
    state_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("shellAddOnManagerBridge")
        self._presenter = AddOnManagerPresenter()
        self._request_bridge = None
        self._workspace_bridge = None
        self._viewer_host_service = None

    @pyqtProperty(QObject, notify=request_bridge_changed)
    def requestBridge(self) -> QObject | None:  # noqa: N802
        return self._request_bridge

    @requestBridge.setter
    def requestBridge(self, bridge: QObject | None) -> None:  # noqa: N802
        if self._request_bridge is bridge:
            return
        previous = self._request_bridge
        if previous is not None:
            try:
                previous.state_changed.disconnect(self._on_request_state_changed)
            except (AttributeError, TypeError):
                pass
        self._request_bridge = bridge
        if bridge is not None:
            try:
                bridge.state_changed.connect(self._on_request_state_changed)
            except AttributeError:
                pass
        self._sync_presenter_bindings()
        self.request_bridge_changed.emit()
        self._refresh_from_request()

    @pyqtProperty(QObject, notify=workspace_bridge_changed)
    def workspaceBridge(self) -> QObject | None:  # noqa: N802
        return self._workspace_bridge

    @workspaceBridge.setter
    def workspaceBridge(self, bridge: QObject | None) -> None:  # noqa: N802
        if self._workspace_bridge is bridge:
            return
        self._workspace_bridge = bridge
        self._sync_presenter_bindings()
        self.workspace_bridge_changed.emit()
        self._refresh_from_request()

    @pyqtProperty(QObject, notify=viewer_host_service_changed)
    def viewerHostServiceRef(self) -> QObject | None:  # noqa: N802
        return self._viewer_host_service

    @viewerHostServiceRef.setter
    def viewerHostServiceRef(self, service: QObject | None) -> None:  # noqa: N802
        if self._viewer_host_service is service:
            return
        self._viewer_host_service = service
        self._sync_presenter_bindings()
        self.viewer_host_service_changed.emit()
        self.state_changed.emit()

    @pyqtProperty(bool, notify=state_changed)
    def hasSelection(self) -> bool:  # noqa: N802
        return self._presenter.has_selection

    @pyqtProperty(str, notify=state_changed)
    def selectedAddonId(self) -> str:  # noqa: N802
        return self._presenter.selected_addon_id

    @pyqtProperty(int, notify=state_changed)
    def requestSerial(self) -> int:  # noqa: N802
        return self._presenter.request_serial

    @pyqtProperty(str, notify=state_changed)
    def activeTab(self) -> str:  # noqa: N802
        return self._presenter.active_tab

    @pyqtProperty(str, notify=state_changed)
    def statusFilter(self) -> str:  # noqa: N802
        return self._presenter.status_filter

    @pyqtProperty(int, notify=state_changed)
    def rowCount(self) -> int:  # noqa: N802
        return self._presenter.row_count

    @pyqtProperty(int, notify=state_changed)
    def pendingRestartCount(self) -> int:  # noqa: N802
        return self._presenter.pending_restart_count

    @pyqtProperty(str, notify=state_changed)
    def summaryText(self) -> str:  # noqa: N802
        return self._presenter.summary_text

    @pyqtProperty(str, notify=state_changed)
    def lastError(self) -> str:  # noqa: N802
        return self._presenter.last_error

    @pyqtProperty("QVariantList", notify=state_changed)
    def filteredRows(self) -> list[dict]:  # noqa: N802
        return self._presenter.filtered_rows()

    @pyqtProperty("QVariantMap", notify=state_changed)
    def selectedAddon(self) -> dict:  # noqa: N802
        return self._presenter.selected_payload()

    @pyqtSlot()
    def refresh(self) -> None:
        self._refresh_from_request()

    @pyqtSlot(str)
    def setActiveTab(self, tab_id: str) -> None:  # noqa: N802
        self._presenter.set_active_tab(tab_id)
        self.state_changed.emit()

    @pyqtSlot(str)
    def setStatusFilter(self, filter_id: str) -> None:  # noqa: N802
        self._presenter.set_status_filter(filter_id)
        self.state_changed.emit()

    @pyqtSlot(str)
    def selectAddon(self, addon_id: str) -> None:  # noqa: N802
        self._presenter.select_addon(addon_id)
        self.state_changed.emit()

    @pyqtSlot(str, bool, result=bool)
    def setAddonEnabled(self, addon_id: str, enabled: bool) -> bool:  # noqa: N802
        applied = self._presenter.set_addon_enabled(addon_id, enabled)
        self.state_changed.emit()
        return applied

    @pyqtSlot(result=bool)
    def toggleSelectedAddon(self) -> bool:  # noqa: N802
        selected = self._presenter.selected_payload()
        addon_id = str(selected.get("addonId", "")).strip()
        if not addon_id:
            return False
        enabled = bool(selected.get("enabled"))
        return self.setAddonEnabled(addon_id, not enabled)

    @pyqtSlot()
    def requestOpenWorkflowSettings(self) -> None:  # noqa: N802
        self._presenter.open_workflow_settings()
        self.state_changed.emit()

    @pyqtSlot()
    def requestClose(self) -> None:  # noqa: N802
        bridge = self._request_bridge
        if bridge is not None and hasattr(bridge, "requestClose"):
            bridge.requestClose()

    def _shell_window(self):
        bridge = self._workspace_bridge
        if bridge is not None:
            shell_window = getattr(bridge, "shell_window", None)
            if shell_window is not None:
                return shell_window
        return None

    def _sync_presenter_bindings(self) -> None:
        self._presenter.bind(
            shell_window=self._shell_window(),
            viewer_host_service=self._viewer_host_service,
        )

    def _refresh_from_request(self) -> None:
        bridge = self._request_bridge
        if bridge is None:
            self._presenter.refresh()
            self.state_changed.emit()
            return
        self._presenter.sync_request(
            open_=bool(getattr(bridge, "open", False)),
            focus_addon_id=str(getattr(bridge, "focusAddonId", "") or ""),
            request_serial=int(getattr(bridge, "requestSerial", 0) or 0),
        )
        self.state_changed.emit()

    @pyqtSlot()
    def _on_request_state_changed(self) -> None:
        self._refresh_from_request()


def register_qml_types() -> None:
    global _QML_REGISTERED
    if _QML_REGISTERED:
        return
    qmlRegisterType(
        ShellAddOnManagerBridge,
        _QML_IMPORT_NAME,
        _QML_IMPORT_MAJOR_VERSION,
        _QML_IMPORT_MINOR_VERSION,
        _QML_TYPE_NAME,
    )
    _QML_REGISTERED = True


__all__ = ["ShellAddOnManagerBridge", "register_qml_types"]
