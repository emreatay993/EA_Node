# Purpose: Own source-authoritative Python Script drafts, authoring assistance, and local history.
# Map: subsystems/qml_shell_and_bridges.md
# Tests: tests/test_script_editor_authoring_model.py, tests/test_script_editor_dock.py
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.nodes.python_script_authoring import (
    AuthoringAnalysis, SourceEditResult, analyze_source, edit_source,
)
from ea_node_editor.ui.support.python_script_authoring import (
    completions, decorator_choices, field_choices, type_choices,
)


def _variant(value: Any) -> Any:
    """Expose only ordinary QVariant-compatible values to QML."""
    if isinstance(value, dict):
        return {str(key): _variant(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_variant(item) for item in value]
    return value


def _qt_offset(source: str, offset: int) -> int:
    return len(source[:offset].encode("utf-16-le")) // 2


def _python_offset(source: str, offset: int) -> int:
    return len(source.encode("utf-16-le")[:max(0, offset) * 2].decode("utf-16-le", errors="ignore"))


@dataclass
class _DocumentState:
    source: str
    identities: dict[str, int] = field(default_factory=dict)
    selected_key: str = ""


@dataclass
class _Draft:
    baseline: str
    state: _DocumentState
    baseline_identities: dict[str, int]
    undo: list[_DocumentState] = field(default_factory=list)
    redo: list[_DocumentState] = field(default_factory=list)


class ScriptEditorModel(QObject):
    visibility_changed = pyqtSignal()
    node_changed = pyqtSignal()
    content_changed = pyqtSignal()
    cursor_changed = pyqtSignal()
    dirty_changed = pyqtSignal()
    focus_changed = pyqtSignal()
    width_changed = pyqtSignal()
    authoring_changed = pyqtSignal()
    history_changed = pyqtSignal()
    rename_review_changed = pyqtSignal()
    preview_bridge_changed = pyqtSignal()
    form_flush_requested = pyqtSignal()
    form_discard_requested = pyqtSignal()
    form_owner_changed = pyqtSignal()
    selection_range_requested = pyqtSignal(int, int)
    script_apply_requested = pyqtSignal(str, str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._visible = False
        self._floating = False
        self._panel_width = 0.0
        self._current_node_id = ""
        self._current_node_label = ""
        self._node = None
        self._base_script = ""
        self._script_text = ""
        self._dirty = False
        self._cursor_label = "Ln 1, Col 1 | Sel 0 | Pos 0"
        self._has_focus = False
        self._source_revision = 0
        self._next_identity = 0
        self._drafts: dict[tuple[Any, ...], _Draft] = {}
        self._draft: _Draft | None = None
        self._context_key: tuple[Any, ...] = ()
        self._context_provider: Callable[[], tuple[Any, Any, Any]] | None = None
        self._project_identity = None
        self._prepare_callback = None
        self._apply_callback = None
        self._error_callback = None
        self._analysis = AuthoringAnalysis()
        self._analysis_status = "unavailable"
        self._operation_error = ""
        self._rename_result: SourceEditResult | None = None
        self._rename_review: dict[str, Any] = {}
        self._completion: dict[str, Any] = {}
        self._prepared = None
        self._apply_impact: dict[str, Any] = {}
        self._preview_bridge = None
        self._form_states: dict[QObject, tuple[bool, str]] = {}
        self._flushing_forms = False
        self._editing_form = False
        self._form_owner = None
        self._form_buffers: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._analysis_timer = QTimer(self)
        self._analysis_timer.setSingleShot(True)
        self._analysis_timer.setInterval(300)
        self._analysis_timer.timeout.connect(self.analyze_now)

    def configure_authoring(self, *, context_provider, prepare, apply, report_error=None) -> None:
        """Bind shell services; the model never commits graph records itself.

        context_provider returns the current (project, workspace, registry).
        Keeping the project object alive prevents object-ID reuse between loads.
        """
        self._context_provider = context_provider
        self._prepare_callback = prepare
        self._apply_callback = apply
        self._error_callback = report_error
        if self._preview_bridge is None:
            from ea_node_editor.ui_qml.python_script_preview import PythonScriptPreview
            self.set_preview_bridge(PythonScriptPreview(self))

    @property
    def registry(self):
        return self._context_provider()[2] if self._context_provider else None

    @property
    def catalog(self):
        registry = self.registry
        return registry.data_types if registry is not None else None

    @property
    def current_node(self):
        return copy.deepcopy(self._node)

    @property
    def analysis(self) -> AuthoringAnalysis:
        return self._analysis

    @property
    def renamed_keys(self) -> dict[str, str]:
        if self._draft is None:
            return {}
        current = {identity: key for key, identity in self._draft.state.identities.items()}
        return {old: current[identity] for old, identity in self._draft.baseline_identities.items()
                if identity in current and old != current[identity]}

    @pyqtProperty(bool, notify=visibility_changed)
    def visible(self) -> bool:
        return self._visible

    @pyqtProperty(bool, notify=visibility_changed)
    def floating(self) -> bool:
        return self._floating

    @pyqtProperty(float, notify=width_changed)
    def panel_width(self) -> float:
        return self._panel_width

    @pyqtProperty(str, notify=node_changed)
    def current_node_id(self) -> str:
        return self._current_node_id

    @pyqtProperty(str, notify=node_changed)
    def current_node_label(self) -> str:
        return self._current_node_label

    @pyqtProperty(str, notify=content_changed)
    def script_text(self) -> str:
        return self._script_text

    @pyqtProperty(bool, notify=dirty_changed)
    def dirty(self) -> bool:
        return self._dirty

    @pyqtProperty(str, notify=cursor_changed)
    def cursor_label(self) -> str:
        return self._cursor_label

    @pyqtProperty(bool, notify=focus_changed)
    def has_focus(self) -> bool:
        return self._has_focus

    @pyqtProperty(int, notify=authoring_changed)
    def source_revision(self) -> int:
        return self._source_revision

    @pyqtProperty(str, notify=authoring_changed)
    def analysis_status(self) -> str:
        return self._analysis_status

    @pyqtProperty(str, notify=authoring_changed)
    def operation_error(self) -> str:
        return self._operation_error

    @pyqtProperty(bool, notify=authoring_changed)
    def can_synchronize(self) -> bool:
        return self._analysis.can_synchronize

    @pyqtProperty(bool, notify=history_changed)
    def can_undo(self) -> bool:
        return bool(self._draft and self._draft.undo)

    @pyqtProperty(bool, notify=history_changed)
    def can_redo(self) -> bool:
        return bool(self._draft and self._draft.redo)

    @pyqtProperty(str, notify=authoring_changed)
    def selected_key(self) -> str:
        return self._draft.state.selected_key if self._draft else ""

    @pyqtProperty("QVariantList", notify=authoring_changed)
    def interface_items(self) -> list[dict[str, Any]]:
        saved = getattr(self._node, "properties", {})
        baseline_keys = ({identity: key for key, identity in self._draft.baseline_identities.items()}
                         if self._draft else {})
        saved_keys = ({key: baseline_keys.get(identity) for key, identity in self._draft.state.identities.items()}
                      if self._draft else {})
        return [_variant({
            **asdict(item), "form_fields": field_choices(item.kind, item.fields),
            "saved_value": saved.get(saved_keys.get(item.key)),
            "has_saved_value": saved_keys.get(item.key) in saved,
            "start": _qt_offset(self._script_text, item.source_range.start),
            "end": _qt_offset(self._script_text, item.source_range.end),
        }) for item in self._analysis.items]

    @pyqtProperty("QVariantList", notify=authoring_changed)
    def sections(self) -> list[dict[str, Any]]:
        groups: dict[str, list[str]] = {}
        for item in self._analysis.items:
            if item.section and item.kind != "output":
                groups.setdefault(item.section, []).append(item.key)
        return [{"name": name, "keys": keys} for name, keys in groups.items()]

    @pyqtProperty("QVariantMap", notify=authoring_changed)
    def selected_item(self) -> dict[str, Any]:
        return next((item for item in self.interface_items if item["key"] == self.selected_key), {})

    @pyqtProperty("QVariantList", notify=authoring_changed)
    def diagnostics(self) -> list[dict[str, Any]]:
        return [_variant(asdict(item)) for item in self._analysis.diagnostics]

    @pyqtProperty("QVariantMap", notify=rename_review_changed)
    def rename_review(self) -> dict[str, Any]:
        return copy.deepcopy(self._rename_review)

    @pyqtProperty("QVariantMap", notify=authoring_changed)
    def apply_impact(self) -> dict[str, Any]:
        return copy.deepcopy(self._apply_impact)

    @pyqtProperty(QObject, notify=preview_bridge_changed)
    def preview_bridge(self):
        return self._preview_bridge

    def set_preview_bridge(self, bridge: QObject) -> None:
        self._preview_bridge = bridge
        self.preview_bridge_changed.emit()

    @pyqtSlot(QObject, bool, str)
    def set_form_state(self, owner: QObject, pending: bool, error: str) -> None:
        if owner is not self._form_owner:
            return
        if pending or error:
            self._form_states[owner] = (pending, error)
        else:
            self._form_states.pop(owner, None)

    @pyqtProperty(QObject, notify=form_owner_changed)
    def form_owner(self):
        return self._form_owner

    @pyqtProperty(bool, notify=authoring_changed)
    def has_unapplied_edits(self) -> bool:
        return self._dirty or bool(self._form_states)

    @pyqtSlot(QObject, result="QVariantMap")
    def activate_form(self, owner: QObject) -> dict[str, Any]:
        if self._form_owner is not owner:
            self._form_owner = owner
            self._form_states.clear()
            self.form_owner_changed.emit()
        buffer = self._form_buffers.get(self._context_key, {})
        return copy.deepcopy(buffer) if buffer.get("source") == self._script_text else {}

    @pyqtSlot(QObject, "QVariantMap", bool, str)
    def store_form_buffer(self, owner: QObject, buffer: dict[str, Any], pending: bool, error: str) -> None:
        if owner is not self._form_owner:
            return
        previous_pending = bool(self._form_states)
        self.set_form_state(owner, pending, error)
        if pending:
            self._form_buffers[self._context_key] = copy.deepcopy(buffer)
        else:
            self._form_buffers.pop(self._context_key, None)
        if previous_pending != bool(self._form_states):
            self.authoring_changed.emit()

    def _flush_forms(self) -> bool:
        if self._flushing_forms or self._editing_form:
            return True
        self._flushing_forms = True
        try:
            self.form_flush_requested.emit()
        finally:
            self._flushing_forms = False
        if self._form_states:
            return self._fail(next((error for _pending, error in self._form_states.values() if error),
                                   "Complete or correct the pending interface fields before continuing."))
        return True

    @pyqtSlot("QVariantMap", result=bool)
    def perform_form_edit(self, request: dict[str, Any]) -> bool:
        self._editing_form = True
        try:
            return self.perform_edit("update", request)
        finally:
            self._editing_form = False

    @pyqtSlot(str, result=str)
    def choose_color(self, current: str) -> str:
        """Choose a draft value without invoking a graph property editor."""
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog
        chosen = QColorDialog.getColor(QColor(current), None, "Choose default color")
        return chosen.name() if chosen.isValid() else ""

    @pyqtSlot(str, str, result=str)
    def choose_path(self, current: str, file_filter: str) -> str:
        from PyQt6.QtWidgets import QFileDialog
        chosen, _ = QFileDialog.getOpenFileName(None, "Choose file", current, file_filter or "All files (*)")
        return chosen

    def set_visible(self, visible: bool) -> None:
        if self._visible != bool(visible):
            self._visible = bool(visible)
            if not visible:
                self._set_focus(False)
            self.visibility_changed.emit()

    def set_floating(self, floating: bool) -> None:
        if self._floating != bool(floating):
            self._floating = bool(floating)
            self.visibility_changed.emit()

    @pyqtSlot(float)
    def set_width(self, width: Any) -> None:
        try:
            value = float(width)
        except (TypeError, ValueError):
            value = 0.0
        if value != value or value < 0.0:
            value = 0.0
        if self._panel_width != value:
            self._panel_width = value
            self.width_changed.emit()

    def _key_for_node(self, node_id: str) -> tuple[Any, ...]:
        if not self._context_provider:
            return ("standalone", node_id)
        project, workspace, _registry = self._context_provider()
        if self._project_identity is not project:
            self._drafts.clear()
            self._form_buffers.clear()
            self._project_identity = project
        return (id(project), getattr(project, "project_id", ""),
                getattr(workspace, "workspace_id", ""), node_id)

    def _context_is_current(self) -> bool:
        if not self._context_provider:
            return True
        project, workspace, _registry = self._context_provider()
        return self._context_key == (id(project), getattr(project, "project_id", ""),
                                     getattr(workspace, "workspace_id", ""), self._current_node_id)

    def _new_identity(self) -> int:
        self._next_identity += 1
        return self._next_identity

    def _identities_for(self, source: str, previous: dict[str, int]) -> dict[str, int]:
        analysis = analyze_source(source)
        if not analysis.items and not analysis.valid:
            return dict(previous)
        return {item.key: previous[item.key] if item.key in previous else self._new_identity()
                for item in analysis.items}

    def refresh_node(self, node: Any | None) -> None:
        """Refresh saved values without replacing a same-context draft or its history."""
        if (node is None or getattr(node, "type_id", "") != "code.python_script"
                or str(getattr(node, "node_id", "")) != self._current_node_id
                or not self._context_is_current()
                or str(node.properties.get("script", "")) != self._base_script):
            self.set_node(node)
            return
        self._node = copy.deepcopy(node)
        self._current_node_label = str(getattr(node, "title", "")).strip() or "Python Script"
        self.node_changed.emit()
        self.authoring_changed.emit()

    def set_node(self, node: Any | None) -> None:
        is_script = node is not None and getattr(node, "type_id", "") == "code.python_script"
        node_id = str(getattr(node, "node_id", "")) if is_script else ""
        key = self._key_for_node(node_id)
        if key != self._context_key:
            self._form_owner = None
            self._form_states.clear()
            self.form_owner_changed.emit()
        self._node = copy.deepcopy(node) if is_script else None
        if not is_script:
            self._draft = None
            self._current_node_id = self._current_node_label = self._base_script = ""
            self._context_key = key
            self._set_script_text_internal("")
            self._set_dirty(False)
            self._set_focus(False)
        else:
            source = str(node.properties.get("script", ""))
            draft = self._drafts.get(key)
            if draft is None:
                identities = self._identities_for(source, {})
                draft = _Draft(source, _DocumentState(source, identities), dict(identities))
                self._drafts[key] = draft
            elif draft.baseline != source:
                was_clean = draft.state.source == draft.baseline
                known = next((state for state in [draft.state, *reversed(draft.undo), *draft.redo]
                              if state.source == source), None)
                baseline_ids = (dict(known.identities) if known else
                                self._identities_for(source, draft.baseline_identities))
                draft.baseline = source
                draft.baseline_identities = baseline_ids
                if was_clean:
                    draft.state = _DocumentState(source, dict(baseline_ids), draft.state.selected_key)
                    draft.undo.clear()
                    draft.redo.clear()
            self._draft = draft
            self._context_key = key
            self._current_node_id = node_id
            self._current_node_label = str(getattr(node, "title", "")).strip() or "Python Script"
            self._base_script = draft.baseline
            self._set_script_text_internal(draft.state.source)
            self._set_dirty(draft.state.source != draft.baseline)
        self._invalidate_authoring()
        self.analyze_now()
        self.node_changed.emit()
        self.history_changed.emit()

    @pyqtSlot(str)
    def set_script_text(self, text: str) -> None:
        if self._draft is None or text == self._script_text:
            return
        self._push_state(_DocumentState(str(text), dict(self._draft.state.identities), self.selected_key))

    def _push_state(self, state: _DocumentState) -> None:
        assert self._draft is not None
        self._draft.undo.append(copy.deepcopy(self._draft.state))
        del self._draft.undo[:-200]
        self._draft.redo.clear()
        self._draft.state = state
        self._install_state()

    def _install_state(self) -> None:
        assert self._draft is not None
        self._set_script_text_internal(self._draft.state.source)
        self._set_dirty(self._script_text != self._base_script)
        self._invalidate_authoring()
        self._analysis_timer.start()
        self.history_changed.emit()

    def _invalidate_authoring(self) -> None:
        self._source_revision += 1
        self._analysis_status = "updating" if self._current_node_id else "unavailable"
        self._operation_error = ""
        self._prepared = None
        self._apply_impact = {}
        self._completion = {}
        self._rename_result = None
        self._rename_review = {}
        self.rename_review_changed.emit()
        self.authoring_changed.emit()

    @pyqtSlot()
    def analyze_now(self) -> None:
        self._analysis_timer.stop()
        self._analysis = analyze_source(self._script_text) if self._current_node_id else AuthoringAnalysis()
        if self._draft and (self._analysis.items or self._analysis.valid):
            old = self._draft.state.identities
            self._draft.state.identities = {
                item.key: old[item.key] if item.key in old else self._new_identity()
                for item in self._analysis.items
            }
            if self.selected_key not in self._draft.state.identities:
                self._draft.state.selected_key = ""
        self._analysis_status = "ready" if self._current_node_id and self._analysis.valid else "unavailable"
        self.authoring_changed.emit()

    @pyqtSlot(str, "QVariantMap", result=bool)
    def perform_edit(self, operation: str, request: dict[str, Any]) -> bool:
        if not self._draft:
            return False
        if not self._flush_forms():
            return False
        if operation == "rename":
            self.preview_rename(str(request.get("key", "")), str(request.get("new_key", "")))
            return False
        self.analyze_now()
        try:
            if operation == "section":
                name = str(request.get("name", "")).strip()
                keys = list(dict.fromkeys(request.get("keys", [])))
                old_name = str(request.get("old_name", ""))
                if not name or not keys:
                    raise ValueError("Name the section and choose at least one input or control")
                eligible = {item.key: item for item in self._analysis.items if item.kind != "output"}
                if any(key not in eligible for key in keys):
                    raise ValueError("Sections contain inputs and controls; outputs stay at the top level")
                source = self._script_text
                if old_name:
                    for item in eligible.values():
                        if item.section == old_name and item.key not in keys:
                            source = edit_source(source, "update", key=item.key, remove_fields=("section",)).source
                for key in keys:
                    source = edit_source(source, "update", key=key, fields={"section": name}).source
                self._accept_edit(SourceEditResult(source, selected_key=keys[0]))
                return True
            values = dict(request)
            numeric_mode = values.pop("numeric_mode", "")
            if numeric_mode:
                if numeric_mode not in {"whole", "decimal"}:
                    raise ValueError("Choose Whole number or Decimal")
                item = next((item for item in self._analysis.items if item.key == values.get("key")), None)
                kind = values.get("kind") if operation == "add" else (item.kind if item else "")
                if kind not in {"number", "slider"}:
                    raise ValueError("Numeric mode applies only to Number and Slider")
                fields = dict(values.get("fields", {}))
                for name in ("default", "minimum", "maximum", "step"):
                    if name not in fields:
                        continue
                    value = fields[name]
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise ValueError(f"{name.title()} must be a number")
                    if isinstance(value, float) and not math.isfinite(value):
                        raise ValueError(f"{name.title()} must be finite")
                    if numeric_mode == "whole" and int(value) != value:
                        raise ValueError(f"{name.title()} must be a whole number; fractions are not rounded")
                    fields[name] = int(value) if numeric_mode == "whole" else float(value)
                values["fields"] = fields
            if "remove_fields" in values:
                values["remove_fields"] = tuple(values["remove_fields"])
            result = edit_source(self._script_text, operation, **values)
        except (TypeError, ValueError) as exc:
            return self._fail(str(exc))
        self._accept_edit(result)
        return True

    def _accept_edit(self, result: SourceEditResult) -> None:
        assert self._draft is not None
        identities = dict(self._draft.state.identities)
        for rename in result.renames:
            identity = identities.pop(rename.old_key, self._new_identity())
            identities[rename.new_key] = identity
        identities = self._identities_for(result.source, identities)
        self._push_state(_DocumentState(result.source, identities, result.selected_key or self.selected_key))
        self.analyze_now()
        if result.selected_key:
            self.select_item(result.selected_key)

    @pyqtSlot(str, str, result="QVariantMap")
    def preview_rename(self, key: str, new_key: str) -> dict[str, Any]:
        if not self._flush_forms():
            return {"error": self._operation_error, "changes": []}
        self.analyze_now()
        self._rename_result = None
        try:
            self._rename_result = edit_source(self._script_text, "rename", key=key, new_key=new_key)
            self._rename_review = {"key": key, "new_key": new_key, "error": "",
                                   "source_revision": self._source_revision,
                                   "changes": [_variant(asdict(change)) for change in self._rename_result.changes]}
        except (TypeError, ValueError) as exc:
            self._rename_review = {"error": str(exc), "changes": [], "source_revision": self._source_revision}
        self.rename_review_changed.emit()
        return self.rename_review

    @pyqtSlot(result=bool)
    def confirm_rename(self) -> bool:
        if not self._rename_result or self._rename_review.get("source_revision") != self._source_revision:
            return self._fail("The draft changed. Review the rename again.")
        result = self._rename_result
        self._accept_edit(result)
        return True

    @pyqtSlot(str)
    def select_item(self, key: str) -> None:
        if self._draft is None:
            return
        item = next((item for item in self._analysis.items if item.key == key), None)
        if item is None:
            return
        self._draft.state.selected_key = key
        self.authoring_changed.emit()
        self.selection_range_requested.emit(_qt_offset(self._script_text, item.source_range.start),
                                            _qt_offset(self._script_text, item.source_range.end))

    @pyqtSlot(int)
    def select_source_position(self, position: int) -> None:
        offset = _python_offset(self._script_text, position)
        item = next((item for item in self._analysis.items
                     if item.source_range.start <= offset <= item.source_range.end), None)
        if self._draft and item and self.selected_key != item.key:
            self._draft.state.selected_key = item.key
            self.authoring_changed.emit()

    @pyqtSlot(int)
    def select_diagnostic(self, index: int) -> None:
        if not 0 <= index < len(self._analysis.diagnostics):
            return
        diagnostic = self._analysis.diagnostics[index]
        lines = self._script_text.splitlines(keepends=True)
        offset = sum(map(len, lines[:max(0, diagnostic.line - 1)])) + max(0, diagnostic.column - 1)
        offset = _qt_offset(self._script_text, min(offset, len(self._script_text)))
        self.selection_range_requested.emit(offset, offset)

    @pyqtSlot(str, result="QVariantList")
    def query_decorators(self, query: str = "") -> list[dict[str, Any]]:
        choices = decorator_choices(query)
        if query.casefold() in "section group expandable collapsible settings":
            choices.append({"kind": "section", "label": "Section", "description": "Group inputs and controls under an expandable heading.",
                            "example": "Choose a name and the items to include.", "initial_fields": {}, "fields": []})
        return _variant(choices)

    @pyqtSlot(str, "QVariantMap", result="QVariantList")
    def fields_for(self, kind: str, values: dict[str, Any]) -> list[dict[str, Any]]:
        return _variant(field_choices(kind, values))

    @pyqtSlot(str, bool, str, result="QVariantList")
    def query_types(self, query: str = "", list_items: bool = False, current_type: str = "") -> list[dict[str, Any]]:
        return _variant(type_choices(self.catalog, query, list_items=list_items, current_type=current_type)) if self.catalog else []

    @pyqtSlot(int, result="QVariantMap")
    def query_completions(self, cursor: int) -> dict[str, Any]:
        if self.catalog is None:
            return {}
        result = completions(self._script_text, _python_offset(self._script_text, cursor), self.catalog)
        self._completion = {**result, "source_revision": self._source_revision}
        return _variant({**self._completion, "start": _qt_offset(self._script_text, result["start"]),
                         "end": _qt_offset(self._script_text, result["end"])})

    @pyqtSlot(int, result=bool)
    def accept_completion(self, index: int) -> bool:
        result = self._completion
        if (not self._draft or result.get("source_revision") != self._source_revision
                or self.catalog is None or result.get("catalog_fingerprint") != self.catalog.fingerprint()
                or not 0 <= index < len(result.get("items", []))):
            return self._fail("Suggestions changed. Open completion again.")
        insertion = result["items"][index]["insert_text"]
        start, end = result["start"], result["end"]
        self.set_script_text(self._script_text[:start] + insertion + self._script_text[end:])
        cursor = _qt_offset(self._script_text, start + len(insertion))
        self.selection_range_requested.emit(cursor, cursor)
        return True

    @pyqtSlot(result=bool)
    def undo(self) -> bool:
        if self._form_states:
            self.form_discard_requested.emit()
            self._form_states.clear()
            return True
        if not self.can_undo:
            return False
        self._draft.redo.append(copy.deepcopy(self._draft.state))
        self._draft.state = self._draft.undo.pop()
        self._install_state()
        self.analyze_now()
        return True

    @pyqtSlot(result=bool)
    def redo(self) -> bool:
        if not self.can_redo:
            return False
        self._draft.undo.append(copy.deepcopy(self._draft.state))
        self._draft.state = self._draft.redo.pop()
        self._install_state()
        self.analyze_now()
        return True

    @pyqtSlot(result="QVariantMap")
    def prepare_apply(self) -> dict[str, Any]:
        if not self._flush_forms():
            return {"error": self._operation_error}
        self.analyze_now()
        if not self._current_node_id or not self._prepare_callback:
            return {}
        if not self._context_is_current():
            self._prepared = None
            self._apply_impact = {"error": "The active project or workspace changed. Select the script again."}
            self._fail(self._apply_impact["error"])
            return self.apply_impact
        try:
            self._prepared = self._prepare_callback(self._current_node_id, self._script_text,
                                                   self.renamed_keys, self._source_revision)
        except (TypeError, ValueError, KeyError) as exc:
            self._prepared = None
            self._apply_impact = {"error": str(exc)}
            self._fail(str(exc))
            return self.apply_impact
        self._apply_impact = {"error": "", "source_revision": self._source_revision,
                              "removed_edge_ids": list(self._prepared.removed_edge_ids),
                              "reset_keys": list(self._prepared.reset_keys),
                              "renamed_keys": dict(self._prepared.renamed_keys)}
        self.authoring_changed.emit()
        return self.apply_impact

    @pyqtSlot(result=bool)
    def apply(self) -> bool:
        if not self._flush_forms():
            return False
        if not self._current_node_id:
            return False
        if not self._dirty:
            return True
        node_id, source = self._current_node_id, self._script_text
        self.analyze_now()
        if self._apply_callback:
            if not self._context_is_current():
                return self._fail("The active project or workspace changed. Select the script again.")
            if self._prepared is None:
                self.prepare_apply()
            if self._prepared is None:
                return False
            try:
                self._apply_callback(node_id, source, self.renamed_keys, self._source_revision, self._prepared)
            except (TypeError, ValueError, KeyError) as exc:
                if "stale" in str(exc).lower():
                    self.prepare_apply()
                    return self._fail("The graph changed. Review the updated Apply impact, then Apply again.")
                return self._fail(str(exc))
        else:
            self.script_apply_requested.emit(node_id, "script", source)
        self.focus_editor()
        return self._current_node_id == node_id and self._base_script == source and not self._dirty

    @pyqtSlot()
    def revert(self) -> None:
        self.form_discard_requested.emit()
        self._form_states.clear()
        if self._draft is None or not self._dirty:
            return
        self._push_state(_DocumentState(self._base_script, dict(self._draft.baseline_identities), self.selected_key))
        self.analyze_now()
        self.focus_editor()

    def focus_editor(self) -> bool:
        self._set_focus(self._visible and bool(self._current_node_id))
        return self._has_focus

    @pyqtSlot(int, int, int, int)
    def set_cursor_metrics(self, line: int, column: int, position: int, selection: int) -> None:
        label = f"Ln {line}, Col {column} | Sel {selection} | Pos {position}"
        if self._cursor_label != label:
            self._cursor_label = label
            self.cursor_changed.emit()
        self.select_source_position(position)

    def _fail(self, message: str) -> bool:
        self._operation_error = message
        if self._error_callback:
            self._error_callback(message)
        self.authoring_changed.emit()
        return False

    def _set_focus(self, focused: bool) -> None:
        if self._has_focus != bool(focused):
            self._has_focus = bool(focused)
            self.focus_changed.emit()

    def _set_dirty(self, dirty: bool) -> None:
        if self._dirty != bool(dirty):
            self._dirty = bool(dirty)
            self.dirty_changed.emit()

    def _set_script_text_internal(self, value: str) -> None:
        if self._script_text != value:
            self._script_text = value
            self.content_changed.emit()
