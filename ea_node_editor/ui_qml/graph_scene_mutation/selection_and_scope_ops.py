from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QPointF

from ea_node_editor.graph.effective_ports import find_port, preferred_connection_port
from ea_node_editor.graph.hierarchy import is_node_in_scope, scope_parent_id
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_PORT_KEY,
    is_subnode_pin_type,
    is_subnode_shell_type,
)
from ea_node_editor.ui.shell.runtime_clipboard import (
    normalize_edge_label as _normalize_edge_label,
    normalize_visual_style_payload,
)
from ea_node_editor.ui.shell.runtime_history import (
    ACTION_ADD_EDGE,
    ACTION_ADD_NODE,
    ACTION_EDIT_EDGE_LABEL,
    ACTION_EDIT_EDGE_STYLE,
    ACTION_EDIT_NODE_PROPERTY,
    ACTION_EDIT_NODE_STYLE,
    ACTION_EDIT_PORT_LABEL,
    ACTION_REMOVE_EDGE,
    ACTION_REMOVE_NODE,
    ACTION_RENAME_NODE,
    ACTION_TOGGLE_COLLAPSED,
    ACTION_TOGGLE_EXPOSED_PORT,
)

if TYPE_CHECKING:
    from ea_node_editor.graph.mutation_service import WorkspaceMutationService

_MISSING = object()


def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
    return self.create_node_from_type(
        type_id=type_id,
        x=float(x),
        y=float(y),
        parent_node_id=scope_parent_id(self._scene_context.scope_path),
        select_node=True,
    )


def create_node_from_type(
    self,
    *,
    type_id: str,
    x: float,
    y: float,
    parent_node_id: str | None,
    select_node: bool,
    property_overrides: dict[str, Any] | None = None,
    after_create: Callable[[NodeInstance, WorkspaceMutationService], None] | None = None,
) -> str:
    model, registry = self._scene_context.require_bound()
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return ""
    history_before = self._capture_history_snapshot()
    spec = registry.get_spec(type_id)
    mutations = self._mutation_boundary()
    properties = registry.default_properties(type_id)
    if property_overrides:
        properties.update(
            {
                str(key): registry.normalize_property_value(type_id, key, value)
                for key, value in property_overrides.items()
            }
        )
    node = mutations.add_node(
        type_id=type_id,
        title=spec.display_name,
        x=float(x),
        y=float(y),
        properties=properties,
        exposed_ports={port.key: port.exposed for port in spec.ports},
        parent_node_id=parent_node_id,
    )
    if after_create is not None:
        after_create(node, mutations)
    self._scene_context.sync_surface_title(node, spec)
    if select_node:
        self._scope_selection.set_selected_node_ids([node.node_id], workspace=workspace)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_ADD_NODE, history_before)
    return node.node_id


def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
    model, _registry = self._scene_context.require_bound()
    history_before = self._capture_history_snapshot()
    workspace = model.project.workspaces[self._scene_context.workspace_id]
    if not is_node_in_scope(workspace, source_node_id, self._scene_context.scope_path) or not is_node_in_scope(
        workspace,
        target_node_id,
        self._scene_context.scope_path,
    ):
        raise ValueError("Connections are only allowed for nodes in the active scope.")
    edge = self._mutation_boundary().add_edge(
        source_node_id=source_node_id,
        source_port_key=source_port,
        target_node_id=target_node_id,
        target_port_key=target_port,
    )
    self._scene_context.rebuild_models()
    self._record_history(ACTION_ADD_EDGE, history_before)
    return edge.edge_id


def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
    model, registry = self._scene_context.require_bound()
    workspace = model.project.workspaces[self._scene_context.workspace_id]
    if not is_node_in_scope(workspace, node_a_id, self._scene_context.scope_path) or not is_node_in_scope(
        workspace,
        node_b_id,
        self._scene_context.scope_path,
    ):
        raise ValueError("Selected nodes must be in the active scope.")
    node_a = workspace.nodes[node_a_id]
    node_b = workspace.nodes[node_b_id]
    spec_a = registry.get_spec(node_a.type_id)
    spec_b = registry.get_spec(node_b.type_id)

    a_to_b = (
        preferred_connection_port(
            node=node_a,
            spec=spec_a,
            workspace_nodes=workspace.nodes,
            direction="out",
            peer_node=node_b,
        ),
        preferred_connection_port(
            node=node_b,
            spec=spec_b,
            workspace_nodes=workspace.nodes,
            direction="in",
            peer_node=node_a,
        ),
    )
    b_to_a = (
        preferred_connection_port(
            node=node_b,
            spec=spec_b,
            workspace_nodes=workspace.nodes,
            direction="out",
            peer_node=node_a,
        ),
        preferred_connection_port(
            node=node_a,
            spec=spec_a,
            workspace_nodes=workspace.nodes,
            direction="in",
            peer_node=node_b,
        ),
    )

    can_a_to_b = all(a_to_b)
    can_b_to_a = all(b_to_a)
    prefer_a_to_b = float(node_a.x) < float(node_b.x) or (
        float(node_a.x) == float(node_b.x) and float(node_a.y) <= float(node_b.y)
    )
    if can_a_to_b and (not can_b_to_a or prefer_a_to_b):
        return self.add_edge(node_a_id, a_to_b[0], node_b_id, a_to_b[1])
    if can_b_to_a:
        return self.add_edge(node_b_id, b_to_a[0], node_a_id, b_to_a[1])
    raise ValueError("Selected nodes do not have compatible out/in ports.")


