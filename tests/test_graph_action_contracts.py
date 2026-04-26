from __future__ import annotations

import ast
import re
from tempfile import TemporaryDirectory
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
from ea_node_editor.ui.folder_explorer import FolderExplorerFilesystemService
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge


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
INPUT_LAYERS_QML = (
    REPO_ROOT
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph_canvas"
    / "GraphCanvasInputLayers.qml"
)
ACTION_ROUTER_QML = (
    REPO_ROOT
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph_canvas"
    / "GraphCanvasActionRouter.qml"
)
WINDOW_ACTIONS = REPO_ROOT / "ea_node_editor" / "ui" / "shell" / "window_actions.py"
WORKSPACE_GRAPH_ACTIONS = (
    REPO_ROOT
    / "ea_node_editor"
    / "ui"
    / "shell"
    / "window_state"
    / "workspace_graph_actions.py"
)

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
P03_RETIRED_SHELL_GRAPH_ACTION_FACADE_SLOTS = {
    "request_navigate_scope_parent",
    "request_navigate_scope_root",
    "request_align_selection_left",
    "request_align_selection_right",
    "request_align_selection_top",
    "request_align_selection_bottom",
    "request_distribute_selection_horizontally",
    "request_distribute_selection_vertically",
    "request_connect_selected_nodes",
    "request_duplicate_selected_nodes",
    "request_wrap_selected_nodes_in_comment_backdrop",
    "request_group_selected_nodes",
    "request_ungroup_selected_nodes",
    "request_copy_selected_nodes",
    "request_cut_selected_nodes",
    "request_paste_selected_nodes",
    "request_delete_selected_graph_items",
}

FOLDER_EXPLORER_ACTION_PAYLOAD_KEYS = {
    GraphActionId.FOLDER_EXPLORER_LIST: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_NAVIGATE: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_REFRESH: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_SET_SORT: ("node_id", "path", "sort_key"),
    GraphActionId.FOLDER_EXPLORER_SET_SEARCH: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_OPEN: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_OPEN_IN_NEW_WINDOW: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_NEW_FOLDER: ("node_id", "path", "name"),
    GraphActionId.FOLDER_EXPLORER_RENAME: ("node_id", "path", "new_name"),
    GraphActionId.FOLDER_EXPLORER_DELETE: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_CUT: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_COPY: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_PASTE: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_COPY_PATH: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_PROPERTIES: ("node_id", "path"),
    GraphActionId.FOLDER_EXPLORER_SEND_TO_COREX_PATH_POINTER: ("node_id", "path"),
}


class _FolderExplorerConfirmationProbe:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.calls: list[tuple[str, str, str]] = []

    def confirm_folder_explorer_operation(self, operation: str, path: str, target_path: str = "") -> bool:
        self.calls.append((operation, path, target_path))
        return self.accepted


class _FolderExplorerClipboardProbe:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:  # noqa: N802
        self.text = text


class _FolderExplorerOpenProbe:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted
        self.paths: list[str] = []

    def open_folder_explorer_path(self, path: str) -> bool:
        self.paths.append(path)
        return self.accepted


class _FolderExplorerSceneCommandProbe:
    def __init__(self) -> None:
        self.added_nodes: list[tuple[str, float, float, str]] = []
        self.properties: list[tuple[str, str, object]] = []
        self.bulk_properties: list[tuple[str, dict[str, object]]] = []
        self._serial = 0

    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        self._serial += 1
        node_id = f"node-{self._serial}"
        self.added_nodes.append((type_id, float(x), float(y), node_id))
        return node_id

    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        self.properties.append((node_id, key, value))

    def set_node_properties(self, node_id: str, values: dict[str, object]) -> bool:
        self.bulk_properties.append((node_id, dict(values)))
        return True


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
    return set(re.findall(r'"actionId"\s*:\s*"([^"]+)"', _source(ACTION_ROUTER_QML)))


