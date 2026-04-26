from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.ui.shell.graph_action_contracts import (
    GRAPH_ACTION_SPECS,
    GraphActionId,
    normalize_graph_action_id,
    normalize_graph_action_payload,
)

_UNSET = object()

_WORKSPACE_ACTION_METHODS: dict[GraphActionId, tuple[str, bool]] = {
    GraphActionId.CONNECT_SELECTED: ("connect_selected_nodes", True),
    GraphActionId.COPY_SELECTION: ("copy_selected_nodes_to_clipboard", False),
    GraphActionId.CUT_SELECTION: ("cut_selected_nodes_to_clipboard", False),
    GraphActionId.PASTE_SELECTION: ("paste_nodes_from_clipboard", False),
    GraphActionId.DUPLICATE_SELECTION: ("duplicate_selected_nodes", False),
    GraphActionId.GROUP_SELECTION: ("group_selected_nodes", False),
    GraphActionId.UNGROUP_SELECTION: ("ungroup_selected_nodes", False),
    GraphActionId.ALIGN_SELECTION_LEFT: ("align_selection_left", False),
    GraphActionId.ALIGN_SELECTION_RIGHT: ("align_selection_right", False),
    GraphActionId.ALIGN_SELECTION_TOP: ("align_selection_top", False),
    GraphActionId.ALIGN_SELECTION_BOTTOM: ("align_selection_bottom", False),
    GraphActionId.DISTRIBUTE_SELECTION_HORIZONTALLY: ("distribute_selection_horizontally", False),
    GraphActionId.DISTRIBUTE_SELECTION_VERTICALLY: ("distribute_selection_vertically", False),
}

_NODE_HOST_ACTION_METHODS: dict[GraphActionId, str] = {
    GraphActionId.EDIT_PASSIVE_NODE_STYLE: "request_edit_passive_node_style",
    GraphActionId.RESET_PASSIVE_NODE_STYLE: "request_reset_passive_node_style",
    GraphActionId.COPY_PASSIVE_NODE_STYLE: "request_copy_passive_node_style",
    GraphActionId.PASTE_PASSIVE_NODE_STYLE: "request_paste_passive_node_style",
    GraphActionId.RENAME_NODE: "request_rename_node",
    GraphActionId.UNGROUP_NODE: "request_ungroup_node",
    GraphActionId.REMOVE_NODE: "request_remove_node",
}

_EDGE_HOST_ACTION_METHODS: dict[GraphActionId, str] = {
    GraphActionId.EDIT_FLOW_EDGE_STYLE: "request_edit_flow_edge_style",
    GraphActionId.EDIT_FLOW_EDGE_LABEL: "request_edit_flow_edge_label",
    GraphActionId.RESET_FLOW_EDGE_STYLE: "request_reset_flow_edge_style",
    GraphActionId.COPY_FLOW_EDGE_STYLE: "request_copy_flow_edge_style",
    GraphActionId.PASTE_FLOW_EDGE_STYLE: "request_paste_flow_edge_style",
    GraphActionId.REMOVE_EDGE: "request_remove_edge",
}