def remove_edge(self, edge_id: str) -> None:
    model = self._scene_context.model
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None or edge_id not in workspace.edges:
        return
    edge = workspace.edges.get(edge_id)
    if edge is None:
        return
    if not is_node_in_scope(workspace, edge.source_node_id, self._scene_context.scope_path):
        return
    if not is_node_in_scope(workspace, edge.target_node_id, self._scene_context.scope_path):
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().remove_edge(edge_id)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_REMOVE_EDGE, history_before)


def remove_node_with_policy(self, node_id: str, *, require_visible: bool) -> bool:
    model = self._scene_context.model
    if model is None:
        return False
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None or node_id not in workspace.nodes:
        return False
    if require_visible and not is_node_in_scope(workspace, node_id, self._scene_context.scope_path):
        return False
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().remove_node(node_id)
    self._scope_selection.set_selected_node_ids(
        [value for value in self._scene_context.selected_node_ids if value != node_id],
        workspace=workspace,
    )
    self._scene_context.rebuild_models()
    self._record_history(ACTION_REMOVE_NODE, history_before)
    return True


def remove_node(self, node_id: str) -> None:
    self.remove_node_with_policy(node_id, require_visible=True)


def remove_workspace_node(self, node_id: str) -> bool:
    return self.remove_node_with_policy(node_id, require_visible=False)


def focus_node(self, node_id: str) -> QPointF | None:
    item = self._scope_selection.node_item(node_id)
    if item is None:
        return None
    selection_changed = self._scope_selection.set_selected_node_ids([node_id])
    if not selection_changed:
        self._scene_context.emit_node_selected(node_id)
    return item.sceneBoundingRect().center()


def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
    model = self._scene_context.model
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    node = workspace.nodes.get(node_id)
    if node is None:
        return
    normalized_collapsed = bool(collapsed)
    if bool(node.collapsed) == normalized_collapsed:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_node_collapsed(node_id, normalized_collapsed)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_TOGGLE_COLLAPSED, history_before)


def set_node_property(self, node_id: str, key: str, value: Any) -> None:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return
    workspace = model.project.workspaces[self._scene_context.workspace_id]
    node = workspace.nodes[node_id]
    spec = registry.get_spec(node.type_id)
    if key == "title":
        normalized_title = self._normalized_title_update(node, value)
        if normalized_title is None:
            return
        history_before = self._capture_history_snapshot()
        self._apply_title_update(node_id, node, spec, normalized_title)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_RENAME_NODE, history_before)
        return
    normalized = registry.normalize_property_value(node.type_id, key, value)
    current_value = node.properties.get(key, _MISSING)
    if current_value is not _MISSING and current_value == normalized:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_node_property(node_id, key, normalized)
    self._scene_context.rebuild_models()
    self.notify_selected_node_context_updated(node_id)
    self._record_history(ACTION_EDIT_NODE_PROPERTY, history_before)


def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return False
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return False
    node = workspace.nodes.get(node_id)
    if node is None:
        return False
    spec = registry.get_spec(node.type_id)
    normalized_updates: dict[str, Any] = {}
    normalized_title = None
    for raw_key, raw_value in dict(values or {}).items():
        key = str(raw_key or "")
        if not key:
            continue
        if key == "title":
            normalized_title = self._normalized_title_update(node, raw_value)
            continue
        try:
            normalized = registry.normalize_property_value(node.type_id, key, raw_value)
        except KeyError:
            continue
        current_value = node.properties.get(key, _MISSING)
        if current_value is not _MISSING and current_value == normalized:
            continue
        normalized_updates[key] = normalized
    if not normalized_updates and normalized_title is None:
        return False

    history_before = self._capture_history_snapshot()
    if normalized_title is not None and not normalized_updates:
        self._apply_title_update(node_id, node, spec, normalized_title)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node_id)
        self._record_history(ACTION_RENAME_NODE, history_before)
        return True
    self._mutation_boundary().set_node_properties(node_id, normalized_updates)
    if normalized_title is not None:
        self._apply_title_update(node_id, node, spec, normalized_title)
    self._scene_context.rebuild_models()
    self.notify_selected_node_context_updated(node_id)
    self._record_history(ACTION_EDIT_NODE_PROPERTY, history_before)
    return True


def normalize_node_visual_style(visual_style: Any) -> dict[str, Any]:
    return normalize_visual_style_payload(visual_style)


