from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GraphActionId(str, Enum):
    CONNECT_SELECTED = "connect_selected"
    COPY_SELECTION = "copy_selection"
    CUT_SELECTION = "cut_selection"
    PASTE_SELECTION = "paste_selection"
    DUPLICATE_SELECTION = "duplicate_selection"
    DELETE_SELECTION = "delete_selection"
    WRAP_SELECTION_IN_COMMENT_BACKDROP = "wrap_selection_in_comment_backdrop"
    GROUP_SELECTION = "group_selection"
    UNGROUP_SELECTION = "ungroup_selection"
    ALIGN_SELECTION_LEFT = "align_selection_left"
    ALIGN_SELECTION_RIGHT = "align_selection_right"
    ALIGN_SELECTION_TOP = "align_selection_top"
    ALIGN_SELECTION_BOTTOM = "align_selection_bottom"
    DISTRIBUTE_SELECTION_HORIZONTALLY = "distribute_selection_horizontally"
    DISTRIBUTE_SELECTION_VERTICALLY = "distribute_selection_vertically"
    NAVIGATE_SCOPE_PARENT = "navigate_scope_parent"
    NAVIGATE_SCOPE_ROOT = "navigate_scope_root"
    OPEN_ADDON_MANAGER_FOR_NODE = "open_addon_manager_for_node"
    OPEN_SUBNODE_SCOPE = "open_subnode_scope"
    PUBLISH_CUSTOM_WORKFLOW_FROM_NODE = "publish_custom_workflow_from_node"
    OPEN_COMMENT_PEEK = "open_comment_peek"
    CLOSE_COMMENT_PEEK = "close_comment_peek"
    EDIT_PASSIVE_NODE_STYLE = "edit_passive_node_style"
    RESET_PASSIVE_NODE_STYLE = "reset_passive_node_style"
    COPY_PASSIVE_NODE_STYLE = "copy_passive_node_style"
    PASTE_PASSIVE_NODE_STYLE = "paste_passive_node_style"
    RENAME_NODE = "rename_node"
    SHOW_NODE_HELP = "show_node_help"
    UNGROUP_NODE = "ungroup_node"
    REMOVE_NODE = "remove_node"
    DUPLICATE_NODE = "duplicate_node"
    EDIT_FLOW_EDGE_STYLE = "edit_flow_edge_style"
    EDIT_FLOW_EDGE_LABEL = "edit_flow_edge_label"
    RESET_FLOW_EDGE_STYLE = "reset_flow_edge_style"
    COPY_FLOW_EDGE_STYLE = "copy_flow_edge_style"
    PASTE_FLOW_EDGE_STYLE = "paste_flow_edge_style"
    REMOVE_EDGE = "remove_edge"


@dataclass(frozen=True)
class GraphActionSpec:
    action_id: GraphActionId
    label: str | None
    shortcut: str | None
    surfaces: tuple[str, ...]
    destructive: bool = False
    required_payload_keys: tuple[str, ...] = ()
    legacy_route_names: tuple[str, ...] = ()
    legacy_labels: tuple[str, ...] = ()


