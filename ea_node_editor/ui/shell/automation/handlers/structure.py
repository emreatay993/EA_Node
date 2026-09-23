# Purpose: Structure automation handlers: Group backdrops, subnodes (create/ungroup/pins), scope navigation, selection, align/distribute.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_structure.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ea_node_editor.automation.errors import INVALID_PARAMS, AutomationOpError, no_effect
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    is_subnode_pin_type,
    is_subnode_shell_type,
)
from ea_node_editor.ui.shell.automation.context import AutomationContext

ALIGNMENTS: dict[str, str] = {
    "align_left": "left",
    "align_right": "right",
    "align_top": "top",
    "align_bottom": "bottom",
}
DISTRIBUTIONS: dict[str, str] = {
    "distribute_horizontal": "horizontal",
    "distribute_vertical": "vertical",
}
PIN_TYPE_BY_DIRECTION: dict[str, str] = {"in": SUBNODE_INPUT_TYPE_ID, "out": SUBNODE_OUTPUT_TYPE_ID}


# ----------------------------------------------------------------- helpers


def _unique_ids(values: Iterable[Any]) -> list[str]:
    ordered: list[str] = []
    for value in values or ():
        node_id = str(value or "").strip()
        if node_id and node_id not in ordered:
            ordered.append(node_id)
    return ordered


def _nodes_in_scope(context: AutomationContext, node_ids: Iterable[str]) -> list[NodeInstance]:
    return [context.require_node_in_scope(node_id) for node_id in node_ids]


def _require_shell(context: AutomationContext, node: NodeInstance, op: str) -> NodeInstance:
    if not is_subnode_shell_type(node.type_id):
        raise AutomationOpError(
            INVALID_PARAMS,
            f"{op}: node '{node.node_id}' is a {node.type_id}, not a subnode shell.",
            hint="Pass the shell_node_id returned by subnode.create (type core.subnode).",
            details={"node_id": node.node_id, "type_id": node.type_id, "op": op},
        )
    return node


def _apply_title(context: AutomationContext, op: str, node_id: str, title: Any) -> None:
    """Set a node title through the verified scene path; fall back to the persisted title property."""
    normalized = str(title if title is not None else "").strip()
    if not normalized:
        return
    scene = context.scene
    scene.set_node_title(node_id, normalized)
    node = context.require_node(node_id)
    if node.title == normalized:
        return
    scene.set_node_property(node_id, "title", normalized)
    node = context.require_node(node_id)
    if node.title != normalized and str(node.properties.get("title", "")) != normalized:
        raise no_effect(op, f"title '{normalized}' was not applied to node '{node_id}'", details={"node_id": node_id, "title": normalized})


def _children_of(context: AutomationContext, parent_node_id: str) -> list[NodeInstance]:
    workspace = context.active_workspace()
    return [node for node in workspace.nodes.values() if (node.parent_node_id or "") == parent_node_id]


def _pin_ids(children: Iterable[NodeInstance], pin_type_id: str) -> list[str]:
    return [node.node_id for node in children if str(node.type_id) == pin_type_id]


# ---------------------------------------------------------------- handlers