def set_node_visual_style(self, node_id: str, visual_style: Any) -> None:
    model = self._scene_context.model
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    node = workspace.nodes.get(node_id)
    if node is None:
        return
    normalized = normalize_visual_style_payload(visual_style)
    if node.visual_style == normalized:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_node_visual_style(node_id, normalized)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_EDIT_NODE_STYLE, history_before)


def clear_node_visual_style(self, node_id: str) -> None:
    self.set_node_visual_style(node_id, {})


def set_node_title(self, node_id: str, title: str) -> None:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return
    node = self._node(node_id)
    if node is None:
        return
    spec = registry.get_spec(node.type_id)
    normalized = self._normalized_title_update(node, title)
    if normalized is None:
        return
    history_before = self._capture_history_snapshot()
    self._apply_title_update(node_id, node, spec, normalized)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_RENAME_NODE, history_before)


def normalize_edge_label(label: Any) -> str:
    return _normalize_edge_label(label)


def set_edge_label(self, edge_id: str, label: Any) -> None:
    model = self._scene_context.model
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    edge = workspace.edges.get(edge_id)
    if edge is None:
        return
    normalized = _normalize_edge_label(label)
    if edge.label == normalized:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_edge_label(edge_id, normalized)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_EDIT_EDGE_LABEL, history_before)


def clear_edge_label(self, edge_id: str) -> None:
    self.set_edge_label(edge_id, "")


def normalize_edge_visual_style(visual_style: Any) -> dict[str, Any]:
    return normalize_visual_style_payload(visual_style)


def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None:
    model = self._scene_context.model
    if model is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    edge = workspace.edges.get(edge_id)
    if edge is None:
        return
    normalized = normalize_visual_style_payload(visual_style)
    if edge.visual_style == normalized:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_edge_visual_style(edge_id, normalized)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_EDIT_EDGE_STYLE, history_before)


def clear_edge_visual_style(self, edge_id: str) -> None:
    self.set_edge_visual_style(edge_id, {})


def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    node = workspace.nodes.get(node_id)
    if node is None:
        return
    spec = registry.get_spec(node.type_id)
    port = find_port(
        node=node,
        spec=spec,
        workspace_nodes=workspace.nodes,
        port_key=key,
    )
    if port is None:
        return
    normalized_exposed = bool(exposed)
    current_exposed = bool(port.exposed)
    if current_exposed == normalized_exposed:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_exposed_port(node_id, key, normalized_exposed)
    self._scene_context.rebuild_models()
    self._record_history(ACTION_TOGGLE_EXPOSED_PORT, history_before)


def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if model is None or registry is None:
        return
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return
    node = workspace.nodes.get(node_id)
    if node is None:
        return
    normalized_label = str(label or "").strip()

    if is_subnode_shell_type(node.type_id):
        pin_node = workspace.nodes.get(str(port_key or "").strip())
        if pin_node is None or str(pin_node.parent_node_id or "").strip() != str(node.node_id):
            return
        current_label = str(pin_node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")).strip()
        if not normalized_label or normalized_label == current_label:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_property(pin_node.node_id, SUBNODE_PIN_LABEL_PROPERTY, normalized_label)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node.node_id)
        self._record_history(ACTION_EDIT_PORT_LABEL, history_before)
        return

    if is_subnode_pin_type(node.type_id) and str(port_key or "").strip() == SUBNODE_PIN_PORT_KEY:
        current_label = str(node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")).strip()
        if not normalized_label or normalized_label == current_label:
            return
        history_before = self._capture_history_snapshot()
        self._mutation_boundary().set_node_property(node.node_id, SUBNODE_PIN_LABEL_PROPERTY, normalized_label)
        self._scene_context.rebuild_models()
        self.notify_selected_node_context_updated(node.node_id)
        self._record_history(ACTION_EDIT_PORT_LABEL, history_before)
        return

    current_label = node.port_labels.get(port_key, "")
    if normalized_label == current_label:
        return
    history_before = self._capture_history_snapshot()
    self._mutation_boundary().set_port_label(node_id, port_key, normalized_label)
    self._scene_context.rebuild_models()
    self.notify_selected_node_context_updated(node_id)
    self._record_history(ACTION_EDIT_PORT_LABEL, history_before)


__all__ = [
    "add_edge",
    "add_node_from_type",
    "clear_edge_label",
    "clear_edge_visual_style",
    "clear_node_visual_style",
    "connect_nodes",
    "create_node_from_type",
    "focus_node",
    "normalize_edge_label",
    "normalize_edge_visual_style",
    "normalize_node_visual_style",
    "remove_edge",
    "remove_node",
    "remove_node_with_policy",
    "remove_workspace_node",
    "set_edge_label",
    "set_edge_visual_style",
    "set_exposed_port",
    "set_node_collapsed",
    "set_node_port_label",
    "set_node_properties",
    "set_node_property",
    "set_node_title",
    "set_node_visual_style",
]

