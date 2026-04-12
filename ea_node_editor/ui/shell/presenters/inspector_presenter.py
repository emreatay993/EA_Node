from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.file_issue_state import (
    collect_node_file_issues,
    decode_file_repair_request,
)
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.nodes.types import property_inspector_editor
from ea_node_editor.ui.shell.window_library_inspector import (
    build_pin_data_type_options,
    build_selected_node_header_data,
    build_selected_node_port_items,
    build_selected_node_property_items,
)

from .contracts import _ShellInspectorPresenterHostProtocol, _presenter_parent


class ShellInspectorPresenter(QObject):
    selected_node_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    inspector_state_changed = pyqtSignal()

    def __init__(
        self,
        host: _ShellInspectorPresenterHostProtocol,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(_presenter_parent(host, parent))
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
        return build_selected_node_header_data(node=node, spec=spec, workflow_nodes=workflow_nodes)

    @property
    def selected_node_title(self) -> str: return str(self._selected_node_header_data().get("title", ""))

    @property
    def selected_node_subtitle(self) -> str: return str(self._selected_node_header_data().get("subtitle", ""))

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
    def has_selected_node(self) -> bool: return self._selected_node_context() is not None

    @property
    def selected_node_collapsible(self) -> bool:
        selected = self._selected_node_context()
        return bool(selected[1].collapsible) if selected is not None else False

    @property
    def selected_node_collapsed(self) -> bool:
        selected = self._selected_node_context()
        return bool(selected[0].collapsed) if selected is not None else False

    @property
    def selected_node_is_subnode_pin(self) -> bool:
        selected = self._selected_node_context()
        return bool(selected and selected[0].type_id in self._host._SUBNODE_PIN_TYPE_IDS)

    @property
    def selected_node_is_subnode_shell(self) -> bool:
        selected = self._selected_node_context()
        return bool(selected and selected[0].type_id == SUBNODE_TYPE_ID)

    @property
    def selected_node_property_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return []
        port_connection_counts: dict[tuple[str, str], int] = {}
        for edge in workspace.edges.values():
            source_key = (edge.source_node_id, edge.source_port_key)
            target_key = (edge.target_node_id, edge.target_port_key)
            port_connection_counts[source_key] = port_connection_counts.get(source_key, 0) + 1
            port_connection_counts[target_key] = port_connection_counts.get(target_key, 0) + 1
        metadata = self._host.model.project.metadata
        return build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=self._host._SUBNODE_PIN_TYPE_IDS,
            workspace_nodes=workspace.nodes,
            workspace_edges=workspace.edges,
            port_connection_counts=port_connection_counts,
            file_issues_by_key=collect_node_file_issues(
                node=node,
                spec=spec,
                project_path=str(self._host.project_path or "").strip() or None,
                project_metadata=dict(metadata) if isinstance(metadata, dict) else None,
            ),
            project_path=str(self._host.project_path or "").strip() or None,
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
        return build_selected_node_port_items(node=node, spec=spec, workspace_nodes=workspace.nodes)

    @property
    def pin_data_type_options(self) -> list[str]:
        return build_pin_data_type_options(
            registry_specs=self._host.registry.all_specs(),
            workspaces=self._host.model.project.workspaces.values(),
            subnode_pin_type_ids=self._host._SUBNODE_PIN_TYPE_IDS,
            subnode_pin_data_type_property=SUBNODE_PIN_DATA_TYPE_PROPERTY,
        )

    def _node_context_by_id(self, node_id: str):
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return None
        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return None
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return None
        return node, self._host.registry.get_spec(node.type_id)

    def _node_property_spec(self, node_id: str, key: str):
        normalized_key = str(key).strip()
        if not normalized_key:
            return None
        node_context = self._node_context_by_id(node_id)
        if node_context is None:
            return None
        _node, spec = node_context
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
        selected = self._selected_node_context()
        if selected is None:
            return ""
        node, _spec = selected
        property_spec = self._selected_node_property_spec(key)
        if property_spec is None or str(property_spec.type) != "path":
            return ""
        repair_request = decode_file_repair_request(current_path)
        if repair_request is not None:
            return self._host._repair_property_path_dialog(
                node_type_id=node.type_id,
                property_key=property_spec.key,
                property_label=property_spec.label,
                current_path=repair_request.current_value,
            )
        return self._host.shell_host_presenter.browse_property_path_dialog(property_spec.label, current_path)

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        node_context = self._node_context_by_id(node_id)
        if node_context is None:
            return ""
        node, _spec = node_context
        property_spec = self._node_property_spec(node_id, key)
        if property_spec is None or str(property_spec.type) != "path":
            return ""
        repair_request = decode_file_repair_request(current_path)
        if repair_request is not None:
            return self._host._repair_property_path_dialog(
                node_type_id=node.type_id,
                property_key=property_spec.key,
                property_label=property_spec.label,
                current_path=repair_request.current_value,
            )
        return self._host.shell_host_presenter.browse_property_path_dialog(property_spec.label, current_path)

    def pick_selected_node_property_color(self, key: str, current_value: str) -> str:
        property_spec = self._selected_node_property_spec(key)
        if property_spec is None or property_inspector_editor(property_spec) != "color":
            return ""
        return self._host.shell_host_presenter.pick_property_color_dialog(property_spec.label, current_value)

    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str:
        property_spec = self._node_property_spec(node_id, key)
        if property_spec is None or str(property_spec.inline_editor).strip() != "color":
            return ""
        return self._host.shell_host_presenter.pick_property_color_dialog(property_spec.label, current_value)

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


__all__ = ["ShellInspectorPresenter"]