def wrap_group(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids = _unique_ids(params["node_ids"])
    _nodes_in_scope(context, node_ids)
    before = context.node_id_set()
    group_id = str(context.scene.wrap_node_ids_in_group_backdrop(list(node_ids)) or "").strip()
    new_ids = context.new_ids_since(before)
    if not group_id and len(new_ids) == 1:
        group_id = new_ids[0]
    group = context.node_or_none(group_id) if group_id else None
    if group is None:
        raise no_effect(
            "group.wrap",
            "the scene did not create a Group backdrop",
            details={"node_ids": node_ids, "new_node_ids": new_ids, "scope_path": context.scope_path()},
        )
    _apply_title(context, "group.wrap", group_id, params.get("title"))
    group = context.require_node(group_id)
    return {"group_node_id": group_id, "member_node_ids": node_ids, "group": context.node_summary(group)}


def create_subnode(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids = _unique_ids(params["node_ids"])
    _nodes_in_scope(context, node_ids)
    if len(node_ids) < 2:
        raise AutomationOpError(
            INVALID_PARAMS,
            "subnode.create needs at least two distinct nodes in the open scope.",
            details={"node_ids": node_ids, "problems": ["node_ids: must contain at least 2 distinct ids"]},
        )
    scope_parent = context.scope_parent_id()
    before = context.node_id_set()
    with context.with_selection(node_ids):
        selected = context.selected_node_ids()
        missing = [node_id for node_id in node_ids if node_id not in selected]
        if missing:
            raise no_effect("subnode.create", "the scene refused to select some nodes", details={"missing_node_ids": missing})
        grouped = bool(context.scene.group_selected_nodes())
    new_ids = context.new_ids_since(before)
    workspace = context.active_workspace()
    shells = [
        node_id
        for node_id in new_ids
        if is_subnode_shell_type(workspace.nodes[node_id].type_id)
        and (workspace.nodes[node_id].parent_node_id or None) == scope_parent
    ]
    if not grouped or len(shells) != 1:
        raise no_effect(
            "subnode.create",
            "the scene did not collapse the nodes into a subnode shell",
            details={"node_ids": node_ids, "new_node_ids": new_ids, "owner_result": grouped},
        )
    shell_id = shells[0]
    children = _children_of(context, shell_id)
    _apply_title(context, "subnode.create", shell_id, params.get("title"))
    shell = context.require_node(shell_id)
    return {
        "shell_node_id": shell_id,
        "input_pin_ids": _pin_ids(children, SUBNODE_INPUT_TYPE_ID),
        "output_pin_ids": _pin_ids(children, SUBNODE_OUTPUT_TYPE_ID),
        "member_node_ids": [node.node_id for node in children if not is_subnode_pin_type(node.type_id)],
        "shell": context.node_summary(shell),
    }


def ungroup_subnode(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    shell = _require_shell(context, context.require_node_in_scope(str(params["shell_node_id"])), "subnode.ungroup")
    shell_id = shell.node_id
    scope_parent = context.scope_parent_id()
    workspace = context.active_workspace()
    parents_before = {node_id: (node.parent_node_id or None) for node_id, node in workspace.nodes.items()}
    with context.with_selection([shell_id]):
        ungrouped = bool(context.scene.ungroup_selected_subnode())
    if not ungrouped or context.node_or_none(shell_id) is not None:
        raise no_effect(
            "subnode.ungroup",
            f"the scene did not dissolve shell '{shell_id}'",
            details={"shell_node_id": shell_id, "owner_result": ungrouped},
        )
    restored = [
        node_id
        for node_id, node in context.active_workspace().nodes.items()
        if node_id in parents_before
        and parents_before[node_id] != (node.parent_node_id or None)
        and (node.parent_node_id or None) == scope_parent
    ]
    return {"restored_node_ids": restored, "removed_shell_node_id": shell_id}


def add_subnode_pin(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    shell = _require_shell(context, context.require_node(str(params["shell_node_id"])), "subnode.add_pin")
    direction = str(params["direction"]).strip().lower()
    pin_type_id = PIN_TYPE_BY_DIRECTION[direction]
    pin_id = str(context.scene.add_subnode_shell_pin(shell.node_id, pin_type_id) or "").strip()
    pin = context.node_or_none(pin_id) if pin_id else None
    if pin is None or (pin.parent_node_id or "") != shell.node_id or str(pin.type_id) != pin_type_id:
        raise no_effect(
            "subnode.add_pin",
            f"the scene did not add a {direction} pin to shell '{shell.node_id}'",
            details={"shell_node_id": shell.node_id, "direction": direction, "pin_node_id": pin_id},
        )
    return {"pin_node_id": pin_id, "direction": direction, "pin": context.node_summary(pin)}


def navigate_scope(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    target = str(params["target"]).strip().lower()
    before = context.scope_path()
    scene = context.scene
    expected_leaf: str | None = None
    if target == "root":
        navigated = bool(scene.navigate_scope_root())
    elif target == "parent":
        navigated = bool(scene.navigate_scope_parent())
    else:
        node_id = str(params.get("node_id") or "").strip()
        if not node_id:
            raise AutomationOpError(
                INVALID_PARAMS,
                "scope.navigate: node_id is required when target=node.",
                details={"problems": ["params.node_id: is required when target=node"]},
            )
        shell = _require_shell(context, context.require_node(node_id), "scope.navigate")
        if not context.in_active_scope(shell):
            # Move to the scope that contains the shell first, then step inside it.
            scene.open_scope_for_node(shell.node_id)
        navigated = bool(scene.open_subnode_scope(shell.node_id))
        expected_leaf = shell.node_id
    after = context.scope_path()
    if not navigated or after == before or (expected_leaf is not None and (not after or after[-1] != expected_leaf)):
        location = "/".join(after) or "root"
        raise no_effect(
            "scope.navigate",
            f"the scope did not change (now at {location})",
            details={"target": target, "scope_path": after, "previous_scope_path": before},
        )
    return {"scope_path": after, "previous_scope_path": before}


def set_selection(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    mode = str(params.get("mode") or "replace").strip().lower()
    node_ids = _unique_ids(params.get("node_ids") or ())
    scene = context.scene
    if mode == "clear":
        scene.clear_selection()
        return {"selected_node_ids": context.selected_node_ids(), "mode": mode}
    if not node_ids:
        raise AutomationOpError(
            INVALID_PARAMS,
            f"selection.set: node_ids is required for mode={mode}.",
            details={"problems": ["params.node_ids: must contain at least 1 items"], "mode": mode},
        )
    _nodes_in_scope(context, node_ids)
    if mode == "replace":
        scene.clear_selection()
    already_selected = set(context.selected_node_ids())
    for node_id in node_ids:
        if node_id in already_selected:
            continue  # additive select_node toggles; keep it selected
        scene.select_node(node_id, True)
    selected = context.selected_node_ids()
    missing = [node_id for node_id in node_ids if node_id not in selected]
    if missing:
        raise no_effect("selection.set", "the scene refused to select some nodes", details={"missing_node_ids": missing, "mode": mode})
    return {"selected_node_ids": selected, "mode": mode}


def arrange_layout(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids = _unique_ids(params["node_ids"])
    action = str(params["action"]).strip().lower()
    snap_to_grid = bool(params.get("snap_to_grid", False))
    nodes = _nodes_in_scope(context, node_ids)
    if len(node_ids) < 2:
        raise AutomationOpError(
            INVALID_PARAMS,
            "layout.arrange needs at least two distinct nodes.",
            details={"node_ids": node_ids, "problems": ["node_ids: must contain at least 2 distinct ids"]},
        )
    positions_before = {node.node_id: (float(node.x), float(node.y)) for node in nodes}
    scene = context.scene
    with context.with_selection(node_ids):
        if action in ALIGNMENTS:
            scene.align_selected_nodes(ALIGNMENTS[action], snap_to_grid=snap_to_grid)
        else:
            scene.distribute_selected_nodes(DISTRIBUTIONS[action], snap_to_grid=snap_to_grid)
    workspace = context.active_workspace()
    positions_after = {node_id: (float(workspace.nodes[node_id].x), float(workspace.nodes[node_id].y)) for node_id in node_ids}
    moved = [node_id for node_id in node_ids if positions_after[node_id] != positions_before[node_id]]
    return {
        "moved_node_ids": moved,
        "action": action,
        "positions": {node_id: {"x": x, "y": y} for node_id, (x, y) in positions_after.items()},
    }


HANDLERS = {
    'group.wrap': wrap_group,
    'subnode.create': create_subnode,
    'subnode.ungroup': ungroup_subnode,
    'subnode.add_pin': add_subnode_pin,
    'scope.navigate': navigate_scope,
    'selection.set': set_selection,
    'layout.arrange': arrange_layout,
}

__all__ = ["ALIGNMENTS", "DISTRIBUTIONS", "HANDLERS", "PIN_TYPE_BY_DIRECTION"]
