# Purpose: Own a fullscreen tabular draft, virtual catalogue and cancellable preview lifecycle.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_session.py
from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
import threading
from typing import Any

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.addons.tabular_data.input_node import tabular_load_options_from_node_properties
from ea_node_editor.addons.tabular_data.operations import tabular_operation
from ea_node_editor.runtime_contracts.data_view import DataViewDefinition
from ea_node_editor.ui.tabular_preview_async import TabularPreviewWorkerPool
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider

CONFIG_KEYS = frozenset({"path", "data_view", "data_view_name", "data_view_migration_notice", "delimiter", "encoding",
                         "header_row", "skip_rows", "schema_hints", "cache_policy", "project_managed_source",
                         "project_managed_cache", "allow_npz_archive_preview"})


def _configuration(properties: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy({key: value for key, value in properties.items() if key in CONFIG_KEYS})


def _qml_definition(value):
    """QML Number(text) creates doubles even for integer-only recipe fields."""
    if isinstance(value, float) and value.is_integer() and abs(value) <= 2**53:
        return int(value)
    if isinstance(value, Mapping):
        return {key: _qml_definition(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_qml_definition(item) for item in value]
    return value


class TabularCatalogueModel(QAbstractListModel):
    changed = pyqtSignal()
    _ROLES = ("object_id", "display_name", "kind", "shape_text", "dtype", "size_text", "supported")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: list[dict[str, Any]] = []
        self._visible: list[dict[str, Any]] = []
        self._filter = ""
        self._show_metadata = False

    def roleNames(self):
        return {int(Qt.ItemDataRole.UserRole) + index: name.encode() for index, name in enumerate(self._ROLES)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._visible)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._visible):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self._visible[index.row()]["display_name"]
        position = int(role) - int(Qt.ItemDataRole.UserRole)
        return self._visible[index.row()].get(self._ROLES[position]) if 0 <= position < len(self._ROLES) else None

    @pyqtProperty(int, notify=changed)
    def total(self):
        return len(self.items)

    @pyqtProperty(int, notify=changed)
    def matched(self):
        return len(self._visible)

    def replace(self, items):
        self.items = []
        for source in items:
            item = copy.deepcopy(source)
            shape = item.get("shape") or ([item.get("row_count"), item.get("column_count")] if item.get("kind") == "table" else [])
            item["shape_text"] = " × ".join("?" if size is None else f"{size:,}" for size in shape)
            metadata = item.get("metadata", {})
            size = metadata.get("nbytes", metadata.get("uncompressed_bytes", 0))
            item["size_text"] = f"{size / 1024 / 1024:.1f} MiB" if size else ""
            item["supported"] = metadata.get("supported", True)
            self.items.append(item)
        self._refilter()

    @pyqtSlot(str)
    def search(self, text):
        self._filter = text.casefold().strip()
        self._refilter()

    @pyqtSlot(bool)
    def show_metadata(self, visible):
        self._show_metadata = visible
        self._refilter()

    def _refilter(self):
        self.beginResetModel()
        self._visible = [item for item in self.items if (self._show_metadata or not item["object_id"].startswith("__"))
                         and self._filter in item["object_id"].casefold()]
        self.endResetModel()
        self.changed.emit()


class TabularComposerSession(QObject):
    changed = pyqtSignal()
    applied = pyqtSignal()
    close_ready = pyqtSignal()
    close_cancelled = pyqtSignal()

    def __init__(self, parent=None, *, read_properties: Callable[[], Mapping[str, Any] | None],
                 apply_properties: Callable[[dict[str, Any]], bool], project_context: Callable[[], Any],
                 choose_source: Callable[[str], str] | None = None,
                 stage_source: Callable[[str], str] | None = None,
                 discard_source: Callable[[str], None] | None = None,
                 choose_export: Callable[[str, str, str], str] | None = None,
                 provider_factory: Callable[..., TabularPreviewProvider] = TabularPreviewProvider):
        super().__init__(parent)
        self._read_properties = read_properties
        self._apply_properties = apply_properties
        self._project_context = project_context
        self._choose_source = choose_source
        self._stage_source = stage_source
        self._discard_source = discard_source
        self._choose_export = choose_export
        self._provider_factory = provider_factory
        self._catalogue = TabularCatalogueModel(self)
        self._members = TabularCatalogueModel(self)
        self._members.show_metadata(True)
        self._pool = TabularPreviewWorkerPool(self)
        self._pool.job_finished.connect(self._finished)
        self._baseline: dict[str, Any] = {}
        self._draft: dict[str, Any] = {}
        self._preview: dict[str, Any] = {}
        self._schema: list[dict[str, Any]] = []
        self._pending: dict[str, dict[str, Any]] = {}
        self._generation = 0
        self._cancel = threading.Event()
        self._active = False
        self._busy = False
        self._valid = False
        self._conflict = False
        self._close_pending = False
        self._managed_copy = False
        self._error = ""
        self._applying = False
        self._source_stamp = None
        self._preview_axes = {"row": 0, "column": 1, "fixed": {}}
        self._suggestion = ""
        self._export_cancel = threading.Event()
        self._export_busy = False
        self._export_counter = 0
        self._export_status = ""
        self._export_result: dict[str, Any] = {}
        self._preview_request = {"row_offset": 0, "row_limit": 50, "column_offset": 0, "column_limit": 50}

    @pyqtProperty(QObject, constant=True)
    def catalogue(self):
        return self._catalogue

    @pyqtProperty(QObject, constant=True)
    def members(self):
        return self._members

    @pyqtSlot(str, result="QVariantMap")
    def member_details(self, member):
        if not member and len(self._catalogue.items) == 1:
            return copy.deepcopy(self._catalogue.items[0])
        return copy.deepcopy(next((item for item in self._catalogue.items if item["object_id"] == member), {}))

    @pyqtProperty("QVariantMap", notify=changed)
    def state(self):
        return {"draft": copy.deepcopy(self._draft), "preview": copy.deepcopy(self._preview), "schema": copy.deepcopy(self._schema),
                "dirty": self.dirty, "busy": self._busy, "valid": self._valid, "conflict": self._conflict,
                "close_pending": self._close_pending, "error": self._error, "managed_copy": self._managed_copy,
                "source_name": Path(str(self._draft.get("path", ""))).name,
                "preview_axes": copy.deepcopy(self._preview_axes), "suggestion": self._suggestion,
                "preview_request": copy.deepcopy(self._preview_request),
                "export_busy": self._export_busy, "export_status": self._export_status,
                "export_result": copy.deepcopy(self._export_result)}

    @property
    def dirty(self):
        return self._managed_copy or self._draft != self._baseline

    @property
    def active(self):
        return self._active

    def begin(self, properties: Mapping[str, Any]):
        self._export_cancel.set()
        self._export_counter += 1
        self._export_busy = False
        self._export_status = ""
        self._export_result = {}
        self._active = True
        self._baseline = _configuration(properties)
        self._draft = copy.deepcopy(self._baseline)
        self._reset_preview_window()
        self._conflict = self._close_pending = self._managed_copy = False
        self._preview_axes = {"row": 0, "column": 1, "fixed": {}}
        self._schedule()

    @pyqtSlot("QVariantMap")
    def update_definition(self, definition):
        self.edit_property("data_view", _qml_definition(definition))

    @pyqtSlot(str, "QVariant")
    def edit_property(self, key, value):
        if not self._active or key not in CONFIG_KEYS:
            return
        if self._draft.get(key) == value:
            return
        self._draft[key] = copy.deepcopy(value)
        if key in {"data_view_name", "data_view_migration_notice"}:
            self.changed.emit()
        else:
            self._reset_preview_window()
            self._schedule()

    @pyqtSlot(str, bool)
    def set_source(self, path, managed_copy=False):
        if not self._active:
            return
        self._draft["path"] = path
        self._preview_axes = {"row": 0, "column": 1, "fixed": {}}
        self._draft["data_view"] = {"version": 1, "mode": "source"}
        self._draft["data_view_migration_notice"] = {}
        self._managed_copy = managed_copy
        self._reset_preview_window()
        self._catalogue.replace([])
        self._schedule()

    @pyqtSlot(bool)
    def browse_source(self, managed_copy=False):
        if self._choose_source is None:
            self._error = "Source browsing is unavailable."
            self.changed.emit()
            return
        chosen = self._choose_source(str(self._draft.get("path", "")))
        if chosen:
            self.set_source(chosen, managed_copy)

    @pyqtSlot(str)
    def select_member(self, member):
        item = next((item for item in self._catalogue.items if item["object_id"] == member), None)
        if item is None or not item["supported"]:
            return
        self.update_definition({"version": 1, "mode": "source", "member": member})

    @pyqtSlot("QVariantMap")
    def request_preview(self, request):
        self._preview_request = copy.deepcopy(request)
        self._schedule()

    @pyqtSlot("QVariantMap")
    def set_preview_axes(self, axes):
        self._preview_axes = copy.deepcopy(axes)
        self._reset_preview_window()
        self._schedule()

    def _reset_preview_window(self):
        self._preview_request = {"row_offset": 0, "row_limit": 50, "column_offset": 0, "column_limit": 50}

    @pyqtSlot()
    def suggest_mapping(self):
        import numpy as np

        view = DataViewDefinition(self._draft.get("data_view")).to_payload()
        if view["mode"] != "table":
            view.update(mode="table", array_slices=[], segments=[{"blocks": [{"member": view["member"]}]}])
            view = DataViewDefinition(view).to_payload()
        assigned = 0
        for segment in view["segments"]:
            for block in segment["blocks"]:
                shape = self.member_details(block["member"]).get("shape", [])
                if len(shape) < 2:
                    continue
                axes = block["axes"]
                if axes["row"] >= len(shape) or axes["column"] is None or axes["column"] >= len(shape):
                    continue
                label_candidates, row_candidates = [], []
                for member in self._catalogue.items:
                    if len(member.get("shape", [])) != 1 or not member["supported"]:
                        continue
                    try:
                        kind = np.dtype(member["dtype"]).kind
                    except TypeError:
                        continue
                    if kind in "US" and member["shape"][0] == shape[axes["column"]]:
                        label_candidates.append(member["object_id"])
                    if kind in "iufM" and member["shape"][0] == shape[axes["row"]]:
                        row_candidates.append(member["object_id"])
                if not block["labels_member"] and len(label_candidates) == 1:
                    block["labels_member"] = label_candidates[0]
                    assigned += 1
                if segment["coordinate"] is None and len(row_candidates) == 1:
                    member = row_candidates[0]
                    segment["coordinate"] = {"member": member, "name": member, "column": None, "unit": ""}
                    assigned += 1
        self._suggestion = f"Suggested {assigned} mapping(s). Review them before applying." if assigned else "No unambiguous mapping found; choose coordinates and labels explicitly."
        self.update_definition(view)
        self.changed.emit()

    def _schedule(self):
        self._cancel.set()
        self._cancel = threading.Event()
        self._generation += 1
        generation = self._generation
        self._preview = {"state": "loading", "message": "Preparing the configured data…"}
        self._schema = []
        self._valid = False
        self._busy = True
        self._error = ""
        self._source_stamp = None
        self.changed.emit()
        properties = copy.deepcopy(self._draft)
        context = copy.deepcopy(self._project_context())
        request = copy.deepcopy(self._preview_request)
        axes = copy.deepcopy(self._preview_axes)
        cancel = self._cancel
        key = str(generation)
        result: dict[str, Any] = {}
        self._pending[key] = result

        def work():
            with tabular_operation(cancel):
                provider = self._provider_factory(project_context_provider=lambda: context)
                selector = provider.describe_selector(properties)
                resolved = selector.get("source", {}).get("resolved_path", "")
                source = Path(resolved) if resolved else None
                before = source.stat() if source is not None and source.is_file() else None
                result["objects"] = selector.get("selector", {}).get("objects", [])
                from ea_node_editor.ui.tabular_composer_preview import describe_raw_plane
                preview = describe_raw_plane(provider, properties, request, axes)
                if preview is None:
                    preview = provider.describe_preview(properties, request, mode="fullscreen")
                schema = preview.get("schema", {}).get("columns", [])
                if preview.get("preview_kind") == "table":
                    from ea_node_editor.runtime_contracts import TabularDataRef
                    ref = TabularDataRef.from_payload(preview.get("ref", {}))
                    if ref is not None:
                        schema = [column.to_payload() for column in provider._service_factory().configuration_schema(ref).columns]
                result["schema"] = schema
                preview.pop("selector", None)
                result["preview"] = preview
                if before is not None:
                    after = source.stat()
                    if (after.st_mtime_ns, after.st_size) != (before.st_mtime_ns, before.st_size):
                        raise ValueError("Source changed while preparing the preview. Refresh it before applying.")
                    result["source_stamp"] = (str(source), after.st_mtime_ns, after.st_size)
        self._pool.schedule(key, work)

    def _finished(self, key, error):
        result = self._pending.pop(key, {})
        if key.startswith("export:"):
            if self._active and key == f"export:{self._export_counter}":
                self._export_busy = False
                self._export_result = result.get("export", {})
                self._export_status = error or f"Exported {self._export_result.get('rows', 0):,} rows."
                self.changed.emit()
            return
        if not self._active or key != str(self._generation):
            return
        self._busy = False
        if "objects" in result:
            self._catalogue.replace(result["objects"])
            self._members.replace(result["objects"])
        self._preview = result.get("preview", {"state": "error", "message": error or "Data preview unavailable"})
        self._schema = result.get("schema", [])
        self._error = error or self._preview.get("error", {}).get("message", "")
        self._valid = self._preview.get("state") in {"ready", "array_axes_required"} and not self._conflict and not error
        self._source_stamp = result.get("source_stamp")
        self.changed.emit()

    def observe(self, properties: Mapping[str, Any] | None):
        if not self._active or self._applying:
            return
        if properties is None:
            self.retire()
            return
        current = _configuration(properties)
        if current != self._baseline:
            self._conflict = True
            self._valid = False
            self._error = "This node's configuration changed elsewhere. Reload the current configuration."
            self.changed.emit()

    @pyqtSlot()
    def reload_current(self):
        current = self._read_properties()
        if current is not None:
            self.begin(current)

    @pyqtSlot(result=bool)
    def apply(self):
        if not self._active or self._busy or self._export_busy or not self._valid:
            return False
        self.observe(self._read_properties())
        if not self._active or self._conflict:
            return False
        staged = ""
        try:
            if self._source_stamp is not None:
                path, mtime, size = self._source_stamp
                stamp = Path(path).stat()
                if (stamp.st_mtime_ns, stamp.st_size) != (mtime, size):
                    raise ValueError("Source changed since this preview. Refresh it before applying.")
            DataViewDefinition(self._draft.get("data_view"))
            updates = {key: copy.deepcopy(value) for key, value in self._draft.items() if value != self._baseline.get(key)}
            if self._managed_copy:
                if self._stage_source is None:
                    raise ValueError("Project-managed source import is unavailable")
                staged = self._stage_source(str(self._draft.get("path", "")))
                if not staged:
                    raise ValueError("The source could not be imported; the current node is unchanged")
                updates["path"] = staged
            self._applying = True
            if updates and not self._apply_properties(updates):
                raise ValueError("The node could not accept this configuration")
            self._baseline = _configuration(self._read_properties() or self._draft)
            self._draft = copy.deepcopy(self._baseline)
            self._managed_copy = self._close_pending = False
            self.changed.emit()
            self.applied.emit()
            return True
        except Exception as exc:
            if staged and self._discard_source is not None and (self._read_properties() or {}).get("path") != staged:
                try:
                    self._discard_source(staged)
                except Exception as cleanup_error:
                    self._error = f"{exc}; temporary source cleanup failed: {cleanup_error}"
                    self.changed.emit()
                    return False
            self._error = str(exc)
            self.changed.emit()
            return False
        finally:
            self._applying = False

    @pyqtSlot()
    def request_close(self):
        if self.dirty or self._export_busy:
            self._close_pending = True
            self.changed.emit()
        else:
            self.close_ready.emit()

    @pyqtSlot()
    def keep_editing(self):
        self._close_pending = False
        self.changed.emit()
        self.close_cancelled.emit()

    @pyqtSlot()
    def discard(self):
        self._draft = copy.deepcopy(self._baseline)
        self._managed_copy = self._close_pending = False
        self.close_ready.emit()

    @pyqtSlot()
    def dismiss_notice(self):
        self.edit_property("data_view_migration_notice", {})

    @pyqtSlot()
    def refresh(self):
        if self._active:
            self._schedule()

    @pyqtSlot(str)
    def copy_text(self, text):
        from PyQt6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    @pyqtSlot(str, "QVariantMap", result=bool)
    def export_data(self, scope, selection):
        if not self._active or not self._valid or self._busy or self._export_busy:
            return False
        if self._choose_export is None:
            self._export_status = "Export destination browsing is unavailable."
            self.changed.emit()
            return False
        kind = self._preview.get("preview_kind", "table")
        name = Path(str(self._draft.get("path", "data"))).stem + "-" + scope
        suffix = ".npy" if kind == "array" and scope == "output" else ".csv"
        chosen = self._choose_export(scope, kind, name + suffix)
        if not chosen:
            return False
        properties, context, preview = copy.deepcopy(self._draft), copy.deepcopy(self._project_context()), copy.deepcopy(self._preview)
        selection = copy.deepcopy(selection)
        self._export_counter += 1
        self._export_cancel = threading.Event()
        cancel = self._export_cancel
        key = f"export:{self._export_counter}"
        result: dict[str, Any] = {}
        self._pending[key] = result
        self._export_busy = True
        self._export_status = "Exporting draft data..." if self.dirty else "Exporting configured data..."
        self.changed.emit()

        def work():
            from ea_node_editor.ui.tabular_composer_export import export_composer_data
            with tabular_operation(cancel):
                result["export"] = export_composer_data(properties=properties, project_context=context, preview=preview,
                                                         scope=scope, selection=selection, output_path=Path(chosen))
        self._pool.schedule(key, work)
        return True

    @pyqtSlot()
    def cancel_export(self):
        self._export_cancel.set()

    @pyqtSlot()
    def use_previous_selection(self):
        previous = self._draft.get("data_view_migration_notice", {}).get("previous_selection", {})
        view = DataViewDefinition(self._draft.get("data_view")).to_payload()
        bounds = previous.get("array_slice_2d", {})
        preview = self._preview
        if preview.get("preview_kind") == "array":
            shape = preview.get("array", {}).get("shape", [])
            view["mode"] = "array"
            view["array_slices"] = [[int(bounds.get("row_offset", 0)), int(bounds.get("row_limit", 0))]]
            if len(shape) > 1:
                view["array_slices"].append([int(bounds.get("column_offset", 0)), int(bounds.get("column_limit", 0))])
            view["array_slices"].extend([[0, 0] for _ in shape[2:]])
        else:
            view["output"] = {"row_offset": int(bounds.get("row_offset", 0)), "row_limit": int(bounds.get("row_limit", 0)),
                              "columns": previous.get("tabular_selected_columns", [])}
        self._draft["data_view_migration_notice"] = {}
        self.update_definition(view)

    def retire(self):
        self._active = False
        self._cancel.set()
        self._export_cancel.set()
        self._export_busy = False
        self._generation += 1
        self._busy = self._valid = False
        self._pending.clear()
        self.changed.emit()

    def shutdown(self):
        self.retire()
        self._pool.shutdown()


__all__ = ["TabularComposerSession", "TabularCatalogueModel", "CONFIG_KEYS"]