def _qml_node_delegate_action_literals() -> set[str]:
    return set(re.findall(r'"actionId"\s*:\s*"([^"]+)"', _source(ACTION_ROUTER_QML)))


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
    canvas_source = _source(REPO_ROOT / "ea_node_editor" / "ui_qml" / "components" / "GraphCanvas.qml")
    context_source = _source(CONTEXT_MENUS_QML)
    delegate_source = _source(NODE_DELEGATE_QML)
    root_bindings_source = _source(ROOT_BINDINGS_QML)
    input_layers_source = _source(INPUT_LAYERS_QML)
    action_router_source = _source(ACTION_ROUTER_QML)

    assert "property var graphActionBridge: null" in root_bindings_source
    assert "readonly property var graphActionBridgeRef: root.graphActionBridge || null" in root_bindings_source
    assert "GraphCanvasComponents.GraphCanvasActionRouter {" in canvas_source
    assert "readonly property var canvasActionRouter: actionRouter" in canvas_source
    assert "canvasActionRouter: root.canvasActionRouter" in canvas_source
    assert "property var graphActionBridge: null" in action_router_source
    assert "bridge.trigger_graph_action(String(actionId || \"\"), payload || ({}))" in action_router_source
    assert "property var canvasActionRouter: null" in context_source
    assert "function handleNodeContextAction(actionId)" in action_router_source
    assert "function handleEdgeContextAction(actionId)" in action_router_source
    assert "function handleSelectionContextAction(actionId)" in action_router_source
    assert "actionRouter.handleNodeDelegateAction(nodeCard, nodeId, normalized)" in delegate_source
    assert "payload.inline_title_edit = true" in delegate_source
    assert "canvasItem.graphActionBridgeRef" in delegate_source
    assert "property var graphActionBridge: null" in input_layers_source
    assert "root.canvasActionRouter.deleteSelection(edgeIds)" in input_layers_source
    assert "root.canvasActionRouter.navigateScopeParent()" in input_layers_source
    assert "root.canvasActionRouter.navigateScopeRoot()" in input_layers_source
    assert "root.canvasActionRouter.closeCommentPeekIfActive()" in input_layers_source
    assert "readonly property var shellContextRef" in context_source
    assert "readonly property var shellContextRef" in input_layers_source
    assert "typeof viewerSessionBridge" not in delegate_source
    assert "property var shellCommandBridge" not in input_layers_source

    retired_hits = {
        slot
        for slot in RETIRED_QML_COMMAND_BRIDGE_ACTION_SLOTS
        if f".{slot}" in context_source or f".{slot}" in delegate_source
    }
    assert retired_hits == set()


def test_qml_graph_action_bridge_payloads_use_contract_keys() -> None:
    context_source = _source(CONTEXT_MENUS_QML)
    delegate_source = _source(NODE_DELEGATE_QML)
    action_router_source = _source(ACTION_ROUTER_QML)

    assert 'return edgeId.length ? { "edge_id": edgeId } : null;' in action_router_source
    assert 'var payload = { "node_id": nodeId };' in action_router_source
    assert '{ "node_id": String(nodeId || "") }' in delegate_source
    assert "inline_title_edit" in action_router_source
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


def test_p03_shell_graph_action_facades_are_retired_from_window_state_helpers() -> None:
    source = _source(WORKSPACE_GRAPH_ACTIONS)
    retired_definitions = {
        slot_name
        for slot_name in P03_RETIRED_SHELL_GRAPH_ACTION_FACADE_SLOTS
        if f"def {slot_name}" in source
    }
    assert retired_definitions == set()
    assert "graph_action_controller.trigger(GraphActionId" not in source


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


def test_folder_explorer_action_contract_declares_stable_commands_and_payload_keys() -> None:
    for action_id, payload_keys in FOLDER_EXPLORER_ACTION_PAYLOAD_KEYS.items():
        spec = graph_action_spec(action_id)
        assert spec.required_payload_keys == payload_keys
        assert any(surface.startswith("qml_folder_explorer") for surface in spec.surfaces)

    assert graph_action_spec(GraphActionId.FOLDER_EXPLORER_DELETE).destructive is True
    assert graph_action_spec(GraphActionId.FOLDER_EXPLORER_SEND_TO_COREX_PATH_POINTER).destructive is False
    assert normalize_graph_action_id("folderExplorerSendToCorexPathPointer") is (
        GraphActionId.FOLDER_EXPLORER_SEND_TO_COREX_PATH_POINTER
    )
    assert normalize_graph_action_payload(
        "folder_explorer_new_folder",
        {"node_id": " folder-node ", "path": " C:/tmp ", "name": " Created "},
    ) == {"node_id": "folder-node", "path": "C:/tmp", "name": "Created"}
    assert normalize_graph_action_payload(
        "folder_explorer_set_sort",
        {"node_id": "folder-node", "path": "C:/tmp"},
    ) is None