class GraphActionController:
    def __init__(
        self,
        *,
        workspace_library_controller: object | None = None,
        workspace_graph_edit_controller: object | None = None,
        graph_canvas_presenter: object | None = None,
        graph_canvas_host_presenter: object | None = None,
        shell_library_presenter: object | None = None,
        scene_bridge: object | None = None,
        help_bridge: object | None = None,
        addon_manager_bridge: object | None = None,
    ) -> None:
        self._workspace_library_controller = workspace_library_controller
        self._workspace_graph_edit_controller = workspace_graph_edit_controller
        self._graph_canvas_presenter = graph_canvas_presenter
        self._graph_canvas_host_presenter = graph_canvas_host_presenter
        self._shell_library_presenter = shell_library_presenter
        self._scene_bridge = scene_bridge
        self._help_bridge = help_bridge
        self._addon_manager_bridge = addon_manager_bridge

    def bind_sources(
        self,
        *,
        workspace_library_controller: object | None = None,
        workspace_graph_edit_controller: object | None = None,
        graph_canvas_presenter: object | None = None,
        graph_canvas_host_presenter: object | None = None,
        shell_library_presenter: object | None = None,
        scene_bridge: object | None = None,
        help_bridge: object | None = None,
        addon_manager_bridge: object | None = None,
    ) -> None:
        if workspace_library_controller is not None:
            self._workspace_library_controller = workspace_library_controller
        if workspace_graph_edit_controller is not None:
            self._workspace_graph_edit_controller = workspace_graph_edit_controller
        if graph_canvas_presenter is not None:
            self._graph_canvas_presenter = graph_canvas_presenter
        if graph_canvas_host_presenter is not None:
            self._graph_canvas_host_presenter = graph_canvas_host_presenter
        if shell_library_presenter is not None:
            self._shell_library_presenter = shell_library_presenter
        if scene_bridge is not None:
            self._scene_bridge = scene_bridge
        if help_bridge is not None:
            self._help_bridge = help_bridge
        if addon_manager_bridge is not None:
            self._addon_manager_bridge = addon_manager_bridge

    @property
    def available_action_ids(self) -> tuple[str, ...]:
        return tuple(spec.action_id.value for spec in GRAPH_ACTION_SPECS)

    def trigger(
        self,
        action_id: str,
        payload: Mapping[str, object] | None = None,
    ) -> bool:
        normalized_action_id = normalize_graph_action_id(action_id)
        if normalized_action_id is None:
            return False
        if normalized_action_id is GraphActionId.SHOW_NODE_HELP and payload is None:
            return self._trigger_show_help_for_selected_node()
        normalized_payload = normalize_graph_action_payload(normalized_action_id, payload)
        if normalized_payload is None:
            return False
        return self._trigger_normalized(normalized_action_id, normalized_payload)

    def _trigger_normalized(self, action_id: GraphActionId, payload: Mapping[str, object]) -> bool:
        if action_id in _WORKSPACE_ACTION_METHODS:
            method_name, none_is_success = _WORKSPACE_ACTION_METHODS[action_id]
            return self._invoke_bool(
                self._workspace_library_controller_source(),
                method_name,
                none_is_success=none_is_success,
            )
        if action_id is GraphActionId.DELETE_SELECTION:
            return self._trigger_delete_selection(payload)
        if action_id is GraphActionId.WRAP_SELECTION_IN_COMMENT_BACKDROP:
            return self._invoke_bool(
                self._workspace_graph_edit_controller_source(),
                "wrap_selected_nodes_in_comment_backdrop",
            )
        if action_id is GraphActionId.NAVIGATE_SCOPE_PARENT:
            return self._trigger_navigate_scope("request_navigate_scope_parent")
        if action_id is GraphActionId.NAVIGATE_SCOPE_ROOT:
            return self._trigger_navigate_scope("request_navigate_scope_root")
        if action_id is GraphActionId.OPEN_ADDON_MANAGER_FOR_NODE:
            return self._trigger_open_addon_manager_for_node(payload)
        if action_id is GraphActionId.OPEN_SUBNODE_SCOPE:
            return self._trigger_node_action_on_canvas_presenter(payload, "request_open_subnode_scope")
        if action_id is GraphActionId.PUBLISH_CUSTOM_WORKFLOW_FROM_NODE:
            return self._trigger_publish_custom_workflow_from_node(payload)
        if action_id is GraphActionId.OPEN_COMMENT_PEEK:
            return self._invoke_bool(self._scene_bridge_source(), "open_comment_peek", _required_str(payload, "node_id"))
        if action_id is GraphActionId.CLOSE_COMMENT_PEEK:
            return self._invoke_bool(self._scene_bridge_source(), "close_comment_peek")
        if action_id is GraphActionId.RENAME_NODE and bool(payload.get("inline_title_edit")):
            return True
        if action_id in _NODE_HOST_ACTION_METHODS:
            return self._trigger_node_action_on_host_presenter(payload, _NODE_HOST_ACTION_METHODS[action_id])
        if action_id is GraphActionId.DUPLICATE_NODE:
            return self._trigger_duplicate_node(payload)
        if action_id is GraphActionId.SHOW_NODE_HELP:
            return self._invoke_bool(self._help_bridge_source(), "show_help_for_node", _required_str(payload, "node_id"))
        if action_id in _EDGE_HOST_ACTION_METHODS:
            return self._trigger_edge_action_on_host_presenter(payload, _EDGE_HOST_ACTION_METHODS[action_id])
        return False

    def _trigger_delete_selection(self, payload: Mapping[str, object]) -> bool:
        edge_ids = _optional_list(payload, "edge_ids")
        if edge_ids is None:
            return False
        return self._invoke_bool(
            self._graph_canvas_host_presenter_source(),
            "request_delete_selected_graph_items",
            edge_ids,
        ) or self._invoke_bool(
            self._workspace_library_controller_source(),
            "request_delete_selected_graph_items",
            edge_ids,
        )

    def _trigger_navigate_scope(self, host_method_name: str) -> bool:
        return self._invoke_bool(self._graph_canvas_host_presenter_source(), host_method_name)

    def _trigger_show_help_for_selected_node(self) -> bool:
        help_bridge = self._help_bridge_source()
        return self._invoke_bool(help_bridge, "show_help_for_selected_node")

    def _trigger_node_action_on_canvas_presenter(
        self,
        payload: Mapping[str, object],
        method_name: str,
    ) -> bool:
        node_id = _required_str(payload, "node_id")
        return self._invoke_bool(
            self._graph_canvas_presenter_source(),
            method_name,
            node_id,
        )

    def _trigger_publish_custom_workflow_from_node(self, payload: Mapping[str, object]) -> bool:
        node_id = _required_str(payload, "node_id")
        return (
            self._invoke_bool(
                self._shell_library_presenter_source(),
                "request_publish_custom_workflow_from_node",
                node_id,
            )
            or self._invoke_bool(
                self._workspace_library_controller_source(),
                "publish_custom_workflow_from_node",
                node_id,
            )
        )

    def _trigger_node_action_on_host_presenter(
        self,
        payload: Mapping[str, object],
        method_name: str,
    ) -> bool:
        node_id = _required_str(payload, "node_id")
        return self._invoke_bool(
            self._graph_canvas_host_presenter_source(),
            method_name,
            node_id,
        )

    def _trigger_edge_action_on_host_presenter(
        self,
        payload: Mapping[str, object],
        method_name: str,
    ) -> bool:
        edge_id = _required_str(payload, "edge_id")
        return self._invoke_bool(
            self._graph_canvas_host_presenter_source(),
            method_name,
            edge_id,
        )

    def _trigger_duplicate_node(self, payload: Mapping[str, object]) -> bool:
        node_id = _required_str(payload, "node_id")
        scene = self._scene_bridge_source()
        command_source = getattr(scene, "command_bridge", scene) if scene is not None else None
        if not self._invoke_bool(command_source, "select_node", node_id, False, none_is_success=True):
            return False
        return self._invoke_bool(scene, "duplicate_selected_subgraph")

    def _trigger_open_addon_manager_for_node(self, payload: Mapping[str, object]) -> bool:
        focus_addon_id = self._addon_focus_id(payload)
        if not focus_addon_id:
            return False
        addon_manager_bridge = self._addon_manager_bridge_source()
        if self._invoke_bool(addon_manager_bridge, "requestOpen", focus_addon_id, none_is_success=True):
            return True
        return False

    def _addon_focus_id(self, payload: Mapping[str, object]) -> str:
        explicit = _first_non_empty_str(payload, "focus_addon_id", "addon_id")
        if explicit:
            return explicit
        node_id = _required_str(payload, "node_id")
        node_payload = self._scene_node_payload(node_id)
        locked_state = node_payload.get("locked_state")
        if isinstance(locked_state, Mapping):
            focus_addon_id = _first_non_empty_str(locked_state, "focus_addon_id")
            if focus_addon_id:
                return focus_addon_id
        return _first_non_empty_str(node_payload, "addon_id")

    def _scene_node_payload(self, node_id: str) -> Mapping[str, object]:
        scene = self._scene_bridge_source()
        normalized_node_id = str(node_id or "").strip()
        if scene is None or not normalized_node_id:
            return {}
        for attr_name in ("nodes_model", "backdrop_nodes_model"):
            payloads = getattr(scene, attr_name, None)
            if not isinstance(payloads, list):
                continue
            for payload in payloads:
                if not isinstance(payload, Mapping):
                    continue
                if str(payload.get("node_id", "")).strip() == normalized_node_id:
                    return payload
        return {}

    def _workspace_library_controller_source(self) -> object | None:
        return self._workspace_library_controller

    def _workspace_graph_edit_controller_source(self) -> object | None:
        if self._workspace_graph_edit_controller is not None:
            return self._workspace_graph_edit_controller
        workspace_library_controller = self._workspace_library_controller_source()
        return getattr(workspace_library_controller, "workspace_graph_edit_controller", None)

    def _graph_canvas_presenter_source(self) -> object | None:
        return self._graph_canvas_presenter

    def _graph_canvas_host_presenter_source(self) -> object | None:
        return self._graph_canvas_host_presenter

    def _shell_library_presenter_source(self) -> object | None:
        return self._shell_library_presenter

    def _scene_bridge_source(self) -> object | None:
        return self._scene_bridge

    def _help_bridge_source(self) -> object | None:
        return self._help_bridge

    def _addon_manager_bridge_source(self) -> object | None:
        return self._addon_manager_bridge

    @staticmethod
    def _invoke_bool(
        source: object | None,
        method_name: str,
        *args: object,
        none_is_success: bool = False,
    ) -> bool:
        callback = getattr(source, method_name, None) if source is not None else None
        if not callable(callback):
            return False
        result = callback(*args)
        return _result_bool(result, none_is_success=none_is_success)

def _result_bool(result: object, *, none_is_success: bool = False) -> bool:
    if result is None:
        return none_is_success
    payload = getattr(result, "payload", _UNSET)
    if payload is not _UNSET:
        return bool(payload)
    return bool(result)


def _required_str(payload: Mapping[str, object], key: str) -> str:
    value = payload[key]
    return str(value).strip()


def _first_non_empty_str(payload: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized:
            return normalized
    return ""


def _optional_list(payload: Mapping[str, object], key: str) -> list[object] | None:
    value = payload.get(key, [])
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return None


__all__ = ["GraphActionController"]
