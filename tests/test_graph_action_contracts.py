from __future__ import annotations

import ast
import re
from pathlib import Path

from ea_node_editor.ui.shell.graph_action_contracts import (
    GRAPH_ACTION_LITERAL_NAMES,
    GRAPH_ACTION_SPECS,
    GRAPH_ACTION_SPECS_BY_LITERAL,
    LOW_LEVEL_QML_ACTION_EXCEPTIONS,
    GraphActionId,
    graph_action_spec,
    normalize_graph_action_id,
    normalize_graph_action_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_MENUS_QML = (
    REPO_ROOT
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph_canvas"
    / "GraphCanvasContextMenus.qml"
)
NODE_DELEGATE_QML = (
    REPO_ROOT
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph_canvas"
    / "GraphCanvasNodeDelegate.qml"
)
ROOT_BINDINGS_QML = (
    REPO_ROOT
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph_canvas"
    / "GraphCanvasRootBindings.qml"
)
WINDOW_ACTIONS = REPO_ROOT / "ea_node_editor" / "ui" / "shell" / "window_actions.py"

RETIRED_QML_COMMAND_BRIDGE_ACTION_SLOTS = {
    "request_edit_flow_edge_style",
    "request_edit_flow_edge_label",
    "request_reset_flow_edge_style",
    "request_copy_flow_edge_style",
    "request_paste_flow_edge_style",
    "request_remove_edge",
    "request_publish_custom_workflow_from_node",
    "request_open_comment_peek",
    "request_edit_passive_node_style",
    "request_reset_passive_node_style",
    "request_copy_passive_node_style",
    "request_paste_passive_node_style",
    "request_ungroup_node",
    "request_remove_node",
    "request_duplicate_node",
    "request_wrap_selected_nodes_in_comment_backdrop",
}


def _pyqt_graph_actions_from_contract() -> dict[str, GraphActionId]:
    actions: dict[str, GraphActionId] = {}
    for spec in GRAPH_ACTION_SPECS:
        if not any(surface.startswith("pyqt_") for surface in spec.surfaces):
            continue
        action_routes = [route for route in spec.legacy_route_names if route.startswith("action_")]
        assert len(action_routes) == 1, spec.action_id.value
        actions[action_routes[0]] = spec.action_id
    return actions


PYQT_GRAPH_ACTIONS: dict[str, GraphActionId] = _pyqt_graph_actions_from_contract()

PYQT_MENU_ACTION_EXCEPTIONS = {
    "action_undo",
    "action_redo",
    "action_snap_to_grid",
    "action_graph_search",
    "action_toggle_script_editor",
    "action_show_port_labels",
    "action_show_tooltips",
    "action_frame_all",
    "action_frame_selection",
    "action_center_selection",
}

STANDARD_KEY_SHORTCUTS = {
    "Copy": "Ctrl+C",
    "Cut": "Ctrl+X",
    "Paste": "Ctrl+V",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _qml_context_action_ids() -> set[str]:
    return set(re.findall(r'"actionId"\s*:\s*"([^"]+)"', _source(CONTEXT_MENUS_QML)))


def _qml_node_delegate_action_literals() -> set[str]:
    source = _source(NODE_DELEGATE_QML)
    return set(re.findall(r'normalized\s*===\s*"([^"]+)"', source))


def _window_action_assignments() -> dict[str, ast.Call]:
    tree = ast.parse(_source(WINDOW_ACTIONS), filename=str(WINDOW_ACTIONS))
    assignments: dict[str, ast.Call] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if not _is_qaction_constructor(node.value):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            if isinstance(target.value, ast.Name) and target.value.id == "window":
                assignments[target.attr] = node.value
    return assignments


def _window_graph_action_contract_assignments() -> dict[str, GraphActionId]:
    tree = ast.parse(_source(WINDOW_ACTIONS), filename=str(WINDOW_ACTIONS))
    assignments: dict[str, GraphActionId] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id != "_create_graph_action":
            continue
        if len(call.args) != 2:
            continue
        action_id = _graph_action_id_from_ast(call.args[1])
        if action_id is None:
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            if isinstance(target.value, ast.Name) and target.value.id == "window":
                assignments[target.attr] = action_id
    return assignments


def _graph_action_id_from_ast(node: ast.AST) -> GraphActionId | None:
    if not isinstance(node, ast.Attribute):
        return None
    if not isinstance(node.value, ast.Name) or node.value.id != "GraphActionId":
        return None
    return GraphActionId[node.attr]


def _window_action_shortcuts() -> dict[str, str]:
    tree = ast.parse(_source(WINDOW_ACTIONS), filename=str(WINDOW_ACTIONS))
    shortcuts: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Attribute):
            continue
        if call.func.attr not in {"setShortcut", "setShortcuts"}:
            continue
        owner = call.func.value
        if not isinstance(owner, ast.Attribute):
            continue
        if not isinstance(owner.value, ast.Name) or owner.value.id != "window":
            continue
        shortcut = _shortcut_from_call(call)
        if shortcut is not None:
            shortcuts[owner.attr] = shortcut
    return shortcuts


def _window_graph_menu_actions() -> set[str]:
    tree = ast.parse(_source(WINDOW_ACTIONS), filename=str(WINDOW_ACTIONS))
    actions: set[str] = set()
    graph_menu_names = {"edit_menu", "layout_menu", "view_menu"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "addAction":
            continue
        if not isinstance(call.func.value, ast.Name) or call.func.value.id not in graph_menu_names:
            continue
        if not call.args:
            continue
        action = call.args[0]
        if not isinstance(action, ast.Attribute):
            continue
        if isinstance(action.value, ast.Name) and action.value.id == "window":
            actions.add(action.attr)
    return actions - PYQT_MENU_ACTION_EXCEPTIONS


def _is_qaction_constructor(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == "QAction"


def _shortcut_from_call(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first = call.args[0]
    if call.func.attr == "setShortcuts":
        return None
    if isinstance(first, ast.Attribute):
        return _standard_key_shortcut(first)
    if not isinstance(first, ast.Call):
        return None
    if not isinstance(first.func, ast.Name) or first.func.id != "QKeySequence":
        return None
    if not first.args:
        return None
    value = first.args[0]
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Attribute):
        return _standard_key_shortcut(value)
    return None


def _standard_key_shortcut(value: ast.Attribute) -> str | None:
    if not isinstance(value.value, ast.Attribute):
        return None
    if not isinstance(value.value.value, ast.Name) or value.value.value.id != "QKeySequence":
        return None
    if value.value.attr != "StandardKey":
        return None
    return STANDARD_KEY_SHORTCUTS.get(value.attr)


def _qaction_label(call: ast.Call) -> str:
    assert call.args, "QAction constructor is missing text"
    text_arg = call.args[0]
    assert isinstance(text_arg, ast.Constant) and isinstance(text_arg.value, str)
    return text_arg.value


def test_graph_action_ids_are_unique() -> None:
    ids = [spec.action_id.value for spec in GRAPH_ACTION_SPECS]
    assert len(ids) == len(set(ids))


def test_qml_action_literals_are_represented_by_contract() -> None:
    qml_literals = _qml_context_action_ids() | _qml_node_delegate_action_literals()
    missing = qml_literals - GRAPH_ACTION_LITERAL_NAMES - LOW_LEVEL_QML_ACTION_EXCEPTIONS
    assert missing == set()


def test_low_level_qml_action_exceptions_are_current() -> None:
    qml_literals = _qml_context_action_ids() | _qml_node_delegate_action_literals()
    assert LOW_LEVEL_QML_ACTION_EXCEPTIONS <= qml_literals


def test_qml_graph_canvas_actions_route_through_graph_action_bridge() -> None:
    context_source = _source(CONTEXT_MENUS_QML)
    delegate_source = _source(NODE_DELEGATE_QML)
    root_bindings_source = _source(ROOT_BINDINGS_QML)

    assert "property var graphActionBridge: null" in root_bindings_source
    assert "readonly property var graphActionBridgeRef: root.graphActionBridge || null" in root_bindings_source
    assert "property var graphActionBridge: null" in context_source
    assert "root.graphActionBridge.trigger_graph_action(actionId, payload || ({}))" in context_source
    assert 'var payload = { "node_id": String(nodeId || "") };' in delegate_source
    assert "graphActionBridge.trigger_graph_action(actionId, payload)" in delegate_source
    assert "payload.inline_title_edit = true" in delegate_source
    assert "canvasItem.graphActionBridgeRef" in delegate_source

    retired_hits = {
        slot
        for slot in RETIRED_QML_COMMAND_BRIDGE_ACTION_SLOTS
        if f".{slot}" in context_source or f".{slot}" in delegate_source
    }
    assert retired_hits == set()


def test_qml_graph_action_bridge_payloads_use_contract_keys() -> None:
    context_source = _source(CONTEXT_MENUS_QML)
    delegate_source = _source(NODE_DELEGATE_QML)

    assert 'return { "edge_id": edgeId }' in context_source
    assert 'return { "node_id": nodeId }' in context_source
    assert '{ "node_id": String(nodeId || "") }' in delegate_source
    assert "inline_title_edit" in context_source
    assert "inline_title_edit" in delegate_source


def test_pyqt_graph_action_declarations_use_contract_ids() -> None:
    assignments = _window_graph_action_contract_assignments()
    missing_actions = set(PYQT_GRAPH_ACTIONS) - set(assignments)
    assert missing_actions == set()
    assert assignments == PYQT_GRAPH_ACTIONS


def test_pyqt_graph_action_factory_uses_contract_labels_shortcuts_and_controller() -> None:
    source = _source(WINDOW_ACTIONS)
    assert "graph_action_spec(action_id)" in source
    assert "QAction(str(spec.label or action_id.value), window)" in source
    assert "action.setShortcut(QKeySequence(spec.shortcut))" in source
    assert "controller.trigger(action_id.value)" in source


def test_pyqt_graph_menu_actions_are_mapped_to_contract() -> None:
    missing = _window_graph_menu_actions() - set(PYQT_GRAPH_ACTIONS)
    assert missing == set()


def test_pyqt_graph_action_declarations_are_in_legacy_routes() -> None:
    assignments = _window_graph_action_contract_assignments()
    missing = {
        pyqt_action_name
        for pyqt_action_name, action_id in assignments.items()
        if pyqt_action_name not in graph_action_spec(action_id).legacy_route_names
    }
    assert missing == set()


def test_required_payload_keys_are_declared_for_payload_actions() -> None:
    payload_action_ids = {
        GraphActionId.OPEN_ADDON_MANAGER_FOR_NODE,
        GraphActionId.OPEN_SUBNODE_SCOPE,
        GraphActionId.PUBLISH_CUSTOM_WORKFLOW_FROM_NODE,
        GraphActionId.OPEN_COMMENT_PEEK,
        GraphActionId.EDIT_PASSIVE_NODE_STYLE,
        GraphActionId.RESET_PASSIVE_NODE_STYLE,
        GraphActionId.COPY_PASSIVE_NODE_STYLE,
        GraphActionId.PASTE_PASSIVE_NODE_STYLE,
        GraphActionId.RENAME_NODE,
        GraphActionId.UNGROUP_NODE,
        GraphActionId.REMOVE_NODE,
        GraphActionId.DUPLICATE_NODE,
        GraphActionId.EDIT_FLOW_EDGE_STYLE,
        GraphActionId.EDIT_FLOW_EDGE_LABEL,
        GraphActionId.RESET_FLOW_EDGE_STYLE,
        GraphActionId.COPY_FLOW_EDGE_STYLE,
        GraphActionId.PASTE_FLOW_EDGE_STYLE,
        GraphActionId.REMOVE_EDGE,
    }
    missing = {
        action_id.value
        for action_id in payload_action_ids
        if not graph_action_spec(action_id).required_payload_keys
    }
    assert missing == set()


def test_graph_action_literals_resolve_to_canonical_action_ids() -> None:
    assert normalize_graph_action_id("remove_edge") is GraphActionId.REMOVE_EDGE
    assert normalize_graph_action_id("request_remove_edge") is GraphActionId.REMOVE_EDGE
    assert normalize_graph_action_id(GraphActionId.REMOVE_EDGE) is GraphActionId.REMOVE_EDGE
    assert normalize_graph_action_id("not_a_graph_action") is None
    assert GRAPH_ACTION_SPECS_BY_LITERAL["show_help"].action_id is GraphActionId.SHOW_NODE_HELP


def test_graph_action_payload_normalization_rejects_invalid_required_payloads() -> None:
    assert normalize_graph_action_payload(GraphActionId.REMOVE_EDGE, {"edge_id": " edge-1 "}) == {
        "edge_id": "edge-1"
    }
    assert normalize_graph_action_payload("remove_edge", {"edge_id": ""}) is None
    assert normalize_graph_action_payload("remove_edge", {"node_id": "node-1"}) is None
    assert normalize_graph_action_payload("remove_edge", {"edge_id": 123}) is None
    assert normalize_graph_action_payload("copy_selection", None) == {}