GRAPH_ACTION_SPECS: tuple[GraphActionSpec, ...] = (
    GraphActionSpec(
        GraphActionId.CONNECT_SELECTED,
        "Connect Selected",
        "Ctrl+L",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        legacy_route_names=("action_connect_selected", "_connect_selected_nodes", "request_connect_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.COPY_SELECTION,
        "Copy Selection",
        "Ctrl+C",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        legacy_route_names=("action_copy_selection", "_copy_selected_nodes_to_clipboard", "request_copy_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.CUT_SELECTION,
        "Cut Selection",
        "Ctrl+X",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        destructive=True,
        legacy_route_names=("action_cut_selection", "_cut_selected_nodes_to_clipboard", "request_cut_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.PASTE_SELECTION,
        "Paste Selection",
        "Ctrl+V",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        legacy_route_names=("action_paste_selection", "_paste_nodes_from_clipboard", "request_paste_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.DUPLICATE_SELECTION,
        "Duplicate Selection",
        "Ctrl+D",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        legacy_route_names=("action_duplicate_selection", "_duplicate_selected_nodes", "request_duplicate_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.DELETE_SELECTION,
        "Delete Selection",
        "Delete",
        ("qml_key_handler",),
        destructive=True,
        legacy_route_names=("request_delete_selected_graph_items",),
    ),
    GraphActionSpec(
        GraphActionId.WRAP_SELECTION_IN_COMMENT_BACKDROP,
        "Wrap Selection in Comment Backdrop",
        "C",
        ("pyqt_edit_menu", "pyqt_shortcut", "qml_selection_context_menu"),
        legacy_route_names=(
            "action_wrap_selection_in_comment_backdrop",
            "wrap_into_frame",
            "_wrap_selected_nodes_in_comment_backdrop",
            "request_wrap_selected_nodes_in_comment_backdrop",
        ),
        legacy_labels=("Wrap into frame",),
    ),
    GraphActionSpec(
        GraphActionId.GROUP_SELECTION,
        "Group Selection",
        "Ctrl+G",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        legacy_route_names=("action_group_selection", "_group_selected_nodes", "request_group_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.UNGROUP_SELECTION,
        "Ungroup Selection",
        "Ctrl+Shift+G",
        ("pyqt_edit_menu", "pyqt_shortcut"),
        destructive=True,
        legacy_route_names=("action_ungroup_selection", "_ungroup_selected_nodes", "request_ungroup_selected_nodes"),
    ),
    GraphActionSpec(
        GraphActionId.ALIGN_SELECTION_LEFT,
        "Align Left",
        None,
        ("pyqt_layout_menu",),
        legacy_route_names=("action_align_left", "_align_selection_left", "request_align_selection_left"),
    ),
    GraphActionSpec(
        GraphActionId.ALIGN_SELECTION_RIGHT,
        "Align Right",
        None,
        ("pyqt_layout_menu",),
        legacy_route_names=("action_align_right", "_align_selection_right", "request_align_selection_right"),
    ),
    GraphActionSpec(
        GraphActionId.ALIGN_SELECTION_TOP,
        "Align Top",
        None,
        ("pyqt_layout_menu",),
        legacy_route_names=("action_align_top", "_align_selection_top", "request_align_selection_top"),
    ),
    GraphActionSpec(
        GraphActionId.ALIGN_SELECTION_BOTTOM,
        "Align Bottom",
        None,
        ("pyqt_layout_menu",),
        legacy_route_names=("action_align_bottom", "_align_selection_bottom", "request_align_selection_bottom"),
    ),
    GraphActionSpec(
        GraphActionId.DISTRIBUTE_SELECTION_HORIZONTALLY,
        "Distribute Horizontally",
        None,
        ("pyqt_layout_menu",),
        legacy_route_names=(
            "action_distribute_horizontally",
            "_distribute_selection_horizontally",
            "request_distribute_selection_horizontally",
        ),
    ),
    GraphActionSpec(
        GraphActionId.DISTRIBUTE_SELECTION_VERTICALLY,
        "Distribute Vertically",
        None,
        ("pyqt_layout_menu",),
        legacy_route_names=(
            "action_distribute_vertically",
            "_distribute_selection_vertically",
            "request_distribute_selection_vertically",
        ),
    ),
    GraphActionSpec(
        GraphActionId.NAVIGATE_SCOPE_PARENT,
        "Scope Parent",
        "Alt+Left",
        ("pyqt_view_menu", "pyqt_shortcut", "qml_key_handler"),
        legacy_route_names=("action_scope_parent", "request_navigate_scope_parent"),
    ),
    GraphActionSpec(
        GraphActionId.NAVIGATE_SCOPE_ROOT,
        "Scope Root",
        "Alt+Home",
        ("pyqt_view_menu", "pyqt_shortcut", "qml_key_handler"),
        legacy_route_names=("action_scope_root", "request_navigate_scope_root"),
    ),
    GraphActionSpec(
        GraphActionId.OPEN_ADDON_MANAGER_FOR_NODE,
        "Open Add-On Manager",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("open_addon_manager", "requestOpenAddonManagerForNode"),
    ),
    GraphActionSpec(
        GraphActionId.OPEN_SUBNODE_SCOPE,
        "Enter Subnode",
        None,
        ("qml_node_context_menu", "qml_node_delegate"),
        required_payload_keys=("node_id",),
        legacy_route_names=("enter_subnode", "enterScope", "requestOpenSubnodeScope", "request_open_subnode_scope"),
    ),
    GraphActionSpec(
        GraphActionId.PUBLISH_CUSTOM_WORKFLOW_FROM_NODE,
        "Add to Workflows",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("add_to_workflows", "request_publish_custom_workflow_from_node"),
    ),
    GraphActionSpec(
        GraphActionId.OPEN_COMMENT_PEEK,
        "Peek Inside",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("peek_comment", "request_open_comment_peek"),
    ),
    GraphActionSpec(
        GraphActionId.CLOSE_COMMENT_PEEK,
        "Exit Peek",
        None,
        ("qml_node_context_menu",),
        legacy_route_names=("exit_comment_peek", "request_close_comment_peek"),
    ),
    GraphActionSpec(
        GraphActionId.EDIT_PASSIVE_NODE_STYLE,
        "Edit Style...",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("edit_node_style", "request_edit_passive_node_style"),
    ),
    GraphActionSpec(
        GraphActionId.RESET_PASSIVE_NODE_STYLE,
        "Reset Style",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("reset_node_style", "request_reset_passive_node_style"),
    ),
    GraphActionSpec(
        GraphActionId.COPY_PASSIVE_NODE_STYLE,
        "Copy Style",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("copy_node_style", "request_copy_passive_node_style"),
    ),
    GraphActionSpec(
        GraphActionId.PASTE_PASSIVE_NODE_STYLE,
        "Paste Style",
        None,
        ("qml_node_context_menu",),
        required_payload_keys=("node_id",),
        legacy_route_names=("paste_node_style", "request_paste_passive_node_style"),
    ),
    GraphActionSpec(
        GraphActionId.RENAME_NODE,
        "Rename Node",
        None,
        ("qml_node_context_menu", "qml_node_delegate"),
        required_payload_keys=("node_id",),
        legacy_route_names=("rename_node", "rename", "requestInlineRenameForNode", "request_rename_node"),
    ),
    GraphActionSpec(
        GraphActionId.SHOW_NODE_HELP,
        "Help",
        "F1",
        ("pyqt_shortcut", "qml_node_context_menu"),
        required_payload_keys=("node_id",),
        legacy_route_names=("action_show_help", "show_help", "show_help_for_node", "show_help_for_selected_node"),
    ),
    GraphActionSpec(
        GraphActionId.UNGROUP_NODE,
        "Ungroup Subnode",
        None,
        ("qml_node_context_menu",),
        destructive=True,
        required_payload_keys=("node_id",),
        legacy_route_names=("ungroup_subnode", "request_ungroup_node"),
    ),
    GraphActionSpec(
        GraphActionId.REMOVE_NODE,
        "Remove Node",
        None,
        ("qml_node_context_menu", "qml_node_delegate"),
        destructive=True,
        required_payload_keys=("node_id",),
        legacy_route_names=("remove_node", "delete", "request_remove_node"),
    ),
    GraphActionSpec(
        GraphActionId.DUPLICATE_NODE,
        "Duplicate Node",
        None,
        ("qml_node_delegate",),
        required_payload_keys=("node_id",),
        legacy_route_names=("duplicate", "request_duplicate_node"),
    ),
    GraphActionSpec(
        GraphActionId.EDIT_FLOW_EDGE_STYLE,
        "Edit Flow Edge...",
        None,
        ("qml_edge_context_menu",),
        required_payload_keys=("edge_id",),
        legacy_route_names=("edit_flow_edge", "request_edit_flow_edge_style"),
    ),
    GraphActionSpec(
        GraphActionId.EDIT_FLOW_EDGE_LABEL,
        "Edit Label...",
        None,
        ("qml_edge_context_menu",),
        required_payload_keys=("edge_id",),
        legacy_route_names=("edit_edge_label", "request_edit_flow_edge_label"),
    ),
    GraphActionSpec(
        GraphActionId.RESET_FLOW_EDGE_STYLE,
        "Reset Style",
        None,
        ("qml_edge_context_menu",),
        required_payload_keys=("edge_id",),
        legacy_route_names=("reset_flow_edge_style", "request_reset_flow_edge_style"),
    ),
    GraphActionSpec(
        GraphActionId.COPY_FLOW_EDGE_STYLE,
        "Copy Style",
        None,
        ("qml_edge_context_menu",),
        required_payload_keys=("edge_id",),
        legacy_route_names=("copy_flow_edge_style", "request_copy_flow_edge_style"),
    ),
    GraphActionSpec(
        GraphActionId.PASTE_FLOW_EDGE_STYLE,
        "Paste Style",
        None,
        ("qml_edge_context_menu",),
        required_payload_keys=("edge_id",),
        legacy_route_names=("paste_flow_edge_style", "request_paste_flow_edge_style"),
    ),
    GraphActionSpec(
        GraphActionId.REMOVE_EDGE,
        "Remove Connection",
        None,
        ("qml_edge_context_menu",),
        destructive=True,
        required_payload_keys=("edge_id",),
        legacy_route_names=("remove_edge", "request_remove_edge"),
    ),
)

GRAPH_ACTION_SPECS_BY_ID: dict[GraphActionId, GraphActionSpec] = {
    spec.action_id: spec for spec in GRAPH_ACTION_SPECS
}
GRAPH_ACTION_IDS: frozenset[str] = frozenset(spec.action_id.value for spec in GRAPH_ACTION_SPECS)
GRAPH_ACTION_LEGACY_ROUTE_NAMES: frozenset[str] = frozenset(
    route for spec in GRAPH_ACTION_SPECS for route in spec.legacy_route_names
)
GRAPH_ACTION_LITERAL_NAMES: frozenset[str] = GRAPH_ACTION_IDS | GRAPH_ACTION_LEGACY_ROUTE_NAMES

# P01 keeps the inventory exhaustive for current high-level QML action literals.
LOW_LEVEL_QML_ACTION_EXCEPTIONS: frozenset[str] = frozenset()


def graph_action_spec(action_id: GraphActionId | str) -> GraphActionSpec:
    return GRAPH_ACTION_SPECS_BY_ID[GraphActionId(action_id)]


__all__ = [
    "GRAPH_ACTION_IDS",
    "GRAPH_ACTION_LEGACY_ROUTE_NAMES",
    "GRAPH_ACTION_LITERAL_NAMES",
    "GRAPH_ACTION_SPECS",
    "GRAPH_ACTION_SPECS_BY_ID",
    "LOW_LEVEL_QML_ACTION_EXCEPTIONS",
    "GraphActionId",
    "GraphActionSpec",
    "graph_action_spec",
]