def test_qml_folder_explorer_actions_route_through_canvas_command_bridge() -> None:
    action_router_source = _source(ACTION_ROUTER_QML)
    surface_bridge_source = _source(
        REPO_ROOT
        / "ea_node_editor"
        / "ui_qml"
        / "components"
        / "graph_canvas"
        / "GraphCanvasNodeSurfaceBridge.qml"
    )

    assert "readonly property var folderExplorerActionDescriptors" in action_router_source
    assert '"sendToCorexPathPointer": { "actionId": "folder_explorer_send_to_corex_path_pointer" }' in (
        action_router_source
    )
    assert "function requestFolderExplorerAction(actionId, payload)" in action_router_source
    assert "bridge.request_folder_explorer_action(String(actionId || \"\"), payload || ({}))" in action_router_source
    assert "function requestFolderExplorerAction(nodeId, command, payload)" in surface_bridge_source
    assert "function createFolderExplorerPathPointer(nodeId, path, sceneX, sceneY)" in surface_bridge_source
    assert '"type_id": "io.path_pointer"' in surface_bridge_source


def test_folder_explorer_bridge_lists_and_updates_current_path_through_scene_mutation() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        child = root / "Child"
        child.mkdir()
        (child / "note.txt").write_text("hello", encoding="utf-8")
        scene = _FolderExplorerSceneCommandProbe()
        bridge = GraphCanvasCommandBridge(
            scene_bridge=scene,
            folder_explorer_service=FolderExplorerFilesystemService(),
            folder_explorer_confirmation_source=_FolderExplorerConfirmationProbe(True),
        )

        result = bridge.request_folder_explorer_action(
            "folder_explorer_navigate",
            {"node_id": "folder-node", "path": str(child), "sort_key": "name"},
        )

        assert result["success"] is True
        assert result["path"] == str(child.resolve())
        assert result["listing"]["directory_path"] == str(child.resolve())
        assert [entry["name"] for entry in result["listing"]["entries"]] == ["note.txt"]
        assert scene.properties == [("folder-node", "current_path", str(child.resolve()))]


def test_folder_explorer_bridge_declined_delete_does_not_call_service_mutation() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        target = root / "delete-me.txt"
        target.write_text("keep", encoding="utf-8")
        confirmation = _FolderExplorerConfirmationProbe(False)
        bridge = GraphCanvasCommandBridge(
            folder_explorer_service=FolderExplorerFilesystemService(),
            folder_explorer_confirmation_source=confirmation,
        )

        result = bridge.request_folder_explorer_action(
            "folder_explorer_delete",
            {"node_id": "folder-node", "path": str(target), "current_path": str(root)},
        )

        assert result["success"] is False
        assert result["cancelled"] is True
        assert result["error"]["code"] == "cancelled"
        assert target.exists()
        assert confirmation.calls == [("delete", str(target), "")]


def test_folder_explorer_bridge_confirmed_mutation_returns_refreshed_listing() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        confirmation = _FolderExplorerConfirmationProbe(True)
        bridge = GraphCanvasCommandBridge(
            folder_explorer_service=FolderExplorerFilesystemService(),
            folder_explorer_confirmation_source=confirmation,
        )

        result = bridge.request_folder_explorer_action(
            "folder_explorer_new_folder",
            {"node_id": "folder-node", "path": str(root), "name": "Created"},
        )

        assert result["success"] is True
        assert (root / "Created").is_dir()
        assert result["entry"]["kind"] == "folder"
        assert [entry["name"] for entry in result["listing"]["entries"]] == ["Created"]
        assert confirmation.calls == [("new_folder", str(root), str(root / "Created"))]


def test_folder_explorer_bridge_confirmed_rename_cut_and_paste_mutate_only_temp_paths() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "source.txt"
        source.write_text("move me", encoding="utf-8")
        sibling = root / "sibling.txt"
        sibling.write_text("keep me", encoding="utf-8")
        destination = root / "Destination"
        destination.mkdir()
        renamed = root / "renamed.txt"
        confirmation = _FolderExplorerConfirmationProbe(True)
        bridge = GraphCanvasCommandBridge(
            folder_explorer_service=FolderExplorerFilesystemService(),
            folder_explorer_confirmation_source=confirmation,
        )

        rename_result = bridge.request_folder_explorer_action(
            "folder_explorer_rename",
            {"node_id": "folder-node", "path": str(source), "new_name": "renamed.txt", "current_path": str(root)},
        )
        cut_result = bridge.request_folder_explorer_action(
            "folder_explorer_cut",
            {"node_id": "folder-node", "path": str(renamed)},
        )
        paste_result = bridge.request_folder_explorer_action(
            "folder_explorer_paste",
            {"node_id": "folder-node", "path": str(destination)},
        )

        assert rename_result["success"] is True
        assert cut_result["success"] is True
        assert paste_result["success"] is True
        assert not source.exists()
        assert not renamed.exists()
        assert (destination / "renamed.txt").read_text(encoding="utf-8") == "move me"
        assert sibling.read_text(encoding="utf-8") == "keep me"
        assert paste_result["listing"]["directory_path"] == str(destination.resolve(strict=False))
        assert [entry["name"] for entry in paste_result["listing"]["entries"]] == ["renamed.txt"]
        assert confirmation.calls == [
            ("rename", str(source), str(renamed)),
            ("cut", str(renamed), ""),
            ("paste", str(destination), ""),
        ]


