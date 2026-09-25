# Purpose: Render and interact with a detached, non-executing Python Script draft.
# Map: subsystems/qml_shell_and_bridges.md
# Tests: tests/test_python_script_authoring_ui.py
from __future__ import annotations

import copy
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.declaration_engine import BUILTIN_TYPES
from ea_node_editor.ui_qml.graph_scene_payload import GraphScenePayloadBuilder


class PythonScriptPreview(QObject):
    changed = pyqtSignal()

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self._builder = GraphScenePayloadBuilder()
        self._node = None
        self._payload = {}
        self._identity = None
        self._error = ""
        self._theme = None
        self._group_expansion = {}
        self._document_id = ""
        editor.authoring_changed.connect(self.refresh)
        editor.node_changed.connect(self.refresh)
        self.refresh()

    @pyqtProperty("QVariantMap", notify=changed)
    def payload(self):
        return self._payload

    @pyqtProperty("QVariantMap", notify=changed)
    def values(self):
        return copy.deepcopy(self._node.properties) if self._node else {}

    @pyqtProperty(str, notify=changed)
    def error(self):
        return self._error

    @pyqtSlot(QObject)
    def set_theme(self, theme):
        if self._theme is theme:
            return
        if self._theme is not None:
            self._theme.changed.disconnect(self._rebuild)
        self._theme = theme
        if theme is not None:
            theme.changed.connect(self._rebuild)
        self._rebuild()

    def refresh(self):
        editor = self.editor
        if editor.analysis_status != "ready" or editor.registry is None:
            self._payload = {}
            self._node = None
            self._identity = None
            self.changed.emit()
            return
        identity = (editor.current_node_id, editor.source_revision, editor.current_node_label, editor.catalog.fingerprint())
        if identity == self._identity:
            return
        self._identity = identity
        self._error = ""
        if self._document_id != editor.current_node_id:
            self._group_expansion = {}
            self._document_id = editor.current_node_id
        try:
            spec = editor.registry.resolve_spec("code.python_script", {"script": editor.script_text})
            values = {prop.key: prop.make_default() for prop in spec.properties}
            values["script"] = editor.script_text
            self._node = NodeInstance(
                node_id="__script_authoring_preview__", type_id="code.python_script",
                title=editor.current_node_label, x=0, y=0, properties=values,
                expanded_settings_group_ids=tuple(
                    group.group_id for group in spec.settings_groups
                    if group.show_header and self._group_expansion.get(group.group_id, True)
                ),
            )
            self._rebuild()
        except (ValueError, TypeError, KeyError) as exc:
            self._node = None
            self._payload = {}
            self._error = str(exc)
            self.changed.emit()

    def _rebuild(self):
        if self._node is not None:
            self._payload = self._builder.build_script_preview_node_payload(
                registry=self.editor.registry, node=self._node, graph_theme_bridge=self._theme,
            )
        self.changed.emit()

    @pyqtSlot(str, "QVariant", result=bool)
    def set_value(self, key, value):
        if self._node is None or self.editor.analysis_status != "ready":
            return False
        item = next((item for item in self.editor.analysis.items if item.key == key), None)
        if item is None or item.kind in {"input", "output"}:
            return False
        try:
            normalized = self.editor.registry.normalize_property_value(
                "code.python_script", key, value, properties=self._node.properties,
            )
        except (TypeError, ValueError, KeyError) as exc:
            self._error = str(exc)
            self.changed.emit()
            return False
        self._node.properties[key] = normalized
        self.editor.select_item(key)
        self._error = ""
        self._rebuild()
        return True

    @pyqtSlot(str, bool)
    def set_group_expanded(self, group_id, expanded):
        if self._node is None:
            return
        if not any(
            group["group_id"] == group_id and group.get("show_header", True)
            for group in self._payload.get("settings_groups", ())
        ):
            return
        groups = set(self._node.expanded_settings_group_ids)
        self._group_expansion[group_id] = expanded
        groups.add(group_id) if expanded else groups.discard(group_id)
        self._node.expanded_settings_group_ids = tuple(sorted(groups))
        self._rebuild()

    @pyqtSlot(str, result=bool)
    def use_as_default(self, key):
        if self._node is None or key not in self._node.properties:
            return False
        item = next((item for item in self.editor.analysis.items if item.key == key), None)
        if item is None or item.kind in {"input", "output"}:
            return False
        request = {"key": key, "fields": {"default": copy.deepcopy(self._node.properties[key])}}
        if item.kind in {"number", "slider"}:
            request["numeric_mode"] = "whole" if item.data_type == BUILTIN_TYPES["int"] else "decimal"
        return self.editor.perform_edit("update", request)

    @pyqtSlot()
    def reset(self):
        self._identity = None
        self.refresh()
