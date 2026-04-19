from __future__ import annotations

import copy
import re
from typing import Any

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID
from ea_node_editor.addons.hot_apply import apply_addon_enabled_state
from ea_node_editor.nodes.plugin_contracts import AddOnRecord
from ea_node_editor.nodes.plugin_loader import discover_addon_records
from ea_node_editor.persistence.serializer import JsonProjectSerializer

_VALID_TABS = ("about", "dependencies", "nodes", "changelog")
_VALID_FILTERS = ("all", "enabled", "disabled")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


def _canonical_token(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return _NON_ALNUM_RE.sub("", normalized)


def _normalized_filter(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _VALID_FILTERS:
        return normalized
    return "all"


def _normalized_tab(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _VALID_TABS:
        return normalized
    return "about"


def _status_label(record: AddOnRecord) -> str:
    if record.status == "pending_restart":
        return "Pending restart"
    if record.status == "disabled":
        return "Disabled"
    if record.status == "unavailable":
        return "Unavailable"
    return "Loaded"


def _policy_label(record: AddOnRecord) -> str:
    if record.apply_policy == "hot_apply":
        return "Hot apply"
    return "Requires restart"


def _policy_copy(record: AddOnRecord) -> str:
    if record.apply_policy == "hot_apply":
        return "Applies immediately to the live registry."
    return "Applies after the next COREX restart."


def _availability_copy(record: AddOnRecord) -> str:
    summary = str(record.availability.summary or "").strip()
    if summary:
        return summary
    if record.availability.missing_dependencies:
        return "Missing dependencies: " + ", ".join(record.availability.missing_dependencies)
    return "The add-on is available."


class AddOnManagerPresenter:
    def __init__(self) -> None:
        self._shell_window = None
        self._viewer_host_service = None
        self._records: tuple[AddOnRecord, ...] = ()
        self._selected_addon_id = ""
        self._active_tab = "about"
        self._status_filter = "all"
        self._last_error = ""
        self._request_serial = 0

    def bind(self, *, shell_window=None, viewer_host_service=None) -> None:  # noqa: ANN001
        self._shell_window = shell_window
        self._viewer_host_service = viewer_host_service

    @property
    def active_tab(self) -> str:
        return self._active_tab

    @property
    def status_filter(self) -> str:
        return self._status_filter

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def selected_addon_id(self) -> str:
        return self._selected_addon_id

    @property
    def request_serial(self) -> int:
        return self._request_serial

    @property
    def row_count(self) -> int:
        return len(self.filtered_rows())

    @property
    def pending_restart_count(self) -> int:
        return sum(1 for record in self._records if record.status == "pending_restart")

    @property
    def summary_text(self) -> str:
        loaded_count = sum(
            1 for record in self._records if record.state.enabled and record.availability.is_available
        )
        return f"{loaded_count} loaded / {len(self._records)} installed"

    @property
    def has_selection(self) -> bool:
        return self.selected_record() is not None

    def selected_record(self) -> AddOnRecord | None:
        for record in self._records:
            if record.addon_id == self._selected_addon_id:
                return record
        return None

    def filtered_rows(self) -> list[dict[str, Any]]:
        return [self._row_payload(record) for record in self._filtered_records()]

    def selected_payload(self) -> dict[str, Any]:
        record = self.selected_record()
        if record is None:
            return {}
        return self._detail_payload(record)

    def sync_request(self, *, open_: bool, focus_addon_id: str, request_serial: int) -> None:
        self._request_serial = int(request_serial)
        self.refresh(focus_addon_id=focus_addon_id if open_ else "")

    def refresh(
        self,
        *,
        focus_addon_id: str = "",
        preferences_document: Any = None,
    ) -> None:
        shell_window = self._shell_window
        if shell_window is None:
            self._records = ()
            self._selected_addon_id = ""
            return
        document = (
            shell_window.app_preferences_controller.document()
            if preferences_document is None
            else preferences_document
        )
        self._records = tuple(
            sorted(
                discover_addon_records(preferences_document=document),
                key=lambda record: (record.display_name.casefold(), record.addon_id.casefold()),
            )
        )
        normalized_focus = self._resolve_focus_addon_id(focus_addon_id)
        if normalized_focus:
            self._selected_addon_id = normalized_focus
            self._active_tab = "about"
        self._realign_selection()
        if self._last_error:
            self._last_error = ""

    def set_status_filter(self, filter_id: str) -> None:
        normalized = _normalized_filter(filter_id)
        if normalized == self._status_filter:
            return
        self._status_filter = normalized
        self._realign_selection()

    def set_active_tab(self, tab_id: str) -> None:
        self._active_tab = _normalized_tab(tab_id)

    def select_addon(self, addon_id: str) -> None:
        normalized = self._resolve_focus_addon_id(addon_id)
        if normalized:
            self._selected_addon_id = normalized
            return
        if any(record.addon_id == addon_id for record in self._records):
            self._selected_addon_id = str(addon_id)
            return
        self._realign_selection()

    def set_addon_enabled(self, addon_id: str, enabled: bool) -> bool:
        shell_window = self._shell_window
        if shell_window is None:
            return False
        normalized_addon_id = self._resolve_focus_addon_id(addon_id)
        if not normalized_addon_id:
            return False
        selected = next((record for record in self._records if record.addon_id == normalized_addon_id), None)
        if selected is None or not selected.availability.is_available:
            return False
        app_preferences_controller = shell_window.app_preferences_controller
        try:
            result = apply_addon_enabled_state(
                normalized_addon_id,
                enabled=bool(enabled),
                app_preferences_store=app_preferences_controller._store,
                preferences_document=app_preferences_controller.document(),
                graph_scene_bridge=shell_window.scene,
                viewer_host_service=self._viewer_host_service,
                on_registry_rebuilt=self._on_registry_rebuilt,
            )
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            return False
        app_preferences_controller._document = copy.deepcopy(result.preferences_document)
        if result.restart_required:
            shell_window.workspace_state_changed.emit()
        self.refresh(
            focus_addon_id=normalized_addon_id,
            preferences_document=result.preferences_document,
        )
        return True

    def open_workflow_settings(self) -> None:
        shell_window = self._shell_window
        if shell_window is None:
            return
        shell_window.project_session_controller.show_workflow_settings_dialog()

    def _filtered_records(self) -> list[AddOnRecord]:
        if self._status_filter == "enabled":
            return [record for record in self._records if record.state.enabled]
        if self._status_filter == "disabled":
            return [record for record in self._records if not record.state.enabled]
        return list(self._records)

    def _realign_selection(self) -> None:
        if not self._records:
            self._selected_addon_id = ""
            return
        visible_records = self._filtered_records()
        if any(record.addon_id == self._selected_addon_id for record in visible_records):
            return
        if visible_records:
            self._selected_addon_id = visible_records[0].addon_id
            return
        if any(record.addon_id == self._selected_addon_id for record in self._records):
            return
        self._selected_addon_id = self._records[0].addon_id

    def _resolve_focus_addon_id(self, addon_id: str) -> str:
        normalized = str(addon_id or "").strip()
        if not normalized:
            return ""
        for record in self._records:
            if record.addon_id == normalized:
                return record.addon_id
        aliases = {
            "ansys.dpf": ANSYS_DPF_ADDON_ID,
            "ansys_dpf": ANSYS_DPF_ADDON_ID,
        }
        if normalized in aliases:
            return aliases[normalized]
        requested_token = _canonical_token(normalized)
        if not requested_token:
            return ""
        for record in self._records:
            record_token = _canonical_token(record.addon_id)
            if record_token.endswith(requested_token) or requested_token.endswith(record_token):
                return record.addon_id
        return ""

    def _row_payload(self, record: AddOnRecord) -> dict[str, Any]:
        return {
            "addonId": record.addon_id,
            "displayName": record.display_name,
            "vendor": record.vendor,
            "version": record.version,
            "summary": record.summary,
            "enabled": bool(record.state.enabled),
            "status": record.status,
            "statusLabel": _status_label(record),
            "applyPolicy": record.apply_policy,
            "policyLabel": _policy_label(record),
            "pendingRestart": record.status == "pending_restart",
            "requiresRestart": record.apply_policy == "restart_required",
            "supportsHotApply": record.apply_policy == "hot_apply",
            "available": bool(record.availability.is_available),
            "unavailable": not record.availability.is_available,
            "selected": record.addon_id == self._selected_addon_id,
            "nodeCount": len(record.provided_node_type_ids),
        }

    def _detail_payload(self, record: AddOnRecord) -> dict[str, Any]:
        return {
            "addonId": record.addon_id,
            "displayName": record.display_name,
            "vendor": record.vendor,
            "version": record.version,
            "summary": record.summary,
            "details": record.details or record.summary,
            "enabled": bool(record.state.enabled),
            "status": record.status,
            "statusLabel": _status_label(record),
            "applyPolicy": record.apply_policy,
            "policyLabel": _policy_label(record),
            "policyCopy": _policy_copy(record),
            "pendingRestart": record.status == "pending_restart",
            "requiresRestart": record.apply_policy == "restart_required",
            "supportsHotApply": record.apply_policy == "hot_apply",
            "available": bool(record.availability.is_available),
            "unavailable": not record.availability.is_available,
            "availabilitySummary": _availability_copy(record),
            "dependencyItems": list(record.manifest.dependencies),
            "missingDependencies": list(record.availability.missing_dependencies),
            "providedNodeTypeIds": list(record.provided_node_type_ids),
            "nodeCount": len(record.provided_node_type_ids),
            "hasChangelog": False,
        }

    def _on_registry_rebuilt(self, rebuilt_registry) -> None:  # noqa: ANN001
        shell_window = self._shell_window
        if shell_window is None:
            return
        shell_window.registry = rebuilt_registry
        graph_interactions = getattr(shell_window, "graph_interactions", None)
        if graph_interactions is not None and hasattr(graph_interactions, "_registry"):
            graph_interactions._registry = rebuilt_registry
        serializer = JsonProjectSerializer(rebuilt_registry)
        shell_window.serializer = serializer
        session_store = getattr(shell_window, "session_store", None)
        if session_store is not None and hasattr(session_store, "_serializer"):
            session_store._serializer = serializer
        shell_window.node_library_changed.emit()
        shell_window.selected_node_changed.emit()
        shell_window.workspace_state_changed.emit()


__all__ = ["AddOnManagerPresenter"]