def test_folder_explorer_bridge_copy_path_and_open_use_shell_seams() -> None:
    with TemporaryDirectory() as temporary_directory:
        target = Path(temporary_directory) / "open-me.txt"
        target.write_text("hello", encoding="utf-8")
        clipboard = _FolderExplorerClipboardProbe()
        opener = _FolderExplorerOpenProbe()
        bridge = GraphCanvasCommandBridge(
            folder_explorer_service=FolderExplorerFilesystemService(),
            folder_explorer_clipboard_source=clipboard,
            folder_explorer_open_source=opener,
        )

        copy_result = bridge.request_folder_explorer_action(
            "folder_explorer_copy_path",
            {"node_id": "folder-node", "path": str(target)},
        )
        open_result = bridge.request_folder_explorer_action(
            "folder_explorer_open",
            {"node_id": "folder-node", "path": str(target)},
        )

        assert copy_result["success"] is True
        assert clipboard.text == str(target.resolve())
        assert open_result["success"] is True
        assert opener.paths == [str(target.resolve())]


def test_folder_explorer_bridge_creates_path_pointer_and_new_explorer_nodes() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        target_file = root / "selected.txt"
        target_file.write_text("hello", encoding="utf-8")
        scene = _FolderExplorerSceneCommandProbe()
        bridge = GraphCanvasCommandBridge(
            scene_bridge=scene,
            folder_explorer_service=FolderExplorerFilesystemService(),
        )

        path_pointer_result = bridge.request_folder_explorer_action(
            "folder_explorer_send_to_corex_path_pointer",
            {"node_id": "folder-node", "path": str(target_file), "scene_x": 120, "scene_y": 240},
        )
        explorer_result = bridge.request_folder_explorer_action(
            "folder_explorer_open_in_new_window",
            {"node_id": "folder-node", "path": str(root), "scene_x": 360, "scene_y": 480},
        )

        assert path_pointer_result["success"] is True
        assert path_pointer_result["created_type_id"] == "io.path_pointer"
        assert explorer_result["success"] is True
        assert explorer_result["created_type_id"] == "io.folder_explorer"
        assert scene.added_nodes == [
            ("io.path_pointer", 120.0, 240.0, "node-1"),
            ("io.folder_explorer", 360.0, 480.0, "node-2"),
        ]
        assert scene.bulk_properties == [
            ("node-1", {"path": str(target_file.resolve()), "mode": "file"}),
            ("node-2", {"current_path": str(root.resolve())}),
        ]


def test_folder_explorer_bridge_accepts_qml_command_aliases_for_drag_and_new_window() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        target_folder = root / "Selected Folder"
        target_folder.mkdir()
        scene = _FolderExplorerSceneCommandProbe()
        bridge = GraphCanvasCommandBridge(
            scene_bridge=scene,
            folder_explorer_service=FolderExplorerFilesystemService(),
        )

        drag_result = bridge.request_folder_explorer_action(
            "sendToCorexPathPointer",
            {"node_id": "folder-node", "path": str(target_folder), "scene_x": 10, "scene_y": 20},
        )
        new_window_result = bridge.request_folder_explorer_action(
            "openInNewWindow",
            {"node_id": "folder-node", "path": str(root), "scene_x": 30, "scene_y": 40},
        )

        assert drag_result["success"] is True
        assert drag_result["created_type_id"] == "io.path_pointer"
        assert drag_result["mode"] == "folder"
        assert new_window_result["success"] is True
        assert new_window_result["created_type_id"] == "io.folder_explorer"
        assert scene.added_nodes == [
            ("io.path_pointer", 10.0, 20.0, "node-1"),
            ("io.folder_explorer", 30.0, 40.0, "node-2"),
        ]
        assert scene.bulk_properties == [
            ("node-1", {"path": str(target_folder.resolve()), "mode": "folder"}),
            ("node-2", {"current_path": str(root.resolve())}),
        ]
